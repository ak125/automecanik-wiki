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
    --explain         — print JSON arithmetic and section evidence, without writes.

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
import json
import math
import re
import sys
import unicodedata
from importlib.metadata import version
from pathlib import Path
from statistics import mean

from markdown_it import MarkdownIt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from editorial_sections import GAMME_SCORING_ALIASES

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

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
TOLERANCE = 0.01


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 5 :]


def _heading_key(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).replace("’", "'").casefold().split())


def parse_sections(body: str) -> list[dict]:
    """Read top-level H2 sections; never render HTML or execute source markup."""
    if version("markdown-it-py") != "3.0.0" or version("mdurl") != "0.1.2":
        raise ValueError("score_parser_version_unsupported")
    tokens = MarkdownIt("commonmark").enable("table").parse(body)
    sections, current = [], None
    for i, token in enumerate(tokens):
        if token.type == "heading_open":
            # H1/H2 close the previous section. Nested quoted/list headings
            # are not document sections. H3+ titles never supply prose length.
            if token.level == 0 and token.tag in ("h1", "h2"):
                current = None
                if token.tag == "h2":
                    inline = tokens[i + 1]
                    if any(child.type == "html_inline" for child in (inline.children or [])):
                        continue
                    heading = "".join(child.content for child in (inline.children or [])
                                      if child.type in ("text", "code_inline"))
                    current = {"heading": heading, "text_chars": 0}
                    sections.append(current)
            continue
        if token.type != "inline" or current is None:
            continue
        if i and tokens[i - 1].type == "heading_open":
            continue
        if any(child.type == "html_inline" for child in (token.children or [])):
            continue
        # Comments/HTML blocks, fenced and indented code are distinct tokens.
        # Image alternative text and inline code are not documentary prose.
        text = "".join(child.content for child in (token.children or [])
                       if child.type == "text")
        current["text_chars"] += len(re.sub(r"\s+", "", text))
    return sections


def section_evidence(body: str, required: list[str], aliases=None) -> dict:
    sections = parse_sections(body)
    aliases = aliases or {}
    matches, owners = {}, {}
    for criterion in required:
        names = (criterion, *aliases.get(criterion, ()))
        normalized = {_heading_key(name) for name in names}
        for key in normalized:
            if key in owners and owners[key] != criterion:
                raise ValueError("score_section_alias_collision")
            owners[key] = criterion
        matches[criterion] = [s["heading"] for s in sections
                              if _heading_key(s["heading"]) in normalized and s["text_chars"] >= 20]
    return {"required": list(required),
            "filled": [name for name in required if matches[name]],
            "missing_or_insufficient": [name for name in required if not matches[name]],
            "observed_headings": [s["heading"] for s in sections],
            "matched_headings": matches, "matcher": "commonmark_exact_aliases_v1",
            "parser": "markdown-it-py@3.0.0", "minimum_prose_chars": 20}


def filled_section_names(body: str, required: list[str]) -> list[str]:
    return section_evidence(body, required)["filled"]


def count_filled_sections(body: str, required: list[str]) -> int:
    return len(filled_section_names(body, required))


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


def explain_score(fm: dict, body: str, wiki_root: Path) -> dict:
    """Single arithmetic implementation for scoring and read-only diagnostics.

    This legacy formula counts kinds, not independent publishers, and section
    length, not factual validity. It never establishes promotion eligibility.
    """
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
    section_details = section_evidence(body, required,
                                      GAMME_SCORING_ALIASES if et == "gamme" else None)
    filled = section_details["filled"]
    sec_ratio = len(filled) / len(required) if required else 0.0

    # Component 3: internal links resolved ratio
    resolved, total = count_links(body, wiki_root)
    link_ratio = resolved / max(total, 1)

    # Component 4: source diversity bonus
    kinds = {r.get("kind") for r in refs if isinstance(r, dict)}
    diversity = 1.0 if len(kinds) >= 2 else 0.0

    components = {
        "source_confidence": {"weight": 0.40, "value": src_score,
                              "reference_count": len(nums), "default_confidence": "medium"},
        "sections": {"weight": 0.30, "value": sec_ratio,
                     **section_details},
        "internal_links": {"weight": 0.20, "value": link_ratio,
                           "resolved": resolved, "total": total},
        "source_kind_diversity": {"weight": 0.10, "value": diversity,
                                  "distinct_kind_count": len(kinds),
                                  "measures_publisher_independence": False},
    }
    # Preserve the existing order and full precision before the final rounding.
    contributions = []
    for component in components.values():
        contribution = component["weight"] * component["value"]
        contributions.append(contribution)
        component["contribution"] = round(contribution, 6)
    return {"schema_version": "1.0.0", "scope": "formula_only_not_promotion",
            "engine": "legacy", "score": round(sum(contributions), 2),
            "components": components}


def compute_score(fm: dict, body: str, wiki_root: Path) -> float:
    return explain_score(fm, body, wiki_root)["score"]


def _finite_score(value) -> float:
    if isinstance(value, bool):
        raise ValueError("score must be finite and numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("score must be finite and numeric")
    return result


def explain_files(files: list[Path], wiki_root: Path) -> int:
    results, errors = [], []
    for path in files:
        try:
            fm_yaml, body = split_frontmatter(path.read_text(encoding="utf-8"))
            fm = yaml.safe_load(fm_yaml)
            if not isinstance(fm, dict):
                raise ValueError("invalid frontmatter")
            report = explain_score(fm, body, wiki_root)
            declared = fm.get("confidence_score")
            try:
                declared = _finite_score(declared)
                status = "matches" if abs(declared - report["score"]) <= TOLERANCE else "mismatch"
            except (TypeError, ValueError, OverflowError):
                status = "missing" if "confidence_score" not in fm else "invalid"
                declared = None
            results.append({"path": str(path), **report, "declared_score": declared,
                            "declared_score_status": status})
        except (OSError, UnicodeError, yaml.YAMLError, TypeError, ValueError, AttributeError):
            errors.append({"path": str(path), "code": "score_explanation_unavailable"})
    print(json.dumps({"schema_version": "1.0.0", "results": results, "errors": errors},
                     ensure_ascii=False, allow_nan=False))
    return 1 if errors else 0


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
            written_f = _finite_score(written)
        except (TypeError, ValueError, OverflowError):
            print(f"FAIL {path}: confidence_score must be finite and numeric")
            return False
        if abs(written_f - expected) > TOLERANCE:
            print(
                f"FAIL {path}: confidence_score mismatch — written={written_f:.2f} expected={expected:.2f}"
            )
            return False
        print(f"PASS {path}: confidence_score={written_f:.2f}")
        return True

    # mode == "fix"
    try:
        already_matches = abs(_finite_score(written) - expected) <= TOLERANCE
    except (TypeError, ValueError, OverflowError):
        already_matches = False
    if already_matches:
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
    g.add_argument("--explain", action="store_true", help="Explain the formula as JSON, without writes")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    mode = "fix" if args.fix else "check"
    files = gather_files(args)
    wiki_root = REPO_ROOT / "wiki"
    if args.explain:
        return explain_files(files, wiki_root)
    if not files:
        sys.stderr.write("No files to process\n")
        return 0

    failed = 0
    for f in files:
        if not process_file(f, mode, wiki_root):
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
