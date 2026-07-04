"""H1-B — cross-repo source-catalog raw_ref gate fail-closed (must-fix owner 2026-07-04).

Durcit `gate_source_catalog_raw_refs` (quality-gates.py) en TDD :

  B1 — raw_inventory_unreachable : une PREUVE DÉCLARÉE (entrée `active` + `raw_ref`)
       dont le raw inventory est INJOIGNABLE devient une FAILURE (avant : WARN silencieux).
       INVARIANT CATÉGORIE (owner) : le fail-closed porte sur une preuve DÉCLARÉE mais
       invérifiable, JAMAIS sur l'absence abstraite du repo quand rien ne le consomme
       (0 entrée active → aucun check → PASS, même RAW absent).

  B2 — duplicate_manifest_id : un manifest_id dupliqué dans le raw inventory consommé
       rend la preuve ambiguë (quel SHA fait foi ?) → FAILURE. Aucun tri, aucun premier,
       aucun dernier gagnant. Défense INDÉPENDANTE du repo RAW (recompute depuis le CSV
       réellement consommé) MAIS de contrat IDENTIQUE : exception gouvernée `rec-<doc_id>`
       (recyclé, partagé à dessein entre chunks) mirroir de regen-manifests.py:299-303 —
       sinon fork silencieux de contrat vs le SoT RAW.

Exécution : cd _scripts/tests && python3 -m pytest test_source_catalog_raw_refs.py -v
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent

# Load quality-gates.py as a module (filename has hyphen, can't import directly) —
# même seam que test_quality_gates.py ; le read top-level du catalog réel réussit.
_spec = importlib.util.spec_from_file_location("quality_gates", SCRIPTS_DIR / "quality-gates.py")
qg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qg)

# Un SHA arbitraire mais cohérent des deux côtés (catalog.expected_sha256 == CSV.sha256).
# Le gate compare par égalité de chaîne exacte, le format importe peu tant qu'il matche.
SHA_X = "sha256:" + "a" * 64
SHA_Y = "sha256:" + "b" * 64

INVENTORY_HEADER = "path,manifest_id,layer,unstable_id,sha256,size_bytes,added_at"


def _write_inventory(tmp_path: Path, rows: list[tuple[str, str]]) -> Path:
    """Écrit un raw inventory CSV minimal réaliste. rows = [(manifest_id, sha256), ...]."""
    inv = tmp_path / "manifests" / "source-inventory.csv"
    inv.parent.mkdir(parents=True, exist_ok=True)
    lines = [INVENTORY_HEADER]
    for i, (mid, sha) in enumerate(rows):
        lines.append(f"sources/x{i}.md,{mid},sources,,{sha},100,2026-07-04")
    inv.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return inv


def _active(mid: str, expected_sha: str | None = None) -> dict:
    """Entrée source-catalog `active` déclarant une preuve raw_ref (= preuve DÉCLARÉE)."""
    raw_ref = {"repo": "automecanik-raw", "manifest_id": mid}
    if expected_sha is not None:
        raw_ref["expected_sha256"] = expected_sha
    return {"status": "active", "raw_ref": raw_ref}


def _to_capture(mid: str) -> dict:
    """Entrée `to_capture` — status EXPLICITE (un status omis défaulte à 'active',
    quality-gates.py:265, ce qui ferait fail-closed à tort et masquerait une régression)."""
    return {"status": "to_capture", "raw_ref": {"repo": "automecanik-raw", "manifest_id": mid}}


# ---------------------------------------------------------------------------
# B1 — raw_inventory_unreachable (WARN → FAIL) + garde catégorie
# ---------------------------------------------------------------------------

def test_f1_active_resolved_matching_sha_passes(tmp_path, monkeypatch):
    """Garde anti-sur-durcissement : active + résolu + SHA concordant → PASS."""
    inv = _write_inventory(tmp_path, [("oe_future_x", SHA_X)])
    monkeypatch.setattr(qg, "RAW_INVENTORY", inv)
    failures, warnings = qg.gate_source_catalog_raw_refs({"active_src": _active("oe_future_x", SHA_X)})
    assert failures == [], failures


def test_f2_active_declared_raw_absent_fails_closed(tmp_path, monkeypatch):
    """LE test fail-closed : preuve déclarée + raw inventory absent → FAILURE (pas WARN)."""
    monkeypatch.setattr(qg, "RAW_INVENTORY", tmp_path / "nope" / "missing.csv")
    failures, warnings = qg.gate_source_catalog_raw_refs({"active_src": _active("oe_future_x", SHA_X)})
    assert any("raw_inventory_unreachable" in f for f in failures), failures
    # ne doit PAS rester un simple warning
    assert not any("raw_inventory_unreachable" in w for w in warnings), warnings


def test_f3_active_manifest_absent_fails_source_unresolved(tmp_path, monkeypatch):
    """Case (b) reste distincte : raw joignable mais manifest_id absent → source_unresolved."""
    inv = _write_inventory(tmp_path, [("some_other_id", SHA_X)])
    monkeypatch.setattr(qg, "RAW_INVENTORY", inv)
    failures, warnings = qg.gate_source_catalog_raw_refs({"active_src": _active("oe_future_x", SHA_X)})
    assert any("source_unresolved" in f for f in failures), failures
    # la conversion (a) WARN→FAIL n'a pas fusionné (a) dans (b)
    assert not any("raw_inventory_unreachable" in f for f in failures), failures


def test_f5_no_active_raw_absent_passes(tmp_path, monkeypatch):
    """LOCK garde-catégorie : 0 active + raw absent → PASS (rien à vérifier)."""
    monkeypatch.setattr(qg, "RAW_INVENTORY", tmp_path / "nope" / "missing.csv")
    catalog = {"a": _to_capture("m_a"), "b": _to_capture("m_b")}  # miroir réel G2a : 0 active
    failures, warnings = qg.gate_source_catalog_raw_refs(catalog)
    assert failures == [], failures
    assert not any("raw_inventory_unreachable" in w for w in warnings), warnings


# ---------------------------------------------------------------------------
# B2 — duplicate_manifest_id (indépendant + contrat identique : exception rec-)
# ---------------------------------------------------------------------------

def test_f4_active_duplicate_src_fails(tmp_path, monkeypatch):
    """Preuve captée (src-*) dupliquée dans l'inventaire consommé → duplicate_manifest_id."""
    inv = _write_inventory(tmp_path, [("src-oe-future", SHA_X), ("src-oe-future", SHA_Y)])
    monkeypatch.setattr(qg, "RAW_INVENTORY", inv)
    failures, warnings = qg.gate_source_catalog_raw_refs({"active_src": _active("src-oe-future", SHA_X)})
    assert any("duplicate_manifest_id" in f for f in failures), failures
    # duplicate a priorité et n'émet PAS aussi source_unresolved pour le même slug
    assert not any("source_unresolved" in f for f in failures), failures


