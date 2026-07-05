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


def _scan_bucket(text: str) -> tuple[str | None, list[dict], bool]:
    """(aspect, items, has_facts_section). `items` = TOUTES les lignes candidates ('- …')
    sous '## Faits sourcés', chacune {index, raw, matched, fact}. `matched=False` = ligne
    candidate au MAUVAIS format (parser incapable → unsupported_format, A7). `has_facts_section`
    = la section attendue existe (sinon bucket au format non reconnu → unsupported_format FILE)."""
    fm, _ = (_split_fm(text) if text.startswith("---") else ({}, text))
    aspect = fm.get("aspect")
    items: list[dict] = []
    in_facts = False
    has_section = False
    idx = 0
    for line in text.splitlines():
        s = line.strip()
        if line.startswith("## "):
            in_facts = s.lower().startswith("## faits sourc")
            has_section = has_section or in_facts
            continue
        if in_facts and s.startswith("- "):
            m = BULLET.match(s)
            fact = ({"claim": m.group("claim").strip(), "source_id": _domain_id(m.group("url")),
                     "conf": m.group("conf")} if m else None)
            items.append({"index": idx, "raw": s, "matched": bool(m), "fact": fact})
            idx += 1
    return aspect, items, has_section


def _parse_bucket(text: str) -> tuple[str | None, list[dict]]:
    """(aspect, [{claim, source_id, conf}]) depuis la section '## Faits sourcés' — bullets parsés."""
    aspect, items, _ = _scan_bucket(text)
    return aspect, [it["fact"] for it in items if it["matched"]]


def _section_prose(facts: list[dict]) -> str:
    """Prose body déterministe = faits OE structurés en phrases (0 invention). 1 fait = 1 phrase."""
    out = []
    for f in facts:
        c = f["claim"].rstrip()
        out.append(c if c.endswith((".", "!", "?")) else c + ".")
    return " ".join(out)


def _finalize_accounting(items: list[dict], editorial: dict) -> dict:
    """A7 : ferme la comptabilité de perte RAW sur l'unité STABLE input_item_id. Chaque item
    éligible est dans EXACTEMENT un état final (partition MECE) ; l'équation de conservation
    `eligible == consumed + unmapped + intentional_drop + unsupported_format` doit fermer.
    `extracted_count` (bullets parsés) est une métrique INTERMÉDIAIRE séparée."""
    from collections import Counter
    states = Counter(it["state"] for it in items)
    eligible = len(items)
    consumed = states.get("consumed", 0)
    unmapped = states.get("unmapped", 0)
    intentional = states.get("intentional_drop", 0)
    unsupported = states.get("unsupported_format", 0)
    extracted = consumed + unmapped + intentional  # = bullets parsés (mappés ou non, gardés ou droppés)
    conservation_ok = (eligible == consumed + unmapped + intentional + unsupported)
    return {
        "unit": "input_item_id (source_file::aspect::index)",
        "eligible_input_count": eligible,
        "extracted_count": extracted,
        "consumed_count": consumed,
        "unmapped_count": unmapped,
        "intentional_drop_count": intentional,
        "unsupported_format_count": unsupported,
        "conservation_ok": conservation_ok,
        "authored": len(editorial) > 0,
        "items": [{"input_item_id": it["input_item_id"], "state": it["state"],
                   "reason_code": it.get("reason_code"), "policy": it.get("policy"),
                   "aspect": it.get("aspect")} for it in items],
    }


