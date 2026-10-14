"""Tests pipeline auto GAP-1 (author_from_raw + gen_coverage_map + gap1_auto_review).

Garde-fous vérifiés (invariants owner 2026-07-02, Option A) :
1. static : 0 import LLM, 0 import DB dans les 3 modules.
2. fail-closed : aspect hors table contrôlée → section NON authored (jamais devinée).
3. editorial émis = sourcé (source_ids depuis les bullets, jamais vide).
4. NE PROMEUT PAS : review_status / exportable de la proposal sont préservés à l'identique.
5. déterminisme : même entrée → même sortie (pas de wall-clock / random).
6. Option A : source hors source-catalog → pending_source_validation, NE compte PAS pour dim A.
7. Option A : source déjà cataloguée (autorité validée) → entrée valide réutilisée.
8. dim D : related_gammes ⊆ manifest gamme_slugs (0 slug inventé).
9. sécurité : fiche freinage → is_safety True (verdict jamais auto).
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

import author_from_raw as A
import gen_coverage_map as CM

SCRIPTS = Path(__file__).resolve().parent.parent


# ---- fixtures hermétiques (aucune dépendance au repo raw réel) --------------------------------
def _mk_proposal(d: Path, slug: str, title: str, review_status="proposed") -> Path:
    fm = {
        "schema_version": "2.0.0", "id": f"gamme:{slug}", "entity_type": "gamme",
        "slug": slug, "title": title, "lang": "fr", "truth_level": "L2",
        "review_status": review_status, "exportable": {"rag": False, "seo": False, "support": False},
        "entity_data": {"pg_id": 82, "family": "freinage"},
    }
    p = d / "proposals"; p.mkdir(parents=True, exist_ok=True)
    (p / f"{slug}.md").write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
                                  + "---\n\n# " + title + "\n", encoding="utf-8")
    return p


def _mk_bucket(raw: Path, slug: str, aspect: str, bullets: list[str],
               sources: list[dict] | None = None) -> None:
    bd = raw / "sources" / "web-research" / slug
    bd.mkdir(parents=True, exist_ok=True)
    fm = {"gamme": slug, "aspect": aspect, "source_type": "web-research"}
    body = "## Faits sourcés\n" + "\n".join(bullets) + "\n"
    (bd / f"{aspect}.md").write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True) + "---\n\n" + body,
                                     encoding="utf-8")
    if sources is not None:
        (bd / "source-index.json").write_text(json.dumps({"gamme": slug, "source_count": len(sources),
                                                           "sources": sources}), encoding="utf-8")


def _mk_manifest(d: Path, slugs: list[str]) -> Path:
    m = {"schema_version": "1", "engine_codes": [], "gamme_slugs": slugs}
    p = d / "reality-manifest.json"; p.write_text(json.dumps(m), encoding="utf-8")
    return p


LONG = "x" * 130  # dépasse MIN_LEN=120
BULLET = f"- {LONG} claim technique sur le disque — https://www.textar.com/tech — high"


# ---- 1. static guards --------------------------------------------------------------------------
def test_no_llm_no_db_imports() -> None:
    forbidden = ["anthropic", "openai", "groq", "cohere", "mistralai",
                 "psycopg", "asyncpg", "supabase", "sqlalchemy"]
    for mod in ("author_from_raw.py", "gen_coverage_map.py", "gap1_auto_review.py"):
        txt = (SCRIPTS / mod).read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in txt, f"{needle} must not appear in {mod}"


# ---- 2. fail-closed : aspect hors table ---------------------------------------------------------
def test_unknown_aspect_skipped(tmp_path: Path) -> None:
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _mk_bucket(tmp_path, "disque-de-frein", "aspect_bidon_hors_table", [BULLET])
    md, rep = A.author("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []))
    assert rep["editorial_sections"] == 0, "aspect hors table → aucune section"
    assert any(s.get("skip") == "aspect_hors_table" for s in rep["skipped"])


# ---- 3. editorial sourcé -----------------------------------------------------------------------
def test_editorial_has_sources(tmp_path: Path) -> None:
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _mk_bucket(tmp_path, "disque-de-frein", "selection_criteria", [BULLET])
    md, rep = A.author("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []))
    fm, _ = A._split_fm(md)
    ed = fm["entity_data"]["editorial"]
    assert ed, "editorial émis"
    for sec, blk in ed.items():
        assert blk["source_ids"], f"{sec} sans source_ids"
        assert blk["truth_level"] == "sourced"


# ---- 4. ne promeut pas -------------------------------------------------------------------------
def test_does_not_mutate_review_status(tmp_path: Path) -> None:
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein", review_status="proposed")
    _mk_bucket(tmp_path, "disque-de-frein", "selection_criteria", [BULLET])
    md, _ = A.author("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []))
    fm, _ = A._split_fm(md)
    assert fm["review_status"] == "proposed", "review_status intact (pas de promotion)"
    assert fm["exportable"] == {"rag": False, "seo": False, "support": False}, "exportable intact"


# ---- 5. déterminisme ---------------------------------------------------------------------------
def test_deterministic(tmp_path: Path) -> None:
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _mk_bucket(tmp_path, "disque-de-frein", "selection_criteria", [BULLET])
    m = _mk_manifest(tmp_path, [])
    a, _ = A.author("disque-de-frein", tmp_path, pdir, m)
    b, _ = A.author("disque-de-frein", tmp_path, pdir, m)
    assert a == b, "sortie non déterministe"


# ---- 6. Option A : source inconnue = pending, ne compte pas ------------------------------------
def test_unknown_source_pending_not_counted(tmp_path: Path, monkeypatch) -> None:
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _mk_bucket(tmp_path, "disque-de-frein", "selection_criteria", [BULLET],
               sources=[{"url": "https://www.textar.com/tech", "domain": "textar.com", "level": "oe"}])
    # catalog VIDE → textar inconnu
    empty_cat = tmp_path / "_meta"; empty_cat.mkdir(parents=True, exist_ok=True)
    (empty_cat / "source-catalog.yaml").write_text("sources: []\n", encoding="utf-8")
    monkeypatch.setattr(CM, "SOURCE_CATALOG", empty_cat / "source-catalog.yaml")
    md, _ = A.author("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []))
    cov, rep = CM.generate("disque-de-frein", md, tmp_path)
    assert rep["valid_entries"] == 0, "source inconnue ne doit PAS produire d'entrée valide (dim A)"
    doms = {s["domain"] for s in rep["sources_to_validate"]}
    assert "textar.com" in doms
    assert all(s["status"] == "pending_source_validation" for s in rep["sources_to_validate"])


# ---- 7a. publisher validé + page pending_capture → medium MAX (durcissement page-level) --------
def test_cataloged_pending_page_capped_medium(tmp_path: Path, monkeypatch) -> None:
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _mk_bucket(tmp_path, "disque-de-frein", "selection_criteria", [BULLET])  # bullet conf = high
    meta = tmp_path / "_meta"; meta.mkdir(parents=True, exist_ok=True)
    (meta / "source-catalog.yaml").write_text(yaml.safe_dump({"sources": [
        {"slug": "textar_oem_disque", "type": "oem_manual", "status": "to_capture",
         "title": "Textar textar.com disque"}]}), encoding="utf-8")
    monkeypatch.setattr(CM, "SOURCE_CATALOG", meta / "source-catalog.yaml")
    md, _ = A.author("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []))
    cov, rep = CM.generate("disque-de-frein", md, tmp_path)
    e = cov["coverage_entries"][0]
    assert e["source_slug"] == "textar_oem_disque"
    assert e["confidence"] == "medium", "page pending_capture → high rabattu à medium (publisher ≠ preuve)"
    assert e["source_policy"] == "2_medium_concordant", "pending page → jamais 1_high"
    assert e["source_status"] == "pending_capture"


# ---- 7b. publisher validé + page captured → high / 1_high possible ----------------------------
def test_cataloged_captured_page_can_be_high(tmp_path: Path, monkeypatch) -> None:
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _mk_bucket(tmp_path, "disque-de-frein", "selection_criteria", [BULLET])  # bullet conf = high
    meta = tmp_path / "_meta"; meta.mkdir(parents=True, exist_ok=True)
    (meta / "source-catalog.yaml").write_text(yaml.safe_dump({"sources": [
        {"slug": "textar_oem_disque", "type": "oem_manual", "status": "active",  # active + raw_ref (G1) → coverage captured
         "raw_ref": {"repo": "automecanik-raw", "manifest_id": "textar_oem_disque"},
         "title": "Textar textar.com disque"}]}), encoding="utf-8")
    monkeypatch.setattr(CM, "SOURCE_CATALOG", meta / "source-catalog.yaml")
    md, _ = A.author("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []))
    cov, rep = CM.generate("disque-de-frein", md, tmp_path)
    e = cov["coverage_entries"][0]
    assert e["confidence"] == "high", "page captured + publisher validé + claim ancré → high possible"
    assert e["source_policy"] == "1_high"
    assert e["source_status"] == "captured"


# ---- 8. dim D : related_gammes ⊆ manifest ------------------------------------------------------
def test_related_gammes_manifest_validated(tmp_path: Path) -> None:
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _mk_bucket(tmp_path, "disque-de-frein", "selection_criteria", [BULLET])
    manifest = _mk_manifest(tmp_path, ["plaquette-de-frein", "etrier-de-frein"])  # only 2 known
    md, rep = A.author("disque-de-frein", tmp_path, pdir, manifest)
    rg = rep.get("related_gammes") or []
    assert set(rg) <= {"plaquette-de-frein", "etrier-de-frein"}, "aucun slug hors-manifest"
    assert "liquide-de-frein" not in rg, "slug famille absent du manifest → exclu"


# ---- 9. sécurité : freinage détecté ------------------------------------------------------------
def test_safety_family_detected() -> None:
    import safety_families as sf
    assert sf.is_safety_proposal({"slug": "disque-de-frein", "title": "Disque de frein"}) is True


# ---- 10. Safety Auto-Gate : plus de `human_review` ; verdicts auto (technique vs gouvernance) --
import gap1_auto_review as AR  # noqa: E402


def _cov(valid=27, pending_capped=27, candidates=33):
    return {"valid_entries": valid, "entries_page_pending_capped": pending_capped,
            "candidate_sources": candidates}


def _decision(status="BLOCKED", reasons=()):
    return {"promotion_status": status, "eligible": status == "ELIGIBLE", "blocking_reasons": list(reasons)}


def _safety_reason(blocking=(), adr=None):
    return {"code": "SAFETY_HUMAN_REVIEW", "evidence": {
        "is_safety": True, "blocking_conditions": list(blocking),
        "policy": {"auto_approval_adr": adr, "status": "ratified" if adr else "not_ratified"}}}


POLICY_ONLY = _decision(reasons=[_safety_reason()])
ELIGIBLE = _decision("ELIGIBLE")


def test_no_human_verdict_ever() -> None:
    # comportemental : sur toute la matrice d'entrées, aucun verdict ne doit contenir "human"
    seen = set()
    decisions = (None, ELIGIBLE, POLICY_ONLY, _decision(reasons=[_safety_reason(["dim_A_floor"])]),
                 _decision("UNKNOWN_FAIL_CLOSED", [{"code": "PROVENANCE_GATE_UNAVAILABLE"}]))
    for safety in (True, False):
        for cov in (_cov(), _cov(27, 0, 0), _cov(0, 0, 0)):
            for pdz in decisions:
                seen.add(AR.compute_verdict(safety, cov, promotion_decision=pdz)["verdict"])
    assert seen >= {"safety_auto_blocked", "blocked_by_current_safety_policy", "safety_auto_approved",
                    "auto_promote_eligible", "auto_blocked"}, seen
    assert not any("human" in v for v in seen), f"aucun verdict humain attendu, vu: {seen}"


def test_safety_blocked_technical_when_page_pending() -> None:
    # disque réel : 27 pages pending, 33 sources candidates, plancher A KO côté canonique → TECHNIQUE
    pdz = _decision(reasons=[_safety_reason(["dim_A_floor"])])
    v = AR.compute_verdict(True, _cov(), promotion_decision=pdz)
    assert v["verdict"] == "safety_auto_blocked"
    assert {"dim_A_floor", "page_level_all_captured", "no_pending_source_validation"} <= set(
        v["gate"]["blocking"])


def test_safety_all_proven_but_policy_unratified_holds() -> None:
    ok = _cov(valid=27, pending_capped=0, candidates=0)
    v = AR.compute_verdict(True, ok, numeric_exactitude_verified=True, source_catalog_raw_refs_ok=True,
                           promotion_decision=POLICY_ONLY)
    assert v["verdict"] == "blocked_by_current_safety_policy"
    assert v["gate"]["blocking"] == [] and v["gate"]["policy_only"] is True
    assert v["gate"]["canonical"]["policy"]["status"] == "not_ratified"


def test_safety_auto_approved_only_on_canonical_eligible_and_raw_claims_proven() -> None:
    ok = _cov(valid=27, pending_capped=0, candidates=0)
    v = AR.compute_verdict(True, ok, numeric_exactitude_verified=True, source_catalog_raw_refs_ok=True,
                           promotion_decision=ELIGIBLE)
    assert v["verdict"] == "safety_auto_approved"
    # canonique ELIGIBLE mais un claim RAW non prouvé → bloqué (union, jamais l'un sans l'autre)
    v2 = AR.compute_verdict(True, ok, numeric_exactitude_verified=False, promotion_decision=ELIGIBLE)
    assert v2["verdict"] == "safety_auto_blocked"
    assert v2["gate"]["blocking"] == ["numeric_exactitude_verified"]


def test_safety_without_or_with_unexplained_canonical_decision_is_blocked() -> None:
    ok = _cov(valid=27, pending_capped=0, candidates=0)
    v = AR.compute_verdict(True, ok, promotion_decision=None)
    assert v["verdict"] == "safety_auto_blocked"
    assert "canonical_decision_available" in v["gate"]["blocking"]
    malformed = {"promotion_status": "BLOCKED", "eligible": False, "blocking_reasons": []}
    v2 = AR.compute_verdict(True, ok, promotion_decision=malformed)
    assert v2["gate"]["blocking"] == ["canonical_decision_eligible"]
    unreported = _decision(reasons=[{"code": "SAFETY_HUMAN_REVIEW", "evidence": {"is_safety": True}}])
    v3 = AR.compute_verdict(True, ok, promotion_decision=unreported)
    assert v3["gate"]["blocking"] == ["canonical_safety_conditions_reported"]


def test_safety_other_canonical_codes_block_alongside_safety_conditions() -> None:
    ok = _cov(valid=27, pending_capped=0, candidates=0)
    pdz = _decision("UNKNOWN_FAIL_CLOSED", [_safety_reason(["provenance_pass"]),
                                            {"code": "PROVENANCE_GATE_UNAVAILABLE"}])
    v = AR.compute_verdict(True, ok, promotion_decision=pdz)
    assert v["verdict"] == "safety_auto_blocked"
    assert v["gate"]["blocking"] == ["provenance_pass", "PROVENANCE_GATE_UNAVAILABLE"]


def test_safety_reason_separates_unavailable_from_failing_conditions() -> None:
    """Une condition canonique non évaluable faute d'entrée est nommée comme telle, à part des
    échecs ; la condition RAW homonyme, elle, reste un échec de contenu."""
    ok = _cov(valid=27, pending_capped=0, candidates=0)
    head = "Safety Auto-Gate KO (raisons techniques, PAS besoin humain) : "
    absent = "non évaluables dans ce contexte (entrée absente) : "
    cases = [
        (["dim_A_floor", "proof_sources_min"], ["proof_sources_min"], None,
         "dim_A_floor ; " + absent + "proof_sources_min"),
        (["proof_sources_min", "numeric_exactitude_verified"],
         ["proof_sources_min", "numeric_exactitude_verified"], None,
         absent + "proof_sources_min, numeric_exactitude_verified"),
        (["numeric_exactitude_verified"], ["numeric_exactitude_verified"], False,
         "numeric_exactitude_verified ; " + absent + "numeric_exactitude_verified"),
        # Décision incohérente (non évaluable hors des conditions bloquantes) : ignorée, bloqué.
        (["dim_A_floor"], ["proof_sources_min"], None, "dim_A_floor"),
    ]
    for blocking, unavailable, numeric, expected in cases:
        reason = _safety_reason(blocking)
        reason["evidence"]["unavailable_conditions"] = unavailable
        v = AR.compute_verdict(True, ok, numeric_exactitude_verified=numeric,
                               promotion_decision=_decision(reasons=[reason]))
        assert v["verdict"] == "safety_auto_blocked"
        assert v["reason"] == head + expected, v["reason"]


def test_non_safety_auto_promote_eligible() -> None:
    v = AR.compute_verdict(False, _cov(0, 0, 0), promotion_decision=ELIGIBLE)
    assert v["verdict"] == "auto_promote_eligible"
    assert "human" not in v["verdict"]


def test_gap1_has_no_policy_override_of_its_own() -> None:
    """La politique sécurité n'a qu'une source : la constante canonique. Aucune option CLI."""
    import inspect
    assert "adr091" not in inspect.getsource(AR).lower()
    assert "SAFETY_AUTO_APPROVAL_ADR" in inspect.getsource(AR)


# ---- A4 : gap1 = REPORTER — embarque la décision canonique, ne décide plus la promotion --------
import promotion_decision as PD  # noqa: E402


def _mk_proposal_nonsafety(d: Path, slug: str, title: str) -> Path:
    fm = {
        "schema_version": "2.0.0", "id": f"gamme:{slug}", "entity_type": "gamme",
        "slug": slug, "title": title, "lang": "fr", "truth_level": "L2",
        "review_status": "proposed", "exportable": {"rag": False, "seo": False, "support": False},
        "entity_data": {"pg_id": 42, "family": "filtration"},  # non-sécurité
    }
    p = d / "proposals"; p.mkdir(parents=True, exist_ok=True)
    (p / f"{slug}.md").write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
                                  + "---\n\n# " + title + "\n", encoding="utf-8")
    return p


def test_compute_verdict_nonsafety_delegates_to_canonical_decision() -> None:
    """A4 : la promotion NON-sécurité vient de la décision canonique EMBARQUÉE, jamais
    d'un tier/floor local. eligible=True ⇒ auto_promote_eligible ; sinon auto_blocked."""
    elig = {"promotion_status": "ELIGIBLE", "eligible": True, "blocking_reasons": []}
    v = AR.compute_verdict(False, _cov(), promotion_decision=elig)
    assert v["verdict"] == "auto_promote_eligible"  # pages pending côté RAW, mais décision canonique ELIGIBLE
    blocked = {"promotion_status": "BLOCKED", "eligible": False,
               "blocking_reasons": [{"code": "COVERAGE_STRICT_FAIL"}]}
    v2 = AR.compute_verdict(False, _cov(), promotion_decision=blocked)
    assert v2["verdict"] == "auto_blocked"
    assert "COVERAGE_STRICT_FAIL" in v2["reason"]


