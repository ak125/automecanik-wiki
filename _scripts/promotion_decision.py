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