def author(slug: str, raw_root: Path, proposals_dir: Path,
           manifest_path: Path | None = None) -> tuple[str, dict]:
    """Retourne (fiche_shadow_md, rapport). N'écrit rien. Fail-closed.

    A7 : comptabilité de perte RAW (report['extraction_accounting']) + `hard_fail` quand du
    RAW non vide n'extrait AUCUN fait (cesse de prétendre avoir authoré)."""
    proposal = proposals_dir / f"{slug}.md"
    if not proposal.exists():
        raise SystemExit(f"proposal introuvable: {proposal}")
    fm, _old_body = _split_fm(proposal.read_text(encoding="utf-8"))
    bucket_dir = raw_root / "sources" / "web-research" / slug

    report: dict = {"slug": slug, "buckets": [], "skipped": [], "sections": [], "facts_total": 0}
    acc: dict[str, dict] = {}       # section → {facts, sources, items(refs)}
    aspects_seen: list[str] = []
    items: list[dict] = []          # A7 : 1 input_item_id éligible → 1 état final (MECE)

    if not bucket_dir.is_dir():
        report["skipped"].append({"reason": "no_bucket_dir", "path": str(bucket_dir)})
        report["extraction_accounting"] = _finalize_accounting(items, {})
        report["authored"] = False
        report["hard_fail"] = None  # eligible==0 : « aucun input » (route capture), pas un échec dur
        report["editorial_sections"] = 0
        return proposal.read_text(encoding="utf-8"), report

    for b in sorted(bucket_dir.glob("*.md")):
        text = b.read_text(encoding="utf-8")
        aspect, bucket_items, has_section = _scan_bucket(text)
        section = ASPECT_TO_SECTION.get(aspect or "")
        if aspect:
            aspects_seen.append(aspect)

        # A7 : bucket non-vide SANS section '## Faits sourcés' reconnue (facet/.full.md invisible
        # au reader) → 1 item FILE unsupported_format (jamais perdu en silence, jamais inventé de format).
        body_after_fm = text.split("\n---\n", 1)[-1] if text.startswith("---") else text
        if not bucket_items and not has_section and body_after_fm.strip():
            items.append({"input_item_id": f"{b.name}::{aspect or 'none'}::FILE", "bucket": b.name,
                          "aspect": aspect, "state": "unsupported_format",
                          "reason_code": "no_faits_sourcees_section"})

        for it in bucket_items:
            rec = {"input_item_id": f"{b.name}::{aspect or 'none'}::{it['index']}",
                   "bucket": b.name, "aspect": aspect}
            if not it["matched"]:                    # parser incapable → unsupported_format (jamais drop)
                rec.update(state="unsupported_format", reason_code="bullet_regex_no_match")
            elif section is None:                    # parsé mais pas de section d'accueil → unmapped (visible)
                rec.update(state="unmapped", reason_code="aspect_not_in_section_table")
            else:                                    # état différé jusqu'au verdict MIN_LEN de la section
                rec.update(state="_pending_section", section=section, fact=it["fact"])
                slot = acc.setdefault(section, {"facts": [], "sources": set(), "items": []})
                slot["facts"].append(it["fact"]); slot["sources"].add(it["fact"]["source_id"])
                slot["items"].append(rec)
            items.append(rec)

        matched_n = sum(1 for it in bucket_items if it["matched"])
        rec_b = {"bucket": b.name, "aspect": aspect, "section": section, "facts": matched_n}
        if section is None:
            rec_b["skip"] = "aspect_hors_table"; report["skipped"].append(rec_b)
        elif matched_n == 0:
            rec_b["skip"] = "0_fait"; report["skipped"].append(rec_b)
        else:
            report["buckets"].append(rec_b); report["facts_total"] += matched_n

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
            # A7 : facts parsés+mappés mais section sous le plancher anti-thin → INTENTIONAL_DROP
            # gouverné (reason_code + policy + aspect), JAMAIS une poubelle silencieuse.
            for rec in slot["items"]:
                rec.update(state="intentional_drop", reason_code="section_below_min_len",
                           policy=f"MIN_LEN={MIN_LEN}")
                rec.pop("fact", None)
            continue
        src_ids = sorted(slot["sources"])
        body_parts += [h2, "", prose, ""]
        editorial[edkey] = {"content_md": prose, "source_ids": src_ids, "truth_level": "sourced"}
        report["sections"].append({"section": section, "h2": h2, "facts": len(slot["facts"]),
                                   "sources": len(src_ids), "content_len": len(prose)})
        for rec in slot["items"]:
            rec.update(state="consumed"); rec.pop("fact", None)

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

    # A7 : comptabilité de perte RAW (MECE, conservation) + échec dur fail-closed.
    acct = _finalize_accounting(items, editorial)
    report["extraction_accounting"] = acct
    report["authored"] = acct["authored"]
    hard_fail = None
    if acct["eligible_input_count"] > 0 and acct["extracted_count"] == 0:
        hard_fail = {"reason": "zero_extracted_from_nonempty_raw",
                     "eligible_input_count": acct["eligible_input_count"],
                     "detail": "RAW non vide mais 0 fait extrait (format non reconnu) — "
                               "capturer/réparer la source, ne PAS prétendre avoir authoré"}
    elif not acct["conservation_ok"]:  # invariant cassé = bug de partition (fail-closed)
        hard_fail = {"reason": "accounting_conservation_broken", "accounting": acct}
    report["hard_fail"] = hard_fail
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
    # A7 : échec dur fail-closed → exit non-zéro (RAW non vide, 0 fait extrait / conservation cassée).
    if report.get("hard_fail"):
        print(f"HARD FAIL: {report['hard_fail']['reason']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