def test_compute_verdict_nonsafety_no_decision_is_failclosed() -> None:
    """Aucune décision canonique fournie ⇒ auto_blocked (fail-closed), jamais eligible."""
    v = AR.compute_verdict(False, _cov(), promotion_decision=None)
    assert v["verdict"] == "auto_blocked"


def test_review_embeds_canonical_promotion_decision(tmp_path: Path, monkeypatch) -> None:
    """A4 (embed) : review() embarque l'OBJET PromotionDecision canonique tel quel
    (schema_version + promotion_status + eligible + blocking_reasons typés)."""
    monkeypatch.setenv("AUTOMECANIK_RAW_PATH", str(tmp_path / "raw-absent"))
    pdir = _mk_proposal_nonsafety(tmp_path, "filtre-a-huile", "Filtre à huile")
    _mk_bucket(tmp_path, "filtre-a-huile", "selection_criteria", [BULLET])
    rep = AR.review("filtre-a-huile", tmp_path, pdir, _mk_manifest(tmp_path, []), tmp_path / "shadow")
    assert rep["safety_family"] is False
    pdz = rep["promotion_decision"]
    assert pdz["schema_version"] == PD.SCHEMA_VERSION
    assert pdz["promotion_status"] in ("ELIGIBLE", "BLOCKED", "UNKNOWN_FAIL_CLOSED")
    assert isinstance(pdz["eligible"], bool)
    for r in pdz["blocking_reasons"]:
        assert set(("code", "owner_stage", "detector_stage", "evidence")) <= set(r)
    # le verdict gap1 dérive de la décision canonique (jamais un calcul local)
    assert (rep["verdict"] == "auto_promote_eligible") == (pdz["eligible"] is True)


