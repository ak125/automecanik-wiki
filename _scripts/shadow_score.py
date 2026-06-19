"""shadow_score — scorer 6 dimensions/100 en SHADOW (ADR-088, Phase 3.3). REPORT-ONLY.

Calcule le nouveau score **à côté** de l'ancien (`compute-confidence-score.compute_score`), **sans rien
remplacer ni câbler** à `promote.py`. Le but du shadow = **observer la distribution + comparer old↔new sur le
corpus AVANT cutover** (critère de bascule mesurable, ADR-088 §F précision #4).

Design (ADR-088) :
- **6 dimensions** : A Sources 30 · B Granularité moteur 20 · C Richesse 20 · D Commerce 15 · E Structure 10 ·
  F Review 5.
- **Planchers ENTITY-TYPE-AWARE** (précision #1) : une dimension non applicable à un type est **neutralisée**
  (exclue du total ET des planchers) ; le total est **renormalisé** sur les dimensions applicables.
- **Dégradation sûre** : pas de coverage-map → A dégradé (flag, pas crash) ; manifest non-`ready` → reality-check
  **skippé** (jamais de faux rejet, via `reality_manifest`).
- ⚠️ **Formules de dimension = v0 heuristique**, à TUNER pendant la fenêtre shadow (c'est le but). Le FRAMEWORK
  (profils par entité, renormalisation, planchers, tiers, dégradation) est ce qui est figé ici.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import reality_manifest as rm  # noqa: E402

WEIGHTS = {"A": 30, "B": 20, "C": 20, "D": 15, "E": 10, "F": 5}

# Profils par entité (précision #1) : dimensions applicables + planchers (sur le max brut de la dimension).
PROFILES = {
    "vehicle":      {"dims": {"A", "B", "C", "D", "E", "F"}, "floors": {"A": 22, "B": 15, "C": 15, "D": 10}},
    "gamme":        {"dims": {"A", "C", "D", "E", "F"},      "floors": {"A": 22, "C": 15, "D": 10}},
    "diagnostic":   {"dims": {"A", "C", "E", "F"},           "floors": {"A": 22, "C": 15}},
    "constructeur": {"dims": {"A", "C", "E", "F"},           "floors": {"A": 22, "C": 15}},
    "support":      {"dims": {"A", "C", "E", "F"},           "floors": {"A": 22}},
}
CONFIDENCE_NUMERIC = {"high": 1.0, "medium": 0.6, "low": 0.3}
TIERS = [(90, "S"), (80, "A"), (60, "B"), (40, "C"), (0, "D")]


@dataclass
class ShadowResult:
    path: str = ""
    entity_type: str = ""
    old_score: float | None = None
    dims: dict = field(default_factory=dict)        # raw points par dim applicable
    applicable: list = field(default_factory=list)
    total: int = 0                                   # renormalisé /100
    tier: str = "D"
    floors_failed: list = field(default_factory=list)
    blocked: list = field(default_factory=list)      # BLOCKED_* simulés
    notes: list = field(default_factory=list)


# --- dimensions (v0 heuristique, à tuner en shadow) --------------------------
def _dim_A(fm, coverage_map):
    """Sources, claim par claim depuis la coverage-map. Absente → 0 + flag (dégradation, pas crash)."""
    if not coverage_map:
        return 0.0, "A:no_coverage_map(dégradé)"
    # ADR-040 : la coverage-map canonique porte la clé 'coverage_entries' ; 'coverage'/'claims' = compat ascendante.
    cov = (coverage_map.get("coverage_entries") or coverage_map.get("coverage")
           or coverage_map.get("claims") or [])
    nums = [CONFIDENCE_NUMERIC.get((c or {}).get("confidence"), 0.0) for c in cov if isinstance(c, dict)]
    if not nums:
        return 0.0, "A:coverage_map_vide"
    return WEIGHTS["A"] * (sum(nums) / len(nums)), None


def _engine_blocks(fm):
    ed = fm.get("entity_data") or {}
    out = []
    for fld in ("known_issues_by_engine", "maintenance_by_engine"):
        blk = ed.get(fld)
        if isinstance(blk, dict):
            out.extend(v for v in blk.values() if isinstance(v, dict))
    return out


def _dim_B(fm, manifest, ready):
    """Granularité moteur : blocs avec applies_to.engine_codes (code-spécifique) + reality-check si manifest ready."""
    blocks = _engine_blocks(fm)
    if not blocks:
        return 0.0, "B:aucun_engineBlock"
    coded = [b for b in blocks if (b.get("applies_to") or {}).get("engine_codes")]
    frac = len(coded) / len(blocks)
    note = None
    if ready:
        all_codes = [c for b in coded for c in (b.get("applies_to") or {}).get("engine_codes", [])]
        unknown = rm.unknown_engine_codes(manifest, all_codes)
        if unknown:
            note = f"B:codes_hors_manifest={sorted(set(unknown))[:5]}"
            frac *= max(0.0, 1 - len(set(unknown)) / max(len(set(all_codes)), 1))
    return WEIGHTS["B"] * frac, note


def _editorial_blocks(fm):
    """Blocs éditoriaux gamme (ADR-086 §2bis) : sections curées + sourcées (`source_ids`)."""
    ed = fm.get("entity_data") or {}
    blk = ed.get("editorial")
    if isinstance(blk, dict):
        return [v for v in blk.values() if isinstance(v, dict)]
    return []


def _dim_C(fm):
    """Richesse (v0, à tuner en shadow) — un bloc ne compte QUE rattaché à une source (anti-padding) :
    - engine-blocks `evidence`-sourcés (véhicule / gamme moteur : filtration, distribution, injection…) ; OU
    - blocs éditoriaux `source_ids`-sourcés (gamme CHÂSSIS — frein/suspension/direction : le code moteur n'y est
      PAS le différenciateur, la richesse vit dans `entity_data.editorial`, cf. seo-content-loop §axe par famille).
    On prend le MAX des deux signaux pour ne pénaliser aucune famille de gamme."""
    eng = _engine_blocks(fm)
    edi = _editorial_blocks(fm)
    if not eng and not edi:
        return 0.0, "C:aucun_bloc"
    c_eng = (len([b for b in eng if b.get("evidence")]) / len(eng)) if eng else 0.0
    sourced_edi = [b for b in edi if b.get("source_ids")]
    c_edi = min(1.0, len(sourced_edi) / 6.0) if edi else 0.0  # cible v0 : ~6 sections sourcées = richesse pleine
    return WEIGHTS["C"] * max(c_eng, c_edi), None


def _dim_D(fm, manifest, ready):
    """Commerce : related_gammes résolues + commerce_intent."""
    ed = fm.get("entity_data") or {}
    gammes = ed.get("related_gammes") or []
    if not gammes:
        return 0.0, "D:aucune_related_gamme"
    score = 0.7
    note = None
    if ready:
        unknown = rm.unknown_gamme_slugs(manifest, gammes)
        if unknown:
            note = f"D:gammes_hors_manifest={sorted(set(unknown))[:5]}"
            score *= max(0.0, 1 - len(set(unknown)) / len(gammes))
    if ed.get("commerce_intent"):
        score = min(1.0, score + 0.3)
    return WEIGHTS["D"] * score, note


H2_RE = re.compile(r"^##\s+", re.MULTILINE)


def _dim_E(fm, body):
    """Structure : présence de sections H2 (proxy v0)."""
    n = len(H2_RE.findall(body or ""))
    return WEIGHTS["E"] * min(1.0, n / 5.0), None


def _dim_F(fm):
    """Review/traçabilité."""
    s = 0.0
    if fm.get("review_status") == "approved":
        s += 0.5
    if fm.get("lineage_id"):
        s += 0.3
    if isinstance(fm.get("exportable"), dict):
        s += 0.2
    return WEIGHTS["F"] * min(1.0, s), None


def score(fm: dict, body: str, ctx: dict) -> ShadowResult:
    et = fm.get("entity_type", "")
    res = ShadowResult(path=ctx.get("path", ""), entity_type=et)
    profile = PROFILES.get(et)
    if profile is None:
        res.notes.append(f"entity_type inconnu '{et}' → non scoré")
        return res

    manifest = ctx.get("manifest")
    ready = rm.is_ready(manifest)
    if not ready:
        res.notes.append(f"reality-check SKIPPÉ (manifest status={rm.status(manifest)})")
    cmap = ctx.get("coverage_map")

    computed = {
        "A": _dim_A(fm, cmap), "B": _dim_B(fm, manifest, ready), "C": _dim_C(fm),
        "D": _dim_D(fm, manifest, ready), "E": _dim_E(fm, body), "F": _dim_F(fm),
    }
    applicable = profile["dims"]
    res.applicable = sorted(applicable)
    raw_total = 0.0
    max_applicable = 0
    for dim in applicable:
        pts, note = computed[dim]
        res.dims[dim] = round(pts, 1)
        raw_total += pts
        max_applicable += WEIGHTS[dim]
        if note:
            res.notes.append(note)

    res.total = round(raw_total / max_applicable * 100) if max_applicable else 0
    for tmin, name in TIERS:
        if res.total >= tmin:
            res.tier = name
            break

    # planchers entity-type-aware
    for dim, floor in profile["floors"].items():
        if res.dims.get(dim, 0) < floor:
            res.floors_failed.append(f"{dim}<{floor}")
    if res.floors_failed and res.tier in ("A", "S"):
        res.tier = "B"  # plancher non atteint → jamais TIER A (cap à B)
        res.blocked.append("FLOOR_NOT_MET:" + ",".join(res.floors_failed))

    if ctx.get("compute_old"):
        try:
            res.old_score = round(float(ctx["compute_old"](fm, body, ctx.get("wiki_root"))), 2)
        except Exception:  # noqa: BLE001
            res.old_score = None
    return res


# --- CLI : rapport SHADOW (new vs old), report-only ---------------------------
def _load_compute_old():
    path = SCRIPTS_DIR / "compute-confidence-score.py"
    spec = importlib.util.spec_from_file_location("_ccs_shadow", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.compute_score


def _load_coverage_map(slug, proposals_dir):
    """Charge proposals/_coverage/<slug>.coverage.yaml (ADR-040, clé `coverage_entries`).

    Absent / slug inconnu / YAML illisible → None : dégradation SÛRE — dim A retombe sur
    `A:no_coverage_map(dégradé)`, jamais de crash ni de faux rejet. Import yaml différé pour
    garder score() sans dépendance.
    """
    if not slug:
        return None
    path = Path(proposals_dir) / "_coverage" / f"{slug}.coverage.yaml"
    if not path.exists():
        return None
    try:
        import yaml  # noqa: PLC0415 — lazy : score() reste sans dépendance yaml
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except Exception:  # noqa: BLE001 — dégradation sûre (un YAML cassé ne doit jamais bloquer le rapport)
        return None


def main(argv: list[str] | None = None) -> int:
    from gates._common import parse_markdown_file

    ap = argparse.ArgumentParser(description="Shadow score 6-dim vs ancien (report-only).")
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--proposals-dir", type=Path, default=SCRIPTS_DIR.parent / "proposals")
    ap.add_argument("--wiki-root", type=Path, default=SCRIPTS_DIR.parent)
    ap.add_argument("--manifest", type=Path, default=SCRIPTS_DIR.parent / "_meta" / "reality-manifest.json")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args(argv)

    manifest = rm.load_manifest(args.manifest)
    compute_old = _load_compute_old()
    targets = list(args.files)
    if args.all:
        targets += sorted(p for p in args.proposals_dir.glob("*.md") if not p.name.startswith("_"))
    if not targets:
        ap.error("aucune fiche : passer des fichiers ou --all")

    results = []
    for p in targets:
        try:
            fm, _fm_yaml, body = parse_markdown_file(p)
        except Exception as exc:  # noqa: BLE001
            print(f"• {p.name}  ERROR: {exc}")
            continue
        cmap = _load_coverage_map(fm.get("slug") or p.stem, args.proposals_dir)
        ctx = {"path": str(p), "manifest": manifest, "coverage_map": cmap,
               "compute_old": compute_old, "wiki_root": args.wiki_root}
        results.append(score(fm, body, ctx))

    if args.format == "json":
        print(json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2, default=str))
    else:
        print(f"SHADOW SCORE 6-dim vs ancien (REPORT-ONLY, 0 cutover) — manifest status={rm.status(manifest)}\n")
        for r in results:
            old = f"old={r.old_score}" if r.old_score is not None else "old=?"
            dims = " ".join(f"{k}={r.dims[k]}" for k in r.applicable)
            print(f"• {Path(r.path).name} [{r.entity_type}] new={r.total}/100 tier={r.tier} {old}")
            print(f"    dims: {dims}")
            if r.floors_failed:
                print(f"    planchers KO: {r.floors_failed}")
            if r.blocked:
                print(f"    BLOCKED(sim): {r.blocked}")
            if r.notes:
                print(f"    notes: {r.notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
