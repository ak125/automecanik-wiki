"""Tests for _scripts/quality-gates.py against fixtures in _scripts/tests/fixtures/.

Each fixture exercises one specific gate (positive or negative case).
We run the gates in-process and assert presence/absence of expected blocked_reasons.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCRIPTS_DIR = Path(__file__).resolve().parent.parent

# Load quality-gates.py as a module (filename has hyphen, can't import directly)
spec = importlib.util.spec_from_file_location(
    "quality_gates", SCRIPTS_DIR / "quality-gates.py"
)
qg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qg)


@pytest.fixture(scope="module")
def registry():
    return qg.load_registry()


@pytest.fixture(scope="module")
def source_catalog():
    return qg.load_source_catalog()


# Cases : (fixture_filename, expected_pattern_in_failures_OR_None_if_should_pass)
CASES = [
    ("valid-plaquette-de-frein.md", None),
    ("valid-non-safety-filtre.md", None),
    ("invalid-no-relation-to-part.md", "relation_to_part_missing"),
    ("invalid-overclaimed-brochure-high.md", "confidence_overclaimed"),
    ("invalid-legacy-symptoms-block.md", "legacy_symptoms_block"),
    ("invalid-source-slug-unknown.md", "source_slug_unknown"),
    ("invalid-maintenance-advice-missing.md", "maintenance_advice_missing"),
]


@pytest.mark.parametrize("fixture_name, expected_failure", CASES)
def test_fixture_gate(fixture_name, expected_failure, registry, source_catalog):
    fpath = FIXTURES / fixture_name
    assert fpath.exists(), f"Missing fixture {fpath}"
    failures, warnings = qg.run_gates(fpath, registry, source_catalog)

    if expected_failure is None:
        # PASS expected
        assert not failures, f"Expected PASS but got failures: {failures}"
    else:
        # Must contain the expected failure pattern
        assert any(expected_failure in f for f in failures), (
            f"Expected failure containing {expected_failure!r}; got: {failures}"
        )


def test_source_catalog_loads(source_catalog):
    """Sanity check: catalog has at least our seed entries."""
    assert "bosch_fad_2020" in source_catalog
    assert "oem_renault_clio_iii_workshop" in source_catalog
    assert source_catalog["bosch_fad_2020"]["type"] == "brochure"
