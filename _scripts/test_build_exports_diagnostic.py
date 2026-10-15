"""Tests build_exports_diagnostic — vue dérivée des diagnostic_relations (ADR-033).

Chaque test construit un dépôt git jetable (fiches + catalogue + schéma) et lance le
builder comme la CI : `main` via CliRunner. Exécution :
    cd _scripts && python3 -m pytest test_build_exports_diagnostic.py -v
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import click
import jsonschema
import pytest
import yaml
from click.testing import CliRunner
from referencing import Registry, Resource

import build_exports_diagnostic as builder

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "_meta" / "schema"
SCHEMA_PATH = SCHEMA_DIR / "exports-diagnostic.schema.json"
SCRIPT_PATH = Path(__file__).resolve().parent / "build_exports_diagnostic.py"

CATALOG = [
    {"slug": "oem_doc", "title": "OEM", "type": "oem_manual", "license": "x", "status": "active",
     "raw_ref": {"repo": "automecanik-raw", "manifest_id": "rec-oem-doc",
                 "expected_sha256": "sha256:" + "a" * 64}},
    {"slug": "brochure_doc", "title": "Brochure", "type": "brochure", "license": "x",
     "status": "to_capture",
     "raw_ref": {"repo": "automecanik-raw", "manifest_id": "brochure_doc", "expected_sha256": None}},
    {"slug": "blog_doc", "title": "Blog", "type": "blog_pro", "license": "x", "status": "to_capture"},
]


def _relation(sources: list[str], part_role: str = "filtre colmaté réduisant le débit d'air") -> dict:
    return {
        "symptom_slug": "perte_puissance_filtration",
        "system_slug": "filtration",
        "relation_to_part": "possible_cause",
        "part_role": part_role,
        "evidence": {"confidence": "medium", "source_policy": "2_medium_concordant",
                     "reviewed": False, "diagnostic_safe": False},
        "sources": sources,
    }


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _write_fiche(root: Path, slug: str, *, review_status: str = "approved",
                 relations: list[dict] | None = None, fm_slug: str | None = None) -> None:
    fm = {"schema_version": "2.0.0", "id": f"gamme:{slug}", "entity_type": "gamme",
          "slug": fm_slug or slug, "title": slug, "lang": "fr", "review_status": review_status}
    if relations is not None:
        fm["diagnostic_relations"] = relations
    path = root / "wiki" / "gamme" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
                    + "---\n\n# " + slug + "\n", encoding="utf-8")


def _write_catalog(root: Path, entries: list[dict]) -> None:
    path = root / "_meta" / "source-catalog.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"sources": entries}, sort_keys=False), encoding="utf-8")


@pytest.fixture
def wiki(tmp_path: Path) -> Path:
    root = tmp_path / "wiki-repo"
    (root / "_meta" / "schema").mkdir(parents=True)
    shutil.copy(SCHEMA_PATH, root / "_meta" / "schema" / SCHEMA_PATH.name)
    _write_catalog(root, CATALOG)
    _write_fiche(root, "filtre-a-air", relations=[_relation(["oem_doc", "brochure_doc"])])
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    return root


def _run(root: Path, *extra: str):
    return CliRunner().invoke(builder.main, ["--wiki-root", str(root), *extra])


def _commit_all(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", message)
    return _git(root, "rev-parse", "HEAD")


def _read(root: Path, rel: str) -> dict:
    return json.loads((root / "exports" / "diagnostic" / rel).read_text(encoding="utf-8"))


def _validator() -> jsonschema.Draft202012Validator:
    registry = Registry()
    for name in ("frontmatter.schema.json", "source-catalog-entry.schema.json"):
        schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema, registry=registry)


# --- éligibilité et sortie --------------------------------------------------------


def test_only_approved_fiches_with_relations_are_exported(wiki: Path):
    _write_fiche(wiki, "filtre-a-huile", review_status="draft",
                 relations=[_relation(["oem_doc"])])
    _write_fiche(wiki, "bougie", relations=[])
    _write_fiche(wiki, "courroie")
    _commit_all(wiki, "more fiches")

    result = _run(wiki)

    assert result.exit_code == 0, result.output
    gamme_files = sorted(p.name for p in (wiki / "exports" / "diagnostic" / "gamme").glob("*.json"))
    assert gamme_files == ["filtre-a-air.json"]
    assert [f["path"] for f in _read(wiki, "_index.json")["files"]] == ["gamme/filtre-a-air.json"]


def test_outputs_validate_against_schema(wiki: Path):
    assert _run(wiki).exit_code == 0
    validator = _validator()
    validator.validate(_read(wiki, "gamme/filtre-a-air.json"))
    validator.validate(_read(wiki, "_index.json"))


def test_rerun_produces_identical_bytes(wiki: Path):
    assert _run(wiki).exit_code == 0
    out = wiki / "exports" / "diagnostic"
    first = {p: p.read_bytes() for p in out.rglob("*.json")}
    assert _run(wiki).exit_code == 0
    assert {p: p.read_bytes() for p in out.rglob("*.json")} == first


def test_written_files_end_with_newline(wiki: Path):
    assert _run(wiki).exit_code == 0
    for path in (wiki / "exports" / "diagnostic").rglob("*.json"):
        assert path.read_bytes().endswith(b"}\n"), path


def test_index_hashes_the_written_bytes(wiki: Path):
    assert _run(wiki).exit_code == 0
    entry = _read(wiki, "_index.json")["files"][0]
    data = (wiki / "exports" / "diagnostic" / entry["path"]).read_bytes()
    assert entry["sha256"] == builder._sha256_prefixed(data)
    assert entry["relation_count"] == 1


def test_index_carries_no_fiche_text(wiki: Path):
    """L'index ne publie que constantes, chemins, empreintes et compteurs, jamais un texte de
    fiche : la Safety Auto-Gate lit le document par gamme, pas l'index."""
    _write_fiche(wiki, "colonne", relations=[
        _relation(["oem_doc", "brochure_doc"], part_role="Jeu de 2 mm au braquage.")])
    _commit_all(wiki, "colonne")
    assert _run(wiki).exit_code == 0

    def strings(node):
        if isinstance(node, dict):
            for key, value in node.items():
                yield key
                yield from strings(value)
        elif isinstance(node, list):
            for item in node:
                yield from strings(item)
        elif isinstance(node, str):
            yield node

    shape = re.compile(r"[a-z_]+|sha256|\d+\.\d+\.\d+|[0-9a-f]{40}|sha256:[0-9a-f]{64}|gamme/[a-z0-9-]+\.json")
    assert [s for s in strings(_read(wiki, "_index.json")) if not shape.fullmatch(s)] == []
    assert _read(wiki, "gamme/colonne.json")["relations"][0]["part_role"] == "Jeu de 2 mm au braquage."


