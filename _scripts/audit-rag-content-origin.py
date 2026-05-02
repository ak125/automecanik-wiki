#!/usr/bin/env python3
"""Étape 3 du plan v3 (rag → wiki SoT) — Audit read-only de
`automecanik-rag/knowledge/<7 cats>/*.md`.

Produit un JSON de classification dans `_audit/rag-content-classification-<date>.json`
avec, pour chaque fiche :
- chemin source
- entity_type (déduit du dossier parent)
- slug
- last_enriched_by (lifecycle.last_enriched_by, ou null si absent)
- origin_class : `human_curated` | `auto_generated` | `ambiguous`
- regenerable : true|false (true si auto_generated)

Aucune modification — pure analyse, sortie JSON.

Référence : plan v3 §Étape 3.
"""
from __future__ import annotations
import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

CATEGORIES = ["gammes", "vehicles", "constructeurs", "faq", "policies", "guides", "reference", "diagnostic"]


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 5 :]


def classify_origin(last_enriched_by: str | None) -> tuple[str, bool]:
    """Returns (origin_class, regenerable)."""
    if not last_enriched_by:
        return ("ambiguous", False)
    val = str(last_enriched_by).strip()
    if val.startswith("script:") or val.startswith("r7-") or val.startswith("script_"):
        return ("auto_generated", True)
    if val.startswith("skill:") or val.startswith("human:") or val.startswith("@"):
        return ("human_curated", False)
    return ("ambiguous", False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--rag-knowledge-root",
        default="/opt/automecanik/rag/knowledge",
        help="Path to automecanik-rag/knowledge clone (default: %(default)s)",
    )
    ap.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: _audit/rag-content-classification-<YYYY-MM-DD>.json relative to script repo)",
    )
    args = ap.parse_args()

    rag_root = Path(args.rag_knowledge_root).resolve()
    if not rag_root.exists():
        sys.stderr.write(f"FATAL: rag knowledge root not found: {rag_root}\n")
        return 2

    repo_root = Path(__file__).resolve().parent.parent
    if args.output:
        out_path = Path(args.output).resolve()
    else:
        today = datetime.now(timezone.utc).date().isoformat()
        out_path = repo_root / "_audit" / f"rag-content-classification-{today}.json"

    fiches: list[dict] = []
    by_origin: dict[str, list[dict]] = defaultdict(list)
    counts_by_class: Counter = Counter()
    counts_by_cat: Counter = Counter()
    parse_failures: list[dict] = []

    for cat in CATEGORIES:
        cat_dir = rag_root / cat
        if not cat_dir.is_dir():
            continue
        for md_path in sorted(cat_dir.glob("*.md")):
            counts_by_cat[cat] += 1
            slug = md_path.stem
            try:
                text = md_path.read_text(encoding="utf-8")
            except Exception as e:
                parse_failures.append({"path": str(md_path.relative_to(rag_root)), "error": f"read: {e}"})
                continue
            fm_yaml, _ = split_frontmatter(text)
            if not fm_yaml:
                parse_failures.append(
                    {"path": str(md_path.relative_to(rag_root)), "error": "no frontmatter"}
                )
                origin_class, regenerable = "ambiguous", False
                last_enriched_by = None
                category_value = None
            else:
                try:
                    fm = yaml.safe_load(fm_yaml) or {}
                except yaml.YAMLError as e:
                    parse_failures.append(
                        {"path": str(md_path.relative_to(rag_root)), "error": f"yaml: {e}"}
                    )
                    fm = {}
                lifecycle = fm.get("lifecycle") or {}
                if not isinstance(lifecycle, dict):
                    lifecycle = {}
                last_enriched_by = lifecycle.get("last_enriched_by")
                category_value = fm.get("category") or fm.get("source_type")
                origin_class, regenerable = classify_origin(last_enriched_by)

            entry = {
                "path": str(md_path.relative_to(rag_root.parent)),  # e.g. "knowledge/gammes/foo.md"
                "category_dir": cat,
                "category_field": category_value,
                "slug": slug,
                "last_enriched_by": last_enriched_by,
                "origin_class": origin_class,
                "regenerable": regenerable,
            }
            fiches.append(entry)
            by_origin[str(last_enriched_by or "<missing>")].append(
                {"path": entry["path"], "slug": slug, "category": cat}
            )
            counts_by_class[origin_class] += 1

    # Detect cross-category slug collisions
    slug_to_cats: dict[str, set[str]] = defaultdict(set)
    for f in fiches:
        slug_to_cats[f["slug"]].add(f["category_dir"])
    collisions = {s: sorted(cs) for s, cs in slug_to_cats.items() if len(cs) > 1}

    out = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "source_repo": "automecanik-rag",
        "source_root": str(rag_root),
        "categories_scanned": list(counts_by_cat.keys()),
        "total_fiches": len(fiches),
        "counts_by_category": dict(counts_by_cat),
        "counts_by_class": dict(counts_by_class),
        "by_origin_summary": {k: len(v) for k, v in by_origin.items()},
        "collisions_cross_category": collisions,
        "parse_failures_count": len(parse_failures),
        "parse_failures": parse_failures,
        "fiches": fiches,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=False) + "\n")

    print(f"AUDIT WRITTEN  {out_path.relative_to(repo_root)}")
    print(f"  total_fiches: {len(fiches)}")
    print(f"  counts_by_class: {dict(counts_by_class)}")
    print(f"  collisions: {len(collisions)}")
    print(f"  parse_failures: {len(parse_failures)}")
    print(f"  by_origin (top 10):")
    for k, v in sorted(by_origin.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"    {k}: {len(v)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
