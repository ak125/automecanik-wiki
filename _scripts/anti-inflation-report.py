#!/usr/bin/env python3
"""anti-inflation-report — Phases 0+1 (amendement ADR-083/086 EN ATTENTE), REPORT-ONLY / ADVISORY.

Détecte les leviers de « gonflage de score » + la non-conformité de schéma sur les fiches WIKI
**sans rien bloquer** : émet des findings `BLOCKED_*` **SIMULÉS** (advisory) pour le rapport dry-run,
afin d'empêcher les agents d'apprendre à optimiser le silence (incitation perverse du défaut `medium`)
et de mesurer l'impact AVANT tout durcissement de gate câblé.

⚠️ CONTRAT (zéro blast-radius — cf. plan « gate 2-niveaux », Garde-fous) :
  - **PAS** importé par `quality-gates.run_gates`, `gates/run_all`, ni `promote.py`.
  - **N'échoue NI la CI NI la promotion** (exit 0 par défaut ; `--strict` opt-in pour usage futur).
  - **Aucune** mutation (lecture seule).
  - Conversion en gate bloquant + câblage `promote.py` + suppression du défaut `medium` + flip réel de
    `gate_schema_invalid` = **Phase 3, APRÈS ADR vault + migration du corpus**.

Réutilise l'existant (no-bricolage) :
  - `_meta/source-policy.md §9.1` via `SOURCE_TYPE_TO_MAX_CONFIDENCE` / `CONFIDENCE_RANK` (quality-gates.py)
    + `load_source_catalog()`.
  - `gates/_common.parse_markdown_file`.
  - `compute-confidence-score.compute_score` (relie les findings au score actuel = preuve du gonflage).
  - `_meta/schema/entity-data/<entity_type>.schema.json` via `jsonschema` Draft 2020-12 (schéma AUTORITATIF —
    remplace toute heuristique regex de structure).

Checks (tous SIMULÉS / advisory) :
  CONFIDENCE_MISSING    — `source_refs[]` sans `confidence` déclarée → défaut `medium`=0.6 ⇒ ~0.24 « gratuits »
                          sur les 0.40 de la dimension Sources. C'EST l'incitation perverse.
  SOURCE_WEAK_ALONE     — claim adossé UNIQUEMENT à des sources de type faible (forum / wiki_externe /
                          blog_consumer, §9.1) sans corroboration medium/high.
  SOURCE_UNCATALOGED    — sources hors `_meta/source-catalog.yaml` (URL brute / kind:raw sans slug) →
                          force de source non gouvernable par §9.1 (advisory).
  ENGINE_GENERIC        — bloc `*_by_engine` keyé sur un axe générique `fuel:` / `fuel_displacement:` alors qu'un
                          claim peut être spécifique à un code moteur (advisory : affiner en engine_family:).
  SCHEMA_NONCONFORMANT  — `entity_data` ne valide pas son schéma canonique entity-data/<type>.schema.json
                          (ex. `known_issues_by_engine` keyé `BKC`/`all_engines` ou en tableaux de strings au lieu
                          d'engineBlocks sourcés). Délégation documentée mais NON enforced aujourd'hui (gap réel).

Usage :
  anti-inflation-report.py <fiche.md>...
  anti-inflation-report.py --all [--proposals-dir <dir>] [--wiki-root <dir>] [--schema-dir <dir>]
                           [--format text|json] [--strict]
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

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover — dégrade : SCHEMA_NONCONFORMANT skip si jsonschema absent
    Draft202012Validator = None

# Axe générique d'un engineBlock (cf. vehicle.schema.json v1.1.0 — valide mais peu granulaire).
GENERIC_AXIS_PREFIXES = ("fuel:", "fuel_displacement:")
ENGINE_BLOCK_FIELDS = ("known_issues_by_engine", "maintenance_by_engine")
WEAK_STRENGTH = "low"


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
    base = re.sub(r"_p\d+$", "", str(slug))  # str() défensif + suffixe page _pNN (cf. gate_diagnostic_relations)
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
    if cataloged and all(st == WEAK_STRENGTH for st, _ in cataloged):
        out.append(Finding(
            code="SOURCE_WEAK_ALONE",
            severity="blocking_simulated",
            locus="source_refs/diagnostic_relations",
            message=("toutes les sources cataloguées citées sont de type faible (§9.1 → low : "
                     "forum/wiki_externe/blog_consumer) sans corroboration medium/high."),
        ))
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
    """Advisory : axe générique fuel:/fuel_displacement: (valide schéma mais peu granulaire).
    La conformité STRUCTURELLE (clé non canonique, valeur non engineBlock) est couverte
    AUTORITAIREMENT par check_schema_conformance — pas de regex ici."""
    out: list[Finding] = []
    if fm.get("entity_type") != "vehicle":
        return out
    ed = fm.get("entity_data") or {}
    for fieldname in ENGINE_BLOCK_FIELDS:
        block = ed.get(fieldname)
        if not isinstance(block, dict):
            continue
        for key in block:
            if str(key).startswith(GENERIC_AXIS_PREFIXES):
                out.append(Finding(
                    code="ENGINE_GENERIC",
                    severity="advisory",
                    locus=f"{fieldname}['{key}']",
                    message=("axe générique (fuel/fuel_displacement) : si le contenu fait des claims "
                             "spécifiques à un code moteur, affiner en engine_family:<code>."),
                ))
    return out


def check_schema_conformance(fm: dict, schema_dir: Path, limit: int = 8) -> list[Finding]:
    """Valide entity_data contre le schéma AUTORITATIF entity-data/<entity_type>.schema.json
    (Draft 2020-12). La délégation est documentée dans frontmatter.schema.json mais NON enforced
    aujourd'hui (gap). Report-only."""
    out: list[Finding] = []
    if Draft202012Validator is None:
        return out
    et = fm.get("entity_type")
    ed = fm.get("entity_data")
    if not et or not isinstance(ed, dict):
        return out
    schema_path = schema_dir / "entity-data" / f"{et}.schema.json"
    if not schema_path.exists():
        return out
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema).iter_errors(ed), key=lambda e: list(e.path))
    except Exception as exc:  # noqa: BLE001 — report-only, jamais crash
        return [Finding("SCHEMA_NONCONFORMANT", "advisory", "entity_data",
                        f"validation impossible ({et}.schema.json) : {exc}")]
    for err in errors[:limit]:
        loc = "entity_data" + "".join(f"[{p!r}]" for p in err.path)
        out.append(Finding(
            code="SCHEMA_NONCONFORMANT",
            severity="blocking_simulated",
            locus=loc,
            message=err.message[:240],
        ))
    if len(errors) > limit:
        out.append(Finding("SCHEMA_NONCONFORMANT", "advisory", "entity_data",
                           f"... +{len(errors) - limit} autres erreurs schéma (tronqué)."))
    return out


