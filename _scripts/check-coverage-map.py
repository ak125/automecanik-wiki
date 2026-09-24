#!/usr/bin/env python3
"""check-coverage-map.py — validateur coverage-map (livrable différé ADR-089).

Backing de gouvernance : ADR-089 (Content Coverage-Map Canon), encore `proposed`
au vault. Ce validateur est le « `check-coverage-map.py` » que le schéma
(`_meta/schema/coverage-map.schema.json`) et ADR-089 §Invariant nomment mais qui
n'avait jamais été construit — d'où une structure coverage-map produite ad-hoc et
incohérente (6/15 fiches sans coverage-map, dim A du score ADR-088 à 0 pour elles).

REPORT-ONLY par défaut (exit 0, observabilité). L'ENFORCEMENT (`--strict`, exit 1)
et le câblage CI restent GELÉS jusqu'à la ratification d'ADR-089 (owner G3) —
cohérent avec ADR-089 §Séquence « owner-sponsorisé après acceptation ». Aucun repli
silencieux : un trou est toujours rapporté, jamais masqué.

Invariants (ADR-089 §5) : 0 LLM, 0 DB. Reality-check via `_meta/source-catalog.yaml`
commité (FK strict), jamais de requête DB.

Vérifie, par fiche `proposals/<slug>.md` :
  1. Présence d'une coverage-map `proposals/_coverage/<slug>.coverage.yaml`
     (WARN si la fiche porte des sections H2 sourçables mais n'a pas de coverage-map).
  2. Conformité au schéma `_meta/schema/coverage-map.schema.json`.
  3. FK strict : chaque `coverage_entries[].source_slug` existe dans
     `_meta/source-catalog.yaml` (FAIL sinon — anti-gonflement du score, ADR-089 §3).
  4. Ancrage : chaque `coverage_entries[].section` correspond à un H2 OU H3 réel de la fiche
     (les fiches structurent en sous-sections ; H4+ = niveau-item, hors ancrage).
  5. Quand text_anchor est déclaré, son texte doit apparaître dans un bloc de prose
     de cette section unique. Markdown analysé, pas de correspondance floue : les
     exemples de code, commentaires et URL de lien ne constituent pas une preuve.
     Cette présence ne valide ni la vérité du claim ni son appui par la source.
  La promotion appelle require_source_proof=True : carte non vide, ancre explicite,
  source capturée/active et empreinte exigées. Le mode de préparation conserve les
  sources en attente. L'intégrité RAW reste contrôlée par quality-gates.py.

Usage:
  python3 _scripts/check-coverage-map.py --all
  python3 _scripts/check-coverage-map.py proposals/disque-de-frein.md
  python3 _scripts/check-coverage-map.py --all --strict        # enforcement (post-ADR-089)
  python3 _scripts/check-coverage-map.py --all --format json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import unicodedata

from markdown_it import MarkdownIt
from pathlib import Path

import yaml

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    Draft202012Validator = None

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def _repo_root(start: Path) -> Path:
    """Remonte jusqu'au repo wiki (présence _meta/source-catalog.yaml)."""
    cur = start.resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "_meta" / "source-catalog.yaml").is_file():
            return cand
    return start


def _load_catalog(root: Path) -> dict[str, dict]:
    """Read the selected checkout, rejecting ambiguous source identifiers."""
    cat = root / "_meta" / "source-catalog.yaml"
    data = yaml.safe_load(cat.read_text(encoding="utf-8")) or {}
    entries = {}
    for source in data.get("sources") or []:
        if not isinstance(source, dict) or not source.get("slug"):
            continue
        slug = source["slug"]
        if slug in entries:
            raise ValueError(f"duplicate_source_slug:{slug}")
        entries[slug] = source
    return entries


def _load_catalog_slugs(root: Path) -> set[str]:
    return set(_load_catalog(root))


def referenced_source_slugs(md_path: Path, root: Path) -> set[str]:
    """Scope of archive inputs; malformed maps are rejected by check_fiche."""
    path = root / "proposals" / "_coverage" / f"{md_path.stem}.coverage.yaml"
    if not path.is_file():
        return set()
    coverage = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {entry["source_slug"] for entry in coverage.get("coverage_entries") or []
            if isinstance(entry, dict) and isinstance(entry.get("source_slug"), str)}


def _load_schema(root: Path):
    sp = root / "_meta" / "schema" / "coverage-map.schema.json"
    if not sp.is_file():
        return None
    return json.loads(sp.read_text(encoding="utf-8"))


