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
    "slug": "filtre-a-huile",
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


def test_tier_B_safety_family_by_slug_never_auto(tmp_path):
    """Invariant sécurité (slug) : famille sécurité-critique détectée par le slug —
    entity_data.family ABSENT, ex: plaquette/colonne-de-direction — → JAMAIS auto-promue,
    même toutes conditions réunies. Revue humaine obligatoire."""
    mod = _load_promote()
    fm = {**FM_OK, "slug": "colonne-de-direction"}  # direction, sans entity_data.family
    d = mod.evaluate_tier(fm, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.99)
    assert d["tier"] == "B"
    assert any("safety:" in r for r in d["blocking_reasons"])


def test_tier_B_safety_family_by_declared_family_never_auto(tmp_path):
    """Invariant sécurité (family) : entity_data.family ∈ familles sécurité → TIER B,
    même si le slug n'a aucun token sécurité."""
    mod = _load_promote()
    fm = {**FM_OK, "entity_data": {"family": "freinage"}}  # slug non-safety + family safety
    d = mod.evaluate_tier(fm, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.99)
    assert d["tier"] == "B"
    assert any("safety:" in r for r in d["blocking_reasons"])


def test_tier_B_numeric_high_harm_torque_routes_to_human(tmp_path):
    """Anti number-swapping : une valeur couple/pression (HIGH-HARM) non auto-vérifiable
    → TIER B (revue humaine), même fiche non-sécurité, toutes autres conditions OK."""
    mod = _load_promote()
    body = "Couple de serrage recommandé : 250 Nm. Pression d'injection 2000 bar."
    d = mod.evaluate_tier(FM_OK, body, tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.99)
    assert d["tier"] == "B"
    assert any("numeric:" in r for r in d["blocking_reasons"])
    assert "250 Nm" in " ".join(d["numeric_flags"]["block"])


def test_tier_A_numeric_descriptive_mm_does_not_block(tmp_path):
    """Les cotes descriptives (mm/µm/°C) sont OBSERVÉES (flag) mais NE bloquent PAS :
    fiche non-sécurité avec seulement des cotes mm reste promouvable."""
    mod = _load_promote()
    body = "Cote de diamètre 280 mm, épaisseur mini 22 mm."
    d = mod.evaluate_tier(FM_OK, body, tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.90)
    assert d["tier"] == "A", d["blocking_reasons"]
    assert d["numeric_flags"]["block"] == []                       # rien à bloquer
    assert any("mm" in o for o in d["numeric_flags"]["observe"])   # mais observé


def test_numeric_flags_always_attached_for_observability(tmp_path):
    """numeric_flags est toujours présent dans la décision (observabilité), même vide."""
    mod = _load_promote()
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.90)
    assert "numeric_flags" in d
    assert d["numeric_flags"] == {"block": [], "observe": []}


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
    assert out == (tmp_path / "wiki" / "gamme" / "filtre-a-huile.md").resolve()
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
    _write_canon(tmp_path, "filtre-a-huile", "approved")
    assert mod._canon_already_approved(tmp_path, FM_OK) is True


def test_canon_already_approved_false_when_absent(tmp_path):
    mod = _load_promote()
    assert mod._canon_already_approved(tmp_path, FM_OK) is False


def test_canon_already_approved_false_when_in_review(tmp_path):
    mod = _load_promote()
    _write_canon(tmp_path, "filtre-a-huile", "in_review")
    assert mod._canon_already_approved(tmp_path, FM_OK) is False


def test_apply_refuses_overwrite_of_approved_canon(tmp_path):
    mod = _load_promote()
    _write_canon(tmp_path, "filtre-a-huile", "approved")
    with pytest.raises(Exception):
        mod.apply_promotion(tmp_path / "proposals" / "x.md", FM_OK, "body", tmp_path,
                            {"gate_status": {}, "confidence_score": 0.9})


