#!/usr/bin/env python3
"""
promotion_decision — composition canonique de la décision de promotion WIKI.

INNER LOOP control-plane (ADR-083 / ADR-089 / ADR-092) : compose les évaluateurs
SPÉCIALISÉS existants en UNE décision, à la SURFACE promotion — jamais un monolithe
dans `evaluate_tier`. Architecture (contrats P0-1/P0-2, C0, #1..#7) :

    snapshot → collect_promotion_evidence(...) → PromotionEvidenceBundle
             → decide_promotion(bundle)  [PURE, 0 I/O]  → PromotionDecision

Invariants :
  - `evaluate_tier` (promote.py) reste UN composant (substance + policy + 5 gates).
  - `decide_promotion` est PURE : même bundle ⇒ même PromotionDecision (déterministe).
  - Fail-closed PRÉSERVANT les dimensions (P0-2) : un évaluateur UNAVAILABLE ⇒
    `promotion_status=BLOCKED/UNKNOWN_FAIL_CLOSED` + reason typé, `substance_tier`
    PRÉSERVÉ — jamais un faux TIER B, jamais router un défaut d'infra→specialist.
  - Détection ≠ routage (C0) : une BlockingReason porte {code, owner_stage,
    detector_stage, evidence} et JAMAIS next_action / worker / ExecutableActionKind.
  - Ordre canonique déterministe des reasons (C0/#4) : jamais un set à ordre implicite.

Unités A3 : (ii) `decide_promotion` pur sur `substance` seul · (iii) coverage /
regression / provenance composés (mêmes invariants fail-closed) · (iv) snapshot +
input_manifest + engine revisions (anti-TOCTOU pendant l'éval) · (v) porte du DUMB
EXECUTOR : `authorize_apply` exige eligible + `reverify_inputs` (manifeste complet +
DEUX engine revisions inchangés) — le `--apply` n'est JAMAIS un 2ᵉ décideur.
"""
from __future__ import annotations

import contextlib
import hashlib
import html
import importlib.util
import io
import itertools
import json
import os
import re
import subprocess
import sys
import stat
import tempfile
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent

SCHEMA_VERSION = "promotion-decision/v1"

PROMOTABLE_INPUT_STATUSES = {"proposed", "in_review"}

STATUS_ELIGIBLE = "ELIGIBLE"
STATUS_BLOCKED = "BLOCKED"
STATUS_UNKNOWN_FAIL_CLOSED = "UNKNOWN_FAIL_CLOSED"

_SUBSTANCE_DETECTOR = "PROMOTE_EVALUATE_TIER"
_COVERAGE_DETECTOR = "COVERAGE_MAP"
_REGRESSION_DETECTOR = "REGRESSION"
_PROVENANCE_DETECTOR = "PROVENANCE_GATE"
_REVISION_DETECTOR = "CANON_REVISION"
_APPLY_GUARD = "APPLY_GUARD"


class PromotionInputError(Exception):
    """Erreur de cœur métier promotion (input invalide / config introuvable) —
    exception de DOMAINE click-free. Le CLI (`promote.py`) la traduit en
    `click.ClickException` À SA FRONTIÈRE (jamais l'inverse : la bibliothèque
    n'importe pas click ; seuls les modules qu'elle charge à l'appel l'importent —
    `gates/`, et les exporteurs `build_exports_seo.py` / `build_exports_diagnostic.py`
    qu'exécute la Safety Auto-Gate). Sous-classe d'`Exception` ⇒ capturée telle quelle
    par les handlers fail-closed existants (`except Exception`), 0 changement de
    comportement."""


class SafetyInputUnavailable(Exception):
    """Entrée gouvernée absente de l'arbre évalué (ex. répertoire de travail de la revue
    gap1, sans `_meta/`) : la condition de la Safety Auto-Gate qui la lit n'y est pas
    évaluable. Défaut d'infrastructure, jamais un verdict sur le contenu (P0-2) : la
    condition reste fausse (fail-closed) et son détail porte `status: UNAVAILABLE`."""


def blocking_reason(code: str, owner_stage: str, detector_stage: str, evidence) -> dict:
    """Construit une BlockingReason typée (C0). `evidence` reste un dict structuré."""
    return {
        "code": str(code),
        "owner_stage": str(owner_stage),
        "detector_stage": str(detector_stage),
        "evidence": evidence if isinstance(evidence, dict) else {"detail": evidence},
    }


def _reason_sort_key(r: dict):
    """Ordre canonique STABLE (C0/#4) — reason code, detector, owner, evidence."""
    return (
        r.get("code", ""),
        r.get("detector_stage", ""),
        r.get("owner_stage", ""),
        str(r.get("evidence", "")),
    )


def _substance_tier(substance: dict):
    """Dimension SUBSTANCE, exposée même quand la promotion est bloquée (P0-2).

    Priorité au tier 6-dim shadow (granularité S/A/B/C/D, observabilité toujours
    calculée) ; sinon dérive du check SUBSTANCE_SCORE/SUBSTANCE_TIER (A si pass, B sinon).
    """
    shadow = (substance or {}).get("shadow_score") or {}
    st = shadow.get("shadow_tier")
    if st:
        return st
    for c in (substance or {}).get("checks", []):
        if c.get("code") in ("SUBSTANCE_SCORE", "SUBSTANCE_TIER"):
            return "A" if c.get("status") == "pass" else "B"
    return None


def _reasons_from_substance(substance: dict) -> list[dict]:
    """Dérive les BlockingReason typées depuis les CHECKS structurés (pas de prose, C0).
    SAFETY_HUMAN_REVIEW est composé à part (`_reasons_from_safety`)."""
    reasons: list[dict] = []
    for c in (substance or {}).get("checks", []):
        if c.get("code") == "SAFETY_HUMAN_REVIEW":
            continue
        if c.get("status") != "pass":
            reasons.append(blocking_reason(
                c.get("code", "SUBSTANCE_UNKNOWN"),
                c.get("owner_stage", "SUBSTANCE"),
                _SUBSTANCE_DETECTOR,
                c.get("evidence", {}),
            ))
    return reasons


def _reasons_from_coverage(coverage) -> list[dict]:
    """Coverage-strict (check-coverage-map). FAIL → bloquant (mirror CI --strict) ;
    WARN → observability (advisory) ; UNAVAILABLE → fail-closed distinct (infra)."""
    if not coverage:
        return []
    status = str(coverage.get("status", "")).upper()
    ev = coverage.get("evidence", {})
    if status == "FAIL":
        return [blocking_reason("COVERAGE_STRICT_FAIL", "COVERAGE", _COVERAGE_DETECTOR, ev)]
    if status == "UNAVAILABLE":
        return [blocking_reason("COVERAGE_GATE_UNAVAILABLE", "COVERAGE", _COVERAGE_DETECTOR, ev)]
    return []  # PASS / WARN → non bloquant


def _reasons_from_regression(regression) -> list[dict]:
    """Régression (compare-proposal-versions). REGRESSED → bloquant ;
    NEW/NEUTRAL/IMPROVED → pass ; UNAVAILABLE (baseline attendue introuvable) → fail-closed."""
    if not regression:
        return []
    verdict = str(regression.get("verdict", "")).upper()
    ev = regression.get("evidence", {})
    if verdict == "REGRESSED":
        return [blocking_reason("REGRESSION_DETECTED", "AUTHORING", _REGRESSION_DETECTOR, ev)]
    if verdict == "UNAVAILABLE":
        return [blocking_reason("REGRESSION_GATE_UNAVAILABLE", "AUTHORING", _REGRESSION_DETECTOR, ev)]
    return []


def _reasons_from_provenance(provenance) -> list[dict]:
    """Provenance raw_ref cross-repo (quality-gates). FAIL → bloquant (fail-open
    non-safety fermé, A6) ; UNAVAILABLE → fail-closed DISTINCT (infra, P0-2) —
    JAMAIS confondu avec un échec de contenu, substance_tier préservé en amont."""
    if not provenance:
        return []
    status = str(provenance.get("status", "")).upper()
    ev = provenance.get("evidence", {})
    if status == "FAIL":
        return [blocking_reason("PROVENANCE_RAW_REF_FAIL", "PROVENANCE", _PROVENANCE_DETECTOR, ev)]
    if status == "UNAVAILABLE":
        return [blocking_reason("PROVENANCE_GATE_UNAVAILABLE", "PROVENANCE", _PROVENANCE_DETECTOR, ev)]
    return []


_REGRESSION_PASS_VERDICTS = {"NEW", "NEUTRAL", "IMPROVED"}


def _reasons_from_safety(substance: dict, bundle: dict) -> list[dict]:
    """Safety Auto-Gate composée (quality-gates.md §7). Non-sécurité → aucun motif.

    Sécurité → éligible seulement si les conditions locales (evaluate_tier), la couverture
    stricte, la régression et la provenance PASSENT, ET si `SAFETY_AUTO_APPROVAL_ADR` est
    renseignée. Un résultat absent (None) n'est jamais un succès. Sinon UN motif
    SAFETY_HUMAN_REVIEW (identifiant historique) portant les conditions bloquantes et l'état
    de la politique : blocage technique ou de gouvernance, jamais une tâche humaine."""
    check = next((c for c in (substance or {}).get("checks", [])
                  if c.get("code") == "SAFETY_HUMAN_REVIEW"), None)
    if check is None or check.get("status") == "pass":
        return []  # `_build_checks` : fail ⇔ famille sécurité
    evidence = check.get("evidence") or {}
    conditions = dict(evidence.get("conditions") or {})
    if not conditions:
        conditions["safety_local_conditions_evaluated"] = False
    coverage = bundle.get("coverage") or {}
    regression = bundle.get("regression") or {}
    provenance = bundle.get("provenance") or {}
    conditions["coverage_strict_pass"] = str(coverage.get("status", "")).upper() == "PASS"
    conditions["regression_gate_pass"] = (
        str(regression.get("verdict", "")).upper() in _REGRESSION_PASS_VERDICTS)
    conditions["provenance_pass"] = str(provenance.get("status", "")).upper() == "PASS"
    blocking = [k for k, ok in conditions.items() if ok is not True]
    if not blocking and SAFETY_AUTO_APPROVAL_ADR:
        return []
    details = evidence.get("details") or {}
    return [blocking_reason("SAFETY_HUMAN_REVIEW", check.get("owner_stage", "POLICY_SAFETY"),
                            _SUBSTANCE_DETECTOR, {
                                "is_safety": True,
                                "conditions": conditions,
                                "blocking_conditions": blocking,
                                # entrée gouvernée absente du contexte évalué : infra, pas contenu
                                "unavailable_conditions": [
                                    k for k in blocking if isinstance(details.get(k), dict)
                                    and details[k].get("status") == "UNAVAILABLE"],
                                "details": details,
                                "policy": {"auto_approval_adr": SAFETY_AUTO_APPROVAL_ADR,
                                           "status": "ratified" if SAFETY_AUTO_APPROVAL_ADR
                                           else "not_ratified"},
                            })]


def _relation_review_trace(substance: dict, status: str) -> dict:
    """Relecture des relations hors sécurité (ADR-116), en trace seulement : jamais un motif
    bloquant, une relation non relue ne bloque pas sa fiche (D3). Pour chaque relation : les
    conditions de D2, `fiche_eligible` composée ici sur le statut de la fiche, les conditions
    bloquantes, `would_review` et le détail de chaque calcul (D6). Une condition absente n'est
    jamais un succès. Conditions locales absentes ou en erreur : `evaluated` faux, et
    `apply_promotion` écrit les relations telles que proposées."""
    policy = {"relation_review_adr": RELATION_REVIEW_ADR,
              "status": "ratified" if RELATION_REVIEW_ADR else "not_ratified"}
    local = (substance or {}).get("relation_review")
    if not isinstance(local, dict) or "error" in local:
        return {"evaluated": False, "policy": policy, "relations": [],
                **({"error": local["error"]} if isinstance(local, dict) else {})}
    relations = []
    for relation in local.get("relations") or []:
        conditions = {"fiche_eligible": status == STATUS_ELIGIBLE, **(relation.get("conditions") or {})}
        blocking = [k for k in RELATION_REVIEW_CONDITIONS if conditions.get(k) is not True]
        relations.append({"index": relation.get("index"), "conditions": conditions,
                          "blocking_conditions": blocking, "would_review": not blocking,
                          "details": relation.get("details") or {}})
    return {"evaluated": True, "policy": policy, "relations": relations}


def _relation_review_verdicts(decision: dict):
    """Verdicts qu'`apply_promotion` écrit (ADR-116 D3) : index d'une relation de D1 (`not_safety`
    prouvée) → `would_review`. Trace absente ou non évaluée : None, relations telles que proposées."""
    trace = (decision or {}).get("relation_review")
    if not isinstance(trace, dict) or trace.get("evaluated") is not True:
        return None
    return {r["index"]: r.get("would_review") is True for r in trace.get("relations") or []
            if isinstance(r, dict) and isinstance(r.get("index"), int)
            and (r.get("conditions") or {}).get("not_safety") is True}


def _canon_revision_trace(bundle: dict, status: str):
    """Révision du canon (ADR-117 D7), seulement si la proposition déclare `revision_of` : la
    déclaration, la version remplacée, les conditions de D1 à D3, les conditions bloquantes et
    leurs codes de refus, le verdict et le delta de régression, `would_revise` et l'état de la
    politique. `fiche_eligible` (statut de la fiche avant ces motifs) et `regression_pass` (porte
    de régression existante, le canon remplacé pour base) sont composées ici. Une condition
    absente ou en erreur n'est jamais un succès. Aucune révision déclarée : None."""
    local = bundle.get("canon_revision")
    if local is None:
        return None
    if not isinstance(local, dict):
        local = {"error": "canon_revision_malformed"}
    regression = bundle.get("regression") or {}
    verdict = str(regression.get("verdict", "")).upper()
    computed = local.get("conditions") or {}
    conditions = {k: computed.get(k) is True for k in CANON_REVISION_CONDITIONS}
    conditions["fiche_eligible"] = status == STATUS_ELIGIBLE
    conditions["regression_pass"] = (verdict in _REVISION_REGRESSION_PASS_VERDICTS
                                     and computed.get("baseline_is_canon") is True)
    details = dict(local.get("details") or {})
    details["regression_pass"] = {"verdict": verdict or None,
                                  "baseline_is_canon": computed.get("baseline_is_canon") is True}
    blocking = [k for k in CANON_REVISION_CONDITIONS if conditions[k] is not True]
    return {
        "evaluated": "error" not in local,
        "revision_of": local.get("revision_of"),
        "replaced": local.get("replaced"),
        "policy": {"canon_revision_adr": CANON_REVISION_ADR,
                   "status": "ratified" if CANON_REVISION_ADR else "not_ratified"},
        "conditions": conditions,
        "blocking_conditions": blocking,
        "refusal_codes": [CANON_REVISION_REFUSALS[k] for k in blocking if k in CANON_REVISION_REFUSALS],
        "would_revise": not blocking,
        "regression": {"verdict": verdict or None, **(regression.get("evidence") or {})},
        "details": details,
        **({"error": local["error"]} if "error" in local else {}),
    }


def _reasons_from_canon_revision(trace) -> list[dict]:
    """Motifs d'une révision déclarée (ADR-117 D1 à D3, D5) : un par code de refus, et
    `CANON_REVISION_NOT_RATIFIED` tant que `CANON_REVISION_ADR` est vide, même toutes conditions
    prouvées. Aucune révision déclarée : aucun motif."""
    if trace is None:
        return []
    reasons = [blocking_reason(CANON_REVISION_REFUSALS[k], "POLICY_REVISION", _REVISION_DETECTOR, {
                   "condition": k, "revision_of": trace["revision_of"],
                   "detail": trace["details"].get(k)})
               for k in trace["blocking_conditions"] if k in CANON_REVISION_REFUSALS]
    if not CANON_REVISION_ADR:
        reasons.append(blocking_reason("CANON_REVISION_NOT_RATIFIED", "POLICY_REVISION",
                                       _REVISION_DETECTOR, {
                                           "revision_of": trace["revision_of"],
                                           "would_revise": trace["would_revise"],
                                           "policy": trace["policy"]}))
    return reasons


def _status_of(reasons: list[dict]) -> str:
    definitive = [r for r in reasons if not r["code"].endswith("_UNAVAILABLE")]
    if not reasons:
        return STATUS_ELIGIBLE
    if definitive:
        return STATUS_BLOCKED
    return STATUS_UNKNOWN_FAIL_CLOSED  # seulement des évaluateurs indisponibles


def decide_promotion(bundle: dict) -> dict:
    """PURE : compose un PromotionEvidenceBundle en PromotionDecision (0 I/O, 0 repo).

    Déterministe : même bundle ⇒ même décision. Fail-closed préservant les dimensions
    (P0-2) : un évaluateur UNAVAILABLE ⇒ status UNKNOWN_FAIL_CLOSED, jamais un faux
    TIER B, `substance_tier` toujours exposé. Une révision déclarée (ADR-117) ajoute ses motifs
    à ceux de la fiche et sa trace à la décision (`canon_revision`).
    """
    bundle = bundle or {}
    substance = bundle.get("substance") or {}
    reasons: list[dict] = list(_reasons_from_substance(substance))
    reasons += _reasons_from_safety(substance, bundle)
    reasons += _reasons_from_coverage(bundle.get("coverage"))
    reasons += _reasons_from_regression(bundle.get("regression"))
    reasons += _reasons_from_provenance(bundle.get("provenance"))
    revision = _canon_revision_trace(bundle, _status_of(reasons))
    reasons += _reasons_from_canon_revision(revision)

    reasons.sort(key=_reason_sort_key)
    status = _status_of(reasons)

    decision = {
        "schema_version": SCHEMA_VERSION,
        "substance_tier": _substance_tier(substance),
        "promotion_status": status,
        "eligible": not reasons,
        "blocking_reasons": reasons,
        "relation_review": _relation_review_trace(substance, status),
    }
    if revision is not None:
        decision["canon_revision"] = revision
    return decision


# --- Normalizers (PURS) : sortie brute d'un évaluateur → sous-résultat du bundle -
# Isolent la forme spécifique de chaque évaluateur existant du contrat du bundle.
# Aucune I/O ici : les évaluateurs réels sont appelés par le callable canonique (A3-iv).
def normalize_coverage(check_result: dict) -> dict:
    """`check-coverage-map.check_fiche` → {status: PASS/WARN/FAIL, evidence}."""
    return {
        "status": str((check_result or {}).get("status", "")).upper(),
        "evidence": {
            "fails": (check_result or {}).get("fails", []),
            "warns": (check_result or {}).get("warns", []),
        },
    }


def normalize_regression(compare_result: dict) -> dict:
    """`compare-proposal-versions.compare` → {verdict, evidence}."""
    cr = compare_result or {}
    return {
        "verdict": str(cr.get("verdict", "")).upper(),
        "evidence": {
            "delta_score": cr.get("delta_score"),
            "old_score": cr.get("old_score"),
            "new_score": cr.get("new_score"),
            "predecessor_found": cr.get("predecessor_found"),
        },
    }


def normalize_provenance(failures, warnings, raw_available: bool = True) -> dict:
    """`quality-gates.gate_source_catalog_raw_refs` (+ dispo RAW) → {status, evidence}.

    Distingue INFRA-indisponible (raw absent / raw_inventory_unreachable /
    cross_repo_env_missing) d'un ÉCHEC de contenu (P0-2) — jamais confondus.
    """
    failures = list(failures or [])
    warnings = list(warnings or [])
    infra_markers = ("raw_inventory_unreachable", "cross_repo_env_missing")
    infra_unavailable = (not raw_available) or any(
        any(m in f for m in infra_markers) for f in failures
    )
    if infra_unavailable:
        return {"status": "UNAVAILABLE",
                "evidence": {"failures": failures, "warnings": warnings,
                             "raw_available": bool(raw_available)}}
    if failures:
        return {"status": "FAIL", "evidence": {"failures": failures, "warnings": warnings}}
    return {"status": "PASS", "evidence": {"warnings": warnings}}


