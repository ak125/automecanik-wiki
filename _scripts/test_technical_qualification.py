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


# --- Condition technical_qualification_pass (ADR-131 D3 à D5, D7, D9) ----------------------

import copy  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import yaml  # noqa: E402

import semantic_review as sr  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
CAP_A, CAP_B = "sources/auto-captures/filtre-test/a.md", "sources/auto-captures/filtre-test/b.md"
TEXT_A = "# Notice constructeur\n\nLe filtre retient les poussières.\nSerrer le couvercle à 25 N·m.\n"
TEXT_B = "# Notice équipementier\n\nSerrer le couvercle à 25 N·m.\n"
BODY_TQ = ("## Rôle technique\n\nLe filtre retient les poussières.\n\n"
           "## Montage\n\nSerrer le couvercle à 25 N·m.\n")
COMMIT = "a" * 40
FRESH = {"read_from": "origin", "ref": "origin/main", "commit": COMMIT, "raw_commit": "b" * 40,
         "checked_at": "2026-11-17T14:00:00Z"}
Q_REVIEWER = {"model": "claude-opus-5-5", "provider": "anthropic"}
C_REVIEWER = {"model": "gpt-5.5", "provider": "openai"}


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid",
                           "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
                          cwd=root, check=True, capture_output=True, text=True).stdout


def _commit(root: Path) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "--allow-empty", "-m", "test")


def _catalog(cid_a, cid_b, *, publisher_class=True):
    entries = [{"publisher": "Renault", "type": "oem_manual", "publisher_class": "constructeur",
                "raw_ref": {"expected_sha256": cid_a}},
               {"publisher": "MANN", "type": "oem_manual", "publisher_class": "equipementier",
                "raw_ref": {"expected_sha256": cid_b}}]
    if not publisher_class:
        for entry in entries:
            del entry["publisher_class"]
    return {"source_type_editorial_role": {"oem_manual": "proof"}, "sources": entries}


@pytest.fixture
def w(tmp_path):
    """WIKI temporaire versionné (schéma, skill, catalogue) et RAW temporaire à deux captures de
    deux classes d'éditeur."""
    root, raw = tmp_path / "wiki", tmp_path / "raw"
    cids = []
    for rel, text in ((CAP_A, TEXT_A), (CAP_B, TEXT_B)):
        (raw / rel).parent.mkdir(parents=True, exist_ok=True)
        (raw / rel).write_text(text, encoding="utf-8")
        cids.append("sha256:" + hashlib.sha256((raw / rel).read_bytes()).hexdigest())
    for rel in (tq.RUN_SCHEMA_RELPATH, tq.SKILL_RELPATH):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(SCRIPTS_DIR.parent / rel, root / rel)
    (root / tq.CATALOG_RELPATH).write_text(yaml.safe_dump(_catalog(*cids)), encoding="utf-8")
    _git(root, "init", "-q")
    _commit(root)
    fm = {"entity_type": "gamme", "slug": "filtre-test", "title": "Filtre",
          "source_refs": [{"kind": "raw", "path": CAP_A, "cid": cids[0]},
                          {"kind": "raw", "path": CAP_B, "cid": cids[1]}]}
    return SimpleNamespace(root=root, raw=raw, fm=fm, body=BODY_TQ, cid_a=cids[0], cid_b=cids[1])


def _passage(w, which, quote):
    return {"path": CAP_A if which == "a" else CAP_B, "cid": w.cid_a if which == "a" else w.cid_b,
            "quote": quote}


def _key(w, fm=None, body=None):
    return tq.expected_key(fm or w.fm, body or w.body, w.root, tq.load_catalog(w.root))


