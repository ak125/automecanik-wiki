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


def test_long_heading_without_body_is_not_substance():
    body = '\n'.join(
        f"## {heading} avec un titre artificiellement tres long sans explication\n"
        for heading in SCORER.SECTIONS_REQUIRED['gamme']
    )
    assert SCORER.count_filled_sections(body, SCORER.SECTIONS_REQUIRED['gamme']) == 0


def test_next_heading_cannot_fill_previous_section():
    body = '## Definition\n\n## Another long heading that contains no explanation\n'
    assert SCORER.count_filled_sections(body, ['Definition']) == 0


@pytest.mark.parametrize('content, expected', [('x' * 19, 0), ('x' * 20, 1), (' \n\t', 0)])
def test_substance_boundary_excludes_heading_and_whitespace(content, expected):
    body = f'## Definition with a long explanatory-looking heading\n{content}\n'
    assert SCORER.count_filled_sections(body, ['Definition']) == expected


def test_duplicate_heading_counts_required_section_only_once():
    body = '## Definition\n' + 'x' * 20 + '\n## Definition\n' + 'y' * 20
    assert SCORER.count_filled_sections(body, ['Definition']) == 1


def test_score_details_explain_observed_oil_filter_components(tmp_path):
    fm = document()  # absent confidence is the historical medium default
    body = '## Fonctionnement\n' + 'x' * 25 + '\n## FAQ\n' + 'y' * 25
    details = SCORER.compute_score_details(fm, body, tmp_path)
    assert details['score'] == SCORER.compute_score(fm, body, tmp_path) == 0.46
    assert {k: v['points'] for k, v in details['components'].items()} == {
        'sources': 0.24, 'sections': 0.12, 'internal_links': 0.0, 'source_kinds': 0.1}
    assert details['components']['sources']['defaulted_confidence_indices'] == [0, 1]
    assert details['components']['sections']['unmatched_required'] == [
        'Définition', "Symptômes d'usure", 'Choix selon véhicule']
    assert details['components']['internal_links']['total'] == 0
    assert details['scope'] == 'metadata_structure_proxy_not_factual_or_seo_validation'


def test_score_details_identify_unresolved_links(tmp_path):
    (tmp_path / 'known.md').write_text('canonical fixture')
    details = SCORER.compute_score_details(document(), '[[known]] [[missing]]', tmp_path)
    assert details['components']['internal_links']['unresolved'] == ['missing']
    assert details['components']['internal_links']['resolved'] == 1
    assert details['components']['internal_links']['points'] == 0.1
