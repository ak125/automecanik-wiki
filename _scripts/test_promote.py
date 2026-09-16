#!/usr/bin/env python3
"""
Tests pour promote.py (ADR-083). Miroir de la discipline build_exports_seo /
gates : tests statiques (0 LLM / 0 DB / 0 nouveau gate / no-op par défaut) +
tests de la porte tiered par injection de gates factices (pas de dépendance
au runtime réel des 5 gates).
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

PROMOTE_PATH = Path(__file__).resolve().parent / "promote.py"


def _load_promote():
    spec = importlib.util.spec_from_file_location("_promote", PROMOTE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SRC = PROMOTE_PATH.read_text(encoding="utf-8")


@pytest.mark.parametrize("with_shadow", [False, True])
def test_promoted_full_document_matches_frontmatter_schema(tmp_path, with_shadow):
    """The executor must serialize a schema-valid document, including audit metadata."""
    mod = _load_promote()
    fixture = PROMOTE_PATH.parent / "tests/fixtures/valid-non-safety-filtre.md"
    fm, body = mod._parse_markdown(fixture)
    fm["review_status"] = "in_review"  # schema fixture starts draft; executor requires submission
    decision = {"gate_status": {}, "confidence_score": 0.9}
    if with_shadow:
        decision["shadow_score"] = mod._compute_shadow(fm, body, fixture, PROMOTE_PATH.parent.parent)
    out = _apply_fixture(mod, tmp_path / "proposals/test.md", fm, body, tmp_path, decision)
    saved, _ = mod._parse_markdown(out)
    schema_path = PROMOTE_PATH.parent.parent / "_meta/schema/frontmatter.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(saved)
    assert saved["review_status"] == "approved"
    assert saved["validation_mode"] == "automatic"


# --- Tests statiques (garde-fous architecturaux) ------------------------------
def test_no_llm_imports():
    assert not re.search(r"\b(anthropic|openai|groq|cohere|mistralai|google\.generativeai)\b", SRC)


def test_no_db_imports():
    assert not re.search(r"\b(psycopg|asyncpg|supabase|sqlalchemy|django)\b", SRC)


def test_no_new_gate_defined():
    # promote COMPOSE les gates existants, n'en (re)définit aucun.
    assert not re.search(r"def\s+gate_\w+", SRC)
    assert not re.search(r"def\s+run_\w+_gate", SRC)


def test_default_threshold_is_reachable_quality_floor():
    mod = _load_promote()
    assert mod.AUTO_PROMOTE_THRESHOLD == 0.85


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


def test_default_threshold_allows_qualified_content_without_human(tmp_path):
    mod = _load_promote()
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=mod.AUTO_PROMOTE_THRESHOLD, gates=_gates(True),
                          compute_score=lambda *a: 1.00)
    assert d["tier"] == "A", d["blocking_reasons"]


@pytest.mark.parametrize('score,expected',[(0.849,'B'),(0.85,'A'),(0.99,'A')])
def test_automatic_quality_floor(score, expected, tmp_path):
    mod = _load_promote()
    d = mod.evaluate_tier(FM_OK, 'body', tmp_path/'p.md', tmp_path,
                          threshold=mod.AUTO_PROMOTE_THRESHOLD, gates=_gates(True),
                          compute_score=lambda *a: score)
    assert d['tier'] == expected


@pytest.mark.parametrize('threshold',['0.0','0.84','1.01'])
def test_cli_refuses_quality_floor_bypass(threshold, tmp_path):
    from click.testing import CliRunner
    mod = _load_promote()
    result = CliRunner().invoke(mod.main,['--wiki-root',str(tmp_path),'--all','--threshold',threshold])
    assert result.exit_code == 2


def test_human_metadata_is_replaced_on_automatic_validation(tmp_path):
    mod = _load_promote()
    fm = {**FM_OK,'validation_mode':'human_required','reviewed_by':'old-reviewer'}
    out = _apply_fixture(mod, tmp_path/'proposals'/'x.md',fm,'body',tmp_path,
                              {'gate_status':{},'confidence_score':0.9})
    saved,_ = mod._parse_markdown(out)
    assert saved['validation_mode'] == 'automatic'
    assert saved['reviewed_by'].startswith('skill:promoter@')


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
    out = _apply_fixture(mod, tmp_path / "proposals" / "x.md", FM_OK, "body", tmp_path,
                              {"gate_status": {}, "confidence_score": 0.9})
    assert out == (tmp_path / "wiki" / "gamme" / "filtre-a-huile.md").resolve()
    written = out.read_text(encoding="utf-8")
    assert "review_status: approved" in written
    assert "auto_promoted: true" in written
    assert "validation_mode: automatic" in written
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
        _apply_fixture(mod, tmp_path / "proposals" / "x.md", FM_OK, "body", tmp_path,
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
    out = _apply_fixture(mod, prop, FM_OK, "body", tmp_path,
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
    out = _apply_fixture(mod, stray, FM_OK, "body", tmp_path,
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
    out = _apply_fixture(mod, tmp_path / "proposals" / "x.md", FM_OK, "body", tmp_path, decision)
    written = out.read_text(encoding="utf-8")
    assert "shadow_score" in written
    assert "shadow_tier" in written


def test_shadow_evidence_omitted_when_none(tmp_path):
    """Rétro-compat : decision sans shadow (ou shadow=None) → promotion_evidence inchangée."""
    mod = _load_promote()
    (tmp_path / "wiki" / "gamme").mkdir(parents=True)
    out = _apply_fixture(mod, tmp_path / "proposals" / "x.md", FM_OK, "body", tmp_path,
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
    import promotion_decision as _pd  # evaluate_tier vit ici après le boundary move A+
    monkeypatch.setattr(_pd, "_compute_shadow", lambda *a: {"shadow_tier": "A"})
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.10)
    assert d["tier"] == "B"
    assert any("confidence_score" in r for r in d["blocking_reasons"])


def test_gate_engine_adr088_promotes_on_shadow_A_despite_low_confidence(tmp_path, monkeypatch):
    """Flag ON : substance = tier 6-dim. Shadow A + autres conditions OK → TIER A même si confidence faible."""
    monkeypatch.setenv("PROMOTE_GATE_ENGINE", "adr088_6dim")
    mod = _load_promote()
    import promotion_decision as _pd  # evaluate_tier vit ici après le boundary move A+
    monkeypatch.setattr(_pd, "_compute_shadow", lambda *a: {"shadow_tier": "A"})
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.10)
    assert d["tier"] == "A", d["blocking_reasons"]
    assert d["gate_engine"] == "adr088_6dim"


def test_gate_engine_adr088_blocks_on_shadow_B_despite_high_confidence(tmp_path, monkeypatch):
    """Flag ON : shadow B bloque même si confidence haute (le 6-dim gouverne la substance)."""
    monkeypatch.setenv("PROMOTE_GATE_ENGINE", "adr088_6dim")
    mod = _load_promote()
    import promotion_decision as _pd  # evaluate_tier vit ici après le boundary move A+
    monkeypatch.setattr(_pd, "_compute_shadow", lambda *a: {"shadow_tier": "B"})
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.99)
    assert d["tier"] == "B"
    assert any("shadow_tier=B" in r for r in d["blocking_reasons"])


def test_gate_engine_adr088_fail_closed_on_shadow_error(tmp_path, monkeypatch):
    """Flag ON + shadow indéterminable/erreur → fail-closed : TIER B (jamais d'auto-promo sur erreur)."""
    monkeypatch.setenv("PROMOTE_GATE_ENGINE", "adr088_6dim")
    mod = _load_promote()
    import promotion_decision as _pd  # evaluate_tier vit ici après le boundary move A+
    monkeypatch.setattr(_pd, "_compute_shadow", lambda *a: {"shadow_error": "boom"})
    d = mod.evaluate_tier(FM_OK, "body", tmp_path / "p.md", tmp_path,
                          threshold=0.80, gates=_gates(True), compute_score=lambda *a: 0.99)
    assert d["tier"] == "B"
    assert any("boom" in r or "indéterminable" in r for r in d["blocking_reasons"])



def _cli_snapshot_fixture(tmp_path, monkeypatch):
    import yaml
    from click.testing import CliRunner
    mod = _load_promote()
    source = tmp_path / 'proposals/filtre-a-huile.md'
    source.parent.mkdir(parents=True)
    def document(slug, body):
        return '---\n' + yaml.safe_dump({**FM_OK, 'slug': slug}) + '---\n' + body
    source.write_text(document('filtre-a-huile', 'PRELOADED BODY'))
    monkeypatch.setattr(mod, '_load_gates', lambda: [])
    monkeypatch.setattr(mod, '_load_confidence_fn', lambda: lambda *a: 0.9)
    canonical = mod.canonical_promotion_decision
    def decide(*args, **kwargs):
        return canonical(*args, **kwargs, run_evaluators=lambda *a: (
            {'tier': 'A', 'confidence_score': .9, 'gate_status': {}, 'checks': []},
            {'status': 'PASS'}, {'verdict': 'NEW'}, ([], []), True))
    monkeypatch.setattr(mod, 'canonical_promotion_decision', decide)
    def invoke(output_format='json'):
        return CliRunner().invoke(mod.main, ['--wiki-root', str(tmp_path),
            '--target', str(source), '--apply', '--format', output_format])
    return mod, source, document, decide, invoke


@pytest.mark.parametrize('slug', ['filtre-a-huile', 'filtre-revise'])
def test_cli_applies_content_and_identity_from_evaluated_snapshot(tmp_path, monkeypatch, slug):
    mod, source, document, decide, invoke = _cli_snapshot_fixture(tmp_path, monkeypatch)
    def changed_before_capture(*args, **kwargs):
        source.write_text(document(slug, 'EVALUATED BODY'))
        return decide(*args, **kwargs)
    monkeypatch.setattr(mod, 'canonical_promotion_decision', changed_before_capture)
    result = invoke()
    assert result.exit_code == 0, result.output
    entry, = json.loads(result.stdout)['report']
    assert 'promoted_to' in entry, entry
    output = tmp_path / 'wiki/gamme' / f'{slug}.md'
    assert output.exists()
    fm, body = mod._parse_markdown(output)
    assert fm['slug'] == slug
    assert body == 'EVALUATED BODY'
    if slug != 'filtre-a-huile':
        assert not (output.parent / 'filtre-a-huile.md').exists()


def test_cli_refuses_source_changed_inside_executor_before_write(tmp_path, monkeypatch):
    mod, source, document, _, invoke = _cli_snapshot_fixture(tmp_path, monkeypatch)
    import promotion_decision as core
    def mutate(root):
        source.write_text(document('filtre-a-huile', 'CONCURRENT BODY'))
        return 'fixture'
    monkeypatch.setattr(core, '_wiki_commit_sha', mutate)
    result = invoke()
    assert result.exit_code == 1, result.output
    entry, = json.loads(result.stdout)['report']
    assert 'apply_error' in entry or 'apply_refused' in entry
    assert source.exists() and 'CONCURRENT BODY' in source.read_text()
    assert not (tmp_path / 'wiki/gamme/filtre-a-huile.md').exists()



def _apply_fixture(mod, source, fm, body, root, evaluation):
    import yaml
    import promotion_decision as core
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text('---\n' + yaml.safe_dump(fm) + '---\n' + body)
    decision = {'eligible': True, 'promotion_status': 'ELIGIBLE',
                'evaluation': evaluation,
                'inputs': core.capture_input_manifest(source, root, None, None)}
    return mod.apply_promotion(source, root, decision)



def test_executor_preserves_proposal_changed_during_canonical_write(tmp_path, monkeypatch):
    mod, source, document, _, invoke = _cli_snapshot_fixture(tmp_path, monkeypatch)
    import promotion_decision as core
    replace = core.os.replace
    out = tmp_path / 'wiki/gamme/filtre-a-huile.md'
    def changed(staged, destination):
        result = replace(staged, destination)
        if Path(destination) == out:
            source.write_text(document('filtre-a-huile', 'CONCURRENT PROPOSAL'))
        return result
    monkeypatch.setattr(core.os, 'replace', changed)
    result = invoke()
    assert result.exit_code == 1, result.output
    entry, = json.loads(result.stdout)['report']
    assert 'apply_error' in entry and 'conservée' in entry['apply_error']
    assert 'promoted_to' not in entry
    assert source.exists() and 'CONCURRENT PROPOSAL' in source.read_text()
    assert mod._parse_markdown(out)[1] == 'PRELOADED BODY'


@pytest.mark.parametrize('status', ['draft', 'approved', 'deprecated'])
def test_executor_rechecks_status_of_actual_evaluated_source(tmp_path, monkeypatch, status):
    mod, source, document, decide, invoke = _cli_snapshot_fixture(tmp_path, monkeypatch)
    def changed_before_capture(*args, **kwargs):
        content = document('filtre-a-huile', 'EVALUATED BODY')
        source.write_text(content.replace('review_status: in_review', 'review_status: ' + status))
        return decide(*args, **kwargs)
    monkeypatch.setattr(mod, 'canonical_promotion_decision', changed_before_capture)
    result = invoke()
    assert result.exit_code == 1, result.output
    entry, = json.loads(result.stdout)['report']
    assert 'apply_error' in entry and 'non promouvable' in entry['apply_error']
    assert source.exists()
    assert not (tmp_path / 'wiki/gamme/filtre-a-huile.md').exists()


def test_executor_refuses_bare_evaluation_without_canonical_decision(tmp_path):
    mod = _load_promote()
    source = tmp_path / 'proposal.md'
    source.write_text('preserved fixture')
    with pytest.raises(mod.PromotionInputError, match='APPLY_NOT_ELIGIBLE'):
        mod.apply_promotion(source, tmp_path, {'gate_status': {}, 'confidence_score': .9})
    assert source.read_text() == 'preserved fixture'
    assert not (tmp_path / 'wiki').exists()


def test_executor_hash_check_catches_change_after_first_authorization(tmp_path, monkeypatch):
    mod, source, document, decide, _ = _cli_snapshot_fixture(tmp_path, monkeypatch)
    import promotion_decision as core
    decision = decide(source, tmp_path)
    authorize = core.authorize_apply
    def changed(*args, **kwargs):
        result = authorize(*args, **kwargs)
        source.write_text(document('filtre-a-huile', 'CHANGED AFTER CHECK'))
        return result
    monkeypatch.setattr(core, 'authorize_apply', changed)
    with pytest.raises(mod.PromotionInputError, match='candidate bytes differ'):
        mod.apply_promotion(source, tmp_path, decision)
    assert source.exists()
    assert not (tmp_path / 'wiki/gamme/filtre-a-huile.md').exists()


def test_executor_parses_captured_bytes_without_reopening_source(tmp_path, monkeypatch):
    mod, source, document, decide, _ = _cli_snapshot_fixture(tmp_path, monkeypatch)
    import promotion_decision as core
    decision = decide(source, tmp_path)
    parse = core._parse_markdown
    def changed(path, **kwargs):
        if kwargs.get('source_bytes') is not None:
            source.write_text(document('filtre-revise', 'CHANGED DURING PARSE'))
            fm, body = parse(path, **kwargs)
            assert body == 'PRELOADED BODY'
            assert fm['slug'] == 'filtre-a-huile'
            return fm, body
        return parse(path, **kwargs)
    monkeypatch.setattr(core, '_parse_markdown', changed)
    with pytest.raises(mod.PromotionInputError, match='STALE_DECISION'):
        mod.apply_promotion(source, tmp_path, decision)
    assert source.exists()
    assert not list((tmp_path / 'wiki').glob('*/*.md'))



@pytest.mark.parametrize('failure', ['file_fsync', 'replace'])
def test_atomic_publish_failure_preserves_previous_file_and_proposal(tmp_path, monkeypatch, failure):
    mod, source, _, decide, _ = _cli_snapshot_fixture(tmp_path, monkeypatch)
    import promotion_decision as core
    out = tmp_path / 'wiki/gamme/filtre-a-huile.md'
    out.parent.mkdir(parents=True)
    before = b'---\nreview_status: in_review\n---\nPREVIOUS COMPLETE BODY'
    out.write_bytes(before)
    decision = decide(source, tmp_path)
    def fail(*args, **kwargs):
        raise OSError('injected atomic publication failure')
    monkeypatch.setattr(core.os, 'fsync' if failure == 'file_fsync' else 'replace', fail)
    with pytest.raises(OSError, match='injected atomic'):
        mod.apply_promotion(source, tmp_path, decision)
    assert out.read_bytes() == before
    assert source.exists()
    assert sorted(p.name for p in out.parent.iterdir()) == [out.name]



def test_real_process_lock_serializes_native_promoters(tmp_path, monkeypatch):
    import multiprocessing
    mod, source, _, decide, _ = _cli_snapshot_fixture(tmp_path, monkeypatch)
    decision = decide(source, tmp_path)
    ctx = multiprocessing.get_context('fork')
    started, release = ctx.Event(), ctx.Event()
    results = ctx.Queue()
    def first():
        import promotion_decision as core
        def pause(root):
            started.set()
            if not release.wait(10):
                raise RuntimeError('fixture synchronization timeout')
            return 'fixture'
        core._wiki_commit_sha = pause
        try:
            mod.apply_promotion(source, tmp_path, decision)
            results.put('first:published')
        except Exception as exc:
            results.put('first:' + str(exc))
    def second():
        try:
            mod.apply_promotion(source, tmp_path, decision)
            results.put('second:unexpected-publication')
        except Exception as exc:
            results.put('second:' + str(exc))
    one, two = ctx.Process(target=first), ctx.Process(target=second)
    one.start()
    try:
        assert started.wait(5)
        two.start()
        assert 'second:PROMOTION_BUSY' in results.get(timeout=5)
        assert not (tmp_path / 'wiki/gamme/filtre-a-huile.md').exists()
        release.set()
        assert results.get(timeout=5) == 'first:published'
        one.join(5); two.join(5)
        assert one.exitcode == two.exitcode == 0
        assert not source.exists()
    finally:
        release.set()
        for proc in (one, two):
            if proc.pid is not None:
                if proc.is_alive():
                    proc.kill()
                proc.join(5)
        results.close(); results.join_thread()


def test_sigkill_before_atomic_replace_keeps_old_file_and_releases_lock(tmp_path, monkeypatch):
    import multiprocessing
    mod, source, _, decide, _ = _cli_snapshot_fixture(tmp_path, monkeypatch)
    out = tmp_path / 'wiki/gamme/filtre-a-huile.md'
    out.parent.mkdir(parents=True)
    before = b'---\nreview_status: in_review\n---\nPREVIOUS COMPLETE BODY'
    out.write_bytes(before)
    decision = decide(source, tmp_path)
    ctx = multiprocessing.get_context('fork')
    staged = ctx.Event()
    def interrupted():
        import promotion_decision as core
        def pause(*args):
            staged.set()
            # Parent terminates this owned fixture process after observing staging.
            ctx.Event().wait(10)
            raise RuntimeError('fixture kill did not arrive')
        core.os.replace = pause
        mod.apply_promotion(source, tmp_path, decision)
    worker = ctx.Process(target=interrupted)
    worker.start()
    try:
        assert staged.wait(5)
        assert out.read_bytes() == before  # no partial body was exposed
        assert source.exists()
        worker.kill(); worker.join(5)
        assert worker.exitcode == -9
        # OS released the flock. Leftover .tmp is not a canonical Markdown file.
        assert len(list(out.parent.glob('*.tmp'))) == 1
        mod.apply_promotion(source, tmp_path, decision)
        assert mod._parse_markdown(out)[1] == 'PRELOADED BODY'
        assert not source.exists()
        assert len(list(out.parent.glob('*.md'))) == 1
    finally:
        if worker.is_alive():
            worker.kill()
        worker.join(5)


def test_directory_sync_failure_reports_published_file_and_preserves_proposal(tmp_path, monkeypatch):
    mod, source, _, decide, _ = _cli_snapshot_fixture(tmp_path, monkeypatch)
    import promotion_decision as core
    decision = decide(source, tmp_path)
    fsync = core.os.fsync
    calls = []
    def fail_directory(fd):
        calls.append(fd)
        if len(calls) == 2:
            raise OSError('injected directory sync failure')
        return fsync(fd)
    monkeypatch.setattr(core.os, 'fsync', fail_directory)
    with pytest.raises(mod.PromotionInputError, match='canon publié.*proposal conservée'):
        mod.apply_promotion(source, tmp_path, decision)
    assert source.exists()
    assert mod._parse_markdown(tmp_path / 'wiki/gamme/filtre-a-huile.md')[1] == 'PRELOADED BODY'


@pytest.mark.parametrize('output_format', ['text', 'json'])
def test_cli_apply_failure_has_nonzero_exit_and_visible_error(tmp_path, monkeypatch, output_format):
    mod, source, _, _, invoke = _cli_snapshot_fixture(tmp_path, monkeypatch)
    def fail(*args, **kwargs):
        raise mod.PromotionInputError('PROMOTION_BUSY: injected fixture contention')
    monkeypatch.setattr(mod, 'apply_promotion', fail)
    result = invoke(output_format)
    assert result.exit_code == 1
    assert 'PROMOTION_BUSY' in result.stdout
    assert source.exists()


def test_entity_selection_is_exact_not_substring(tmp_path):
    mod = _load_promote()
    proposals = tmp_path / 'proposals'
    proposals.mkdir()
    for slug in ('filtre', 'filtre-a-air', 'support-filtre'):
        (proposals / f'{slug}.md').write_text('fixture')
    assert mod._candidate_files(tmp_path, None, 'gamme:filtre') == [proposals / 'filtre.md']
    assert mod._candidate_files(tmp_path, None, 'filtre') == [proposals / 'filtre.md']


def test_entity_selection_does_not_replace_missing_entity_by_neighbor(tmp_path):
    mod = _load_promote()
    proposals = tmp_path / 'proposals'
    proposals.mkdir()
    (proposals / 'filtre-a-air.md').write_text('fixture')
    assert mod._candidate_files(tmp_path, None, 'gamme:filtre') == []


@pytest.mark.parametrize('kind,slug', [('vehicle', 'filtre'), ('gamme', 'autre')])
def test_cli_blocks_entity_identity_mismatch_before_evaluation(tmp_path, monkeypatch, kind, slug):
    from click.testing import CliRunner
    mod = _load_promote()
    proposals = tmp_path / 'proposals'
    proposals.mkdir()
    proposal = proposals / 'filtre.md'
    proposal.write_text(f'---\nentity_type: {kind}\nslug: {slug}\nreview_status: in_review\n---\nFixture.\n')
    before = proposal.read_bytes()
    def must_not_evaluate(*args, **kwargs):
        pytest.fail('The requested identity must be checked before evaluating another entity')
    monkeypatch.setattr(mod, 'canonical_promotion_decision', must_not_evaluate)
    result = CliRunner().invoke(mod.main, ['--wiki-root', str(tmp_path), '--entity-id', 'gamme:filtre', '--dry-run', '--format', 'json'])
    assert result.exit_code == 0, result.output
    row = json.loads(result.output)['report'][0]
    assert row['promotion_status'] == 'BLOCKED' and row['eligible'] is False
    assert row['blocking_reasons'][0]['code'] == 'ENTITY_ID_MISMATCH'
    assert proposal.read_bytes() == before
    assert not (tmp_path / 'wiki').exists()


def test_explicit_target_cannot_override_requested_entity_identity(tmp_path):
    from click.testing import CliRunner
    mod = _load_promote()
    proposals = tmp_path / 'proposals'
    proposals.mkdir()
    (proposals / 'autre.md').write_text('---\nentity_type: gamme\nslug: autre\nreview_status: approved\n---\nFixture.\n')
    result = CliRunner().invoke(mod.main, ['--wiki-root', str(tmp_path), '--target', 'proposals/autre.md', '--entity-id', 'gamme:filtre', '--dry-run', '--format', 'json'])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)['report'][0]['promotion_status'] == 'BLOCKED'