def assemble_bundle(substance: dict, *, coverage_raw=None, regression_raw=None,
                    provenance_raw=None, raw_available: bool = True) -> dict:
    """Assemble un PromotionEvidenceBundle (PUR) depuis les sorties brutes des
    évaluateurs. `*_raw is None` ⇒ évaluateur non exécuté (champ None ⇒ non bloquant).
    `provenance_raw` = tuple (failures, warnings)."""
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "substance": substance,
        "coverage": None,
        "regression": None,
        "provenance": None,
    }
    if coverage_raw is not None:
        bundle["coverage"] = normalize_coverage(coverage_raw)
    if regression_raw is not None:
        bundle["regression"] = normalize_regression(regression_raw)
    if provenance_raw is not None:
        failures, warnings = provenance_raw
        bundle["provenance"] = normalize_provenance(failures, warnings, raw_available=raw_available)
    return bundle


# --- A3-iv : snapshot / lignée reproductible (contrats #1/#3/#4/#5) ------------
# Fichiers-source des évaluateurs qui produisent le bundle : leur hash = la
# `evaluation_engine_revision` (couvre le code réellement exécuté, worktree dirty inclus).
_EVALUATION_ENGINE_FILES = (
    "promotion_decision.py", "quality-gates.py", "check-coverage-map.py",
    "compare-proposal-versions.py", "shadow_score.py", "compute-confidence-score.py",
    "editorial_sections.py", "requirements-scoring.txt", "gen_coverage_map.py",
    # Safety Auto-Gate : classifieur, lock numérique, famille, projections des exports SEO et
    # diagnostic (texte publié depuis le frontmatter ; la seconde exécute la formule de
    # confiance symptôme), et les 5 contrôles qualité.
    "safety_families.py", "numeric_exactitude.py", "author_from_raw.py", "build_exports_seo.py",
    "build_exports_diagnostic.py", "compute-symptom-confidence.py",
    "gates/__init__.py", "gates/_common.py", "gates/source_gate.py", "gates/claim_gate.py",
    "gates/contradiction_gate.py", "gates/risk_gate.py", "gates/confidence_gate.py",
)


def _sha256_file(path: Path):
    p = Path(path)
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _repo_rel(path: Path, *roots) -> str:
    """Chemin repo-relatif POSIX (jamais absolu machine-dépendant)."""
    p = Path(path).resolve()
    for root in roots:
        if root is None:
            continue
        try:
            return p.relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            continue
    return p.name


def _git_revision(root) -> str:
    """SHA git court + drapeau `-dirty` (contrat #3 : SHA seule ≠ contenu réel)."""
    root = Path(root)
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                             check=True, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root,
                               check=True, capture_output=True, text=True).stdout.strip()
        return f"{sha}-dirty" if dirty else sha
    except Exception:
        return "unknown"


def _engine_revision(filenames) -> str:
    """Hash déterministe du CONTENU des fichiers-source (couvre le code dirty)."""
    h = hashlib.sha256()
    for name in sorted(filenames):
        p = SCRIPTS_DIR / name
        h.update(name.encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes() if p.is_file() else b"<absent>")
        h.update(b"\0")
    return h.hexdigest()


def _effective_raw_root(raw_root, wiki_root) -> Path:
    """Use the same explicit/environment/default RAW root for snapshots and gates."""
    selected = raw_root if raw_root is not None else os.environ.get("AUTOMECANIK_RAW_PATH")
    return Path(selected or Path(wiki_root).parent / "automecanik-raw").resolve()


def capture_input_manifest(candidate_path, wiki_root, raw_root, baseline_path) -> dict:
    """Manifeste déterministe des inputs verdict-affectants réellement lisibles +
    revisions d'engine. `input_manifest` trié canoniquement (role, path). Le hash suit
    le contenu réel (worktree dirty). Aucune prétention de repro si SHA-only insuffisant."""
    wiki_root = Path(wiki_root)
    raw_root = _effective_raw_root(raw_root, wiki_root)
    entries: list[dict] = []

    def add(role: str, path):
        p = Path(path)
        entries.append({"role": role, "path": _repo_rel(p, wiki_root, raw_root),
                        "sha256": _sha256_file(p)})

    add("candidate", candidate_path)
    # The native evaluator can resolve its baseline without a caller override.
    # Capture the actual destination (including absence) independently: another
    # baseline must never hide a concurrent change to the canonical fiche.
    fm, body = _parse_markdown(Path(candidate_path))
    add("canon_target", _promotion_target_path(wiki_root, fm))
    if baseline_path is not None:
        add("baseline", baseline_path)
    add("source_catalog", wiki_root / "_meta" / "source-catalog.yaml")
    add("coverage_schema", wiki_root / "_meta" / "schema" / "coverage-map.schema.json")
    add("reality_manifest", wiki_root / "_meta" / "reality-manifest.json")
    add("numeric_ranges", wiki_root / NUMERIC_RANGES_RELPATH)
    # Coverage checker keys by filename; shadow loader keys by declared slug.
    # Capture both when different, including absence, before allowing any apply.
    for slug in sorted({Path(candidate_path).stem, fm.get("slug") or Path(candidate_path).stem}):
        add("coverage_map", wiki_root / "proposals" / "_coverage" / f"{slug}.coverage.yaml")
    # Snapshot only targets actually referenced by this candidate, using the
    # scorer's own syntax. An unrelated fiche must not invalidate the decision.
    scorer = _load_module("_confidence_snapshot", "compute-confidence-score.py")
    link_slugs = {slug.strip() for slug in scorer.WIKILINK_RE.findall(body)}
    if link_slugs:
        for link_target in sorted((wiki_root / "wiki").rglob("*.md")):
            if link_target.stem in link_slugs:
                add("canonical_link_target", link_target)
    if raw_root is not None:
        add("raw_inventory", raw_root / "manifests" / "source-inventory.csv")
        add("raw_checksums", raw_root / "manifests" / "checksums.json")
        # Bind the bytes of referenced archives as well as inventory metadata.
        # Missing/malformed evidence still has its map/catalog inputs captured;
        # the real evaluators reject it instead of the snapshot inventing proof.
        try:
            ccm = _load_module("_coverage_snapshot", "check-coverage-map.py")
            catalog = ccm._load_catalog(wiki_root)
            qg = _load_module("_archive_snapshot", "quality-gates.py")
            qg.RAW_INVENTORY = raw_root / "manifests" / "source-inventory.csv"
            # Archives cited by citations[] are verdict inputs too (gate_citation_anchors).
            slugs = ccm.referenced_source_slugs(Path(candidate_path), wiki_root) | qg.cited_source_slugs(fm)
            paths, _ = qg.source_archive_paths({slug: catalog[slug] for slug in slugs if slug in catalog})
        except (OSError, ValueError, TypeError, AttributeError, yaml.YAMLError):
            paths = {}
        for path in sorted(set(paths.values())):
            add("raw_archive", path)

    entries.sort(key=lambda e: (e["role"], e["path"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "input_manifest": entries,
        "wiki_revision": _git_revision(wiki_root),
        "raw_revision": _git_revision(raw_root) if raw_root else None,
        "evaluation_engine_revision": _engine_revision(_EVALUATION_ENGINE_FILES),
        "decision_engine_revision": _engine_revision(("promotion_decision.py",)),
    }


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# =============================================================================
# Cœur métier de promotion — DÉPLACÉ depuis promote.py (A+ : frontière CLI↔library).
# `promote.py` (adapter CLI) IMPORTE ces symboles ; la bibliothèque canonique ne
# charge/n'importe JAMAIS le module CLI (jamais library→CLI). Corps INCHANGÉS
# (mêmes invariants ADR-083/088/091) — seule différence : les erreurs de cœur métier
# lèvent `PromotionInputError` (domain), que le CLI traduit en click à sa frontière.
# `evaluate_tier` + `gates/` restent tels quels (leur découplage click/pydantic est
# un autre chantier, hors périmètre).
# =============================================================================


# --- Constantes gouvernées (ADR-083) -----------------------------------------
# Validation automatique demandée le 2026-09-12 ; plancher qualité §7 conservé.
# Ce score est un filtre déterministe, pas une probabilité de vérité.
AUTO_PROMOTE_THRESHOLD = 0.85
AUTO_PROMOTE_TRUTH_LEVELS = {"L1", "L2"}
# Cutover ADR-088 (gaté par flag, défaut OFF) : quel moteur de substance gate l'auto-promotion.
#   legacy      = confidence_score scalaire 0-1 >= seuil (comportement historique, défaut)
#   adr088_6dim = tier 6-dim shadow_score (planchers entity-aware) ∈ {A,S}
# Le FLIP (mettre PROMOTE_GATE_ENGINE=adr088_6dim) reste owner-gated : ADR-088 accepté au vault
# + 3 critères §F mesurés (new⊆old · known-bad→B/C · ≥1 fiche TIER A). Fail-closed dans les 2 modes.
PROMOTE_GATE_ENGINE_ENV = "PROMOTE_GATE_ENGINE"
ADR088_PROMOTE_TIERS = {"A", "S"}
MIN_DISTINCT_SOURCE_KINDS = 2
PROMOTER_ID = "skill:promoter"
WIKI_ENTITY_DIRS = {"gamme", "vehicle", "constructeur", "diagnostic"}

# --- Invariant SÉCURITÉ : familles sécurité-critiques → JAMAIS auto-promues ----
# Classification déléguée au SINGLE SOURCE `safety_families.is_safety_proposal`
# (ADR fix #5) — partagé avec `quality-gates.gate_safety_unsourced`. Import paresseux
# (même pattern que `_load_gates` / `_compute_shadow` : modules chargés par chemin).
# Fail-closed : une fiche sécurité reste 100% revue humaine, même substance forte.
_safety_families_mod = None


def _is_safety_proposal(fm: dict) -> bool:
    """Délègue au classifieur sécurité unifié (single source, ADR fix #5). Fail-closed."""
    global _safety_families_mod
    try:
        if _safety_families_mod is None:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import safety_families as _sf
            _safety_families_mod = _sf
        return _safety_families_mod.is_safety_proposal(fm)
    except Exception:
        return True  # fail-closed : doute → sécurité → revue humaine


# --- Safety Auto-Gate (quality-gates.md §7) -------------------------------------
# Une fiche sécurité n'est éligible que si TOUTES ses conditions sont prouvées ET que la
# politique est levée. La politique est une constante de CODE, jamais une variable
# d'environnement ni une option CLI : la lever = PR WIKI dédiée qui y inscrit l'ADR vault
# ACCEPTÉE amendant ADR-091 §4 / ADR-093. Le fichier entre dans `decision_engine_revision` :
# changer la constante invalide toute décision déjà rendue (STALE_DECISION).
# Levée par ADR-114 (vault, acceptée le 2026-10-15, D5), refermée le 2026-10-22 (ADR-114
# §Retour arrière) : la relecture a posteriori de la première fiche promue a relevé des défauts
# de sens. La relever à nouveau = PR WIKI dédiée qui y réinscrit l'ADR.
SAFETY_AUTO_APPROVAL_ADR: str | None = None
# Planchers des dimensions shadow A (preuve) et C (couverture), en points bruts.
SAFETY_DIM_FLOORS = {"A": 22.0, "C": 15.0}
# Éditeurs distincts exigés parmi les sources de rôle `proof` citées : la barre L3 d'ADR-093
# (≥ 3 sources primaires distinctes, non-sécurité) ; une fiche sécurité ne passe pas plus bas,
# une relation relue par la règle d'ADR-116 non plus (ADR-116 D2, `proof_publishers_min`).
SAFETY_PROOF_PUBLISHERS_MIN = 3

# --- Relecture des relations hors sécurité par la règle de preuve (ADR-116) ------
# Même verrou que la Safety Auto-Gate : une constante de CODE, jamais une variable
# d'environnement ni une option CLI. Vide : report-only, le décideur inscrit les conditions de
# D2 dans sa trace (`would_review`) et `apply_promotion` n'écrit rien dans la fiche. La lever =
# PR WIKI dédiée qui y inscrit "ADR-116", recevable une fois ses préconditions (a)-(e)
# fusionnées (ADR-116 D4). Le fichier entre dans `decision_engine_revision` : changer la
# constante invalide toute décision déjà rendue (STALE_DECISION). Refermer = la remettre à None
# (ADR-116 §Retour arrière).
RELATION_REVIEW_ADR: str | None = None
# Conditions d'ADR-116 D2, toutes exigées pour chaque relation, dans l'ordre de l'ADR.
RELATION_REVIEW_CONDITIONS = ("fiche_eligible", "not_safety", "sources_raw_proven",
                              "citations_anchored", "proof_publishers_min",
                              "source_policy_resolved", "numeric_verified", "no_review_claimed")
# Préfixe du cachet qu'`apply_promotion` écrit sur une relation relue (ADR-116 D3), seule
# autorité de relecture qu'une révision peut remplacer (ADR-117 D1).
RELATION_REVIEW_STAMP_PREFIX = "rule:ADR-116@"

# --- Révision en place du canon écrit par le promoteur (ADR-117) -------------------
# Même verrou que les deux précédents : une constante de CODE, jamais une variable
# d'environnement ni une option CLI. Vide : report-only, le décideur calcule D1 à D3 pour toute
# proposition qui déclare `revision_of` et inscrit `would_revise` dans sa trace ; la décision
# reste BLOCKED (`CANON_REVISION_NOT_RATIFIED`) et `apply_promotion` refuse l'écrasement (L4
# d'ADR-093). La lever = PR WIKI dédiée qui y inscrit "ADR-117", recevable une fois ses
# préconditions (a)-(e) fusionnées (ADR-117 D5). Le fichier entre dans
# `decision_engine_revision` : changer la constante invalide toute décision déjà rendue
# (STALE_DECISION). Refermer = la remettre à None (ADR-117 §Retour arrière).
# Levée par ADR-117 (vault, acceptée le 2026-10-22, D5).
CANON_REVISION_ADR: str | None = "ADR-117"
# Conditions d'ADR-117 D1 à D3, toutes exigées, dans l'ordre de l'ADR.
CANON_REVISION_CONDITIONS = ("promoter_canon", "not_safety", "no_human_authority",
                             "target_approved", "base_current", "fiche_eligible",
                             "regression_pass", "exportable_unchanged", "safety_rules_unchanged")
# Code de refus de chaque condition. `fiche_eligible` n'en a pas : la décision porte déjà les
# motifs qui la rendent non éligible.
CANON_REVISION_REFUSALS = {
    "promoter_canon": "REVISION_NOT_PROMOTER_CANON",
    "not_safety": "REVISION_SAFETY",
    "no_human_authority": "REVISION_HUMAN_AUTHORITY_PRESENT",
    "target_approved": "REVISION_TARGET_MISSING",
    "base_current": "REVISION_BASE_STALE",
    "regression_pass": "REVISION_REGRESSION",
    "exportable_unchanged": "REVISION_EXPORTABLE_CHANGED",
    "safety_rules_unchanged": "REVISION_SAFETY_RULES_CHANGED",
}
# Base de régression d'une révision : le canon remplacé. NEW (base absente) ne passe pas (D3).
_REVISION_REGRESSION_PASS_VERDICTS = {"NEUTRAL", "IMPROVED"}
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
# Les 5 contrôles qualité attendus, dans l'ordre de `_load_gates` (test de parité).
CANONICAL_GATE_NAMES = ("source", "claim", "contradiction", "risk", "confidence")
NUMERIC_RANGES_RELPATH = Path("_meta") / "numeric-plausibility.yaml"
SOURCE_CATALOG_RELPATH = Path("_meta") / "source-catalog.yaml"


def load_numeric_ranges(path) -> dict:
    """{family: {quantity: {...}}} depuis `_meta/numeric-plausibility.yaml` — chargeur unique.

    Absent → {} : aucune plage, aucune valeur ne peut être `numeric_verified` (fail-closed).
    Illisible ou mal formé → ValueError ; l'appelant le rend observable, jamais de repli ici."""
    path = Path(path)
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"numeric_ranges_unreadable: {exc}") from exc
    families = data.get("families", {}) if isinstance(data, dict) else None
    if not isinstance(families, dict):
        raise ValueError("numeric_ranges_malformed: `families` doit être un mapping")
    return families


# --- Invariant ANTI-NUMBER-SWAPPING : valeurs numériques critiques → revue humaine -
# Axiome n°0 : le contenu ne FABRIQUE jamais une valeur. La provenance PAR-VALEUR
# n'existe pas dans le modèle (`source_refs` = niveau document) → la corroboration
# automatique par-nombre est IMPOSSIBLE. On route donc vers la revue humaine les
# valeurs HIGH-HARM (couple, pression) où un number-swapping est dangereux ; les
# cotes mm/µm et températures sont FLAGGÉES (observabilité) sans bloquer (mesuré :
# block ≈ 2 fiches véhicule à couple/pression ; les fiches sécurité sont déjà bloquées).
# Enforcement par-valeur complet = futur (provenance par-claim au schéma, ADR-gated).
_NUM_PREFIX = r"(?<![\w.,])\d[\d.,   ]*\s?"
CRITICAL_NUMERIC_BLOCK = re.compile(
    _NUM_PREFIX + r"(Nm|N·m|N\.m|daNm|m\.kg|mkg|bar|kPa|MPa|psi)\b", re.IGNORECASE
)
CRITICAL_NUMERIC_OBSERVE = re.compile(
    _NUM_PREFIX + r"(mm|µm|μm|microns?|°\s?C)\b", re.IGNORECASE
)


def _numeric_review_flags(body: str) -> dict:
    """Inventaire des valeurs numériques critiques d'un corps de proposal.

    `block`   = couple/pression (HIGH-HARM) : number-swapping dangereux, non
                auto-vérifiable → revue humaine obligatoire avant auto-promotion.
    `observe` = cotes / températures : flaggées pour le relecteur, NE bloquent PAS.
    Fail-closed : toute erreur → `block` non vide (route vers revue humaine).
    """
    try:
        block = sorted({m.group(0).strip() for m in CRITICAL_NUMERIC_BLOCK.finditer(body or "")})
        observe = sorted({m.group(0).strip() for m in CRITICAL_NUMERIC_OBSERVE.finditer(body or "")})
        return {"block": block, "observe": observe}
    except Exception as exc:  # fail-closed : doute → revue humaine
        return {"block": [f"<erreur classif numérique: {exc}>"], "observe": []}


FRONTMATTER_SEPARATOR = "---"


# --- Composition de l'existant (aucun nouveau gate, aucun nouvel index) -------
def _load_gates():
    """Importe les 5 wrappers de gates existants (package _scripts/gates/)."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    from gates.claim_gate import run_claim_gate
    from gates.confidence_gate import run_confidence_gate
    from gates.contradiction_gate import run_contradiction_gate
    from gates.risk_gate import run_risk_gate
    from gates.source_gate import run_source_gate

    return [
        ("source", run_source_gate),
        ("claim", run_claim_gate),
        ("contradiction", run_contradiction_gate),
        ("risk", run_risk_gate),
        ("confidence", run_confidence_gate),
    ]


def _load_confidence_fn():
    """Charge le calcul détaillé unique (`explain_score`) depuis compute-confidence-score.py
    (filename à tirets). Il renvoie un dict à clé `score` que `evaluate_tier` accepte tel quel."""
    path = SCRIPTS_DIR / "compute-confidence-score.py"
    spec = importlib.util.spec_from_file_location("_confidence_score", path)
    if spec is None or spec.loader is None:
        raise PromotionInputError(f"compute-confidence-score.py introuvable: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.explain_score


def _parse_markdown(path: Path, *, source_bytes: bytes | None = None) -> tuple[dict[str, Any], str]:
    text = (path.read_text(encoding="utf-8") if source_bytes is None else
            source_bytes.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n"))
    if not text.startswith(FRONTMATTER_SEPARATOR):
        raise PromotionInputError(f"proposal sans frontmatter: {path}")
    parts = text.split(f"\n{FRONTMATTER_SEPARATOR}\n", 1)
    if len(parts) != 2:
        raise PromotionInputError(f"frontmatter close-fence manquante: {path}")
    fm = yaml.safe_load(parts[0].lstrip(FRONTMATTER_SEPARATOR).lstrip("\n"))
    if not isinstance(fm, dict):
        raise PromotionInputError(f"frontmatter non-dict: {path}")
    return fm, parts[1]


_COMMIT_SHA_FALLBACK = "0000000"


def _wiki_commit_sha(wiki_root: Path) -> str:
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=wiki_root, check=True, capture_output=True, text=True,
        )
        return out.stdout.strip()
    except Exception:
        return _COMMIT_SHA_FALLBACK


# --- Shadow scoring 6-dim (ADR-088 §F : observabilité AVANT cutover) ----------
# SHADOW pur : calcule le tier 6-dim À CÔTÉ de la décision legacy, l'attache à
# l'evidence pour mesurer les 3 critères de cutover sur le VRAI chemin de promotion,
# SANS jamais modifier la décision de porte. Fail-closed total : toute erreur →
# None (jamais de blocage, jamais d'exception remontée à evaluate_tier).
def _compute_shadow(fm: dict, body: str, target: Path, wiki_root: Path) -> dict | None:
    """Tier shadow 6-dim (report-only). Retourne un dict observabilité ou None si indéterminable.

    Réutilise `shadow_score.score` (ADR-088 Phase 3.3) + `reality_manifest` (lecture 0-DB).
    coverage-map : réutilise `shadow_score._load_coverage_map` (PR #53) si présent, sinon dégrade
    proprement à `coverage_map=None` (dim A → `A:no_coverage_map(dégradé)`, jamais de crash).
    """
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        import reality_manifest as _rm
        import shadow_score as _ss

        manifest = _rm.load_manifest(wiki_root / "_meta" / "reality-manifest.json")
        cmap = None
        loader = getattr(_ss, "_load_coverage_map", None)  # fourni par PR #53
        if callable(loader):
            cmap = loader(fm.get("slug") or target.stem, wiki_root / "proposals")
        ctx = {"path": str(target), "manifest": manifest, "coverage_map": cmap,
               "wiki_root": wiki_root}
        r = _ss.score(fm, body, ctx)
        return {
            "shadow_tier": r.tier,
            "shadow_total": r.total,
            "shadow_dims": r.dims,
            "shadow_applicable": r.applicable,
            "shadow_floors_failed": r.floors_failed,
            "shadow_blocked": r.blocked,
            "shadow_notes": r.notes,
            "manifest_status": _rm.status(manifest),
            "scorer": "shadow_score.score@6dim-v0",
        }
    except Exception as exc:  # noqa: BLE001 — fail-closed : observabilité best-effort, jamais bloquante
        return {"shadow_error": str(exc)}


# --- La porte tiered (cœur ADR-083) -------------------------------------------
def _serialize_gate_outcome(name: str, result) -> dict:
    """Sérialise un GateResult (gates/_common) en dict structuré et STABLE.

    Contrat #2 (composition-promotion) : préserver l'evidence par-gate (violations
    = gate_id + message) jusqu'à la décision — 1 gate = 1 exécution = 1 résultat
    structuré conservé, jamais aplati en `gate:{n}={s}`. Tolérant aux gates factices
    status-only (`.violations` absent → dégradé à [], jamais de crash).
    """
    violations = getattr(result, "violations", None) or []
    return {
        "name": name,
        "status": result.status,
        "violations": [
            {"gate_id": getattr(v, "gate_id", ""), "message": getattr(v, "message", str(v))}
            for v in violations
        ],
    }


def _coverage_entries(wiki_root: Path, target: Path) -> list[dict]:
    """Entrées de la coverage-map de la fiche, clé = nom de fichier (comme check_fiche)."""
    path = Path(wiki_root) / "proposals" / "_coverage" / f"{Path(target).stem}.coverage.yaml"
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"coverage_map_malformed: {path.name}")
    return [e for e in (data.get("coverage_entries") or []) if isinstance(e, dict)]


# Suite d'échappements d'URL (`%C2%B7`, `%6d`, `%20`) : une chaîne publiée peut être affichée
# décodée, symbole ou lettre d'unité compris (`N%C2%B7m`, `N%6D`). Une suite qui suit un nombre
# (espaces compris) reste littérale : son `%` peut être un signe pour cent (`50%C3%A9`), que
# `numeric_exactitude` lit comme tel.
_PCT_ESCAPE_RUN = re.compile(r"(\d\s*)?((?:%[0-9A-Fa-f]{2})+)")
_JSON_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _percent_decoded(text: str, *, keep_ascii: bool = False) -> str:
    """`text`, suites d'échappements `%XX` décodées en UTF-8, sauf après un nombre ; un octet
    qui ne forme pas un caractère valide reste échappé (`%XX`). `keep_ascii` : un échappement
    de caractère ASCII, comme un octet invalide, reste tel qu'écrit (casse comprise), seuls les
    caractères non ASCII valides sont décodés — affichage de type IRI, plus strict que RFC 3987
    §3.2 : `%C3%A9` s'affiche `é` mais `%45` reste `%45`. Deux échappements gardés consécutifs
    sont séparés par `·` : les chiffres hexadécimaux de l'un ne forment pas, avec le `%` de
    l'autre, une valeur en pour cent que personne ne lit (`%20%28` → `%20·%28`, jamais `20%`)."""
    def decode(m):
        if m.group(1) is not None:
            return m.group(0)
        written = re.findall(r"%[0-9A-Fa-f]{2}", m.group(2))
        decoded = bytes.fromhex(m.group(2).replace("%", "")).decode("utf-8", "surrogateescape")
        out, at, kept = [], 0, False
        for ch in decoded:
            invalid = 0xDC80 <= ord(ch) <= 0xDCFF
            keep = invalid or (keep_ascii and ord(ch) < 0x80)
            if keep and kept:
                out.append("·")
            if keep_ascii and keep:
                out.append(written[at])
            else:
                out.append(f"%{ord(ch) - 0xDC00:02X}" if invalid else ch)
            kept = keep
            at += len(ch.encode("utf-8", "surrogateescape"))
        return "".join(out)
    return _PCT_ESCAPE_RUN.sub(decode, text)


# Propriété Unicode Bidi_Control (PropList.txt, Unicode 15.0) : marques, plongements, forçages et
# isolats bidirectionnels. Ils font afficher un texte dans un autre ordre que celui où il est écrit
# (`mN 52` forcé de droite à gauche s'affiche `25 Nm`) ; invisibles, `ccm._compat` les retire.
_BIDI_CONTROLS = frozenset({0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)})
# Monde fermé : ce qu'aucune lecture du contrôle (`visible_text_blocks`, `_string_readings`) ne
# rend, une construction qu'un rendu affiche autrement que tout texte lu. Chacune est une
# violation, quoi qu'elle affiche, au lieu d'un modèle de chaque moteur de rendu :
# - formule (`$`, rendue par GitHub : `$25^\circ C$` s'affiche `25°C`) ;
# - bloc de code que GitHub ou Obsidian rend autrement que son texte (`_RENDERED_FENCES` :
#   formule, diagramme, carte, modèle 3D, recherche et vue « Bases » d'Obsidian), par le premier
#   mot de son info ;
# - HTML brut, balise ou commentaire (`_RAW_HTML` : direction, style, texte masqué) ;
# - note (`_FOOTNOTE` : son renvoi affiche un numéro, sa définition s'affiche en fin de page),
#   note en ligne d'Obsidian (`^[…]`) comprise, fermée ou non ;
# - syntaxe d'Obsidian, lecteur que déclare le dépôt (README : « Markdown / Obsidian »), avec ses
#   modules de base, activés ou non, sans module tiers (`.obsidian/community-plugins.json` vide),
#   qui masque ou remplace son texte (`_OBSIDIAN`, `_OBSIDIAN_LINK`) : insertion `![[…]]` (contenu
#   d'une autre note ou d'un fichier, affiché à sa place), lien à libellé, à titre ou à bloc
#   (`[[note|25]]` n'affiche que `25`, `[[note#titre]]` affiche `note > titre`), lien écrit avec
#   l'extension de sa note (`[[25.md]]`, qu'Obsidian peut afficher sans elle), blancs ECMAScript
#   de fin compris (`_JS_TRIM`), commentaire `%%…%%` (masqué : `2%%x%%5 Nm` s'affiche `25 Nm`),
#   identifiant de bloc `^id` en fin de ligne (masqué : `à 2 ^b5` affiche `à 2`, lu avec la ligne
#   qui suit), relevé dans tout dernier mot de ligne dont un `^` précède un caractère, hors note
#   (`[^…]`, `^[…]`), suivi au plus de blancs ECMAScript (U+FEFF compris), encadré : citation dont
#   la première ligne que lit l'analyseur (lignes blanches sautées), blancs ECMAScript retirés,
#   commence par `[!`, quel que soit le bloc qu'il en tire (son marqueur, alerte de GitHub
#   comprise, s'affiche en icône et en titre : le type, s'il n'en a pas). Un lien simple,
#   `[[note]]`, affiche son texte sans ses crochets, que la lecture sans balisage lit ; un
#   surlignage `==…==`, la lecture squelette, qui retire ses signes ;
# - code emoji (`_EMOJI_SHORTCODE`, que GitHub affiche en image hors du code : `:two:` affiche le
#   chiffre 2 en touche), tout nom de cette forme sauf celle, qu'aucun code ne porte, des minutes
#   d'une heure et de son décalage horaire (`10:00:00`, `2026-10-14T10:00:00+02:00`) ;
# - ordre d'affichage : contrôle bidirectionnel (`_BIDI_CONTROLS`) ou caractère de classe
#   bidirectionnelle R, AL ou AN. Sans eux ni HTML, l'algorithme bidirectionnel Unicode (UAX #9)
#   affiche un paragraphe de gauche à droite dans l'ordre où il est écrit : direction du paragraphe
#   gauche à droite (P2-P3), chiffres européens lus de gauche à droite (W7), niveau 0 partout ;
# - caractère de contrôle (catégorie Cc), hors tabulation et fins de ligne : son affichage n'est
#   pas défini (retiré, remplacé, ou effaçant le caractère précédent) ;
# - caractère que la base Unicode de l'interpréteur ne définit pas (`_UNKNOWN_CATEGORIES` : non
#   attribué, usage privé, demi-codet isolé) : sa classe bidirectionnelle, sa valeur numérique et
#   son affichage lui sont inconnus — un caractère attribué après elle peut être un chiffre ou
#   une lettre de droite à gauche pour un lecteur plus récent ;
# - chiffre que la lecture ne lit pas tel qu'il s'affiche (`_misread_numeral`) : caractère de
#   valeur numérique Unicode que les chiffres décimaux de sa décomposition de compatibilité
#   n'écrivent pas (`❷`, `〇` : aucun chiffre ; `½`, décomposé `1⁄2`, lu `2`), barre de fraction
#   (`1⁄2` affiché en fraction) — `numeric_exactitude.py` ne lit que les chiffres décimaux ;
# - image (fichier du dépôt ou distante) : ce qu'elle affiche n'est pas du texte ;
# - imbrication au-delà de la profondeur de l'analyseur (`maxNesting`) : il ne lit pas le contenu
#   d'une citation ou d'un item de liste ouvert au dernier niveau (`_BLOCK_CONTAINERS`) — 20
#   citations, 10 niveaux de liste —, que GitHub affiche ;
# - numéro d'un item de liste ordonnée suivi d'une unité ou d'un chiffre : le numéro qu'affiche le
#   navigateur (`start` de la liste, puis compté de 1 en 1) n'est dans aucune lecture, et se lit
#   avec ce qui le suit (`25.` puis `Nm`, ou `24.` puis un second item `1. Nm`, affiché `25. Nm`),
#   case à cocher en tête de paragraphe comprise (`[x]`, tout caractère entre crochets, suivie
#   d'un blanc ou de la fin de ligne, affichée en case ; le rendu projeté n'en a pas) ; un premier
#   bloc qui n'affiche rien (code, titre ou cellule vides, ou faits de caractères invisibles ou de
#   glyphes blancs, lien sans libellé) n'a pas de ligne, et le numéro se lit avec le bloc suivant,
#   quel qu'il soit.
# Chaque propriété de caractère est celle de la base Unicode de l'interpréteur qui exécute le
# contrôle (`unicodedata.unidata_version`) : le monde fermé vaut pour elle.
_RENDERED_FENCES = frozenset({"math", "mermaid", "geojson", "topojson", "stl", "query", "base"})
_BLOCK_CONTAINERS = frozenset({"blockquote_open", "list_item_open"})
_ITEM_CONTENT = frozenset({"inline", "code_block", "fence", "html_block"})
_TASK_MARKER = re.compile(r"\A\[[^\]\n]\](?=[ \t\n])")
_RAW_HTML = re.compile(r"<[A-Za-z!?/][^\s<>]*")
# Note `[^…]` ou `^[…]`, fermée ou non, chacune lue jusqu'au premier `]` ou à la fin de ligne :
# un seul passage, linéaire
_FOOTNOTE = re.compile(r"\[\^[^\]\n]*+\]?|\^\[[^\]\n]*+\]?")
_OBSIDIAN = re.compile(r"!\[\[[^\]\n]*+(?:\]\])?|%%"
                       r"|(?<!\S)(?=\S*?(?<!\[)\^[^\s\[])\S*+"
                       r"(?=(?:[^\S\n\r\u2028\u2029]|\ufeff)*+(?:[\n\r\u2028\u2029]|\Z))")
