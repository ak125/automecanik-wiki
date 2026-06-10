#!/usr/bin/env python3
"""
Tests pour promote.py (ADR-083). Miroir de la discipline build_exports_seo /
gates : tests statiques (0 LLM / 0 DB / 0 nouveau gate / no-op par défaut) +
tests de la porte tiered par injection de gates factices (pas de dépendance
au runtime réel des 5 gates).
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

PROMOTE_PATH = Path(__file__).resolve().parent / "promote.py"


def _load_promote():
    spec = importlib.util.spec_from_file_location("_promote", PROMOTE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SRC = PROMOTE_PATH.read_text(encoding="utf-8")


# --- Tests statiques (garde-fous architecturaux) ------------------------------
def test_no_llm_imports():
    assert not re.search(r"\b(anthropic|openai|groq|cohere|mistralai|google\.generativeai)\b", SRC)


def test_no_db_imports():
    assert not re.search(r"\b(psycopg|asyncpg|supabase|sqlalchemy|django)\b", SRC)


def test_no_new_gate_defined():
    # promote COMPOSE les gates existants, n'en (re)définit aucun.
    assert not re.search(r"def\s+gate_\w+", SRC)
    assert not re.search(r"def\s+run_\w+_gate", SRC)


def test_default_threshold_is_noop():
    mod = _load_promote()
    assert mod.AUTO_PROMOTE_THRESHOLD > 1.0, "défaut doit être no-op (aucune auto-promotion)"


def test_only_l1_l2_eligible_constant():
    mod = _load_promote()
    assert mod.AUTO_PROMOTE_TRUTH_LEVELS == {"L1", "L2"}


# --- Helpers de test ----------------------------------------------------------
def _gate(status):
    return lambda target: SimpleNamespace(status=status)


def _gates(all_pass=True, fail="risk"):
    names = ["source", "claim", "contradiction", "risk", "confidence"]
    return [(n, _gate("pass" if all_pass or n != fail else "fail")) for n in names]


FM_OK = {
    "entity_type": "gamme",
    "slug": "colonne-de-direction",
    "truth_level": "L1",
    "review_status": "in_review",
    "source_refs": [{"kind": "raw"}, {"kind": "web"}],
    "exportable": {"seo": False, "rag": False},
}


# --- Tests de la porte tiered -------------------------------------------------
def test_tier_A_when_all_conditions_met(tmp_path):
    mod = _load_promote()
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.90)
    assert d["tier"] == "A", d["blocking_reasons"]


def test_tier_B_when_gate_fails(tmp_path):
    mod = _load_promote()
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(False, "risk"), compute_score=lambda *a: 0.90)
    assert d["tier"] == "B"
    assert any("gate:risk" in r for r in d["blocking_reasons"])


def test_tier_B_when_score_below_threshold(tmp_path):
    mod = _load_promote()
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.50)
    assert d["tier"] == "B"


def test_tier_B_when_truth_level_l3(tmp_path):
    mod = _load_promote()
    fm = {**FM_OK, "truth_level": "L3"}
    d = mod.evaluate_tier(fm, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.95)
    assert d["tier"] == "B"


def test_tier_B_when_single_source_kind(tmp_path):
    mod = _load_promote()
    fm = {**FM_OK, "source_refs": [{"kind": "raw"}, {"kind": "raw"}]}
    d = mod.evaluate_tier(fm, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.95)
    assert d["tier"] == "B"


def test_default_noop_threshold_blocks_everything(tmp_path):
    mod = _load_promote()
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=mod.AUTO_PROMOTE_THRESHOLD, gates=_gates(True),
                          compute_score=lambda *a: 1.00)
    assert d["tier"] == "B", "le défaut no-op (1.01) doit bloquer même un score parfait (1.00)"


def test_fail_closed_on_score_exception(tmp_path):
    mod = _load_promote()
    def boom(*a):
        raise RuntimeError("indéterminable")
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=boom)
    assert d["tier"] == "B"


def test_apply_writes_only_under_wiki_entity_dir(tmp_path):
    mod = _load_promote()
    (tmp_path / "wiki" / "gamme").mkdir(parents=True)
    out = mod.apply_promotion(tmp_path / "proposals" / "x.md", FM_OK, "body", tmp_path,
                              {"gate_status": {}, "confidence_score": 0.9})
    assert out == (tmp_path / "wiki" / "gamme" / "colonne-de-direction.md").resolve()
    written = out.read_text(encoding="utf-8")
    assert "review_status: approved" in written
    assert "auto_promoted: true" in written
    assert "promotion_tier: A" in written


def test_apply_rejects_entity_outside_canon(tmp_path):
    mod = _load_promote()
    fm = {**FM_OK, "entity_type": "support"}  # support exclu de wiki/<entity>/ SEO
    with pytest.raises(Exception):
        mod._promotion_target_path(tmp_path, fm)


# --- Garde anti-écrasement (durcissement ADR-083) -----------------------------
def _write_canon(tmp_path, slug, status):
    d = tmp_path / "wiki" / "gamme"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.md").write_text(
        f"---\nentity_type: gamme\nslug: {slug}\nreview_status: {status}\n---\nbody\n",
        encoding="utf-8",
    )


def test_canon_already_approved_true_when_approved_exists(tmp_path):
    mod = _load_promote()
    _write_canon(tmp_path, "colonne-de-direction", "approved")
    assert mod._canon_already_approved(tmp_path, FM_OK) is True


def test_canon_already_approved_false_when_absent(tmp_path):
    mod = _load_promote()
    assert mod._canon_already_approved(tmp_path, FM_OK) is False


def test_canon_already_approved_false_when_in_review(tmp_path):
    mod = _load_promote()
    _write_canon(tmp_path, "colonne-de-direction", "in_review")
    assert mod._canon_already_approved(tmp_path, FM_OK) is False


def test_apply_refuses_overwrite_of_approved_canon(tmp_path):
    mod = _load_promote()
    _write_canon(tmp_path, "colonne-de-direction", "approved")
    with pytest.raises(Exception):
        mod.apply_promotion(tmp_path / "proposals" / "x.md", FM_OK, "body", tmp_path,
                            {"gate_status": {}, "confidence_score": 0.9})
