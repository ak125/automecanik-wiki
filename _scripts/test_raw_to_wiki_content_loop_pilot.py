"""Tests raw_to_wiki_content_loop_pilot — l'ORCHESTRATEUR (helpers purs + logique blockers).

Le run() complet est intégration (repos + subprocess) ; ici on verrouille les parties pures :
extraction JSON robuste (le bug citation), détection RAW, et que loop_closed dérive des blockers."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
_spec = importlib.util.spec_from_file_location("loop_pilot", SCRIPTS_DIR / "raw_to_wiki_content_loop_pilot.py")
lp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lp)


def test_extract_json_strips_warn_preamble():
    # cas réel : citation-readiness imprime des lignes WARN AVANT le JSON sur stdout.
    s = 'WARN a\nWARN b\n{\n  "reports": [{"entity_id": "gamme:x", "status": "PARTIAL"}]\n}\n'
    assert lp._extract_json(s)["reports"][0]["status"] == "PARTIAL"


def test_extract_json_handles_list_and_indent():
    assert lp._extract_json("bruit\n  [1, 2, 3]\n") == [1, 2, 3]


def test_extract_json_raises_without_json():
    import pytest
    with pytest.raises(ValueError):
        lp._extract_json("que du texte\nsans json\n")


def test_stage_raw_counts_md_and_index(tmp_path):
    d = tmp_path / "sources" / "web-research" / "x"
    d.mkdir(parents=True)
    (d / "a.md").write_text("x", encoding="utf-8")
    (d / "b.md").write_text("y", encoding="utf-8")
    (d / "deep-source-index.json").write_text("{}", encoding="utf-8")
    r = lp.stage_raw("x", tmp_path)
    assert r["ok"] and r["md_files"] == 2 and r["has_source_index"]


def test_stage_raw_absent_is_not_ok(tmp_path):
    r = lp.stage_raw("inexistant", tmp_path)
    assert not r["ok"] and r["md_files"] == 0


def test_stage_consumer_replay_only_is_blocked(tmp_path):
    # un repo monorepo avec SEULEMENT replay_projection.py → pas de writer forward → bloqué.
    proj = tmp_path / "scripts" / "seo-projection"
    proj.mkdir(parents=True)
    (proj / "replay_projection.py").write_text("# exports/seo replay only, no INSERT", encoding="utf-8")
    r = lp.stage_consumer("plaquette-de-frein", tmp_path)
    assert not r["ok"] and r["forward_writer"] is None


def test_stage_consumer_detects_forward_writer(tmp_path):
    proj = tmp_path / "scripts" / "seo-projection"
    proj.mkdir(parents=True)
    (proj / "project_exports.py").write_text(
        "# reads exports/seo and writes\nq = 'INSERT INTO __seo_entity_facts ...'\n", encoding="utf-8")
    r = lp.stage_consumer("plaquette-de-frein", tmp_path)
    assert r["ok"] and r["forward_writer"] == "project_exports.py"
