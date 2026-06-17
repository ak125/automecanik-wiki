#!/usr/bin/env python3
"""anti-inflation-report — Phase 0 (amendement ADR-083 EN ATTENTE), REPORT-ONLY / ADVISORY.

Détecte les leviers de « gonflage de score » sur les fiches WIKI **sans rien bloquer** :
émet des findings `BLOCKED_*` **SIMULÉS** (severity advisory) pour le rapport dry-run, afin
d'empêcher les agents d'apprendre à optimiser le silence (incitation perverse du défaut `medium`).

⚠️ CONTRAT (zéro blast-radius — cf. plan « gate 2-niveaux », Garde-fous) :
  - N'est **PAS** importé par `quality-gates.run_gates`, `gates/run_all`, ni `promote.py`.
  - N'échoue **NI** la CI **NI** la promotion (exit 0 par défaut ; `--strict` opt-in pour usage futur).
  - Ne modifie **aucun** fichier (lecture seule).
  - Conversion en gate bloquant + câblage `promote.py` + suppression du défaut `medium` = **Phase 3, APRÈS ADR vault**.

Réutilise l'existant (no-bricolage) :
  - `_meta/source-policy.md §9.1` via `SOURCE_TYPE_TO_MAX_CONFIDENCE` / `CONFIDENCE_RANK` (quality-gates.py)
    + `load_source_catalog()`.
  - `gates/_common.parse_markdown_file`.
  - `compute-confidence-score.compute_score` (relie les findings au score actuel = preuve du gonflage).

Checks (tous SIMULÉS / advisory) :
  CONFIDENCE_MISSING    — `source_refs[]` (ou evidence) sans `confidence` déclarée → défaut `medium`=0.6 ⇒ 0.24
                          « gratuits » sur les 0.40 de la dimension Sources. C'EST l'incitation perverse.
  SOURCE_WEAK_ALONE     — claim adossé UNIQUEMENT à des sources de type faible (forum / wiki_externe /
                          blog_consumer, §9.1) sans corroboration medium/high.
  SOURCE_UNCATALOGED    — sources citées hors `_meta/source-catalog.yaml` (URL brute / kind:raw sans slug) →
                          force de source non gouvernable par §9.1 (advisory).
  ENGINE_GENERIC        — bloc `*_by_engine` keyé de façon NON code-résolvable : clé `fuel:`/`fuel_displacement:`
                          générique, OU clé hors pattern canonique `^(fuel|fuel_displacement|engine_family):`
                          (ex. `all_engines`, `BKC`) — viole vehicle.schema.json engineBlock.

Usage :
  anti-inflation-report.py <fiche.md>...
  anti-inflation-report.py --all [--proposals-dir <dir>] [--wiki-root <dir>] [--format text|json] [--strict]
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
REPO_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from gates._common import load_legacy_gates_module, parse_markdown_file  # noqa: E402

# Clé d'axe canonique d'un engineBlock (cf. vehicle.schema.json v1.1.0 patternProperties).
CANON_ENGINE_KEY = re.compile(r"^(fuel|fuel_displacement|engine_family):[a-z0-9][a-z0-9._:-]*$")
GENERIC_AXIS_PREFIXES = ("fuel:", "fuel_displacement:")
ENGINE_BLOCK_FIELDS = ("known_issues_by_engine", "maintenance_by_engine")


def _load_compute_score():
    path = SCRIPTS_DIR / "compute-confidence-score.py"
    spec = importlib.util.spec_from_file_location("_confidence_score_ro", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.compute_score


@dataclass
class Finding:
    code: str                 # BLOCKED_* simulé
    severity: str             # "blocking_simulated" | "advisory"
    locus: str                # où dans la fiche
    message: str
    heuristic: bool = False


@dataclass
class FicheReport:
    path: str
    entity_type: str = ""
    confidence_score: float | None = None
    findings: list[Finding] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["counts"] = {
            "blocking_simulated": sum(1 for f in self.findings if f.severity == "blocking_simulated"),
            "advisory": sum(1 for f in self.findings if f.severity == "advisory"),
        }
        return d


def _max_conf(legacy, source_catalog: dict, slug: str) -> str | None:
    """Force §9.1 d'un slug catalogué, ou None si non catalogué."""
    base = re.sub(r"_p\d+$", "", slug)  # tolère suffixe page _pNN (cf. gate_diagnostic_relations)
    entry = source_catalog.get(base)
    if not entry:
        return None
    return legacy.SOURCE_TYPE_TO_MAX_CONFIDENCE.get(entry.get("type"))