def _qual(w, *, mount="conserver", role_verdict="conserver", mount_sources="ab", producer="anthropic",
          freshness=None, error=None, drop=None, mount_depth=None, mount_quote="Serrer le couvercle à 25 N·m."):
    """Qualification v2 : body:2 (descriptif) et body:4 (montage, valeur) portent une affirmation."""
    key, key_inputs = _key(w)
    segs = sr.segments(w.fm, w.body)
    floors = tq.depth_floors(w.fm, segs)
    domains = key_inputs["capture_domains"]
    out = []
    for seg in segs:
        sid = seg["id"]
        floor, reasons = floors[sid]
        item = {"id": sid, "sha256": seg["sha256"], "depth_floor": floor, "depth": floor,
                "depth_reasons": reasons}
        if sid == "body:2":
            claim = {"id": "c1", "text": "Le filtre retient les poussières.", "verdict": role_verdict,
                     "sources": [_passage(w, "a", "Le filtre retient les poussières.")],
                     "portee": "ce filtre", "limite": "aucune autre pièce",
                     "corroboration": {"concordance": "single_source"}}
        elif sid == "body:4":
            if mount_depth:
                item["depth_floor"] = item["depth"] = mount_depth
                item["depth_reasons"] = []
            claim = {"id": "c2", "text": "Serrer le couvercle à 25 N·m.", "verdict": mount,
                     "sources": [_passage(w, x, mount_quote) for x in mount_sources],
                     "portee": "ce filtre", "limite": "aucune autre pièce",
                     "corroboration": {"concordance": "concordant"}}
        else:
            item["no_claims"] = True
            out.append(item)
            continue
        item["claims"] = [tq.enforce(claim, item["depth"], domains)]
        out.append(item)
    if drop:
        out = [s for s in out if s["id"] != drop]
    run = {"schema_version": "technical-qualification/v2", "role": "qualification", "key": key,
           "key_inputs": key_inputs, "subject": {"repo": "automecanik-wiki", "path": "wiki/gammes/filtre-test.md",
                                                 "commit": COMMIT, "slug": "filtre-test"},
           "freshness": freshness or dict(FRESH), "reviewer": dict(Q_REVIEWER),
           "producer": {"declared": "wiki-proposal-writer", "provider": producer,
                        "basis": "_meta/source-policy.md:74"},
           "segments": out}
    run["retake_questions"] = tq.retake_questions(run)
    if error:
        run["error"] = error
    return run


def _contest(w, qualification_path, *, positions=None, missed=(), reviewer=None, contests=None,
             freshness=None, error=None, checks=None):
    """Contestation : `agree` sur chaque affirmation, sauf `positions` {claim_id: (position, verdict)}."""
    qual = json.loads(qualification_path.read_text(encoding="utf-8"))
    segs = []
    for seg in qual["segments"]:
        if not seg.get("claims"):
            continue
        items = []
        for claim in seg["claims"]:
            kind, verdict = (positions or {}).get(claim["id"], ("agree", None))
            pos = {"claim_id": claim["id"], "position": kind, "statement": "lu",
                   "passage": claim["sources"][0] if claim["sources"] else None,
                   "checks": dict(checks or {"concordance": "holds", "independence": "holds"})}
            if verdict:
                pos["verdict"] = verdict
            items.append(pos)
        segs.append({"id": seg["id"], "depth_floor": seg["depth_floor"], "depth": seg["depth"],
                     "positions": items})
    run = {"schema_version": "technical-qualification/v2", "role": "contestation", "key": qual["key"],
           "key_inputs": qual["key_inputs"], "subject": qual["subject"],
           "freshness": freshness or dict(FRESH), "reviewer": dict(reviewer or C_REVIEWER),
           "producer": qual["producer"], "segments": segs, "missed": list(missed),
           "contests": contests or {"artifact_sha256": qualification_path.stem,
                                    "reviewer_model": qual["reviewer"]["model"],
                                    "reviewer_provider": qual["reviewer"]["provider"]}}
    if error:
        run["error"] = error
    return run


