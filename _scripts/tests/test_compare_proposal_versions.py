"""Tests for _scripts/compare-proposal-versions.py.

The comparator scores a proposal fiche's CURRENT version against its
PREDECESSOR (from git) so a rebuilt fiche is never promoted/overwritten
without proof it is at least as good. Verdict is score-based; the gate
category diff is reported for transparency (report-only in Phase A).

Pure protocol logic (decide_verdict / diff_categories / extract_category)
is unit-tested without git or files. One end-to-end test exercises compare()
on fixtures, and read_predecessor() is checked against the real repo git.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parent
WIKI_ROOT = REPO_ROOT / "wiki"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cmp = _load("compare_proposal_versions", "compare-proposal-versions.py")


# --- decide_verdict : the protocol, score-based ---

def test_verdict_new_when_no_predecessor():
    assert cmp.decide_verdict(None, 0.36) == ("NEW", None)


def test_verdict_improved_when_score_rises():
    assert cmp.decide_verdict(0.24, 0.36) == ("IMPROVED", 0.12)


def test_verdict_regressed_when_score_drops():
    assert cmp.decide_verdict(0.40, 0.30) == ("REGRESSED", -0.1)


def test_verdict_neutral_when_equal():
    assert cmp.decide_verdict(0.50, 0.50) == ("NEUTRAL", 0.0)


def test_verdict_neutral_within_tolerance():
    assert cmp.decide_verdict(0.50, 0.46, max_regression=0.05) == ("NEUTRAL", -0.04)


def test_verdict_regressed_beyond_tolerance():
    assert cmp.decide_verdict(0.50, 0.44, max_regression=0.05) == ("REGRESSED", -0.06)


# --- extract_category / diff_categories : informational gate diff ---

def test_extract_category_strips_message():
    msg = "safety_unsourced: diagnostic_relations[0] family=freinage requires manual_review"
    assert cmp.extract_category(msg) == "safety_unsourced"


def test_diff_categories_introduced_and_resolved():
    old = ["symptom_unstructured: x", "maintenance_advice_missing: y"]
    new = ["safety_unsourced: z"]
    introduced, resolved = cmp.diff_categories(old, new)
    assert introduced == ["safety_unsourced"]
    assert resolved == ["maintenance_advice_missing", "symptom_unstructured"]


# --- evaluate_path : reuse legacy score + gates (no reinvention) ---

def test_evaluate_path_returns_score_and_categories():
    ev = cmp.evaluate_path(FIXTURES / "compare-fixture-rich.md", wiki_root=WIKI_ROOT)
    assert isinstance(ev["score"], float)
    assert 0.0 <= ev["score"] <= 1.0
    assert isinstance(ev["blocked_categories"], list)


# --- compare : end-to-end on fixtures ---

def test_compare_rich_beats_poor_is_improved():
    result = cmp.compare(
        new_path=FIXTURES / "compare-fixture-rich.md",
        old_path=FIXTURES / "compare-fixture-poor.md",
        wiki_root=WIKI_ROOT,
    )
    assert result["new_score"] > result["old_score"]
    assert result["verdict"] == "IMPROVED"


def test_compare_poor_replacing_rich_is_regressed():
    result = cmp.compare(
        new_path=FIXTURES / "compare-fixture-poor.md",
        old_path=FIXTURES / "compare-fixture-rich.md",
        wiki_root=WIKI_ROOT,
    )
    assert result["verdict"] == "REGRESSED"


def test_compare_no_predecessor_is_new():
    result = cmp.compare(
        new_path=FIXTURES / "compare-fixture-rich.md",
        old_path=None,
        wiki_root=WIKI_ROOT,
    )
    assert result["verdict"] == "NEW"
    assert result["old_score"] is None


# --- read_predecessor : git layer, against the real repo ---

def test_read_predecessor_returns_none_for_absent_file():
    assert cmp.read_predecessor(REPO_ROOT, "HEAD", "proposals/__does_not_exist__.md") is None


def test_read_predecessor_returns_committed_text():
    # filtre-a-huile.md is a committed proposal on origin/main (HEAD of this worktree).
    text = cmp.read_predecessor(REPO_ROOT, "HEAD", "proposals/filtre-a-huile.md")
    assert text is not None
    assert text.startswith("---")


# --- robustness : report-only must never crash (BUG-1 / BUG-3) ---

def test_evaluate_path_malformed_yaml_does_not_crash():
    # Unparseable frontmatter must degrade to score 0.0, never raise.
    ev = cmp.evaluate_path(FIXTURES / "compare-fixture-malformed.md", wiki_root=WIKI_ROOT)
    assert ev["score"] == 0.0
    assert isinstance(ev["blocked_categories"], list)


def test_evaluate_path_no_frontmatter_does_not_crash(tmp_path):
    p = tmp_path / "plain.md"
    p.write_text("# just a title\n\nno frontmatter here\n", encoding="utf-8")
    ev = cmp.evaluate_path(p, wiki_root=WIKI_ROOT)
    assert ev["score"] == 0.0


def test_main_report_only_exit_zero_on_unreadable_file(tmp_path):
    import subprocess
    import sys

    missing = tmp_path / "does-not-exist.md"  # path passed but absent on disk
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "compare-proposal-versions.py"), str(missing)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"report-only must exit 0; got {r.returncode}: {r.stderr}"


def test_main_fail_on_regression_exits_one_on_error(tmp_path):
    import subprocess
    import sys

    missing = tmp_path / "does-not-exist.md"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "compare-proposal-versions.py"),
            "--fail-on-regression",
            str(missing),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1, f"fail-closed expected exit 1; got {r.returncode}: {r.stderr}"
