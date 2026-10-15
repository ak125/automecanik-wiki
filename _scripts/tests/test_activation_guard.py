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
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

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


# --- main() sur un vrai dépôt git : la base doit désigner un commit existant ---------


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _commit_catalog(root: Path, entries: list[dict]) -> str:
    path = root / guard.CATALOG_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"sources": entries}), encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "catalog")
    return _git(root, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _git(tmp_path, "init", "-q")
    monkeypatch.setattr(guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(guard, "CATALOG", tmp_path / guard.CATALOG_REL)
    return tmp_path


def _main(monkeypatch: pytest.MonkeyPatch, base: str) -> int:
    monkeypatch.setattr(sys, "argv", ["check-activation-guard.py", "--base", base])
    return guard.main()


def test_main_flags_activation_pushed_between_two_commits(repo, monkeypatch):
    before = _commit_catalog(repo, [_e("s", "to_capture")])
    _commit_catalog(repo, [_e("s", "active")])
    assert _main(monkeypatch, before) == 1


def test_main_passes_when_catalog_unchanged(repo, monkeypatch):
    before = _commit_catalog(repo, [_e("s", "to_capture")])
    assert _main(monkeypatch, before) == 0


def test_main_fails_loud_on_null_push_base(repo, monkeypatch):
    _commit_catalog(repo, [_e("s", "to_capture")])
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "0" * 40)
    assert exc.value.code == 2


def test_main_fails_loud_on_unknown_full_sha_base(repo, monkeypatch):
    # `rev-parse --verify` accepte un SHA complet sans vérifier que l'objet existe ;
    # sans `^{commit}` la base vaut « catalogue vide » et le guard passe à tort.
    _commit_catalog(repo, [_e("s", "to_capture")])
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "1" * 40)
    assert exc.value.code == 2
