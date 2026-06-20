#!/usr/bin/env python3
"""Compare a proposal fiche's CURRENT version against its git PREDECESSOR.

Goal: a rebuilt fiche must never silently overwrite / get promoted without
proof it is at least as good as the version it replaces. This is the
"score-and-compare-before-overwrite" gate.

The verdict is SCORE-BASED (the canonical confidence_score, reused — never
reinvented). The new version's quality-gate status is also reported for
transparency. Phase A is REPORT-ONLY: exit 0 always, unless
--fail-on-regression is passed explicitly (kept off until the formula
re-calibration + ADR — see governance notes in the wiki gate plan).

Reuse, no reinvention:
- score        ← _scripts/compute-confidence-score.py : compute_score()
- gate status  ← _scripts/quality-gates.py            : run_gates()
- predecessor  ← native git (`git show <ref>:<path>`), zero baseline file

Verdict:
    NEW        no predecessor at <base> → nothing to regress against
    IMPROVED   new_score > old_score + max_regression
    NEUTRAL    |delta| within max_regression
    REGRESSED  new_score < old_score - max_regression

Usage:
    compare-proposal-versions.py <file>... [--base <ref>] [--format text|json]
                                 [--max-regression F] [--fail-on-regression]

Exit:
    0  report-only (default), or no regression when --fail-on-regression
    1  at least one REGRESSED and --fail-on-regression set
    2  script error
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent


def _load_module(name: str, filename: str):
    """Load a hyphenated sibling script (not importable directly)."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"unable to load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_confidence = _load_module("_cpv_confidence", "compute-confidence-score.py")
_gates = _load_module("_cpv_gates", "quality-gates.py")


# --- pure protocol helpers ---------------------------------------------------

def decide_verdict(old_score, new_score, max_regression: float = 0.0):
    """Score-based verdict. Returns (verdict, delta_score).

    delta_score is None when there is no predecessor. The boundary is
    exclusive on purpose: a delta of exactly ±max_regression is NEUTRAL,
    not REGRESSED/IMPROVED (only a strict move past the tolerance counts)."""
    if old_score is None:
        return ("NEW", None)
    delta = round(new_score - old_score, 4)
    if delta < -max_regression:
        return ("REGRESSED", delta)
    if delta > max_regression:
        return ("IMPROVED", delta)
    return ("NEUTRAL", delta)


def extract_category(message: str) -> str:
    """The blocked-reason category = the text before the first ':'."""
    return message.split(":", 1)[0].strip()


def diff_categories(old_messages, new_messages):
    """Returns (introduced, resolved) category lists.

    introduced = categories present in new but not old (regressions to watch).
    resolved   = categories present in old but not new (fixes).
    Kept as a tested utility for the future blocking phase."""
    old = {extract_category(m) for m in old_messages}
    new = {extract_category(m) for m in new_messages}
    return sorted(new - old), sorted(old - new)


# --- evaluation (reuse legacy score + gates) ---------------------------------

