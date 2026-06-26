"""Loader guard (S1a→S1d) — the source_type → max_confidence policy has ONE machine SoT.

`_meta/source-catalog.yaml › source_type_max_confidence` is the machine source of truth
for the source_type → max_confidence policy (mirrored in prose at source-policy.md §9.1).
Cutover S1d DONE: _scripts/quality-gates.py now reads this map directly (single-read,
hardcoded dict removed). `SOURCE_TYPE_TO_MAX_CONFIDENCE` is the loaded value, so equality
with the catalog is by construction — this test now guards the loader (a broken/filtering
loader, or a missing/invalid catalog map, fails here instead of silently mis-enforcing).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parent
SOURCE_CATALOG = REPO_ROOT / "_meta" / "source-catalog.yaml"
VALID_CONFIDENCE = {"low", "medium", "high"}


def _load_quality_gates():
    # filename has a hyphen → load via importlib (same pattern as test_quality_gates.py)
    spec = importlib.util.spec_from_file_location("quality_gates", SCRIPTS_DIR / "quality-gates.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _catalog_map() -> dict:
    data = yaml.safe_load(SOURCE_CATALOG.read_text(encoding="utf-8"))
    return data.get("source_type_max_confidence")


def test_catalog_declares_source_type_max_confidence():
    cat = _catalog_map()
    assert isinstance(cat, dict) and cat, (
        "_meta/source-catalog.yaml must declare `source_type_max_confidence` (machine SoT, §9.1)"
    )
    assert set(cat.values()) <= VALID_CONFIDENCE, (
        f"confidence values must be a subset of {VALID_CONFIDENCE}, got {set(cat.values())}"
    )


def test_catalog_in_parity_with_quality_gates():
    cat = _catalog_map()
    gate = _load_quality_gates().SOURCE_TYPE_TO_MAX_CONFIDENCE
    assert cat == gate, (
        "DRIFT: _meta/source-catalog.yaml `source_type_max_confidence` (SoT-of-record) != "
        "_scripts/quality-gates.py SOURCE_TYPE_TO_MAX_CONFIDENCE. Keep them identical — edit "
        "the catalog (SoT) and mirror the gate dict (cutover to single-read = S1d)."
    )
