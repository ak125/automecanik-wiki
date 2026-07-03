#!/usr/bin/env python3
"""author_from_raw — AUTHORING automatique déterministe RAW OE → fiche structurée (GAP-1 pilote).

Chaîne cible (owner 2026-07-02) : RAW OE réel → **authoring automatique** → `entity_data.editorial`
+ body H2/H3 → (coverage-map candidate : gen_coverage_map.py) → shadow_score → auto-review.
Ce module = LE maillon authoring. 0 LLM, 0 DB, 0 réseau, 0 invention, fail-closed strict.

Principe anti-#72 (« le levier est la qualité-source OE, pas le réviseur ») : le contenu émis est
une STRUCTURATION déterministe des faits OE déjà sourcés (buckets `web-research/<slug>/*.md`,
section `## Faits sourcés`, format `- claim — url — conf`). Aucun texte inventé, aucune reformulation
LLM. `truth_level: sourced` (pas `editorial` : ce n'est pas encore de la prose humaine-polie).
Ce sont les GATES (shadow_score ADR-088 / quality-gates / check-coverage-map) qui décident ensuite —
un draft faible est CLASSÉ D avec raisons, jamais promu (l'humain ne réécrit pas, il tranche l'exception).

Sortie = fiche SHADOW (--out), JAMAIS la proposal réelle. Ne touche pas review_status/exportable :
la promotion (et l'exclusion sécurité ADR-091) restent à promote.py.

Le mapping aspect(bucket machine-key) → section canonique est CONTRÔLÉ (table, fail-closed hors table).
Sections = clés `_GAMME_EDITORIAL_ROLES` de build_exports_seo.py ; H2 alignés sur la fiche gold #72.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_REPO_PATH = Path(os.environ.get("AUTOMECANIK_RAW_PATH", REPO_ROOT.parent / "automecanik-raw")).resolve()
PROPOSALS_DIR = REPO_ROOT / "proposals"

MIN_LEN = 120  # content_md minimal (schema editorialBlock minLength=60 ; on durcit à 120 anti-thin)

# Section canonique → (H2 body, clé editorial). Clés = _GAMME_EDITORIAL_ROLES (contrat ADR-086 §2bis).
SECTION_SPEC: dict[str, tuple[str, str]] = {
    "function":            ("## Rôle technique",                     "function"),
    "failure_symptoms":    ("## Symptômes & diagnostic",             "failure_symptoms"),
    "maintenance_interval":("## Entretien & bonnes pratiques",       "maintenance_interval"),
    "variants":            ("## Compatibilité & versions",           "variants"),
    "selection_criteria":  ("## Critères de choix selon le véhicule","selection_criteria"),
    "quality_tiers":       ("## Marques & qualité",                  "quality_tiers"),
    "standards_norms":     ("## Normes & conformité",                "standards_norms"),
    "replacement_guidance":("## Montage & erreurs fréquentes",       "replacement_guidance"),
    "faq":                 ("## FAQ",                                "faq"),
}

# aspect (champ MACHINE des buckets) → section canonique. Fail-closed : hors table → skip (jamais deviné).
ASPECT_TO_SECTION: dict[str, str] = {
    "selection_criteria":            "selection_criteria",
    "selection_anti_mistakes":       "replacement_guidance",
    "common_mistakes":               "replacement_guidance",
    "compatibility":                 "variants",
    "compatibility_technical":       "variants",
    "compatibility_and_technical":   "variants",
    "fiabilite_variantes":           "variants",
    "faq_symptoms":                  "faq",
    "faq_and_symptoms":              "faq",
    "diagnostic_symptomes":          "failure_symptoms",
    "maintenance_intervals":         "maintenance_interval",
    "price_quality_brands":          "quality_tiers",
    "reglementaire_normes":          "standards_norms",
    # HORS table (fail-closed) : catalogue_edge_autodata, science_materiaux_performance,
    # serp_beating_gaps, identification_crossref, known_issues_by_engine, golf5_19tdi_specifique
}

BULLET = re.compile(
    r"^-\s+(?P<claim>.+?)\s+—\s+(?P<url>https?://\S+)\s+—\s+(?P<conf>high|medium|low)"
    r"(?:\s+\*\*\[PRIMARY\]\*\*)?\s*$"
)

# Table CONTRÔLÉE famille → gammes-sœurs commerce (dim D). Chaque slug = gamme réelle de la famille ;
# FILTRÉE contre le manifest committé (reality-check 0-DB) → 0 invention, 0 slug hors-manifest.
FAMILY_SIBLINGS: dict[str, list[str]] = {
    "freinage": ["plaquette-de-frein", "etrier-de-frein", "liquide-de-frein", "flexible-de-frein",
                 "disque-de-frein", "machoire-de-frein", "tambour-de-frein", "maitre-cylindre-de-frein"],
    "direction": ["cremaillere-de-direction", "rotule-de-direction", "biellette-de-direction",
                  "colonne-de-direction", "pompe-de-direction-assistee"],
}
# aspect présent → intention commerce (enum commerce_intent). Déterministe.
ASPECT_TO_INTENT: dict[str, str] = {
    "selection_criteria": "remplacement_piece", "compatibility": "remplacement_piece",
    "compatibility_technical": "remplacement_piece", "common_mistakes": "remplacement_piece",
    "selection_anti_mistakes": "remplacement_piece",
    "faq_symptoms": "diagnostic_avant_achat", "diagnostic_symptomes": "diagnostic_avant_achat",
    "maintenance_intervals": "entretien_preventif",
}


def _family_of(slug: str, fm: dict) -> str | None:
    fam = ((fm.get("entity_data") or {}).get("family") or "").strip().lower()
    if fam in FAMILY_SIBLINGS:
        return fam
    hay = slug.lower() + " " + str(fm.get("title") or "").lower()
    if re.search(r"frein|plaquette|disque-de-frein|etrier|ma[iî]tre-cylindre|machoire|tambour", hay):
        return "freinage"
    if re.search(r"direction|cremaillere|rotule|biellette|colonne-de-direction", hay):
        return "direction"
    return None


def _manifest_gamme_slugs(manifest_path: Path) -> set[str]:
    try:
        return set((json.loads(manifest_path.read_text(encoding="utf-8")).get("gamme_slugs")) or [])
    except Exception:
        return set()


def _domain_id(url: str) -> str:
    host = (urlparse(url).netloc or "").lower().removeprefix("www.")
    return "web:" + host if host else "web:unknown"


def _split_fm(md: str) -> tuple[dict, str]:
    if not md.startswith("---"):
        raise SystemExit("fiche sans frontmatter")
    fm_raw, body = md.split("\n---\n", 1)
    return yaml.safe_load(fm_raw.lstrip("-").lstrip("\n")) or {}, body


def _parse_bucket(text: str) -> tuple[str | None, list[dict]]:
    """(aspect, [{claim, source_id, conf}]) depuis la section '## Faits sourcés'."""
    fm, _ = (_split_fm(text) if text.startswith("---") else ({}, text))
    aspect = fm.get("aspect")
    facts: list[dict] = []
    in_facts = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_facts = line.strip().lower().startswith("## faits sourc")
            continue
        if in_facts:
            m = BULLET.match(line.strip())
            if m:
                facts.append({"claim": m.group("claim").strip(),
                              "source_id": _domain_id(m.group("url")),
                              "conf": m.group("conf")})
    return aspect, facts


def _section_prose(facts: list[dict]) -> str:
    """Prose body déterministe = faits OE structurés en phrases (0 invention). 1 fait = 1 phrase."""
    out = []
    for f in facts:
        c = f["claim"].rstrip()
        out.append(c if c.endswith((".", "!", "?")) else c + ".")
    return " ".join(out)


def author(slug: str, raw_root: Path, proposals_dir: Path,
           manifest_path: Path | None = None) -> tuple[str, dict]:
    """Retourne (fiche_shadow_md, rapport). N'écrit rien. Fail-closed."""
    proposal = proposals_dir / f"{slug}.md"
    if not proposal.exists():
        raise SystemExit(f"proposal introuvable: {proposal}")
    fm, _old_body = _split_fm(proposal.read_text(encoding="utf-8"))
    bucket_dir = raw_root / "sources" / "web-research" / slug

    report: dict = {"slug": slug, "buckets": [], "skipped": [], "sections": [], "facts_total": 0}
    # section → {facts:[...], sources:set}
    acc: dict[str, dict] = {}
    aspects_seen: list[str] = []
    if not bucket_dir.is_dir():
        report["skipped"].append({"reason": "no_bucket_dir", "path": str(bucket_dir)})
        return proposal.read_text(encoding="utf-8"), report

    for b in sorted(bucket_dir.glob("*.md")):
        aspect, facts = _parse_bucket(b.read_text(encoding="utf-8"))
        section = ASPECT_TO_SECTION.get(aspect or "")
        if aspect:
            aspects_seen.append(aspect)
        rec = {"bucket": b.name, "aspect": aspect, "section": section, "facts": len(facts)}
        if section is None:
            rec["skip"] = "aspect_hors_table"; report["skipped"].append(rec); continue
        if not facts:
            rec["skip"] = "0_fait"; report["skipped"].append(rec); continue
        slot = acc.setdefault(section, {"facts": [], "sources": set()})
        slot["facts"].extend(facts)
        slot["sources"].update(f["source_id"] for f in facts)
        report["buckets"].append(rec)
        report["facts_total"] += len(facts)

    # Build body (H2 déterministe, ordre = taxonomie SECTION_SPEC) + entity_data.editorial
    ed = fm.setdefault("entity_data", {})
    editorial: dict = {}
    body_parts: list[str] = [f"# {fm.get('title') or slug}", ""]
    for section, (h2, edkey) in SECTION_SPEC.items():
        slot = acc.get(section)
        if not slot:
            continue
        prose = _section_prose(slot["facts"])
        if len(prose) < MIN_LEN:
            report["skipped"].append({"section": section, "skip": "prose_courte", "len": len(prose)})
            continue
        src_ids = sorted(slot["sources"])
        body_parts += [h2, "", prose, ""]
        editorial[edkey] = {"content_md": prose, "source_ids": src_ids, "truth_level": "sourced"}
        report["sections"].append({"section": section, "h2": h2, "facts": len(slot["facts"]),
                                   "sources": len(src_ids), "content_len": len(prose)})

    if editorial:
        ed["editorial"] = editorial

    # dim D — related_gammes (famille ∩ manifest, 0 invention) + commerce_intent (aspects présents)
    family = _family_of(slug, fm)
    if family and manifest_path is not None:
        known = _manifest_gamme_slugs(manifest_path)
        sibs = [s for s in FAMILY_SIBLINGS.get(family, []) if s != slug and s in known]
        if sibs:
            ed["related_gammes"] = sibs
            report["related_gammes"] = sibs
    intents = sorted({ASPECT_TO_INTENT[a] for a in aspects_seen if a in ASPECT_TO_INTENT})
    if intents:
        ed["commerce_intent"] = intents
        report["commerce_intent"] = intents

    body = "\n".join(body_parts).rstrip() + "\n"
    out = "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n\n" + body
    report["editorial_sections"] = len(editorial)
    return out, report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--raw-root", type=Path, default=RAW_REPO_PATH)
    ap.add_argument("--proposals-dir", type=Path, default=PROPOSALS_DIR)
    ap.add_argument("--manifest", type=Path, default=REPO_ROOT / "_meta" / "reality-manifest.json",
                    help="reality-manifest committé (validation related_gammes, 0-DB)")
    ap.add_argument("--out", type=Path, default=None, help="fiche shadow (défaut: stdout json report only)")
    ap.add_argument("--json", action="store_true", help="imprime le rapport JSON")
    args = ap.parse_args(argv)
    md, report = author(args.slug, args.raw_root.resolve(), args.proposals_dir.resolve(), args.manifest)
    if args.out:
        args.out.write_text(md, encoding="utf-8")
        report["written"] = str(args.out)
    if args.json or not args.out:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