def test_json_format_success_report(wiki: Path):
    result = _run(wiki, "--format", "json")

    assert result.exit_code == 0, result.output
    written = len(list((wiki / "exports" / "diagnostic" / "gamme").glob("*.json")))
    assert written == 1
    report = json.loads(result.stdout[result.stdout.index("{"): result.stdout.rindex("}") + 1])
    assert report == {"status": "OK", "written": written, "observations": []}


def test_zero_eligible_fiche_gives_empty_valid_index(wiki: Path):
    _write_fiche(wiki, "filtre-a-air", review_status="draft", relations=[_relation(["oem_doc"])])
    _commit_all(wiki, "unapprove")

    result = _run(wiki)

    assert result.exit_code == 0, result.output
    index = _read(wiki, "_index.json")
    assert index["files"] == []
    _validator().validate(index)


# --- provenance git ---------------------------------------------------------------


def test_commits_are_the_last_ones_touching_fiche_and_catalog(wiki: Path):
    fiche_commit = _git(wiki, "rev-parse", "HEAD")
    _write_catalog(wiki, CATALOG + [{"slug": "other_doc", "title": "o", "type": "forum",
                                     "license": "x", "status": "to_capture"}])
    catalog_commit = _commit_all(wiki, "catalog change")
    (wiki / "unrelated.txt").write_text("x", encoding="utf-8")
    _commit_all(wiki, "unrelated")

    assert _run(wiki).exit_code == 0
    export = _read(wiki, "gamme/filtre-a-air.json")
    assert export["source_wiki_commit"] == fiche_commit
    assert export["source_catalog_commit"] == catalog_commit
    assert _read(wiki, "_index.json")["source_catalog_commit"] == catalog_commit


