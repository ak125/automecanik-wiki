#!/usr/bin/env python3
"""
Tests de l'auto-review de sens (ADR-119 D2, D3, D8) : `semantic_review.py` et son branchement dans
`promotion_decision.py`.

Précondition (d) d'ADR-119 D4 : la condition `semantic_auto_review_pass` est fausse pour une
exécution absente, périmée, incomplète, en erreur ou illisible ; un FAIL n'est jamais remplacé par
un PASS sur la même clé ; le branchement vaut quelle que soit `SAFETY_AUTO_APPROVAL_ADR`.

Discipline test_promote : 0 LLM / 0 DB. Les exécutions sont écrites à la main, ou produites par
l'exécuteur avec un relecteur simulé, dans un dépôt git temporaire, avec une capture RAW temporaire.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import semantic_review as sr  # noqa: E402
import semantic_review_executor as sre  # noqa: E402

CAPTURE_PATH = "sources/auto-captures/plaquette-test/capture.md"
CAPTURE = ("# Remplacement\n\nToujours remplacer les plaquettes par essieu complet.\n"
           "Contrôler l'épaisseur minimale   indiquée par le constructeur.\n")
QUOTE = "remplacer les plaquettes par essieu complet"
BODY = ("## Rôle technique\n\nLa plaquette frotte sur le disque.\n\n"
        "- Remplacer par essieu.\n- Contrôler l'épaisseur.\n\n"
        "| Pièce | Usure |\n|---|---|\n| Plaquette | Oui |\n\n"
        "> Attention au rodage.\n\n```\nnote\n```\n")


def _load_decision():
    spec = importlib.util.spec_from_file_location("_promotion_decision_sr", SCRIPTS_DIR / "promotion_decision.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid",
                           "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
                          cwd=root, check=True, capture_output=True, text=True).stdout


def _commit(root: Path, message: str = "test") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "--allow-empty", "-m", message)


@pytest.fixture
def w(tmp_path):
    """WIKI temporaire versionné (schéma d'exécution copié) et RAW temporaire à une capture."""
    root, raw = tmp_path / "wiki", tmp_path / "raw"
    capture = raw / CAPTURE_PATH
    capture.parent.mkdir(parents=True)
    capture.write_text(CAPTURE, encoding="utf-8")
    cid = "sha256:" + hashlib.sha256(capture.read_bytes()).hexdigest()
    (root / sr.RUN_SCHEMA_RELPATH).parent.mkdir(parents=True)
    shutil.copy(SCRIPTS_DIR.parent / sr.RUN_SCHEMA_RELPATH, root / sr.RUN_SCHEMA_RELPATH)
    _git(root, "init", "-q")
    _commit(root, "init")
    fm = {"entity_type": "gamme", "slug": "plaquette-test", "title": "Plaquette",
          "source_refs": [{"kind": "raw", "path": CAPTURE_PATH, "cid": cid},
                          {"kind": "external_url", "url": "https://example.invalid/a"}]}
    return SimpleNamespace(root=root, raw=raw, fm=fm, body=BODY, cid=cid)


def _refutation(w, i, verdict, quote=QUOTE):
    passage = None if quote is None else {"path": CAPTURE_PATH, "cid": w.cid, "quote": quote}
    return {"refuter_id": f"r{i}", "model": "model-a", "verdict": verdict, "passage": passage}


def _candidate(w, klass, verdicts, *, quotes=None, cid="c1"):
    quotes = quotes or [QUOTE] * len(verdicts)
    return {"id": cid, "class": klass, "segment_id": "body:2", "claim_ids": ["a1"],
            "statement": "La fiche omet le remplacement par essieu.", "raised_by": ["p0"],
            "refutations": [_refutation(w, i, v, q) for i, (v, q) in enumerate(zip(verdicts, quotes))]}


def _run(w, *, fm=None, body=None, candidates=(), passes=2, drop_segment=False, error=None):
    packet = sr.build_packet(fm or w.fm, body or w.body, w.raw)
    segments = [{"id": s["id"], "sha256": s["sha256"], "no_claims": True} for s in packet["segments"]]
    for s in segments:
        if s["id"] == "body:2":  # « La plaquette frotte sur le disque. »
            del s["no_claims"]
            s["claims"] = [{"id": "a1", "text": "La plaquette frotte sur le disque.", "kind": "affirmation"}]
    if drop_segment:
        segments = [s for s in segments if s["id"] != "body:1"]
    ids = [s["id"] for s in segments]
    run = {"schema_version": sr.SCHEMA_VERSION, "key": packet["key"], "key_inputs": packet["key_inputs"],
           "models": ["model-a", "model-b"], "segments": segments,
           "passes": [{"pass_id": f"p{i}", "model": "model-b", "covered_segments": ids}
                      for i in range(passes)],
           "candidates": list(candidates)}
    if error:
        run["error"] = error
    return run


def _record(w, run, *, commit=True):
    path = sr.record_run(w.root, w.fm["slug"], w.fm, w.body, run)
    if commit:
        _commit(w.root, "run")
    return path


def _status(w, fm=None, body=None):
    return sr.review_status(w.root, w.fm["slug"], fm or w.fm, body or w.body, w.raw)


# --- Statut de la fiche (D3) --------------------------------------------------------------

def test_absent_run_is_never_a_pass(w):
    status = _status(w)
    assert status["status"] == "ABSENT" and status["pass"] is False


def test_clean_run_passes_and_traces_d8_fields(w):
    _record(w, _run(w))
    status = _status(w)
    assert status["status"] == "PASS" and status["pass"] is True, status
    run = status["runs"][0]
    assert run["verdict"] == "PASS"
    assert run["confirmed_by_class"] == {"valeur": 0, "securite": 0, "sens": 0, "formulation": 0}
    assert run["dismissed"] == 0 and run["unsettled_share"] is None
    assert status["key"] == sr.review_key(w.fm, w.body)[0]


def test_candidate_dismissed_by_three_anchored_refutations(w):
    """Citation retrouvée malgré casse d'origine, espaces et retour à la ligne normalisés."""
    _record(w, _run(w, candidates=[_candidate(w, "securite", ["refuted"] * 3, quotes=[
        QUOTE, "Contrôler l'épaisseur minimale indiquée", "Toujours remplacer les plaquettes"])]))
    status = _status(w)
    assert status["pass"] is True, status
    assert status["runs"][0]["dismissed"] == 1


@pytest.mark.parametrize("verdicts, quotes, unsettled", [
    # Un passage introuvable dans la capture confirme le candidat, même réfuté.
    (["refuted"] * 3, [QUOTE, QUOTE, "remplacer une seule plaquette"], 1),
    # Aucune capture ne tranche : le candidat reste confirmé.
    (["refuted", "refuted", "undecidable"], [QUOTE, QUOTE, None], 1),
    # Écart confirmé par un passage : tranché.
    (["refuted", "upheld", "refuted"], [QUOTE] * 3, 0),
])
def test_candidate_not_unanimously_refuted_with_passage_is_confirmed(w, verdicts, quotes, unsettled):
    _record(w, _run(w, candidates=[_candidate(w, "sens", verdicts, quotes=quotes)]))
    status = _status(w)
    assert status["status"] == "FAIL" and status["pass"] is False, status
    run = status["runs"][0]
    assert run["confirmed_by_class"]["sens"] == 1
    assert run["unsettled_confirmed"] == unsettled
    assert run["unsettled_share"] == float(unsettled)


def test_passage_from_an_uncited_capture_never_dismisses(w):
    candidate = _candidate(w, "valeur", ["refuted"] * 3)
    candidate["refutations"][0]["passage"]["cid"] = "sha256:" + "0" * 64
    _record(w, _run(w, candidates=[candidate]))
    status = _status(w)
    assert status["status"] == "FAIL" and status["runs"][0]["confirmed_by_class"]["valeur"] == 1


def test_fewer_refuters_than_protocol_leaves_candidate_pending(w):
    _record(w, _run(w, candidates=[_candidate(w, "securite", ["refuted"] * 2)]))
    status = _status(w)
    assert status["status"] == "INCOMPLETE" and status["pass"] is False, status
    assert status["runs"][0]["pending"] == 1


def test_formulation_discrepancy_does_not_block(w):
    _record(w, _run(w, candidates=[_candidate(w, "formulation", ["upheld"] * 3)]))
    status = _status(w)
    assert status["pass"] is True, status
    assert status["runs"][0]["confirmed_by_class"]["formulation"] == 1


@pytest.mark.parametrize("kwargs, expected", [
    ({"passes": 1}, "INCOMPLETE"),
    ({"drop_segment": True}, "INCOMPLETE"),
    ({"error": "délai dépassé"}, "ERROR"),
])
def test_incomplete_or_errored_run_is_never_a_pass(w, kwargs, expected):
    _record(w, _run(w, **kwargs))
    status = _status(w)
    assert status["status"] == expected and status["pass"] is False, status


def test_blocking_discrepancy_fails_even_when_review_is_incomplete(w):
    _record(w, _run(w, passes=1, candidates=[_candidate(w, "valeur", ["upheld"])]))
    assert _status(w)["status"] == "FAIL"


def test_run_for_a_previous_text_is_stale(w):
    _record(w, _run(w))
    changed = w.body.replace("frotte sur", "serre")
    status = _status(w, body=changed)
    assert status["status"] == "STALE" and status["pass"] is False


def test_key_binds_published_text_captures_and_protocol(w, monkeypatch):
    key, inputs = sr.review_key(w.fm, w.body)
    assert inputs["captures"] == [{"path": CAPTURE_PATH, "cid": w.cid}]
    assert inputs["protocol_revision"] == sr.protocol_revision()
    assert sr.review_key(w.fm, w.body + "Ajout.\n")[0] != key
    assert sr.review_key({**w.fm, "title": "Autre"}, w.body)[0] != key
    monkeypatch.setitem(sr.PROTOCOL, "refuters_min", 4)
    assert sr.review_key(w.fm, w.body)[0] != key


def test_fail_is_never_replaced_by_a_pass_on_the_same_key(w):
    _record(w, _run(w, candidates=[_candidate(w, "securite", ["upheld"] * 3)]))
    _record(w, _run(w))
    status = _status(w)
    assert sorted(r["verdict"] for r in status["runs"]) == ["FAIL", "PASS"]
    assert status["status"] == "FAIL" and status["pass"] is False


def test_removed_fail_is_a_history_gap(w):
    failed = _record(w, _run(w, candidates=[_candidate(w, "securite", ["upheld"] * 3)]))
    failed.unlink()
    _record(w, _run(w))
    status = _status(w)
    assert status["status"] == "HISTORY_GAP" and status["pass"] is False, status
    assert any("retirée" in gap for gap in status["history_gaps"])


def test_uncommitted_or_modified_run_is_a_history_gap(w):
    path = _record(w, _run(w), commit=False)
    assert _status(w)["status"] == "HISTORY_GAP"
    _commit(w.root)
    assert _status(w)["status"] == "PASS"
    path.write_text(path.read_text(encoding="utf-8").replace("model-a", "model-c"), encoding="utf-8")
    assert _status(w)["status"] == "HISTORY_GAP"


def test_unreadable_run_blocks(w):
    key = sr.review_key(w.fm, w.body)[0]
    _record(w, _run(w))
    key_dir = w.root / sr.REVIEW_DIR / w.fm["slug"] / key
    (key_dir / ("f" * 64 + ".json")).write_text("{}\n", encoding="utf-8")
    _commit(w.root)
    status = _status(w)
    assert status["status"] == "UNREADABLE" and status["pass"] is False, status
    assert status["unreadable"][0]["error"].startswith("nom différent")


@pytest.mark.parametrize("mutate", [
    lambda run: run["candidates"][0].update(raised_by=["p9"]),
    lambda run: run["candidates"][0]["refutations"][0].update(model="model-z"),
    lambda run: run["candidates"][0].update(segment_id="body:99"),
    lambda run: run["candidates"][0].update(claim_ids=["a9"]),
    lambda run: run["passes"].append(dict(run["passes"][0])),
    lambda run: run.update(key="0" * 64),
    lambda run: run.update(verdict="PASS"),
])
def test_run_with_inconsistent_references_is_invalid(w, mutate):
    run = _run(w, candidates=[_candidate(w, "sens", ["refuted"] * 3)])
    mutate(run)
    with pytest.raises(sr.RunInvalid):
        sr.validate_run(run, sr.load_run_schema(w.root))


def test_record_refuses_a_run_for_another_text(w):
    run = _run(w)
    with pytest.raises(sr.RunInvalid):
        sr.record_run(w.root, w.fm["slug"], w.fm, w.body + "\nAjout.\n", run)


def test_shallow_or_absent_history_is_unavailable(w, tmp_path):
    _record(w, _run(w))
    shallow = tmp_path / "shallow"
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{w.root}", str(shallow)],
                   check=True, capture_output=True)
    with pytest.raises(sr.ReviewInputUnavailable):
        sr.review_status(shallow, w.fm["slug"], w.fm, w.body, w.raw)
    plain = tmp_path / "plain"
    shutil.copytree(w.root, plain, ignore=shutil.ignore_patterns(".git"))
    with pytest.raises(sr.ReviewInputUnavailable):
        sr.review_status(plain, w.fm["slug"], w.fm, w.body, w.raw)


