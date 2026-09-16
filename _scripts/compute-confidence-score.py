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


def filled_sections(body: str, required: list[str]) -> list[str]:
    headings = list(H2_RE.finditer(body))
    filled = []
    for sec in required:
        sec_low = sec.lower()
        for index, heading in enumerate(headings):
            title = heading.group(1).lower()
            if sec_low not in title and title not in sec_low:
                continue
            # Only the body after the COMPLETE heading contributes substance.
            # Matching the first eight title characters counted the remaining
            # title as content and let empty sections pass the 20-char floor.
            end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
            section_body = body[heading.end():end]
            if len(re.sub(r"\s+", "", section_body)) >= 20:
                filled.append(sec)
                break
    return filled


def count_filled_sections(body: str, required: list[str]) -> int:
    return len(filled_sections(body, required))


def link_details(body: str, wiki_root: Path) -> dict:
    """Resolve the existing slug convention within the canonical wiki directory."""
    matches = WIKILINK_RE.findall(body)
    existing_slugs = {p.stem for p in wiki_root.rglob("*.md")} if matches and wiki_root.exists() else set()
    unresolved = [slug.strip() for slug in matches if slug.strip() not in existing_slugs]
    return {"resolved": len(matches) - len(unresolved), "total": len(matches),
            "unresolved": unresolved}


def count_links(body: str, wiki_root: Path) -> tuple[int, int]:
    details = link_details(body, wiki_root)
    return details["resolved"], details["total"]


def compute_score_details(fm: dict, body: str, wiki_root: Path) -> dict:
    """Explain the existing formula, without asserting factual or SEO quality.

    Unmatched headings describe this lexical detector, not proven missing facts.
    Defaulted confidence is metadata, not evidence to upgrade a source to high.
    `wiki_root` is the canonical wiki/ directory (same contract as the CLI).
    """
    refs = fm.get("source_refs") or []
    nums = [CONFIDENCE_NUMERIC.get(r.get("confidence", "medium"), 0.6)
            for r in refs if isinstance(r, dict)]
    src_score = mean(nums) if nums else 0.0
    defaulted = [i for i, r in enumerate(refs) if isinstance(r, dict)
                 and r.get("confidence") not in CONFIDENCE_NUMERIC]
    required = SECTIONS_REQUIRED.get(fm.get("entity_type", ""), [])
    filled = filled_sections(body, required)
    sec_ratio = len(filled) / len(required) if required else 0.0
    links = link_details(body, wiki_root)
    link_ratio = links["resolved"] / max(links["total"], 1)
    kinds = {r.get("kind") for r in refs if isinstance(r, dict)}
    diversity = 1.0 if len(kinds) >= 2 else 0.0
    components = {
        "sources": {"weight": 0.40, "ratio": src_score,
                    "reference_count": len(nums), "defaulted_confidence_indices": defaulted},
        "sections": {"weight": 0.30, "ratio": sec_ratio, "required": required,
                     "filled": filled, "unmatched_required": [s for s in required if s not in filled]},
        "internal_links": {"weight": 0.20, "ratio": link_ratio, **links},
        "source_kinds": {"weight": 0.10, "ratio": diversity, "distinct_count": len(kinds)},
    }
    for component in components.values():
        component["points"] = round(component["weight"] * component["ratio"], 6)
    # Round only the final sum, exactly like the original public scalar scorer.
    value = sum(c["weight"] * c["ratio"] for c in components.values())
    return {"score": round(value, 2), "components": components,
            "scope": "metadata_structure_proxy_not_factual_or_seo_validation"}


def compute_score(fm: dict, body: str, wiki_root: Path) -> float:
    return compute_score_details(fm, body, wiki_root)["score"]


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