# Lien `[[…]]`, chacun lu jusqu'au premier `]` ou à la fin de ligne : un seul passage, linéaire
_OBSIDIAN_LINK = re.compile(r"(?<!!)\[\[([^\]\n]*+)(\]\])?")
_EMOJI_SHORTCODE = re.compile(r":(?![0-9]{1,2}(?:[+-][0-9]{2})?:)[A-Za-z0-9_+-]+:")
_REORDERING_BIDI_CLASSES = frozenset({"R", "AL", "AN"})
_UNKNOWN_CATEGORIES = frozenset({"Cn", "Co", "Cs"})


def _misread_numeral(ch: str) -> bool:
    """`ch` affiche une valeur que `numeric_exactitude` ne lit pas telle quelle : valeur numérique
    Unicode que les chiffres décimaux de sa décomposition de compatibilité n'écrivent pas, ou
    barre de fraction, seule ou dans cette décomposition."""
    value = unicodedata.numeric(ch, None)
    if value is None:
        return ch == "\N{FRACTION SLASH}"
    compat = unicodedata.normalize("NFKC", ch)
    digits = "".join(str(unicodedata.decimal(c)) for c in compat if unicodedata.category(c) == "Nd")
    return "\N{FRACTION SLASH}" in compat or not digits or int(digits) != value


def _decodings(text: str) -> list[str]:
    """`text` tel qu'écrit, entités HTML décodées, échappements d'URL tous décodés, et les deux
    dans chaque ordre, dédoublonnés."""
    unescaped, unquoted = html.unescape(text), urllib.parse.unquote(text)
    return list(dict.fromkeys((text, unescaped, unquoted, urllib.parse.unquote(unescaped),
                               html.unescape(unquoted))))


