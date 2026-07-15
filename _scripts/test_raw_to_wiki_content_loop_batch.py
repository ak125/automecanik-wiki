"""Tests — raw_to_wiki_content_loop_batch (Option A thin wrapper, cadrage 2026-07-15).

Vérifie le périmètre STRICT du GO owner : sélection worklist-only, gating INPUT_NOT_READY
sans tentative de collecte, fail-closed, appel pilote injecté (par facette), déterminisme,
sortie fail-closed hors stores, et invariant zéro-écriture worklist.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import raw_to_wiki_content_loop_batch as batch  # noqa: E402


# ── fixtures d'environnement (temp, hermétiques) ─────────────────────────────

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
                    "subject_type": {
                        "enum": ["vehicle", "gamme", "vehicle_gamme_fit", "product_fact"]
                    },
                    "gamme": {"type": ["string", "null"]},
                    "vehicle": {"type": ["object", "null"]},
                    "capture": {"type": "object"},
                },
            },
        },
    },
}


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


def _write_env(tmp_path, entries, schema=MINIMAL_SCHEMA):
    import yaml
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
    monorepo_root = tmp_path / "app"
    monorepo_root.mkdir()
    return {"worklist": wl, "schema": schema_path, "raw_root": raw_root,
            "wiki_root": wiki_root, "monorepo_root": monorepo_root}


def _run(env, runner=None):
    return batch.run_batch(
        worklist_path=env["worklist"], schema_path=env["schema"],
        raw_root=env["raw_root"], wiki_root=env["wiki_root"],
        monorepo_root=env["monorepo_root"], baseline_ref="origin/main",
        threshold=0.80, pilot_runner=(runner or _never_call),
    )


def _never_call(*a, **k):  # pilote qui échoue si jamais appelé
    raise AssertionError("pilot_runner must NOT be called for INPUT_NOT_READY facets")


# ── tests ────────────────────────────────────────────────────────────────────

def test_selects_only_vehicle_gamme_fit_sorted(tmp_path):
    env = _write_env(tmp_path, [
        _entry("wl-b-vgf"),
        _entry("wl-a-vgf"),
        _entry("wl-c-gamme", stype="gamme"),
        _entry("wl-d-pf", stype="product_fact"),
    ])
    report = _run(env)
    ids = [r["worklist_id"] for r in report["rows"]]
    assert ids == ["wl-a-vgf", "wl-b-vgf"]  # only vgf, sorted by id


def test_todo_entry_both_facets_input_not_ready_no_pilot_call(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-todo", status="TODO")])
    report = _run(env, runner=_never_call)  # AssertionError if pilot invoked
    facets = report["rows"][0]["facets"]
    assert facets["gamme"]["state"] == "INPUT_NOT_READY"
    assert facets["vehicle"]["state"] == "INPUT_NOT_READY"
    assert "TODO" in facets["gamme"]["reason"] or "captur" in facets["gamme"]["reason"].lower()
    assert facets["gamme"]["pilot_verdict"] is None
    assert facets["vehicle"]["pilot_verdict"] is None


def test_fail_closed_on_schema_invalid(tmp_path):
    # subject_type illégal → viole l'enum du schéma → fail-closed, aucun rapport
    env = _write_env(tmp_path, [_entry("wl-bad", stype="not_a_type")])
    with pytest.raises(batch.WorklistError):
        _run(env)


def test_fail_closed_on_missing_schema_file(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-x")])
    env["schema"].unlink()  # schéma absent → JAMAIS de skip silencieux
    with pytest.raises(batch.WorklistError):
        _run(env)


def test_captured_gamme_invokes_pilot_vehicle_unresolvable(tmp_path):
    env = _write_env(tmp_path, [
        _entry("wl-cap", status="CAPTURED", raw_path="sources/web-clips/x.md"),
    ])
    calls = []

    def fake_runner(entity_id, **kw):
        calls.append(entity_id)
        return {"projection_operational": False, "business_loop_closed": False,
                "remaining_blockers": ["wiki_proposal"]}

    report = _run(env, runner=fake_runner)
    facets = report["rows"][0]["facets"]
    # gamme facette : résolue → pilote appelé UNE fois avec gamme:<slug>
    assert calls == ["gamme:disque-de-frein"]
    assert facets["gamme"]["state"] == "RESOLVED_PILOT_RAN"
    assert facets["gamme"]["entity_id"] == "gamme:disque-de-frein"
    assert facets["gamme"]["pilot_verdict"]["remaining_blockers"] == ["wiki_proposal"]
    # vehicle facette : pas de slug explicite dans la worklist → INPUT_NOT_READY (0 invention)
    assert facets["vehicle"]["state"] == "INPUT_NOT_READY"
    assert facets["vehicle"]["entity_id"] is None


def test_no_couple_level_verdict(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-x")])
    row = _run(env)["rows"][0]
    assert set(row["facets"].keys()) == {"gamme", "vehicle"}
    forbidden = {"couple_verdict", "couple_score", "vehicle_gamme_fit_verdict",
                 "verdict", "score", "tier"}
    assert forbidden.isdisjoint(row.keys())


def test_deterministic_same_input_same_report(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-1"), _entry("wl-2", gamme="plaquette-de-frein")])
    assert _run(env) == _run(env)


def test_out_path_fail_closed_inside_wiki_proposals(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-x")])
    bad = env["wiki_root"] / "proposals" / "leak.json"
    with pytest.raises(batch.UnsafeOutputPath):
        batch.write_report({"kind": "x"}, bad, env["raw_root"], env["wiki_root"])
    assert not bad.exists()


def test_out_path_fail_closed_inside_raw_sources(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-x")])
    (env["raw_root"] / "sources").mkdir()
    bad = env["raw_root"] / "sources" / "leak.json"
    with pytest.raises(batch.UnsafeOutputPath):
        batch.write_report({"kind": "x"}, bad, env["raw_root"], env["wiki_root"])
    assert not bad.exists()


def test_worklist_file_not_written(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-x")])
    before = env["worklist"].read_bytes()
    _run(env)
    assert env["worklist"].read_bytes() == before  # zéro écriture worklist


def test_counts_are_mechanical_aggregation(tmp_path):
    env = _write_env(tmp_path, [_entry("wl-1"), _entry("wl-2")])
    report = _run(env)
    assert report["counts"]["couples"] == 2
    # 2 couples × 2 facettes, toutes TODO/unresolvable → 4 INPUT_NOT_READY, 0 pilot
    assert report["counts"]["facets_input_not_ready"] == 4
    assert report["counts"]["facets_pilot_ran"] == 0