# --- Move-semantics (la promotion DÉPLACE, ne copie pas) -----------------------
def test_apply_deletes_source_proposal_after_promotion(tmp_path):
    """La proposal source est supprimée après écriture du canon (slug-uniqueness)."""
    mod = _load_promote()
    prop = tmp_path / "proposals" / "filtre-a-huile.md"
    prop.parent.mkdir(parents=True)
    prop.write_text(
        "---\nentity_type: gamme\nslug: filtre-a-huile\nreview_status: proposed\n---\nbody\n",
        encoding="utf-8",
    )
    out = mod.apply_promotion(prop, FM_OK, "body", tmp_path,
                              {"gate_status": {}, "confidence_score": 0.9})
    assert out.is_file()                         # canon écrit
    assert "review_status: approved" in out.read_text(encoding="utf-8")
    assert not prop.exists()                     # source déplacée (supprimée)


def test_apply_never_deletes_source_outside_proposals(tmp_path):
    """Garde sécurité : un target hors proposals/ n'est JAMAIS supprimé."""
    mod = _load_promote()
    stray = tmp_path / "staging" / "filtre-a-huile.md"
    stray.parent.mkdir(parents=True)
    stray.write_text("---\nentity_type: gamme\nslug: filtre-a-huile\n---\nx\n",
                     encoding="utf-8")
    out = mod.apply_promotion(stray, FM_OK, "body", tmp_path,
                              {"gate_status": {}, "confidence_score": 0.9})
    assert out.is_file()
    assert stray.exists()                        # hors proposals/ → conservé


# --- Shadow scoring (ADR-088 §F : observabilité AVANT cutover, 0-risque) -------
def test_shadow_decision_unchanged_tier_A(tmp_path):
    """(i) Le shadow N'ALTÈRE PAS la décision : conditions legacy OK → toujours TIER A."""
    mod = _load_promote()
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.90)
    assert d["tier"] == "A", d["blocking_reasons"]
    # shadow attaché, mais le tier de porte reste piloté par les critères legacy
    assert "shadow_score" in d


def test_shadow_decision_unchanged_tier_B(tmp_path):
    """(i bis) Même quand le shadow tournerait, un gate fail garde la décision en TIER B."""
    mod = _load_promote()
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(False, "risk"), compute_score=lambda *a: 0.90)
    assert d["tier"] == "B"
    assert any("gate:risk" in r for r in d["blocking_reasons"])
    # blocking_reasons ne contient JAMAIS de raison issue du shadow
    assert not any("shadow" in r.lower() for r in d["blocking_reasons"])


def test_shadow_tier_recorded_in_decision(tmp_path):
    """(ii) Le tier shadow 6-dim est calculé et exposé dans la décision."""
    mod = _load_promote()
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.90)
    shadow = d["shadow_score"]
    assert isinstance(shadow, dict)
    # soit un score nominal (shadow_tier présent), soit une erreur tracée (shadow_error)
    assert ("shadow_tier" in shadow) or ("shadow_error" in shadow)
    if "shadow_tier" in shadow:
        assert shadow["shadow_tier"] in {"S", "A", "B", "C", "D"}
        assert "manifest_status" in shadow
        assert shadow["scorer"].startswith("shadow_score.score")


def test_shadow_recorded_in_promotion_evidence(tmp_path):
    """(ii bis) Le shadow_score est persisté dans promotion_evidence à l'écriture."""
    mod = _load_promote()
    (tmp_path / "wiki" / "gamme").mkdir(parents=True)
    decision = {"gate_status": {}, "confidence_score": 0.9,
                "shadow_score": {"shadow_tier": "B", "shadow_total": 55}}
    out = mod.apply_promotion(tmp_path / "proposals" / "x.md", FM_OK, "body", tmp_path, decision)
    written = out.read_text(encoding="utf-8")
    assert "shadow_score" in written
    assert "shadow_tier" in written


def test_shadow_evidence_omitted_when_none(tmp_path):
    """Rétro-compat : decision sans shadow (ou shadow=None) → promotion_evidence inchangée."""
    mod = _load_promote()
    (tmp_path / "wiki" / "gamme").mkdir(parents=True)
    out = mod.apply_promotion(tmp_path / "proposals" / "x.md", FM_OK, "body", tmp_path,
                              {"gate_status": {}, "confidence_score": 0.9})  # pas de clé shadow
    written = out.read_text(encoding="utf-8")
    assert "shadow_score" not in written  # rien d'ajouté, comportement legacy


