"""Guard d'activation (must-fix owner 2026-07-04) — SAME-REPO, RAW-INDÉPENDANT.

L'état dangereux n'est pas « un commit existe » — c'est précisément qu'une source passe à
`active`. Une transition `to_capture → active` (ou une nouvelle entrée `active`) crée une
PREUVE active dont la validité exige le gate cross-repo (`--cross-repo`, 2 repos frais), non
vérifiable par la CI wiki seule. Ce guard fail-closed empêche l'activation par ÉDITION DIRECTE
de _meta/source-catalog.yaml — le contournement du flux gouverné.

Exécution : cd _scripts/tests && python3 -m pytest test_activation_guard.py -v
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "activation_guard", SCRIPTS_DIR / "check-activation-guard.py"
)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


def _e(slug: str, status: str | None = None) -> dict:
    e = {"slug": slug}
    if status is not None:
        e["status"] = status
    return e


def test_to_capture_to_active_flagged():
    base = {"s": _e("s", "to_capture")}
    head = {"s": _e("s", "active")}
    illicit = guard.find_illicit_activations(base, head)
    assert any("to_capture" in m and "active" in m for m in illicit), illicit


def test_new_active_entry_flagged():
    base: dict = {}
    head = {"s": _e("s", "active")}
    assert guard.find_illicit_activations(base, head), "une nouvelle entrée active doit être signalée"


def test_active_unchanged_not_flagged():
    base = {"s": _e("s", "active")}
    head = {"s": _e("s", "active")}
    assert guard.find_illicit_activations(base, head) == []


def test_to_capture_unchanged_not_flagged():
    base = {"s": _e("s", "to_capture")}
    head = {"s": _e("s", "to_capture")}
    assert guard.find_illicit_activations(base, head) == []


def test_removal_not_flagged():
    # active côté base, supprimée côté head → pas une activation
    base = {"s": _e("s", "active")}
    head: dict = {}
    assert guard.find_illicit_activations(base, head) == []


def test_deactivation_not_flagged():
    # active → to_capture (désactivation) → autorisé
    base = {"s": _e("s", "active")}
    head = {"s": _e("s", "to_capture")}
    assert guard.find_illicit_activations(base, head) == []


def test_new_to_capture_not_flagged():
    # nouvelle entrée to_capture = enregistrement de capture, pas une activation
    base: dict = {}
    head = {"s": _e("s", "to_capture")}
    assert guard.find_illicit_activations(base, head) == []


def test_missing_status_defaults_active_so_new_entry_flagged():
    # status omis = active (même défaut que le gate) → nouvelle entrée sans status = activation
    base: dict = {}
    head = {"s": _e("s")}
    assert guard.find_illicit_activations(base, head), "status omis = active → nouvelle entrée signalée"