def _record(w, run, *, commit=True, key=None):
    data = (json.dumps(run, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    target = w.root / tq.QUALIFICATION_DIR / w.fm["slug"] / (key or run["key"]) / \
        f"{hashlib.sha256(data).hexdigest()}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    if commit:
        _commit(w.root)
    return target


def _mount(run):
    return next(seg for seg in run["segments"] if seg["id"] == "body:4")["claims"][0]


def _pair(w, qual_kwargs=None, contest_kwargs=None):
    q = _record(w, _qual(w, **(qual_kwargs or {})))
    _record(w, _contest(w, q, **(contest_kwargs or {})))
    return q


def _status(w, fm=None, body=None):
    return tq.qualification_status(w.root, w.fm["slug"], fm or w.fm, body or w.body, w.raw)


def _blocking(status):
    return sorted(b["where"] for p in status["pairs"] for b in p["blocking"])


def test_absent_qualification_is_never_a_pass(w):
    status = _status(w)
    assert status["status"] == "ABSENT" and status["pass"] is False


def test_qualification_contested_by_another_family_passes(w):
    _pair(w)
    status = _status(w)
    assert status["status"] == "PASS" and status["pass"] is True, status
    assert status["pairs"][0]["claims"] == 2
    assert status["floors"]["body:4"]["reasons"] == ["numeric_value", "procedure"]


def test_qualification_without_contestation_never_passes(w):
    _record(w, _qual(w))
    status = _status(w)
    assert status["status"] == "NO_CONTESTATION" and status["pass"] is False


@pytest.mark.parametrize("verdict", ["preciser", "reformuler", "retirer"])
def test_complete_claim_not_conserved_fails(w, verdict):
    _pair(w, {"mount": verdict})
    status = _status(w)
    assert status["status"] == "FAIL" and _blocking(status) == ["body:4 c2"]


def test_allegee_claim_blocks_only_on_retirer(w):
    _pair(w, {"role_verdict": "preciser"})
    assert _status(w)["status"] == "PASS"
    _pair(w, {"role_verdict": "retirer"})
    status = _status(w)
    assert status["status"] == "FAIL" and _blocking(status) == ["body:2 c1"]


def test_fail_is_never_replaced_by_a_pass_on_the_same_key(w):
    _pair(w, {"mount": "retirer"})
    _pair(w)
    status = _status(w)
    assert sorted(p["status"] for p in status["pairs"]) == ["FAIL", "PASS"]
    assert status["status"] == "FAIL" and status["pass"] is False


def test_unknown_producer_family_is_never_a_pass(w):
    _pair(w, {"producer": "unknown"})
    assert _status(w)["status"] == "PRODUCER_UNKNOWN"


@pytest.mark.parametrize("contest_kwargs", [
    {"reviewer": {"model": "claude-sonnet-5-5", "provider": "anthropic"}},
    {"contests": {"artifact_sha256": None, "reviewer_model": "autre", "reviewer_provider": "anthropic"}},
])
def test_contestation_of_the_same_family_or_another_reviewer_is_not_independent(w, contest_kwargs):
    q = _record(w, _qual(w))
    if "contests" in contest_kwargs:
        contest_kwargs = {"contests": {**contest_kwargs["contests"], "artifact_sha256": q.stem}}
    _record(w, _contest(w, q, **contest_kwargs))
    assert _status(w)["status"] == "NOT_INDEPENDENT"


@pytest.mark.parametrize("change", [
    {"raw_commit": None},
    {"read_from": "freshness_guard", "guard_exit": 1},
    {"read_from": "freshness_guard"},
])
def test_missing_freshness_proof_is_never_a_pass(w, change):
    freshness = {k: v for k, v in {**FRESH, **change}.items() if v is not None}
    _pair(w, contest_kwargs={"freshness": freshness})
    assert _status(w)["status"] == "NO_FRESHNESS"


def test_freshness_guard_passed_is_accepted(w):
    _pair(w, {"freshness": {**FRESH, "read_from": "freshness_guard", "guard_exit": 0}})
    assert _status(w)["status"] == "PASS"


@pytest.mark.parametrize("qual_kwargs, contest_kwargs", [
    ({"error": "délai dépassé"}, {}),
    ({}, {"error": "réponse hors contrat"}),
])
def test_errored_artifact_is_neither_pass_nor_fail(w, qual_kwargs, contest_kwargs):
    _pair(w, qual_kwargs, contest_kwargs)
    assert _status(w)["status"] == "ERROR"


def test_errored_contestation_does_not_hide_a_qualification_fail(w):
    _pair(w, {"mount": "retirer"}, {"error": "délai dépassé"})
    assert _status(w)["status"] == "FAIL"


def test_missing_segment_or_position_is_incomplete(w):
    _pair(w, {"drop": "body:1"})
    assert _status(w)["status"] == "INCOMPLETE"


def test_claim_without_position_is_not_acquired(tmp_path, w):
    q = _record(w, _qual(w))
    run = _contest(w, q)
    run["segments"] = [s for s in run["segments"] if s["id"] != "body:2"]
    _record(w, run)
    status = _status(w)
    assert status["status"] == "INCOMPLETE"
    assert any("aucune position" in n for n in status["pairs"][0]["notes"])


def test_floor_is_recomputed_never_lowered_by_the_artifact(w):
    # La qualification déclare le montage `allegee` : le plancher recalculé le remet `complete`.
    _pair(w, {"mount": "preciser", "mount_depth": "allegee"})
    status = _status(w)
    assert status["status"] == "FAIL" and _blocking(status) == ["body:4 c2"]
    assert status["pairs"][0]["blocking"][0]["depth"] == "complete"


def test_unanchored_passage_counts_as_no_source_in_complete(w):
    _pair(w, {"mount_quote": "Serrer le couvercle à 30 N·m."})
    status = _status(w)
    assert status["status"] == "FAIL" and status["pairs"][0]["blocking"][0]["anchored"] is False


def test_single_domain_conserver_complete_is_declassed_then_blocks(w):
    _pair(w, {"mount_sources": "a"})
    status = _status(w)
    assert status["status"] == "FAIL" and status["pairs"][0]["blocking"][0]["declassed_by"] == "control"


def test_forged_corroboration_is_unreadable(w):
    # Un conserver complete dont la corroboration consignée ne correspond plus aux passages.
    q = _qual(w)
    claim = _mount(q)
    claim["sources"] = claim["sources"][:1]
    q["retake_questions"] = []
    _record(w, q)
    status = _status(w)
    assert status["status"] == "UNREADABLE"
    assert "corroboration incohérente" in status["unreadable"][0]["error"]


def test_catalog_without_publisher_class_declasses_every_complete_conserver(w):
    catalog = _catalog(w.cid_a, w.cid_b, publisher_class=False)
    (w.root / tq.CATALOG_RELPATH).write_text(yaml.safe_dump(catalog), encoding="utf-8")
    _commit(w.root)
    q = _qual(w)
    assert _mount(q)["verdict"] == "preciser"
    assert _mount(q)["corroboration"]["declassed_by"] == "control"
    p = _record(w, q)
    _record(w, _contest(w, p))
    assert _status(w)["status"] == "FAIL"


@pytest.mark.parametrize("positions, expected", [
    ({"c2": ("contest", "conserver")}, "FAIL"),     # complete : toute position autre que agree bloque
    ({"c2": ("undecidable", None)}, "FAIL"),
    ({"c1": ("contest", "preciser")}, "CONTESTED"),  # allegee : consignée, non acquise
    ({"c1": ("undecidable", None)}, "CONTESTED"),
    ({"c1": ("contest", "retirer")}, "FAIL"),
    ({"c1": ("contest", None)}, "FAIL"),             # verdict inconnu : fail-closed
])
def test_contestation_takes_the_stricter_verdict(w, positions, expected):
    _pair(w, contest_kwargs={"positions": positions})
    assert _status(w)["status"] == expected


def test_contested_claim_is_not_replaced_by_another_agreeing_pair(w):
    q = _record(w, _qual(w))
    _record(w, _contest(w, q, positions={"c1": ("contest", "preciser")}))
    _record(w, _contest(w, q, reviewer={"model": "gpt-5.5-pro", "provider": "openai"}))
    assert _status(w)["status"] == "CONTESTED"


@pytest.mark.parametrize("checks", [{"concordance": "holds", "independence": "fails"},
                                    {"concordance": "fails", "independence": "holds"}])
def test_failed_independence_or_concordance_check_blocks_a_complete_conserver(w, checks):
    _pair(w, contest_kwargs={"checks": checks})
    status = _status(w)
    assert status["status"] == "FAIL" and _blocking(status) == ["body:4 c2"]


@pytest.mark.parametrize("verdict, segment, expected", [
    ("retirer", "body:2", "FAIL"),
    ("preciser", "body:2", "PASS"),
    ("conserver", "body:4", "FAIL"),  # complete : un seul passage, un seul domaine
])
def test_missed_claim_follows_the_blocking_rule(w, verdict, segment, expected):
    quote = "Le filtre retient les poussières."
    _pair(w, contest_kwargs={"missed": [{"segment_id": segment, "text": "oubli", "verdict": verdict,
                                         "statement": "oubli", "passage": _passage(w, "a", quote)}]})
    assert _status(w)["status"] == expected


def test_artifacts_of_a_previous_text_are_stale(w):
    _pair(w)
    status = _status(w, body=w.body + "\nUne phrase de plus.\n")
    assert status["status"] == "STALE" and status["pass"] is False


def test_skill_revision_changes_the_key(w):
    _pair(w)
    (w.root / tq.SKILL_RELPATH).write_text("révision\n", encoding="utf-8")
    _commit(w.root)
    assert _status(w)["status"] == "STALE"


def test_removed_or_uncommitted_artifact_is_a_history_gap(w):
    failed = _pair(w, {"mount": "retirer"})
    failed.unlink()
    _commit(w.root)
    status = _status(w)
    assert status["status"] == "HISTORY_GAP" and status["pass"] is False
    assert any("retirée" in gap for gap in status["history_gaps"])
    assert "absente de la clé" in status["unreadable"][0]["error"]  # la contestation reste orpheline


def test_uncommitted_artifact_is_a_history_gap(w):
    _pair(w)
    _record(w, _qual(w, role_verdict="preciser"), commit=False)
    assert _status(w)["status"] == "HISTORY_GAP"


def test_unreadable_or_orphan_artifact_blocks_a_pass(w):
    q = _pair(w)
    bad = q.parent / ("0" * 64 + ".json")
    bad.write_text("{}", encoding="utf-8")
    _commit(w.root)
    status = _status(w)
    assert status["status"] == "UNREADABLE" and status["pass"] is False


def test_fiche_without_raw_capture_is_no_capture(w):
    fm = {k: v for k, v in w.fm.items() if k != "source_refs"}
    assert _status(w, fm=fm)["status"] == "NO_CAPTURE"


@pytest.mark.parametrize("missing", ["catalog", "skill", "schema"])
def test_missing_governed_input_is_unavailable(w, missing):
    rel = {"catalog": tq.CATALOG_RELPATH, "skill": tq.SKILL_RELPATH, "schema": tq.RUN_SCHEMA_RELPATH}[missing]
    (w.root / rel).unlink()
    with pytest.raises(tq._sibling("semantic_review").ReviewInputUnavailable):
        _status(w)


# --- Plancher de profondeur (ADR-131 D4) -----------------------------------------------------

def _floor(fm, body):
    return {sid: reasons for sid, (_, reasons) in tq.depth_floors(fm, sr.segments(fm, body)).items()}


def test_floor_safety_family_covers_every_segment():
    fm = {"entity_type": "gamme", "slug": "plaquette-de-frein", "title": "Plaquette"}
    floors = _floor(fm, "## Rôle\n\nTexte descriptif.\n")
    assert all("safety_family" in r for r in floors.values())


def test_floor_numeric_procedure_and_diagnostic_motifs():
    fm = {"entity_type": "gamme", "slug": "filtre-test", "title": "Filtre",
          "maintenance_interval": "selon carnet", "diagnostic_relations": [{"symptom": "bruit"}],
          "entity_data": {"failure_symptoms": ["colmatage"]}, "aliases": ["filtre"]}
    body = ("## Rôle\n\nTexte descriptif.\n\nPoids 2 kg.\n\n## Entretien\n\nContrôler.\n\n"
            "## Symptômes\n\nBruit.\n")
    floors = _floor(fm, body)
    assert floors["body:2"] == [] and floors["fm:aliases"] == []
    assert floors["body:3"] == ["numeric_value"]
    assert floors["body:5"] == ["procedure"] and floors["fm:maintenance_interval"] == ["procedure"]
    assert floors["body:7"] == ["diagnostic_relation"]
    assert floors["fm:diagnostic_relations"] == ["diagnostic_relation"]
    assert floors["fm:entity_data"] == ["diagnostic_relation"]
