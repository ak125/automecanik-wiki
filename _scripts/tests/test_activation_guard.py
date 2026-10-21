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
import activation_receipt  # noqa: E402 — importable via le chemin posé par le guard


def _e(slug: str, status: str | None = None, raw_ref: dict | None = None, **fields) -> dict:
    e = {"slug": slug}
    if status is not None:
        e["status"] = status
    if raw_ref is not None:
        e["raw_ref"] = raw_ref
    e.update(fields)
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


# Requalification d'une source déjà active : le `type` donne le rôle (`proof`/`corroboration`) et
# le plafond de confiance, le `publisher` l'éditeur compté pour l'indépendance (ADR-114 D3).
def _proof(slug: str = "s", **fields) -> dict:
    return {**_e(slug, "active", _ref("a"), type="oem_workshop", publisher="Éditeur A"), **fields}


@pytest.mark.parametrize("field, value", [
    ("type", "oem_manual"),            # preuve → autre preuve
    ("publisher", "Éditeur B"),        # éditeur scindé : compterait comme un éditeur de plus
    ("publisher", "éditeur a"),        # même clé normalisée : changement de texte quand même signé
])
def test_active_authority_field_change_flagged(field, value):
    base = {"s": _proof()}
    head = {"s": _proof(**{field: value})}
    illicit = guard.find_illicit_activations(base, head)
    assert len(illicit) == 1 and field in illicit[0] and "requalification" in illicit[0], illicit


def test_corroboration_retyped_as_proof_flagged():
    base = {"s": _proof(type="brochure")}
    head = {"s": _proof(type="oem_workshop")}
    assert guard.find_illicit_activations(base, head)


def test_publisher_set_on_active_entry_flagged():
    # éditeur absent = non compté (publisher_absent) → éditeur posé : création d'une preuve comptée
    base = {"s": _e("s", "active", _ref("a"), type="oem_workshop")}
    head = {"s": _proof()}
    assert guard.find_illicit_activations(base, head)


def test_type_and_raw_ref_changed_together_reported_once():
    base = {"s": _proof()}
    head = {"s": _proof(type="normative_standard", raw_ref=_ref("b"))}
    illicit = guard.find_illicit_activations(base, head)
    assert len(illicit) == 1 and "raw_ref" in illicit[0] and "type" in illicit[0], illicit


def test_publisher_removed_not_flagged():
    # retrait = l'éditeur n'est plus compté : aucune preuve créée, comme le retrait du raw_ref
    base = {"s": _proof()}
    head = {"s": {k: v for k, v in _proof().items() if k != "publisher"}}
    assert guard.find_illicit_activations(base, head) == []


def test_descriptive_fields_change_not_flagged():
    base = {"s": _proof(title="Titre", notes="n", license="third_party_extract", year=2020)}
    head = {"s": _proof(title="Titre corrigé", notes="n2", license="captured_for_internal_review", year=2021)}
    assert guard.find_illicit_activations(base, head) == []


def test_requalification_with_demotion_not_flagged():
    # chemin gouverné : repasser en to_capture (libre), puis activer par le flux signé
    base = {"s": _proof(type="brochure")}
    head = {"s": _proof(status="to_capture", type="oem_workshop", publisher="Éditeur B")}
    assert guard.find_illicit_activations(base, head) == []


def test_to_capture_requalification_not_flagged():
    base = {"s": _proof(status="to_capture", type="brochure")}
    head = {"s": _proof(status="to_capture", type="oem_workshop")}
    assert guard.find_illicit_activations(base, head) == []


# Une seule définition de l'activation : le guard signale exactement les slugs que le reçu doit
# couvrir (`activation_receipt.transitions`). Une divergence ferait passer un reçu qui ne couvre
# pas tout ce que le guard signale, ou exigerait un reçu impossible à émettre.
_MATRIX = [
    ({}, {"s": _proof()}),
    ({"s": _proof(status="to_capture")}, {"s": _proof()}),
    ({"s": _proof()}, {"s": _proof()}),
    ({"s": _proof()}, {"s": _proof(raw_ref=_ref("b"))}),
    ({"s": _proof()}, {"s": _proof(type="brochure")}),
    ({"s": _proof(type="brochure")}, {"s": _proof()}),
    ({"s": _proof()}, {"s": _proof(publisher="Éditeur B")}),
    ({"s": _proof()}, {"s": {k: v for k, v in _proof().items() if k != "publisher"}}),
    ({"s": _proof()}, {"s": _proof(status="to_capture", type="brochure")}),
    ({"s": _proof()}, {"s": _proof(title="autre")}),
    ({"s": _proof()}, {}),
    ({"s": _proof(), "t": _proof("t", type="brochure")}, {"s": _proof(), "t": _proof("t")}),
]


@pytest.mark.parametrize("base, head", _MATRIX)
def test_guard_and_receipt_agree_on_activations(base, head):
    flagged = {m.split(":", 1)[0] for m in guard.find_illicit_activations(base, head)}
    assert flagged == set(activation_receipt.transitions(base, head))


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


def test_main_flags_requalification_pushed_between_two_commits(repo, monkeypatch):
    before = _commit_catalog(repo, [_proof(type="brochure")])
    _commit_catalog(repo, [_proof()])
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