def test_no_git_repository_fails(tmp_path: Path):
    root = tmp_path / "plain"
    (root / "_meta" / "schema").mkdir(parents=True)
    shutil.copy(SCHEMA_PATH, root / "_meta" / "schema" / SCHEMA_PATH.name)
    _write_catalog(root, CATALOG)
    _write_fiche(root, "filtre-a-air", relations=[_relation(["oem_doc"])])

    result = _run(root)

    assert result.exit_code == 1
    assert "no commit found" in result.output
    assert not (root / "exports").exists()


def test_shallow_clone_fails(wiki: Path, tmp_path: Path):
    (wiki / "unrelated.txt").write_text("x", encoding="utf-8")
    _commit_all(wiki, "second")
    clone = tmp_path / "shallow"
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{wiki}", str(clone)], check=True)

    result = _run(clone)

    assert result.exit_code == 1
    assert "SHALLOW" in result.output


def test_missing_export_schema_exits_2(wiki: Path):
    (wiki / "_meta" / "schema" / SCHEMA_PATH.name).unlink()
    result = _run(wiki)
    assert result.exit_code == 2
    assert "export schema not found" in result.output
    assert SCHEMA_PATH.name in result.output


# --- retrait gouverné ---------------------------------------------------------------


def test_export_without_eligible_fiche_is_preserved_and_fails(wiki: Path):
    assert _run(wiki).exit_code == 0
    _write_fiche(wiki, "filtre-a-air", review_status="draft", relations=[_relation(["oem_doc"])])
    _commit_all(wiki, "unapprove")
    export = wiki / "exports" / "diagnostic" / "gamme" / "filtre-a-air.json"
    before = export.read_bytes()

    result = _run(wiki, "--format", "json")

    assert result.exit_code == 1
    assert export.read_bytes() == before
    report = json.loads(result.stdout[: result.stdout.rindex("}") + 1])
    assert report["status"] == "UNRECONCILED"
    assert report["observations"] == [
        {"export_path": "exports/diagnostic/gamme/filtre-a-air.json", "withdrawal_authorized": False}
    ]


def test_governed_withdrawal_regenerates_index(wiki: Path):
    assert _run(wiki).exit_code == 0
    _write_fiche(wiki, "filtre-a-air", review_status="draft", relations=[_relation(["oem_doc"])])
    (wiki / "exports" / "diagnostic" / "gamme" / "filtre-a-air.json").unlink()
    _commit_all(wiki, "withdraw")

    result = _run(wiki)

    assert result.exit_code == 0, result.output
    assert _read(wiki, "_index.json")["files"] == []


# --- sources -----------------------------------------------------------------------


def test_part_suffix_is_normalised_to_catalog_slug(wiki: Path):
    _write_fiche(wiki, "filtre-a-air", relations=[_relation(["oem_doc_p3"])])
    _commit_all(wiki, "part suffix")

    assert _run(wiki).exit_code == 0
    source = _read(wiki, "gamme/filtre-a-air.json")["relations"][0]["sources"][0]
    assert source["slug"] == "oem_doc_p3"
    assert source["catalog_slug"] == "oem_doc"


def test_unknown_source_slug_fails(wiki: Path):
    _write_fiche(wiki, "filtre-a-air", relations=[_relation(["ghost_doc_p2"])])
    _commit_all(wiki, "unknown source")

    result = _run(wiki)

    assert result.exit_code == 1
    assert "source slug unknown to the catalog" in result.output


def test_catalog_entry_without_status_fails(wiki: Path):
    entries = [dict(e) for e in CATALOG]
    del entries[1]["status"]
    _write_catalog(wiki, entries)
    _commit_all(wiki, "implicit status")

    result = _run(wiki)

    assert result.exit_code == 1
    assert "without explicit status: brochure_doc" in result.output


def test_duplicate_catalog_slug_fails(wiki: Path):
    _write_catalog(wiki, CATALOG + [dict(CATALOG[0])])
    _commit_all(wiki, "duplicate")

    result = _run(wiki)

    assert result.exit_code == 1
    assert "duplicate source catalog slug: oem_doc" in result.output