def test_review_promotion_decision_matches_direct_canonical_call(tmp_path: Path, monkeypatch) -> None:
    """A4 (adversarial, hermétique) : gap1.promotion_decision == canonical_promotion_decision()
    en direct sur le MÊME shadow fiche. La COLLECTE réelle (gates click+pydantic) est remplacée
    par un fake runner injecté (le job minimal reste click/pydantic-free) ; la VRAIE
    decide_promotion décide. gap1 EMBARQUE l'objet — 0 reconstruction, 0 redécision, 0 divergence."""
    monkeypatch.setenv("AUTOMECANIK_RAW_PATH", str(tmp_path / "raw-absent"))
    calls = {"n": 0}

    def fake_runner(candidate_path, wiki_root, raw_root, baseline_path, threshold, gates, compute_score):
        calls["n"] += 1
        substance = {
            "tier": "A", "confidence_score": 0.9,
            "gate_status": {"source": "pass", "claim": "pass", "contradiction": "pass",
                            "risk": "pass", "confidence": "pass"},
            "checks": [],  # substance PASS (aucune raison de blocage côté substance)
            "shadow_score": {"shadow_tier": "A"},
            "numeric_flags": {"block": [], "observe": []},
        }
        # coverage FAIL ⇒ un code de blocage DÉTERMINISTE (équalité de codes non vacante).
        return substance, {"status": "FAIL", "fails": ["source_slug FK absent"]}, {"verdict": "NEW"}, ([], []), True

    # Le MÊME fake pour les DEUX chemins : gap1.review (interne) + l'appel direct.
    # canonical_promotion_decision(run_evaluators=None) résout _run_real_evaluators au module.
    monkeypatch.setattr(PD, "_run_real_evaluators", fake_runner)
    pdir = _mk_proposal_nonsafety(tmp_path, "filtre-a-air", "Filtre à air")
    _mk_bucket(tmp_path, "filtre-a-air", "selection_criteria", [BULLET])
    workdir = tmp_path / "shadow"
    rep = AR.review("filtre-a-air", tmp_path, pdir, _mk_manifest(tmp_path, []), workdir)
    assert calls["n"] == 1  # gap1 = exactement UNE collecte par décision (pas de double exécution)
    embedded = rep["promotion_decision"]
    direct = PD.canonical_promotion_decision(workdir / "filtre-a-air.md", workdir, raw_root=tmp_path)
    assert calls["n"] == 2  # +1 collecte pour l'appel direct
    keys = ("promotion_status", "eligible", "substance_tier")
    assert {k: embedded.get(k) for k in keys} == {k: direct.get(k) for k in keys}
    codes = sorted(r["code"] for r in embedded["blocking_reasons"])
    assert codes == sorted(r["code"] for r in direct["blocking_reasons"])
    assert codes == ["COVERAGE_STRICT_FAIL"]  # équalité prouvée sur une décision NON triviale


