#!/usr/bin/env python3
"""citation-readiness-report — AI Citation Readiness (report-only, Phase 1a).

Mesure READ-ONLY : une fiche WIKI porte-t-elle des CLAIMS atomiques, sourcés,
spécifiques, projetables (donc citables par une IA) ? Ne MUTE rien. Ne décide
JAMAIS l'indexabilité (il la LIT — le gate noindex/pg_relfollow/vendable est
ajouté par la couche cockpit Phase 1b). Frère report-only de
compute-confidence-score.py / anti-inflation-report.py.

Câblage (réutilise l'existant — ZÉRO nouvelle source de vérité) :
  - claim atomique   = coverage_entries[]  (proposals/_coverage/<slug>.coverage.yaml, ADR-040)
  - projection R2     = build_exports_seo._extract_facts_sources_blocks(fm, body, type)  (ADR-086)
  - confidence fiche  = compute-confidence-score.compute_score(fm, body, wiki_root)
  - conformité moteur = jsonschema Draft202012Validator vs entity-data/vehicle.schema.json

Statuts (AiCitationStatus) :
  READY | PARTIAL | BLOCKED | NOT_ELIGIBLE
  - NOT_ELIGIBLE : claim hors périmètre (claim_type indérivable, pas de text_anchor).
  - BLOCKED      : finding bloquant (confidence non déclarée, source faible seule, non projeté).
  - PARTIAL      : claims présents mais faibles, ou score>=READY mais confidence_score fiche < gate.
  - READY        : score>=floor + 0 bloquant + confidence_score fiche >= gate.

Exit : 0 (report-only). --strict → 1 si >=1 finding bloquant. --format text|json.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from gates._common import parse_markdown_file  # noqa: E402  (réutilise l'existant stable)

ANALYZER_VERSION = "1.0.0"

# --- Constantes nommées + documentées (calibration initiale, owner-tunable) -------------------
# Poids du score de citabilité par claim. Somme == 1.0 (assert au chargement).
CITATION_READINESS_WEIGHTS: dict[str, float] = {
    "atomicity": 0.20,      # text_anchor présent, <= MAX_CLAIM_ANCHOR_CHARS, mono-phrase
    "context": 0.20,        # entity_scope résolu ; axe moteur générique = facteur réduit
    "proof": 0.30,          # CONFIDENCE_NUMERIC clampé à 0 si confidence non déclarée
    "actionability": 0.15,  # claim_type actionnable (sinon neutre, pas pénalisé à 0)
    "projectability": 0.15, # le claim atteint >=1 bloc projeté (R2 reachable) sinon 0
}
assert abs(sum(CITATION_READINESS_WEIGHTS.values()) - 1.0) < 1e-9, "weights must sum to 1.0"

CITATION_READY_FLOOR = 0.80
CITATION_PARTIAL_FLOOR = 0.55
CITATION_CONFIDENCE_GATE = 0.70   # = plancher 'low' de compute-confidence-score
ENGINE_GENERIC_CONTEXT_FACTOR = 0.5
ACTIONABILITY_NEUTRAL = 0.5
MAX_CLAIM_ANCHOR_CHARS = 140      # = cap text_anchor dans coverage-map.schema.json
CONFIDENCE_NUMERIC = {"high": 1.0, "medium": 0.6, "low": 0.3}
ACTIONABLE_CLAIM_TYPES = {"maintenance", "diagnostic", "buying_advice"}

# Bloc projeté = unité citable runtime (ADR-086). truth_level → composante 'proof'.
TRUTHLEVEL_PROOF = {"db_owned": 1.0, "sourced": 0.9, "inferred": 0.6, "editorial": 0.4}
# claim_type d'un bloc, par (role, section). Unmapped -> None + CLAIM_TYPE_UNMAPPED.
_BLOCK_TO_CLAIM_TYPE: dict[tuple[str, str], str] = {
    ("R8_VEHICLE", "known_issues"): "symptom",
    ("R8_VEHICLE", "maintenance"): "maintenance",
    ("R3_CONSEILS", "maintenance"): "maintenance",
    ("R3_CONSEILS", "failure_symptoms"): "symptom",
    ("R3_CONSEILS", "function"): "compatibility",
    ("R4_REFERENCE", "compatibility"): "compatibility",
    ("R4_REFERENCE", "related"): "compatibility",
    ("R6_GUIDE_ACHAT", "selection"): "buying_advice",
}

# Dérivation claim_type depuis la section H2 (le coverage_entry porte la section markdown).
# Mapping nommé, précédence par ordre d'itération. Unmapped -> None + CLAIM_TYPE_UNMAPPED.
_SECTION_KEYWORD_TO_CLAIM_TYPE: list[tuple[str, str]] = [
    ("diagnostic", "diagnostic"),
    ("symptôme", "symptom"),
    ("symptome", "symptom"),
    ("entretien", "maintenance"),
    ("maintenance", "maintenance"),
    ("critère", "buying_advice"),
    ("critere", "buying_advice"),
    ("choix", "buying_advice"),
    ("compatib", "compatibility"),
    ("motoris", "compatibility"),
    ("version", "compatibility"),
    ("présentation", "compatibility"),
    ("presentation", "compatibility"),
]


def _load_module(name: str, filename: str) -> ModuleType:
    """Charge un module _scripts/ (filename à tiret -> non importable directement)."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_BUILDER = _load_module("_build_exports_seo", "build_exports_seo.py")
