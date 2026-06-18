"""Tests shadow_score (ADR-088 Phase 3.3) — le FRAMEWORK (pas les formules v0 tunables).

Vérifie : profils entity-type-aware, renormalisation, dégradation sûre, cap de tier par plancher.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import shadow_score as ss  # noqa: E402


def _ctx(manifest=None, coverage_map=None):
    return {"manifest": manifest, "coverage_map": coverage_map, "path": "x.md"}


def _block(**extra):
    b = {"axis_key_type": "engine_family", "content_md": "x" * 50, "source_ids": ["oem:vw"],
         "truth_level": "sourced", "evidence": [{"source_ref": "oem", "strength": "primary"}]}
    b.update(extra)
    return b


def test_unknown_entity_type_not_scored():
    r = ss.score({"entity_type": "weird"}, "", _ctx())
    assert r.tier == "D"
    assert any("non scoré" in n for n in r.notes)


def test_profiles_entity_type_aware():
    assert "B" in ss.PROFILES["vehicle"]["floors"]          # véhicule : plancher granularité moteur
    assert "B" not in ss.PROFILES["gamme"]["dims"]           # gamme : pas de dim B
    assert "D" not in ss.PROFILES["diagnostic"]["dims"]      # diagnostic : pas de dim commerce


def test_renormalization_gamme_excludes_B():
    r = ss.score({"entity_type": "gamme", "entity_data": {}}, "## a\n## b\n", _ctx())
    assert set(r.applicable) == {"A", "C", "D", "E", "F"}
    assert "B" not in r.dims


def test_degradation_no_coverage_map_A_zero_no_crash():
    r = ss.score({"entity_type": "vehicle", "entity_data": {}}, "", _ctx())
    assert r.dims.get("A") == 0.0
    assert any("no_coverage_map" in n for n in r.notes)


def test_degradation_manifest_not_ready_skips_realitycheck():
    r = ss.score({"entity_type": "vehicle", "entity_data": {}}, "", _ctx(manifest=None))
    assert any("SKIPP" in n for n in r.notes)


def test_floor_caps_tier_to_B_when_commerce_floor_fails():
    cov = {"coverage": [{"confidence": "high"}]}  # A=30
    fm = {"entity_type": "vehicle", "review_status": "approved", "lineage_id": "x", "exportable": {},
          "entity_data": {"known_issues_by_engine": {"engine_family:bkc": _block(applies_to={"engine_codes": ["BKC"]})}}}
    # PAS de related_gammes → D=0 → plancher D<10 échoue ; total=85 (≥80) → tier A capé à B
    body = "## a\n## b\n## c\n## d\n## e\n"
    r = ss.score(fm, body, _ctx(coverage_map=cov))
    assert r.total >= 80
    assert "D<10" in r.floors_failed
    assert r.tier == "B"
    assert any("FLOOR_NOT_MET" in b for b in r.blocked)


def test_old_score_computed_in_shadow():
    # compute_old branché → old_score renseigné (ou None si indéterminable, jamais crash)
    called = {}
    def fake_old(fm, body, wiki_root):
        called["yes"] = True
        return 0.42
    r = ss.score({"entity_type": "gamme", "entity_data": {}}, "", {**_ctx(), "compute_old": fake_old})
    assert called.get("yes") and r.old_score == 0.42
