"""Tests du schéma technical-qualification (v1, v2) et du skill qualification-technique (ADR-131, candidat).

Candidat non câblé : aucun code de promotion ne lit ce schéma. Les tests gardent le contrat de
l'artefact (rôles exclusifs, segment à une seule forme, verdicts fermés, profondeur bornée), la règle
de corroboration de la v2 (un `conserver` complete exige une preuve et deux domaines concordants),
la présence des deux invites du skill, et la conformité des artefacts déposés sous
_audit/technical-qualification/, contrôle de corroboration compris pour la v2.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))
import technical_qualification as tq  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "_meta" / "schema" / "technical-qualification-run.schema.json"
SKILL = ROOT / "_meta" / "skills" / "qualification-technique" / "SKILL.md"
AUDIT = ROOT / "_audit" / "technical-qualification"
H = "a" * 64
CID = "sha256:" + "b" * 64
SHA = "c" * 40


def _v() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))


def _claim(**extra) -> dict:
    claim = {"id": "c0", "text": "Le filtre se change à chaque vidange.", "verdict": "retirer", "sources": [],
             "portee": "aucune capture", "limite": "intervalle du constructeur", "proposed_wording": None}
    claim.update(extra)
    return claim


def _qualification(**extra) -> dict:
    run = {
        "schema_version": "technical-qualification/v1",
        "role": "qualification",
        "key": H,
        "key_inputs": {"text_sha256": H, "captures": [{"path": "sources/x.md", "cid": CID}], "skill_sha256": H},
        "subject": {"repo": "ak125/automecanik-wiki", "path": "wiki/gamme/x.md", "commit": SHA, "slug": "x"},
        "freshness": {"read_from": "origin", "ref": "origin/main", "commit": SHA, "checked_at": "2026-11-15T09:19:00Z"},
        "reviewer": {"model": "m", "provider": "anthropic"},
        "producer": {"declared": None, "provider": "unknown", "basis": "aucun champ"},
        "segments": [
            {"id": "fm:slug", "depth_floor": "allegee", "depth": "allegee", "no_claims": True},
            {"id": "body:1", "depth_floor": "complete", "depth": "complete", "depth_reasons": ["procedure"],
             "claims": [_claim()]},
        ],
    }
    run.update(extra)
    return run


def _contestation(**extra) -> dict:
    run = _qualification(role="contestation", reviewer={"model": "g", "provider": "openai"},
                         contests={"artifact_sha256": H, "reviewer_model": "m", "reviewer_provider": "anthropic"},
                         missed=[], segments=[
                             {"id": "body:1", "depth_floor": "complete", "depth": "complete",
                              "positions": [{"claim_id": "c0", "position": "agree", "statement": "tient",
                                             "passage": None}]}])
    run.update(extra)
    return run


def _errors(run) -> list:
    return list(_v().iter_errors(run))


def test_schema_itself_is_valid():
    Draft202012Validator.check_schema(json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_minimal_qualification_and_contestation_validate():
    assert not _errors(_qualification())
    assert not _errors(_contestation())


def test_contestation_requires_the_contested_artifact():
    run = _contestation()
    del run["contests"]
    assert _errors(run)


def test_qualification_cannot_carry_contestation_fields():
    assert _errors(_qualification(contests={"artifact_sha256": H, "reviewer_model": "m",
                                            "reviewer_provider": "anthropic"}))
    assert _errors(_qualification(missed=[]))


@pytest.mark.parametrize("mutation", ["both_forms", "no_form", "bad_verdict", "bad_depth", "bad_provider",
                                      "missing_limit", "verdict_field", "approval_field"])
def test_out_of_contract_artifacts_are_refused(mutation):
    run = _qualification()
    segment = run["segments"][1]
    if mutation == "both_forms":
        segment["no_claims"] = True
    elif mutation == "no_form":
        del segment["claims"]
    elif mutation == "bad_verdict":
        segment["claims"][0]["verdict"] = "valider"
    elif mutation == "bad_depth":
        segment["depth"] = "aucune"
    elif mutation == "bad_provider":
        run["reviewer"]["provider"] = "unknown"
    elif mutation == "missing_limit":
        del segment["claims"][0]["limite"]
    elif mutation == "verdict_field":
        run["verdict"] = "PASS"
    elif mutation == "approval_field":
        run["approved"] = True
    assert _errors(run), mutation


def test_unknown_producer_is_recorded_not_assumed():
    run = _qualification()
    assert run["producer"]["provider"] == "unknown" and not _errors(run)
    run = copy.deepcopy(run)
    del run["producer"]["basis"]
    assert _errors(run)


def test_skill_carries_both_invites_and_is_not_wired():
    text = SKILL.read_text(encoding="utf-8")
    for name in ("qualification", "contestation"):
        assert re.search(rf"<!-- invite:{name} -->\n.+?<!-- /invite -->", text, re.S), name
    assert re.search(r"^wired: false$", text, re.M)


CID2 = "sha256:" + "d" * 64


def _corr(**extra) -> dict:
    corr = {"domains": ["constructeur", "equipementier"], "captures": [CID, CID2], "proof": True,
            "concordance": "concordant", "discordance_on": None, "declassed_from": None, "declassed_by": None}
    corr.update(extra)
    return corr


def _v2(verdict="conserver", depth="complete", **corr) -> dict:
    run = _qualification(schema_version="technical-qualification/v2", retake_questions=[])
    run["key_inputs"].update(domain_definition="publisher_class", capture_domains=[
        {"cid": CID, "publisher": "R", "domain": "constructeur", "editorial_role": "proof"},
        {"cid": CID2, "publisher": "M", "domain": "equipementier", "editorial_role": "proof"}])
    seg = run["segments"][1]
    seg["depth"] = seg["depth_floor"] = depth
    seg["claims"] = [_claim(verdict=verdict, corroboration=_corr(**corr), retake_question=None, sources=[
        {"path": "sources/x.md", "cid": CID, "quote": "q"}, {"path": "sources/y.md", "cid": CID2, "quote": "q"}])]
    return run


def test_v2_conserver_complete_with_two_concordant_domains_validates():
    assert not _errors(_v2())
    assert tq.corroboration_violations(_v2()) == []


@pytest.mark.parametrize("corr", [{"domains": ["equipementier"]}, {"proof": False},
                                  {"concordance": "single_source"}, {"concordance": "undetermined"}])
def test_v2_schema_refuses_conserver_complete_without_second_domain(corr):
    assert _errors(_v2(**corr)), corr


def test_v2_allegee_keeps_the_rule_unchanged():
    assert not _errors(_v2(depth="allegee", domains=["equipementier"], concordance="single_source"))


def test_v2_requires_corroboration_and_domains():
    run = _v2()
    del run["segments"][1]["claims"][0]["corroboration"]
    assert _errors(run)
    run = _v2()
    del run["key_inputs"]["capture_domains"]
    assert _errors(run)
    run = _v2()
    del run["retake_questions"]
    assert _errors(run)


def test_v1_cannot_carry_v2_fields():
    assert _errors(_qualification(retake_questions=[]))
    run = _qualification()
    run["segments"][1]["claims"][0]["corroboration"] = _corr()
    assert _errors(run)


def test_control_recomputes_domains_instead_of_trusting_the_artifact():
    # L'artefact déclare deux domaines, mais les deux passages viennent du même domaine.
    run = _v2()
    run["key_inputs"]["capture_domains"][1]["domain"] = "constructeur"
    assert not _errors(run)  # le schéma ne voit que ce qui est consigné
    violations = tq.corroboration_violations(run)
    assert any("domains" in v for v in violations)
    assert any("sans preuve ni second domaine" in v for v in violations)


def test_control_requires_retirer_on_blocking_discordance():
    run = _v2(verdict="preciser", concordance="discordant", discordance_on="value")
    assert any("sans retirer" in v for v in tq.corroboration_violations(run))
    run = _v2(verdict="preciser", concordance="discordant", discordance_on="other")
    assert tq.corroboration_violations(run) == []


def test_skill_is_v030_and_states_the_corroboration_rule():
    text = SKILL.read_text(encoding="utf-8")
    assert re.search(r"^version: 0\.3\.0$", text, re.M)
    qualification = re.search(r"<!-- invite:qualification -->\n(.+?)<!-- /invite -->", text, re.S).group(1)
    contestation = re.search(r"<!-- invite:contestation -->\n(.+?)<!-- /invite -->", text, re.S).group(1)
    assert "concordance" in qualification and "retake_question" in qualification
    assert "concordance" in contestation and "independence" in contestation


def _deposited():
    return sorted(AUDIT.rglob("*.json")) if AUDIT.is_dir() else []


@pytest.mark.parametrize("path", _deposited(), ids=lambda p: p.relative_to(AUDIT).as_posix() if isinstance(p, Path) else str(p))
def test_deposited_artifacts_conform(path):
    import hashlib
    data = path.read_bytes()
    assert path.name == f"{hashlib.sha256(data).hexdigest()}.json"
    run = json.loads(data)
    assert not _errors(run)
    assert path.parent.name == run["key"]
    assert tq.corroboration_violations(run) == []