def evaluate_path(path, wiki_root) -> dict:
    """Score + quality-gate categories for a single fiche on disk."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    # Reuse the legacy robust parser (catches YAMLError + enforces dict) — never
    # hand-roll yaml.safe_load here: malformed frontmatter must degrade to an
    # empty mapping (score 0.0 + schema_invalid gate), never crash a report-only run.
    fm, body = _gates.parse_fm(text)
    score = float(_confidence.compute_score(fm, body, Path(wiki_root)))
    registry = _gates.load_registry()
    source_catalog = _gates.load_source_catalog()
    failures, warnings = _gates.run_gates(path, registry, source_catalog)
    return {
        "score": score,
        "blocked_categories": sorted({extract_category(f) for f in failures}),
        "warning_categories": sorted({extract_category(w) for w in warnings}),
    }


def compare(new_path, old_path, wiki_root, max_regression: float = 0.0) -> dict:
    """Compare new vs predecessor. Verdict is score-based; new gate status reported."""
    new_eval = evaluate_path(new_path, wiki_root)
    old_eval = evaluate_path(old_path, wiki_root) if old_path is not None else None
    old_score = old_eval["score"] if old_eval else None
    verdict, delta = decide_verdict(old_score, new_eval["score"], max_regression)
    return {
        "predecessor_found": old_eval is not None,
        "old_score": old_score,
        "new_score": new_eval["score"],
        "delta_score": delta,
        "verdict": verdict,
        "new_blocked_categories": new_eval["blocked_categories"],
        "new_warning_categories": new_eval["warning_categories"],
    }


# --- git predecessor ---------------------------------------------------------

def read_predecessor(repo_root, ref: str, relpath: str):
    """Return the text of <relpath> at git <ref>, or None.

    None covers both 'file absent at this ref' and 'ref unresolvable' — the
    caller treats either as "no predecessor" → verdict NEW (report-only, no
    false regression). CI resolves <ref> availability explicitly before calling."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{ref}:{relpath}"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout


# --- CLI ---------------------------------------------------------------------

def _format_text(r: dict) -> str:
    v = r["verdict"]
    if v == "ERROR":
        return f"ERROR     {r['target']}  ({r.get('error', 'evaluation failed')})"
    if v == "NEW":
        head = f"NEW       {r['target']}  (no predecessor at {r['base_ref']}, score={r['new_score']:.2f})"
    else:
        head = (
            f"{v:<9} {r['target']}  {r['old_score']:.2f} → {r['new_score']:.2f}"
            f"  (Δ {r['delta_score']:+.2f})"
        )
    if r["new_blocked_categories"]:
        head += f"\n          gates FAIL (new): {', '.join(r['new_blocked_categories'])}"
    if r["new_warning_categories"]:
        head += f"\n          gates WARN (new): {', '.join(r['new_warning_categories'])}"
    return head


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--base", default="HEAD", help="git ref for the predecessor (default: HEAD)")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--max-regression", type=float, default=0.0,
                    help="allowed score drop before REGRESSED (default 0.0)")
    ap.add_argument("--fail-on-regression", action="store_true",
                    help="exit 1 on any REGRESSED (default: report-only, exit 0)")
    ap.add_argument("--wiki-root", default=None)
    args = ap.parse_args()

    wiki_root = Path(args.wiki_root) if args.wiki_root else (REPO_ROOT / "wiki")
    results = []
    any_regression = False
    had_error = False

    for f in args.files:
        p = Path(f).resolve()
        try:
            relpath = str(p.relative_to(REPO_ROOT.resolve()))
        except ValueError:
            relpath = f
        tmp_name = None
        try:
            pred_text = read_predecessor(REPO_ROOT, args.base, relpath)
            old_path = None
            if pred_text is not None:
                fd, tmp_name = tempfile.mkstemp(suffix=".md")
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(pred_text)
                old_path = Path(tmp_name)
            res = compare(p, old_path, wiki_root, args.max_regression)
        except Exception as exc:  # report-only: never crash the commit / CI
            res = {
                "predecessor_found": None,
                "old_score": None,
                "new_score": None,
                "delta_score": None,
                "verdict": "ERROR",
                "error": str(exc),
                "new_blocked_categories": [],
                "new_warning_categories": [],
            }
            had_error = True
        finally:
            if tmp_name and os.path.exists(tmp_name):
                os.unlink(tmp_name)
        res["target"] = relpath
        res["base_ref"] = args.base
        results.append(res)
        if res["verdict"] == "REGRESSED":
            any_regression = True

    if args.format == "json":
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(_format_text(r))

    # Report-only by default (exit 0). --fail-on-regression is fail-closed:
    # a REGRESSED verdict OR an evaluation ERROR both block.
    return 1 if (args.fail_on_regression and (any_regression or had_error)) else 0


if __name__ == "__main__":
    sys.exit(main())