# ---- A5 : ensemble autoritaire DÉRIVÉ du SoT PAR RÔLE (editorial_role=proof ∧ high), 0 hardcode ---
def _load_qg_a5():
    import importlib.util
    p = SCRIPTS / "quality-gates.py"
    spec = importlib.util.spec_from_file_location("_qg_a5", p)
    qg = importlib.util.module_from_spec(spec); spec.loader.exec_module(qg)
    return qg


def _sot_high_types():
    qg = _load_qg_a5()
    return {t for t, c in qg.SOURCE_TYPE_TO_MAX_CONFIDENCE.items() if str(c).lower() == "high"}


def _sot_proof_types():
    qg = _load_qg_a5()
    return {t for t, r in qg.SOURCE_TYPE_EDITORIAL_ROLE.items() if r == "proof"}


def test_authoritative_types_derived_from_sot_not_hardcoded() -> None:
    """A5 : l'ensemble autoritaire = {types high du SoT} ∩ {types editorial_role=proof} — DÉRIVÉ
    PAR RÔLE depuis le SoT, plus aucune blocklist hardcodée (`_G2_PAUSED_AUTHORITATIVE_TYPES`
    supprimé). Fin de la dérive : les 3 phantoms hardcodés (db_owned/manufacturer_official/tecdoc
    bare) disparaissent ; les vrais types high-proof (oem_workshop…) apparaissent."""
    auth = set(CM._authoritative_types())
    expected = _sot_high_types() & _sot_proof_types()
    assert auth == expected
    # phantoms hardcodés éliminés
    assert not ({"db_owned", "manufacturer_official", "tecdoc"} & auth)
    # vrai type high-proof précédemment manquant, désormais présent
    assert "oem_workshop" in auth


