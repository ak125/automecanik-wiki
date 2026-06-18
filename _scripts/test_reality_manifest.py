"""Tests reality_manifest (0-DB reader, ADR-088 Phase 3.2).

Vérifie la **dégradation sûre** : seul un manifest 'ready' (frais + non vide) autorise un reality-check ;
absent / non généré / vide / périmé → pas 'ready' → le scorer doit SKIPPER (jamais de faux rejet).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import reality_manifest as rm  # noqa: E402 — module sans tiret, importable

NOW = datetime(2026, 6, 18, tzinfo=timezone.utc)


def _ready(generated_at: str | None = None) -> dict:
    return {
        "generated": True,
        "generated_at": generated_at or NOW.isoformat(),
        "engine_codes": ["BKC", "BXE"],
        "gamme_slugs": ["turbo", "vanne-egr"],
    }


def test_status_absent():
    assert rm.status(None) == "absent"
    assert not rm.is_ready(None)


def test_status_ungenerated():
    assert rm.status({"generated": False}) == "ungenerated"


def test_status_empty():
    assert rm.status({"generated": True, "engine_codes": [], "gamme_slugs": []}) == "empty"


def test_status_stale():
    old = (NOW - timedelta(days=40)).isoformat()
    assert rm.status(_ready(old), now=NOW) == "stale"


def test_status_ready():
    assert rm.status(_ready(), now=NOW) == "ready"
    assert rm.is_ready(_ready(), now=NOW)


def test_load_absent_returns_none(tmp_path):
    assert rm.load_manifest(tmp_path / "nope.json") is None


def test_load_roundtrip(tmp_path):
    p = tmp_path / "reality-manifest.json"
    p.write_text(json.dumps(_ready()), encoding="utf-8")
    assert rm.load_manifest(p)["engine_codes"] == ["BKC", "BXE"]


def test_membership_and_unknown():
    m = _ready()
    assert rm.engine_code_set(m) == {"BKC", "BXE"}
    assert rm.unknown_engine_codes(m, ["BKC", "FAKE"]) == ["FAKE"]
    assert rm.unknown_gamme_slugs(m, ["turbo", "nope"]) == ["nope"]


def test_degradation_no_false_reject_when_not_ready():
    # manifest absent : is_ready False → le scorer NE DOIT PAS rejeter (skip reality-check)
    assert not rm.is_ready(None)
    assert rm.status(_ready((NOW - timedelta(days=40)).isoformat()), now=NOW) != "ready"