def _unmodelled_constructs(text: str, ccm, *, body: bool, leading) -> list[tuple[str, str]]:
    """(genre, marque) de chaque construction de `text` qu'aucune lecture ne modélise, dans
    chacun de ses décodages (`_decodings`), dédoublonnés. Chaîne publiée, qu'un lecteur peut
    servir sous toute forme : tout `$`, tout début de balise (`<` suivi d'une lettre, `!`, `?` ou
    `/`, autolien compris) et tout code emoji, et, chaque décodage lu en Markdown, tout bloc rendu,
    toute image, et tout item numéroté de la projection (`_projection_ordered_items`, numéroté
    par son rang). `body` :
    `text` est le corps, chacun de ses décodages lu par CommonMark — `$`, début de balise et code
    emoji relevés dans son texte (entités décodées), et dans son code s'il n'est pas le corps tel
    qu'écrit (un décodage peut fabriquer le délimiteur qui le rendrait inerte), balise ou
    commentaire HTML là où l'analyseur les produit, bloc rendu par son info, image (sa
    destination ; son texte alternatif lu comme le texte). Dans chaque lecture CommonMark, du corps
    comme d'une chaîne : imbrication au-delà de la profondeur de l'analyseur, et item de liste
    ordonnée dont le contenu commence par ce que `leading` en rapporte (unité ou chiffre en tête),
    marqué du numéro affiché. Note, syntaxe d'Obsidian, ordre d'affichage, caractère de contrôle,
    caractère inconnu et chiffre non lu : partout, dans chaque décodage."""
    found: list[tuple[str, str]] = []
    decodings = _decodings(text)
    md = ccm.MarkdownIt("commonmark").enable("table")
    deepest = md.options["maxNesting"] - 1

    def callout(state, start, end, silent):
        # Encadré : première ligne que l'analyseur lit dans une citation (lignes blanches sautées),
        # blancs ECMAScript retirés, qui commence par `[!`, quel que soit le bloc qu'il en tire
        # (paragraphe, titre, tableau, définition de lien) ; règle qui ne consomme rien
        if state.tokens and state.tokens[-1].type == "blockquote_open":
            first = state.src[state.bMarks[start] + state.tShift[start]:state.eMarks[start]]
            if (line := _JS_TRIM.sub("", first)).startswith("[!"):
                found.append(("callout", line[:40]))
        return False

    md.block.ruler.before("table", "callout", callout)

    def mark(source):
        m = _RAW_HTML.search(source)
        return m.group(0) if m else source.strip()[:40]

    def fences(tokens):
        return [("rendered_fence", info) for t in tokens if t.type == "fence"
                and (info := (t.info.split() or [""])[0].lower()) in _RENDERED_FENCES]

    def image(token):
        return "image", str(token.attrGet("src") or "")[:40]

    def images(tokens):
        return [found for t in tokens for found in
                ([image(t)] if t.type == "image" else []) + images(t.children or [])]

    def numbered(rank, source, task=True):
        # Une case à cocher en tête de paragraphe (`[x]`) s'affiche en case : le numéro se lit
        # avec ce qui suit ; un bloc de code n'en a pas, ni le rendu projeté
        if source is None:
            return
        for text in dict.fromkeys((source, _TASK_MARKER.sub("", source)) if task else (source,)):
            if (head := leading(text)) is not None:
                found.append(("ordered_list_number", f"{rank}. {head}"))
                return

    def item_content(tokens, at):
        # Premier contenu de l'item ouvert en `at`, avant sa fermeture : ce qu'affiche son numéro
        for t in tokens[at + 1:]:
            if t.type == "list_item_close" and t.level == tokens[at].level:
                return None
            if t.type in _ITEM_CONTENT:
                return t
        return None

    def shown(source):
        # Caractère affiché : ni blanc, ni invisible, ni glyphe blanc (`ccm._compat`)
        return bool(ccm._compat(source).strip())

    def shows_text(token):
        # Un bloc qui n'affiche aucun caractère (code, titre ou cellule vides, ou faits de
        # caractères invisibles ou de glyphes blancs, lien sans libellé) n'a pas de ligne : le
        # navigateur aligne le numéro de l'item sur le bloc suivant
        if token.type != "inline":
            return shown(token.content)
        return any(c.type in ("image", "html_inline")
                   or (c.type in ("text", "code_inline") and shown(c.content))
                   for c in token.children or [])

    def structure(tokens):
        # Conteneur ouvert au dernier niveau : l'analyseur n'en lit pas le contenu
        found.extend(("nesting", t.type) for t in tokens
                     if t.type in _BLOCK_CONTAINERS and t.level >= deepest)
        found.extend(fences(tokens))
        for at, t in enumerate(tokens):
            if t.type != "ordered_list_open":
                continue
            rank = 1 if (start := t.attrGet("start")) is None else int(start)
            for k in range(at + 1, len(tokens)):
                if tokens[k].type == "ordered_list_close" and tokens[k].level == t.level:
                    break
                if tokens[k].type == "list_item_open" and tokens[k].level == t.level + 1:
                    if (first := item_content(tokens, k)) is not None and not shows_text(first):
                        found.append(("ordered_list_number", f"{rank}. (bloc vide)"))
                    else:
                        numbered(rank, first.content if first is not None else None,
                                 task=first is None or first.type == "inline")
                    rank += 1

    def written(source):
        if "$" in source:
            found.append(("formula", "$"))
        found.extend(("raw_html", m.group(0)) for m in _RAW_HTML.finditer(source))
        found.extend(("emoji_shortcode", m.group(0)) for m in _EMOJI_SHORTCODE.finditer(source))

    def inline(children, inert_code):
        # Texte et caractère échappé ou en entité qui se suivent, relus joints, comme `text_join`
        # les joint dans un paragraphe : il ne descend pas dans le texte alternatif d'une image
        runs = itertools.groupby(children, key=lambda c: c.type in ("text", "text_special"))
        for is_text, run in runs:
            if is_text:
                written("".join(c.content for c in run))
                continue
            for c in run:
                if c.type == "code_inline" and not inert_code:
                    written(c.content)
                elif c.type == "html_inline":
                    found.append(("raw_html", mark(c.content)))
                elif c.type == "image":
                    found.append(image(c))
                    inline(c.children or [], inert_code)

    for decoded in decodings:
        if body:
            inert_code = decoded == text
            tokens = md.parse(decoded)
            for t in tokens:
                if t.type == "inline":
                    inline(t.children or [], inert_code)
                elif t.type == "html_block":
                    found.append(("raw_html", mark(t.content)))
                elif t.type in ("code_block", "fence") and not inert_code:
                    written(t.content)
            structure(tokens)
        else:
            written(decoded)
            tokens = md.parse(decoded)
            structure(tokens)
            found += images(tokens)
            for rank, source in _projection_ordered_items(decoded):
                numbered(rank, source, task=False)
    def rewritten_link(m):
        # Lien fermé qu'Obsidian n'affiche pas tel qu'écrit, crochets retirés
        target = m.group(1)
        return m.group(2) is not None and (any(c in "|#^" for c in target)
                                           or _JS_TRIM.sub("", target).lower().endswith(".md"))

    for decoded in decodings:
        found += [("footnote", m.group(0)) for m in _FOOTNOTE.finditer(decoded)]
        marks = [(m.start(), m.group(0)) for m in _OBSIDIAN.finditer(decoded)]
        marks += [(m.start(), m.group(0)) for m in _OBSIDIAN_LINK.finditer(decoded)
                  if rewritten_link(m)]
        found += [("obsidian", mark[:40]) for _, mark in sorted(marks)]
        for ch in decoded:
            category = unicodedata.category(ch)
            if ord(ch) in _BIDI_CONTROLS or unicodedata.bidirectional(ch) in _REORDERING_BIDI_CLASSES:
                found.append(("display_order", f"U+{ord(ch):04X}"))
            elif category == "Cc" and ch not in "\t\n\r":
                found.append(("control_character", f"U+{ord(ch):04X}"))
            elif category in _UNKNOWN_CATEGORIES:
                found.append(("unknown_character", f"U+{ord(ch):04X}"))
            elif _misread_numeral(ch):
                found.append(("numeral", f"U+{ord(ch):04X}"))
    return list(dict.fromkeys(found))


# Squelette : ce que lit un lecteur qui retire d'un texte tout sauf lettres, chiffres, espaces,
# ponctuation de nombre et de clause (`.,;:`), symboles d'unité (`°%²·`) et signe `×` entre deux
# nombres — après `&amp;` décodé, toute suite de la forme d'une entité (`&quot;`, `&nbsp_;`, `&x;`).
# Modèle commun des lecteurs qui effacent le balisage sans séparateur : `stripHtml` du monorepo,
# appliqué au rendu des blocs projetés (`&quot;` du `"` échappé, entités, balises retirés : `25"Nm`
# s'y affiche `25Nm`). Le `×` d'une cote ou d'un filetage (`340×30`, `M8×1,25`) n'est pas du
# balisage : `numeric_exactitude` y lit la référence précise et le contexte d'une valeur.
_AMP_ENTITY = re.compile(r"&amp;", re.I)
_ENTITY_LIKE = re.compile(r"&#?\w+;")
_SKELETON_KEPT = frozenset(".,;:°%²·")
# `×` qui n'est pas entre deux nombres (une espace au plus de chaque côté, espaces déjà réduits)
_SKELETON_LONE_TIMES = re.compile(r"×(?! ?\d)|(?<!\d)(?<!\d )×")


def _skeleton(text: str, ccm) -> str:
    """`text` lu en squelette (`_ENTITY_LIKE` retiré après `&amp;` décodé, compatibilité Unicode,
    puis tout caractère hors lettres, chiffres, espaces et `_SKELETON_KEPT` retiré, et tout `×`
    qui n'est pas entre deux nombres), espaces réduits."""
    while (decoded := _AMP_ENTITY.sub("&", text)) != text:
        text = decoded
    text = ccm._compat(_ENTITY_LIKE.sub("", text))
    kept = " ".join("".join(ch for ch in text if ch.isalnum() or ch.isspace()
                            or ch in _SKELETON_KEPT or ch == "×").split())
    return " ".join(_SKELETON_LONE_TIMES.sub("", kept).split())


# `renderProjectionMarkdown` (monorepo, `backend/src/modules/seo-projection/
# projection-markdown.renderer.ts`, au commit d3b0060e6d), qui rend les blocs projetés (`content_md`)
# des pages R3 : ses expressions, telles quelles (ses deux titres en une, `###?`, qui affiche le
# même texte), aux classes JavaScript près, écrites en clair —
# `\s` et `trim` (blancs et fins de ligne ECMAScript, U+FEFF compris, U+0085 et U+001C-U+001F
# exclus), `.` (tout sauf une fin de ligne : U+2028 et U+2029 en sont), `\d` (chiffres ASCII).
_JS_SPACE = "[\t\n\x0b\x0c\r \xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]"
_JS_DOT = "[^\n\r\u2028\u2029]"
# `trim` d'ECMAScript : ses blancs retirés en tête et en fin
_JS_TRIM = re.compile(rf"\A{_JS_SPACE}+|{_JS_SPACE}+\Z")
_PROJECTION_CODE = re.compile(r"`([^`]*)`")
_PROJECTION_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
_PROJECTION_STRONG = re.compile(rf"\*\*(?!{_JS_SPACE})([^*]+)(?<!{_JS_SPACE})\*\*")
_PROJECTION_EM = re.compile(rf"\*(?!{_JS_SPACE})([^*]+)(?<!{_JS_SPACE})\*")
_PROJECTION_HEADING = re.compile(rf"###?{_JS_SPACE}+({_JS_DOT}+?){_JS_SPACE}*\Z")
_PROJECTION_ITEMS = (re.compile(rf"[-*]{_JS_SPACE}+({_JS_DOT}*)\Z"),
                     re.compile(rf"[0-9]+\.{_JS_SPACE}+({_JS_DOT}*)\Z"))
_PROJECTION_BLANK = re.compile(rf"{_JS_SPACE}*\Z")


def _projection_inline(text: str) -> str:
    """Texte qu'affiche `renderInline` : de gauche à droite, à chaque position, code (son
    contenu), lien (son libellé rendu ; la destination n'est qu'un `href`, jamais affichée),
    `**…**` puis `*…*` (leur contenu rendu) ; tout autre caractère affiché tel qu'écrit — le HTML
    compris, que le rendu échappe."""
    out, at = [], 0
    while at < len(text):
        if m := _PROJECTION_CODE.match(text, at):
            out.append(m.group(1))
        elif m := (_PROJECTION_LINK.match(text, at) or _PROJECTION_STRONG.match(text, at)
                   or _PROJECTION_EM.match(text, at)):
            out.append(_projection_inline(m.group(1)))
        else:
            out.append(text[at])
            at += 1
            continue
        at = m.end()
    return "".join(out)


def _projection_parse(md: str):
    """(rang, source) de chaque bloc (`<h3>`, `<h4>`, `<li>`, `<p>`) que `renderProjectionMarkdown`
    rend pour `md`, source avant sa grammaire inline : lignes coupées à `\\r\\n`, `\\r` et `\\n`
    seulement, ligne blanche sautée, titre `### ` puis `## `, items consécutifs d'une liste, et
    paragraphe — lignes consécutives jusqu'à une ligne blanche ou un début de bloc, jointes par une
    espace. Rang : celui d'un item de liste numérotée dans sa suite d'items, à partir de 1 — le
    numéro qu'affiche le navigateur, la liste rendue sans `start` ; None pour tout autre bloc."""
    lines = re.sub(r"\r\n?", "\n", md).split("\n")
    starts = (_PROJECTION_HEADING, *_PROJECTION_ITEMS)
    at = 0
    while at < len(lines):
        if _PROJECTION_BLANK.match(lines[at]):
            at += 1
        elif m := _PROJECTION_HEADING.match(lines[at]):
            yield None, m.group(1)
            at += 1
        elif item := next((r for r in _PROJECTION_ITEMS if r.match(lines[at])), None):
            rank = 1
            while at < len(lines) and (m := item.match(lines[at])):
                yield (rank if item is _PROJECTION_ITEMS[1] else None), m.group(1)
                rank += 1
                at += 1
        else:
            start = at
            while (at < len(lines) and not _PROJECTION_BLANK.match(lines[at])
                   and not any(r.match(lines[at]) for r in starts)):
                at += 1
            yield None, " ".join(lines[start:at])


def _projection_blocks(md: str) -> list[str]:
    """Texte de chaque bloc que `renderProjectionMarkdown` affiche pour `md` (`_projection_parse`)."""
    return [_projection_inline(source) for _rank, source in _projection_parse(md)]


def _projection_ordered_items(md: str) -> list[tuple[int, str]]:
    """(numéro affiché, source) de chaque item de liste numérotée que `renderProjectionMarkdown`
    rend pour `md` (`_projection_parse`)."""
    return [(rank, source) for rank, source in _projection_parse(md) if rank is not None]


def _string_readings(text: str, ccm) -> list[tuple[str, str]]:
    """Lectures d'une chaîne publiée, dédoublonnées. Telle qu'écrite (`littérale`) ; chaque forme
    de `check-coverage-map.visible_text_blocks` lue comme un corps Markdown (`rendue` : emphase,
    entités et balises résolues ; `écrite` : HTML, titres et destinations de lien ; `sans
    balisage` : balisage ignoré, lien réduit à son libellé quelle que soit sa destination) ;
    telle que l'affiche le rendu des blocs projetés, `renderProjectionMarkdown` (`projection`,
    `_projection_blocks` : HTML affiché tel qu'écrit, et sa grammaire inline appliquée jusque dans
    ce HTML), ses blocs séparés, puis joints sans séparateur comme les joint `stripHtml` sur ce
    rendu (`projection jointe` : `25` / `1. Nm` y affiche `25Nm`) ; balisage ET structure de
    blocs ignorés (`sans structure` : `markup_blind_text` de la chaîne entière), lignes jointes
    comme les joint un lecteur qui la sert en texte, HTML retiré, là où CommonMark sépare code
    indenté, bloc HTML et paragraphe. Chaque lecture part de la chaîne affichée en IRI
    (`_percent_decoded(keep_ascii=True)` : `%C3%A9` lu `é`, `%45` lu tel qu'écrit), puis,
    suffixée `décodée`, de la chaîne aux échappements tous décodés ; les échappements qu'une
    lecture révèle (entité décodée : `N&#37;6D` lu `N%6D`) y sont lus de même, comme dans le
    corps."""
    forms: list[tuple[str, str]] = []
    for suffix, keep_ascii in (("", True), (" décodée", False)):
        base = _percent_decoded(text, keep_ascii=keep_ascii)
        blocks = ccm.visible_text_blocks(base)
        readings = [("littérale", " ".join(unicodedata.normalize("NFC", base).split()))]
        readings += [(form, " ; ".join(b["text"] for b in blocks if b["form"] == form))
                     for form in ("rendue", "écrite", "sans balisage")]
        projected = _projection_blocks(base)
        readings.append(("projection", ccm._compat(" ; ".join(projected))))
        readings.append(("projection jointe", ccm._compat("".join(projected))))
        readings.append(("sans structure", ccm.markup_blind_text(base)))
        for form, reading in readings:
            if (revealed := _percent_decoded(reading, keep_ascii=keep_ascii)) != reading:
                reading = ccm._compat(revealed)
            if reading and reading not in {r for _, r in forms}:
                forms.append((form + suffix, reading))
    return forms


def _scalar_text(value):
    """Texte publié d'une clé ou valeur scalaire : la chaîne elle-même, sinon son texte (date YAML,
    octets décodés) ; None pour un nombre, un booléen ou un nul, qui ne portent pas d'unité."""
    if value is None or isinstance(value, (bool, int, float)):
        return None
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", "replace")
    return value if isinstance(value, str) else str(value)


def _encodable(text: str) -> str:
    """`text`, chaque demi-codet isolé écrit en échappement (`\\udcff`) : la sortie UTF-8 de
    `promote.py`, en json comme en texte, ne peut pas l'encoder tel quel. En json, l'échappement
    est celui du demi-codet, que `json.loads` relit tel quel, sauf un demi-codet haut suivi d'un
    demi-codet bas : JSON ne les distingue pas du caractère que la paire code, relu à leur place
    (deux clés qui ne diffèrent que par là se confondent à la relecture)."""
    return text.encode("utf-8", "backslashreplace").decode("utf-8")


def _published_strings(node, path: str = "$"):
    """(chemin, chaîne) pour chaque chaîne d'un document publié (frontmatter de la fiche,
    document exporté), valeurs ET clés, quel que soit le champ : ni liste de champs, ni typage
    par schéma. Clé ou valeur scalaire autre qu'une chaîne : lue par son texte (`_scalar_text` :
    date, octets) ; un nombre, un booléen ou un nul ne sont pas lus (aucune unité), sauf en clé,
    où le chemin les nomme."""
    if isinstance(node, dict):
        for key, value in node.items():
            key_text = _scalar_text(key)
            name = key_text if key_text is not None else str(key)
            child = (f"{path}.{name}" if _JSON_IDENTIFIER.fullmatch(name)
                     else f"{path}[{_encodable(json.dumps(name, ensure_ascii=False))}]")
            if key_text is not None:
                yield f"{child} (clé)", key_text
            yield from _published_strings(value, child)
    elif isinstance(node, (list, tuple, set, frozenset)):
        items = sorted(node, key=repr) if isinstance(node, (set, frozenset)) else node
        for i, value in enumerate(items):
            yield from _published_strings(value, f"{path}[{i}]")
    elif _scalar_text(node) is not None:
        yield path, _scalar_text(node)


@contextlib.contextmanager
def _promoted_fiche(fm: dict, body: str, target: Path, wiki_root: Path, evaluation=None,
                    relation_verdicts=None):
    """La fiche telle qu'`apply_promotion` l'écrirait (`_promoted_frontmatter`, `_render_fiche`),
    à son chemin canonique sous une racine temporaire : les exporteurs la lisent comme un
    fichier du canon. `evaluation` : l'évaluation que la décision portera (`gate_status`,
    `confidence_score`, `shadow_score`), écrite telle quelle dans `promotion_evidence` ; None
    (appel direct, hors `evaluate_tier`) : valeurs neutres. `relation_verdicts` : relecture des
    relations (ADR-116 D3) projetée, avec la révision réelle du décideur, celle qu'écrira
    l'application. SHA du commit et horodatages, connus à l'application seulement, restent
    neutres et de la forme qu'elle écrit : le repli de `_wiki_commit_sha` et un ISO-8601."""
    root = Path(wiki_root)
    promoted = _promoted_frontmatter(
        fm, evaluation if evaluation is not None else {"gate_status": "pass", "confidence_score": 0.0},
        target_rel=str(Path(target).resolve().relative_to(root.resolve())),
        sha=_COMMIT_SHA_FALLBACK, now="1970-01-01T00:00:00+00:00",
        relation_verdicts=relation_verdicts,
        decider_revision=(None if relation_verdicts is None
                          else _engine_revision(("promotion_decision.py",))))
    with tempfile.TemporaryDirectory(prefix="safety-projection-") as tmp:
        tmp_root = Path(tmp).resolve()
        path = _promotion_target_path(tmp_root, promoted)
        path.parent.mkdir(parents=True)
        path.write_text(_render_fiche(promoted, body), encoding="utf-8")
        yield tmp_root, path


def _seo_projection(path: Path, tmp_root: Path):
    """Document que `build_exports_seo.build_export` publie pour la fiche (None : non publiée),
    et les avertissements que l'exporteur écrit sur stderr, rapportés et non imprimés."""
    seo = _load_module("_seo_export_projection", "build_exports_seo.py")
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        doc = seo.build_export(path, tmp_root, seo._COMMIT_SHA_PLACEHOLDER, seo._GENERATED_AT_PLACEHOLDER)
    return doc, [line for line in stderr.getvalue().splitlines() if line.strip()]


def _diagnostic_projection(path: Path, tmp_root: Path, wiki_root: Path):
    """Document que `build_exports_diagnostic` publie pour la fiche (None : non publiée), par
    les étapes de son `_plan` pour un fichier : fiches de `wiki/gamme/` seulement, éligibilité
    de l'exporteur, catalogue de sources de l'arbre évalué. Catalogue absent :
    `SafetyInputUnavailable` ; catalogue ou relation invalides : l'exporteur lève."""
    if path.parent != (tmp_root / "wiki" / "gamme").resolve():
        return None  # `_plan` ne lit que wiki/gamme/*.md
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    diag = _load_module("_diagnostic_export_projection", "build_exports_diagnostic.py")
    fm, _body = diag._parse_markdown(path, source_bytes=diag._read_source(path))
    if not diag.is_eligible(fm):
        return None
    catalog_path = Path(wiki_root) / diag.CATALOG_REL
    if not catalog_path.is_file():
        raise SafetyInputUnavailable(f"{diag.CATALOG_REL} absent de l'arbre évalué")
    catalog = diag._load_catalog(Path(wiki_root), source_bytes=diag._read_source(catalog_path))
    return diag.build_gamme_export(fm, path, tmp_root, catalog, "0" * 40, "0" * 40)


