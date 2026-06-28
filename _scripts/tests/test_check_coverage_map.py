"""Tests for _scripts/check-coverage-map.py (validateur coverage-map, ADR-089).

Construit une mini-arbo wiki en tmp_path et exerce les 4 vérifications :
PASS (coverage valide), WARN (coverage absente mais H2 présents),
FAIL FK (source_slug hors source-catalog), FAIL anchor (section ∉ H2 de la fiche).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parent

spec = importlib.util.spec_from_file_location("check_coverage_map", SCRIPTS_DIR / "check-coverage-map.py")
ccm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccm)


def _make_wiki(tmp_path: Path, *, catalog_slugs, fiche_body, coverage=None) -> Path:
    (tmp_path / "_meta" / "schema").mkdir(parents=True)
    (tmp_path / "proposals" / "_coverage").mkdir(parents=True)
    # source-catalog
    cat = {"sources": [{"slug": s} for s in catalog_slugs]}
    (tmp_path / "_meta" / "source-catalog.yaml").write_text(yaml.safe_dump(cat), encoding="utf-8")
    # real schema (copied from repo so the test exercises the canonical contract)
    schema_src = REPO_ROOT / "_meta" / "schema" / "coverage-map.schema.json"
    (tmp_path / "_meta" / "schema" / "coverage-map.schema.json").write_text(
        schema_src.read_text(encoding="utf-8"), encoding="utf-8")
    # fiche
    (tmp_path / "proposals" / "demo.md").write_text(
        "---\nslug: demo\n---\n" + fiche_body, encoding="utf-8")
    if coverage is not None:
        (tmp_path / "proposals" / "_coverage" / "demo.coverage.yaml").write_text(
            yaml.safe_dump(coverage), encoding="utf-8")
    return tmp_path


def _check(root: Path):
    catalog = ccm._load_catalog_slugs(root)
    schema = ccm._load_schema(root)
    return ccm.check_fiche(root / "proposals" / "demo.md", root, catalog, schema)


def _valid_entry(section="## Fonctionnement", slug="oem_x"):
    return {
        "claim_id": "demo-claim-un", "section": section, "source_slug": slug,
        "evidence_type": "oem_workshop_excerpt", "confidence": "high",
        "source_policy": "1_high", "source_status": "captured",
    }


def test_pass_valid_coverage(tmp_path):
    root = _make_wiki(
        tmp_path, catalog_slugs=["oem_x"],
        fiche_body="## Fonctionnement\ntexte\n",
        coverage={"fiche": "demo", "schema_version": "1.0.0", "coverage_entries": [_valid_entry()]},
    )
    r = _check(root)
    assert r["status"] == "PASS", r["fails"] + r["warns"]


def test_warn_when_coverage_absent_but_h2_present(tmp_path):
    root = _make_wiki(tmp_path, catalog_slugs=["oem_x"], fiche_body="## Fonctionnement\ntexte\n", coverage=None)
    r = _check(root)
    assert r["status"] == "WARN"
    assert any("coverage_map_absente" in w for w in r["warns"])


def test_fail_fk_unknown_source_slug(tmp_path):
    root = _make_wiki(
        tmp_path, catalog_slugs=["oem_x"],
        fiche_body="## Fonctionnement\ntexte\n",
        coverage={"fiche": "demo", "schema_version": "1.0.0",
                  "coverage_entries": [_valid_entry(slug="slug_inconnu")]},
    )
    r = _check(root)
    assert r["status"] == "FAIL"
    assert any("source-catalog" in f for f in r["fails"])


def test_fail_section_anchor_not_in_fiche(tmp_path):
    root = _make_wiki(
        tmp_path, catalog_slugs=["oem_x"],
        fiche_body="## Fonctionnement\ntexte\n",
        coverage={"fiche": "demo", "schema_version": "1.0.0",
                  "coverage_entries": [_valid_entry(section="## Section Fantome")]},
    )
    r = _check(root)
    assert r["status"] == "FAIL"
    assert any("H2" in f for f in r["fails"])


def test_strict_exit_code_via_cli(tmp_path, monkeypatch, capsys):
    root = _make_wiki(
        tmp_path, catalog_slugs=["oem_x"],
        fiche_body="## Fonctionnement\ntexte\n",
        coverage={"fiche": "demo", "schema_version": "1.0.0",
                  "coverage_entries": [_valid_entry(slug="slug_inconnu")]},
    )
    monkeypatch.setattr("sys.argv", ["check-coverage-map.py", "--all", "--wiki-root", str(root), "--strict"])
    assert ccm.main() == 1  # FAIL → enforcement exit 1
    monkeypatch.setattr("sys.argv", ["check-coverage-map.py", "--all", "--wiki-root", str(root)])
    assert ccm.main() == 0  # report-only → exit 0 malgré le FAIL
