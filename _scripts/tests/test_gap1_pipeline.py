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


def _score(a, c, floors=None):
    return {"dims": {"A": a, "C": c, "D": 15, "E": 10, "F": 1}, "tier": "B", "floors_failed": floors or []}


def _cov(valid=27, pending_capped=27, candidates=33):
    return {"valid_entries": valid, "entries_page_pending_capped": pending_capped,
            "candidate_sources": candidates}


def test_no_human_verdict_ever() -> None:
    # comportemental : sur toute la matrice d'entrées, aucun verdict ne doit contenir "human"
    seen = set()
    for safety in (True, False):
        for a, c in ((0, 0), (18, 16.7), (30, 20)):
            for cov in (_cov(), _cov(27, 0, 0), _cov(0, 0, 0)):
                for amended in (False, True):
                    fl = [] if a >= 22 else ["A"]
                    seen.add(AR.compute_verdict(safety, _score(a, c, fl), cov, amended)["verdict"])
    assert seen, "au moins un verdict"
    assert not any("human" in v for v in seen), f"aucun verdict humain attendu, vu: {seen}"


def test_safety_blocked_technical_when_page_pending() -> None:
    # disque réel : dim A 18, 27 pages pending, 33 sources candidates → blocage TECHNIQUE (pas humain)
    v = AR.compute_verdict(True, _score(18.0, 16.7, ["A"]), _cov(), adr091_amended=False)
    assert v["verdict"] == "safety_auto_blocked"
    assert "dim_A_floor" in v["gate"]["blocking"]
    assert "page_level_all_captured" in v["gate"]["blocking"]


def test_safety_gate_pass_but_adr091_holds() -> None:
    # planchers OK + pages captured + 0 source pending, mais conditions gate encore à câbler → buildout
    ok = _cov(valid=27, pending_capped=0, candidates=0)
    v = AR.compute_verdict(True, _score(30.0, 20.0, []), ok, adr091_amended=False)
    assert v["verdict"] == "safety_blocked_pending_gate_buildout"  # jamais auto-approuvé tant que gate incomplète


def test_non_safety_auto_promote_eligible() -> None:
    v = AR.compute_verdict(False, _score(30.0, 20.0, []), _cov(0, 0, 0), adr091_amended=False)
    # tier B (pas S/A) → auto_blocked ; on vérifie surtout l'absence de tout état humain
    assert v["verdict"] in ("auto_promote_eligible", "auto_blocked")
    assert "human" not in v["verdict"]


# ---- 11. Lock valeur numérique sécurité (numeric_exactitude) câblé dans la Safety Auto-Gate --------
def _cov_ok():
    return _cov(valid=27, pending_capped=0, candidates=0)  # tous les autres computables PASS


def test_numeric_false_blocks_safety_verdict() -> None:
    # tout le reste passerait, mais valeur numérique non vérifiée → BLOQUE (raison technique)
    v = AR.compute_verdict(True, _score(30.0, 20.0, []), _cov_ok(),
                           adr091_amended=True, numeric_exactitude_verified=False)
    assert v["verdict"] == "safety_auto_blocked"
    assert "numeric_exactitude_verified" in v["gate"]["blocking"]


def test_numeric_true_included_but_not_blocking() -> None:
    # valeur vérifiée → check présent et NON bloquant ; verdict reste buildout (not_yet_wired non vide)
    v = AR.compute_verdict(True, _score(30.0, 20.0, []), _cov_ok(),
                           adr091_amended=True, numeric_exactitude_verified=True)
    assert v["gate"]["computable"]["numeric_exactitude_verified"] is True
    assert "numeric_exactitude_verified" not in v["gate"]["blocking"]
    assert v["verdict"] == "safety_blocked_pending_gate_buildout"  # jamais auto-approuvé (gate incomplète)


def test_numeric_none_is_backward_compatible() -> None:
    # défaut None = check non évalué → absent des computables (compat tests/verdicts existants)
    v = AR.compute_verdict(True, _score(30.0, 20.0, []), _cov_ok(), adr091_amended=True)
    assert "numeric_exactitude_verified" not in v["gate"]["computable"]


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
