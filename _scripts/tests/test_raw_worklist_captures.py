"""Captures RAW liées par identité canonique (pg_id) — lecteur quality-gates + pilote + coverage map.

Verrouille le contrat de liaison : identité = `entity_ref.pg_id`, jamais le libellé `gamme` ;
une capture ne compte que si l'inventaire RAW la désigne une seule fois ET que ses octets ont
le sha256 inventorié ; toute ambiguïté est rapportée (fail-closed), jamais comptée en silence."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent.parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lp = _load("_t_loop_pilot", "raw_to_wiki_content_loop_pilot.py")
gcm = _load("_t_gen_coverage_map", "gen_coverage_map.py")

CAPTURE = "sources/auto-captures/filtre-x/fabricant-test-wl-a.md"


def _item(wid="wl-a", pg_id=7, gamme="filtre-x", status="CAPTURED_NEEDS_REVIEW",
          raw_path=CAPTURE, url="https://fabricant-test.example/guide.html"):
    item = {"id": wid, "subject_type": "gamme", "gamme": gamme,
            "source": {"authoritative_domain": "fabricant-test.example", "url": url,
                       "source_type": "manufacturer_maintenance"},
            "capture": {"status": status}}
    if pg_id is not None:
        item["entity_ref"] = {"pg_id": pg_id}
    if raw_path is not None:
        item["capture"]["raw_path"] = raw_path
    return item


def _raw(tmp_path: Path, items, files=None, inventory=None, worklist_text=None) -> Path:
    """Checkout RAW minimal : worklist + fichiers + inventaire (sha256 réel sauf surcharge)."""
    root = tmp_path / "raw"
    (root / "manifests").mkdir(parents=True)
    wl = root / "manifests" / "ingestion-worklist.yaml"
    wl.write_text(worklist_text if worklist_text is not None
                  else yaml.safe_dump({"schema_version": "2.0.0", "worklist": items}), encoding="utf-8")
    files = {CAPTURE: b"capture bytes\n"} if files is None else files
    rows = []
    for rel, data in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
        rows.append({"path": rel, "manifest_id": "src-auto-capture-" + "a" * 64, "layer": "sources",
                     "unstable_id": "false", "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
                     "size_bytes": str(len(data)), "added_at": "2026-09-13"})
    rows = rows if inventory is None else inventory
    with (root / "manifests" / "source-inventory.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "manifest_id", "layer", "unstable_id", "sha256",
                                          "size_bytes", "added_at"])
        w.writeheader()
        w.writerows(rows)
    return root


def _captures(root: Path, slug="filtre-x", pg_id=7) -> dict:
    return lp._quality_gates_for(root).raw_worklist_captures(slug, pg_id)


# ── quality-gates.raw_worklist_captures ────────────────────────────────────────────────────

def test_capture_bound_by_pg_id_resolves_with_inventory_id_and_bytes(tmp_path):
    r = _captures(_raw(tmp_path, [_item()]))
    assert r["readable"] and not r["failures"] and not r["mismatch"]
    [cap] = r["resolved"]
    assert cap["manifest_id"] == "src-auto-capture-" + "a" * 64
    assert cap["sha256"] == "sha256:" + hashlib.sha256(b"capture bytes\n").hexdigest()
    assert cap["source_type"] == "manufacturer_maintenance"


def test_pg_id_absent_binds_nothing(tmp_path):
    r = _captures(_raw(tmp_path, [_item()]), pg_id=None)
    assert r["detail"] == "pg_id_absent" and r["resolved"] == []


def test_bool_pg_id_is_not_an_identity(tmp_path):
    # True == 1 en Python : un booléen ne doit jamais lier une capture à pg_id=1.
    r = _captures(_raw(tmp_path, [_item(pg_id=True)]), pg_id=1)
    assert r["resolved"] == [] and r["unbound_same_label"] == ["wl-a"]


def test_label_alone_never_binds(tmp_path):
    r = _captures(_raw(tmp_path, [_item(pg_id=None)]))
    assert r["resolved"] == [] and r["unbound_same_label"] == ["wl-a"]


def test_same_pg_id_other_label_is_a_mismatch(tmp_path):
    r = _captures(_raw(tmp_path, [_item(gamme="autre-gamme")]))
    assert r["resolved"] == [] and r["mismatch"] == [{"worklist_id": "wl-a", "gamme": "autre-gamme"}]


def test_todo_item_is_reported_not_counted(tmp_path):
    r = _captures(_raw(tmp_path, [_item(status="TODO", raw_path=None)]))
    assert r["resolved"] == [] and [n["worklist_id"] for n in r["not_captured"]] == ["wl-a"]
    assert not r["failures"]


def test_captured_without_raw_path_fails(tmp_path):
    r = _captures(_raw(tmp_path, [_item(raw_path=None)]))
    assert r["failures"] == ["capture_raw_path_absent:wl-a"]


def test_capture_missing_from_inventory_is_unresolved(tmp_path):
    r = _captures(_raw(tmp_path, [_item()], inventory=[]))
    assert r["resolved"] == [] and r["failures"][0].startswith("raw_archive_unresolved:wl-a")


def test_duplicate_inventory_rows_are_unresolved(tmp_path):
    root = _raw(tmp_path, [_item()])
    rows = list(csv.DictReader((root / "manifests" / "source-inventory.csv").open(encoding="utf-8")))
    r = _captures(_raw(tmp_path / "dup", [_item()], inventory=rows * 2))
    assert r["resolved"] == [] and r["failures"][0].startswith("raw_archive_unresolved:wl-a")


def test_byte_drift_is_refused(tmp_path):
    root = _raw(tmp_path, [_item()])
    (root / CAPTURE).write_bytes(b"altered after inventory\n")
    r = _captures(root)
    assert r["resolved"] == [] and r["failures"][0].startswith("raw_archive_sha_drift:wl-a")


def test_path_outside_raw_is_refused(tmp_path):
    outside = "../outside.md"
    (tmp_path / "outside.md").write_bytes(b"x")
    r = _captures(_raw(tmp_path, [_item(raw_path=outside)], files={},
                       inventory=[{"path": outside, "manifest_id": "src-x", "sha256": "sha256:x"}]))
    assert r["resolved"] == [] and r["failures"][0].startswith("raw_archive_path_invalid:wl-a")


def test_malformed_worklist_is_unreadable_not_zero(tmp_path):
    r = _captures(_raw(tmp_path, [], worklist_text="schema_version: 2.0.0\n"))
    assert r["readable"] is False


def test_absent_worklist_is_a_deterministic_absence(tmp_path):
    root = _raw(tmp_path, [])
    (root / "manifests" / "ingestion-worklist.yaml").unlink()
    r = _captures(root)
    assert r["readable"] is True and r["detail"] == "worklist_absent" and r["resolved"] == []


# ── pilote : stage_raw / stage_wiki ────────────────────────────────────────────────────────

def test_stage_raw_passes_on_bound_capture_without_web_research(tmp_path):
    r = lp.stage_raw("filtre-x", _raw(tmp_path, [_item()]), 7)
    assert r["state"] == lp.PASS and r["auto_captures"]["count"] == 1
    assert r["legacy_web_research"]["md_files"] == 0


def test_stage_raw_fails_closed_on_binding_mismatch_even_with_valid_capture(tmp_path):
    items = [_item(), _item(wid="wl-b", gamme="autre-gamme", raw_path=None, status="TODO")]
    r = lp.stage_raw("filtre-x", _raw(tmp_path, items), 7)
    assert r["state"] == lp.FAIL and r["reason"].startswith("entity_binding_mismatch")


def test_stage_raw_fails_on_unresolved_capture(tmp_path):
    r = lp.stage_raw("filtre-x", _raw(tmp_path, [_item()], inventory=[]), 7)
    assert r["state"] == lp.FAIL and "raw_archive_unresolved" in r["reason"]


def test_stage_raw_unknown_when_worklist_unreadable(tmp_path):
    r = lp.stage_raw("filtre-x", _raw(tmp_path, [], worklist_text="worklist: {}\n"), 7)
    assert r["state"] == lp.UNKNOWN


def test_stage_raw_without_pg_id_does_not_bind_by_slug(tmp_path):
    r = lp.stage_raw("filtre-x", _raw(tmp_path, [_item()]), None)
    assert r["state"] == lp.FAIL and r["auto_captures"]["count"] == 0 and "pg_id absent" in r["reason"]


def test_document_receipts_pending_until_raw_reader_exists(tmp_path):
    root = _raw(tmp_path, [_item()])
    assert lp.stage_raw("filtre-x", root, 7)["document_receipts"]["state"] == lp.PENDING
    (root / "_scripts").mkdir()
    (root / "_scripts" / "document_contract.py").write_text("# reader\n", encoding="utf-8")
    assert lp.stage_raw("filtre-x", root, 7)["document_receipts"]["state"] == lp.NA


def _fiche(tmp_path: Path, entity_data: dict, entity_type: str = "gamme") -> Path:
    p = tmp_path / "wiki" / "proposals" / "filtre-x.md"
    p.parent.mkdir(parents=True)
    fm = {"entity_type": entity_type, "review_status": "draft", "entity_data": entity_data}
    p.write_text("---\n" + yaml.safe_dump(fm) + "---\n\n## Rôle\n\ntexte\n", encoding="utf-8")
    return p


def test_stage_wiki_exposes_integer_pg_id_only(tmp_path):
    _fiche(tmp_path, {"pg_id": 7})
    assert lp.stage_wiki("filtre-x", tmp_path / "wiki")["pg_id"] == 7


def test_stage_wiki_rejects_boolean_pg_id(tmp_path):
    _fiche(tmp_path, {"pg_id": True})
    assert lp.stage_wiki("filtre-x", tmp_path / "wiki")["pg_id"] is None


# ── gen_coverage_map : proposition de raw_ref, jamais d'activation ─────────────────────────

def _generate(tmp_path: Path, root: Path, monkeypatch, catalog: dict | None = None,
              entity_data: dict | None = None, entity_type: str = "gamme"):
    cat = tmp_path / "source-catalog.yaml"
    cat.write_text(yaml.safe_dump(catalog or {"sources": []}), encoding="utf-8")
    monkeypatch.setattr(gcm, "SOURCE_CATALOG", cat)
    md = _fiche(tmp_path, {"pg_id": 7} if entity_data is None else entity_data,
                entity_type).read_text(encoding="utf-8")
    return gcm.generate("filtre-x", md, root)


def test_coverage_map_proposes_raw_ref_without_counting_a_claim(tmp_path, monkeypatch):
    cov, report = _generate(tmp_path, _raw(tmp_path, [_item()]), monkeypatch)
    assert cov is None and report["valid_entries"] == 0 and report["candidate_claims"] == 0
    [row] = report["sources_to_validate"]
    assert row["domain"] == "fabricant-test.example" and row["claims"] == 0
    assert row["status"] == "pending_source_validation"
    [cap] = row["raw_captures"]
    assert cap["raw_source_type"] == "manufacturer_maintenance"
    assert cap["proposed_raw_ref"] == {
        "manifest_id": "src-auto-capture-" + "a" * 64,
        "expected_sha256": "sha256:" + hashlib.sha256(b"capture bytes\n").hexdigest()}


def test_coverage_map_proposes_nothing_on_binding_mismatch(tmp_path, monkeypatch):
    items = [_item(), _item(wid="wl-b", gamme="autre-gamme", raw_path=None, status="TODO")]
    _, report = _generate(tmp_path, _raw(tmp_path, items), monkeypatch)
    assert report["sources_to_validate"] == [] and report["raw_captures"]["mismatch"]


def test_coverage_map_skips_already_cataloged_domain(tmp_path, monkeypatch):
    catalog = {"sources": [{"slug": "fabricant-guide", "type": "manufacturer_maintenance",
                            "status": "to_capture", "title": "Guide fabricant-test.example"}]}
    _, report = _generate(tmp_path, _raw(tmp_path, [_item()]), monkeypatch, catalog=catalog)
    assert report["sources_to_validate"] == []
    assert report["raw_captures"]["resolved"][0]["catalog_domain_match"] == "fabricant-guide"


def test_coverage_map_without_pg_id_proposes_nothing(tmp_path, monkeypatch):
    _, report = _generate(tmp_path, _raw(tmp_path, [_item()]), monkeypatch, entity_data={})
    assert report["sources_to_validate"] == [] and report["raw_captures"]["detail"] == "pg_id_absent"


def test_inventoried_capture_absent_from_disk_is_missing(tmp_path):
    root = _raw(tmp_path, [_item()])
    (root / CAPTURE).unlink()
    r = _captures(root)
    assert r["resolved"] == [] and r["failures"] == ["raw_archive_missing:wl-a"]


def test_inventory_row_without_manifest_id_is_unresolved_not_drift(tmp_path):
    rows = [{"path": CAPTURE, "manifest_id": "", "sha256": "sha256:" + "0" * 64}]
    r = _captures(_raw(tmp_path, [_item()], inventory=rows))
    assert r["resolved"] == [] and r["failures"] == [
        "raw_archive_unresolved:wl-a: inventory row without manifest_id"]


def test_gated_or_rejected_items_never_count(tmp_path):
    items = [_item(wid="wl-g", status="GATED"), _item(wid="wl-r", status="REJECTED")]
    r = _captures(_raw(tmp_path, items))
    assert r["resolved"] == [] and sorted(n["worklist_id"] for n in r["not_captured"]) == ["wl-g", "wl-r"]


def test_coverage_map_binds_pg_id_only_for_gamme_pages(tmp_path, monkeypatch):
    # pg_id est l'identité d'une GAMME : une fiche d'un autre type ne lie aucune capture.
    _, report = _generate(tmp_path, _raw(tmp_path, [_item()]), monkeypatch, entity_type="vehicle")
    assert report["sources_to_validate"] == [] and report["raw_captures"]["detail"] == "pg_id_absent"
