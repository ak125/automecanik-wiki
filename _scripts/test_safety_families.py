"""Tests du SINGLE SOURCE de classification sécurité (ADR fix #5).

Verrouille : les 6 familles, la détection par family ET par slug (entity_data.family
souvent absent), la couverture airbag/suspension (manquaient à gate_safety_unsourced),
les négatifs non-sécurité, et le comportement fail-closed.
"""
import importlib.util
from pathlib import Path

SF_PATH = Path(__file__).resolve().parent / "safety_families.py"


def _load():
    spec = importlib.util.spec_from_file_location("safety_families", SF_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_six_families_present():
    sf = _load()
    assert sf.SAFETY_FAMILY_LABELS == {
        "freinage", "direction", "distribution", "electricite-safety", "airbag", "suspension",
    }


def test_safety_by_declared_family():
    sf = _load()
    for fam in sf.SAFETY_FAMILY_LABELS:
        assert sf.is_safety_proposal({"slug": "x", "entity_data": {"family": fam}}) is True, fam


def test_safety_by_slug_when_family_absent():
    sf = _load()
    # entity_data.family ABSENT (cas réels : plaquette/colonne échappaient au gate)
    for slug in ["plaquette-de-frein", "disque-de-frein", "colonne-de-direction",
                 "amortisseur", "courroie-de-distribution"]:
        assert sf.is_safety_proposal({"slug": slug}) is True, slug


def test_airbag_suspension_now_covered():
    """airbag + suspension (manquaient à gate_safety_unsourced) sont couverts."""
    sf = _load()
    assert sf.is_safety_proposal({"slug": "airbag-conducteur"}) is True
    assert sf.is_safety_proposal({"slug": "amortisseur-avant"}) is True


def test_non_safety_negatives():
    sf = _load()
    for slug in ["filtre-a-huile", "alternateur", "filtre-a-air", "demarreur", "turbo"]:
        assert sf.is_safety_proposal({"slug": slug}) is False, slug


def test_fail_closed_on_bad_input():
    sf = _load()
    # aliases non-itérable → exception interne → True (fail-closed : doute → sécurité)
    assert sf.is_safety_proposal({"aliases": 123}) is True