def test_status_type_and_raw_ref_are_copied_from_catalog(wiki: Path):
    _write_fiche(wiki, "filtre-a-air", relations=[_relation(["oem_doc", "brochure_doc", "blog_doc"])])
    _commit_all(wiki, "three sources")

    assert _run(wiki).exit_code == 0
    sources = _read(wiki, "gamme/filtre-a-air.json")["relations"][0]["sources"]
    assert [(s["type"], s["status"]) for s in sources] == [
        ("oem_manual", "active"), ("brochure", "to_capture"), ("blog_pro", "to_capture")]
    assert sources[0]["raw_ref"] == CATALOG[0]["raw_ref"]
    assert sources[1]["raw_ref"] == CATALOG[1]["raw_ref"]
    assert sources[2]["raw_ref"] is None


def test_raw_proven_is_the_g1_predicate():
    from gen_coverage_map import is_page_proven

    catalog = {e["slug"]: e for e in CATALOG}
    catalog["active_no_ref"] = {"slug": "active_no_ref", "type": "forum", "status": "active"}
    for slug, entry in catalog.items():
        assert builder._export_source(slug, catalog)["raw_proven"] is is_page_proven(entry)
    assert builder._export_source("oem_doc", catalog)["raw_proven"] is True
    assert builder._export_source("brochure_doc", catalog)["raw_proven"] is False
    assert builder._export_source("active_no_ref", catalog)["raw_proven"] is False


def test_confidence_score_is_the_canonical_formula(wiki: Path):
    assert _run(wiki).exit_code == 0
    relation = _read(wiki, "gamme/filtre-a-air.json")["relations"][0]
    catalog = {e["slug"]: e for e in CATALOG}
    assert relation["confidence_score_computed"] == builder.compute_score(
        ["oem_doc", "brochure_doc"], catalog)
    assert relation["confidence_score_computed"] == 1.0
    assert "confidence_score_computed" not in relation["evidence"]


# --- identité des relations ----------------------------------------------------------


def test_relation_sha256_is_stable_and_content_sensitive():
    catalog = {e["slug"]: e for e in CATALOG}
    item = _relation(["oem_doc"])
    first = builder._export_relation(0, item, catalog)["relation_sha256"]
    assert builder._export_relation(0, json.loads(json.dumps(item)), catalog)["relation_sha256"] == first
    changed = builder._export_relation(0, _relation(["oem_doc"], part_role="autre rôle de la pièce"),
                                       catalog)["relation_sha256"]
    assert changed != first
    assert first.startswith("sha256:") and len(first) == len("sha256:") + 64


def _malformed_relation_cases():
    no_evidence = _relation(["oem_doc"])
    del no_evidence["evidence"]
    no_sources = _relation(["oem_doc"])
    del no_sources["sources"]
    no_role = _relation(["oem_doc"])
    del no_role["part_role"]
    return [
        ([no_evidence], "evidence"),
        ([no_sources], "sources"),
        ([no_role], "part_role"),
        (["pas un objet"], "relation"),
        ({"symptom_slug": "x"}, "list"),
    ]


@pytest.mark.parametrize("relations,expected_word", _malformed_relation_cases())
def test_malformed_relation_fails_naming_fiche_and_key(wiki: Path, relations, expected_word: str):
    _write_fiche(wiki, "filtre-a-huile", relations=relations)
    _commit_all(wiki, "malformed relation")

    result = _run(wiki)

    assert result.exit_code == 1
    assert "filtre-a-huile" in result.output
    assert expected_word in result.output
    assert "Traceback" not in result.output
    assert not (wiki / "exports").exists()


def test_frontmatter_slug_must_match_file_name(wiki: Path):
    _write_fiche(wiki, "filtre-a-air", relations=[_relation(["oem_doc"])], fm_slug="filtre-air")
    _commit_all(wiki, "slug mismatch")

    result = _run(wiki)

    assert result.exit_code == 1
    assert "differs from file name" in result.output


def test_writes_are_refused_outside_exports_diagnostic(wiki: Path):
    with pytest.raises(click.ClickException, match="outside"):
        builder._write_strict(wiki / "exports" / "seo" / "x.json", b"{}\n", wiki)


# --- schéma --------------------------------------------------------------------------


def _valid_export(wiki: Path) -> dict:
    assert _run(wiki).exit_code == 0
    return _read(wiki, "gamme/filtre-a-air.json")