def test_capture_bytes_must_match_their_cid(w):
    (w.raw / CAPTURE_PATH).write_text(CAPTURE + "ajout\n", encoding="utf-8")
    with pytest.raises(ValueError, match="capture_cid_mismatch"):
        _status(w)
    (w.raw / CAPTURE_PATH).unlink()
    with pytest.raises(sr.ReviewInputUnavailable):
        _status(w)


@pytest.mark.parametrize("ref, code", [
    ({"kind": "raw", "path": CAPTURE_PATH}, "capture_ref_unpinned"),
    ({"kind": "raw", "path": "../hors-raw.md", "cid": "sha256:" + "0" * 64}, "capture_ref_malformed"),
    ({"kind": "raw", "path": "/abs.md", "cid": "sha256:" + "0" * 64}, "capture_ref_malformed"),
    ({"kind": "raw", "path": CAPTURE_PATH, "cid": "0" * 64}, "capture_ref_malformed"),
])
def test_capture_reference_must_be_pinned_and_relative(w, ref, code):
    with pytest.raises(ValueError, match=code):
        sr.cited_captures({**w.fm, "source_refs": [ref]})


def test_fiche_without_raw_capture_never_passes(w):
    fm = {**w.fm, "source_refs": [{"kind": "external_url", "url": "https://example.invalid/a"}]}
    status = _status(w, fm=fm)
    assert status["status"] == "NO_CAPTURE" and status["pass"] is False


