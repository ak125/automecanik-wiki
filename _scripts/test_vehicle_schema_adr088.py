"""Tests ADR-088 — enrichissement ADDITIF de vehicle.schema.json (engineBlock factuel + related_gammes).

Garde-fous :
  - rétro-compat : les fiches v1.1 (sans champs ADR-088) valident toujours ;
  - les nouveaux champs sont OPTIONNELS mais correctement contraints quand présents.
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).resolve().parents[1] / "_meta" / "schema" / "entity-data" / "vehicle.schema.json"


def _schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def _v() -> Draft202012Validator:
    return Draft202012Validator(_schema())


def _block(**extra) -> dict:
    b = {"axis_key_type": "engine_family", "content_md": "x" * 50, "source_ids": ["oem:vw"], "truth_level": "sourced"}
    b.update(extra)
    return b


def test_schema_itself_is_valid():
    Draft202012Validator.check_schema(_schema())


def test_version_bumped_to_v120():
    assert "v1.2.0" in _schema()["title"]


def test_retrocompat_minimal_make_model():
    assert not list(_v().iter_errors({"make": "vw", "model": "golf-5"}))


def test_retrocompat_v11_engineblock_without_adr088_fields():
    inst = {"make": "vw", "model": "golf-5", "known_issues_by_engine": {"engine_family:bkc": _block()}}
    assert not list(_v().iter_errors(inst))


def test_adr088_enriched_block_validates():
    inst = {
        "make": "vw", "model": "golf-5",
        "related_gammes": ["turbo", "vanne-egr"], "commerce_intent": ["remplacement_piece"],
        "known_issues_by_engine": {"engine_family:bkc": _block(
            claim="Le BKC est réputé fiable au-delà de 400 000 km",
            applies_to={"engine_codes": ["BKC"], "years": [2004, 2007]},
            excluded_from={"engine_codes": ["BXE"], "reason": "coussinets de bielle fragiles"},
            evidence=[{"source_ref": "oem_vw", "strength": "secondary", "confidence": "medium", "status": "captured"}],
            projectability="projectable",
        )},
    }
    assert not list(_v().iter_errors(inst))


def test_excluded_from_requires_reason():
    inst = {"make": "vw", "model": "golf-5",
            "known_issues_by_engine": {"engine_family:bkc": _block(excluded_from={"engine_codes": ["BXE"]})}}
    assert list(_v().iter_errors(inst))  # reason manquant → invalide


def test_evidence_strength_enum_enforced():
    inst = {"make": "vw", "model": "golf-5",
            "known_issues_by_engine": {"engine_family:bkc": _block(evidence=[{"source_ref": "x", "strength": "super_strong"}])}}
    assert list(_v().iter_errors(inst))


def test_projectability_enum_enforced():
    inst = {"make": "vw", "model": "golf-5",
            "known_issues_by_engine": {"engine_family:bkc": _block(projectability="maybe")}}
    assert list(_v().iter_errors(inst))


def test_related_gammes_slug_pattern_enforced():
    inst = {"make": "vw", "model": "golf-5", "related_gammes": ["Turbo Invalid!"]}
    assert list(_v().iter_errors(inst))