def test_tecdoc_official_non_authoritative_by_corroboration_role() -> None:
    """Frontière PAR RÔLE (owner 2026-07-06) : tecdoc_official est `high` au SoT mais son
    editorial_role = `corroboration` → exclu du set autoritaire PAR SON RÔLE, plus par une
    blocklist hardcodée. TecDoc corrobore, ne PROUVE pas (vérité catalogue = DB Massdoc)."""
    qg = _load_qg_a5()
    assert "tecdoc_official" in _sot_high_types()                          # bien high au SoT
    assert qg.SOURCE_TYPE_EDITORIAL_ROLE["tecdoc_official"] == "corroboration"
    assert "tecdoc_official" not in CM._authoritative_types()              # jamais autoritaire ici


def test_authoritative_high_is_editor_cap_not_auto_proof(tmp_path: Path, monkeypatch) -> None:
    """`high` = plafond d'autorité ÉDITEUR, JAMAIS preuve automatique : un type autoritaire
    SANS raw_ref (page non prouvée) ⇒ capé medium/pending_capture (pas de fail-open)."""
    entry_no_rawref = {"status": "active", "type": "oem_workshop"}  # autoritaire mais pas is_page_proven
    assert CM.is_page_proven(entry_no_rawref) is False
    entry_proven = {"status": "active", "type": "oem_workshop",
                    "raw_ref": {"repo": "automecanik-raw", "manifest_id": "m1"}}
    assert CM.is_page_proven(entry_proven) is True


# ---- A6 : fail-open raw_ref non-safety fermé (enforcé par la décision canonique embarquée) --------
def test_no_local_raw_ref_safety_conditional_failopen() -> None:
    """A6 : plus de `if safety else None` local sur le raw_ref — le non-safety n'est plus
    ignoré localement, il est ENFORCÉ par la décision canonique (provenance)."""
    src = (SCRIPTS / "gap1_auto_review.py").read_text(encoding="utf-8")
    assert "raw_refs_ok if safety else None" not in src, "fail-open non-safety raw_ref doit être retiré"


