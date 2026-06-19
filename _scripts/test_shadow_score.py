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


def test_dim_A_reads_canonical_coverage_entries_key():
    # ADR-040 : la coverage-map réelle utilise 'coverage_entries' (pas 'coverage'/'claims').
    cov = {"coverage_entries": [{"confidence": "high"}, {"confidence": "medium"}]}
    pts, note = ss._dim_A({}, cov)
    assert note is None
    assert pts == ss.WEIGHTS["A"] * ((1.0 + 0.6) / 2)  # 30 * 0.8 = 24.0


def test_dim_A_backward_compat_legacy_coverage_key():
    # compat ascendante : l'ancienne clé 'coverage' reste lue.
    pts, _ = ss._dim_A({}, {"coverage": [{"confidence": "high"}]})
    assert pts == ss.WEIGHTS["A"] * 1.0


def test_load_coverage_map_safe_degradation(tmp_path):
    # slug inconnu / None → None (jamais de crash) = dégradation sûre.
    assert ss._load_coverage_map("inexistant", tmp_path) is None
    assert ss._load_coverage_map(None, tmp_path) is None


def test_load_coverage_map_reads_real_file(tmp_path):
    cov_dir = tmp_path / "_coverage"
    cov_dir.mkdir()
    (cov_dir / "x.coverage.yaml").write_text(
        "coverage_entries:\n  - confidence: high\n  - confidence: low\n", encoding="utf-8")
    cmap = ss._load_coverage_map("x", tmp_path)
    assert cmap is not None and len(cmap["coverage_entries"]) == 2
    pts, note = ss._dim_A({}, cmap)  # bout-en-bout : loader → _dim_A
    assert note is None and pts == ss.WEIGHTS["A"] * ((1.0 + 0.3) / 2)


def test_dim_C_counts_sourced_editorial_blocks_for_gammes():
    # gamme châssis : richesse via blocs éditoriaux SOURCÉS (pas d'engine-block) — 6 sourcés = plein.
    ed = {"editorial": {f"s{i}": {"content_md": "x" * 60, "source_ids": ["web:x"], "truth_level": "sourced"}
                        for i in range(6)}}
    pts, note = ss._dim_C({"entity_data": ed})
    assert note is None and pts == ss.WEIGHTS["C"] * 1.0


def test_dim_C_editorial_requires_source_ids():
    # anti-padding : un bloc éditorial SANS source_ids ne compte pas.
    ed = {"editorial": {"a": {"content_md": "x" * 60, "truth_level": "sourced"}}}
    pts, _ = ss._dim_C({"entity_data": ed})
    assert pts == 0.0


def test_dim_C_engine_block_path_unchanged_for_vehicles():
    # rétro-compat : le chemin engine-block (véhicule / gamme moteur) reste inchangé.
    fm = {"entity_data": {"known_issues_by_engine": {"e": {"evidence": [{"x": 1}]}}}}
    pts, _ = ss._dim_C(fm)
    assert pts == ss.WEIGHTS["C"] * 1.0


def test_old_score_computed_in_shadow():
    # compute_old branché → old_score renseigné (ou None si indéterminable, jamais crash)
    called = {}
    def fake_old(fm, body, wiki_root):
        called["yes"] = True
        return 0.42
    r = ss.score({"entity_type": "gamme", "entity_data": {}}, "", {**_ctx(), "compute_old": fake_old})
    assert called.get("yes") and r.old_score == 0.42
