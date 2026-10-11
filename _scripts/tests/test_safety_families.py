"""Tests du SINGLE SOURCE de classification sécurité (ADR fix #5).

Verrouille : les 6 familles, la détection par family ET par slug (entity_data.family
souvent absent), la couverture airbag/suspension (manquaient à gate_safety_unsourced),
l'union L0 d'ADR-093 (précondition (b) d'ADR-114 D5), les négatifs non-sécurité, et le
comportement fail-closed.

Placé sous _scripts/tests/ pour être exécuté par la CI (job « pytest fixtures »).
"""
import importlib.util
from pathlib import Path

SF_PATH = Path(__file__).resolve().parent.parent / "safety_families.py"


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


def test_adr093_l0_union_covered():
    """ADR-093 L0 : union minimale {…, transmission, roulement-de-roue/moyeu,
    fixation/visserie-de-roue, durite/circuit-de-frein, direction-assistée}.
    Chaque famille est prouvée par slug (fiches) ET par titre accentué (fail-closed)."""
    sf = _load()
    l0 = {
        "transmission": ["cardan", "soufflet-de-cardan", "arbre-de-transmission",
                         "manchette-arbre-a-cardan"],
        "roulement-moyeu-de-roue": ["roulement-de-roue", "kit-de-roulement-de-roue",
                                    "moyeu-de-roue"],
        "visserie-de-roue": ["vis-de-roue", "ecrou-de-roue", "goujon-de-roue",
                             "boulon-de-roue", "antivol-de-roue"],
        "circuit-de-frein": ["durite-de-frein", "conduite-de-frein", "cylindre-de-roue",
                             "capteur-de-pression-servofrein"],
        "direction-assistee": ["pompe-de-direction-assistee", "durite-de-direction-assistee"],
    }
    for family, slugs in l0.items():
        for slug in slugs:
            assert sf.is_safety_proposal({"slug": slug}) is True, (family, slug)
    for title in ["Écrou de roue", "Joint homocinétique", "Roulement de roue",
                  "Moyeu de roue", "Vis de roue", "Direction assistée"]:
        assert sf.is_safety_proposal({"slug": "x", "title": title}) is True, title


def test_non_safety_negatives():
    sf = _load()
    for slug in ["filtre-a-huile", "alternateur", "filtre-a-air", "demarreur", "turbo",
                 # voisins lexicaux des motifs L0 : pas des pièces de roue / de frein
                 "vis-roue-dentee-arbre-a-came", "reservoir-de-carburant"]:
        assert sf.is_safety_proposal({"slug": slug}) is False, slug


def test_fail_closed_on_bad_input():
    sf = _load()
    # aliases non-itérable → exception interne → True (fail-closed : doute → sécurité)
    assert sf.is_safety_proposal({"aliases": 123}) is True