def test_native_score_does_not_resolve_links_to_unpromoted_proposals(tmp_path):
    mod = _load_promote()
    (tmp_path / 'proposals').mkdir()
    (tmp_path / 'proposals/related.md').write_text('not canonical')
    body = '[[related]]'
    d = mod.evaluate_tier(FM_OK, body, tmp_path / 'p.md', tmp_path,
                         threshold=.85, gates=[], compute_score=mod._load_confidence_fn())
    assert d['confidence_score'] == .34
    assert d['score_details']['components']['internal_links']['unresolved'] == ['related']
    (tmp_path / 'wiki/gammes').mkdir(parents=True)
    (tmp_path / 'wiki/gammes/related.md').write_text('canonical fixture')
    canonical = mod.evaluate_tier(FM_OK, body, tmp_path / 'p.md', tmp_path,
                         threshold=.85, gates=[], compute_score=mod._load_confidence_fn())
    assert canonical['confidence_score'] == .54


def test_shadow_uses_evaluated_repository_manifest_and_keeps_degradation(tmp_path):
    mod = _load_promote()
    # The actual code checkout has a stale manifest; this evaluated root has none.
    result = mod._compute_shadow(FM_OK, '', tmp_path / 'p.md', tmp_path)
    assert result['manifest_status'] == 'absent'
    assert any('SKIPP' in note for note in result['shadow_notes'])