def test_f4b_active_duplicate_rec_passes(tmp_path, monkeypatch):
    """Exception gouvernée : rec-<doc_id> partagé entre chunks n'est PAS un doublon-preuve
    (miroir regen-manifests.py:299-303). Une entrée active le référençant → PAS de failure."""
    inv = _write_inventory(tmp_path, [("rec-shared-doc", SHA_X), ("rec-shared-doc", SHA_Y)])
    monkeypatch.setattr(qg, "RAW_INVENTORY", inv)
    failures, warnings = qg.gate_source_catalog_raw_refs({"active_src": _active("rec-shared-doc")})
    assert not any("duplicate_manifest_id" in f for f in failures), failures
    assert failures == [], failures


def test_f5b_no_active_raw_present_with_duplicate_passes(tmp_path, monkeypatch):
    """LOCK garde-catégorie (chemin doublon) : 0 active + raw présent-mais-sale (src-* dupliqué)
    → PASS. Un doublon que rien d'active ne consomme ne doit pas rougir un catalog 0-active."""
    inv = _write_inventory(tmp_path, [("src-oe-future", SHA_X), ("src-oe-future", SHA_Y)])
    monkeypatch.setattr(qg, "RAW_INVENTORY", inv)
    catalog = {"a": _to_capture("m_a"), "b": _to_capture("m_b")}  # 0 active
    failures, warnings = qg.gate_source_catalog_raw_refs(catalog)
    assert failures == [], failures


