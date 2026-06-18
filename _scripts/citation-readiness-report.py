#!/usr/bin/env python3
"""citation-readiness-report — AI Citation Readiness, FORME citable (report-only).

Mesure READ-ONLY : une fiche WIKI porte-t-elle des claims **mis en forme pour être
cités par une IA** (atomiques, typés, actionnables, projetables) ? Ne MUTE rien.
Ne décide JAMAIS l'indexabilité (la lit). Ne re-score PAS la SUBSTANCE.

CÂBLAGE (no bricolage — zéro scorer parallèle) :
  - SUBSTANCE / sources / granularité / richesse  → DÉLÉGUÉE à `shadow_score` (PR #50, ADR-088).
    Consommée si présente (son `tier`) ; sinon « substance pending #50 » (dégradation propre,
    PAS de re-dérivation). READY exige le tier substance — donc impossible sans #50 (honnête).
  - PROJECTABILITÉ  → champ ADR-088 `engineBlock.projectability` si présent, sinon « bloc émis ».
  - claim atomique  = `coverage_entries[]` (ADR-040) OU bloc projeté (R8 par motorisation, ADR-086).
  - parsing = `gates/_common.parse_markdown_file`. Projection = `build_exports_seo` (mapping pur).

CE QUI EST PROPRE À CETTE COUCHE (absent de shadow_score) : `atomicity`, `actionability`,
taxonomie `claim_type`, et le verdict citation `READY/PARTIAL/BLOCKED/NOT_ELIGIBLE`.

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

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from gates._common import parse_markdown_file  # noqa: E402

ANALYZER_VERSION = "2.0.0"  # 2.0 = délègue la substance à shadow_score (no parallel scorer)

# --- FORME citable : facettes PROPRES à cette couche (constantes nommées, owner-tunable) ------
CITABILITY_WEIGHTS = {"atomicity": 0.40, "actionability": 0.30, "projectability": 0.30}
assert abs(sum(CITABILITY_WEIGHTS.values()) - 1.0) < 1e-9, "weights must sum to 1.0"
SHAPE_FLOOR = 0.60               # forme citable minimale
MAX_CLAIM_ANCHOR_CHARS = 140     # = cap text_anchor dans coverage-map.schema.json
ACTIONABILITY_NEUTRAL = 0.5
ACTIONABLE_CLAIM_TYPES = {"maintenance", "diagnostic", "buying_advice"}
# tiers substance shadow_score ouvrant READY (sinon plafond PARTIAL)
SUBSTANCE_TIERS_READY = {"S", "A", "B"}

# claim_type d'un coverage_entry, par mot-clé de section H2. Unmapped -> None + CLAIM_TYPE_UNMAPPED.
_SECTION_KEYWORD_TO_CLAIM_TYPE: list[tuple[str, str]] = [
    ("diagnostic", "diagnostic"), ("symptôme", "symptom"), ("symptome", "symptom"),
    ("entretien", "maintenance"), ("maintenance", "maintenance"),
    ("critère", "buying_advice"), ("critere", "buying_advice"), ("choix", "buying_advice"),
    ("compatib", "compatibility"), ("motoris", "compatibility"), ("version", "compatibility"),
    ("présentation", "compatibility"), ("presentation", "compatibility"),
]
# claim_type d'un bloc projeté, par (role, section).
_BLOCK_TO_CLAIM_TYPE: dict[tuple[str, str], str] = {
    ("R8_VEHICLE", "known_issues"): "symptom", ("R8_VEHICLE", "maintenance"): "maintenance",
    ("R3_CONSEILS", "maintenance"): "maintenance", ("R3_CONSEILS", "failure_symptoms"): "symptom",
    ("R3_CONSEILS", "function"): "compatibility", ("R4_REFERENCE", "compatibility"): "compatibility",
    ("R4_REFERENCE", "related"): "compatibility", ("R6_GUIDE_ACHAT", "selection"): "buying_advice",
}


def _load_module(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_BUILDER = _load_module("_build_exports_seo", "build_exports_seo.py")


def _load_shadow_score():
    """SUBSTANCE déléguée à shadow_score (PR #50). Absent sur main → None (dégradation propre)."""
    path = SCRIPTS_DIR / "shadow_score.py"
    if not path.exists():
        return None
    try:
        return _load_module("_shadow_score", "shadow_score.py")
    except Exception:  # noqa: BLE001  (deps reality_manifest absentes, etc.)
        return None


_SHADOW = _load_shadow_score()


def _substance_tier(fm: dict, body: str, wiki_root: Path) -> str | None:
    """tier substance via shadow_score si dispo, sinon None (« pending #50 »). Jamais re-dérivé ici."""
    if _SHADOW is None:
        return None
    try:
        res = _SHADOW.score(fm, body, {"path": "", "manifest": None, "coverage_map": None,
                                       "compute_old": None, "wiki_root": wiki_root})
        return getattr(res, "tier", None)
    except Exception:  # noqa: BLE001
        return None


def _vehicle_schema_validator():
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return None
    sp = REPO_ROOT / "_meta" / "schema" / "entity-data" / "vehicle.schema.json"
    if not sp.exists():
        return None
    return Draft202012Validator(json.loads(sp.read_text(encoding="utf-8")))


def _load_coverage_entries(slug: str, wiki_root: Path) -> list[dict]:
    cov = wiki_root / "proposals" / "_coverage" / f"{slug}.coverage.yaml"
    if not cov.exists():
        return []
    import yaml
    data = yaml.safe_load(cov.read_text(encoding="utf-8")) or {}
    return [e for e in (data.get("coverage_entries") or []) if isinstance(e, dict)]


def _derive_coverage_claim_type(entry: dict) -> str | None:
    section = (entry.get("section") or "").lower()
    for needle, ctype in _SECTION_KEYWORD_TO_CLAIM_TYPE:
        if needle in section:
            return ctype
    return None


def _citability(atomicity: float, claim_type: str | None, projectability: float) -> tuple[float, bool]:
    actionability = 1.0 if claim_type in ACTIONABLE_CLAIM_TYPES else ACTIONABILITY_NEUTRAL
    score = round(CITABILITY_WEIGHTS["atomicity"] * atomicity
                  + CITABILITY_WEIGHTS["actionability"] * actionability
                  + CITABILITY_WEIGHTS["projectability"] * projectability, 3)
    return score, score >= SHAPE_FLOOR


def _verdict(claim_type: str | None, projectable: bool, shape_ok: bool, substance_tier: str | None,
             findings: list[str]) -> str:
    if claim_type is None or not projectable:
        return "NOT_ELIGIBLE"
    if findings or not shape_ok:
        return "BLOCKED"
    # forme OK → la substance (shadow_score) décide READY vs PARTIAL ; absente = plafond PARTIAL.
    if substance_tier in SUBSTANCE_TIERS_READY:
        return "READY"
    return "PARTIAL"


def _coverage_claim(entry: dict, substance_tier: str | None, has_blocks: bool) -> dict:
    ctype = _derive_coverage_claim_type(entry)
    anchor = entry.get("text_anchor") or ""
    findings = [] if ctype else ["CLAIM_TYPE_UNMAPPED"]
    atomicity = 1.0 if (anchor and len(anchor) <= MAX_CLAIM_ANCHOR_CHARS and anchor.count(".") <= 1) \
        else (0.5 if anchor else 0.0)
    projectable = has_blocks
    if not projectable:
        findings.append("CITATION_NOT_PROJECTED")
    score, shape_ok = _citability(atomicity, ctype, 1.0 if projectable else 0.0)
    return {"claim_id": entry.get("claim_id"), "origin": "coverage", "claim_type": ctype,
            "is_vehicle_aware": False, "is_actionable": ctype in ACTIONABLE_CLAIM_TYPES,
            "source_slug": entry.get("source_slug"), "shape_score": score,
            "substance_tier": substance_tier,
            "verdict": _verdict(ctype, projectable, shape_ok, substance_tier, findings),
            "findings": findings}


def _block_claim(block: dict, substance_tier: str | None) -> dict:
    role, section = block.get("role") or "", block.get("section") or ""
    content = block.get("content_md") or ""
    ctype = _BLOCK_TO_CLAIM_TYPE.get((role, section))
    findings = [] if ctype else ["CLAIM_TYPE_UNMAPPED"]
    # projectabilité : champ ADR-088 si présent, sinon « bloc émis » (= projeté par construction)
    proj_field = block.get("_projectability")
    if proj_field == "not_projectable":
        projectable, proj_val = False, 0.0
        findings.append("CITATION_NOT_PROJECTED")
    elif proj_field == "needs_review":
        projectable, proj_val = True, 0.5
    else:
        projectable, proj_val = True, 1.0
    if not block.get("source_ids"):
        findings.append("CITATION_SOURCE_MISSING")
    atomicity = 1.0 if len(content) <= MAX_CLAIM_ANCHOR_CHARS else 0.6
    score, shape_ok = _citability(atomicity, ctype, proj_val)
    return {"claim_id": f"block:{role}:{block.get('usefulness_target') or section}", "origin": "block",
            "claim_type": ctype, "is_vehicle_aware": role == "R8_VEHICLE",
            "is_actionable": ctype in ACTIONABLE_CLAIM_TYPES,
            "source_slug": ",".join(block.get("source_ids") or []), "shape_score": score,
            "substance_tier": substance_tier,
            "verdict": _verdict(ctype, projectable, shape_ok, substance_tier, findings),
            "findings": findings}


def _engineblock_projectability(fm: dict) -> dict[str, str]:
    """Map usefulness_target(=clé moteur) → champ ADR-088 projectability (si présent dans entity_data)."""
    out: dict[str, str] = {}
    ed = fm.get("entity_data") or {}
    for field in ("known_issues_by_engine", "maintenance_by_engine"):
        blk = ed.get(field)
        if isinstance(blk, dict):
            for key, entry in blk.items():
                if isinstance(entry, dict) and entry.get("projectability"):
                    out[key] = entry["projectability"]
    return out


def analyze_fiche(source_path: Path, wiki_root: Path) -> dict[str, Any]:
    fm, _y, body = parse_markdown_file(source_path)
    entity_type = fm.get("entity_type", "")
    slug = fm.get("slug") or source_path.stem

    try:
        facts, _src, blocks = _BUILDER._extract_facts_sources_blocks(fm, body, entity_type)
    except Exception as exc:  # noqa: BLE001
        return {"entity_id": f"{entity_type}:{slug}", "status": "BLOCKED",
                "reason": f"extract_error: {exc}", "claims": [], "summary": {}}
    has_blocks = len(blocks) > 0
    proj_map = _engineblock_projectability(fm)
    for b in blocks:  # propage le champ projectability ADR-088 vers le bloc projeté
        b["_projectability"] = proj_map.get(b.get("usefulness_target"))

    schema_findings: list[str] = []
    if entity_type == "vehicle":
        v = _vehicle_schema_validator()
        ed = fm.get("entity_data") or {}
        if v is not None:
            for e in sorted(v.iter_errors(ed), key=lambda e: list(e.path)):
                loc = "/".join(str(p) for p in e.path) or "entity_data"
                schema_findings.append(f"SCHEMA_NONCONFORMANT @ {loc}: {e.message[:90]}")
        elif ed.get("known_issues_by_engine") or ed.get("maintenance_by_engine"):
            schema_findings.append("SCHEMA_CHECK_SKIPPED (jsonschema indisponible)")

    substance_tier = _substance_tier(fm, body, wiki_root)
    coverage = _load_coverage_entries(slug, wiki_root)

    claims = [_coverage_claim(e, substance_tier, has_blocks) for e in coverage]
    claims += [_block_claim(b, substance_tier) for b in blocks]

    if not claims:
        status, reason = "BLOCKED", "claims non déclarés (0 coverage_entries, 0 bloc projeté)"
    else:
        ready = [c for c in claims if c["verdict"] == "READY"]
        partial = [c for c in claims if c["verdict"] == "PARTIAL"]
        has_va = any(c["is_vehicle_aware"] for c in ready)
        has_buy = any(c["claim_type"] in ("buying_advice", "compatibility") for c in ready)
        if len(ready) >= 3 and has_va and has_buy:
            status = "READY"
        elif ready or partial:
            status = "PARTIAL"
        else:
            status = "BLOCKED"
        pend = "" if substance_tier is not None else " · substance pending shadow_score (#50)"
        reason = f"{len(ready)} READY / {len(partial)} PARTIAL / {len(claims)} claims{pend}"

    return {
        "entity_id": f"{entity_type}:{slug}", "status": status, "reason": reason,
        "substance_tier": substance_tier, "schema_findings": schema_findings,
        "claims": sorted(claims, key=lambda c: c.get("claim_id") or ""),
        "summary": {
            "citableShapeClaims": sum(1 for c in claims if c["verdict"] in ("READY", "PARTIAL")),
            "readyClaims": sum(1 for c in claims if c["verdict"] == "READY"),
            "vehicleAwareClaims": sum(1 for c in claims if c["is_vehicle_aware"]),
            "projectableBlocks": len(blocks), "facts": len(facts),
            "substanceTier": substance_tier,
        },
        "analyzer_version": ANALYZER_VERSION,
    }


def _resolve_targets(args) -> list[Path]:
    if args.files:
        return [Path(f).resolve() for f in args.files]
    return sorted((Path(args.wiki_root).resolve() / "proposals").glob("*.md"))


def _print_text(r: dict) -> None:
    icon = {"READY": "✅", "PARTIAL": "🟡", "BLOCKED": "⛔", "NOT_ELIGIBLE": "⚪"}.get(r["status"], "?")
    print(f"{icon} {r['entity_id']:42s} {r['status']:12s} {r['reason']}")
    for f in r.get("schema_findings", []):
        print(f"     ⚠ {f}")
    for c in r["claims"]:
        cv = {"READY": "✅", "PARTIAL": "🟡", "BLOCKED": "⛔", "NOT_ELIGIBLE": "⚪"}.get(c["verdict"], "?")
        fnd = (" | " + ",".join(c["findings"])) if c["findings"] else ""
        print(f"     {cv} {c['claim_id']:48s} {c['claim_type'] or '-':12s} shape={c['shape_score']:.2f}{fnd}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--wiki-root", default=str(REPO_ROOT))
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    wiki_root = Path(args.wiki_root).resolve()
    reports = []
    for t in _resolve_targets(args):
        try:
            reports.append(analyze_fiche(t, wiki_root))
        except Exception as exc:  # noqa: BLE001
            reports.append({"entity_id": t.stem, "status": "BLOCKED",
                            "reason": f"analyze_error: {exc}", "claims": [], "summary": {}})

    if args.format == "json":
        print(json.dumps({"reports": reports, "analyzer_version": ANALYZER_VERSION},
                         ensure_ascii=False, indent=2))
    else:
        for r in reports:
            _print_text(r)
        shadow = "ON" if _SHADOW is not None else "absent (substance pending #50)"
        ready = sum(r["summary"].get("readyClaims", 0) for r in reports)
        cit = sum(r["summary"].get("citableShapeClaims", 0) for r in reports)
        print(f"\ntotal: fiches={len(reports)} citable_shape={cit} ready={ready} | shadow_score={shadow}")

    has_blocking = any(c["findings"] for r in reports for c in r.get("claims", [])) \
        or any(r.get("schema_findings") for r in reports)
    return 1 if (args.strict and has_blocking) else 0


if __name__ == "__main__":
    sys.exit(main())