def _safety_numeric_exactitude(fm: dict, body: str, target: Path, wiki_root: Path,
                               evaluation=None, relation_verdicts=None) -> dict:
    """Chaque valeur chiffrée du texte PUBLIÉ doit être `numeric_verified`.

    Corps : chaque bloc de `visible_text_blocks`, dans chacune de ses formes (rendue, écrite,
    sans balisage). Un extrait ancré (`text_anchor` de la coverage-map, localisé dans le premier
    bloc ancrable de sa section qui le contient) porte le statut et l'identité de sa source ; il
    est lu, puis retiré, dans ce bloc et dans chaque bloc qui en dérive (`origin`), là où il se
    lit dans la forme du bloc (`form_text`). Un extrait dont la borne coupe une valeur (nombre
    coupé, ou séparé de son unité ou de sa marque d'approximation : le bloc et l'extrait lus à
    part par `numeric_exactitude`, tels qu'écrits, à la compatibilité près ou en squelette, ne
    portent plus les mêmes valeurs), ou absent d'un bloc dérivé, n'y est pas retiré : sa valeur reste non sourcée, et il est rapporté
    (`anchors_unmasked`). Tout le reste est non sourcé (`pending_capture`), échappements d'URL
    lus comme dans une chaîne du frontmatter : affichés en IRI (`_percent_decoded(keep_ascii=
    True)`), puis, si la lecture en diffère, tous décodés, classés à part (`corps (<forme>
    décodée)`) ; chaque forme est classée avec ses propres extraits ancrés, et chaque violation
    est préfixée `corps (<forme>)`.

    Fiche et exports : la fiche telle qu'`apply_promotion` l'écrirait (`_promoted_fiche`, avec
    l'évaluation que portera la décision) est publiée elle-même — un lecteur du canon peut en
    servir n'importe quel champ — et passe par les exporteurs eux-mêmes (`_seo_projection`,
    `_diagnostic_projection`), qui peuvent y ajouter du texte venu d'ailleurs (l'export
    diagnostic : le catalogue de sources). Chaque chaîne de son frontmatter tel qu'analysé et de
    chaque document exporté tel que sérialisé, valeurs ET clés, quel que soit le champ, est lue
    telle qu'écrite, telle que rendue, telle que projetée (blocs séparés, puis joints) et sans
    structure de blocs (`_string_readings`), sans ancre (`pending_capture`) : ni liste de champs,
    ni connaissance des lecteurs ; un champ ajouté à la fiche ou à un export entre dans le
    contrôle sans autre modification.

    Squelette : chaque lecture du corps et de chaque chaîne est lue aussi en squelette
    (`_skeleton` : entités et tout caractère hors lettres, chiffres, espaces, ponctuation de
    nombre et de clause, symboles d'unité et signe `×` entre deux nombres retirés), comme la lit
    un lecteur qui efface le balisage sans séparateur (`25"Nm`, `25&Amp;quot;Nm`, `25 &x; Nm`,
    `25 ␣ Nm` s'y lisent `25Nm` ou `25 Nm`, `25"°C` s'y lit `25°C`) ; sa violation est
    rapportée, suffixée `squelette`, si aucune lecture ordinaire du même texte ne la porte déjà,
    espaces non comptés. Chaque extrait ancré est lu aussi en squelette, sous le statut et
    l'identité de sa source (`corps (<forme> squelette)`) : une marque, une touche ou un
    guillemet entre un nombre et son unité, ou entre deux de ses chiffres, n'y cache pas la
    valeur affichée. Le squelette retire aussi un tiret ou une barre oblique entre deux
    chiffres : un extrait ancré qui en écrit un y est classé sur les chiffres joints (`10-20 Nm`
    lu `1020 Nm`, hors plage), ce qui est son coût.

    Monde fermé : ce qu'aucune de ces lectures ne modélise (`_unmodelled_constructs` : formule,
    bloc rendu autrement que son texte, HTML brut, note, code emoji, ordre d'affichage,
    caractère de contrôle, caractère que la base Unicode de l'interpréteur ne définit pas,
    chiffre que la lecture ne lit pas tel qu'il s'affiche, fraction comprise, image, imbrication
    au-delà de la profondeur de l'analyseur, numéro d'un item de liste ordonnée suivi d'une
    unité ou d'un chiffre, ou d'un premier bloc qui n'affiche rien — `25.` puis `Nm`, ou `2.`
    puis `5 Nm`, affiché `2. 5 Nm`), dans le corps ou dans une chaîne publiée, tel qu'écrit, en
    entité HTML ou échappé en URL, est une violation (`unmodelled_<genre>`), quoi qu'il affiche
    (`$25^\\circ C$` s'affiche `25°C`, `mN 52` forcé de droite à gauche s'affiche `25 Nm`) : le
    contrôle ne modélise pas chaque moteur de rendu, il refuse ce qu'il ne lit pas. Sans ordre
    d'affichage modifié ni HTML, chaque texte s'affiche dans l'ordre où il est écrit. Une chaîne
    publiée dont une lecture, ou son squelette, commence par une unité, symbole ou en lettres,
    est une violation aussi (`unmodelled_leading_unit`) : les surfaces R3 joignent sans
    séparateur les champs d'une même section, et un nombre qui finit le champ précédent s'y
    lirait avec elle, y compris par un début d'entité que la chaîne achève (`25&nbsp` puis
    `;mm`) ; un mot qui commence par une unité (`barre`, `Inchangé`) en est le coût, comme tout
    item de liste ordonnée qui commence par un chiffre, par un tel mot (`1. Inchangé`, lu
    `1. Inch`) ou par un bloc vide.

    Résidus (non détectés ; liste complète et coûts : `_meta/quality-gates.md`) : un nombre sans
    unité adjacente — écrit seul dans un champ (nombre YAML ou JSON, ou chaîne) dont l'unité est
    dans sa clé ou dans un champ voisin qui ne commence pas par elle, ou, en fin de champ, suivi
    d'une partie de son unité dont le champ voisin porte le reste (`25 N` puis `m`), ou dans le
    corps séparé de son unité par du texte ou de la structure (unité avant le nombre, unité en
    en-tête de colonne, en amorce de liste ou après deux-points), ou nu dans une clause dont la
    grandeur n'a pas de plage pour la famille de la fiche ; une unité ou un chiffre écrit en
    lettres qui leur ressemblent (`Νm`, nu grec ; `2Ƽ Nm`, lettre latine ton cinq), ou un
    chiffre décimal d'une autre écriture, lu à sa valeur quel que soit le chiffre latin auquel
    il ressemble ; un caractère que le squelette garde entre un nombre et son unité —
    ponctuation de nombre ou de clause (`20.Nm`, `20; Nm`, `⒛ Nm`), point médian ou signe degré
    qui n'écrit pas une unité (`20·Nm`, `20°Nm`) ; une valeur en pictogramme ou en mots ; une
    unité prolongée par un caractère (`25 mm2`, comptée `25 mm`) ; un nombre dont les groupes de
    chiffres sont séparés par un séparateur de milliers, une barre oblique ou tout caractère
    visible que le squelette garde ou change en espace (lettre, `·`, `×`, `˙` : `1 200 Nm` lu
    `200 Nm`, `1/2 Nm` lu `2 Nm`, `1ʼ200 Nm`, `1·200 Nm` et `1˙200 Nm` lus `200 Nm`), extrait
    ancré compris ; une valeur dont les chiffres sont ceux d'une suite d'échappements d'un
    caractère non ASCII (`%E2%80%89 bar`), lue décodée, mais affichée telle qu'écrite hors d'un
    lien.
    Un extrait ancré est classé sur son propre texte : le contexte de sa phrase hors de
    l'ancre n'entre pas dans sa clause. Les valeurs que seule l'application
    connaît (SHA, horodatages) sont lues sur des valeurs neutres (`_promoted_fiche`), le
    catalogue de sources tel qu'il est à la décision.

    Classification déléguée à `numeric_exactitude` : aucune règle numérique n'est redéfinie
    ici. Entrée gouvernée absente : plages chiffrées (`_meta/numeric-plausibility.yaml`) → la
    condition entière est UNAVAILABLE (`SafetyInputUnavailable`), car sans elles un nombre nu
    dans une clause à grandeur dimensionnée n'est plus reconnu et aucun verdict n'est sûr ;
    catalogue de sources d'une fiche gamme à relations → `status: UNAVAILABLE` sauf violation
    prouvée ailleurs. Jamais vérifié.

    Par relation (ADR-116 D2, `numeric_verified`) : chaque chaîne publiée lue dans
    `diagnostic_relations[i]` de la fiche, ou dans la relation de l'export diagnostic dont
    `relation_index` vaut i, est rapportée à la relation i avec ses violations (`relations`) :
    le même contrôle, aucun second détecteur. L'export SEO ne publie pas les relations.
    `relation_verdicts` : la relecture projetée (`_promoted_fiche`), qui fait lire le texte
    qu'elle écrirait."""
    ranges_path = Path(wiki_root) / NUMERIC_RANGES_RELPATH
    if not ranges_path.is_file():
        raise SafetyInputUnavailable(f"{NUMERIC_RANGES_RELPATH.as_posix()} absent de l'arbre évalué")
    sys.path.insert(0, str(SCRIPTS_DIR))
    import author_from_raw as _author
    import numeric_exactitude as _ne
    ccm = _load_module("_coverage_visible_text", "check-coverage-map.py")
    blocks = [dict(b) for b in ccm.visible_text_blocks(body)]

    def masked(text, m):
        # `;` borne la clause : le texte voisin ne s'attache pas à la valeur retirée
        return text[:m.start()] + " ; " + text[m.end():]

    def numbers(text):
        # Ce que `numeric_exactitude` lit d'un texte : nombres, et valeurs avec unité et marque
        # d'approximation
        return (sorted(_ne._BARE_NUM_RE.findall(text)),
                sorted((v.value, v.unit, v.approximate) for v in _ne.extract_values(text)))

    def splits_a_value(text, m):
        # L'extrait et le reste lus à part ne portent pas les nombres et valeurs du texte entier,
        # tel qu'écrit, à la compatibilité près ou en squelette : la borne coupe un nombre ou le
        # sépare de son unité ou de sa marque d'approximation
        for read in (lambda t: t, ccm._compat, lambda t: _skeleton(t, ccm)):
            whole, part, rest = (numbers(read(t)) for t in (text, m.group(0), masked(text, m)))
            if whole != tuple(sorted(a + b) for a, b in zip(part, rest)):
                return True
        return False

    claims: dict[str, list[dict]] = {"rendue": [], "écrite": [], "sans balisage": []}
    anchored = 0
    anchors_unmasked: list[dict] = []
    for entry in _coverage_entries(wiki_root, target):
        anchor = entry.get("text_anchor")
        if not isinstance(anchor, str) or not anchor.strip():
            continue
        source = {"source_status": entry.get("source_status"), "source_id": entry.get("source_slug")}
        needle = re.compile(re.escape(" ".join(unicodedata.normalize("NFC", anchor).split())),
                            re.IGNORECASE)
        for k, block in enumerate(blocks):
            if not block["anchorable"] or entry.get("section") not in block["sections"]:
                continue
            m = needle.search(block["text"])
            if not m:
                continue
            if splits_a_value(block["text"], m):
                anchors_unmasked.append({"anchor": anchor, "form": block["form"], "reason": "value_split"})
                break
            anchored += 1
            claims[block["form"]].append({"text": m.group(0), **source})
            block["text"] = masked(block["text"], m)
            for derived in blocks:
                if derived["origin"] != k:
                    continue
                dm = re.compile(re.escape(ccm.form_text(anchor, derived["form"])),
                                re.IGNORECASE).search(derived["text"])
                if dm is None or splits_a_value(derived["text"], dm):
                    anchors_unmasked.append({"anchor": anchor, "form": derived["form"],
                                             "reason": "absent" if dm is None else "value_split"})
                    continue
                claims[derived["form"]].append({"text": dm.group(0), **source})
                derived["text"] = masked(derived["text"], dm)
            break

    def residual(text, keep_ascii):
        # Échappements d'URL lus comme dans une chaîne du frontmatter (`_string_readings`)
        decoded = _percent_decoded(text, keep_ascii=keep_ascii)
        return text if decoded == text else ccm._compat(decoded)

    def reading(form):
        # Le reste de chaque bloc affiché en IRI, puis, s'il en diffère, aux échappements décodés
        shown = [(residual(b["text"], True), residual(b["text"], False))
                 for b in blocks if b["form"] == form and b["text"].strip()]
        return " ; ".join(s for s, _ in shown), " ; ".join(d for s, d in shown if d != s)

    family = _author._family_of(str(fm.get("slug") or Path(target).stem), fm) or ""
    ranges = load_numeric_ranges(ranges_path)

    def unsourced(text):
        claim = {"text": text, "source_status": "pending_capture", "source_id": None}
        return _ne.gate_numeric_value_exactitude([claim], family=family, ranges=ranges)

    def skeleton_violations(readings, plain, label):
        # Chaque lecture en squelette, dédoublonnée ; violation rapportée si aucune lecture
        # ordinaire ne porte déjà la même, espaces non comptés (`25 Nm` lu `25Nm`)
        known = {"".join(v.split()) for v in plain}
        skeletons: dict[str, str] = {}
        for form, text in readings:
            skeletons.setdefault(_skeleton(text, ccm), form)
        return [f"{label} ({form} squelette) {v}" for text, form in skeletons.items() if text
                for v in unsourced(text) if "".join(v.split()) not in known]

    def values_read(text):
        # (position, unité) de chaque valeur que `numeric_exactitude` lit dans `text` : unité
        # symbole, ou unité écrite en lettres accolée au nombre (règle (a))
        return sorted([(v.start, v.unit) for v in _ne.extract_values(text)]
                      + [(m.start(), re.sub(r"^[\d.,\s]+", "", m.group(0)))
                         for m in _ne._SPELLED_UNIT_RE.finditer(text)])

    def leading_unit(readings):
        # Unité, symbole ou en lettres, en tête d'une lecture ou de son squelette : un nombre qui
        # finit le texte affiché juste avant (champ voisin d'une section R3, que `stripHtml` joint
        # sans séparateur) s'y lirait avec elle (`… sous 3` puis `mm d'épaisseur …` : `3mm`). Le
        # squelette est lu après un nombre, puis après un nombre suivi de `&` ou de `&amp` : le
        # champ précédent peut finir par un début d'entité que celui-ci achève (`25&nbsp` puis
        # `;mm`, `25&` puis `x;Nm`), retirée par le squelette du texte joint.
        for _form, text in readings:
            pairs = [("1" + text, text)] + [(_skeleton(end + text, ccm), _skeleton(text, ccm))
                                            for end in ("1", "1&", "1&amp")]
            for joined, alone in pairs:
                units = [unit for _, unit in values_read(alone)]
                for _, unit in values_read(joined):
                    if unit not in units:
                        return unit
                    units.remove(unit)
        return None

    def leading_value(text):
        # Unité, ou chiffre, en tête d'une lecture de `text` ou de son squelette (espaces réduits,
        # aucun en tête) : affiché juste après le numéro d'un item de liste ordonnée, il se lit avec
        # lui (`25.` puis `Nm`)
        readings = _string_readings(text, ccm)
        if (unit := leading_unit(readings)) is not None:
            return unit
        for _form, reading_text in readings:
            for head in (reading_text, _skeleton(reading_text, ccm)):
                if m := re.match(r"(\d+)", head):
                    return m.group(1)
        return None

    violations: list[str] = []
    plain: set[str] = set()
    body_readings: list[tuple[str, str]] = []
    anchored_claims = {form: list(form_claims) for form, form_claims in claims.items()}
    for form, form_claims in claims.items():
        shown, decoded = reading(form)
        if shown:
            form_claims.append({"text": shown, "source_status": "pending_capture", "source_id": None})
            body_readings.append((form, shown))
        found = _ne.gate_numeric_value_exactitude(form_claims, family=family, ranges=ranges)
        violations += [f"corps ({form}) {v}" for v in found]
        plain.update(found)
        if decoded:
            found = unsourced(decoded)
            violations += [f"corps ({form} décodée) {v}" for v in found]
            plain.update(found)
            body_readings.append((f"{form} décodée", decoded))
    violations += skeleton_violations(body_readings, plain, "corps")
    # Extraits ancrés lus en squelette, chacun avec le statut et l'identité de sa source : une
    # marque ou un caractère retiré entre un nombre et son unité y laisse lire la valeur affichée
    known = {"".join(v.split()) for v in plain}
    for form, form_claims in anchored_claims.items():
        skeletons = [{**claim, "text": _skeleton(claim["text"], ccm)} for claim in form_claims]
        for v in _ne.gate_numeric_value_exactitude(skeletons, family=family, ranges=ranges):
            if "".join(v.split()) not in known:
                known.add("".join(v.split()))
                violations.append(f"corps ({form} squelette) {v}")
    violations += [f"corps unmodelled_{kind}: {marker!r}"
                   for kind, marker in _unmodelled_constructs(body, ccm, body=True,
                                                              leading=leading_value)]
    strings_read = {"fiche": 0, "seo": 0, "diagnostic": 0}
    unavailable: list[str] = []
    relation_strings: dict[int, dict] = {}
    with _promoted_fiche(fm, body, target, wiki_root, evaluation,
                         relation_verdicts) as (tmp_root, path):
        # Frontmatter tel qu'un lecteur YAML du canon l'analyse : clés et valeurs non-texte
        # (dates, nombres) lues par `_published_strings`, aucune clé fusionnée par une conversion.
        fiche_doc = _parse_markdown(path)[0]
        seo_doc, projection_warnings = _seo_projection(path, tmp_root)
        try:
            diag_doc = _diagnostic_projection(path, tmp_root, wiki_root)
        except SafetyInputUnavailable as exc:
            diag_doc = None
            unavailable.append(str(exc))
    for origin, doc in (("fiche", fiche_doc),
                        # Aller-retour JSON : les chaînes de l'export tel qu'écrit ; non sérialisable = en échec.
                        ("seo", None if seo_doc is None else json.loads(json.dumps(seo_doc, ensure_ascii=False))),
                        ("diagnostic", None if diag_doc is None else json.loads(json.dumps(diag_doc, ensure_ascii=False)))):
        if doc is None:
            continue
        for where, text in _published_strings(doc):
            strings_read[origin] += 1
            readings = _string_readings(text, ccm)
            plain = set()
            found_here: list[str] = []
            for form, reading_text in readings:
                found = unsourced(reading_text)
                found_here += [f"{origin} {where} ({form}) {v}" for v in found]
                plain.update(found)
            found_here += skeleton_violations(readings, plain, f"{origin} {where}")
            if (unit := leading_unit(readings)) is not None:
                found_here.append(f"{origin} {where} unmodelled_leading_unit: {unit!r}")
            found_here += [f"{origin} {where} unmodelled_{kind}: {marker!r}"
                           for kind, marker in _unmodelled_constructs(text, ccm, body=False,
                                                                      leading=leading_value)]
            violations += found_here
            if (index := _published_relation_index(origin, where, doc)) is not None:
                read = relation_strings.setdefault(index, {"strings_read": 0, "violations": []})
                read["strings_read"] += 1
                read["violations"] += found_here
    result = {"verified": not violations and not unavailable, "violations_total": len(violations),
              "sample": violations[:8], "anchored_claims": anchored,
              "anchors_unmasked": anchors_unmasked, "strings_read": strings_read,
              "published": {"seo": seo_doc is not None, "diagnostic": diag_doc is not None},
              "projection_warnings": projection_warnings, "unavailable": unavailable,
              "family": family or None, "ranges_loaded": bool(ranges),
              # Liste et non mapping : la décision fait l'aller-retour JSON, qui change une clé
              # entière en texte.
              "relations": [{"index": index, "strings_read": read["strings_read"],
                             "violations_total": len(read["violations"]),
                             "sample": read["violations"][:8]}
                            for index, read in sorted(relation_strings.items())]}
    if unavailable and not violations:
        result.update(status="UNAVAILABLE", missing_input="; ".join(unavailable))
    return result


