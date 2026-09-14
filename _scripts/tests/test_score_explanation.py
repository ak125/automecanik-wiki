"""Arithmetic diagnostics are read-only and never grant promotion eligibility."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "compute-confidence-score.py"
SPEC = importlib.util.spec_from_file_location("score_explanation", SCRIPT)
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)


def write_candidate(path, score=0.30):
    fm = {"entity_type": "gamme", "source_refs": [{"kind": "raw"}],
          "confidence_score": score}
    path.write_text("---\n" + yaml.safe_dump(fm) + "---\n\n## Rôle technique\n"
                    "Une explication documentaire suffisamment longue pour la rubrique.\n",
                    encoding="utf-8")
    return path


def test_explanation_uses_the_production_formula(tmp_path):
    fm = {"entity_type": "gamme", "source_refs": [{"kind": "raw"}]}
    body = "## Rôle technique\nTexte documentaire présent et suffisamment long."
    result = SCORER.explain_score(fm, body, tmp_path)
    assert result["score"] == SCORER.compute_score(fm, body, tmp_path) == 0.30
    assert result["scope"] == "formula_only_not_promotion"
    parts = result["components"]
    assert parts["source_confidence"]["contribution"] == 0.24
    assert parts["sections"]["filled"] == ["Fonctionnement"]
    assert parts["sections"]["observed_headings"] == ["Rôle technique"]
    assert "Définition" in parts["sections"]["missing_or_insufficient"]
    assert parts["internal_links"]["resolved"] == parts["internal_links"]["total"] == 0
    assert parts["source_kind_diversity"]["distinct_kind_count"] == 1
    assert parts["source_kind_diversity"]["measures_publisher_independence"] is False
    assert "eligible" not in result


def test_full_arithmetic_and_legacy_section_count(tmp_path):
    (tmp_path / "related.md").write_text("Fixture")
    fm = {"entity_type": "gamme", "source_refs": [
        {"kind": "raw", "confidence": "high"},
        {"kind": "external_url", "confidence": "medium"}]}
    body = "\n".join(f"## {h}\nTexte de test assez long pour cette section.\n"
                     for h in SCORER.SECTIONS_REQUIRED["gamme"])
    body += "\n[[related]] [[absent]]\n"
    result = SCORER.explain_score(fm, body, tmp_path)
    assert result["score"] == 0.82  # .32 + .30 + .10 + .10
    assert result["components"]["sections"]["filled"] == SCORER.SECTIONS_REQUIRED["gamme"]
    assert SCORER.count_filled_sections(body, SCORER.SECTIONS_REQUIRED["gamme"]) == 5
    assert result["components"]["internal_links"]["resolved"] == 1
    assert result["components"]["internal_links"]["total"] == 2


def test_two_raw_documents_do_not_become_distinct_source_kinds(tmp_path):
    result = SCORER.explain_score({"source_refs": [{"kind": "raw"}, {"kind": "raw"}]}, "", tmp_path)
    assert result["components"]["source_kind_diversity"]["contribution"] == 0


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), "NaN", "Infinity", True])
def test_check_refuses_non_finite_or_boolean_scores(tmp_path, value):
    path = write_candidate(tmp_path / "candidate.md", value)
    before = path.read_bytes()
    assert SCORER.process_file(path, "check", tmp_path) is False
    assert path.read_bytes() == before


@pytest.mark.parametrize("value", [float("nan"), "invalid", True, None])
def test_explicit_fix_can_repair_invalid_score(tmp_path, value):
    path = write_candidate(tmp_path / "candidate.md", value)
    assert SCORER.process_file(path, "fix", tmp_path) is True
    assert SCORER.process_file(path, "check", tmp_path) is True
    after = path.read_bytes()
    assert SCORER.process_file(path, "fix", tmp_path) is True
    assert path.read_bytes() == after


def test_cli_explain_is_read_only_and_json(tmp_path):
    path = write_candidate(tmp_path / "candidate.md")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--explain", str(path)],
                            capture_output=True, text=True)
    assert result.returncode == 0 and not result.stderr
    report = json.loads(result.stdout)
    assert report["errors"] == []
    assert report["results"][0]["score"] == 0.30
    assert report["results"][0]["declared_score_status"] == "matches"
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


@pytest.mark.parametrize("value,status", [(0.99, "mismatch"), (float("nan"), "invalid")])
def test_explanation_distinguishes_declared_score_from_computed(tmp_path, capsys, value, status):
    path = write_candidate(tmp_path / "candidate.md", value)
    assert SCORER.explain_files([path], tmp_path) == 0
    result = json.loads(capsys.readouterr().out)["results"][0]
    assert result["declared_score_status"] == status
    assert result["score"] == 0.30


@pytest.mark.parametrize("text", ["no frontmatter", "---\n- list\n---\n", "---\nx: [\n---\n"])
def test_invalid_input_is_an_explicit_error(tmp_path, capsys, text):
    path = tmp_path / "invalid.md"
    path.write_text(text)
    assert SCORER.explain_files([path, tmp_path / "absent.md"], tmp_path) == 1
    result = json.loads(capsys.readouterr().out)
    assert not result["results"]
    assert len(result["errors"]) == 2
    assert {e["code"] for e in result["errors"]} == {"score_explanation_unavailable"}


def test_explain_cannot_be_combined_with_fix(tmp_path):
    path = write_candidate(tmp_path / "candidate.md")
    before = path.read_bytes()
    result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--explain", "--fix", str(path)],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert path.read_bytes() == before