def test_schema_rejects_raw_proven_source_without_expected_sha256(wiki: Path):
    export = _valid_export(wiki)
    source = export["relations"][0]["sources"][1]  # brochure_doc : to_capture, sha null
    source["raw_proven"] = True
    with pytest.raises(jsonschema.ValidationError):
        _validator().validate(export)
    source["status"] = "active"
    with pytest.raises(jsonschema.ValidationError):
        _validator().validate(export)
    source["raw_ref"]["expected_sha256"] = "sha256:" + "b" * 64
    _validator().validate(export)


def test_schema_rejects_score_inside_evidence(wiki: Path):
    export = _valid_export(wiki)
    export["relations"][0]["evidence"]["confidence_score_computed"] = 1.0
    with pytest.raises(jsonschema.ValidationError):
        _validator().validate(export)


def test_schema_rejects_unprefixed_hash(wiki: Path):
    export = _valid_export(wiki)
    export["content_hash"] = export["content_hash"].removeprefix("sha256:")
    with pytest.raises(jsonschema.ValidationError):
        _validator().validate(export)


# --- garde-fous statiques ------------------------------------------------------------


def _source_text() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


@pytest.mark.parametrize("module", ["anthropic", "openai", "groq", "cohere", "mistralai",
                                    "google.generativeai"])
def test_no_llm_import(module: str):
    assert f"import {module}" not in _source_text()
    assert f"from {module}" not in _source_text()


@pytest.mark.parametrize("module", ["psycopg", "asyncpg", "supabase", "sqlalchemy", "django"])
def test_no_db_import(module: str):
    assert f"import {module}" not in _source_text()
    assert f"from {module}" not in _source_text()


@pytest.mark.parametrize("token", ["datetime.now", "datetime.utcnow", "time.time(", "date.today",
                                   '"HEAD"', "rev-parse"])
def test_no_wall_clock_nor_head(token: str):
    assert token not in _source_text()


# ADR-112/113 fields must survive transport without changing their meaning.
@pytest.mark.parametrize("field,value", [
    ("cause_slug", "filtre_air_colmate"),
    ("vehicle_scope", {"fuel": "diesel"}),
    ("citations", [{"source": "oem_doc", "start": 0, "end": 12,
                     "quote_sha256": "sha256:" + "c" * 64}]),
    ("strength", "parfois"),
])
def test_extended_claims_survive_export(wiki: Path, field, value):
    item = _relation(["oem_doc"])
    target = item["evidence"] if field == "strength" else item
    target[field] = value
    _write_fiche(wiki, "filtre-a-air", relations=[item])
    _commit_all(wiki, "extended claim")
    assert _run(wiki).exit_code == 0
    exported = _read(wiki, "gamme/filtre-a-air.json")
    relation = exported["relations"][0]
    actual = relation["evidence"] if field == "strength" else relation
    assert actual.get(field) == value
    _validator().validate(exported)


def test_legacy_claims_do_not_acquire_invented_fields(wiki: Path):
    exported = _valid_export(wiki)["relations"][0]
    assert not {"cause_slug", "vehicle_scope", "citations"}.intersection(exported)
    assert "strength" not in exported["evidence"]


def test_export_major_protects_readers_that_silently_strip_claims(wiki: Path):
    assert _run(wiki).exit_code == 0
    assert _read(wiki, "_index.json")["schema_version"] == "2.0.0"
    assert _read(wiki, "gamme/filtre-a-air.json")["schema_version"] == "2.0.0"


