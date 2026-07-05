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


# --- Gate 7 catalog_leak — dual-corpus regression (2026-07-05) ------------------
# Grounded in real leaks found in the golf-5-19-tdi RAW scrape. Two corpora:
#   LEAKS  → gate_catalog_leak MUST return a non-empty list (caught).
#   SAFE   → gate_catalog_leak MUST return [] (real knowledge that must survive).
# The SAFE corpus guards the OEM/price patterns against false-positiving on
# km thresholds, torque values, OBD P-codes, oil specs, engine codes, tyre sizes.
CATALOG_LEAKS = [
    "réparation estimée 800 à 1500 €",
    "turbo ~1 645 € pièce seule",
    "crémaillère de direction ~1300€ chez VW",
    "plaquettes ≈60-80 € le jeu",
    "kit d'entretien 18 euros",
    "arbre à cames 038109101R",                 # bare VAG OEM ref (9 digits + letter)
    "vase d'expansion 1K0121407",               # VAG digit-letter-digit ref
    "huile Haldex G060175A2",                   # Haldex fluid ref
    "coussinets de bielle 045105701C",          # VAG 9-digit + letter
    "volant moteur Sachs 2290 601 050",         # brand + product ref
    "embrayage LuK 3000 951 120",
    "voir https://www.automecanik.com/pieces/debitmetre-3927/vw-173/1-9-tdi-17484.html",
    "source https://www.auto-doc.fr/pieces-detachees/disque-10132/vw/golf",
    "prix sur https://www.piecesauto24.com/vw/golf-v-1k1/17484/disque-de-frein",
]

CATALOG_SAFE = [
    "roulement défaillant vers 150000 km",       # km threshold
    "serrage injecteur-pompe 12 Nm +270°",       # torque
    "code défaut P0299 (sous-suralimentation turbo)",  # OBD P-code
    "débitmètre G70 défaut P0101",
    "plateforme PQ35 mutualisée",                # platform code
    "huile conforme à la norme VW 505.01",       # oil spec (safe, causal)
    "spécification 507.00 low-SAPS",
    "entraxe 5x112 et disque 280 mm",            # cotes (hors périmètre Gate 7)
    "codes moteur BKC, BLS, BXE (105 ch)",       # engine codes
    "plaquettes conformes ECE R90",              # brake norm
    "monte pneumatique 195/65 R15",              # tyre size
    "produite de 2003 à 2008",                   # years
    "moteur 1.9 TDI 105 ch",                     # engine designation
    "les plaquettes Textar et Ferodo sont réputées",  # brand-as-vocab, NO ref number
]


@pytest.mark.parametrize("body", CATALOG_LEAKS)
def test_catalog_leak_catches_price_oem_domain(body):
    """Gate 7 MUST flag prices (€/euros), bare OEM refs, brand+ref, catalog URLs."""
    assert qg.gate_catalog_leak(body), f"Expected catalog_leak on: {body!r}"


@pytest.mark.parametrize("body", CATALOG_SAFE)
def test_catalog_leak_spares_safe_knowledge(body):
    """Gate 7 must NOT false-positive on km/torque/P-codes/oil-spec/engine-codes/tyre/brand-vocab."""
    assert not qg.gate_catalog_leak(body), f"False positive catalog_leak on: {body!r}"