# ---------------------------------------------------------------------------
# Caller-split (must-fix owner 2026-07-04) — le gate cross-repo n'est enforcé
# QUE par `--cross-repo` (env RAW fourni par le job). Le gate reste intrinsèquement
# fail-closed ; ce qu'on conditionne, c'est SON APPEL au bon job.
# ---------------------------------------------------------------------------

def _run_main(monkeypatch, argv_tail: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["quality-gates.py", *argv_tail])
    return qg.main()


def test_cross_repo_mode_requires_raw_env(tmp_path, monkeypatch):
    """--cross-repo EXIGE que le job fournisse l'env RAW : inventory absent → FAIL
    (jamais un pass silencieux sur 0 active). Anti « sécurité conditionnée à l'env »."""
    monkeypatch.setattr(qg, "RAW_INVENTORY", tmp_path / "nope" / "missing.csv")
    monkeypatch.setattr(qg, "load_source_catalog", lambda: {"a": _to_capture("m")})  # 0 active
    assert _run_main(monkeypatch, ["--cross-repo"]) == 1


def test_cross_repo_mode_fails_unverifiable_active_proof(tmp_path, monkeypatch):
    """--cross-repo, RAW présent, preuve active non résolue → FAIL métier (source_unresolved)."""
    inv = _write_inventory(tmp_path, [("some_other", SHA_X)])
    monkeypatch.setattr(qg, "RAW_INVENTORY", inv)
    monkeypatch.setattr(qg, "load_source_catalog", lambda: {"active_src": _active("oe_x", SHA_X)})
    assert _run_main(monkeypatch, ["--cross-repo"]) == 1


def test_cross_repo_mode_passes_zero_active_with_raw(tmp_path, monkeypatch):
    """--cross-repo, RAW présent (env fourni) + 0 active → PASS."""
    inv = _write_inventory(tmp_path, [("m", SHA_X)])
    monkeypatch.setattr(qg, "RAW_INVENTORY", inv)
    monkeypatch.setattr(qg, "load_source_catalog", lambda: {"a": _to_capture("m")})
    assert _run_main(monkeypatch, ["--cross-repo"]) == 0


def test_all_local_does_not_invoke_cross_repo_gate(monkeypatch):
    """--all-local n'appelle JAMAIS le gate cross-repo (job sans env RAW)."""
    calls: list[int] = []
    real = qg.gate_source_catalog_raw_refs

    def spy(cat):
        calls.append(1)
        return real(cat)

    monkeypatch.setattr(qg, "gate_source_catalog_raw_refs", spy)
    _run_main(monkeypatch, ["--all-local"])
    assert calls == [], "le gate cross-repo ne doit PAS tourner en --all-local (env RAW incapable)"


def test_all_alias_also_skips_cross_repo_gate(monkeypatch):
    """--all (alias rétro-compat, same-repo) ne lance plus non plus le gate cross-repo."""
    calls: list[int] = []
    real = qg.gate_source_catalog_raw_refs

    def spy(cat):
        calls.append(1)
        return real(cat)

    monkeypatch.setattr(qg, "gate_source_catalog_raw_refs", spy)
    _run_main(monkeypatch, ["--all"])
    assert calls == [], "le gate cross-repo ne doit PAS tourner en --all (same-repo uniquement)"