_FICHE_RELATION_PATH = re.compile(r"^\$\.diagnostic_relations\[(\d+)\](?=[.\[ ]|$)")
_EXPORT_RELATION_PATH = re.compile(r"^\$\.relations\[(\d+)\](?=[.\[ ]|$)")


def _published_relation_index(origin: str, where: str, doc) -> int | None:
    """Index dans `diagnostic_relations[]` de la relation qui publie la chaîne lue à `where`
    (`_published_strings`), None hors d'une relation : dans la fiche, par son chemin ; dans
    l'export diagnostic, par le `relation_index` de la relation exportée (`_export_relation`) ;
    absent ou non entier : ValueError, jamais une chaîne rattachée à aucune relation."""
    if origin == "fiche" and (m := _FICHE_RELATION_PATH.match(where)):
        return int(m.group(1))
    if origin == "diagnostic" and (m := _EXPORT_RELATION_PATH.match(where)):
        index = doc["relations"][int(m.group(1))].get("relation_index")
        if not isinstance(index, int) or isinstance(index, bool):
            raise ValueError(f"relation_index_malformed: {where}")
        return index
    return None


def _sourced_entries(fm: dict):
    """(label, entrée) des listes sourcées ADR-112/113 portant un objet `evidence`."""
    diagnostic = fm.get("diagnostic")
    if diagnostic is not None and not isinstance(diagnostic, dict):
        raise ValueError("diagnostic_malformed: `diagnostic` doit être un mapping")
    for label, items in (("diagnostic_relations", fm.get("diagnostic_relations")),
                         ("diagnostic.quick_checks", (diagnostic or {}).get("quick_checks")),
                         ("safety_rules", fm.get("safety_rules"))):
        if items is None:
            continue
        if not isinstance(items, list):
            raise ValueError(f"{label}_malformed: liste attendue")
        for i, item in enumerate(items):
            if isinstance(item, dict):
                yield f"{label}[{i}]", item


def _claimed_review_authority(fm: dict) -> dict:
    """Entrées où la proposition déclare elle-même une relecture (`reviewed`), l'autorité
    diagnostic (`diagnostic_safe`) ou le cachet de la règle de relecture (`reviewed_by` /
    `reviewed_at`). ADR-033 D4 : ces bascules sont humaines ou couvertes par une règle d'ADR
    explicite, jamais portées par une proposition ; ADR-116 D3 : le cachet n'est écrit que par
    `apply_promotion`, une proposition qui le porte s'attribue la règle. Toute valeur autre que
    false/absente compte ; pour le cachet, la seule présence de la clé, quelle que soit sa
    valeur. Lève ValueError sur une liste mal formée (`_sourced_entries`)."""
    reviewed: list[str] = []
    live: list[str] = []
    stamped: list[str] = []
    for label, item in _sourced_entries(fm):
        evidence = item.get("evidence")
        if not isinstance(evidence, dict):
            continue
        if evidence.get("reviewed") not in (None, False):
            reviewed.append(label)
        if evidence.get("diagnostic_safe") not in (None, False):
            live.append(label)
        if "reviewed_by" in evidence or "reviewed_at" in evidence:
            stamped.append(label)
    not_applicable = fm.get("diagnostic_not_applicable")
    if isinstance(not_applicable, dict) and not_applicable.get("reviewed") not in (None, False):
        reviewed.append("diagnostic_not_applicable")
    return {"reviewed_true": reviewed, "diagnostic_safe_true": live,
            "review_stamp_present": stamped}


def _review_authority_claimed(claims: dict) -> bool:
    """Vrai si une déclaration est trouvée ou si le contrôle n'a pas pu conclure (fail-closed)."""
    return bool(claims.get("error") or claims.get("reviewed_true")
                or claims.get("diagnostic_safe_true") or claims.get("review_stamp_present"))


def _publisher_key(publisher, invisible) -> str:
    """Clé d'égalité de deux éditeurs : correspondance sans casse de compatibilité d'Unicode
    (NFKD(casefold(NFKD(casefold(NFD(x)))))), caractères invisibles retirés (`invisible`, le
    prédicat de `check-coverage-map` : format, sélecteur de variation, remplisseur hangûl…),
    espaces réduits. Forme NFC/NFD, ß/SS, pleine chasse, espaces insécables ou sans chasse et
    caractères invisibles ne font pas deux éditeurs. Vide — aucun éditeur identifiable — quand
    l'éditeur n'est pas un texte, ne contient aucun caractère alphanumérique visible, ou contient
    un caractère que la base Unicode de l'interpréteur ne définit pas (`_UNKNOWN_CATEGORIES` : non
    attribué, usage privé, demi-codet isolé), dont ni l'affichage ni l'égalité ne sont connus."""
    if not isinstance(publisher, str) or any(
            unicodedata.category(ch) in _UNKNOWN_CATEGORIES for ch in publisher):
        return ""
    folded = unicodedata.normalize("NFKD", unicodedata.normalize(
        "NFKD", unicodedata.normalize("NFD", publisher).casefold()).casefold())
    key = " ".join("".join(ch for ch in folded if not invisible(ch)).split())
    return key if any(ch.isalnum() for ch in key) else ""


def _safety_proof_publishers(fm: dict, target: Path, wiki_root: Path) -> tuple[bool, dict]:
    """Au moins `SAFETY_PROOF_PUBLISHERS_MIN` éditeurs distincts parmi les sources citées par la
    fiche dont le type a le rôle `proof` (`source_type_editorial_role` du catalogue de l'arbre
    évalué).

    Citées = mêmes slugs que ceux dont l'évaluateur de provenance vérifie l'archive RAW (entrées
    de la coverage-map, `citations[]`) ; une source ne compte qu'`active`. Leur capture RAW est
    prouvée par `provenance_pass`, composée ensuite, et n'est pas recalculée ici. Éditeur absent,
    rôle autre que `proof` : la source ne compte pas, et la raison est rapportée. Éditeurs
    distincts = clés distinctes (`_publisher_key`) ; l'éditeur est le texte libre du catalogue."""
    ccm = _load_module("_coverage_proof_sources", "check-coverage-map.py")
    qg = _load_module("_quality_gates_proof_sources", "quality-gates.py")
    roles = _editorial_roles(wiki_root)
    catalog = ccm._load_catalog(Path(wiki_root))
    cited = ccm.referenced_source_slugs(Path(target), Path(wiki_root)) | qg.cited_source_slugs(fm)
    return _proof_publishers_min(cited, catalog, roles, ccm.invisible)


def _editorial_roles(wiki_root: Path) -> dict:
    """`source_type_editorial_role` du catalogue de l'arbre évalué. Catalogue absent :
    `SafetyInputUnavailable` ; mapping absent ou vide : ValueError."""
    catalog_path = Path(wiki_root) / SOURCE_CATALOG_RELPATH
    if not catalog_path.is_file():
        raise SafetyInputUnavailable(f"{SOURCE_CATALOG_RELPATH.as_posix()} absent de l'arbre évalué")
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    roles = data.get("source_type_editorial_role") if isinstance(data, dict) else None
    if not isinstance(roles, dict) or not roles:
        raise ValueError("source_type_editorial_role_malformed: mapping non vide attendu")
    return roles


def _proof_publishers_min(slugs, catalog: dict, roles: dict, invisible) -> tuple[bool, dict]:
    """Au moins `SAFETY_PROOF_PUBLISHERS_MIN` éditeurs distincts de rôle `proof` parmi `slugs` :
    le calcul d'ADR-114 D3, partagé par la Safety Auto-Gate (sources citées par la fiche) et par
    la relecture des relations d'ADR-116 D2 (sources des citations ancrées de la relation). Une
    source ne compte qu'`active`, de rôle `proof`, avec un éditeur identifiable ; sinon sa raison
    est rapportée. Éditeurs distincts = clés distinctes (`_publisher_key`)."""
    publishers: dict[str, list[str]] = {}
    not_counted: dict[str, str] = {}
    for slug in sorted(slugs):
        entry = catalog.get(slug)
        if entry is None:
            not_counted[slug] = "absent_du_catalogue"
            continue
        if entry.get("status") != "active":
            not_counted[slug] = f"status={entry.get('status')}"
            continue
        role = roles.get(entry.get("type"))
        if role != "proof":
            not_counted[slug] = f"type={entry.get('type')} role={role}"
            continue
        key = _publisher_key(entry.get("publisher"), invisible)
        if not key:
            not_counted[slug] = "publisher_absent"
            continue
        publishers.setdefault(key, []).append(slug)
    return len(publishers) >= SAFETY_PROOF_PUBLISHERS_MIN, {
        "distinct_publishers": len(publishers), "min": SAFETY_PROOF_PUBLISHERS_MIN,
        "publishers": publishers, "not_counted": not_counted}


def _safety_local_conditions(fm: dict, body: str, target: Path, wiki_root: Path,
                             shadow, gate_results, score) -> dict:
    """Conditions de la Safety Auto-Gate calculables sur la fiche elle-même. Couverture,
    régression et provenance sont composées ensuite par `decide_promotion` (mêmes résultats
    que pour toute fiche, jamais réévalués ici). `shadow`, `gate_results`, `score` : ceux de
    l'évaluation en cours, que la fiche promue portera. Fail-closed : une condition dont le
    calcul lève est FAUSSE et son erreur est rapportée."""
    conditions: dict[str, bool] = {}
    details: dict[str, Any] = {}

    def record(name, compute):
        try:
            ok, detail = compute()
        except SafetyInputUnavailable as exc:  # entrée absente de l'arbre évalué : infra, pas contenu
            ok, detail = False, {"status": "UNAVAILABLE", "missing_input": str(exc)}
        except Exception as exc:  # noqa: BLE001 — fail-closed, erreur rapportée
            ok, detail = False, {"error": f"{type(exc).__name__}: {exc}"}
        conditions[name] = ok is True
        details[name] = detail

    dims = (shadow or {}).get("shadow_dims") or {}

    def dim_floor(dim, floor):
        value = dims.get(dim)
        number = isinstance(value, (int, float)) and not isinstance(value, bool)
        return (number and value >= floor), {"value": value, "floor": floor,
                                             "shadow_error": (shadow or {}).get("shadow_error")}

    for dim, floor in SAFETY_DIM_FLOORS.items():
        record(f"dim_{dim}_floor", lambda dim=dim, floor=floor: dim_floor(dim, floor))

    def quality_gates():
        names = tuple(n for n, _ in gate_results)
        failing = [n for n, r in gate_results if r.status != "pass"]
        return (names == CANONICAL_GATE_NAMES and not failing), {"gates": list(names), "failing": failing}

    record("no_quality_gate_fail", quality_gates)
    record("proof_sources_min", lambda: _safety_proof_publishers(fm, target, wiki_root))

    def numeric():
        # L'évaluation telle que la décision la portera (`_evaluation_passthrough`) et
        # qu'`apply_promotion` l'écrira au canon (`_promoted_frontmatter`).
        evaluation = {"gate_status": {n: r.status for n, r in gate_results},
                      "confidence_score": round(score, 4), "shadow_score": shadow}
        result = _safety_numeric_exactitude(fm, body, target, wiki_root, evaluation)
        return result["verified"], result

    record("numeric_exactitude_verified", numeric)
    # Déclaration explicite exigée ; la détection de contradiction dans la prose est un résidu V2.
    record("no_disputed_claims",
           lambda: (fm.get("no_disputed_claims") is True, {"value": fm.get("no_disputed_claims")}))

    def live_authority():
        claimed = _claimed_review_authority(fm)["diagnostic_safe_true"]
        return not claimed, {"diagnostic_safe_true": claimed}

    # `diagnostic_safe: true` = flip humain ciblé (quality-gates.md §diagnostic_safe), jamais auto.
    record("diagnostic_live_authority_not_claimed", live_authority)

    def manual_review():
        flagged = [label for label, item in _sourced_entries(fm)
                   if isinstance(item.get("evidence"), dict)
                   and item["evidence"].get("source_policy") == "manual_review"]
        flagged += [f"coverage_entries[{e.get('claim_id')}]" for e in _coverage_entries(wiki_root, target)
                    if e.get("source_policy") == "manual_review"]
        return not flagged, {"manual_review": flagged}

    # `manual_review` = « fiche bloquée jusqu'à revue humaine » (schéma) : jamais levé par code.
    record("no_manual_review_policy", manual_review)
    return {"conditions": conditions, "details": details}


def _relation_review_local(fm: dict, body: str, target: Path, wiki_root: Path, raw_root,
                           is_safety: bool, shadow, gate_results, score, review_claims) -> dict:
    """Conditions d'ADR-116 D2 calculables sur la fiche, pour chaque `diagnostic_relations[i]`.
    `fiche_eligible` est composée ensuite par `decide_promotion` (`_relation_review_trace`) sur
    le statut de la fiche, jamais réévalué ici. Trace seulement : aucun motif bloquant.

    Fiche sécurité : ses relations n'entrent pas (D1), `not_safety` seule est rapportée, rien
    d'autre n'est calculé. Sinon, chaque condition réutilise le contrôle existant qui la définit
    (`quality-gates`, calcul d'éditeurs d'ADR-114 D3, vérification chiffrée d'ADR-114 D4 sur le
    texte publié), lié aux racines de la décision. Fail-closed : une condition dont le calcul
    lève est FAUSSE et son erreur rapportée ; une entrée gouvernée absente la rend FAUSSE et
    `UNAVAILABLE`. `shadow`, `gate_results`, `score` : ceux de l'évaluation en cours, que la
    fiche promue portera ; `review_claims` : `_claimed_review_authority` de la même évaluation."""
    relations = fm.get("diagnostic_relations")
    if relations is None:
        return {"relations": []}
    if not isinstance(relations, list):
        return {"error": "diagnostic_relations_malformed: liste attendue"}
    if is_safety:
        return {"relations": [{"index": i, "conditions": {"not_safety": False},
                               "details": {"not_safety": {"is_safety": True}}}
                              for i in range(len(relations))]}
    shared: dict[str, tuple] = {}

    def once(key, compute):
        # Entrée commune aux relations de la fiche : calculée une fois, son erreur comprise
        if key not in shared:
            try:
                shared[key] = (True, compute())
            except Exception as exc:  # noqa: BLE001 — relevée par chaque condition qui la lit
                shared[key] = (False, exc)
        ok, value = shared[key]
        if not ok:
            raise value
        return value

    def catalog():
        if not (Path(wiki_root) / SOURCE_CATALOG_RELPATH).is_file():
            raise SafetyInputUnavailable(f"{SOURCE_CATALOG_RELPATH.as_posix()} absent de l'arbre évalué")
        return _load_module("_coverage_relation_review", "check-coverage-map.py")._load_catalog(Path(wiki_root))

    def exporter():
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        return _load_module("_diagnostic_export_relation_review", "build_exports_diagnostic.py")

    def numeric():
        # L'évaluation que la décision portera, et la relecture projetée pour chaque relation :
        # la fiche lue porte le texte le plus long que l'application puisse écrire.
        evaluation = {"gate_status": {n: r.status for n, r in gate_results},
                      "confidence_score": round(score, 4), "shadow_score": shadow}
        projected = {i: True for i, item in enumerate(relations) if isinstance(item, dict)}
        return _safety_numeric_exactitude(fm, body, target, wiki_root, evaluation,
                                          relation_verdicts=projected)

    qg = _bound_quality_gates("_quality_gates_relation_review", wiki_root, raw_root)
    ccm_invisible = _load_module("_coverage_relation_invisible", "check-coverage-map.py").invisible
    out = []
    for i, item in enumerate(relations):
        label = f"diagnostic_relations[{i}]"
        conditions: dict[str, bool] = {"not_safety": True}
        details: dict[str, Any] = {"not_safety": {"is_safety": False}}

        def record(name, compute):
            try:
                ok, detail = compute()
            except SafetyInputUnavailable as exc:  # entrée absente de l'arbre évalué : infra
                ok, detail = False, {"status": "UNAVAILABLE", "missing_input": str(exc)}
            except Exception as exc:  # noqa: BLE001 — fail-closed, erreur rapportée
                ok, detail = False, {"error": f"{type(exc).__name__}: {exc}"}
            conditions[name] = ok is True
            details[name] = detail

        if not isinstance(item, dict):
            for name in RELATION_REVIEW_CONDITIONS[2:]:
                conditions[name] = False
                details[name] = {"error": f"{label}_malformed: mapping attendu"}
            out.append({"index": i, "conditions": conditions, "details": details})
            continue

        def sources_raw_proven(item=item):
            # Définition des exports : la source exportée (`_export_source`) porte `raw_proven`
            sources = item.get("sources")
            if not isinstance(sources, list) or not sources:
                return False, {"sources": 0}
            diag, entries = exporter(), once("catalog", catalog)
            not_proven: list[dict] = []
            for slug in sources:
                try:
                    if not diag._export_source(slug, entries)["raw_proven"]:
                        not_proven.append({"source": slug, "reason": "raw_ref_absent_ou_non_actif"})
                except Exception as exc:  # noqa: BLE001 — slug inconnu : source non prouvée
                    not_proven.append({"source": slug, "reason": str(getattr(exc, "message", exc))})
            return not not_proven, {"sources": len(sources), "not_raw_proven": not_proven}

        anchored_sources: list[str] = []

        def citations_anchored(item=item, label=label):
            citations = item.get("citations")
            if not isinstance(citations, list) or not citations:
                return False, {"citations": 0}
            entries = once("catalog", catalog)
            if raw_root is None or not qg.RAW_INVENTORY.is_file():
                raise SafetyInputUnavailable(f"inventaire RAW absent ({qg.RAW_INVENTORY}) : ancres non vérifiables")
            # Index réel dans le libellé : relation précédée de positions vides, ignorées par
            # `_sourced_entries` de quality-gates, qui énumère la liste
            issues = (qg._citation_issues(label, item, entries)
                      + qg.gate_citation_anchors({"diagnostic_relations": [None] * i + [item]}, entries))
            for citation in citations:
                alone = {"sources": item.get("sources"), "citations": [citation]}
                if (isinstance(citation, dict) and not qg._citation_issues(label, alone, entries)
                        and not qg.gate_citation_anchors({"diagnostic_relations": [alone]}, entries)):
                    anchored_sources.append(citation["source"])
            return not issues, {"citations": len(citations), "anchored": len(anchored_sources),
                                "issues": issues}

        def proof_publishers_min():
            entries = once("catalog", catalog)
            roles = once("roles", lambda: _editorial_roles(wiki_root))
            return _proof_publishers_min(set(anchored_sources), entries, roles, ccm_invisible)

        def source_policy_resolved(item=item, label=label):
            evidence = item.get("evidence")
            policy = evidence.get("source_policy") if isinstance(evidence, dict) else None
            issues = qg._evidence_and_sources_issues(label, item, once("catalog", catalog))
            # Durcissement : une politique absente ou invalide (`schema_invalid`) n'est pas résolue
            blocking = [x for x in issues if x.startswith(("source_policy_violated:", "schema_invalid:"))]
            return (isinstance(policy, str) and policy != "manual_review" and not blocking), {
                "source_policy": policy, "issues": issues}

        def numeric_verified(i=i):
            result = once("numeric", numeric)
            read = next((r for r in result.get("relations") or [] if r.get("index") == i), None)
            unavailable = result.get("unavailable") or []
            detail = {"strings_read": (read or {}).get("strings_read", 0),
                      "violations_total": (read or {}).get("violations_total", 0),
                      "sample": (read or {}).get("sample", []), "unavailable": unavailable}
            if unavailable and not detail["violations_total"]:
                detail.update(status="UNAVAILABLE", missing_input="; ".join(unavailable))
            return (read is not None and read["strings_read"] > 0
                    and read["violations_total"] == 0 and not unavailable), detail

        def no_review_claimed():
            return (review_claims is not None and not _review_authority_claimed(review_claims)), {
                "review_claims": review_claims if review_claims is not None else {"evaluated": False}}

        record("sources_raw_proven", sources_raw_proven)
        record("citations_anchored", citations_anchored)
        record("proof_publishers_min", proof_publishers_min)
        record("source_policy_resolved", source_policy_resolved)
        record("numeric_verified", numeric_verified)
        record("no_review_claimed", no_review_claimed)
        out.append({"index": i, "conditions": conditions, "details": details})
    return {"relations": out}