def analyze_file(path: Path, legacy, source_catalog: dict, compute_score,
                 wiki_root: Path, schema_dir: Path) -> FicheReport:
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
    # Defense-in-depth : un check qui plante (fiche malformée) ne doit JAMAIS casser le rapport
    # ni faire sortir le process non-zéro (contrat report-only).
    try:
        rep.findings += check_confidence_missing(fm)
        rep.findings += check_sources(legacy, source_catalog, fm)
        rep.findings += check_engine_generic(fm)
        rep.findings += check_schema_conformance(fm, schema_dir)
    except Exception as exc:  # noqa: BLE001 — report-only, jamais crash
        rep.findings.append(Finding("CHECK_ERROR", "advisory", "checks", f"un check a échoué (fiche malformée?): {exc}"))
    return rep


def render_text(reports: list[FicheReport]) -> str:
    lines = ["ANTI-INFLATION + CONFORMANCE REPORT (Phases 0+1 — REPORT-ONLY, 0 mutation, 0 échec CI)\n"]
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
    lines.append("Rappel: report-only. Aucun blocage réel tant que l'ADR-083/086 amendé n'est pas voté (Phase 3).")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Anti-inflation + conformance advisory report (report-only).")
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--all", action="store_true", help="scanner tout --proposals-dir")
    ap.add_argument("--proposals-dir", type=Path, default=REPO_ROOT / "proposals")
    ap.add_argument("--wiki-root", type=Path, default=REPO_ROOT)
    ap.add_argument("--schema-dir", type=Path, default=REPO_ROOT / "_meta" / "schema")
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

    reports = [
        analyze_file(p, legacy, source_catalog, compute_score, args.wiki_root, args.schema_dir)
        for p in targets
    ]

    if args.format == "json":
        print(json.dumps([r.to_dict() for r in reports], ensure_ascii=False, indent=2))
    else:
        print(render_text(reports))

    has_findings = any(r.findings for r in reports)
    return 1 if (args.strict and has_findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
