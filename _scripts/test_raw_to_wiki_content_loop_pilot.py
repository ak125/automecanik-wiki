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
    legacy = r["legacy_web_research"]
    assert r["state"] == lp.PASS and legacy["md_files"] == 2 and legacy["has_source_index"]


def test_stage_raw_absent_is_not_ok(tmp_path):
    r = lp.stage_raw("inexistant", tmp_path)
    assert r["state"] == lp.FAIL and r["legacy_web_research"]["md_files"] == 0


def test_stage_consumer_replay_only_is_blocked(tmp_path):
    # un repo monorepo avec SEULEMENT replay_projection.py → pas de writer forward → bloqué.
    (tmp_path / "backend").mkdir()
    proj = tmp_path / "scripts" / "seo-projection"
    proj.mkdir(parents=True)
    (proj / "replay_projection.py").write_text("# exports/seo replay only, no INSERT", encoding="utf-8")
    r = lp.static_proofs(tmp_path)["writer_code_present"]
    assert r["state"] == lp.FAIL and r["kind"] is None


def test_stage_consumer_detects_forward_writer(tmp_path):
    (tmp_path / "backend").mkdir()
    proj = tmp_path / "scripts" / "seo-projection"
    proj.mkdir(parents=True)
    (proj / "project_exports.py").write_text(
        "# reads exports/seo and writes\nq = 'INSERT INTO __seo_entity_facts ...'\n", encoding="utf-8")
    r = lp.static_proofs(tmp_path)["writer_code_present"]
    assert r["state"] == lp.PASS and r["kind"] == "python_legacy"
    assert "project_exports.py" in r["detail"]


# ── ADR-094 — page_quality_ready (additif) + garde anti-régression des 3 verdicts ──

def test_page_quality_ready_holds_until_external_components_land():
    """Composants externes UNKNOWN ⇒ HOLD (fail-closed), même avec un tier substance A."""
    verdict, comp = lp.compute_page_quality_ready("A", [])
    assert verdict == "HOLD"
    assert comp["content_substance_pass"] is True   # ⟵ ADR-092 tier A
    assert comp["no_hard_blocker"] is True
    assert comp["seo_surface_pass"] == "UNKNOWN"     # pas encore livré


def test_page_quality_ready_substance_and_blockers_feed_components():
    """content_substance_pass ⟵ tier ; no_hard_blocker ⟵ blockers ; toujours HOLD aujourd'hui."""
    verdict, comp = lp.compute_page_quality_ready("C", [{"stage": "score", "state": "FAIL"}])
    assert comp["content_substance_pass"] is False
    assert comp["no_hard_blocker"] is False
    assert verdict == "HOLD"                          # externes UNKNOWN dominent (fail-closed)


def test_three_orchestrator_verdicts_unchanged_vs_7ecd1c2():
    """Garde W1 : les 3 verdicts orchestrateur restent définis EXACTEMENT (anti-régression)."""
    src = (SCRIPTS_DIR / "raw_to_wiki_content_loop_pilot.py").read_text(encoding="utf-8")
    assert "projection_operational = static_chain_pass and projection_runtime_pass" in src
    assert "business_loop_closed = projection_operational and outcome_status == PASS" in src
    assert "loop_closed = business_loop_closed" in src

# Promotion: le capteur doit relayer la decision canonique, jamais redecider par tier.
import json
import pytest


@pytest.mark.parametrize('status,eligible,reasons,expected', [
    ('ELIGIBLE', True, [], lp.PASS),
    ('BLOCKED', False, [{'code': 'SOURCE_MISSING'}], lp.FAIL),
    ('UNKNOWN_FAIL_CLOSED', False, [{'code': 'PROVENANCE_UNAVAILABLE'}], lp.UNKNOWN),
    ('SKIP', False, [], lp.FAIL),
    ('ELIGIBLE', True, [{'code': 'SOURCE_MISSING'}], lp.UNKNOWN),
    ('ELIGIBLE', False, [], lp.UNKNOWN),
    (None, None, [], lp.UNKNOWN),
])
def test_promotion_uses_canonical_decision_not_tier(monkeypatch, tmp_path, status, eligible, reasons, expected):
    row = {'tier': 'A', 'promotion_status': status, 'eligible': eligible, 'blocking_reasons': reasons}
    monkeypatch.setattr(lp, '_run', lambda cmd: (0, json.dumps({'threshold': 0.85, 'report': [row]}), ''))
    result = lp.stage_promotion('gamme:fixture', tmp_path, None)
    assert result['state'] == expected
    assert result['blocking_reasons'] == reasons
    assert result['promotion_status'] == status