def _build_checks(is_safety, numeric_block, gate_results, truth_level,
                  score, threshold, gate_engine, shadow, kinds,
                  safety_local=None, review_claims=None) -> list[dict]:
    """Reconstruit les CHECKS structurés à partir des valeurs DÉJÀ calculées par
    evaluate_tier (aucune ré-exécution). Chaque check = {code, status, owner_stage,
    evidence} — le substrat machine-readable que `decide_promotion` consomme sans
    parser de prose (C0). `owner_stage` = domaine responsable du défaut.
    """
    checks: list[dict] = [
        # Identifiant historique conservé (quality-gates.md §7). `decide_promotion` le compose
        # avec couverture/régression/provenance et la politique (`_reasons_from_safety`).
        {"code": "SAFETY_HUMAN_REVIEW", "status": "fail" if is_safety else "pass",
         "owner_stage": "POLICY_SAFETY",
         "evidence": {"is_safety": bool(is_safety), **(safety_local or {})}},
        {"code": "NUMERIC_HIGH_HARM", "status": "fail" if numeric_block else "pass",
         "owner_stage": "POLICY_NUMERIC", "evidence": {"block": list(numeric_block[:5])}},
        # Absent ⇒ non évalué ⇒ fail (jamais un succès par défaut).
        {"code": "REVIEW_AUTHORITY_CLAIMED",
         "status": "pass" if review_claims is not None
         and not _review_authority_claimed(review_claims) else "fail",
         "owner_stage": "POLICY_REVIEW",
         "evidence": review_claims if review_claims is not None else {"evaluated": False}},
    ]
    for name, r in gate_results:
        checks.append({
            "code": f"GATE_{name.upper()}",
            "status": "pass" if r.status == "pass" else "fail",
            "owner_stage": "QUALITY",
            "evidence": _serialize_gate_outcome(name, r),
        })
    checks.append({
        "code": "TRUTH_LEVEL",
        "status": "pass" if truth_level in AUTO_PROMOTE_TRUTH_LEVELS else "fail",
        "owner_stage": "SUBSTANCE", "evidence": {"truth_level": truth_level},
    })
    if gate_engine == "adr088_6dim":
        st = (shadow or {}).get("shadow_tier")
        checks.append({
            "code": "SUBSTANCE_TIER",
            "status": "pass" if st in ADR088_PROMOTE_TIERS else "fail",
            "owner_stage": "SUBSTANCE",
            "evidence": {"shadow_tier": st, "engine": "adr088_6dim"},
        })
    else:
        checks.append({
            "code": "SUBSTANCE_SCORE",
            "status": "pass" if score >= threshold else "fail",
            "owner_stage": "SUBSTANCE",
            "evidence": {"score": round(score, 4), "threshold": threshold, "engine": "legacy"},
        })
    checks.append({
        "code": "SOURCE_DIVERSITY",
        "status": "pass" if len(kinds) >= MIN_DISTINCT_SOURCE_KINDS else "fail",
        "owner_stage": "SOURCE", "evidence": {"distinct_kinds": len(kinds)},
    })
    return checks


def evaluate_tier(fm: dict, body: str, target: Path, wiki_root: Path,
                  threshold: float, gates, compute_score, *, raw_root=None) -> dict:
    """
    Décision déterministe TIER A (auto) vs TIER B (humain). Fail-closed :
    toute exception est capturée par l'appelant → TIER B.

    `raw_root` : racine RAW de la décision, pour les ancres des citations des relations
    (ADR-116 D2) ; None : ancres non vérifiables, `citations_anchored` UNAVAILABLE.
    """
    reasons: list[str] = []

    # INVARIANT SÉCURITÉ (fail-closed, prioritaire) : famille sécurité-critique →
    # JAMAIS auto-promue, quels que soient la substance et le moteur de gate. Force
    # TIER B (revue humaine ≠ auteur). Miroir de auto_review_wiki_proposal (monorepo).
    # Raison prose insérée en tête plus bas, une fois ses conditions locales calculées.
    is_safety = _is_safety_proposal(fm)

    # INVARIANT ANTI-NUMBER-SWAPPING : valeurs HIGH-HARM (couple/pression) non
    # auto-vérifiables → revue humaine. Cotes/températures = observabilité (ne bloquent pas).
    numeric_flags = _numeric_review_flags(body)
    if numeric_flags["block"]:
        reasons.append(
            "numeric: valeurs critiques couple/pression non auto-vérifiables → "
            f"validation bloquée (anti number-swapping): {numeric_flags['block'][:5]}"
        )

    gate_results = [(name, fn(target)) for name, fn in gates]
    failing = [(n, r.status) for n, r in gate_results if r.status != "pass"]
    if failing:
        reasons += [f"gate:{n}={s}" for n, s in failing]

    truth_level = fm.get("truth_level")
    if truth_level not in AUTO_PROMOTE_TRUTH_LEVELS:
        reasons.append(f"truth_level={truth_level} (auto exige L1/L2)")

    score_details = None
    try:
        # Same canonical link scope as compute-confidence-score.py --check.
        # Native scorer returns evidence from ONE computation; injected legacy
        # scalar callables remain supported without manufacturing explanations.
        computed = compute_score(fm, body, wiki_root / "wiki")
        if isinstance(computed, dict):
            score = float(computed["score"])
            score_details = computed
        else:
            score = float(computed)
    except Exception as exc:  # fail-closed
        reasons.append(f"confidence_score indéterminable: {exc}")
        score = 0.0

    # Le tier 6-dim est calculé dans les 2 modes : observabilité (toujours) + décisionnel (si flag on).
    shadow = _compute_shadow(fm, body, target, wiki_root)
    gate_engine = os.environ.get(PROMOTE_GATE_ENGINE_ENV, "legacy").strip().lower()
    if gate_engine == "adr088_6dim":
        # SUBSTANCE GATE = tier 6-dim (planchers entity-aware). Fail-closed : tier absent/erreur → blocage.
        st = (shadow or {}).get("shadow_tier")
        if st not in ADR088_PROMOTE_TIERS:
            why = st or (shadow or {}).get("shadow_error", "indéterminable")
            reasons.append(f"shadow_tier={why} (cutover ADR-088 : auto-promo exige A/S)")
    else:
        # SUBSTANCE GATE legacy (défaut) = confidence_score scalaire >= seuil.
        if score < threshold:
            reasons.append(f"confidence_score={score:.2f} < seuil={threshold:.2f}")

    kinds = {
        s.get("kind")
        for s in (fm.get("source_refs") or [])
        if isinstance(s, dict) and s.get("kind")
    }
    if len(kinds) < MIN_DISTINCT_SOURCE_KINDS:
        reasons.append(f"source_refs kinds distincts={len(kinds)} (<{MIN_DISTINCT_SOURCE_KINDS})")

    # Relecture / autorité diagnostic déclarées par la proposition : toutes familles (ADR-033 D4,
    # ADR-112 D12). Correction attendue = remettre à false ; la bascule ne passe pas par ici.
    try:
        review_claims = _claimed_review_authority(fm)
    except Exception as exc:  # noqa: BLE001 — fail-closed, erreur rapportée
        review_claims = {"error": f"{type(exc).__name__}: {exc}"}
    if _review_authority_claimed(review_claims):
        reasons.append("review: relecture ou autorité diagnostic déclarée par la proposition "
                       f"(bascule humaine ou règle d'ADR explicite, ADR-033 D4) : {review_claims}")

    safety_local = None
    if is_safety:
        safety_local = _safety_local_conditions(fm, body, target, wiki_root, shadow, gate_results, score)
        failed = [k for k, ok in safety_local["conditions"].items() if not ok]
        if failed or not SAFETY_AUTO_APPROVAL_ADR:
            why = (f"conditions non prouvées : {', '.join(failed)}" if failed else
                   "conditions locales prouvées, auto-validation sécurité non ratifiée au vault")
            reasons.insert(0, "safety: famille sécurité-critique → Safety Auto-Gate "
                              f"({why}) ; décision composée par SAFETY_HUMAN_REVIEW")

    # Relecture des relations hors sécurité (ADR-116) : trace, jamais une raison de blocage.
    try:
        relation_review = _relation_review_local(fm, body, target, wiki_root, raw_root, is_safety,
                                                 shadow, gate_results, score, review_claims)
    except Exception as exc:  # noqa: BLE001 — fail-closed : relations non évaluées
        relation_review = {"error": f"{type(exc).__name__}: {exc}"}

    tier = "A" if not reasons else "B"
    return {
        "tier": tier,
        "confidence_score": round(score, 4),
        "score_details": score_details,
        "gate_engine": gate_engine,
        "gate_status": {n: r.status for n, r in gate_results},
        "gate_outcomes": [_serialize_gate_outcome(n, r) for n, r in gate_results],
        "checks": _build_checks(is_safety, numeric_flags["block"], gate_results,
                                truth_level, score, threshold, gate_engine, shadow, kinds,
                                safety_local, review_claims),
        "blocking_reasons": reasons,
        "shadow_score": shadow,
        "numeric_flags": numeric_flags,
        "relation_review": relation_review,
    }


def _promotion_target_path(wiki_root: Path, fm: dict) -> Path:
    entity_type = fm.get("entity_type")
    slug = fm.get("slug")
    if entity_type not in WIKI_ENTITY_DIRS or not slug:
        raise PromotionInputError(f"entity_type/slug invalides: {entity_type}/{slug}")
    out = (wiki_root / "wiki" / entity_type / f"{slug}.md").resolve()
    canon_root = (wiki_root / "wiki").resolve()
    # path enforcement strict — n'écrit JAMAIS hors wiki/<entity_type>/
    if canon_root not in out.parents:
        raise PromotionInputError(f"refus écriture hors wiki/: {out}")
    return out


def _canon_already_approved(wiki_root: Path, fm: dict) -> bool:
    """
    True si wiki/<entity_type>/<slug>.md existe DÉJÀ en review_status: approved.

    Garde anti-écrasement (ADR-083 durcissement) : promote.py ne clobbe JAMAIS
    une fiche canon déjà validée (humain ou run antérieur). Fail-closed : fichier
    présent mais illisible → True (on ne touche pas).
    """
    entity_type = fm.get("entity_type")
    slug = fm.get("slug")
    if entity_type not in WIKI_ENTITY_DIRS or not slug:
        return False
    target = wiki_root / "wiki" / entity_type / f"{slug}.md"
    if not target.is_file():
        return False
    try:
        existing_fm, _ = _parse_markdown(target)
    except Exception:
        return True  # fail-closed : illisible → ne pas écraser
    return existing_fm.get("review_status") == "approved"


def _declares_revision(fm) -> bool:
    """Vrai si la proposition déclare une révision du canon (ADR-117 D2). La clé suffit : une
    valeur mal formée est refusée par les conditions, jamais lue comme une première promotion."""
    return isinstance(fm, dict) and "revision_of" in fm


def _foreign_review_authority(canon_fm: dict) -> list[str]:
    """Entrées du canon dont l'autorité de relecture n'a pas été écrite par le décideur (ADR-117
    D1) : tout `diagnostic_safe`, `diagnostic_not_applicable.reviewed`, et toute relecture ou tout
    cachet autre qu'une relation `reviewed: true` au cachet `rule:ADR-116@<révision>` (ADR-116
    D3). Lève ValueError sur une liste mal formée (`_sourced_entries`)."""
    claims = _claimed_review_authority(canon_fm)
    entries = dict(_sourced_entries(canon_fm))
    foreign = list(claims["diagnostic_safe_true"])
    for label in dict.fromkeys(claims["reviewed_true"] + claims["review_stamp_present"]):
        evidence = (entries.get(label) or {}).get("evidence")
        if not isinstance(evidence, dict):
            evidence = {}
        stamp = evidence.get("reviewed_by")
        if not (label.startswith("diagnostic_relations[") and evidence.get("reviewed") is True
                and isinstance(stamp, str) and stamp.startswith(RELATION_REVIEW_STAMP_PREFIX)
                and len(stamp) > len(RELATION_REVIEW_STAMP_PREFIX)):
            foreign.append(label)
    return foreign


def _canon_revision_local(candidate_path, wiki_root: Path, manifest: dict, baseline_path):
    """Conditions d'ADR-117 lues sur le canon et la proposition : D1 (`promoter_canon`,
    `not_safety`, `no_human_authority`), D2 (`target_approved`, `base_current`) et les invariants
    de D3 (`exportable_unchanged`, `safety_rules_unchanged`), plus `baseline_is_canon` pour la
    régression. Proposition sans `revision_of` : None, rien ne change (D2). Le canon est lu une
    fois : empreinte et frontmatter viennent des mêmes octets, comparés à l'empreinte
    `canon_target` du manifeste. Une condition dont le calcul échoue est fausse et son erreur est
    rapportée ; un doute de classification vaut sécurité."""
    wiki_root = Path(wiki_root)
    fm, _ = _parse_markdown(Path(candidate_path))
    if not _declares_revision(fm):
        return None
    declared = fm.get("revision_of")
    declared_path = declared.get("path") if isinstance(declared, dict) else None
    declared_sha = declared.get("sha256") if isinstance(declared, dict) else None
    conditions = {k: False for k in CANON_REVISION_CONDITIONS if k in CANON_REVISION_REFUSALS}
    conditions["baseline_is_canon"] = False
    details: dict = {}
    target = _promotion_target_path(wiki_root, fm)
    target_rel = target.relative_to(wiki_root.resolve()).as_posix()
    manifest_sha = [e.get("sha256") for e in (manifest or {}).get("input_manifest") or []
                    if e.get("role") == "canon_target"]
    canon_fm = canon_sha = canon_error = None
    try:
        if target.is_file():
            canon_bytes = target.read_bytes()
            canon_sha = hashlib.sha256(canon_bytes).hexdigest()
            canon_fm, _ = _parse_markdown(target, source_bytes=canon_bytes)
        else:
            canon_error = "canon absent"
    except Exception as exc:  # fail-closed : canon illisible
        canon_error = f"canon illisible: {exc}"

    conditions["target_approved"] = (declared_path == target_rel and canon_fm is not None
                                     and canon_fm.get("review_status") == "approved")
    details["target_approved"] = {"declared_path": declared_path, "target": target_rel,
                                  "review_status": (canon_fm or {}).get("review_status"),
                                  **({"error": canon_error} if canon_error else {})}
    conditions["base_current"] = (isinstance(declared_sha, str)
                                  and bool(_SHA256_HEX_RE.match(declared_sha))
                                  and declared_sha == canon_sha and manifest_sha == [canon_sha])
    details["base_current"] = {"declared_sha256": declared_sha, "canon_sha256": canon_sha,
                               "manifest_sha256": manifest_sha}
    if baseline_path is None or Path(baseline_path).resolve() == target:
        conditions["baseline_is_canon"] = True
    if canon_fm is None:
        for k in ("promoter_canon", "not_safety", "no_human_authority",
                  "exportable_unchanged", "safety_rules_unchanged"):
            details[k] = {"error": canon_error}
        replaced = None
    else:
        reviewed_by = canon_fm.get("reviewed_by")
        evidence = canon_fm.get("promotion_evidence")
        conditions["promoter_canon"] = (
            isinstance(reviewed_by, str) and reviewed_by.startswith(f"{PROMOTER_ID}@")
            and len(reviewed_by) > len(PROMOTER_ID) + 1
            and isinstance(evidence, dict) and evidence.get("promoter") == reviewed_by
            and canon_fm.get("auto_promoted") is True and canon_fm.get("promotion_tier") == "A")
        details["promoter_canon"] = {
            "reviewed_by": reviewed_by,
            "promoter": evidence.get("promoter") if isinstance(evidence, dict) else None,
            "auto_promoted": canon_fm.get("auto_promoted"),
            "promotion_tier": canon_fm.get("promotion_tier")}
        canon_safety, proposal_safety = _is_safety_proposal(canon_fm), _is_safety_proposal(fm)
        conditions["not_safety"] = not canon_safety and not proposal_safety
        details["not_safety"] = {"canon": canon_safety, "proposal": proposal_safety}
        try:
            foreign = _foreign_review_authority(canon_fm)
            conditions["no_human_authority"] = not foreign
            details["no_human_authority"] = {"foreign_authority": foreign}
        except Exception as exc:  # fail-closed : erreur = autorité présente
            details["no_human_authority"] = {"error": str(exc)}
        conditions["exportable_unchanged"] = fm.get("exportable") == canon_fm.get("exportable")
        details["exportable_unchanged"] = {"proposal": fm.get("exportable"),
                                           "canon": canon_fm.get("exportable")}
        conditions["safety_rules_unchanged"] = fm.get("safety_rules") == canon_fm.get("safety_rules")
        details["safety_rules_unchanged"] = {"proposal_count": len(fm.get("safety_rules") or []),
                                             "canon_count": len(canon_fm.get("safety_rules") or [])}
        replaced = {"path": target_rel, "sha256": canon_sha, "reviewed_by": reviewed_by}
    return {"revision_of": declared, "replaced": replaced, "conditions": conditions,
            "details": details}


def _admitted_revision(decision: dict):
    """Trace de la révision qu'`apply_promotion` peut écrire (ADR-117 D4/D5) : verrou levé et
    `would_revise` vrai. Sinon None : l'anti-écrasement (L4) s'applique."""
    trace = (decision or {}).get("canon_revision")
    if (not CANON_REVISION_ADR or not isinstance(trace, dict) or trace.get("evaluated") is not True
            or trace.get("would_revise") is not True):
        return None
    return trace


def _verify_revision_base(wiki_root: Path, revision: dict) -> Path:
    """Canon que la révision remplace, relu au moment de l'écriture : son empreinte doit être
    celle que la révision déclare (ADR-117 D2). Différente ou illisible : `REVISION_BASE_STALE`,
    rien n'est écrit. Retourne le chemin résolu, jamais hors `wiki/`."""
    declared = revision.get("revision_of") if isinstance(revision.get("revision_of"), dict) else {}
    canon_root = (Path(wiki_root) / "wiki").resolve()
    path = (Path(wiki_root) / str(declared.get("path"))).resolve()
    if canon_root not in path.parents:
        raise PromotionInputError(f"refus révision hors wiki/: {path}")
    try:
        current = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise PromotionInputError(f"REVISION_BASE_STALE: canon illisible: {exc}") from exc
    if current != declared.get("sha256"):
        raise PromotionInputError(f"REVISION_BASE_STALE: canon {path} sha256={current}, "
                                  f"révision écrite sur {declared.get('sha256')}")
    return path