def test_review_nonsafety_raw_ref_enforced_no_failopen(tmp_path: Path, monkeypatch) -> None:
    """A6 (hermétique) : provenance KO d'une fiche NON-safety ⇒ fail-closed via la décision
    canonique embarquée (plus de fail-open local). Le fake runner fournit des SORTIES
    d'évaluateurs réalistes (substance A, quality/coverage/regression PASS, provenance FAIL) ;
    la VRAIE decide_promotion calcule le verdict — jamais un 'fake returns blocked'."""
    monkeypatch.setenv("AUTOMECANIK_RAW_PATH", str(tmp_path / "raw-absent"))

    def fake_runner(candidate_path, wiki_root, raw_root, baseline_path, threshold, gates, compute_score):
        substance = {
            "tier": "A", "confidence_score": 0.9,
            "gate_status": {"source": "pass", "claim": "pass", "contradiction": "pass",
                            "risk": "pass", "confidence": "pass"},
            "checks": [],  # substance PASS
            "shadow_score": {"shadow_tier": "A"},
            "numeric_flags": {"block": [], "observe": []},
        }
        # provenance = FAIL (raw_ref CONTENU invalide, pas un défaut d'infra ; RAW disponible)
        return (substance, {"status": "PASS"}, {"verdict": "NEW"},
                (["raw_ref invalide: filtre-carburant"], []), True)

    monkeypatch.setattr(PD, "_run_real_evaluators", fake_runner)
    pdir = _mk_proposal_nonsafety(tmp_path, "filtre-carburant", "Filtre à carburant")
    _mk_bucket(tmp_path, "filtre-carburant", "selection_criteria", [BULLET])
    rep = AR.review("filtre-carburant", tmp_path, pdir, _mk_manifest(tmp_path, []), tmp_path / "shadow")
    assert rep["safety_family"] is False
    pdz = rep["promotion_decision"]
    codes = [r["code"] for r in pdz["blocking_reasons"]]
    assert pdz["eligible"] is False
    assert pdz["promotion_status"] == "BLOCKED"        # provenance FAIL = définitif (pas UNKNOWN_FAIL_CLOSED)
    assert pdz["substance_tier"] == "A"                # dimension substance PRÉSERVÉE (jamais un faux B)
    assert "PROVENANCE_RAW_REF_FAIL" in codes          # le vrai code de refus provenance (non fail-open)


# ---- A7 : comptabilité de perte RAW (conservation) + fail-closed 0-fait --------------------------
def _write_bucket_raw(raw: Path, slug: str, filename: str, text: str) -> None:
    bd = raw / "sources" / "web-research" / slug
    bd.mkdir(parents=True, exist_ok=True)
    (bd / filename).write_text(text, encoding="utf-8")


