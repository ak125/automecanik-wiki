#!/usr/bin/env python3
"""Compute or check confidence_score per plan rev 6 §5.1.1 formula.

Formula:
    confidence_score =
        0.40 × mean(source_refs[].confidence_numeric)   # high=1.0, medium=0.6, low=0.3
      + 0.30 × (sections_remplies / sections_obligatoires)
      + 0.20 × (links_internes_resolus / max(links_internes_total, 1))
      + 0.10 × (1.0 if >=2 source_refs with distinct kinds else 0.0)

Modes:
    --check (default) — verify written value matches formula. FAIL if author cheated.
    --fix             — rewrite frontmatter confidence_score in place.

Usage:
    compute-confidence-score.py --check <file>...
    compute-confidence-score.py --fix <file>...
    compute-confidence-score.py --check --all

Exit:
    0 — all match (check) or all rewritten (fix)
    1 — mismatch detected (check) or write error (fix)
    2 — script error

Reference: plan rev 6 §5.1.1
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from statistics import mean

try:
    import yaml
except ImportError:
    sys.stderr.write("FATAL: PyYAML required\n")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "_meta" / "templates"

CONFIDENCE_NUMERIC = {"high": 1.0, "medium": 0.6, "low": 0.3}

SECTIONS_REQUIRED = {
    "gamme": ["Définition", "Fonctionnement", "Symptômes d'usure", "Choix selon véhicule", "FAQ"],
    "vehicle": ["Identité", "Spécificités", "Pièces fréquentes", "FAQ"],
    "constructeur": ["Identité", "Modèles principaux", "Spécificités techniques", "FAQ"],
    "support": ["Question", "Réponse", "Cas particuliers", "Liens internes"],
    "diagnostic": ["Symptôme", "Causes possibles", "Vérifications", "Renvoi", "safety_advisory"],
}

H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
TOLERANCE = 0.01


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 5 :]


def count_filled_sections(body: str, required: list[str]) -> int:
    headings = [h.lower() for h in H2_RE.findall(body)]
    filled = 0
    for sec in required:
        sec_low = sec.lower()
        if any(sec_low in h or h in sec_low for h in headings):
            # Check section has content (≥ 20 non-whitespace chars after heading)
            pattern = re.compile(rf"^##\s+.*{re.escape(sec[:8])}", re.MULTILINE | re.IGNORECASE)
            m = pattern.search(body)
            if m:
                start = m.end()
                next_h2 = H2_RE.search(body, start)
                section_body = body[start : next_h2.start() if next_h2 else len(body)]
                if len(re.sub(r"\s+", "", section_body)) >= 20:
                    filled += 1
    return filled


def count_links(body: str, wiki_root: Path) -> tuple[int, int]:
    """Returns (resolved, total)."""
    matches = WIKILINK_RE.findall(body)
    if not matches:
        return 0, 0
    resolved = 0
    if not wiki_root.exists():
        return 0, len(matches)
    existing_slugs = {p.stem for p in wiki_root.rglob("*.md")}
    for slug in matches:
        if slug.strip() in existing_slugs:
            resolved += 1
    return resolved, len(matches)


def compute_score(fm: dict, body: str, wiki_root: Path) -> float:
    refs = fm.get("source_refs") or []
    # Component 1: source confidence average
    nums = [
        CONFIDENCE_NUMERIC.get(r.get("confidence", "medium"), 0.6)
        for r in refs
        if isinstance(r, dict)
    ]
    src_score = mean(nums) if nums else 0.0

    # Component 2: sections filled ratio
    et = fm.get("entity_type", "")
    required = SECTIONS_REQUIRED.get(et, [])
    if required:
        filled = count_filled_sections(body, required)
        sec_ratio = filled / len(required)
    else:
        sec_ratio = 0.0

    # Component 3: internal links resolved ratio
    resolved, total = count_links(body, wiki_root)
    link_ratio = resolved / max(total, 1)

    # Component 4: source diversity bonus
    kinds = {r.get("kind") for r in refs if isinstance(r, dict)}
    diversity = 1.0 if len(kinds) >= 2 else 0.0

    score = 0.40 * src_score + 0.30 * sec_ratio + 0.20 * link_ratio + 0.10 * diversity
    return round(score, 2)


def process_file(path: Path, mode: str, wiki_root: Path) -> bool:
    """Returns True if PASS (check) or written (fix); False on failure."""
    text = path.read_text()
    fm_yaml, body = split_frontmatter(text)
    if not fm_yaml:
        print(f"FAIL {path}: no frontmatter")
        return False
    try:
        fm = yaml.safe_load(fm_yaml)
    except yaml.YAMLError as e:
        print(f"FAIL {path}: YAML parse error: {e}")
        return False
    if not isinstance(fm, dict):
        print(f"FAIL {path}: frontmatter not a mapping")
        return False

    expected = compute_score(fm, body, wiki_root)
    written = fm.get("confidence_score")

    if mode == "check":
        if written is None:
            print(f"FAIL {path}: confidence_score missing (expected {expected:.2f})")
            return False
        try:
            written_f = float(written)
        except (TypeError, ValueError):
            print(f"FAIL {path}: confidence_score not numeric: {written!r}")
            return False
        if abs(written_f - expected) > TOLERANCE:
            print(
                f"FAIL {path}: confidence_score mismatch — written={written_f:.2f} expected={expected:.2f}"
            )
            return False
        print(f"PASS {path}: confidence_score={written_f:.2f}")
        return True

    # mode == "fix"
    if "confidence_score" in fm and abs(float(fm.get("confidence_score") or 0) - expected) <= TOLERANCE:
        print(f"SKIP {path}: already correct ({expected:.2f})")
        return True
    new_fm_lines = []
    fm_lines = fm_yaml.split("\n")
    found = False
    for line in fm_lines:
        if line.lstrip().startswith("confidence_score:"):
            indent = line[: len(line) - len(line.lstrip())]
            new_fm_lines.append(f"{indent}confidence_score: {expected:.2f}")
            found = True
        else:
            new_fm_lines.append(line)
    if not found:
        # insert before first blank line or at end of frontmatter
        new_fm_lines = fm_lines + [f"confidence_score: {expected:.2f}"]
    new_text = "---\n" + "\n".join(new_fm_lines) + "\n---\n" + body
    path.write_text(new_text)
    print(f"FIX  {path}: confidence_score={expected:.2f}")
    return True


def gather_files(args) -> list[Path]:
    if args.all:
        roots = [REPO_ROOT / "proposals", REPO_ROOT / "wiki"]
        files: list[Path] = []
        for root in roots:
            if root.exists():
                files.extend(p for p in root.rglob("*.md") if not p.name.startswith("_"))
        return files
    return [Path(p).resolve() for p in args.files]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="Verify (default mode at pre-commit)")
    g.add_argument("--fix", action="store_true", help="Rewrite frontmatter")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    mode = "fix" if args.fix else "check"
    files = gather_files(args)
    if not files:
        sys.stderr.write("No files to process\n")
        return 0

    wiki_root = REPO_ROOT / "wiki"
    failed = 0
    for f in files:
        if not process_file(f, mode, wiki_root):
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
