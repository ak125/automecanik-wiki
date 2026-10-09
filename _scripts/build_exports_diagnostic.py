#!/usr/bin/env python3
"""build_exports_diagnostic.py — vue dérivée des diagnostic_relations (ADR-033).

Filtre + transforme les fiches `wiki/gamme/*.md` approuvées qui portent des
`diagnostic_relations` vers :

    exports/diagnostic/gamme/<slug>.json   (une relation par entrée, sources résolues)
    exports/diagnostic/_index.json         (liste triée des exports + sha256)

Consommateur : writer de projection diagnostic du monorepo (spec
`docs/superpowers/specs/2026-09-30-diagnostic-wiki-provenance-design.md`, §4.2).

Contrat :
- AUCUN LLM, AUCUNE DB, AUCUN enrichissement : chaque champ est copié de la fiche ou
  du catalogue de sources, ou calculé par une fonction canonique existante
  (`compute-symptom-confidence.compute_score`, `gen_coverage_map.is_page_proven`).
- Déterministe : aucun horodatage, aucun HEAD. `source_wiki_commit` = dernier commit
  touchant la fiche ; `source_catalog_commit` = dernier commit touchant le catalogue.
  Deux runs sur le même canon produisent les mêmes octets.
- Retrait : un export existant sans fiche éligible est rapporté UNRECONCILED, conservé,
  et le build échoue. Le retrait est une PR WIKI qui supprime
  `exports/diagnostic/gamme/<slug>.json` puis relance ce builder (l'index est régénéré).

Exit : 0 OK · 1 erreur de build ou UNRECONCILED · 2 schéma d'export introuvable.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import click
import yaml

from build_exports_seo import _assert_full_clone, _parse_markdown
from gen_coverage_map import is_page_proven

SCHEMA_VERSION = "1.0.0"
BUILDER_VERSION = "1.0.0"
CATALOG_REL = "_meta/source-catalog.yaml"
EXPORT_SCHEMA_REL = Path("_meta") / "schema" / "exports-diagnostic.schema.json"
EXPORTS_REL = Path("exports") / "diagnostic"
_PART_SUFFIX = re.compile(r"_p\d+$")
_SCRIPTS_DIR = Path(__file__).resolve().parent


def _load_compute_score():
    """`compute_score` du script canonique (nom à tirets → import par chemin)."""
    spec = importlib.util.spec_from_file_location(
        "compute_symptom_confidence", _SCRIPTS_DIR / "compute-symptom-confidence.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.compute_score


compute_score = _load_compute_score()


def _sha256_prefixed(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_catalog(wiki_root: Path) -> dict[str, dict]:
    """Catalogue de sources strict : slug unique, `status` explicite, aucun repli."""
    path = wiki_root / CATALOG_REL
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise click.ClickException(f"source catalog unreadable: {path}: {exc}") from exc
    sources = data.get("sources") if isinstance(data, dict) else None
    if not isinstance(sources, list):
        raise click.ClickException(f"source catalog has no 'sources' list: {path}")
    catalog: dict[str, dict] = {}
    for entry in sources:
        if not isinstance(entry, dict) or not isinstance(entry.get("slug"), str):
            raise click.ClickException(f"source catalog entry without slug: {entry!r}")
        # Le schéma défaut `active`, le guard aussi, G1 lit « non prouvé » : un statut
        # implicite n'a pas de sens unique. On exige qu'il soit écrit.
        if "status" not in entry:
            raise click.ClickException(
                f"source catalog entry without explicit status: {entry['slug']}"
            )
        if entry["slug"] in catalog:
            raise click.ClickException(f"duplicate source catalog slug: {entry['slug']}")
        catalog[entry["slug"]] = entry
    return catalog


def _last_commit(wiki_root: Path, rel_path: str) -> str:
    """SHA du dernier commit touchant `rel_path`. Pas de sentinelle : échoue fort."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", rel_path],
            cwd=wiki_root,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise click.ClickException(f"git unavailable for {rel_path}: {exc}") from exc
    sha = out.stdout.strip()
    if out.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise click.ClickException(
            f"no commit found for {rel_path} (git repository with the file committed "
            f"is required): {out.stderr.strip()}"
        )
    return sha