_CONF = _load_module("_compute_confidence_score", "compute-confidence-score.py")


def _vehicle_schema_validator():
    """Draft202012Validator contre entity-data/vehicle.schema.json (ou None si jsonschema absent)."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return None
    schema_path = REPO_ROOT / "_meta" / "schema" / "entity-data" / "vehicle.schema.json"
    if not schema_path.exists():
        return None
    return Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))


def _load_coverage_entries(slug: str, wiki_root: Path) -> list[dict]:
    """coverage_entries[] depuis <wiki_root>/proposals/_coverage/<slug>.coverage.yaml (vide si absent)."""
    cov = wiki_root / "proposals" / "_coverage" / f"{slug}.coverage.yaml"
    if not cov.exists():
        return []
    data = yaml.safe_load(cov.read_text(encoding="utf-8")) or {}
    entries = data.get("coverage_entries") or []
    return [e for e in entries if isinstance(e, dict)]


def _derive_claim_type(entry: dict) -> str | None:
    section = (entry.get("section") or "").lower()
    for needle, ctype in _SECTION_KEYWORD_TO_CLAIM_TYPE:
        if needle in section:
            return ctype
    return None


def _score_claim(entry: dict, claim_type: str | None, is_vehicle_aware: bool,
                 engine_generic: bool, has_blocks: bool) -> tuple[float, list[str]]:
    findings: list[str] = []

    anchor = entry.get("text_anchor") or ""
    atomicity = 1.0 if (anchor and len(anchor) <= MAX_CLAIM_ANCHOR_CHARS
                        and anchor.count(".") <= 1) else (0.5 if anchor else 0.0)

    context = 1.0 if is_vehicle_aware else 0.5
    if is_vehicle_aware and engine_generic:
        context *= ENGINE_GENERIC_CONTEXT_FACTOR

    conf = entry.get("confidence")
    if conf not in CONFIDENCE_NUMERIC:
        proof = 0.0
        findings.append("CITATION_CONFIDENCE_UNDECLARED")
    else:
        proof = CONFIDENCE_NUMERIC[conf]
        # source faible seule (low) sans corroboration medium/high -> clamp
        if conf == "low" and entry.get("source_policy") != "2_medium_concordant":
            proof = 0.0
            findings.append("SOURCE_WEAK_ALONE")

    actionability = 1.0 if (claim_type in ACTIONABLE_CLAIM_TYPES) else ACTIONABILITY_NEUTRAL

    projectability = 1.0 if has_blocks else 0.0
    if not has_blocks:
        findings.append("CITATION_NOT_PROJECTED")

    score = (CITATION_READINESS_WEIGHTS["atomicity"] * atomicity
             + CITATION_READINESS_WEIGHTS["context"] * context
             + CITATION_READINESS_WEIGHTS["proof"] * proof
             + CITATION_READINESS_WEIGHTS["actionability"] * actionability
             + CITATION_READINESS_WEIGHTS["projectability"] * projectability)
    return round(score, 3), findings


def _claim_verdict(claim_type: str | None, anchor: str, score: float,
                   findings: list[str], fiche_confidence: float) -> str:
    if claim_type is None or not anchor:
        return "NOT_ELIGIBLE"
    if findings:
        return "BLOCKED"
    if score >= CITATION_READY_FLOOR and fiche_confidence >= CITATION_CONFIDENCE_GATE:
        return "READY"
    if score >= CITATION_PARTIAL_FLOOR:
        return "PARTIAL"
    return "BLOCKED"


def _block_to_claim(block: dict, fiche_confidence: float) -> dict:
    """Un bloc projeté (ADR-086) = un claim citable runtime. Scoré comme tel."""
    role = block.get("role") or ""
    section = block.get("section") or ""
    content = block.get("content_md") or ""
    truth = block.get("truth_level") or "editorial"
    ctype = _BLOCK_TO_CLAIM_TYPE.get((role, section))
    is_va = role == "R8_VEHICLE"

    findings: list[str] = []
    if ctype is None:
        findings.append("CLAIM_TYPE_UNMAPPED")

    # atomicity : un bloc est plus riche qu'une phrase atomique → crédit partiel
    atomicity = 1.0 if len(content) <= MAX_CLAIM_ANCHOR_CHARS else 0.6
    context = 1.0 if is_va else 0.5
    proof = TRUTHLEVEL_PROOF.get(truth, 0.4)
    if not block.get("source_ids"):
        proof = 0.0
        findings.append("CITATION_SOURCE_MISSING")
    actionability = 1.0 if ctype in ACTIONABLE_CLAIM_TYPES else ACTIONABILITY_NEUTRAL
    projectability = 1.0  # un bloc EST projeté par construction

    score = round(
        CITATION_READINESS_WEIGHTS["atomicity"] * atomicity
        + CITATION_READINESS_WEIGHTS["context"] * context
        + CITATION_READINESS_WEIGHTS["proof"] * proof
        + CITATION_READINESS_WEIGHTS["actionability"] * actionability
        + CITATION_READINESS_WEIGHTS["projectability"] * projectability, 3)

    if ctype is None:
        verdict = "NOT_ELIGIBLE"
    elif findings:
        verdict = "BLOCKED"
    elif score >= CITATION_READY_FLOOR and fiche_confidence >= CITATION_CONFIDENCE_GATE:
        verdict = "READY"
    elif score >= CITATION_PARTIAL_FLOOR:
        verdict = "PARTIAL"
    else:
        verdict = "BLOCKED"

    return {
        "claim_id": f"block:{role}:{block.get('usefulness_target') or section}",
        "claim_type": ctype,
        "is_vehicle_aware": is_va,
        "is_actionable": ctype in ACTIONABLE_CLAIM_TYPES,
        "confidence": truth,            # côté bloc, la preuve est portée par truth_level
        "source_slug": ",".join(block.get("source_ids") or []),
        "score": score,
        "verdict": verdict,
        "findings": findings,
        "origin": "block",
    }


def analyze_fiche(source_path: Path, wiki_root: Path) -> dict[str, Any]:
    """Verdict déterministe pour une fiche (proposal ou canon). Aucune mutation."""
    fm, _fm_yaml, body = parse_markdown_file(source_path)
    entity_type = fm.get("entity_type", "")
    slug = fm.get("slug") or source_path.stem

    # Projection R2 via le mapping canon (réutilisé, pas re-dérivé).
    try:
        facts, _sources, blocks = _BUILDER._extract_facts_sources_blocks(fm, body, entity_type)
    except Exception as exc:  # report-only : ne jamais crasher sur une fiche
        return {"entity_id": f"{entity_type}:{slug}", "status": "BLOCKED",
                "reason": f"extract_error: {exc}", "claims": [], "summary": {}}
    has_blocks = len(blocks) > 0

    # Conformité moteur (véhicule) — flag les clés non-canoniques (ex: 'BKC', 'all_engines').
    schema_findings: list[str] = []
    if entity_type == "vehicle":
        validator = _vehicle_schema_validator()
        ed = fm.get("entity_data") or {}
        if validator is not None:
            errs = sorted(validator.iter_errors(ed), key=lambda e: list(e.path))
            for e in errs:
                loc = "/".join(str(p) for p in e.path) or "entity_data"
                schema_findings.append(f"SCHEMA_NONCONFORMANT @ {loc}: {e.message[:90]}")
        elif (ed.get("known_issues_by_engine") or ed.get("maintenance_by_engine")):
            schema_findings.append("SCHEMA_CHECK_SKIPPED (jsonschema indisponible)")

    fiche_confidence = _CONF.compute_score(fm, body, wiki_root)
    coverage = _load_coverage_entries(slug, wiki_root)

    claims_out: list[dict] = []
    for entry in coverage:
        ctype = _derive_claim_type(entry)
        anchor = entry.get("text_anchor") or ""
        # is_vehicle_aware : la fiche est un véhicule (claim ancré véhicule).
        is_va = entity_type == "vehicle"
        engine_generic = False  # axe moteur générique détecté en aval (clé fuel: vs engine_family:)
        score, findings = _score_claim(entry, ctype, is_va, engine_generic, has_blocks)
        if ctype is None:
            findings = ["CLAIM_TYPE_UNMAPPED"] + findings
        verdict = _claim_verdict(ctype, anchor, score, findings, fiche_confidence)
        claims_out.append({
            "claim_id": entry.get("claim_id"),
            "claim_type": ctype,
            "is_vehicle_aware": is_va,
            "is_actionable": ctype in ACTIONABLE_CLAIM_TYPES,
            "confidence": entry.get("confidence"),
            "source_slug": entry.get("source_slug"),
            "score": score,
            "verdict": verdict,
            "findings": findings,
            "origin": "coverage",
        })

    # Blocs projetés (ADR-086) = claims citables runtime (surface R8 par motorisation, etc.)
    for b in blocks:
        claims_out.append(_block_to_claim(b, fiche_confidence))

    # Verdict fiche (agrégat)
    if not claims_out:
        fiche_status = "BLOCKED"
        fiche_reason = "claims non déclarés (0 coverage_entries, 0 bloc projeté) — à formaliser"
    else:
        ready = [c for c in claims_out if c["verdict"] == "READY"]
        partial = [c for c in claims_out if c["verdict"] == "PARTIAL"]
        has_va = any(c["is_vehicle_aware"] for c in ready)
        has_buy = any(c["claim_type"] in ("buying_advice", "compatibility") for c in ready)
        if len(ready) >= 3 and has_va and has_buy:
            fiche_status = "READY"
        elif ready or partial:
            fiche_status = "PARTIAL"
        else:
            fiche_status = "BLOCKED"
        fiche_reason = (f"{len(ready)} READY / {len(partial)} PARTIAL / "
                        f"{len(claims_out)} claims")

    summary = {
        "citableClaimsCount": sum(1 for c in claims_out if c["verdict"] in ("READY", "PARTIAL")),
        "readyClaimsCount": sum(1 for c in claims_out if c["verdict"] == "READY"),
        "vehicleAwareClaimsCount": sum(1 for c in claims_out if c["is_vehicle_aware"]),
        "ficheConfidenceScore": fiche_confidence,
        "projectableBlocks": len(blocks),
        "facts": len(facts),
    }
    return {
        "entity_id": f"{entity_type}:{slug}",
        "status": fiche_status,
        "reason": fiche_reason,
        "schema_findings": schema_findings,
        "claims": sorted(claims_out, key=lambda c: c.get("claim_id") or ""),
        "summary": summary,
        "analyzer_version": ANALYZER_VERSION,
    }


def _resolve_targets(args) -> list[Path]:
    if args.files:
        return [Path(f).resolve() for f in args.files]
    # défaut : toutes les fiches proposals/*.md (hors _coverage/)
    proposals = REPO_ROOT / "proposals"
    return sorted(p for p in proposals.glob("*.md"))


def _print_text(report: dict) -> None:
    s = report["status"]
    icon = {"READY": "✅", "PARTIAL": "🟡", "BLOCKED": "⛔", "NOT_ELIGIBLE": "⚪"}.get(s, "?")
    print(f"{icon} {report['entity_id']:42s} {s:12s} {report['reason']}")
    for f in report.get("schema_findings", []):
        print(f"     ⚠ {f}")
    for c in report["claims"]:
        cv = {"READY": "✅", "PARTIAL": "🟡", "BLOCKED": "⛔", "NOT_ELIGIBLE": "⚪"}.get(c["verdict"], "?")
        fnd = (" | " + ",".join(c["findings"])) if c["findings"] else ""
        print(f"     {cv} {c['claim_id']:48s} {c['claim_type'] or '-':12s} "
              f"score={c['score']:.2f}{fnd}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", help="fiches .md (défaut: proposals/*.md)")
    ap.add_argument("--wiki-root", default=str(REPO_ROOT))
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--strict", action="store_true", help="exit 1 si >=1 finding bloquant")
    args = ap.parse_args()

    wiki_root = Path(args.wiki_root).resolve()
    reports = []
    for target in _resolve_targets(args):
        try:
            reports.append(analyze_fiche(target, wiki_root))
        except Exception as exc:  # report-only : robustesse fiche malformée
            reports.append({"entity_id": target.stem, "status": "BLOCKED",
                            "reason": f"analyze_error: {exc}", "claims": [], "summary": {}})

    if args.format == "json":
        print(json.dumps({"reports": reports, "analyzer_version": ANALYZER_VERSION},
                         ensure_ascii=False, indent=2))
    else:
        for r in reports:
            _print_text(r)
        ready = sum(r["summary"].get("readyClaimsCount", 0) for r in reports)
        citable = sum(r["summary"].get("citableClaimsCount", 0) for r in reports)
        print(f"\ntotal: fiches={len(reports)} citable_claims={citable} ready_claims={ready}")

    has_blocking = any(
        c["findings"] for r in reports for c in r.get("claims", [])
    ) or any(r.get("schema_findings") for r in reports)
    return 1 if (args.strict and has_blocking) else 0


if __name__ == "__main__":
    sys.exit(main())