def test_score_details_and_engine_survive_canonical_evaluation_passthrough():
    import promotion_decision as dec
    details = {'score': .46, 'components': {'sources': {'points': .24}}}
    result = dec._evaluation_passthrough({'confidence_score': .46,
        'gate_engine': 'legacy', 'score_details': details})
    assert result['score_details'] is details
    assert result['gate_engine'] == 'legacy'


def test_detailed_scorer_runs_once_and_its_evidence_is_not_recalculated(tmp_path):
    mod = _load_promote()
    calls = []
    evidence = {'score': .9, 'components': {'fixture': {'points': .9}}}
    def scorer(*args):
        calls.append(args)
        return evidence
    d = mod.evaluate_tier(FM_OK, 'body', tmp_path / 'p.md', tmp_path,
                         threshold=.85, gates=[], compute_score=scorer)
    assert len(calls) == 1
    assert calls[0][2] == tmp_path / 'wiki'
    assert d['score_details'] is evidence
    assert d['confidence_score'] == .9


def test_batch_candidates_exclude_navigation_metadata_but_explicit_target_stays_visible(tmp_path):
    mod = _load_promote()
    proposals = tmp_path / 'proposals'
    proposals.mkdir()
    (proposals / '_index.md').write_text('navigation, not a proposal')
    (proposals / 'actual.md').write_text('candidate')
    assert mod._candidate_files(tmp_path, None, None) == [proposals / 'actual.md']
    assert mod._candidate_files(tmp_path, 'proposals/_index.md', None) == [proposals / '_index.md']