def _export_source(slug: str, catalog: dict[str, dict]) -> dict:
    """Source résolue ; `_pNN` normalisé comme `quality-gates.gate_diagnostic_relations`."""
    catalog_slug = _PART_SUFFIX.sub("", slug)
    entry = catalog.get(catalog_slug)
    if entry is None:
        raise click.ClickException(
            f"source slug unknown to the catalog: {slug!r} (normalised {catalog_slug!r})"
        )
    raw_ref = entry.get("raw_ref")
    return {
        "slug": slug,
        "catalog_slug": catalog_slug,
        "type": entry.get("type"),
        "status": entry["status"],
        "raw_ref": raw_ref if raw_ref else None,
        "raw_proven": is_page_proven(entry),
    }


def _export_relation(index: int, item: dict, catalog: dict[str, dict]) -> dict:
    evidence = item["evidence"]
    return {
        "relation_index": index,
        "relation_sha256": _sha256_prefixed(_canonical_json(item)),
        "symptom_slug": item["symptom_slug"],
        "system_slug": item["system_slug"],
        "relation_to_part": item["relation_to_part"],
        "part_role": item["part_role"],
        "evidence": {
            "confidence": evidence["confidence"],
            "source_policy": evidence["source_policy"],
            "reviewed": evidence["reviewed"],
            "diagnostic_safe": evidence["diagnostic_safe"],
        },
        # La cohérence valeur écrite ↔ formule est portée par
        # `compute-symptom-confidence.py --check --all` (CI wiki) : on appelle la même
        # formule, on ne re-vérifie pas la fiche.
        "confidence_score_computed": compute_score(item["sources"], catalog),
        "sources": [_export_source(slug, catalog) for slug in item["sources"]],
    }


_RELATION_KEYS = ("symptom_slug", "system_slug", "relation_to_part", "part_role", "evidence", "sources")
_EVIDENCE_KEYS = ("confidence", "source_policy", "reviewed", "diagnostic_safe")


def _check_relations(relations: Any, fiche_name: str) -> None:
    """Échec explicite (jamais de défaut ni de relation ignorée) sur une relation malformée."""
    if not isinstance(relations, list):
        raise click.ClickException(
            f"{fiche_name}: diagnostic_relations must be a list, got {type(relations).__name__}"
        )
    for i, item in enumerate(relations):
        where = f"{fiche_name}: diagnostic_relations[{i}]"
        if not isinstance(item, dict):
            raise click.ClickException(f"{where} must be a mapping (relation), got {type(item).__name__}")
        for key in _RELATION_KEYS:
            if key not in item:
                raise click.ClickException(f"{where} is missing required key '{key}'")
        if not isinstance(item["evidence"], dict):
            raise click.ClickException(f"{where}.evidence must be a mapping")
        for key in _EVIDENCE_KEYS:
            if key not in item["evidence"]:
                raise click.ClickException(f"{where}.evidence is missing required key '{key}'")
        if not isinstance(item["sources"], list):
            raise click.ClickException(f"{where}.sources must be a list")


def is_eligible(fm: dict) -> bool:
    """Fiche approuvée portant au moins une diagnostic_relation."""
    return fm.get("review_status") == "approved" and bool(fm.get("diagnostic_relations"))


def build_gamme_export(
    fm: dict,
    source_path: Path,
    wiki_root: Path,
    catalog: dict[str, dict],
    commit_sha: str,
    catalog_commit: str,
) -> dict:
    """Export d'une fiche éligible (`is_eligible(fm)` vrai)."""
    slug = fm.get("slug")
    if slug != source_path.stem:
        raise click.ClickException(
            f"frontmatter slug {slug!r} differs from file name {source_path.name}"
        )
    _check_relations(fm["diagnostic_relations"], source_path.name)
    exported = [
        _export_relation(i, item, catalog) for i, item in enumerate(fm["diagnostic_relations"])
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "builder_version": BUILDER_VERSION,
        "export_kind": "diagnostic_gamme",
        "gamme_slug": slug,
        "wiki_path": source_path.resolve().relative_to(wiki_root.resolve()).as_posix(),
        "source_wiki_commit": commit_sha,
        "source_catalog_commit": catalog_commit,
        "content_hash": _sha256_prefixed(_canonical_json(exported)),
        "relations": exported,
    }