# Commit provenance must describe the exact input bytes, not merely its path.
@pytest.mark.parametrize("rel", ["wiki/gamme/filtre-a-air.md", builder.CATALOG_REL])
@pytest.mark.parametrize("staged", [False, True])
def test_uncommitted_input_is_rejected_without_overwriting_exports(wiki: Path, rel: str, staged: bool):
    assert _run(wiki).exit_code == 0
    before = {p.relative_to(wiki): p.read_bytes()
              for p in (wiki / "exports/diagnostic").rglob("*.json")}
    source = wiki / rel
    original = source.read_bytes()
    if rel == builder.CATALOG_REL:
        source.write_bytes(original.replace(b"status: active", b"status: withdrawn"))
    else:
        source.write_bytes(original.replace(b"reviewed: false", b"reviewed: true"))
    assert source.read_bytes() != original
    if staged:
        _git(wiki, "add", "--", rel)

    result = _run(wiki)

    assert result.exit_code == 1, result.output
    assert "uncommitted source bytes" in result.output
    assert rel in result.output
    assert {p.relative_to(wiki): p.read_bytes()
            for p in (wiki / "exports/diagnostic").rglob("*.json")} == before
    # A real commit makes the same input exportable with the new attribution.
    _git(wiki, "add", "--", rel)
    _git(wiki, "commit", "-qm", "source revision")
    assert _run(wiki).exit_code == 0
    envelope = _read(wiki, "gamme/filtre-a-air.json")
    key = "source_catalog_commit" if rel == builder.CATALOG_REL else "source_wiki_commit"
    assert envelope[key] == _git(wiki, "log", "-1", "--format=%H", "--", rel)
    if rel == builder.CATALOG_REL:
        assert envelope["relations"][0]["sources"][0]["status"] == "withdrawn"
        assert envelope["relations"][0]["sources"][0]["raw_proven"] is False
    else:
        assert envelope["relations"][0]["evidence"]["reviewed"] is True


def test_unrelated_local_changes_do_not_block_export(wiki: Path):
    assert _run(wiki).exit_code == 0
    before = {p: p.read_bytes() for p in (wiki / "exports/diagnostic").rglob("*.json")}
    (wiki / "developer-notes.txt").write_text("unfinished work", encoding="utf-8")
    result = _run(wiki)
    assert result.exit_code == 0, result.output
    assert {p: p.read_bytes() for p in before} == before


def test_untracked_eligible_input_has_no_invented_commit(wiki: Path):
    _write_fiche(wiki, "filtre-a-huile", relations=[_relation(["oem_doc"])])
    result = _run(wiki)
    assert result.exit_code == 1
    assert "no commit found" in result.output
    assert "filtre-a-huile.md" in result.output
    assert not (wiki / "exports").exists()


# --- --check : comparaison sans écriture --------------------------------------------


def _tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts}


def test_check_passes_on_fresh_exports(wiki: Path):
    assert _run(wiki).exit_code == 0
    before = _tree(wiki)

    result = _run(wiki, "--check")

    assert result.exit_code == 0, result.output
    assert "check: 2 file(s) up to date" in result.output
    assert _tree(wiki) == before


@pytest.mark.parametrize("rel", ["gamme/filtre-a-air.json", "_index.json"])
def test_check_reports_hand_edit_without_rewriting(wiki: Path, rel: str):
    assert _run(wiki).exit_code == 0
    path = wiki / "exports" / "diagnostic" / rel
    path.write_bytes(path.read_bytes().replace(b'"schema_version": "2.0.0"', b'"schema_version": "2.0.1"'))
    before = _tree(wiki)

    result = _run(wiki, "--check")

    assert result.exit_code == 1, result.output
    assert f"STALE exports/diagnostic/{rel}" in result.output
    assert "never edited by hand" in result.output
    assert _tree(wiki) == before


@pytest.mark.parametrize("rel", ["gamme/filtre-a-air.json", "_index.json"])
def test_check_reports_missing_file(wiki: Path, rel: str):
    assert _run(wiki).exit_code == 0
    (wiki / "exports" / "diagnostic" / rel).unlink()
    before = _tree(wiki)

    result = _run(wiki, "--check")

    assert result.exit_code == 1, result.output
    assert f"MISSING exports/diagnostic/{rel}" in result.output
    assert _tree(wiki) == before


def test_check_reports_committed_source_change_not_yet_regenerated(wiki: Path):
    assert _run(wiki).exit_code == 0
    _commit_all(wiki, "exports")
    _write_fiche(wiki, "filtre-a-air", relations=[_relation(["oem_doc"])])
    _commit_all(wiki, "fiche change")
    before = _tree(wiki)

    result = _run(wiki, "--check")

    assert result.exit_code == 1, result.output
    assert "STALE exports/diagnostic/gamme/filtre-a-air.json" in result.output
    assert "STALE exports/diagnostic/_index.json" in result.output
    assert _tree(wiki) == before