def check_confidence_missing(fm: dict) -> list[Finding]:
    out: list[Finding] = []
    for i, ref in enumerate(fm.get("source_refs") or []):
        if isinstance(ref, dict) and "confidence" not in ref:
            kind = ref.get("kind", ref.get("type", "?"))
            out.append(Finding(
                code="CONFIDENCE_MISSING",
                severity="blocking_simulated",
                locus=f"source_refs[{i}] (kind={kind})",
                message=("confidence non déclarée → défaut medium=0.6 ⇒ ~0.24 'gratuits' sur la dimension "
                         "Sources (0.40). Doit être déclarée explicitement (§9 : high/medium/low)."),
            ))
    return out


def check_sources(legacy, source_catalog: dict, fm: dict) -> list[Finding]:
    out: list[Finding] = []
    refs = fm.get("source_refs") or []
    # Slugs catalogués cités (source_refs[].slug + diagnostic_relations[].sources[])
    cited_slugs: list[str] = []
    uncataloged = 0
    for ref in refs:
        if isinstance(ref, dict):
            if ref.get("slug"):
                cited_slugs.append(ref["slug"])
            else:
                uncataloged += 1  # ex. {kind: raw, path: ...} — pas de slug catalogue
    for r in fm.get("diagnostic_relations") or []:
        if isinstance(r, dict):
            cited_slugs.extend(r.get("sources") or [])

    strengths = [(_max_conf(legacy, source_catalog, s), s) for s in cited_slugs]
    cataloged = [(st, s) for st, s in strengths if st is not None]
    if cataloged and all(st == "low" for st, _ in cataloged):
        out.append(Finding(
            code="SOURCE_WEAK_ALONE",
            severity="blocking_simulated",
            locus="source_refs/diagnostic_relations",
            message=("toutes les sources cataloguées citées sont de type faible (§9.1 → low : "
                     "forum/wiki_externe/blog_consumer) sans corroboration medium/high."),
        ))
    # slugs cités mais inconnus du catalogue
    unknown = [s for st, s in strengths if st is None]
    if uncataloged or unknown:
        bits = []
        if uncataloged:
            bits.append(f"{uncataloged} source_ref(s) sans slug catalogue (URL brute / kind:raw)")
        if unknown:
            bits.append(f"slug(s) hors catalogue: {sorted(set(unknown))[:5]}")
        out.append(Finding(
            code="SOURCE_UNCATALOGED",
            severity="advisory",
            locus="source_refs",
            message=("; ".join(bits) + " → force de source non gouvernable par §9.1 "
                     "(la fiche devrait citer des slugs de _meta/source-catalog.yaml)."),
        ))
    return out


def check_engine_generic(fm: dict) -> list[Finding]:
    out: list[Finding] = []
    ed = fm.get("entity_data") or {}
    if fm.get("entity_type") != "vehicle":
        return out
    for fieldname in ENGINE_BLOCK_FIELDS:
        block = ed.get(fieldname)
        if not isinstance(block, dict):
            continue
        for key in block:
            if CANON_ENGINE_KEY.match(str(key)):
                if str(key).startswith(GENERIC_AXIS_PREFIXES):
                    out.append(Finding(
                        code="ENGINE_GENERIC",
                        severity="advisory",
                        locus=f"{fieldname}['{key}']",
                        message=("axe générique (fuel/fuel_displacement) : si le contenu fait des claims "
                                 "spécifiques à un code moteur, affiner en engine_family:<code>."),
                    ))
            else:
                out.append(Finding(
                    code="ENGINE_GENERIC",
                    severity="blocking_simulated",
                    locus=f"{fieldname}['{key}']",
                    message=(f"clé '{key}' hors pattern canonique "
                             "^(fuel|fuel_displacement|engine_family): — viole vehicle.schema.json engineBlock, "
                             "non code-résolvable pour la projection R8."),
                ))
    return out