def test_promotion_does_not_accept_output_from_failed_process(monkeypatch, tmp_path):
    row = {'tier': 'A', 'promotion_status': 'ELIGIBLE', 'eligible': True, 'blocking_reasons': []}
    monkeypatch.setattr(lp, '_run', lambda cmd: (2, json.dumps({'report': [row]}), 'invalid argument'))
    assert lp.stage_promotion('gamme:fixture', tmp_path, None)['state'] == lp.UNKNOWN


@pytest.mark.parametrize('rows', [[], [{}, {}]])
def test_promotion_requires_one_unambiguous_decision(monkeypatch, tmp_path, rows):
    monkeypatch.setattr(lp, '_run', lambda cmd: (0, json.dumps({'report': rows}), ''))
    assert lp.stage_promotion('gamme:fixture', tmp_path, None)['state'] == lp.UNKNOWN


def test_promotion_forwards_raw_and_inherits_threshold(monkeypatch, tmp_path):
    calls = []
    row = {'tier': 'A', 'promotion_status': 'ELIGIBLE', 'eligible': True, 'blocking_reasons': []}
    def invoke(cmd):
        calls.append(cmd)
        return 0, json.dumps({'threshold': 0.85, 'report': [row]}), ''
    monkeypatch.setattr(lp, '_run', invoke)
    result = lp.stage_promotion('gamme:fixture', tmp_path, None, raw_root=tmp_path / 'raw')
    assert result['state'] == lp.PASS
    assert result['threshold'] == 0.85
    assert '--threshold' not in calls[0]
    assert calls[0][calls[0].index('--raw-root') + 1] == str(tmp_path / 'raw')
    assert '--dry-run' in calls[0] and '--apply' not in calls[0]
    lp.stage_promotion('gamme:fixture', tmp_path, 0.9, raw_root=tmp_path / 'raw')
    assert calls[1][calls[1].index('--threshold') + 1] == '0.9'


def test_main_inherits_promoter_default(monkeypatch, tmp_path, capsys):
    calls = []
    def run(*args):
        calls.append(args)
        return {'business_loop_closed': False, 'loop_closed': False}
    monkeypatch.setattr(lp, 'run', run)
    lp.main(['--entity', 'gamme:fixture', '--raw-root', str(tmp_path)])
    assert calls[0][2] == tmp_path
    assert calls[0][5] is None


def test_promotion_real_cli_dry_run_does_not_write(tmp_path):
    wiki, raw = tmp_path / 'wiki-repo', tmp_path / 'raw-repo'
    (wiki / 'proposals').mkdir(parents=True)
    raw.mkdir()
    proposal = wiki / 'proposals/fixture.md'
    proposal.write_text('---\nentity_type: gamme\nslug: fixture\nreview_status: approved\n---\nFixture.\n')
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = lp.stage_promotion('gamme:fixture', wiki, None, raw_root=raw)
    assert result['promotion_status'] == 'SKIP'
    assert result['state'] == lp.FAIL
    assert result['threshold'] == 0.85
    assert before == {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert not (wiki / 'wiki').exists()


def test_run_forwards_raw_checkout_to_promotion(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(lp, '_score_at_ref', lambda *args: {'tier': None, 'total': None})
    monkeypatch.setattr(lp, 'stage_citation', lambda *args: {'state': lp.UNKNOWN, 'verdict': 'unavailable'})
    monkeypatch.setattr(lp, 'stage_export', lambda *args: {'state': lp.UNKNOWN})
    def promotion(entity_id, wiki_root, threshold, raw_root=None):
        calls.append((entity_id, wiki_root, threshold, raw_root))
        return {'state': lp.UNKNOWN}
    monkeypatch.setattr(lp, 'stage_promotion', promotion)
    lp.run('gamme:fixture', tmp_path, tmp_path / 'raw', tmp_path / 'app', 'HEAD', None)
    assert calls == [('gamme:fixture', tmp_path, None, tmp_path / 'raw')]


def test_promotion_adapter_preserves_score_evidence_without_reinterpretation(tmp_path, monkeypatch):
    import json
    evaluation = {'confidence_score': .46, 'gate_engine': 'legacy',
                  'score_details': {'score': .46},
                  'shadow_score': {'shadow_total': 91, 'manifest_status': 'stale'}}
    report = {'report': [{'promotion_status': 'BLOCKED', 'eligible': False,
                         'tier': 'B', 'blocking_reasons': [], 'evaluation': evaluation}]}
    monkeypatch.setattr(lp, '_run', lambda cmd: (0, json.dumps(report), ''))
    result = lp.stage_promotion('gamme:fixture', tmp_path, None)
    assert result['state'] == lp.FAIL
    assert result['evaluation'] == evaluation
