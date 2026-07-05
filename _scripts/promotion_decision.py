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

A3-ii : `decide_promotion` ne consomme que `substance` (sortie evaluate_tier).
A3-iii ajoutera coverage / regression / provenance (mêmes invariants fail-closed).
"""
from __future__ import annotations

import hashlib
import importlib.util
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

SCHEMA_VERSION = "promotion-decision/v1"

STATUS_ELIGIBLE = "ELIGIBLE"
STATUS_BLOCKED = "BLOCKED"
STATUS_UNKNOWN_FAIL_CLOSED = "UNKNOWN_FAIL_CLOSED"

_SUBSTANCE_DETECTOR = "PROMOTE_EVALUATE_TIER"
_COVERAGE_DETECTOR = "COVERAGE_MAP"
_REGRESSION_DETECTOR = "REGRESSION"
_PROVENANCE_DETECTOR = "PROVENANCE_GATE"


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
    """Dérive les BlockingReason typées depuis les CHECKS structurés (pas de prose, C0)."""
    reasons: list[dict] = []
    for c in (substance or {}).get("checks", []):
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


def decide_promotion(bundle: dict) -> dict:
    """PURE : compose un PromotionEvidenceBundle en PromotionDecision (0 I/O, 0 repo).

    Déterministe : même bundle ⇒ même décision. Fail-closed préservant les dimensions
    (P0-2) : un évaluateur UNAVAILABLE ⇒ status UNKNOWN_FAIL_CLOSED, jamais un faux
    TIER B, `substance_tier` toujours exposé.
    """
    bundle = bundle or {}
    substance = bundle.get("substance") or {}
    reasons: list[dict] = list(_reasons_from_substance(substance))
    reasons += _reasons_from_coverage(bundle.get("coverage"))
    reasons += _reasons_from_regression(bundle.get("regression"))
    reasons += _reasons_from_provenance(bundle.get("provenance"))

    reasons.sort(key=_reason_sort_key)

    definitive = [r for r in reasons if not r["code"].endswith("_UNAVAILABLE")]
    if not reasons:
        status = STATUS_ELIGIBLE
    elif definitive:
        status = STATUS_BLOCKED
    else:
        status = STATUS_UNKNOWN_FAIL_CLOSED  # seulement des évaluateurs indisponibles

    return {
        "schema_version": SCHEMA_VERSION,
        "substance_tier": _substance_tier(substance),
        "promotion_status": status,
        "eligible": not reasons,
        "blocking_reasons": reasons,
    }


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
    "promote.py", "quality-gates.py", "check-coverage-map.py",
    "compare-proposal-versions.py", "shadow_score.py", "compute-confidence-score.py",
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


def capture_input_manifest(candidate_path, wiki_root, raw_root, baseline_path) -> dict:
    """Manifeste déterministe des inputs verdict-affectants réellement lisibles +
    revisions d'engine. `input_manifest` trié canoniquement (role, path). Le hash suit
    le contenu réel (worktree dirty). Aucune prétention de repro si SHA-only insuffisant."""
    wiki_root = Path(wiki_root)
    raw_root = Path(raw_root) if raw_root else None
    entries: list[dict] = []

    def add(role: str, path):
        p = Path(path)
        entries.append({"role": role, "path": _repo_rel(p, wiki_root, raw_root),
                        "sha256": _sha256_file(p)})

    add("candidate", candidate_path)
    if baseline_path is not None:
        add("baseline", baseline_path)
    add("source_catalog", wiki_root / "_meta" / "source-catalog.yaml")
    add("coverage_schema", wiki_root / "_meta" / "schema" / "coverage-map.schema.json")
    if raw_root is not None:
        add("raw_inventory", raw_root / "manifests" / "source-inventory.csv")
        add("raw_checksums", raw_root / "manifests" / "checksums.json")

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


def _run_real_evaluators(candidate_path, wiki_root, raw_root, baseline_path,
                         threshold, gates, compute_score):
    """Runner I/O par défaut : appelle les évaluateurs RÉELS existants (1 exécution
    chacun) et retourne leurs sorties BRUTES. Chaque évaluateur est fail-closed :
    toute erreur → sous-résultat UNAVAILABLE (jamais un skip silencieux)."""
    candidate_path, wiki_root = Path(candidate_path), Path(wiki_root)
    promote = _load_module("_promote_eval", "promote.py")
    fm, body = promote._parse_markdown(candidate_path)
    if gates is None:
        gates = promote._load_gates()
    if compute_score is None:
        compute_score = promote._load_confidence_fn()
    if threshold is None:
        threshold = promote.AUTO_PROMOTE_THRESHOLD

    substance = promote.evaluate_tier(fm, body, candidate_path, wiki_root,
                                      threshold, gates, compute_score)

    # coverage-strict (check-coverage-map)
    try:
        ccm = _load_module("_check_coverage_map", "check-coverage-map.py")
        catalog = ccm._load_catalog_slugs(wiki_root)
        schema = ccm._load_schema(wiki_root)
        coverage_raw = ccm.check_fiche(candidate_path, wiki_root, catalog, schema)
    except Exception as exc:  # fail-closed
        coverage_raw = {"status": "UNAVAILABLE", "fails": [f"coverage_evaluator_error: {exc}"]}

    # regression (compare-proposal-versions) — baseline = fiche accepted de la même entité
    try:
        cmp_mod = _load_module("_compare_versions", "compare-proposal-versions.py")
        if baseline_path is None:
            try:
                bp = promote._promotion_target_path(wiki_root, fm)
                baseline_path = bp if (bp.is_file() and promote._canon_already_approved(wiki_root, fm)) else None
            except Exception:
                baseline_path = None
        regression_raw = cmp_mod.compare(candidate_path, baseline_path, wiki_root)
    except Exception as exc:  # fail-closed
        regression_raw = {"verdict": "UNAVAILABLE", "error": str(exc)}

    # provenance raw_ref cross-repo (quality-gates) — RAW dispo depuis AUTOMECANIK_RAW_PATH
    try:
        qg = _load_module("_quality_gates_prov", "quality-gates.py")
        source_catalog = qg.load_source_catalog()
        _mids, _sha, _dups, raw_msg = qg.load_raw_inventory()
        raw_available = bool(_mids) or ("absent" not in (raw_msg or "").lower())
        failures, warnings = qg.gate_source_catalog_raw_refs(source_catalog)
        provenance_raw = (failures, warnings)
    except Exception as exc:  # fail-closed → indisponible
        provenance_raw = ([f"provenance_evaluator_error: {exc}"], [])
        raw_available = False

    return substance, coverage_raw, regression_raw, provenance_raw, raw_available


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
    raw_root = Path(raw_root) if raw_root else None
    runner = run_evaluators or _run_real_evaluators

    manifest_before = capture_input_manifest(candidate_path, wiki_root, raw_root, baseline_path)
    substance, cov_raw, reg_raw, prov_raw, raw_avail = runner(
        candidate_path, wiki_root, raw_root, baseline_path, threshold, gates, compute_score)
    manifest_after = capture_input_manifest(candidate_path, wiki_root, raw_root, baseline_path)

    if manifest_before["input_manifest"] != manifest_after["input_manifest"]:
        return {
            "schema_version": SCHEMA_VERSION,
            "substance_tier": _substance_tier(substance or {}),
            "promotion_status": STATUS_UNKNOWN_FAIL_CLOSED,
            "eligible": False,
            "blocking_reasons": [blocking_reason(
                "STALE_DURING_EVALUATION", "SNAPSHOT", "SNAPSHOT_GUARD",
                {"before": manifest_before["input_manifest"],
                 "after": manifest_after["input_manifest"]})],
            "inputs": manifest_after,
        }

    bundle = assemble_bundle(substance, coverage_raw=cov_raw, regression_raw=reg_raw,
                             provenance_raw=prov_raw, raw_available=raw_avail)
    decision = decide_promotion(bundle)
    decision["inputs"] = manifest_after
    return decision