def analyze_file(path: Path, legacy, source_catalog: dict, compute_score, wiki_root: Path) -> FicheReport:
    rep = FicheReport(path=str(path))
    try:
        fm, _fm_yaml, body = parse_markdown_file(path)
    except Exception as exc:  # noqa: BLE001 — report-only, jamais crash
        rep.error = f"parse error: {exc}"
        return rep
    rep.entity_type = fm.get("entity_type", "")
    if compute_score is not None:
        try:
            rep.confidence_score = round(float(compute_score(fm, body, wiki_root)), 2)
        except Exception:  # noqa: BLE001
            rep.confidence_score = None
    rep.findings += check_confidence_missing(fm)
    rep.findings += check_sources(legacy, source_catalog, fm)
    rep.findings += check_engine_generic(fm)
    return rep


def render_text(reports: list[FicheReport]) -> str:
    lines = ["ANTI-INFLATION REPORT (Phase 0 — REPORT-ONLY / advisory, 0 mutation, 0 échec CI)\n"]
    tot_block = tot_adv = 0
    for r in reports:
        d = r.to_dict()
        head = f"• {Path(r.path).name}  [{r.entity_type or '?'}]"
        if r.confidence_score is not None:
            head += f"  score={r.confidence_score}"
        if r.error:
            lines.append(head + f"  ERROR: {r.error}")
            continue
        b, a = d["counts"]["blocking_simulated"], d["counts"]["advisory"]
        tot_block += b
        tot_adv += a
        lines.append(head + f"  → {b} BLOCKED(simulé) · {a} advisory")
        for f in r.findings:
            tag = "⛔SIM" if f.severity == "blocking_simulated" else "⚠️ adv"
            h = " [heuristic]" if f.heuristic else ""
            lines.append(f"    {tag} {f.code}{h} @ {f.locus}\n        {f.message}")
    lines.append(f"\nTOTAL: {tot_block} BLOCKED(simulé) · {tot_adv} advisory sur {len(reports)} fiche(s).")
    lines.append("Rappel: report-only. Aucun blocage réel tant que l'ADR-083 amendé n'est pas voté (Phase 3).")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Anti-inflation advisory report (Phase 0, report-only).")
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--all", action="store_true", help="scanner tout --proposals-dir")
    ap.add_argument("--proposals-dir", type=Path, default=REPO_ROOT / "proposals")
    ap.add_argument("--wiki-root", type=Path, default=REPO_ROOT)
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 si findings (OPT-IN, usage futur ; défaut report-only exit 0)")
    args = ap.parse_args(argv)

    legacy = load_legacy_gates_module()
    source_catalog = legacy.load_source_catalog()
    compute_score = _load_compute_score()

    targets: list[Path] = list(args.files)
    if args.all:
        targets += sorted(p for p in args.proposals_dir.glob("*.md") if not p.name.startswith("_"))
    if not targets:
        ap.error("aucune fiche : passer des fichiers ou --all")

    reports = [analyze_file(p, legacy, source_catalog, compute_score, args.wiki_root) for p in targets]

    if args.format == "json":
        print(json.dumps([r.to_dict() for r in reports], ensure_ascii=False, indent=2))
    else:
        print(render_text(reports))

    has_findings = any(r.findings for r in reports)
    return 1 if (args.strict and has_findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