def _promoted_frontmatter(fm: dict, evaluation: dict, *, target_rel: str, sha: str, now: str,
                          relation_verdicts=None, decider_revision=None, revision=None) -> dict:
    """Frontmatter qu'`apply_promotion` écrit au canon : le frontmatter proposé, plus les champs
    de promotion. Partagé avec la Safety Auto-Gate, qui projette la fiche telle qu'elle sera
    publiée (`_promoted_fiche`).

    Relecture des relations (ADR-116 D3), seulement si `RELATION_REVIEW_ADR` est inscrite et que
    la décision l'a évaluée (`relation_verdicts` : index d'une relation de D1 → toutes ses
    conditions prouvées) : `_reviewed_relations`. Verrou vide : relations telles que proposées.

    Révision admise (ADR-117 D4, trace `_admitted_revision`) : mêmes champs, sauf `exportable`
    conservé tel que proposé (égal au canon, D3) ; `promotion_evidence.revision_of` trace le
    canon remplacé ; la déclaration `revision_of` n'est pas recopiée."""
    new_fm = dict(fm)  # copie — aucune modification du contenu éditorial
    if revision is not None:
        new_fm.pop("revision_of", None)
    if RELATION_REVIEW_ADR and relation_verdicts is not None:
        new_fm["diagnostic_relations"] = _reviewed_relations(
            fm.get("diagnostic_relations"), relation_verdicts, decider_revision, now)
    new_fm["review_status"] = "approved"
    new_fm["reviewed_by"] = f"{PROMOTER_ID}@{sha}"
    new_fm["reviewed_at"] = now
    new_fm["auto_promoted"] = True
    new_fm["validation_mode"] = "automatic"
    new_fm["promotion_tier"] = "A"
    new_fm["promotion_evidence"] = {
        "gate_status": evaluation["gate_status"],
        "confidence_score": evaluation["confidence_score"],
        "promoter": f"{PROMOTER_ID}@{sha}",
        "promoted_at": now,
    }
    # SHADOW (ADR-088 §F) : trace le tier 6-dim si calculé, pour rendre les 3 critères
    # de cutover mesurables sur le chemin réel. .get → rétro-compat (decision sans shadow).
    shadow = evaluation.get("shadow_score")
    if shadow is not None:
        new_fm["promotion_evidence"]["shadow_score"] = shadow
    if revision is not None:
        new_fm["promotion_evidence"]["revision_of"] = dict(revision["replaced"])
    else:
        exportable = dict(new_fm.get("exportable") or {})
        exportable["seo"] = True
        new_fm["exportable"] = exportable
    provenance = dict(new_fm.get("provenance") or {})
    provenance["promoted_from"] = target_rel
    provenance["promoted_at"] = now
    new_fm["provenance"] = provenance
    return new_fm


def _reviewed_relations(relations, verdicts: dict, decider_revision, now: str) -> list:
    """`diagnostic_relations[]` écrites au canon (ADR-116 D3). Relation de D1 (index présent
    dans `verdicts`) : `evidence.reviewed` = son verdict ; vrai, avec `reviewed_by` (la règle et
    la révision du décideur qui a rendu la décision) et `reviewed_at` ; faux, sans eux. La
    relecture n'est jamais héritée : une valeur proposée de ces deux champs n'est pas reprise.
    Entrée hors D1 : telle que proposée. Révision absente pour une relation relue :
    PromotionInputError, jamais un cachet sans révision."""
    if not isinstance(relations, list):
        raise PromotionInputError("diagnostic_relations_malformed: liste attendue")
    written = []
    for i, item in enumerate(relations):
        if i not in verdicts or not isinstance(item, dict) or not isinstance(item.get("evidence"), dict):
            written.append(item)
            continue
        evidence = {k: v for k, v in item["evidence"].items() if k not in ("reviewed_by", "reviewed_at")}
        evidence["reviewed"] = verdicts[i] is True
        if evidence["reviewed"]:
            if not decider_revision:
                raise PromotionInputError("relation_review_revision_missing: cachet sans révision")
            evidence["reviewed_by"] = f"rule:{RELATION_REVIEW_ADR}@{decider_revision}"
            evidence["reviewed_at"] = now
        written.append({**item, "evidence": evidence})
    return written


def _render_fiche(fm: dict, body: str) -> str:
    """Contenu du fichier canon : frontmatter YAML puis corps inchangé."""
    return (
        f"{FRONTMATTER_SEPARATOR}\n"
        f"{yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)}"
        f"{FRONTMATTER_SEPARATOR}\n{body}"
    )


def apply_promotion(target: Path, wiki_root: Path, decision: dict, *,
                    raw_root=None, baseline_path=None) -> Path:
    """Déplace la proposal vers le canon wiki approved (TIER A uniquement). 0 enrichissement.

    Move-semantics (invariant `check-slug-uniqueness`) : une gamme promue ne peut
    coexister comme proposal ET canon. On écrit le canon PUIS on supprime la proposal
    source. Traçabilité conservée : `promotion_evidence` + `provenance.promoted_from`
    + l'historique git. Fail-safe : la proposal n'est supprimée qu'APRÈS écriture d'un
    canon non-vide, et seulement si elle vit bien sous `proposals/`.
    """
    # POSIX runtime, as for the existing flock-based synchronization scripts.
    # Lock the checkout directory inode: no extra lockfile, registry or scheduler.
    # Every native promotion executor shares this lock; external authors must
    # still obey the source-editing protocol (advisory lock, not a universal CAS).
    try:
        import fcntl
    except ImportError as exc:
        raise PromotionInputError("promotion requires POSIX flock; no unlocked fallback") from exc
    lock_fd = os.open(wiki_root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PromotionInputError("PROMOTION_BUSY: another promoter holds this checkout") from exc
        # The executor accepts the full canonical decision, never caller-cached
        # frontmatter/body or a bare score. Parse the exact bytes matched to its input.
        target, wiki_root = Path(target), Path(wiki_root)
        # Révision du canon (ADR-117 D4/D5) : admise seulement verrou levé et `would_revise`
        # vrai ; l'empreinte du canon est revérifiée sous le verrou, avant et après le staging.
        revision = _admitted_revision(decision)
        revised_path = _verify_revision_base(wiki_root, revision) if revision is not None else None
        ok, refusal = authorize_apply(decision, target, wiki_root,
                                      raw_root=raw_root, baseline_path=baseline_path)
        if not ok:
            raise PromotionInputError(f"refus application: {refusal}")
        source_bytes = target.read_bytes()
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        candidates = [entry for entry in decision["inputs"]["input_manifest"]
                      if entry.get("role") == "candidate"]
        if len(candidates) != 1 or candidates[0].get("sha256") != source_hash:
            raise PromotionInputError("STALE_DECISION: candidate bytes differ from evaluated input")
        fm, body = _parse_markdown(target, source_bytes=source_bytes)
        if fm.get("review_status") not in PROMOTABLE_INPUT_STATUSES:
            raise PromotionInputError(f"source non promouvable: {fm.get('review_status')}")
        evaluation = decision.get("evaluation") or {}
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        sha = _wiki_commit_sha(wiki_root)
        out_path = _promotion_target_path(wiki_root, fm)
        # defense-in-depth : ne JAMAIS écraser une fiche canon déjà approved (idempotence / TOCTOU),
        # sauf la révision admise de ce canon précis (ADR-117)
        if revision is None and _canon_already_approved(wiki_root, fm):
            raise PromotionInputError(f"refus écrasement canon déjà approved: {out_path}")
        if revision is not None and revised_path != out_path:
            raise PromotionInputError(f"refus révision: canon déclaré {revised_path} ≠ cible {out_path}")

        new_fm = _promoted_frontmatter(fm, evaluation, target_rel=str(target.relative_to(wiki_root)),
                                       sha=sha, now=now,
                                       relation_verdicts=_relation_review_verdicts(decision),
                                       decider_revision=decision["inputs"]["decision_engine_revision"],
                                       revision=revision)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        rendered = _render_fiche(new_fm, body)
        # Same-directory staging gives readers either the complete previous file
        # or the complete new file. No partial canonical document is published.
        fd, temporary = tempfile.mkstemp(prefix=f".{out_path.stem}-", suffix=".tmp",
                                         dir=out_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                mode_source = out_path if out_path.exists() else target
                os.fchmod(stream.fileno(), stat.S_IMODE(mode_source.stat().st_mode))
                stream.write(rendered)
                stream.flush()
                os.fsync(stream.fileno())
            if revision is not None:
                _verify_revision_base(wiki_root, revision)
            ok, refusal = authorize_apply(decision, target, wiki_root,
                                          raw_root=raw_root, baseline_path=baseline_path)
            if not ok:
                raise PromotionInputError(f"refus application avant écriture: {refusal}")
            os.replace(temporary, out_path)
            parent_fd = os.open(out_path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent_fd)
            except OSError as exc:
                raise PromotionInputError(
                    f"canon publié: {out_path}; synchronisation répertoire échouée; proposal conservée") from exc
            finally:
                os.close(parent_fd)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass  # successful replace consumed the staged name

        # Move-semantics : supprimer la proposal source APRÈS écriture du canon. Gardes :
        # (1) target est un vrai fichier, (2) sous proposals/ uniquement (jamais wiki/),
        # (3) distinct du canon, (4) canon bien écrit et non-vide. Une OSError éventuelle
        # remonte au handler de main() (pas de swallow silencieux — no-silent-fallback).
        proposals_root = (wiki_root / "proposals").resolve()
        if (
            target.is_file()
            and target.resolve() != out_path.resolve()
            and proposals_root in target.resolve().parents
            and out_path.is_file()
            and out_path.stat().st_size > 0
        ):
            if target.read_bytes() != source_bytes:
                raise PromotionInputError(
                    f"canon écrit: {out_path}; proposal modifiée pendant écriture, conservée: {target}")
            target.unlink()

        return out_path
    finally:
        os.close(lock_fd)  # releases flock on every failure and normal return


def _bound_quality_gates(name: str, wiki_root: Path, raw_root):
    """Instance de `quality-gates.py` liée aux racines de la décision : le catalogue de l'arbre
    évalué et l'inventaire RAW capturés dans le manifeste, jamais le checkout d'installation du
    module ni une valeur d'environnement sans rapport. `raw_root` None : inventaire non lié."""
    qg = _load_module(name, "quality-gates.py")
    qg.SOURCE_CATALOG = Path(wiki_root) / SOURCE_CATALOG_RELPATH
    if raw_root is not None:
        qg.RAW_INVENTORY = Path(raw_root) / "manifests" / "source-inventory.csv"
        qg.RAW_CHECKSUMS = Path(raw_root) / "manifests" / "checksums.json"
    return qg


def _run_real_evaluators(candidate_path, wiki_root, raw_root, baseline_path,
                         threshold, gates, compute_score):
    """Runner I/O par défaut : appelle les évaluateurs RÉELS existants (1 exécution
    chacun) et retourne leurs sorties BRUTES. Chaque évaluateur est fail-closed :
    toute erreur → sous-résultat UNAVAILABLE (jamais un skip silencieux)."""
    candidate_path, wiki_root = Path(candidate_path), Path(wiki_root)
    fm, body = _parse_markdown(candidate_path)
    if gates is None:
        gates = _load_gates()
    if compute_score is None:
        compute_score = _load_confidence_fn()
    if threshold is None:
        threshold = AUTO_PROMOTE_THRESHOLD

    substance = evaluate_tier(fm, body, candidate_path, wiki_root,
                                      threshold, gates, compute_score, raw_root=raw_root)

    # coverage-strict (check-coverage-map)
    try:
        ccm = _load_module("_check_coverage_map", "check-coverage-map.py")
        catalog = ccm._load_catalog(wiki_root)
        schema = ccm._load_schema(wiki_root)
        coverage_raw = ccm.check_fiche(
            candidate_path, wiki_root, catalog, schema, require_source_proof=True)
    except Exception as exc:  # fail-closed
        coverage_raw = {"status": "UNAVAILABLE", "fails": [f"coverage_evaluator_error: {exc}"]}

    # regression (compare-proposal-versions) — baseline = fiche accepted de la même entité
    try:
        cmp_mod = _load_module("_compare_versions", "compare-proposal-versions.py")
        if baseline_path is None:
            try:
                bp = _promotion_target_path(wiki_root, fm)
                baseline_path = bp if (bp.is_file() and _canon_already_approved(wiki_root, fm)) else None
            except Exception:
                baseline_path = None
        regression_raw = cmp_mod.compare(candidate_path, baseline_path, wiki_root)
    except Exception as exc:  # fail-closed
        regression_raw = {"verdict": "UNAVAILABLE", "error": str(exc)}

    # provenance raw_ref cross-repo (quality-gates) — RAW dispo depuis AUTOMECANIK_RAW_PATH
    try:
        qg = _bound_quality_gates("_quality_gates_prov", wiki_root, raw_root)
        source_catalog = qg.load_source_catalog()
        _mids, _sha, _dups, raw_msg = qg.load_raw_inventory()
        raw_available = bool(_mids) or ("absent" not in (raw_msg or "").lower())
        ccm = _load_module("_coverage_provenance", "check-coverage-map.py")
        referenced_slugs = ccm.referenced_source_slugs(candidate_path, wiki_root) | qg.cited_source_slugs(fm)
        failures, warnings = qg.gate_source_catalog_raw_refs(
            source_catalog, verify_archive_slugs=referenced_slugs)
        # Citations « ancrées dans RAW » (ADR-112) : span + empreinte contre l'archive épinglée.
        failures = failures + qg.gate_citation_anchors(fm, source_catalog)
        provenance_raw = (failures, warnings)
    except Exception as exc:  # fail-closed → indisponible
        provenance_raw = ([f"provenance_evaluator_error: {exc}"], [])
        raw_available = False

    return substance, coverage_raw, regression_raw, provenance_raw, raw_available


def _evaluation_passthrough(substance) -> dict:
    """Évidence compacte de LA MÊME exécution evaluate_tier (tier/score/gate_status/
    shadow) — portée par la décision pour le stamp `apply_promotion` (DUMB EXECUTOR)
    et le report rétro-compat, SANS réexécution (contrat #2)."""
    substance = substance or {}
    return {
        "tier": substance.get("tier"),
        "confidence_score": substance.get("confidence_score"),
        "score_details": substance.get("score_details"),
        "gate_engine": substance.get("gate_engine"),
        "gate_status": substance.get("gate_status"),
        "shadow_score": substance.get("shadow_score"),
    }


def canonical_promotion_decision(candidate_path, wiki_root, *, raw_root=None,
                                 baseline_path=None, threshold=None, gates=None,
                                 compute_score=None, run_evaluators=None) -> dict:
    """Callable CANONIQUE : `snapshot → collect → decide`. Un seul cœur, plusieurs
    adapters (CLI, gap1, tests) l'appellent (contrat #7).

    Anti-TOCTOU minimal (contrat #1) : hash-before → évaluation → hash-after ; si un
    input change pendant l'évaluation ⇒ STALE_DURING_EVALUATION (fail-closed). La
    `PromotionDecision.inputs` porte le manifeste réellement consommé.
    """
    candidate_path = Path(candidate_path)
    wiki_root = Path(wiki_root)
    raw_root = _effective_raw_root(raw_root, wiki_root)
    runner = run_evaluators or _run_real_evaluators

    manifest_before = capture_input_manifest(candidate_path, wiki_root, raw_root, baseline_path)
    substance, cov_raw, reg_raw, prov_raw, raw_avail = runner(
        candidate_path, wiki_root, raw_root, baseline_path, threshold, gates, compute_score)
    try:
        manifest_after = capture_input_manifest(candidate_path, wiki_root, raw_root, baseline_path)
    except (OSError, UnicodeError, yaml.YAMLError, PromotionInputError) as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "substance_tier": _substance_tier(substance or {}),
            "promotion_status": STATUS_UNKNOWN_FAIL_CLOSED,
            "eligible": False,
            "blocking_reasons": [blocking_reason(
                "STALE_DURING_EVALUATION", "SNAPSHOT", "SNAPSHOT_GUARD",
                {"recapture_error": str(exc)})],
            "evaluation": _evaluation_passthrough(substance),
            "inputs": manifest_before,
        }

    # Engine changes during evaluation invalidate even a dry-run decision.
    # Git revision is provenance only; compare the actual captured file hashes.
    compared_keys = ("input_manifest", "evaluation_engine_revision", "decision_engine_revision")
    if any(manifest_before[k] != manifest_after[k] for k in compared_keys):
        return {
            "schema_version": SCHEMA_VERSION,
            "substance_tier": _substance_tier(substance or {}),
            "promotion_status": STATUS_UNKNOWN_FAIL_CLOSED,
            "eligible": False,
            "blocking_reasons": [blocking_reason(
                "STALE_DURING_EVALUATION", "SNAPSHOT", "SNAPSHOT_GUARD",
                {"before": {k: manifest_before[k] for k in compared_keys},
                 "after": {k: manifest_after[k] for k in compared_keys}})],
            "evaluation": _evaluation_passthrough(substance),
            "inputs": manifest_after,
        }

    bundle = assemble_bundle(substance, coverage_raw=cov_raw, regression_raw=reg_raw,
                             provenance_raw=prov_raw, raw_available=raw_avail)
    try:
        bundle["canon_revision"] = _canon_revision_local(candidate_path, wiki_root,
                                                         manifest_after, baseline_path)
    except Exception as exc:  # fail-closed : révision déclarée non évaluable
        bundle["canon_revision"] = {"error": f"canon_revision_error: {exc}"}
    decision = decide_promotion(bundle)
    decision["evaluation"] = _evaluation_passthrough(substance)
    decision["inputs"] = manifest_after
    return decision


# --- A3-v : porte du DUMB EXECUTOR (dry-run ≡ apply, anti-TOCTOU) --------------
def reverify_inputs(decision, candidate_path, wiki_root, *, raw_root=None,
                    baseline_path=None):
    """Anti-TOCTOU au moment de l'apply : recompute le manifeste CANONIQUE COMPLET +
    les DEUX engine revisions et compare à `decision.inputs`. Retourne None si toujours
    courant, sinon une BlockingReason STALE_DECISION.

    Vérifie TOUT ce qui peut invalider la décision (candidate/baseline/source-catalog/
    schema/RAW via le manifeste + le code des évaluateurs et du décideur via les engine
    revisions) — pas seulement candidate/baseline (contrat A3d). Aucune redécision.
    """
    captured = (decision or {}).get("inputs") or {}
    try:
        fresh = capture_input_manifest(candidate_path, wiki_root, raw_root, baseline_path)
    except (OSError, UnicodeError, yaml.YAMLError, PromotionInputError) as exc:
        return blocking_reason("STALE_DECISION", "SNAPSHOT", _APPLY_GUARD,
                               {"recapture_error": str(exc)})
    drift: dict = {}
    if captured.get("input_manifest") != fresh.get("input_manifest"):
        drift["input_manifest"] = {"before": captured.get("input_manifest"),
                                   "after": fresh.get("input_manifest")}
    for k in ("evaluation_engine_revision", "decision_engine_revision"):
        if captured.get(k) != fresh.get(k):
            drift[k] = {"before": captured.get(k), "after": fresh.get(k)}
    if not drift:
        return None
    return blocking_reason("STALE_DECISION", "SNAPSHOT", _APPLY_GUARD, drift)


def authorize_apply(decision, candidate_path, wiki_root, *, raw_root=None,
                    baseline_path=None):
    """Porte du DUMB EXECUTOR : retourne (ok: bool, refusal: dict|None).

    Exige `eligible=true` + `promotion_status=ELIGIBLE` + anti-TOCTOU (manifeste complet
    + engine revisions inchangés). Le `--apply` n'est JAMAIS un 2ᵉ décideur : cette
    fonction ne rescore/redécide RIEN, elle autorise (ou refuse) la décision déjà rendue.
    """
    decision = decision or {}
    if not (decision.get("eligible") and decision.get("promotion_status") == STATUS_ELIGIBLE):
        return False, blocking_reason(
            "APPLY_NOT_ELIGIBLE", "PROMOTION", _APPLY_GUARD,
            {"promotion_status": decision.get("promotion_status"),
             "eligible": decision.get("eligible")})
    stale = reverify_inputs(decision, candidate_path, wiki_root,
                            raw_root=raw_root, baseline_path=baseline_path)
    if stale is not None:
        return False, stale
    return True, None
