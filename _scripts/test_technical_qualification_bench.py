"""Tests de _scripts/technical_qualification_bench.py — banc d'étalonnage, hors ligne (relecteur simulé)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import technical_qualification_bench as tb  # noqa: E402

CAP_A = "---\nsource_url: https://www.user-manual.renault.com/x\n---\nRemplacer les plaquettes par essieu complet.\n"
CAP_B = "---\nsource_url: https://www.bremboparts.com/y\n---\nAlways replace brake pads per axle.\n"


def _cid(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def setup(tmp_path):
    raw = tmp_path / "raw"
    (raw / "sources").mkdir(parents=True)
    (raw / "sources/a.md").write_text(CAP_A, encoding="utf-8")
    (raw / "sources/b.md").write_text(CAP_B, encoding="utf-8")
    catalog = {"source_type_editorial_role": {"oem_manual": "proof", "brochure": "corroboration"},
               "sources": [{"slug": "renault", "publisher": "Renault", "type": "oem_manual",
                            "raw_ref": {"expected_sha256": _cid(CAP_A)}}]}
    (tmp_path / "catalog.yaml").write_text(yaml.safe_dump(catalog), encoding="utf-8")
    table = {"captures": [
        {"cid": _cid(CAP_A), "publisher": "Renault", "type": "oem_manual", "publisher_class": "constructeur"},
        {"cid": _cid(CAP_B), "publisher": "Brembo", "type": "oem_manual", "publisher_class": "equipementier"}]}
    (tmp_path / "domains.yaml").write_text(yaml.safe_dump(table), encoding="utf-8")
    case = {"slug": "plaquette-de-frein",
            "fm": {"slug": "plaquette-de-frein", "title": "Plaquette de frein",
                   "source_refs": [{"kind": "raw", "path": "sources/a.md", "cid": _cid(CAP_A)},
                                   {"kind": "raw", "path": "sources/b.md", "cid": _cid(CAP_B)}]},
            "body": "## Critères\n\nLes plaquettes se remplacent par essieu.\n",
            "subject": {"repo": "automecanik-wiki", "path": "wiki/gamme/plaquette-de-frein.md",
                        "commit": "67e49d821f17a73692ca0eb976791bcb092483ca", "slug": "plaquette-de-frein"},
            "freshness": {"read_from": "origin", "ref": "origin/main",
                          "commit": "67e49d821f17a73692ca0eb976791bcb092483ca",
                          "raw_commit": "4b4de7180092dd5145f106ed37bbd166b6fd9fb1",
                          "checked_at": "2026-11-15T17:52:04Z"},
            "producer": {"declared": "test", "provider": "unknown", "basis": "test"}}
    (tmp_path / "case.json").write_text(json.dumps(case), encoding="utf-8")
    return tmp_path


def _fake_reviewer(tmp_path: Path, answer: dict) -> str:
    """Relecteur simulé : lit l'invite sur stdin, renvoie `answer` dans un bloc ```json."""
    script = tmp_path / "fake.py"
    script.write_text("import sys, json\nsys.stdin.read()\n"
                      f"print('```json\\n' + json.dumps({answer!r}) + '\\n```')\n", encoding="utf-8")
    return f"{sys.executable} {script} --model {{model}}"


def _claim(verdict, concordance, sources):
    return {"text": "Les plaquettes se remplacent par essieu.", "verdict": verdict, "sources": sources,
            "portee": "tout véhicule", "limite": "aucune", "proposed_wording": None,
            "corroboration": {"concordance": concordance, "discordance_on": None}}


def _answer(claims):
    segs = [{"id": i, "no_claims": True} for i in ("fm:slug", "fm:source_refs", "fm:title", "body:1")]
    return {"segments": segs + [{"id": "body:2", "depth": "complete", "claims": claims}]}


QA = {"path": "sources/a.md", "cid": _cid(CAP_A), "quote": "Remplacer les plaquettes par essieu complet."}
QB = {"path": "sources/b.md", "cid": _cid(CAP_B), "quote": "Always replace brake pads per axle."}


def _qualify(setup, answer, runs=1):
    cmd = _fake_reviewer(setup, answer)
    out = setup / "out"
    rc = tb.main(["qualify", str(setup / "case.json"), "--raw-root", str(setup / "raw"),
                  "--catalog", str(setup / "catalog.yaml"), "--domains", str(setup / "domains.yaml"),
                  "--model", "fake-1", "--provider", "anthropic", "--command", cmd, "--out", str(out),
                  "--runs", str(runs), "--jobs", "1", "--timeout", "30"])
    assert rc == 0
    return sorted(out.rglob("*.json"))


def test_merge_domains_sets_class_and_synthesizes_missing_entry(setup):
    catalog = yaml.safe_load((setup / "catalog.yaml").read_text())
    table = yaml.safe_load((setup / "domains.yaml").read_text())
    merged = tb.merge_domains(catalog, table)
    by_cid = {e["raw_ref"]["expected_sha256"]: e for e in merged["sources"]}
    assert by_cid[_cid(CAP_A)]["publisher_class"] == "constructeur"
    assert by_cid[_cid(CAP_B)]["publisher"] == "Brembo"
    assert "publisher_class" not in catalog["sources"][0]  # fusion en mémoire, entrée intacte


