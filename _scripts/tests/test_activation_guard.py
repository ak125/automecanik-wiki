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


def _e(slug: str, status: str | None = None, raw_ref: dict | None = None) -> dict:
    e = {"slug": slug}
    if status is not None:
        e["status"] = status
    if raw_ref is not None:
        e["raw_ref"] = raw_ref
    return e


def _ref(sha: str, manifest_id: str = "m-doc") -> dict:
    return {"repo": "automecanik-raw", "manifest_id": manifest_id, "expected_sha256": "sha256:" + sha * 64}


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


# Ré-épingle d'une source déjà active (ADR-116 D4 d) : la nouvelle archive devient la preuve,
# les ancres qui la citent doivent passer `--cross-repo` avant la mutation.
def test_active_raw_ref_repin_flagged():
    base = {"s": _e("s", "active", _ref("a"))}
    head = {"s": _e("s", "active", _ref("b"))}
    illicit = guard.find_illicit_activations(base, head)
    assert len(illicit) == 1 and "raw_ref" in illicit[0] and "ADR-116" in illicit[0], illicit


def test_active_raw_ref_other_manifest_flagged():
    base = {"s": _e("s", "active", _ref("a"))}
    head = {"s": _e("s", "active", _ref("a", manifest_id="m-autre"))}
    assert guard.find_illicit_activations(base, head)


def test_active_raw_ref_added_flagged():
    # active sans raw_ref (non prouvée) → raw_ref posé : création de preuve
    base = {"s": _e("s", "active")}
    head = {"s": _e("s", "active", _ref("a"))}
    assert guard.find_illicit_activations(base, head)


def test_active_raw_ref_missing_status_defaults_active_flagged():
    base = {"s": _e("s", raw_ref=_ref("a"))}
    head = {"s": _e("s", raw_ref=_ref("b"))}
    assert guard.find_illicit_activations(base, head)


def test_active_raw_ref_unchanged_not_flagged():
    base = {"s": _e("s", "active", _ref("a"))}
    head = {"s": _e("s", "active", _ref("a"))}
    assert guard.find_illicit_activations(base, head) == []


def test_active_raw_ref_removed_not_flagged():
    # retrait de la preuve = comme une désactivation : aucune preuve active créée
    base = {"s": _e("s", "active", _ref("a"))}
    head = {"s": _e("s", "active")}
    assert guard.find_illicit_activations(base, head) == []


def test_to_capture_raw_ref_change_not_flagged():
    base = {"s": _e("s", "to_capture", _ref("a"))}
    head = {"s": _e("s", "to_capture", _ref("b"))}
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
