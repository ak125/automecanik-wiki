#!/usr/bin/env python3
"""Compute or check confidence_score_computed per diagnostic_relations[] entry.

Formula (ADR-033 §C8 advanced) — pondérée par source_type :

    score = 0
    +2 if any source_type ∈ {oem_manual, oem_workshop}
    +1 if any source_type ∈ {brochure, tecdoc_official, parts_feed_certified, normative_standard}
    +1 if len(sources) >= 2
    +1 if len(distinct source_types) >= 2

    confidence_score_computed = min(score, 5) / 5.0   # normalisé 0-1

Idempotent : recalcul sur même contenu = même score.

Modes :
    --check (défaut) — vérifie cohérence, FAIL si valeur écrite ≠ valeur calculée
    --fix             — réécrit la valeur en place

Usage:
    compute-symptom-confidence.py --check <file>...
    compute-symptom-confidence.py --fix <file>...
    compute-symptom-confidence.py --check --all

Exit:
    0 — all match (check) or all rewritten (fix)
    1 — mismatch detected (check) or write error (fix)
    2 — script error

Reference: plan rev 6 §C8, ADR-033 §D1, _meta/source-policy.md §9.1
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("FATAL: PyYAML required\n")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_CATALOG = REPO_ROOT / "_meta" / "source-catalog.yaml"

OEM_TYPES = {"oem_manual", "oem_workshop"}
SECONDARY_TYPES = {"brochure", "tecdoc_official", "parts_feed_certified", "normative_standard"}

TOLERANCE = 0.01


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 5 :]


def load_source_catalog() -> dict[str, dict]:
    if not SOURCE_CATALOG.exists():
        return {}
    try:
        data = yaml.safe_load(SOURCE_CATALOG.read_text())
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {s["slug"]: s for s in data.get("sources", []) if isinstance(s, dict) and "slug" in s}


def compute_score(sources: list[str], catalog: dict[str, dict]) -> float:
    types: list[str] = []
    for s in sources:
        base = re.sub(r"_p\d+$", "", s)
        entry = catalog.get(base) or catalog.get(s) or {}
        t = entry.get("type")
        if t:
            types.append(t)
    score = 0
    if any(t in OEM_TYPES for t in types):
        score += 2
    if any(t in SECONDARY_TYPES for t in types):
        score += 1
    if len(sources) >= 2:
        score += 1
    if len(set(types)) >= 2:
        score += 1
    return round(min(score, 5) / 5.0, 2)


def process_file(path: Path, mode: str, catalog: dict[str, dict]) -> bool:
    text = path.read_text()
    fm_yaml, body = split_frontmatter(text)
    if not fm_yaml:
        print(f"SKIP {path}: no frontmatter")
        return True
    try:
        fm = yaml.safe_load(fm_yaml) or {}
    except yaml.YAMLError as e:
        print(f"FAIL {path}: YAML parse error: {e}")
        return False
    if not isinstance(fm, dict):
        return True

    relations = fm.get("diagnostic_relations") or []
    if not isinstance(relations, list) or not relations:
        return True  # no relations = nothing to compute

    failed = False
    changed = False
    for i, r in enumerate(relations):
        if not isinstance(r, dict):
            continue
        sources = r.get("sources") or []
        ev = r.get("evidence") or {}
        if not isinstance(ev, dict):
            continue
        expected = compute_score(sources, catalog)
        written = ev.get("confidence_score_computed")

        if mode == "check":
            if written is None:
                print(f"INFO {path}: relation[{i}] confidence_score_computed missing (expected {expected:.2f})")
                continue
            try:
                w = float(written)
            except (TypeError, ValueError):
                print(f"FAIL {path}: relation[{i}] confidence_score_computed not numeric: {written!r}")
                failed = True
                continue
            if abs(w - expected) > TOLERANCE:
                print(
                    f"FAIL {path}: relation[{i}] confidence_score_computed mismatch — written={w:.2f} expected={expected:.2f}"
                )
                failed = True
            else:
                print(f"PASS {path}: relation[{i}] symptom={r.get('symptom_slug', '?')} score={w:.2f}")
        else:  # fix
            if written is None or abs(float(written or 0) - expected) > TOLERANCE:
                ev["confidence_score_computed"] = expected
                r["evidence"] = ev
                relations[i] = r
                changed = True
                print(f"FIX  {path}: relation[{i}] symptom={r.get('symptom_slug', '?')} → score={expected:.2f}")
            else:
                print(f"SKIP {path}: relation[{i}] already correct ({expected:.2f})")

    if mode == "fix" and changed:
        # Rewrite frontmatter
        fm["diagnostic_relations"] = relations
        new_fm_yaml = yaml.safe_dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
        new_text = "---\n" + new_fm_yaml + "---\n" + body
        path.write_text(new_text)

    return not failed


def _is_meta_path(p: Path) -> bool:
    """D19 convention: skip files whose name OR any parent component starts with `_`."""
    try:
        rel = p.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        return False
    return any(part.startswith("_") for part in rel.parts)


def gather_files(args) -> list[Path]:
    if args.all:
        roots = [REPO_ROOT / "proposals", REPO_ROOT / "wiki"]
        files: list[Path] = []
        for root in roots:
            if root.exists():
                files.extend(p for p in root.rglob("*.md") if not _is_meta_path(p))
        return files
    return [p for p in (Path(f).resolve() for f in args.files) if not _is_meta_path(p)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="Verify (default at pre-commit)")
    g.add_argument("--fix", action="store_true", help="Rewrite frontmatter")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    mode = "fix" if args.fix else "check"
    files = gather_files(args)
    if not files:
        sys.stderr.write("No files to process\n")
        return 0

    catalog = load_source_catalog()
    failed = 0
    for f in files:
        if not process_file(f, mode, catalog):
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
