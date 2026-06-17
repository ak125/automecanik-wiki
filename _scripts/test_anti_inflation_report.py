"""Tests du rapport anti-inflation + conformance (Phases 0+1, report-only).

Garde-fous vérifiés :
  - report-only : exit 0 par défaut, exit 1 seulement avec --strict (opt-in).
  - les checks détectent les bons cas et restent silencieux sur les cas propres.
  - conformité schéma = validation AUTORITAIRE (jsonschema), pas regex.
  - isolement : aucun import de promote.py.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = SCRIPTS_DIR.parent / "_meta" / "schema"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load():
    spec = importlib.util.spec_from_file_location(
        "anti_inflation_report", SCRIPTS_DIR / "anti-inflation-report.py"
    )
    mod = importlib.util.module_from_spec(spec)
    # Enregistrer dans sys.modules AVANT exec (requis par @dataclass — cf. _common.load_legacy_gates_module).
    sys.modules["anti_inflation_report"] = mod
    spec.loader.exec_module(mod)
    return mod


air = _load()


# --- CONFIDENCE_MISSING -------------------------------------------------------
def test_confidence_missing_fires_on_undeclared():
    fm = {"source_refs": [{"kind": "raw", "path": "x"}]}
    findings = air.check_confidence_missing(fm)
    assert any(f.code == "CONFIDENCE_MISSING" and f.severity == "blocking_simulated" for f in findings)


def test_confidence_missing_silent_when_declared():
    fm = {"source_refs": [{"kind": "raw", "confidence": "low"}]}
    assert air.check_confidence_missing(fm) == []


# --- ENGINE_GENERIC (advisory, axe générique uniquement) ----------------------
def test_engine_generic_advisory_on_fuel_axis():
    fm = {"entity_type": "vehicle", "entity_data": {"maintenance_by_engine": {"fuel:diesel": {"x": 1}}}}
    findings = air.check_engine_generic(fm)
    assert findings and all(f.severity == "advisory" for f in findings)


def test_engine_generic_silent_on_engine_family_key():
    fm = {"entity_type": "vehicle", "entity_data": {"known_issues_by_engine": {"engine_family:bkc": {"x": 1}}}}
    assert air.check_engine_generic(fm) == []


def test_engine_check_skips_non_vehicle():
    fm = {"entity_type": "gamme", "entity_data": {"known_issues_by_engine": {"BKC": []}}}
    assert air.check_engine_generic(fm) == []


# --- SCHEMA_NONCONFORMANT (validation autoritaire jsonschema) -----------------
def test_schema_nonconformant_fires_on_bad_engine_block():
    # clé brute 'BKC' + valeur tableau de strings = viole vehicle.schema.json engineBlock
    fm = {
        "entity_type": "vehicle",
        "entity_data": {"make": "vw", "model": "golf-5", "known_issues_by_engine": {"BKC": ["claim"]}},
    }
    findings = air.check_schema_conformance(fm, SCHEMA_DIR)
    assert any(f.code == "SCHEMA_NONCONFORMANT" and f.severity == "blocking_simulated" for f in findings)


def test_schema_conformant_silent_on_minimal_vehicle():
    fm = {"entity_type": "vehicle", "entity_data": {"make": "vw", "model": "golf-5"}}
    assert air.check_schema_conformance(fm, SCHEMA_DIR) == []


# --- SOURCE_WEAK_ALONE / SOURCE_UNCATALOGED (réutilise §9.1) -------------------
def test_sources_weak_alone_and_uncataloged():
    legacy = air.load_legacy_gates_module()
    catalog = {"forum_x": {"type": "forum"}, "oem_y": {"type": "oem_manual"}}

    codes_weak = {f.code for f in air.check_sources(legacy, catalog, {"source_refs": [{"slug": "forum_x"}]})}
    assert "SOURCE_WEAK_ALONE" in codes_weak

    codes_strong = {f.code for f in air.check_sources(legacy, catalog, {"source_refs": [{"slug": "oem_y"}]})}
    assert "SOURCE_WEAK_ALONE" not in codes_strong

    codes_unc = {f.code for f in air.check_sources(legacy, catalog, {"source_refs": [{"kind": "raw", "path": "p"}]})}
    assert "SOURCE_UNCATALOGED" in codes_unc


# --- Contrat report-only ------------------------------------------------------
def test_main_report_only_exit_zero_then_strict_one(tmp_path):
    f = tmp_path / "x.md"
    f.write_text("---\nentity_type: vehicle\nsource_refs:\n  - kind: raw\n---\nbody\n", encoding="utf-8")
    assert air.main([str(f)]) == 0           # défaut = report-only
    assert air.main(["--strict", str(f)]) == 1  # opt-in strict (usage futur)


def test_malformed_fiche_never_crashes(tmp_path):
    """Contrat report-only : une fiche malformée (slug non-string) ne crashe jamais, exit 0."""
    f = tmp_path / "bad.md"
    f.write_text("---\nentity_type: vehicle\nsource_refs:\n  - slug: 12345\n---\nbody\n", encoding="utf-8")
    assert air.main([str(f)]) == 0


def test_isolation_no_promote_import():
    """Le module advisory ne doit pas importer promote.py (anti-câblage)."""
    src = (SCRIPTS_DIR / "anti-inflation-report.py").read_text(encoding="utf-8")
    assert "import promote" not in src
    assert "from promote" not in src
