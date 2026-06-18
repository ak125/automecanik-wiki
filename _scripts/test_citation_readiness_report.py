"""Tests citation-readiness-report v2.0 — FORME citable, substance déléguée à shadow_score.

Vérifie : blocs v1.1.0/v1.2.0 → claims de forme citable, substance DÉLÉGUÉE (pas de
READY sans shadow_score → no parallel scorer), clés moteur non-canoniques → BLOCKED
sans crash, déterminisme, contrat exit (0 report-only / 1 --strict).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS.parent

_spec = importlib.util.spec_from_file_location(
    "citation_readiness_report", SCRIPTS / "citation-readiness-report.py"
)
crr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crr)


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


VEHICLE_V11 = """---
schema_version: 1.0.0
id: vehicle:test-v11
entity_type: vehicle
slug: test-v11
review_status: draft
source_refs:
  - kind: raw
    id: r1
entity_data:
  make: testmake
  model: testmodel
  known_issues_by_engine:
    "engine_family:abc":
      axis_key_type: engine_family
      truth_level: sourced
      source_ids:
        - "web:src-abc"
      content_md: "Moteur ABC — panne connue documentee, sourcee, de plus de quarante caracteres."
  maintenance_by_engine:
    "fuel:diesel":
      axis_key_type: fuel
      truth_level: sourced
      source_ids:
        - "web:src-diesel"
      content_md: "Entretien diesel commun — intervalle de vidange documente, plus de quarante caracteres."
---
# Test
## Presentation
Texte.
"""

VEHICLE_BADKEYS = """---
schema_version: 1.0.0
id: vehicle:test-bad
entity_type: vehicle
slug: test-bad
review_status: draft
source_refs:
  - kind: raw
    id: r1
entity_data:
  make: testmake
  model: testmodel
  known_issues_by_engine:
    ABC:
      - "panne non structuree (array de string, cle non canonique)"
---
# Test
## Presentation
Texte.
"""


def test_v11_blocks_become_citable_shape_claims(tmp_path):
    r = crr.analyze_fiche(_write(tmp_path, "test-v11.md", VEHICLE_V11), WIKI_ROOT)
    assert r["status"] in ("PARTIAL", "READY")
    assert r["summary"]["projectableBlocks"] >= 2
    assert len(r["claims"]) >= 2
    assert all(c["is_vehicle_aware"] for c in r["claims"])
    assert any(c["claim_type"] == "maintenance" for c in r["claims"])
    assert not r["schema_findings"]  # v1.1.0/v1.2.0 conforme


def test_substance_deferred_when_shadow_absent(tmp_path, monkeypatch):
    # shadow_score absent → substance None → JAMAIS READY (plafond PARTIAL). Hermétique
    # (monkeypatch) : robuste que shadow_score.py soit présent ou non dans le repo.
    monkeypatch.setattr(crr, "_SHADOW", None)
    r = crr.analyze_fiche(_write(tmp_path, "test-v11.md", VEHICLE_V11), WIKI_ROOT)
    assert r["substance_tier"] is None
    assert r["status"] == "PARTIAL"
    assert r["summary"]["readyClaims"] == 0


def test_composes_substance_tier_reaches_ready(tmp_path, monkeypatch):
    # Prouve le câblage : substance déléguée à shadow_score (tier A) + forme citable → claim READY.
    class _FakeShadow:
        @staticmethod
        def score(fm, body, ctx):
            return type("R", (), {"tier": "A"})()
    monkeypatch.setattr(crr, "_SHADOW", _FakeShadow)
    r = crr.analyze_fiche(_write(tmp_path, "test-v11.md", VEHICLE_V11), WIKI_ROOT)
    assert r["substance_tier"] == "A"
    assert any(c["verdict"] == "READY" for c in r["claims"])  # compose tier A + forme OK → READY


def test_noncanonical_keys_zero_blocks_blocked(tmp_path):
    r = crr.analyze_fiche(_write(tmp_path, "test-bad.md", VEHICLE_BADKEYS), WIKI_ROOT)
    assert r["status"] == "BLOCKED"
    assert r["summary"].get("projectableBlocks", 0) == 0
    assert any("SCHEMA_NONCONFORMANT" in f for f in r["schema_findings"])


def test_deterministic(tmp_path):
    src = _write(tmp_path, "test-v11.md", VEHICLE_V11)
    assert crr.analyze_fiche(src, WIKI_ROOT) == crr.analyze_fiche(src, WIKI_ROOT)


def test_report_only_exit_zero(tmp_path, monkeypatch):
    src = _write(tmp_path, "test-bad.md", VEHICLE_BADKEYS)
    monkeypatch.setattr(sys, "argv", ["prog", str(src), "--wiki-root", str(WIKI_ROOT)])
    assert crr.main() == 0


def test_strict_exit_one_on_blocking(tmp_path, monkeypatch):
    src = _write(tmp_path, "test-bad.md", VEHICLE_BADKEYS)
    monkeypatch.setattr(sys, "argv", ["prog", str(src), "--wiki-root", str(WIKI_ROOT), "--strict"])
    assert crr.main() == 1