def test_compute_shadow_is_fail_closed(tmp_path, monkeypatch):
    """(iii) _compute_shadow ne lève jamais : import/score KO → dict {shadow_error}."""
    mod = _load_promote()
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name in {"shadow_score", "reality_manifest"}:
            raise ImportError("module indisponible (simulé)")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    out = mod._compute_shadow(FM_OK, "body", tmp_path / "p.md", tmp_path)
    assert isinstance(out, dict)
    assert "shadow_error" in out  # erreur tracée, pas d'exception remontée


def test_evaluate_tier_survives_shadow_error(tmp_path, monkeypatch):
    """(iii bis) Même si shadow échoue (import KO), evaluate_tier rend une décision legacy valide."""
    mod = _load_promote()
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name in {"shadow_score", "reality_manifest"}:
            raise ImportError("module indisponible (simulé)")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.90)
    assert d["tier"] == "A", d["blocking_reasons"]           # décision intacte
    assert d["shadow_score"] == {"shadow_error": "module indisponible (simulé)"}


def test_no_db_imports_still_holds_after_shadow_wiring():
    """Garde statique : le wiring shadow n'introduit ni LLM ni DB dans promote.py."""
    src = (Path(__file__).resolve().parent / "promote.py").read_text(encoding="utf-8")
    assert not re.search(r"\b(psycopg|asyncpg|supabase|sqlalchemy|django)\b", src)
    assert not re.search(r"\b(anthropic|openai|groq|cohere|mistralai)\b", src)


# --- Cutover ADR-088 flag-gaté (PROMOTE_GATE_ENGINE) — défaut OFF, fail-closed ----------------
def test_gate_engine_default_is_legacy_unchanged(tmp_path, monkeypatch):
    """Sans flag : substance = confidence_score (comportement historique intact)."""
    monkeypatch.delenv("PROMOTE_GATE_ENGINE", raising=False)
    mod = _load_promote()
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.90)
    assert d["tier"] == "A" and d["gate_engine"] == "legacy"


def test_gate_engine_legacy_blocks_on_low_confidence_ignores_shadow(tmp_path, monkeypatch):
    """Legacy : confidence<seuil bloque même si le shadow serait A (le 6-dim n'est PAS décisionnel)."""
    monkeypatch.delenv("PROMOTE_GATE_ENGINE", raising=False)
    mod = _load_promote()
    monkeypatch.setattr(mod, "_compute_shadow", lambda *a: {"shadow_tier": "A"})
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.10)
    assert d["tier"] == "B"
    assert any("confidence_score" in r for r in d["blocking_reasons"])


def test_gate_engine_adr088_promotes_on_shadow_A_despite_low_confidence(tmp_path, monkeypatch):
    """Flag ON : substance = tier 6-dim. Shadow A + autres conditions OK → TIER A même si confidence faible."""
    monkeypatch.setenv("PROMOTE_GATE_ENGINE", "adr088_6dim")
    mod = _load_promote()
    monkeypatch.setattr(mod, "_compute_shadow", lambda *a: {"shadow_tier": "A"})
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.10)
    assert d["tier"] == "A", d["blocking_reasons"]
    assert d["gate_engine"] == "adr088_6dim"


def test_gate_engine_adr088_blocks_on_shadow_B_despite_high_confidence(tmp_path, monkeypatch):
    """Flag ON : shadow B bloque même si confidence haute (le 6-dim gouverne la substance)."""
    monkeypatch.setenv("PROMOTE_GATE_ENGINE", "adr088_6dim")
    mod = _load_promote()
    monkeypatch.setattr(mod, "_compute_shadow", lambda *a: {"shadow_tier": "B"})
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.99)
    assert d["tier"] == "B"
    assert any("shadow_tier=B" in r for r in d["blocking_reasons"])


def test_gate_engine_adr088_fail_closed_on_shadow_error(tmp_path, monkeypatch):
    """Flag ON + shadow indéterminable/erreur → fail-closed : TIER B (jamais d'auto-promo sur erreur)."""
    monkeypatch.setenv("PROMOTE_GATE_ENGINE", "adr088_6dim")
    mod = _load_promote()
    monkeypatch.setattr(mod, "_compute_shadow", lambda *a: {"shadow_error": "boom"})
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.99)
    assert d["tier"] == "B"
    assert any("boom" in r or "indéterminable" in r for r in d["blocking_reasons"])