def test_check_reports_unreconciled_export(wiki: Path):
    assert _run(wiki).exit_code == 0
    _write_fiche(wiki, "filtre-a-air", review_status="draft", relations=[_relation(["oem_doc"])])
    _commit_all(wiki, "unapprove")
    before = _tree(wiki)

    result = _run(wiki, "--check")

    assert result.exit_code == 1, result.output
    assert "UNRECONCILED exports/diagnostic/gamme/filtre-a-air.json" in result.output
    assert "STALE exports/diagnostic/_index.json" in result.output
    assert _tree(wiki) == before


def test_check_on_a_tree_without_exports_creates_nothing(wiki: Path):
    result = _run(wiki, "--check")

    assert result.exit_code == 1, result.output
    assert "MISSING exports/diagnostic/gamme/filtre-a-air.json" in result.output
    assert "MISSING exports/diagnostic/_index.json" in result.output
    assert not (wiki / "exports").exists()


def test_check_json_report(wiki: Path):
    assert _run(wiki).exit_code == 0
    (wiki / "exports" / "diagnostic" / "_index.json").unlink()

    result = _run(wiki, "--check", "--format", "json")

    assert result.exit_code == 1
    report = json.loads(result.stdout[: result.stdout.rindex("}") + 1])
    assert report == {"status": "DRIFT", "written": 0, "observations": [
        {"export_path": "exports/diagnostic/_index.json", "drift": "missing"}]}
    assert _run(wiki).exit_code == 0
    ok = _run(wiki, "--check", "--format", "json")
    assert ok.exit_code == 0, ok.output
    assert json.loads(ok.stdout) == {"status": "OK", "written": 0, "observations": []}


# --- --require-commits-on : les commits épinglés survivent à la fusion squash ----------


def test_pinned_commits_on_ref_are_accepted(wiki: Path):
    _git(wiki, "branch", "published")

    assert _run(wiki, "--require-commits-on", "published").exit_code == 0
    _commit_all(wiki, "exports")
    result = _run(wiki, "--check", "--require-commits-on", "published")
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("rel", ["wiki/gamme/filtre-a-air.md", builder.CATALOG_REL])
@pytest.mark.parametrize("check", [False, True])
def test_branch_commit_pinned_is_refused(wiki: Path, rel: str, check: bool):
    _git(wiki, "branch", "published")
    _git(wiki, "checkout", "-qb", "feature")
    source = wiki / rel
    source.write_bytes(source.read_bytes().replace(b"reviewed: false", b"reviewed: true")
                       .replace(b"status: active", b"status: withdrawn"))
    branch_commit = _commit_all(wiki, "source change on a branch")
    before = _tree(wiki)

    result = _run(wiki, *(["--check"] if check else []), "--require-commits-on", "published")

    assert result.exit_code == 1, result.output
    assert f"NOT ON published {branch_commit} ({rel})" in result.output
    assert "regenerated after merge" in result.output
    assert _tree(wiki) == before


def test_exports_built_on_a_branch_go_stale_at_squash_merge(wiki: Path):
    """Pourquoi la règle : la fusion squash remplace le commit épinglé par un autre."""
    assert _run(wiki).exit_code == 0
    _commit_all(wiki, "exports")
    _git(wiki, "branch", "published")
    _git(wiki, "checkout", "-qb", "feature")
    _write_fiche(wiki, "filtre-a-air", relations=[_relation(["oem_doc"])])
    _commit_all(wiki, "fiche change")
    assert _run(wiki).exit_code == 0
    _commit_all(wiki, "exports regenerated on the branch")
    _git(wiki, "checkout", "-q", "published")
    _git(wiki, "merge", "--squash", "feature")
    _commit_all(wiki, "squash merge")

    result = _run(wiki, "--check")

    assert result.exit_code == 1, result.output
    assert "STALE exports/diagnostic/gamme/filtre-a-air.json" in result.output


@pytest.mark.parametrize("ref", ["no-such-ref", "-x"])
def test_unverifiable_ref_fails(wiki: Path, ref: str):
    result = _run(wiki, "--require-commits-on", ref)

    assert result.exit_code == 1, result.output
    assert ("cannot verify" in result.output) if ref == "no-such-ref" else ("invalid ref" in result.output)
    assert not (wiki / "exports").exists()
