#!/usr/bin/env python3
"""gen_coverage_map — coverage-map CANDIDATE + rapport sources-à-valider (GAP-1 pilote, Option A owner).

Chaîne : author_from_raw → **gen_coverage_map** → shadow_score/check-coverage-map → auto-review.
0 LLM, 0 DB, 0 réseau, 0 mutation de source-catalog.yaml, fail-closed.

RÈGLE OWNER 2026-07-02 (Option A, anti-inflation ADR-088/091) : la machine PROPOSE, elle
n'auto-attribue JAMAIS le statut « source fiable officielle ». Deux tiers stricts :
  • Tier VALIDE  : la source du claim FK à une entrée EXISTANTE de `_meta/source-catalog.yaml`
                   → entrée coverage-map réelle (schema-conforme) qui COMPTE pour dim A.
  • Tier CANDIDAT: source NOUVELLE/inconnue → JAMAIS dans le YAML coverage-map (elle échouerait le
                   FK strict de check-coverage-map, et surtout ne doit pas gonfler le score). Elle va
                   dans le rapport `sources-to-validate` avec {type proposé, raison, statut
                   pending_source_validation} → validation HUMAINE 1×/source (pas 1×/fiche), puis
                   réutilisable auto sur toutes les fiches de la famille.

DURCISSEMENT OWNER 2026-07-03 — publisher-level ≠ page-level (anti-gonflement d'autorité trop large) :
  • **publisher-level** valide l'AUTORITÉ de l'éditeur (Brembo/ATE… = fiable).
  • **page-level** valide la PREUVE du claim (la page/doc précis est capturée + le claim y est ancré).
  Le fait qu'un publisher soit validé n'autorise PAS `high` claim-par-claim. `claim_confidence_cap` :
    - publisher validé + page `captured`/`verified` + text_anchor  → `high` possible, `source_policy: 1_high`.
    - publisher validé mais page `pending_capture`                 → `medium` MAX, `2_medium_concordant` (report-only, jamais `high`).
    - source inconnue                                              → exclue (`pending_source_validation`).

Le TYPE proposé (oem/équipementier/normative/tecdoc/forum/blog/unknown) est une SUGGESTION d'aide à la
validation — jamais une auto-promotion.
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
SOURCE_CATALOG = REPO_ROOT / "_meta" / "source-catalog.yaml"

BULLET = re.compile(
    r"^-\s+(?P<claim>.+?)\s+—\s+(?P<url>https?://\S+)\s+—\s+(?P<conf>high|medium|low)"
    r"(?:\s+\*\*\[PRIMARY\]\*\*)?\s*$"
)

# Heuristique d'AIDE À LA VALIDATION (jamais auto-trust) : domaine → type proposé.
# Autorité (proposé oem/équipementier/normative) — RESTE candidate tant que non validé humainement.
AUTHORITY_HINTS: list[tuple[str, str]] = [
    (r"(brembo|zf|trw|ate-brakes|ate\.|textar|ferodo|bosch|bendix|delphi|valeo|febi|"
     r"mann-?filter|mann-?hummel|mahle|denso|continental|hella|pagid|jurid|mintex|"
     r"nrf|nissens|sachs|lemforder|lucas)", "équipementier_oem"),
    (r"(iso\.org|unece|sae\.org|eur-lex|cen\.eu|din\.de|afnor|ece-)", "normative"),
    (r"(tecdoc|tecalliance)", "tecdoc"),
]
FORUM_HINTS = re.compile(
    r"(bobistheoilguy|reddit|forum|forums|quora|\.forumactif|caradisiac\.com/forum|"
    r"forum-auto|worldstandards)", re.I)

# Types catalog considérés AUTORITAIRES (→ policy 1_high autorisé quand la source est cataloguée).
# NOTE (G2 EN PAUSE owner 2026-07-03) : le rôle exact de `tecdoc_official` (preuve externe /
# corroboration, JAMAIS vérité métier — la vérité canonique = DB Massdoc) fait l'objet d'un audit
# séparé. Aucune promotion de TecDoc ici : ce set reste inchangé (le membre `tecdoc` bare, absent de
# l'enum `type`, demeure inerte) tant que l'audit n'a pas clarifié le rôle. Ne PAS « corriger » ici.
CATALOG_AUTHORITATIVE = {"oem_manual", "normative_standard", "tecdoc", "db_owned", "manufacturer_official"}


def is_page_proven(entry: dict) -> bool:
    """Prédicat CANONIQUE « source/page prouvée » (G1 Option A owner 2026-07-03, réparation #77).

    Réconcilie les DEUX schémas gouvernés : le catalog `status` (enum active|to_capture, SoT) est
    mappé vers le `source_status` coverage `captured`. RÈGLE OWNER : une entrée `active` n'est
    utilisable que si son `raw_ref` (manifest_id) est PRÉSENT — la vérification d'intégrité (FK
    manifest_id + hash drift) est faite par le gate EXISTANT `gate_source_catalog_raw_refs`
    (quality-gates.py), JAMAIS re-implémentée ici (pas de mini-système de vérité parallèle). Le
    source-catalog PROUVE (il faut un document = raw_ref) ; la vérité métier reste la DB Massdoc.
    Fail-closed : `to_capture`, `active` SANS raw_ref, ou la valeur COVERAGE `captured` (mauvais
    schéma catalog) → NON prouvé."""
    raw_ref = entry.get("raw_ref") or {}
    return (str(entry.get("status", "")).strip().lower() == "active"
            and bool(raw_ref.get("manifest_id")))


def _cap_medium(conf: str) -> str:
    """claim_confidence_cap : rabat `high`→`medium` (page non prouvée). low/medium inchangés."""
    return "medium" if conf == "high" else conf


def _domain(url: str) -> str:
    return (urlparse(url).netloc or "").lower().removeprefix("www.")


def _split_fm(md: str) -> tuple[dict, str]:
    fm_raw, body = md.split("\n---\n", 1)
    return yaml.safe_load(fm_raw.lstrip("-").lstrip("\n")) or {}, body


def _fiche_h2h3(body: str) -> list[str]:
    return [ln.strip() for ln in body.splitlines() if re.match(r"^#{2,3}\s", ln.strip())]


def _propose_type(domain: str) -> str:
    for pat, t in AUTHORITY_HINTS:
        if re.search(pat, domain):
            return t
    if FORUM_HINTS.search(domain):
        return "forum"
    return "unknown"


def _load_catalog() -> dict:
    """slug→entry + index domaine→slug (matché sur title/publisher/notes) pour le FK."""
    slugs: dict[str, dict] = {}
    domain_to_slug: dict[str, str] = {}
    if SOURCE_CATALOG.exists():
        cat = yaml.safe_load(SOURCE_CATALOG.read_text(encoding="utf-8")) or {}
        for e in (cat.get("sources") or cat.get("catalog") or []):
            if not isinstance(e, dict) or not e.get("slug"):
                continue
            slugs[e["slug"]] = e
            hay = " ".join(str(e.get(k, "")) for k in ("title", "publisher", "notes")).lower()
            for tok in re.findall(r"[a-z0-9-]+\.[a-z]{2,}", hay):
                domain_to_slug.setdefault(tok.removeprefix("www."), e["slug"])
    return {"slugs": slugs, "domain_to_slug": domain_to_slug}


def _collect_claims(slug: str, raw_root: Path) -> list[dict]:
    """[{claim, url, domain, conf, section, aspect, level}] depuis buckets + source-index level."""
    from author_from_raw import ASPECT_TO_SECTION, SECTION_SPEC, _parse_bucket  # réutilise le mapping contrôlé
    bdir = raw_root / "sources" / "web-research" / slug
    if not bdir.is_dir():
        return []
    # index domaine→level depuis source-index.json (signal autorité BRUT du scraper — non-décisionnel)
    level: dict[str, str] = {}
    idx = bdir / "source-index.json"
    if idx.exists():
        try:
            for s in (json.loads(idx.read_text(encoding="utf-8")).get("sources") or []):
                d = _domain(str(s.get("url", "")))
                if d:
                    level[d] = str(s.get("level", "")).lower()
        except Exception:
            pass
    out: list[dict] = []
    for b in sorted(bdir.glob("*.md")):
        aspect, facts = _parse_bucket(b.read_text(encoding="utf-8"))
        section = ASPECT_TO_SECTION.get(aspect or "")
        if section is None:
            continue
        h2 = SECTION_SPEC[section][0]
        for f in facts:
            url = ""  # _parse_bucket ne rend que source_id ; re-scan pour l'URL
        # re-scan direct pour garder l'URL complète
        for line in b.read_text(encoding="utf-8").splitlines():
            m = BULLET.match(line.strip())
            if not m:
                continue
            dom = _domain(m.group("url"))
            out.append({"claim": m.group("claim").strip(), "url": m.group("url"), "domain": dom,
                        "conf": m.group("conf"), "section": h2, "aspect": aspect,
                        "level": level.get(dom, "")})
    return out


def _claim_id(slug: str, section: str, i: int) -> str:
    sec = re.sub(r"[^a-z0-9]+", "-", section.lower()).strip("-")[:24]
    return f"{slug}-{sec}-{i}"


def generate(slug: str, fiche_md: str, raw_root: Path) -> tuple[dict, dict]:
    """(coverage_map_dict_or_None, report). N'écrit rien, ne mute pas source-catalog."""
    fm, body = _split_fm(fiche_md)
    valid_sections = set(_fiche_h2h3(body))
    catalog = _load_catalog()
    claims = _collect_claims(slug, raw_root)

    entries: list[dict] = []           # tier VALIDE (FK ok) → comptent dim A
    to_validate: dict[str, dict] = {}  # tier CANDIDAT (par domaine) → rapport, ne comptent pas
    per_section_i: dict[str, int] = {}

    for c in claims:
        dom = c["domain"]
        cat_slug = catalog["domain_to_slug"].get(dom)
        if cat_slug and c["section"] in valid_sections:
            entry = catalog["slugs"][cat_slug]
            authoritative = str(entry.get("type", "")) in CATALOG_AUTHORITATIVE
            # page-level : la PREUVE du claim dépend de la capture de la page (catalog status: active),
            # pas juste de l'éditeur. Le status catalog `active` → source_status coverage `captured`.
            page_proven = is_page_proven(entry)
            # claim_confidence_cap (durcissement owner 2026-07-03)
            if authoritative and page_proven:
                conf, policy, status = c["conf"], "1_high", "captured"
            else:  # publisher validé mais page non prouvée (ou type non-autoritaire) → medium max, report-only
                conf, policy, status = _cap_medium(c["conf"]), "2_medium_concordant", "pending_capture"
            i = per_section_i.get(c["section"], 0); per_section_i[c["section"]] = i + 1
            entries.append({
                "claim_id": _claim_id(slug, c["section"], i),
                "section": c["section"],
                "text_anchor": c["claim"][:80],
                "source_slug": cat_slug,
                "evidence_type": str(entry.get("type", "web_reference")),
                "confidence": conf,
                "source_policy": policy,
                "source_status": status,
            })
        else:
            rec = to_validate.setdefault(dom, {
                "domain": dom, "example_url": c["url"], "proposed_type": _propose_type(dom),
                "scraper_level": c["level"] or "unknown", "claims": 0, "sections": set(),
                "status": "pending_source_validation",
                "reason": "domaine absent de source-catalog.yaml — autorité à confirmer par un humain (1×)",
            })
            rec["claims"] += 1
            rec["sections"].add(c["section"])

    cov = None
    if entries:
        cov = {"fiche": slug, "schema_version": "1.0.0", "coverage_entries": entries}

    tv = sorted(
        ({**v, "sections": sorted(v["sections"])} for v in to_validate.values()),
        key=lambda r: (-r["claims"]))
    report = {
        "slug": slug,
        "claims_total": len(claims),
        "valid_entries": len(entries),
        "cataloged_sources": len({e["source_slug"] for e in entries}),
        "candidate_sources": len(tv),
        "candidate_claims": sum(r["claims"] for r in tv),
        "sources_to_validate": tv,
        "authority_hint_counts": _count_by(tv, "proposed_type"),
        "entries_by_confidence": _count_by(entries, "confidence"),
        "entries_page_pending_capped": sum(1 for e in entries if e["source_status"] == "pending_capture"),
        "note": ("dim A = moyenne des confidences ; page pending_capture → medium MAX (publisher validé "
                 "≠ preuve du claim). Sources inconnues = pending_source_validation, exclues (Option A)."),
    }
    return cov, report


def _count_by(rows: list[dict], key: str) -> dict:
    out: dict[str, int] = {}
    for r in rows:
        out[r[key]] = out.get(r[key], 0) + 1
    return out


def main(argv: list[str] | None = None) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling author_from_raw
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--fiche", type=Path, required=True, help="fiche authored (shadow) — source des H2")
    ap.add_argument("--raw-root", type=Path, default=RAW_REPO_PATH)
    ap.add_argument("--out-coverage", type=Path, default=None, help="écrit la coverage-map (valides only)")
    ap.add_argument("--out-report", type=Path, default=None, help="écrit le rapport sources-to-validate (json)")
    args = ap.parse_args(argv)
    cov, report = generate(args.slug, args.fiche.read_text(encoding="utf-8"), args.raw_root.resolve())
    if args.out_coverage and cov:
        args.out_coverage.write_text(yaml.safe_dump(cov, allow_unicode=True, sort_keys=False), encoding="utf-8")
        report["coverage_written"] = str(args.out_coverage)
    if args.out_report:
        args.out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
