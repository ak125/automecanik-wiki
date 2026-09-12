"""Contract between source metadata, strict frontmatter schema and real scorer.

Synthetic fixtures prove format compatibility and arithmetic, not source truth
or eligibility under the complete promotion decision.
"""
import importlib.util
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "_meta/schema/frontmatter.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)
SPEC = importlib.util.spec_from_file_location("confidence_contract", ROOT / "_scripts/compute-confidence-score.py")
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)


def document():
    text = (ROOT / "_scripts/tests/fixtures/valid-non-safety-filtre.md").read_text()
    fm, _ = SCORER.split_frontmatter(text)
    result = yaml.safe_load(fm)
    result["source_refs"] = [
        {"kind": "raw", "path": "sources/synthetic-test.md"},
        {"kind": "external_url", "url": "https://example.com/synthetic-test", "captured_at": "2026-09-12"},
    ]
    return result


@pytest.mark.parametrize("confidence, expected", [(None, 0.84), ("low", 0.72), ("medium", 0.84), ("high", 1.0)])
def test_schema_valid_source_confidence_reaches_real_scorer(tmp_path, confidence, expected):
    fm = document()
    if confidence is not None:
        for ref in fm["source_refs"]:
            ref["confidence"] = confidence
    VALIDATOR.validate(fm)
    (tmp_path / "related.md").write_text("Synthetic internal link target")
    body = "\n".join(
        f"## {heading}\nSynthetic section content exceeding twenty nonspace characters.\n"
        for heading in SCORER.SECTIONS_REQUIRED["gamme"]
    ) + "\nSee [[related]].\n"
    assert SCORER.compute_score(fm, body, tmp_path) == expected
    if confidence == "high":
        assert expected >= 0.85
    else:
        assert expected < 0.85


@pytest.mark.parametrize("invalid", ["very_high", 1.0, None])
def test_schema_rejects_invalid_confidence(invalid):
    fm = document()
    fm["source_refs"][0]["confidence"] = invalid
    with pytest.raises(ValidationError):
        VALIDATOR.validate(fm)


def test_source_metadata_stays_strict():
    fm = document()
    fm["source_refs"][0]["unrecognized_evidence"] = True
    with pytest.raises(ValidationError):
        VALIDATOR.validate(fm)
