#!/usr/bin/env python3
"""Validate frontmatter YAML of a wiki/proposals Markdown file against schema v1.0.

Usage:
    validate-frontmatter.py <file>...
    validate-frontmatter.py --all       # scan proposals/ and wiki/

Exit:
    0 — all files valid
    1 — at least one file invalid
    2 — script error (missing dep, schema not found)

Reference: plan rev 6 §G9-A, _meta/schema/frontmatter.schema.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("FATAL: PyYAML required (pip install pyyaml)\n")
    sys.exit(2)

try:
    import jsonschema
    from jsonschema import Draft202012Validator, ValidationError
except ImportError:
    sys.stderr.write("FATAL: jsonschema>=4.18 required (pip install jsonschema)\n")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "_meta" / "schema" / "frontmatter.schema.json"


def split_frontmatter(text: str) -> tuple[str, str]:
    """Split YAML frontmatter and body. Returns (frontmatter_yaml, body)."""
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 5 :]


def load_schema() -> dict:
    if not SCHEMA_PATH.exists():
        sys.stderr.write(f"FATAL: schema not found: {SCHEMA_PATH}\n")
        sys.exit(2)
    return json.loads(SCHEMA_PATH.read_text())


def validate_file(path: Path, validator: Draft202012Validator) -> list[str]:
    """Return list of error strings; empty list = valid."""
    text = path.read_text()
    fm_yaml, _ = split_frontmatter(text)
    if not fm_yaml:
        return [f"{path}: no YAML frontmatter found"]
    try:
        fm = yaml.safe_load(fm_yaml)
    except yaml.YAMLError as e:
        return [f"{path}: YAML parse error: {e}"]
    if not isinstance(fm, dict):
        return [f"{path}: frontmatter is not a YAML mapping"]
    errors = sorted(validator.iter_errors(fm), key=lambda e: list(e.path))
    if not errors:
        return []
    return [
        f"{path}: {'/'.join(str(p) for p in err.path) or '<root>'}: {err.message}"
        for err in errors
    ]


def gather_files(args) -> list[Path]:
    if args.all:
        roots = [REPO_ROOT / "proposals", REPO_ROOT / "wiki"]
        files: list[Path] = []
        for root in roots:
            if root.exists():
                files.extend(
                    p
                    for p in root.rglob("*.md")
                    if not any(part.startswith("_") for part in p.relative_to(root).parts)
                )
        return files
    return [Path(p).resolve() for p in args.files]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", help="Markdown files to validate")
    ap.add_argument("--all", action="store_true", help="Scan proposals/ and wiki/")
    ap.add_argument("--quiet", action="store_true", help="Print only failures")
    args = ap.parse_args()

    files = gather_files(args)
    if not files:
        sys.stderr.write("No files to validate\n")
        return 0

    schema = load_schema()
    validator = Draft202012Validator(schema)

    failed = 0
    for f in files:
        errors = validate_file(f, validator)
        if errors:
            failed += 1
            for e in errors:
                print(f"FAIL {e}")
        elif not args.quiet:
            print(f"PASS {f}")
    print(
        f"\n{len(files) - failed}/{len(files)} valid"
        + (f" — {failed} failed" if failed else "")
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