def test_shard_is_deterministic_and_bounded():
    segs = [{"id": f"s{i}", "text": "x" * n} for i, n in enumerate([40, 40, 40, 200, 10])]
    groups = tb.shard(segs, 100)
    assert [[s["id"] for s in g] for g in groups] == [["s0", "s1"], ["s2"], ["s3"], ["s4"]]
    assert tb.shard(segs, 100) == groups


def test_invite_extraction_reads_skill_and_rejects_unknown():
    text = tb.SKILL.read_text(encoding="utf-8")
    assert tb.invite(text, "qualification").strip()
    assert tb.invite(text, "contestation").strip()
    with pytest.raises(ValueError):
        tb.invite(text, "inconnue")


def test_anchored_normalizes_and_checks_path_and_cid():
    texts = {("a.md", "sha256:1"): "Remplacer   les plaquettes\npar essieu."}
    assert tb.anchored({"path": "a.md", "cid": "sha256:1", "quote": "les plaquettes par essieu"}, texts)
    assert not tb.anchored({"path": "a.md", "cid": "sha256:2", "quote": "les plaquettes"}, texts)
    assert not tb.anchored({"path": "a.md", "cid": "sha256:1", "quote": "disque"}, texts)
    assert not tb.anchored({"path": "a.md", "cid": "sha256:1", "quote": " "}, texts)


def test_floors_follow_skill_reasons(setup):
    case = json.loads((setup / "case.json").read_text())
    prep = tb.prepare(case, setup / "raw", setup / "catalog.yaml", setup / "domains.yaml", "publisher_class", 5000)
    assert all(s["depth_floor"] == "complete" and "safety_family" in s["depth_floor_reasons"]
               for s in prep["segments"])
    domains = {d["publisher"]: d["domain"] for d in prep["key_inputs"]["capture_domains"]}
    assert domains == {"Renault": "constructeur", "Brembo": "equipementier"}
    assert "domains.yaml" in prep["key_inputs"]["domain_basis"]


def test_qualify_two_domains_keeps_conserver_and_writes_valid_artifact(setup):
    files = _qualify(setup, _answer([_claim("conserver", "concordant", [QA, QB])]))
    art = json.loads(files[0].read_text())
    claim = next(s for s in art["segments"] if s["id"] == "body:2")["claims"][0]
    assert claim["verdict"] == "conserver"
    assert claim["corroboration"]["domains"] == ["constructeur", "equipementier"]
    assert art["key_inputs"]["skill_sha256"] == hashlib.sha256(tb.SKILL.read_bytes()).hexdigest()
    assert files[0].name == hashlib.sha256(files[0].read_bytes()).hexdigest() + ".json"


def test_qualify_single_domain_declasses_conserver(setup):
    files = _qualify(setup, _answer([_claim("conserver", "concordant", [QB])]))
    claim = next(s for s in json.loads(files[0].read_text())["segments"] if s["id"] == "body:2")["claims"][0]
    assert claim["verdict"] == "preciser"
    assert claim["corroboration"]["declassed_by"] == "control"


def test_qualify_records_reviewer_failure_in_artifact(setup):
    files = _qualify(setup, {"segments": "pas une liste"})
    art = json.loads(files[0].read_text())
    assert "segment absent" in art["error"]


def test_variance_counts_recovered_share_and_dispersion(setup):
    files = _qualify(setup, _answer([_claim("conserver", "concordant", [QA, QB])]), runs=2)
    arts = [(str(f), json.loads(f.read_text())) for f in files]
    arts.append(("x", {**arts[0][1], "segments": [
        {"id": "body:2", "depth_floor": "complete", "depth": "complete",
         "claims": [{**arts[0][1]["segments"][-1]["claims"][0], "verdict": "retirer"}]}]}))
    expected = {"targets": [{"id": "T", "case": "plaquette-de-frein", "segment": "body:2", "match": "essieu",
                             "expected": "conserver", "defensible": ["preciser"]},
                            {"id": "U", "case": "plaquette-de-frein", "segment": "body:2", "match": "disque",
                             "expected": "retirer", "defensible": []}]}
    assert len(files) == 2 and files[0].parent.name == "run-00" and files[1].parent.name == "run-01"
    report = tb.variance(expected, arts, setup / "raw")
    t, u = report["targets"]
    assert t["runs"] == 3 and t["recovered"] == pytest.approx(2 / 3) and t["distinct"] == 2
    assert u["verdicts"] == ["absent"] * 3 and u["recovered"] == 0
    assert report["anchoring"]["quotes"] == report["anchoring"]["anchored"] == 6
    assert "| `T` |" in tb.markdown(report)


def test_variance_flags_conserver_whose_limit_describes_a_contradiction():
    claim = {"id": "c0", "text": "t", "verdict": "conserver", "limite": "Dacia contredit ZF sur le bruit",
             "portee": "p", "sources": [], "corroboration": {}}
    art = {"role": "qualification", "subject": {"slug": "s"}, "reviewer": {"model": "m", "provider": "anthropic"},
           "key_inputs": {"captures": []}, "segments": [{"id": "body:1", "claims": [claim]}]}
    report = tb.variance({"targets": []}, [("a", art)])
    assert report["conserver_limit_signals"][0]["claim"] == "c0"
