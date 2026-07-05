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

import hashlib
import importlib.util
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent

SCHEMA_VERSION = "promotion-decision/v1"

STATUS_ELIGIBLE = "ELIGIBLE"
STATUS_BLOCKED = "BLOCKED"
STATUS_UNKNOWN_FAIL_CLOSED = "UNKNOWN_FAIL_CLOSED"

_SUBSTANCE_DETECTOR = "PROMOTE_EVALUATE_TIER"
_COVERAGE_DETECTOR = "COVERAGE_MAP"
_REGRESSION_DETECTOR = "REGRESSION"
_PROVENANCE_DETECTOR = "PROVENANCE_GATE"
_APPLY_GUARD = "APPLY_GUARD"


class PromotionInputError(Exception):
    """Erreur de cœur métier promotion (input invalide / config introuvable) —
    exception de DOMAINE click-free. Le CLI (`promote.py`) la traduit en
    `click.ClickException` À SA FRONTIÈRE (jamais l'inverse : la bibliothèque ne
    dépend pas de click). Sous-classe d'`Exception` ⇒ capturée telle quelle par les
    handlers fail-closed existants (`except Exception`), 0 changement de comportement."""


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
    "promotion_decision.py", "quality-gates.py", "check-coverage-map.py",
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
# Seuil no-op par défaut. 1.01 = inatteignable → 0 auto-promotion (= aujourd'hui).
# Activation = abaisser à 0.80 (valeur canon ADR-083), owner-décidé.
AUTO_PROMOTE_THRESHOLD = 1.01
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
    """Charge compute_score depuis compute-confidence-score.py (filename à tirets)."""
    path = SCRIPTS_DIR / "compute-confidence-score.py"
    spec = importlib.util.spec_from_file_location("_confidence_score", path)
    if spec is None or spec.loader is None:
        raise PromotionInputError(f"compute-confidence-score.py introuvable: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.compute_score


def _parse_markdown(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith(FRONTMATTER_SEPARATOR):
        raise PromotionInputError(f"proposal sans frontmatter: {path}")
    parts = text.split(f"\n{FRONTMATTER_SEPARATOR}\n", 1)
    if len(parts) != 2:
        raise PromotionInputError(f"frontmatter close-fence manquante: {path}")
    fm = yaml.safe_load(parts[0].lstrip(FRONTMATTER_SEPARATOR).lstrip("\n"))
    if not isinstance(fm, dict):
        raise PromotionInputError(f"frontmatter non-dict: {path}")
    return fm, parts[1]


def _wiki_commit_sha(wiki_root: Path) -> str:
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=wiki_root, check=True, capture_output=True, text=True,
        )
        return out.stdout.strip()
    except Exception:
        return "0000000"


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

        manifest = _rm.load_manifest(SCRIPTS_DIR.parent / "_meta" / "reality-manifest.json")
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


def _build_checks(is_safety, numeric_block, gate_results, truth_level,
                  score, threshold, gate_engine, shadow, kinds) -> list[dict]:
    """Reconstruit les CHECKS structurés à partir des valeurs DÉJÀ calculées par
    evaluate_tier (aucune ré-exécution). Chaque check = {code, status, owner_stage,
    evidence} — le substrat machine-readable que `decide_promotion` consomme sans
    parser de prose (C0). `owner_stage` = domaine responsable du défaut.
    """
    checks: list[dict] = [
        {"code": "SAFETY_HUMAN_REVIEW", "status": "fail" if is_safety else "pass",
         "owner_stage": "POLICY_SAFETY", "evidence": {"is_safety": bool(is_safety)}},
        {"code": "NUMERIC_HIGH_HARM", "status": "fail" if numeric_block else "pass",
         "owner_stage": "POLICY_NUMERIC", "evidence": {"block": list(numeric_block[:5])}},
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
                  threshold: float, gates, compute_score) -> dict:
    """
    Décision déterministe TIER A (auto) vs TIER B (humain). Fail-closed :
    toute exception est capturée par l'appelant → TIER B.
    """
    reasons: list[str] = []

    # INVARIANT SÉCURITÉ (fail-closed, prioritaire) : famille sécurité-critique →
    # JAMAIS auto-promue, quels que soient la substance et le moteur de gate. Force
    # TIER B (revue humaine ≠ auteur). Miroir de auto_review_wiki_proposal (monorepo).
    is_safety = _is_safety_proposal(fm)
    if is_safety:
        reasons.append(
            "safety: famille sécurité-critique → revue humaine obligatoire (jamais auto-promu)"
        )

    # INVARIANT ANTI-NUMBER-SWAPPING : valeurs HIGH-HARM (couple/pression) non
    # auto-vérifiables → revue humaine. Cotes/températures = observabilité (ne bloquent pas).
    numeric_flags = _numeric_review_flags(body)
    if numeric_flags["block"]:
        reasons.append(
            "numeric: valeurs critiques couple/pression non auto-vérifiables → "
            f"revue humaine (anti number-swapping): {numeric_flags['block'][:5]}"
        )

    gate_results = [(name, fn(target)) for name, fn in gates]
    failing = [(n, r.status) for n, r in gate_results if r.status != "pass"]
    if failing:
        reasons += [f"gate:{n}={s}" for n, s in failing]

    truth_level = fm.get("truth_level")
    if truth_level not in AUTO_PROMOTE_TRUTH_LEVELS:
        reasons.append(f"truth_level={truth_level} (auto exige L1/L2)")

    try:
        score = float(compute_score(fm, body, wiki_root))
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

    tier = "A" if not reasons else "B"
    return {
        "tier": tier,
        "confidence_score": round(score, 4),
        "gate_engine": gate_engine,
        "gate_status": {n: r.status for n, r in gate_results},
        "gate_outcomes": [_serialize_gate_outcome(n, r) for n, r in gate_results],
        "checks": _build_checks(is_safety, numeric_flags["block"], gate_results,
                                truth_level, score, threshold, gate_engine, shadow, kinds),
        "blocking_reasons": reasons,
        "shadow_score": shadow,
        "numeric_flags": numeric_flags,
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


def apply_promotion(target: Path, fm: dict, body: str, wiki_root: Path,
                    decision: dict) -> Path:
    """Déplace la proposal vers le canon wiki approved (TIER A uniquement). 0 enrichissement.

    Move-semantics (invariant `check-slug-uniqueness`) : une gamme promue ne peut
    coexister comme proposal ET canon. On écrit le canon PUIS on supprime la proposal
    source. Traçabilité conservée : `promotion_evidence` + `provenance.promoted_from`
    + l'historique git. Fail-safe : la proposal n'est supprimée qu'APRÈS écriture d'un
    canon non-vide, et seulement si elle vit bien sous `proposals/`.
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sha = _wiki_commit_sha(wiki_root)
    out_path = _promotion_target_path(wiki_root, fm)
    # defense-in-depth : ne JAMAIS écraser une fiche canon déjà approved (idempotence / TOCTOU)
    if _canon_already_approved(wiki_root, fm):
        raise PromotionInputError(f"refus écrasement canon déjà approved: {out_path}")

    new_fm = dict(fm)  # copie — aucune modification du contenu éditorial
    new_fm["review_status"] = "approved"
    new_fm["reviewed_by"] = f"{PROMOTER_ID}@{sha}"
    new_fm["reviewed_at"] = now
    new_fm["auto_promoted"] = True
    new_fm["promotion_tier"] = "A"
    new_fm["promotion_evidence"] = {
        "gate_status": decision["gate_status"],
        "confidence_score": decision["confidence_score"],
        "promoter": f"{PROMOTER_ID}@{sha}",
        "promoted_at": now,
    }
    # SHADOW (ADR-088 §F) : trace le tier 6-dim si calculé, pour rendre les 3 critères
    # de cutover mesurables sur le chemin réel. .get → rétro-compat (decision sans shadow).
    shadow = decision.get("shadow_score")
    if shadow is not None:
        new_fm["promotion_evidence"]["shadow_score"] = shadow
    exportable = dict(new_fm.get("exportable") or {})
    exportable["seo"] = True
    new_fm["exportable"] = exportable
    provenance = dict(new_fm.get("provenance") or {})
    provenance["promoted_from"] = str(target.relative_to(wiki_root))
    provenance["promoted_at"] = now
    new_fm["provenance"] = provenance

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = (
        f"{FRONTMATTER_SEPARATOR}\n"
        f"{yaml.safe_dump(new_fm, allow_unicode=True, sort_keys=False)}"
        f"{FRONTMATTER_SEPARATOR}\n{body}"
    )
    out_path.write_text(rendered, encoding="utf-8")

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
        target.unlink()

    return out_path


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
                bp = _promotion_target_path(wiki_root, fm)
                baseline_path = bp if (bp.is_file() and _canon_already_approved(wiki_root, fm)) else None
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


def _evaluation_passthrough(substance) -> dict:
    """Évidence compacte de LA MÊME exécution evaluate_tier (tier/score/gate_status/
    shadow) — portée par la décision pour le stamp `apply_promotion` (DUMB EXECUTOR)
    et le report rétro-compat, SANS réexécution (contrat #2)."""
    substance = substance or {}
    return {
        "tier": substance.get("tier"),
        "confidence_score": substance.get("confidence_score"),
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
            "evaluation": _evaluation_passthrough(substance),
            "inputs": manifest_after,
        }

    bundle = assemble_bundle(substance, coverage_raw=cov_raw, regression_raw=reg_raw,
                             provenance_raw=prov_raw, raw_available=raw_avail)
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
    fresh = capture_input_manifest(candidate_path, wiki_root, raw_root, baseline_path)
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
