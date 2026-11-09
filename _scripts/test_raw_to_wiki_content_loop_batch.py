"""Tests — raw_to_wiki_content_loop_batch (Option A thin wrapper, cadrage 2026-07-15).

Couvre le périmètre STRICT + les 5 défauts bloquants de la revue owner PR #82 :
  (1) --out ne peut PAS écraser la worklist ni écrire sous raw_root/wiki_root ;
  (2) le verdict pilote imbriqué (`verdicts`) est relayé, jamais aplati/perdu ;
  (3) worklist/schéma = chemins CANONIQUES dérivés de raw_root (pas de couple inventé) ;
  (4) une capture dont le fichier n'existe pas sur disque = INPUT_NOT_READY (pas d'appel pilote) ;
  (5) [CI] la suite est exécutée explicitement par GitHub Actions (voir wiki-quality-gates.yml).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import raw_to_wiki_content_loop_batch as batch  # noqa: E402


def _entry(eid, stype="vehicle_gamme_fit", gamme="disque-de-frein", status="TODO",
           raw_path=None, priority="P0"):
    return {
        "id": eid,
        "subject_type": stype,
        "gamme": gamme,
        "vehicle": {"brand": "Renault", "model": "Clio III", "motorisation": "1.5 dCi"},
        "topic": "x",
        "target_consumer": ["R8", "R1", "R2"],
        "priority": priority,
        "rationale": "x",
        "source": {"authoritative_domain": None, "url": None, "source_type": None,
                   "license": None, "license_status": "unknown"},
        "capture": {"status": status, "content_hash": None, "captured_at": None,
                    "raw_path": raw_path},
    }


MINIMAL_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "worklist"],
    "additionalProperties": True,
    "properties": {
        "schema_version": {"type": "string"},
        "worklist": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "subject_type"],
                "properties": {
                    "id": {"type": "string"},
                    "subject_type": {"enum": ["vehicle", "gamme", "vehicle_gamme_fit",
                                              "product_fact"]},
                    "gamme": {"type": ["string", "null"]},
                    "vehicle": {"type": ["object", "null"]},
                    "capture": {"type": "object"},
                },
            },
        },
    },
}


def _write_env(tmp_path, entries, schema=MINIMAL_SCHEMA):
    """Construit un raw_root CANONIQUE (manifests/ + _schemas/) + un wiki_root."""
    raw_root = tmp_path / "raw"
    (raw_root / "_schemas").mkdir(parents=True)
    (raw_root / "manifests").mkdir(parents=True)
    wl = raw_root / "manifests" / "ingestion-worklist.yaml"
    wl.write_text(yaml.safe_dump({"schema_version": "1.0.0", "worklist": entries},
                                 allow_unicode=True, sort_keys=False), encoding="utf-8")
    schema_path = raw_root / "_schemas" / "ingestion-worklist.schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    wiki_root = tmp_path / "wiki"
    (wiki_root / "proposals").mkdir(parents=True)
    (wiki_root / "_scripts").mkdir(parents=True)
    monorepo_root = tmp_path / "app"
    monorepo_root.mkdir()
    return {"worklist": wl, "schema": schema_path, "raw_root": raw_root,
            "wiki_root": wiki_root, "monorepo_root": monorepo_root}


def _run(env, runner=None):
    return batch.run_batch(
        raw_root=env["raw_root"], wiki_root=env["wiki_root"],
        monorepo_root=env["monorepo_root"], baseline_ref="origin/main",
        threshold=0.80, pilot_runner=(runner or _never_call),
    )


def _never_call(*a, **k):
    raise AssertionError("pilot_runner must NOT be called for INPUT_NOT_READY facets")


# ── périmètre de base ────────────────────────────────────────────────────────

def test_selects_only_vehicle_gamme_fit_sorted(tmp_path):
    env = _write_env(tmp_path, [
        _entry("wl-b-vgf"), _entry("wl-a-vgf"),
        _entry("wl-c-gamme", stype="gamme"), _entry("wl-d-pf", stype="product_fact"),
    ])
    ids = [r["worklist_id"] for r in _run(env)["rows"]]
    assert ids == ["wl-a-vgf", "wl-b-vgf"]


def test_todo_entry_both_facets_input_not_ready_no_pilot_call(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-todo", status="TODO")])
    facets = _run(env, runner=_never_call)["rows"][0]["facets"]
    assert facets["gamme"]["state"] == "INPUT_NOT_READY"
    assert facets["vehicle"]["state"] == "INPUT_NOT_READY"
    assert facets["gamme"]["pilot_verdict"] is None
    assert facets["vehicle"]["pilot_verdict"] is None


def test_no_couple_level_verdict(tmp_path):
    row = _run(_write_env(tmp_path, [_entry("wl-x")]))["rows"][0]
    assert set(row["facets"].keys()) == {"gamme", "vehicle"}
    forbidden = {"couple_verdict", "couple_score", "vehicle_gamme_fit_verdict",
                 "verdict", "score", "tier"}
    assert forbidden.isdisjoint(row.keys())


def test_deterministic_same_input_same_report(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-1"), _entry("wl-2", gamme="plaquette-de-frein")])
    assert _run(env) == _run(env)


def test_counts_are_mechanical_aggregation(tmp_path):
    report = _run(_write_env(tmp_path, [_entry("wl-1"), _entry("wl-2")]))
    assert report["counts"]["couples"] == 2
    assert report["counts"]["facets_input_not_ready"] == 4
    assert report["counts"]["facets_pilot_ran"] == 0


# ── défaut (1) : --out ne peut pas écrire sous un dépôt pipeline ─────────────

def test_out_fail_closed_worklist_overwrite(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-x")])
    before = env["worklist"].read_bytes()
    with pytest.raises(batch.UnsafeOutputPath):
        batch.write_report({"k": 1}, env["worklist"], env["raw_root"], env["wiki_root"])
    assert env["worklist"].read_bytes() == before  # worklist intacte


def test_out_fail_closed_anywhere_under_wiki(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-x")])
    bad = env["wiki_root"] / "_scripts" / "leak.json"
    with pytest.raises(batch.UnsafeOutputPath):
        batch.write_report({"k": 1}, bad, env["raw_root"], env["wiki_root"])
    assert not bad.exists()


def test_out_fail_closed_inside_raw_sources(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-x")])
    (env["raw_root"] / "sources").mkdir()
    bad = env["raw_root"] / "sources" / "leak.json"
    with pytest.raises(batch.UnsafeOutputPath):
        batch.write_report({"k": 1}, bad, env["raw_root"], env["wiki_root"])
    assert not bad.exists()


def test_out_allowed_outside_stores(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-x")])
    good = tmp_path / "out" / "report.json"  # hors raw_root ET wiki_root
    batch.write_report({"k": 1}, good, env["raw_root"], env["wiki_root"])
    assert good.exists()


# ── défaut (2) : verdict pilote imbriqué relayé, jamais perdu ────────────────

def test_pilot_nested_verdicts_relayed(tmp_path):
    env = _write_env(tmp_path, [
        _entry("wl-cap", status="CAPTURED", raw_path="sources/web-research/disque-de-frein/f.md"),
    ])
    src = env["raw_root"] / "sources" / "web-research" / "disque-de-frein" / "f.md"
    src.parent.mkdir(parents=True)
    src.write_text("x", encoding="utf-8")
    calls = []

    def fake(entity_id, **kw):  # forme RÉELLE du pilote : verdicts imbriqués
        calls.append(entity_id)
        return {"verdicts": {"projection_operational": False, "outcome_status": "PENDING",
                             "business_loop_closed": False},
                "remaining_blockers": [{"stage": "wiki_proposal", "state": "FAIL"}],
                "tier_after": "C"}

    facets = _run(env, runner=fake)["rows"][0]["facets"]
    assert calls == ["gamme:disque-de-frein"]
    g = facets["gamme"]
    assert g["state"] == "RESOLVED_PILOT_RAN"
    # projection_operational / business_loop_closed NE sont PAS silencieusement supprimés
    assert g["pilot_verdict"]["verdicts"]["projection_operational"] is False
    assert g["pilot_verdict"]["verdicts"]["business_loop_closed"] is False
    assert g["pilot_verdict"]["remaining_blockers"][0]["stage"] == "wiki_proposal"
    # facette véhicule : pas de slug explicite → non résoluble (0 invention)
    assert facets["vehicle"]["state"] == "INPUT_NOT_READY"
    assert facets["vehicle"]["entity_id"] is None


# ── défaut (3) : chemins canoniques dérivés de raw_root (pas de couple inventé) ─

def test_only_canonical_worklist_under_raw_root_is_read(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-real")])
    # worklist pirate (couple inventé) posée AILLEURS sous raw_root → jamais lue
    rogue = env["raw_root"] / "rogue-worklist.yaml"
    rogue.write_text(yaml.safe_dump({"schema_version": "1.0.0",
                                     "worklist": [_entry("wl-INVENTED")]}), encoding="utf-8")
    ids = [r["worklist_id"] for r in _run(env)["rows"]]
    assert ids == ["wl-real"]  # seule manifests/ingestion-worklist.yaml canonique est lue


def test_fail_closed_when_canonical_worklist_missing(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-x")])
    env["worklist"].unlink()
    with pytest.raises(batch.WorklistError):
        _run(env)


def test_fail_closed_on_missing_schema_file(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-x")])
    env["schema"].unlink()  # schéma absent → JAMAIS de skip silencieux
    with pytest.raises(batch.WorklistError):
        _run(env)


def test_fail_closed_on_schema_invalid(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-bad", stype="not_a_type")])  # viole l'enum
    with pytest.raises(batch.WorklistError):
        _run(env)


# ── défaut (4) : existence disque réelle de la capture ──────────────────────

def test_captured_status_but_missing_file_is_input_not_ready(tmp_path):
    env = _write_env(tmp_path, [
        _entry("wl-cap", status="CAPTURED",
               raw_path="sources/web-research/disque-de-frein/missing.md"),
    ])
    # le fichier n'est PAS créé → capture inexistante
    facets = _run(env, runner=_never_call)["rows"][0]["facets"]  # AssertionError si pilote appelé
    assert facets["gamme"]["state"] == "INPUT_NOT_READY"
    assert "absent" in facets["gamme"]["reason"].lower()


def test_raw_path_outside_sources_is_rejected(tmp_path):
    env = _write_env(tmp_path, [
        _entry("wl-cap", status="CAPTURED", raw_path="manifests/ingestion-worklist.yaml"),
    ])  # existe, mais HORS sources/ → fail-closed
    facets = _run(env, runner=_never_call)["rows"][0]["facets"]
    assert facets["gamme"]["state"] == "INPUT_NOT_READY"
    assert "sources" in facets["gamme"]["reason"].lower()


def test_raw_path_traversal_is_rejected(tmp_path):
    env = _write_env(tmp_path, [
        _entry("wl-cap", status="CAPTURED", raw_path="sources/../../etc/passwd"),
    ])
    facets = _run(env, runner=_never_call)["rows"][0]["facets"]
    assert facets["gamme"]["state"] == "INPUT_NOT_READY"


# ── invariant zéro-écriture worklist ─────────────────────────────────────────

def test_worklist_file_not_written(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-x")])
    before = env["worklist"].read_bytes()
    _run(env)
    assert env["worklist"].read_bytes() == before