def _split_md(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    return (fm if isinstance(fm, dict) else {}), m.group(2)


def _normalize_anchor(text: str) -> str:
    # Keep negations, numbers, punctuation and accents: this is an excerpt check,
    # never a semantic similarity score. NFC accepts equivalent Unicode spelling.
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def _prose_sections(body: str) -> dict[str, list[list[str]]]:
    """H2/H3 label -> occurrences -> prose blocks (children included).

    CommonMark parsing avoids treating headings inside fenced code or comments
    as actual sections. Matching within one block prevents assembling a claim
    from unrelated paragraphs. Repeated headings remain ambiguous, not merged.
    """
    tokens = MarkdownIt("commonmark").enable("table").parse(body)
    headings = [(i, int(t.tag[1:]), "#" * int(t.tag[1:]) + " " + tokens[i + 1].content.strip())
                for i, t in enumerate(tokens)
                if t.type == "heading_open" and t.level == 0]
    sections: dict[str, list[list[str]]] = {}
    for pos, (index, depth, label) in enumerate(headings):
        if depth not in (2, 3):
            continue
        end = next((j for j, d, _ in headings[pos + 1:] if d <= depth), len(tokens))
        blocks = []
        for j in range(index + 3, end):
            token = tokens[j]
            if token.type != "inline" or tokens[j - 1].type == "heading_open":
                continue
            children = token.children or []
            # Raw inline HTML may contain hidden content. Conservatively require
            # an excerpt in ordinary Markdown prose instead of interpreting CSS.
            if any(c.type == "html_inline" for c in children):
                continue
            visible = "".join(c.content if c.type in ("text", "code_inline") else
                              " " if c.type in ("softbreak", "hardbreak") else ""
                              for c in children)
            if visible.strip():
                blocks.append(_normalize_anchor(visible))
        sections.setdefault(label, []).append(blocks)
    return sections


def check_fiche(md_path: Path, root: Path, catalog: set[str] | dict[str, dict], schema, *, require_source_proof: bool = False) -> dict:
    """Retourne {slug, status (PASS|WARN|FAIL), fails[], warns[]}."""
    if require_source_proof:
        if not isinstance(catalog, dict):
            raise ValueError("source proof requires the full source catalog")
        if schema is None or Draft202012Validator is None:
            raise RuntimeError("source proof schema validation unavailable")
        spec = importlib.util.spec_from_file_location(
            "_coverage_page_proof", Path(__file__).with_name("gen_coverage_map.py"))
        page_proof = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(page_proof)
    slug = md_path.stem
    fails: list[str] = []
    warns: list[str] = []
    fm, body = _split_md(md_path.read_text(encoding="utf-8"))
    sections = _prose_sections(body)
    h2 = {s for s in sections if s.startswith("## ")}
    valid_sections = set(sections)
    cov_path = root / "proposals" / "_coverage" / f"{slug}.coverage.yaml"

    if not cov_path.is_file():
        # Une fiche sans claim H2 (rare) n'a rien à couvrir ; sinon trou de structure.
        if h2:
            warns.append(
                f"coverage_map_absente: aucune {cov_path.relative_to(root)} "
                f"(la fiche a {len(h2)} sections H2 sourçables → dim A du score = 0)"
            )
        if require_source_proof:
            fails.append("proof_coverage_missing: no claim-to-source evidence available for promotion")
        status = "FAIL" if fails else ("WARN" if warns else "PASS")
        return {"slug": slug, "status": status, "fails": fails, "warns": warns,
                "coverage_entries": 0, "h2_sections": len(h2)}

    try:
        cov = yaml.safe_load(cov_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        fails.append(f"coverage_yaml_invalide: {e}")
        return {"slug": slug, "status": "FAIL", "fails": fails, "warns": warns,
                "coverage_entries": 0, "h2_sections": len(h2)}

    # 2. Schéma
    if schema is not None and Draft202012Validator is not None:
        for err in Draft202012Validator(schema).iter_errors(cov):
            loc = "/".join(str(p) for p in err.path) or "(racine)"
            fails.append(f"schema:{loc}: {err.message}")

    entries = cov.get("coverage_entries") or []

    if cov.get("fiche") and cov["fiche"] != slug:
        fails.append(f"fiche_mismatch: coverage.fiche='{cov['fiche']}' ≠ slug '{slug}'")

    if not entries and require_source_proof:
        fails.append("proof_coverage_empty: no claim-to-source evidence available for promotion")
    if not entries:
        warns.append("coverage_entries_vide: aucune preuve claim↔source (suspect, schéma §coverage_entries)")

    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            fails.append(f"entry[{i}]: entrée non-objet")
            continue
        # 3. FK strict source-catalog
        sslug = e.get("source_slug")
        if sslug and sslug not in catalog:
            fails.append(f"entry[{i}].source_slug='{sslug}' absent de _meta/source-catalog.yaml (FK, ADR-089 §3)")
        if require_source_proof:
            reasons = []
            if e.get("source_status") not in {"captured", "verified"}:
                reasons.append("source_pending")
            source = catalog.get(sslug) or {}
            if source.get("status") != "active" or not page_proof.is_page_proven(source):
                reasons.append("page_not_archived")
            raw_ref = source.get("raw_ref") or {}
            digest = raw_ref.get("expected_sha256")
            if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                reasons.append("archive_hash_missing_or_invalid")
            anchor = e.get("text_anchor")
            if not isinstance(anchor, str) or not _normalize_anchor(anchor):
                reasons.append("claim_anchor_missing")
            if reasons:
                fails.append(
                    f"proof_unavailable:claim_id={e.get('claim_id')}:source_slug={sslug}:"
                    + ",".join(reasons))
        # 4. Ancrage section ↔ H2 réel
        sec = e.get("section")
        if sec and sec not in valid_sections:
            fails.append(f"entry[{i}].section='{sec}' ne correspond à aucun H2/H3 de la fiche")
        elif sec and len(sections[sec]) != 1:
            fails.append(f"entry[{i}].section='{sec}' ambiguë: titre répété")
        elif "text_anchor" in e and sec in sections:
            anchor = e["text_anchor"]
            normalized = _normalize_anchor(anchor) if isinstance(anchor, str) else ""
            if not normalized or not any(normalized in block for block in sections[sec][0]):
                fails.append(
                    f"entry[{i}].text_anchor absent de la prose de '{sec}' "
                    f"(claim_id={e.get('claim_id')})"
                )

    status = "FAIL" if fails else ("WARN" if warns else "PASS")
    return {"slug": slug, "status": status, "fails": fails, "warns": warns,
            "coverage_entries": len(entries), "h2_sections": len(h2)}


def collect_targets(args, root: Path) -> list[Path]:
    if args.all:
        return sorted(p for p in (root / "proposals").glob("*.md") if not p.name.startswith("_"))
    out = []
    for f in args.files:
        p = Path(f)
        if not p.is_absolute():
            p = root / f
        out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Validateur coverage-map (ADR-089, report-only par défaut).")
    ap.add_argument("files", nargs="*", help="proposals/<slug>.md à vérifier")
    ap.add_argument("--all", action="store_true", help="scanner toutes les proposals/*.md")
    ap.add_argument("--wiki-root", default=None, help="racine repo wiki (auto-détectée sinon)")
    ap.add_argument("--strict", action="store_true",
                    help="ENFORCEMENT : exit 1 si FAIL (gelé jusqu'à ratification ADR-089).")
    ap.add_argument("--warn-as-fail", action="store_true", help="traiter les WARN comme des FAIL (--strict).")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    if not args.all and not args.files:
        ap.error("préciser --all ou des fichiers")

    root = Path(args.wiki_root).resolve() if args.wiki_root else _repo_root(Path(args.files[0]) if args.files else Path.cwd())
    if not (root / "_meta" / "source-catalog.yaml").is_file():
        print(f"ERREUR: racine wiki introuvable depuis {root}", file=sys.stderr)
        return 2

    catalog = _load_catalog_slugs(root)
    schema = _load_schema(root)
    if schema is None or Draft202012Validator is None:
        print("WARN: schéma coverage-map ou jsonschema absent — validation schéma désactivée (dégradé, non silencieux)",
              file=sys.stderr)

    results = [check_fiche(p, root, catalog, schema) for p in collect_targets(args, root) if p.is_file()]

    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_warn = sum(1 for r in results if r["status"] == "WARN")
    n_fail = sum(1 for r in results if r["status"] == "FAIL")

    if args.format == "json":
        print(json.dumps({"pass": n_pass, "warn": n_warn, "fail": n_fail, "results": results},
                         ensure_ascii=False, indent=2))
    else:
        for r in results:
            for f in r["fails"]:
                print(f"FAIL {r['slug']}: {f}")
            for w in r["warns"]:
                print(f"WARN {r['slug']}: {w}")
            if r["status"] == "PASS":
                print(f"PASS {r['slug']} ({r['coverage_entries']} entries / {r['h2_sections']} H2)")
        print(f"\n{n_pass} PASS — {n_fail} FAIL — {n_warn} WARN  (report-only ; enforcement gelé jusqu'à ADR-089)")

    enforce = args.strict or args.warn_as_fail
    if enforce and (n_fail or (args.warn_as_fail and n_warn)):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
