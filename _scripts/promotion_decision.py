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


def decide_promotion(bundle: dict) -> dict:
    """PURE : compose un PromotionEvidenceBundle en PromotionDecision (0 I/O, 0 repo).

    Déterministe : même bundle ⇒ même décision. Fail-closed préservant les dimensions.
    """
    substance = (bundle or {}).get("substance") or {}
    reasons: list[dict] = list(_reasons_from_substance(substance))

    # (A3-iii) coverage / regression / provenance seront ajoutés ici, chacun
    # fail-closed (UNAVAILABLE ⇒ BLOCKED + reason typé, substance_tier préservé).

    reasons.sort(key=_reason_sort_key)
    eligible = not reasons
    return {
        "schema_version": SCHEMA_VERSION,
        "substance_tier": _substance_tier(substance),
        "promotion_status": STATUS_ELIGIBLE if eligible else STATUS_BLOCKED,
        "eligible": eligible,
        "blocking_reasons": reasons,
    }