@pytest.mark.parametrize("slug", ["", "../x", "a/b", ".cache", None])
def test_slug_must_be_a_single_safe_path_segment(w, slug):
    with pytest.raises(ValueError, match="slug_malformed"):
        sr.review_status(w.root, slug, w.fm, w.body, w.raw)


# --- Protocole, schéma, découpage -----------------------------------------------------------

def test_protocol_is_never_looser_than_adr_119():
    assert sr.PROTOCOL["detection_passes_min"] >= 2
    assert sr.PROTOCOL["refuters_min"] >= 3
    assert sr.PROTOCOL["refutation"] == "unanimous_with_capture_passage"
    assert {"valeur", "securite", "sens"} <= set(sr.PROTOCOL["blocking_classes"])
    assert set(sr.PROTOCOL["blocking_classes"]) <= set(sr.PROTOCOL["classes"])


def test_run_schema_matches_the_module():
    schema = json.loads((SCRIPTS_DIR.parent / sr.RUN_SCHEMA_RELPATH).read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == sr.SCHEMA_VERSION
    assert schema["$defs"]["candidate"]["properties"]["class"]["enum"] == sr.PROTOCOL["classes"]


def _body_lines(segments):
    return [line for s in segments if s["id"].startswith("body:")
            for line in s["text"].split("\n") if line.strip()]


@pytest.mark.parametrize("body", [
    BODY,
    "Texte sans titre\nsur deux lignes\n\n\n* puce\n  suite\n\n1. un\n2. deux\n",
    "<div>\nhtml\n</div>\n\n---\n\n    code indenté\n\nfin",
    "",
])
def test_segmenter_is_a_deterministic_total_partition(body):
    first = sr.segments({"slug": "x"}, body)
    assert first == sr.segments({"slug": "x"}, body)
    assert _body_lines(first) == [line for line in body.split("\n") if line.strip()]
    assert len({s["id"] for s in first}) == len(first)


def test_segmenter_covers_every_published_frontmatter_field():
    fm = {"b": [1, 2], "a": {"x": "é"}}
    segments = sr.segments(fm, "")
    assert [s["id"] for s in segments] == ["fm:a", "fm:b"]
    assert "é" in segments[0]["text"]


def test_segmenter_covers_the_real_safety_fiche_when_present():
    dec = _load_decision()
    path = SCRIPTS_DIR.parent / "wiki" / "gamme" / "plaquette-de-frein.md"
    if not path.is_file():
        pytest.skip("fiche plaquette-de-frein absente de cet arbre")
    fm, body = dec._parse_markdown(path)
    segments = sr.segments(dec._published_frontmatter(fm), body)
    assert _body_lines(segments) == [line for line in body.split("\n") if line.strip()]


# --- Frontmatter publié : proposition et canon promu partagent la clé ------------------------

PROPOSAL_FM = {
    "entity_type": "gamme", "slug": "plaquette-test", "title": "Plaquette",
    "review_status": "in_review", "exportable": {"seo": False, "rag": False},
    "provenance": {"ingested_by": "test"},
    "diagnostic_relations": [{"symptom_slug": "bruit", "evidence": {"reviewed": False, "confidence": "low"}},
                             "entrée libre"],
}


@pytest.mark.parametrize("fm, revision", [
    (PROPOSAL_FM, None),
    ({k: v for k, v in PROPOSAL_FM.items() if k not in ("exportable", "provenance")}, None),
    ({**PROPOSAL_FM, "revision_of": {"sha256": "a" * 64}}, {"replaced": {"sha256": "a" * 64}}),
])
@pytest.mark.parametrize("relation_review_adr", [None, "ADR-TEST"])
def test_promoted_canon_keeps_the_proposal_review_key(monkeypatch, fm, revision, relation_review_adr):
    dec = _load_decision()
    monkeypatch.setattr(dec, "RELATION_REVIEW_ADR", relation_review_adr)
    promoted = dec._promoted_frontmatter(
        fm, {"gate_status": {"source": "pass"}, "confidence_score": 0.9, "shadow_score": {"tier": "A"}},
        target_rel="wiki/gamme/plaquette-test.md", sha="abc1234", now="2026-10-30T00:00:00+00:00",
        relation_verdicts={0: True}, decider_revision="d" * 64, revision=revision)
    assert promoted != fm
    assert dec._published_frontmatter(promoted) == dec._published_frontmatter(
        {k: v for k, v in fm.items() if k != "revision_of"} if revision else fm)
    assert sr.review_key(dec._published_frontmatter(promoted), "corps")[0] == \
        sr.review_key(dec._published_frontmatter(fm), "corps")[0]


def test_published_frontmatter_keeps_editorial_content():
    dec = _load_decision()
    published = dec._published_frontmatter(PROPOSAL_FM)
    assert published["exportable"] == {"rag": False}
    assert published["provenance"] == {"ingested_by": "test"}
    assert published["diagnostic_relations"] == [
        {"symptom_slug": "bruit", "evidence": {"confidence": "low"}}, "entrée libre"]
    assert "review_status" not in published and PROPOSAL_FM["review_status"] == "in_review"


def test_module_calls_no_model():
    source = (SCRIPTS_DIR / "semantic_review.py").read_text(encoding="utf-8")
    for forbidden in ("anthropic", "openai", "groq", "cohere", "mistralai", "generate_", "requests", "urllib"):
        assert forbidden not in source, forbidden


# --- Branchement dans le décideur (ADR-119 D3, précondition (d)) ----------------------------
# Conditions de la fiche seulement ; une fiche sécurité aux autres conditions toutes prouvées,
# éligible ou non selon sa seule relecture : test_promotion_decision.py.

def _write_fiche(w, fm, name):
    target = w.root / "proposals" / f"{name}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True) + "---\n" + w.body, encoding="utf-8")
    _commit(w.root, "fiche")
    return target


def _evaluate(dec, w, fm, target):
    gates = [(n, lambda t: SimpleNamespace(status="pass", violations=[])) for n in dec.CANONICAL_GATE_NAMES]
    return dec.evaluate_tier(fm, w.body, target, w.root, threshold=0.8, gates=gates,
                             compute_score=lambda *a: 0.99, raw_root=w.raw)


def _record_published(dec, w, fm, run):
    sr.record_run(w.root, fm["slug"], dec._published_frontmatter(fm), w.body, run)
    _commit(w.root, "run")


@pytest.mark.parametrize("policy", [None, "ADR-TEST"])
@pytest.mark.parametrize("state, expected", [
    ("absent", False), ("pass", True), ("fail_then_pass", False), ("incomplete", False),
    ("error", False), ("stale", False),
])
def test_safety_condition_reads_the_versioned_review(monkeypatch, w, policy, state, expected):
    dec = _load_decision()
    monkeypatch.setattr(dec, "SAFETY_AUTO_APPROVAL_ADR", policy)
    fm = {**w.fm, "slug": "colonne-de-direction", "truth_level": "L1", "no_disputed_claims": True}
    assert dec._is_safety_proposal(fm) is True
    target = _write_fiche(w, fm, fm["slug"])
    published = dec._published_frontmatter(fm)
    if state in ("pass", "stale", "fail_then_pass"):
        if state == "fail_then_pass":
            _record_published(dec, w, fm, _run(w, fm=published,
                                               candidates=[_candidate(w, "securite", ["upheld"] * 3)]))
        _record_published(dec, w, fm, _run(w, fm=published))
    elif state == "incomplete":
        _record_published(dec, w, fm, _run(w, fm=published, passes=1))
    elif state == "error":
        _record_published(dec, w, fm, _run(w, fm=published, error="interrompu"))
    if state == "stale":
        fm = {**fm, "title": "Plaquette modifiée"}
    substance = _evaluate(dec, w, fm, target)
    check = next(c for c in substance["checks"] if c["code"] == "SAFETY_HUMAN_REVIEW")
    assert check["evidence"]["conditions"]["semantic_auto_review_pass"] is expected
    assert substance["semantic_review"]["blocking"] is True
    assert substance["semantic_review"]["status"] == {
        "absent": "ABSENT", "pass": "PASS", "fail_then_pass": "FAIL", "incomplete": "INCOMPLETE",
        "error": "ERROR", "stale": "STALE"}[state]
    decision = dec.decide_promotion({"substance": substance})
    assert decision["semantic_review"]["evaluated"] is True
    assert decision["semantic_review"]["pass"] is expected
    reason = next(r for r in decision["blocking_reasons"] if r["code"] == "SAFETY_HUMAN_REVIEW")
    assert ("semantic_auto_review_pass" in reason["evidence"]["blocking_conditions"]) is (not expected)


def test_unavailable_raw_is_reported_as_unavailable_condition(w):
    dec = _load_decision()
    fm = {**w.fm, "slug": "colonne-de-direction", "truth_level": "L1"}
    target = _write_fiche(w, fm, fm["slug"])
    shutil.rmtree(w.raw)
    substance = _evaluate(dec, w, fm, target)
    assert substance["semantic_review"]["status"] == "UNAVAILABLE"
    reason = next(r for r in dec.decide_promotion({"substance": substance})["blocking_reasons"]
                  if r["code"] == "SAFETY_HUMAN_REVIEW")
    assert "semantic_auto_review_pass" in reason["evidence"]["unavailable_conditions"]


def test_non_safety_fiche_is_traced_but_never_blocked_by_the_review(w):
    dec = _load_decision()
    fm = {**w.fm, "slug": "filtre-a-huile", "title": "Filtre à huile", "truth_level": "L1"}
    assert dec._is_safety_proposal(fm) is False
    substance = _evaluate(dec, w, fm, _write_fiche(w, fm, fm["slug"]))
    assert substance["semantic_review"]["blocking"] is False
    assert substance["semantic_review"]["status"] == "ABSENT"
    decision = dec.decide_promotion({"substance": substance})
    assert decision["semantic_review"]["evaluated"] is True and decision["semantic_review"]["pass"] is False
    assert all(r["code"] != "SAFETY_HUMAN_REVIEW" for r in decision["blocking_reasons"])


def test_decision_without_trace_is_never_a_pass():
    dec = _load_decision()
    assert dec.decide_promotion({"substance": {}})["semantic_review"] == {"evaluated": False, "pass": False}


def test_manifest_binds_runs_schema_and_captures(w):
    dec = _load_decision()
    target = _write_fiche(w, w.fm, w.fm["slug"])
    before = dec.capture_input_manifest(target, w.root, w.raw, None)["input_manifest"]
    roles = {e["role"]: e for e in before}
    assert roles["semantic_review_schema"]["sha256"] is not None
    assert roles["semantic_review_capture"]["path"] == CAPTURE_PATH
    assert "semantic_review_run" not in roles
    _record_published(dec, w, w.fm, _run(w))
    after = dec.capture_input_manifest(target, w.root, w.raw, None)["input_manifest"]
    assert [e["role"] for e in after].count("semantic_review_run") == 1
    assert after != before


def test_semantic_review_is_part_of_the_evaluation_engine():
    assert "semantic_review.py" in _load_decision()._EVALUATION_ENGINE_FILES


# --- CLI -----------------------------------------------------------------------------------

def test_cli_packet_record_verdict_round_trip(w, capsys):
    dec = _load_decision()
    fiche = _write_fiche(w, w.fm, w.fm["slug"])
    common = ["--wiki-root", str(w.root), "--raw-root", str(w.raw)]
    assert sr.main(common + ["verdict", str(fiche)]) == 1
    capsys.readouterr()
    assert sr.main(common + ["packet", str(fiche)]) == 0
    packet = json.loads(capsys.readouterr().out)
    assert packet["captures"][0]["text"] == CAPTURE
    fm, body = dec._parse_markdown(fiche)
    run_file = w.root.parent / "run.json"
    run_file.write_text(json.dumps(_run(w, fm=dec._published_frontmatter(fm), body=body)), encoding="utf-8")
    assert sr.main(common + ["record", str(fiche), str(run_file)]) == 0
    recorded = capsys.readouterr().out.strip()
    assert recorded.startswith("_audit/semantic-review/plaquette-test/")
    _commit(w.root, "run")
    assert sr.main(common + ["verdict", str(fiche)]) == 0


# --- Exécuteur (relecteur simulé) ----------------------------------------------------------

FAKE_REVIEWER = """
import json, os, pathlib, sys
prompt = sys.stdin.buffer.read().decode("utf-8")
model = sys.argv[1] if len(sys.argv) > 1 else None
kind = "detection" if prompt.startswith("Relecture de sens — passe de détection") else "refutation"
with open(os.environ["FAKE_REVIEWER_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"kind": kind, "model": model, "cwd": os.getcwd(),
                          "files": os.listdir("."), "prompt": prompt}) + "\\n")
scenario = json.loads(pathlib.Path(os.environ["FAKE_REVIEWER_SCENARIO"]).read_text(encoding="utf-8"))
if model in scenario["fail"].get(kind, []):
    sys.exit(3)
sys.stdout.buffer.write(scenario[kind].encode("utf-8"))
"""

SECURITY_GAP = {"class": "securite", "segment_id": "body:2", "claims": [0],
                "statement": "La fiche omet le remplacement par essieu complet."}


def _detection(w, candidates=()):
    entries = [{"id": s["id"], "no_claims": True} for s in sr.segments(w.fm, w.body)]
    for entry in entries:
        if entry["id"] == "body:2":
            del entry["no_claims"]
            entry["claims"] = [{"text": "La plaquette frotte sur le disque.", "kind": "affirmation"}]
    return json.dumps({"segments": entries, "candidates": list(candidates)}, ensure_ascii=False)


def _verdict(w, verdict, quote=QUOTE):
    return json.dumps({"verdict": verdict, "passage": {"path": CAPTURE_PATH, "cid": w.cid, "quote": quote}})


@pytest.fixture
def ex(w, tmp_path, monkeypatch):
    """Exécuteur branché sur un relecteur simulé : il journalise chaque appel (modèle, répertoire,
    invite) et répond selon un scénario."""
    reviewer, log, scenario = tmp_path / "fake_reviewer.py", tmp_path / "calls.jsonl", tmp_path / "scenario.json"
    reviewer.write_text(FAKE_REVIEWER, encoding="utf-8")
    monkeypatch.setenv("FAKE_REVIEWER_LOG", str(log))
    monkeypatch.setenv("FAKE_REVIEWER_SCENARIO", str(scenario))
    base = f"{shlex.quote(sys.executable)} {shlex.quote(str(reviewer))}"
    default_fiche = _write_fiche(w, w.fm, w.fm["slug"])

    def run(detection, refutation="{}", *, fail=None, extra=(), command=None, fiche=None):
        scenario.write_text(json.dumps({"detection": detection, "refutation": refutation, "fail": fail or {}}),
                            encoding="utf-8")
        code = sre.main([str(fiche or default_fiche), "--command", command or f"{base} {{model}}",
                         "--model", "model-a", "--model", "model-b",
                         "--wiki-root", str(w.root), "--raw-root", str(w.raw), *extra])
        calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
        log.unlink(missing_ok=True)
        if code == 0:
            _commit(w.root, "run")
        return code, calls

    return SimpleNamespace(run=run, base=base)


def test_executor_isolates_each_pass_and_records_a_clean_review(w, ex, capsys):
    code, calls = ex.run(_detection(w))
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "PASS" and out["recorded"].startswith("_audit/semantic-review/plaquette-test/")
    assert _status(w)["status"] == "PASS"
    assert [c["kind"] for c in calls] == ["detection", "detection"]
    assert sorted(c["model"] for c in calls) == ["model-a", "model-b"]
    # Processus neufs, répertoires vides et distincts ; l'invite ne porte que segments et captures.
    assert all(c["files"] == [] for c in calls) and len({c["cwd"] for c in calls}) == 2
    payload = json.loads(calls[0]["prompt"][len(sre.DETECTION_PROMPT):])
    assert payload == {"segments": [{"id": s["id"], "text": s["text"]} for s in sr.segments(w.fm, w.body)],
                       "captures": [{"path": CAPTURE_PATH, "cid": w.cid, "text": CAPTURE}]}


@pytest.mark.parametrize("jobs", ["1", "4"])
def test_executor_records_an_upheld_gap_as_a_fail(w, ex, capsys, jobs):
    code, calls = ex.run(_detection(w, [SECURITY_GAP]), _verdict(w, "upheld"), extra=["--jobs", jobs])
    assert code == 0 and json.loads(capsys.readouterr().out)["verdict"] == "FAIL"
    status = _status(w)
    assert status["status"] == "FAIL" and status["pass"] is False
    run = status["runs"][0]
    assert run["confirmed_by_class"]["securite"] == 2 and run["unsettled_confirmed"] == 0
    refutations = [c for c in calls if c["kind"] == "refutation"]
    assert len(refutations) == 6 and sorted(c["model"] for c in refutations) == ["model-a"] * 4 + ["model-b"] * 2
    payload = json.loads(refutations[0]["prompt"][len(sre.REFUTATION_PROMPT):])
    assert set(payload) == {"candidate", "captures"}
    assert payload["candidate"]["segment"] == {"id": "body:2", "text": "La plaquette frotte sur le disque."}


def test_executor_dismisses_a_candidate_every_refuter_refutes_from_a_capture(w, ex, capsys):
    assert ex.run(_detection(w, [SECURITY_GAP]), _verdict(w, "refuted"))[0] == 0
    status = _status(w)
    assert status["status"] == "PASS" and status["runs"][0]["dismissed"] == 2


def test_executor_may_harden_the_protocol(w, ex, capsys):
    code, calls = ex.run(_detection(w, [SECURITY_GAP]), _verdict(w, "refuted"),
                         extra=["--passes", "3", "--refuters", "4"])
    assert code == 0
    status = _status(w)
    assert status["status"] == "PASS" and status["runs"][0]["dismissed"] == 3
    assert [c["kind"] for c in calls].count("refutation") == 12


def test_failed_pass_is_an_error_never_a_verdict(w, ex, capsys):
    assert ex.run(_detection(w), fail={"detection": ["model-b"]})[0] == 0
    status = _status(w)
    assert status["status"] == "ERROR" and status["pass"] is False
    assert "passe p1" in status["runs"][0]["error"]


@pytest.mark.parametrize("refutation, fail", [
    ("refuted", {"refutation": ["model-b"]}),
    ("pas du JSON", None),
    ("malformed_passage", None),
])
def test_failed_refuter_neither_confirms_nor_dismisses(w, ex, capsys, refutation, fail):
    answer = {"refuted": _verdict(w, "refuted"), "pas du JSON": "pas du JSON",
              "malformed_passage": json.dumps({"verdict": "upheld",
                                               "passage": {"path": CAPTURE_PATH, "cid": "sha256:zz", "quote": QUOTE}})}
    assert ex.run(_detection(w, [SECURITY_GAP]), answer[refutation], fail=fail)[0] == 0
    status = _status(w)
    run = status["runs"][0]
    assert status["status"] == "ERROR" and sum(run["confirmed_by_class"].values()) == 0
    assert run["pending"] == 2 and run["dismissed"] == 0


@pytest.mark.parametrize("answer", [
    "pas du JSON",
    json.dumps({"segments": [{"id": "body:99", "no_claims": True}], "candidates": []}),
    json.dumps({"segments": [{"id": "body:1", "no_claims": True, "claims": [{"text": "x", "kind": "affirmation"}]}],
                "candidates": []}),
    json.dumps({"segments": [{"id": "body:2", "claims": [{"text": "x", "kind": "avis"}]}], "candidates": []}),
    json.dumps({"segments": [{"id": "body:2", "no_claims": True}],
                "candidates": [{"class": "grave", "segment_id": "body:2", "statement": "x"}]}),
    json.dumps({"segments": [{"id": "body:2", "no_claims": True}],
                "candidates": [{"class": "sens", "segment_id": "body:2", "claims": [0], "statement": "x"}]}),
    json.dumps({"segments": [{"id": "body:2", "no_claims": True}],
                "candidates": [{"class": "sens", "segment_id": "body:3", "statement": "x"}]}),
])
def test_detection_out_of_contract_drops_the_pass(w, ex, capsys, answer):
    code, calls = ex.run(answer)
    assert code == 0 and [c["kind"] for c in calls] == ["detection", "detection"]
    status = _status(w)
    run = status["runs"][0]
    assert status["status"] == "ERROR" and "réponse" in run["error"]
    assert "passes: 0 < 2" in run["incomplete"]


def test_fenced_json_answer_is_read(w, ex, capsys):
    assert ex.run("```json\n" + _detection(w) + "\n```")[0] == 0
    assert _status(w)["status"] == "PASS"


@pytest.mark.parametrize("extra, message", [
    (["--passes", "1"], "ADR"), (["--refuters", "2"], "ADR"), (["--jobs", "0"], "--jobs"),
])
def test_executor_never_loosens_the_protocol(w, ex, capsys, extra, message):
    code, calls = ex.run(_detection(w), extra=extra)
    assert code == 2 and calls == [] and message in capsys.readouterr().err
    assert not (w.root / sr.REVIEW_DIR).exists()


def test_executor_requires_the_model_in_its_command(w, ex, capsys):
    code, calls = ex.run(_detection(w), command=ex.base)
    assert code == 2 and calls == [] and "{model}" in capsys.readouterr().err


def test_executor_refuses_a_fiche_without_capture(w, ex, capsys):
    fiche = _write_fiche(w, {**w.fm, "source_refs": [{"kind": "external_url", "url": "https://example.invalid/a"}]},
                         "sans-capture")
    code, calls = ex.run(_detection(w), fiche=fiche)
    assert code == 2 and calls == [] and "no_capture" in capsys.readouterr().err