def test_extraction_accounting_conservation(tmp_path: Path) -> None:
    """A7 : chaque input_item_id éligible tombe dans EXACTEMENT un état final ; l'équation
    de conservation ferme (eligible == consumed + unmapped + intentional_drop + unsupported)."""
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _mk_bucket(tmp_path, "disque-de-frein", "selection_criteria", [BULLET])       # → consumed
    _mk_bucket(tmp_path, "disque-de-frein", "aspect_bidon_hors_table", [BULLET])  # → unmapped
    _, rep = A.author("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []))
    acct = rep["extraction_accounting"]
    assert acct["conservation_ok"] is True
    assert acct["eligible_input_count"] == (acct["consumed_count"] + acct["unmapped_count"]
                                            + acct["intentional_drop_count"]
                                            + acct["unsupported_format_count"])
    assert acct["consumed_count"] >= 1 and acct["unmapped_count"] >= 1
    # extracted = métrique intermédiaire séparée (bullets parsés), pas dans l'équation
    assert acct["extracted_count"] == (acct["consumed_count"] + acct["unmapped_count"]
                                       + acct["intentional_drop_count"])


def test_unmapped_is_visible_never_silent(tmp_path: Path) -> None:
    """A7 : unmapped_count>0 est VISIBLE (jamais un drop silencieux)."""
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _mk_bucket(tmp_path, "disque-de-frein", "aspect_bidon_hors_table", [BULLET])
    _, rep = A.author("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []))
    acct = rep["extraction_accounting"]
    assert acct["unmapped_count"] >= 1
    assert any(it["state"] == "unmapped" for it in acct["items"])


def test_zero_extracted_from_nonempty_raw_is_hard_fail(tmp_path: Path) -> None:
    """A7 (P0) : RAW non vide (candidats présents) mais 0 fait extrait (format cassé) ⇒
    échec dur — jamais un candidat « réussi » silencieux."""
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    # section reconnue MAIS lignes candidates qui NE matchent PAS le format bullet
    _write_bucket_raw(tmp_path, "disque-de-frein", "selection_criteria.md",
                      "---\naspect: selection_criteria\n---\n\n## Faits sourcés\n"
                      "- une phrase sans url ni niveau de confiance\n"
                      "- autre ligne au mauvais format\n")
    _, rep = A.author("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []))
    acct = rep["extraction_accounting"]
    assert acct["eligible_input_count"] > 0
    assert acct["extracted_count"] == 0
    assert acct["unsupported_format_count"] == acct["eligible_input_count"]
    assert rep["hard_fail"] is not None
    assert rep["authored"] is False  # cesse de prétendre avoir authoré


def test_bucket_without_facts_section_is_unsupported_not_silent(tmp_path: Path) -> None:
    """A7 : un bucket non-vide SANS section '## Faits sourcés' (format facet/.full.md invisible
    au reader) ⇒ unsupported_format (compté), jamais perdu en silence."""
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _write_bucket_raw(tmp_path, "disque-de-frein", "identification.full.md",
                      "---\naspect: selection_criteria\n---\n\n## Autre format\n"
                      "contenu facet-keyed que le reader ne sait pas extraire\n")
    _, rep = A.author("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []))
    acct = rep["extraction_accounting"]
    assert acct["unsupported_format_count"] >= 1
    assert any(it["state"] == "unsupported_format" and it["input_item_id"].endswith("::FILE")
               for it in acct["items"])


def test_intentional_drop_requires_reason_never_catchall(tmp_path: Path) -> None:
    """A7 : INTENTIONAL_DROP n'est JAMAIS la poubelle verte — il exige reason_code + policy.
    Un parser incapable (mauvais format) ⇒ unsupported_format, jamais intentional_drop."""
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _write_bucket_raw(tmp_path, "disque-de-frein", "selection_criteria.md",
                      "---\naspect: selection_criteria\n---\n\n## Faits sourcés\n"
                      "- ligne au mauvais format\n")
    _, rep = A.author("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []))
    for it in rep["extraction_accounting"]["items"]:
        if it["state"] == "intentional_drop":
            assert it.get("reason_code") and it.get("policy")
        if it["state"] == "unsupported_format":
            assert it["state"] != "intentional_drop"  # jamais reclassé en drop


def test_main_hard_fail_exits_nonzero(tmp_path: Path) -> None:
    """A7 : le CLI author_from_raw sort non-zéro sur un échec dur (0-fait extrait)."""
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _write_bucket_raw(tmp_path, "disque-de-frein", "selection_criteria.md",
                      "---\naspect: selection_criteria\n---\n\n## Faits sourcés\n- mauvais format\n")
    out = tmp_path / "shadow.md"
    rc = A.main(["--slug", "disque-de-frein", "--raw-root", str(tmp_path),
                 "--proposals-dir", str(pdir), "--manifest", str(_mk_manifest(tmp_path, [])),
                 "--out", str(out)])
    assert rc != 0


# ---- 11. Lock valeur numérique sécurité (numeric_exactitude) câblé dans la Safety Auto-Gate --------
def _cov_ok():
    return _cov(valid=27, pending_capped=0, candidates=0)  # tous les autres computables PASS


def test_numeric_false_blocks_safety_verdict() -> None:
    # tout le reste passerait, mais valeur numérique RAW non vérifiée → BLOQUE (raison technique)
    v = AR.compute_verdict(True, _cov_ok(), numeric_exactitude_verified=False, promotion_decision=ELIGIBLE)
    assert v["verdict"] == "safety_auto_blocked"
    assert "numeric_exactitude_verified" in v["gate"]["blocking"]


def test_numeric_true_included_but_not_blocking() -> None:
    v = AR.compute_verdict(True, _cov_ok(), numeric_exactitude_verified=True, promotion_decision=POLICY_ONLY)
    assert v["gate"]["raw_claims"]["numeric_exactitude_verified"] is True
    assert "numeric_exactitude_verified" not in v["gate"]["blocking"]
    assert v["verdict"] == "blocked_by_current_safety_policy"  # jamais auto-approuvé sans la politique


def test_numeric_none_is_not_evaluated() -> None:
    # défaut None = check non évalué → absent des conditions RAW
    v = AR.compute_verdict(True, _cov_ok(), promotion_decision=POLICY_ONLY)
    assert "numeric_exactitude_verified" not in v["gate"]["raw_claims"]


def test_resolve_status_requires_valid_section() -> None:
    # HAUTE 5 (auto-review) : _resolve_status applique le MÊME gate `section ∈ valid_sections` que generate().
    catalog = {"domain_to_slug": {"brembo.com": "brembo"},
               "slugs": {"brembo": {"type": "oem_manual", "status": "active",
                                    "raw_ref": {"manifest_id": "brembo_x"}}}}  # active + raw_ref (G1) → captured
    valid = {"## Critères de sélection"}
    c_ok = {"domain": "brembo.com", "section": "## Critères de sélection"}
    c_bad_section = {"domain": "brembo.com", "section": "## Section fantôme"}
    c_unknown_domain = {"domain": "forum.example", "section": "## Critères de sélection"}
    assert AR._resolve_status(c_ok, catalog, valid) == "captured"
    assert AR._resolve_status(c_bad_section, catalog, valid) == "pending_capture"  # section invalide → fail-closed
    assert AR._resolve_status(c_unknown_domain, catalog, valid) == "pending_capture"


# ---- 12. Gate raw_ref cross-repo (Plan P2) câblé dans la Safety Auto-Gate (point 4 owner) --------
def test_raw_ref_gate_false_blocks_safety_verdict() -> None:
    # échec FK/hash du gate source-catalog/raw-ref → BLOQUE le verdict sécurité (raison technique)
    v = AR.compute_verdict(True, _cov_ok(), numeric_exactitude_verified=True,
                           source_catalog_raw_refs_ok=False, promotion_decision=ELIGIBLE)
    assert v["verdict"] == "safety_auto_blocked"
    assert "source_catalog_raw_refs_ok" in v["gate"]["blocking"]


def test_raw_ref_gate_true_included_and_policy_still_holds() -> None:
    v = AR.compute_verdict(True, _cov_ok(), numeric_exactitude_verified=True,
                           source_catalog_raw_refs_ok=True, promotion_decision=POLICY_ONLY)
    assert v["gate"]["raw_claims"]["source_catalog_raw_refs_ok"] is True
    assert "source_catalog_raw_refs_ok" not in v["gate"]["blocking"]
    assert v["verdict"] == "blocked_by_current_safety_policy", "jamais auto-approuvé sans la politique"


def test_raw_ref_gate_none_is_not_evaluated() -> None:
    v = AR.compute_verdict(True, _cov_ok(), promotion_decision=POLICY_ONLY)
    assert "source_catalog_raw_refs_ok" not in v["gate"]["raw_claims"]


def test_raw_ref_gate_helper_flags_unreferenceable_source() -> None:
    # le gate EXISTANT (gate_source_catalog_raw_refs) tourne RÉELLEMENT : entrée active sans raw_ref
    # ni archived_at → source_unreferenceable → ok=False (contrôle structural, sans raw inventory).
    ok, failures, warnings = AR._raw_ref_gate({"broken": {"status": "active", "type": "oem_manual"}})
    assert ok is False
    assert any("source_unreferenceable" in f for f in failures)


def test_raw_ref_gate_helper_ok_when_to_capture() -> None:
    # to_capture → pas de check (état attendu) → ok, non bloquant
    ok, failures, warnings = AR._raw_ref_gate(
        {"pending": {"status": "to_capture", "raw_ref": {"repo": "automecanik-raw", "manifest_id": "x"}}})
    assert ok is True
    assert failures == []


def test_review_wires_raw_ref_gate(tmp_path: Path, monkeypatch) -> None:
    # point 4 : review() invoque RÉELLEMENT le gate raw_ref → champ d'observabilité présent + alimente le verdict sécurité.
    monkeypatch.setenv("AUTOMECANIK_RAW_PATH", str(tmp_path / "raw-absent"))  # inventory absent → hermétique
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _mk_bucket(tmp_path, "disque-de-frein", "selection_criteria", [BULLET])
    meta = tmp_path / "_meta"; meta.mkdir(parents=True, exist_ok=True)
    # catalog avec une entrée CASSÉE (active sans raw_ref) → gate FAIL → doit remonter
    (meta / "source-catalog.yaml").write_text(yaml.safe_dump({"sources": [
        {"slug": "broken_src", "type": "oem_manual", "status": "active", "title": "broken"}]}), encoding="utf-8")
    monkeypatch.setattr(CM, "SOURCE_CATALOG", meta / "source-catalog.yaml")
    rep = AR.review("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []), tmp_path / "shadow")
    assert "source_catalog_raw_refs" in rep, "review() doit exposer le résultat du gate raw_ref"
    assert rep["source_catalog_raw_refs"]["ok"] is False
    assert any("source_unreferenceable" in f for f in rep["source_catalog_raw_refs"]["failures"])
    # sécurité (freinage) + gate FAIL → verdict bloqué avec la raison raw_ref
    assert "source_catalog_raw_refs_ok" in (rep.get("safety_auto_gate") or {}).get("blocking", [])


def test_review_names_conditions_unavailable_in_the_shadow_workdir(tmp_path: Path, monkeypatch) -> None:
    """Workdir shadow sans `_meta/source-catalog.yaml` : la décision canonique y est rendue,
    compose `proof_sources_min` UNAVAILABLE en condition non évaluable, et le verdict la nomme
    comme telle, jamais comme un échec. Hermétique : la COLLECTE réelle (gates click+pydantic,
    projections des exporteurs) est remplacée par un fake runner injecté (le job minimal reste
    click/pydantic-free) ; la VRAIE decide_promotion compose. Que le catalogue absent rende la
    condition UNAVAILABLE est prouvé sur le vrai calcul par
    test_promotion_decision.py::test_safety_local_conditions_absent_catalog_are_unavailable."""
    monkeypatch.setenv("AUTOMECANIK_RAW_PATH", str(tmp_path / "raw-absent"))
    meta = tmp_path / "_meta"; meta.mkdir(parents=True, exist_ok=True)
    (meta / "source-catalog.yaml").write_text(yaml.safe_dump({"sources": []}), encoding="utf-8")
    monkeypatch.setattr(CM, "SOURCE_CATALOG", meta / "source-catalog.yaml")
    missing = "_meta/source-catalog.yaml absent de l'arbre évalué"
    evaluated = []

    def fake_runner(candidate_path, wiki_root, raw_root, baseline_path, threshold, gates, compute_score):
        evaluated.append((Path(wiki_root), (Path(wiki_root) / "_meta" / "source-catalog.yaml").exists()))
        local = {"conditions": {"dim_A_floor": True, "proof_sources_min": False},
                 "details": {"dim_A_floor": {"value": 30.0, "floor": 20.0},
                             "proof_sources_min": {"status": "UNAVAILABLE", "missing_input": missing}}}
        substance = {
            "tier": "B", "confidence_score": 0.9,
            "gate_status": {"source": "pass", "claim": "pass", "contradiction": "pass",
                            "risk": "pass", "confidence": "pass"},
            "checks": [{"code": "SAFETY_HUMAN_REVIEW", "status": "fail", "owner_stage": "POLICY_SAFETY",
                        "evidence": {"is_safety": True, **local}}],
            "shadow_score": {"shadow_tier": "A"},
            "numeric_flags": {"block": [], "observe": []},
        }
        return substance, {"status": "PASS", "fails": []}, {"verdict": "NEW"}, ([], []), True

    monkeypatch.setattr(PD, "_run_real_evaluators", fake_runner)
    pdir = _mk_proposal(tmp_path, "disque-de-frein", "Disque de frein")
    _mk_bucket(tmp_path, "disque-de-frein", "selection_criteria", [BULLET])
    workdir = tmp_path / "shadow"
    rep = AR.review("disque-de-frein", tmp_path, pdir, _mk_manifest(tmp_path, []), workdir)
    assert evaluated == [(workdir, False)]  # une décision, rendue sur le workdir sans catalogue
    safety = next(r for r in rep["promotion_decision"]["blocking_reasons"]
                  if r["code"] == "SAFETY_HUMAN_REVIEW")
    assert safety["evidence"]["details"]["proof_sources_min"] == {
        "status": "UNAVAILABLE", "missing_input": missing}
    assert safety["evidence"]["unavailable_conditions"] == ["proof_sources_min"]
    assert rep["safety_auto_gate"]["canonical"]["safety_unavailable_conditions"] == ["proof_sources_min"]
    failing, unavailable = rep["verdict_reason"].split(
        " ; non évaluables dans ce contexte (entrée absente) : ")
    assert unavailable == "proof_sources_min" and "proof_sources_min" not in failing