def _serialise(payload: dict) -> bytes:
    # Newline final : le WIKI lint via end-of-file-fixer.
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write_strict(out_path: Path, data: bytes, wiki_root: Path) -> None:
    """Refuse toute écriture hors `exports/diagnostic/`."""
    try:
        rel = out_path.resolve().relative_to((wiki_root / EXPORTS_REL).resolve())
    except ValueError as exc:
        raise click.ClickException(f"refused: {out_path} is outside {EXPORTS_REL}/") from exc
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    click.echo(f"OK {EXPORTS_REL / rel}", err=True)


@click.command()
@click.option(
    "--wiki-root",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("/opt/automecanik/automecanik-wiki"),
    show_default=True,
)
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def main(wiki_root: Path, output_format: str) -> None:
    """wiki/gamme/*.md approuvées avec diagnostic_relations → exports/diagnostic/."""
    if not (wiki_root / EXPORT_SCHEMA_REL).exists():
        click.echo(f"export schema not found: {wiki_root / EXPORT_SCHEMA_REL}", err=True)
        sys.exit(2)
    _assert_full_clone(wiki_root)

    catalog = _load_catalog(wiki_root)
    catalog_commit = _last_commit(wiki_root, CATALOG_REL)

    payloads: list[dict] = []
    gamme_dir = wiki_root / "wiki" / "gamme"
    for src in sorted(gamme_dir.glob("*.md")) if gamme_dir.is_dir() else []:
        fm, _body = _parse_markdown(src)
        if not is_eligible(fm):
            continue
        rel = src.resolve().relative_to(wiki_root.resolve()).as_posix()
        payloads.append(
            build_gamme_export(fm, src, wiki_root, catalog, _last_commit(wiki_root, rel), catalog_commit)
        )

    exports_root = wiki_root / EXPORTS_REL
    expected = {exports_root / "gamme" / f"{p['gamme_slug']}.json" for p in payloads}
    existing = {p for p in (exports_root / "gamme").glob("*.json") if p.is_file()}
    unreconciled = sorted(existing - expected)
    if unreconciled:
        observations = [
            {"export_path": p.relative_to(wiki_root).as_posix(), "withdrawal_authorized": False}
            for p in unreconciled
        ]
        if output_format == "json":
            click.echo(json.dumps(
                {"status": "UNRECONCILED", "written": 0, "observations": observations},
                ensure_ascii=False, indent=2, sort_keys=True,
            ))
        for obs in observations:
            click.echo(f"UNRECONCILED {obs['export_path']} (preserved)", err=True)
        raise click.ClickException(
            "Retained diagnostic exports have no eligible fiche; governed withdrawal "
            "(WIKI PR deleting the export) required before publication."
        )

    files = []
    for payload in sorted(payloads, key=lambda p: p["gamme_slug"]):
        data = _serialise(payload)
        _write_strict(exports_root / "gamme" / f"{payload['gamme_slug']}.json", data, wiki_root)
        files.append({
            "path": f"gamme/{payload['gamme_slug']}.json",
            "sha256": _sha256_prefixed(data),
            "source_wiki_commit": payload["source_wiki_commit"],
            "relation_count": len(payload["relations"]),
        })
    index = {
        "schema_version": SCHEMA_VERSION,
        "builder_version": BUILDER_VERSION,
        "export_kind": "diagnostic_index",
        "source_catalog_commit": catalog_commit,
        "files": files,
    }
    _write_strict(exports_root / "_index.json", _serialise(index), wiki_root)

    if output_format == "json":
        click.echo(json.dumps(
            {"status": "OK", "written": len(files), "observations": []},
            ensure_ascii=False, indent=2, sort_keys=True,
        ))
    else:
        click.echo(f"total: exported={len(files)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
