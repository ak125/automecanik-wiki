"""Tests de _scripts/technical_qualification.py — corroboration par un second domaine (ADR-131, candidat)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import technical_qualification as tq  # noqa: E402

C1, C2, C3, C4 = ("sha256:" + c * 64 for c in "1234")
CATALOG = {
    "source_type_editorial_role": {"oem_manual": "proof", "wiki_externe": "corroboration"},
    "sources": [
        {"publisher": "Renault", "type": "oem_manual", "publisher_class": "constructeur",
         "raw_ref": {"expected_sha256": C1}},
        {"publisher": "Brembo", "type": "oem_manual", "publisher_class": "equipementier",
         "raw_ref": {"expected_sha256": C2}},
        {"publisher": "Brembo", "type": "oem_manual", "publisher_class": "equipementier",
         "raw_ref": {"expected_sha256": C3}},
        {"publisher": "Wikipedia", "type": "wiki_externe", "raw_ref": {"expected_sha256": C4}},
    ],
}
CAPTURES = [{"path": "a.md", "cid": C1, "source_url": "https://www.user-manual.renault.com/x"},
            {"path": "b.md", "cid": C2, "source_url": "https://www.bremboparts.com/x"},
            {"path": "c.md", "cid": C3, "source_url": "https://brembo.com/y"},
            {"path": "d.md", "cid": C4, "source_url": "https://fr.wikipedia.org/z"}]


def _domains(definition):
    return {d["cid"]: d["domain"] for d in tq.capture_domains(CAPTURES, CATALOG, definition)}


def test_publisher_class_is_fail_closed_and_merges_one_publisher():
    d = _domains("publisher_class")
    assert d == {C1: "constructeur", C2: "equipementier", C3: "equipementier", C4: None}


def test_source_type_and_host_definitions_differ():
    assert set(_domains("source_type").values()) == {"oem_manual", "wiki_externe"}
    # Un même éditeur sur deux hôtes compte deux fois sous la définition host.
    assert _domains("host")[C2] != _domains("host")[C3]


def test_capture_absent_from_catalog_has_no_domain_and_unknown_role():
    out = tq.capture_domains([{"path": "z.md", "cid": "sha256:" + "9" * 64}], CATALOG, "source_type")
    assert out == [{"cid": "sha256:" + "9" * 64, "publisher": None, "domain": None, "editorial_role": "unknown"}]


def test_unknown_definition_is_refused():
    with pytest.raises(ValueError):
        tq.capture_domains(CAPTURES, CATALOG, "editeur")


def _claim(verdict, cids, **corr):
    return {"id": "c0", "text": "t", "verdict": verdict, "sources": [{"path": "p", "cid": c, "quote": "q"} for c in cids],
            "portee": "p", "limite": "l", "corroboration": corr}


DOM = tq.capture_domains(CAPTURES, CATALOG, "publisher_class")


def test_enforce_keeps_conserver_with_proof_and_two_concordant_domains():
    out = tq.enforce(_claim("conserver", [C1, C2], concordance="concordant"), "complete", DOM)
    assert out["verdict"] == "conserver" and out["corroboration"]["declassed_by"] is None
    assert out["corroboration"]["domains"] == ["constructeur", "equipementier"]


@pytest.mark.parametrize("cids", [[C2, C3], [C2, C4], [C2]])
def test_enforce_declasses_conserver_complete_without_second_domain(cids):
    out = tq.enforce(_claim("conserver", cids, concordance="concordant"), "complete", DOM)
    assert out["verdict"] == "preciser"
    assert out["corroboration"]["declassed_from"] == "conserver"
    assert out["corroboration"]["declassed_by"] == "control"
    assert out["corroboration"]["concordance"] == "single_source"


def test_enforce_treats_missing_concordance_as_unconfirmed():
    out = tq.enforce(_claim("conserver", [C1, C2]), "complete", DOM)
    assert out["corroboration"]["concordance"] == "undetermined" and out["verdict"] == "preciser"


def test_enforce_blocking_discordance_gives_retirer_other_gives_preciser():
    out = tq.enforce(_claim("conserver", [C1, C2], concordance="discordant", discordance_on="safety"), "complete", DOM)
    assert out["verdict"] == "retirer"
    out = tq.enforce(_claim("conserver", [C1, C2], concordance="discordant", discordance_on="other"), "complete", DOM)
    assert out["verdict"] == "preciser"


def test_enforce_allegee_is_unchanged():
    out = tq.enforce(_claim("conserver", [C2], concordance="concordant"), "allegee", DOM)
    assert out["verdict"] == "conserver" and out["corroboration"]["declassed_by"] is None


def test_enforce_without_source_records_no_source():
    out = tq.enforce(_claim("retirer", []), "complete", DOM)
    assert out["corroboration"]["concordance"] == "no_source" and out["verdict"] == "retirer"


def _run(claims, depth="complete"):
    return {"schema_version": "technical-qualification/v2", "role": "qualification",
            "key_inputs": {"capture_domains": DOM},
            "segments": [{"id": "body:1", "depth": depth, "claims": claims}]}


def test_retake_questions_and_loop_score():
    claims = [tq.enforce(_claim("conserver", [C1, C2], concordance="concordant"), "complete", DOM),
              tq.enforce(_claim("conserver", [C2], concordance="concordant"), "complete", DOM),
              tq.enforce(_claim("retirer", []), "complete", DOM)]
    for i, c in enumerate(claims):
        c["id"] = f"c{i}"
    claims[1]["retake_question"] = "Quel constructeur publie cette consigne ?"
    run = _run(claims)
    qs = tq.retake_questions(run)
    assert [(q["claim_id"], q["reason"], q["question_source"]) for q in qs] == [
        ("c1", "single_domain", "model"), ("c2", "no_capture", "template")]
    assert tq.loop_score(run) == {"complete_claims": 3, "confirmed": 1, "score": 1 / 3}
    assert tq.corroboration_violations(run) == []


def test_loop_score_ignores_allegee():
    run = _run([tq.enforce(_claim("conserver", [C2], concordance="concordant"), "allegee", DOM)], depth="allegee")
    assert tq.loop_score(run) == {"complete_claims": 0, "confirmed": 0, "score": None}
    assert tq.retake_questions(run) == []


@pytest.mark.parametrize("scores,target,maximum,expected", [
    ([0.2], 0.8, 2, None),
    ([0.2, 0.9], 0.8, 2, "target_reached"),
    ([0.2, 0.2], 0.8, 2, "no_progress"),
    ([0.2, 0.4, 0.6], 0.8, 2, "max_retakes"),
    ([0.2, 0.4], 1.0, 3, None),
])
def test_loop_stop(scores, target, maximum, expected):
    assert tq.loop_stop(scores, target, maximum) == expected
