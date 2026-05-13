#!/usr/bin/env python3
"""
bridge_rag_to_pipeline — Pont ultra-minimal rag/knowledge/ → pipeline PR-3a.

Référence : ADR-059 SEO Runtime Projection (accepted 2026-05-13), Phase B PR-3b.

**Principe non-négociable** : ce script ne contient AUCUNE logique d'extraction.
Il convertit un fichier rag markdown → artefact raw HTML synthétique →
invocation subprocess du pipeline canonique PR-3a (extract_claims +
build_source_map + render_proposal).

Garde-fous hérités transitivement (via subprocess invocation) :
- 0 LLM (vérifié par PR-3a test_no_llm_inference_imports_*)
- 0 écriture DB (vérifié par PR-3a test_no_db_imports_anywhere)
- 0 écriture wiki canon (vérifié par PR-3a _refuse_wiki_canon_write)

Flow :
    rag/knowledge/<cat>/<slug>.md
       ↓ parse frontmatter (category, slug, title)
       ↓ body markdown → HTML synthétique minimal
       ↓ sha256(body) = filename
       ↓ écrit raw/recycled/rag-knowledge/<cat>/<sha256>.html + .manifest.yaml
       ↓ subprocess: extract_claims → claims.yaml
       ↓ subprocess: build_source_map → source_map.yaml
       ↓ subprocess: render_proposal → proposals/<slug>.md
       ↓ proposal final (avec review_status: proposed, exportable: false)

Usage:
    bridge_rag_to_pipeline.py --rag-file /opt/automecanik/rag/knowledge/gammes/plaquette-de-frein.md
    bridge_rag_to_pipeline.py --rag-file ... --dry-run
    bridge_rag_to_pipeline.py --rag-file ... \\
        --pipeline-root /opt/automecanik/app \\
        --raw-root /opt/automecanik/automecanik-raw \\
        --wiki-root /opt/automecanik/automecanik-wiki

Exit codes:
    0 — success
    1 — rag file invalid / pipeline subprocess error
    2 — category not mappable to entity_type canon ADR-031
"""
from __future__ import annotations

import hashlib
import html as html_lib
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
import yaml


# rag/knowledge/<cat>/ → entity_type canon ADR-031 (singulier)
CATEGORY_TO_ENTITY_TYPE: dict[str, str] = {
    "gammes": "gamme",
    "vehicles": "vehicle",
    "constructeurs": "constructeur",
    "support": "support",
    "policies": "support",
    "faq": "support",
    "faqs": "support",
    "diagnostic": "diagnostic",
}


FRONTMATTER_RE = re.compile(r"^---\n([\s\S]*?)\n---\n([\s\S]*)$")


def _parse_rag_frontmatter(rag_path: Path) -> tuple[dict[str, Any], str]:
    """Retourne (frontmatter_dict, body_markdown) depuis un fichier rag."""
    text = rag_path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise click.ClickException(
            f"rag file lacks YAML frontmatter (---...---): {rag_path}"
        )
    fm = yaml.safe_load(match.group(1))
    if not isinstance(fm, dict):
        raise click.ClickException(f"rag frontmatter parse failed: {rag_path}")
    return fm, match.group(2)


def _category_from_path_or_frontmatter(
    rag_path: Path, frontmatter: dict[str, Any]
) -> str:
    """
    Détermine la category rag (gammes/vehicles/...) depuis :
      1. frontmatter `category` si présent
      2. sinon le nom du dossier parent (e.g. rag/knowledge/gammes/x.md → 'gammes')
    """
    cat = frontmatter.get("category")
    if isinstance(cat, str) and cat in CATEGORY_TO_ENTITY_TYPE:
        return cat
    parent = rag_path.parent.name
    if parent in CATEGORY_TO_ENTITY_TYPE:
        return parent
    raise click.ClickException(
        f"unable to determine rag category for {rag_path} "
        f"(frontmatter.category={cat}, parent={parent}); "
        f"expected one of {sorted(CATEGORY_TO_ENTITY_TYPE)}"
    )


def _markdown_body_to_synthetic_html(title: str, body_markdown: str, source_path: Path) -> str:
    """
    Conversion ULTRA-MINIMALE markdown → HTML synthétique.

    Ne tente PAS une vraie conversion Markdown → HTML (pas de markdown lib —
    on garde la dépendance graph minimale et évite toute interprétation
    sémantique). Le body est emballé en <article><pre> pour préserver le
    contenu littéral, lisible par Readability et Trafilatura.

    Le but : produire un HTML acceptable par le pipeline PR-3a sans
    réimplémenter d'extracteur côté wiki.
    """
    title_esc = html_lib.escape(title)
    body_esc = html_lib.escape(body_markdown)
    return (
        "<!doctype html>\n"
        f'<html lang="fr"><head><meta charset="utf-8"/>'
        f"<title>{title_esc}</title>"
        f'<meta name="description" content="{title_esc} (source rag: {html_lib.escape(str(source_path))})"/>'
        f"</head><body>"
        f"<h1>{title_esc}</h1>"
        f"<article><pre>{body_esc}</pre></article>"
        "</body></html>\n"
    )


def _write_raw_artifact(
    raw_root: Path,
    category: str,
    slug: str,
    html: str,
    rag_path: Path,
    trust_level: str,
) -> Path:
    """
    Écrit raw/recycled/rag-knowledge/<cat>/<sha256>.html + sidecar manifest.

    Retourne le path du HTML écrit (utilisable comme input pour extract_claims).
    """
    body_bytes = html.encode("utf-8")
    content_hash = f"sha256:{hashlib.sha256(body_bytes).hexdigest()}"
    hash_short = content_hash.split(":", 1)[1]

    target_dir = raw_root / "recycled" / "rag-knowledge" / category
    target_dir.mkdir(parents=True, exist_ok=True)
    target_html = target_dir / f"{hash_short}.html"
    target_manifest = target_dir / f"{hash_short}.manifest.yaml"

    if not target_html.exists():
        target_html.write_bytes(body_bytes)

    if not target_manifest.exists():
        manifest = {
            "content_hash": content_hash,
            "url": f"file://{rag_path.resolve()}",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "origin_repo": "automecanik-raw",
            "source_level": "manual",
            "trust_level": trust_level,
            "can_feed_wiki": False,
            "http_status": 200,
            "content_length_bytes": len(body_bytes),
            "user_agent": "bridge_rag_to_pipeline/1.0",
            "capture_tool": "bridge_rag_to_pipeline",
            "capture_tool_version": "1.0.0",
            "bridge_source_rag_path": str(rag_path),
            "bridge_source_kind": "rag_recycled",
        }
        target_manifest.write_text(
            yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    return target_html


def _run_pipeline_step(
    pipeline_root: Path,
    module: str,
    args: list[str],
) -> None:
    """Subprocess invocation du module pipeline PR-3a depuis pipeline_root."""
    cmd = [sys.executable, "-m", f"scripts.wiki_promotion.{module}", *args]
    result = subprocess.run(
        cmd,
        cwd=pipeline_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise click.ClickException(
            f"pipeline step {module!r} failed ({result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


@click.command()
@click.option(
    "--rag-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Fichier rag source (e.g. /opt/automecanik/rag/knowledge/gammes/<slug>.md)",
)
@click.option(
    "--pipeline-root",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("/opt/automecanik/app"),
    show_default=True,
    help="Racine du monorepo (où vit scripts/wiki_promotion/)",
)
@click.option(
    "--raw-root",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("/opt/automecanik/automecanik-raw"),
    show_default=True,
)
@click.option(
    "--wiki-root",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("/opt/automecanik/automecanik-wiki"),
    show_default=True,
)
@click.option(
    "--trust-level",
    default="2_medium_concordant",
    show_default=True,
    help="Trust level pour le manifest synthétique du raw artifact",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="N'invoque pas le pipeline, affiche seulement le mapping calculé",
)
def main(
    rag_file: Path,
    pipeline_root: Path,
    raw_root: Path,
    wiki_root: Path,
    trust_level: str,
    dry_run: bool,
) -> None:
    """
    Bridge un fichier rag/knowledge/<cat>/<slug>.md vers le pipeline PR-3a.

    Conformément à ADR-059 Phase B PR-3b : ce bridge est un simple adaptateur
    d'entrée. AUCUNE extraction ou logique métier locale. Tout passe par les
    scripts canon PR-3a invoqués en subprocess.
    """
    frontmatter, body_markdown = _parse_rag_frontmatter(rag_file)

    slug = frontmatter.get("slug")
    title = frontmatter.get("title")
    if not isinstance(slug, str) or not slug:
        raise click.ClickException(f"rag frontmatter missing 'slug': {rag_file}")
    if not isinstance(title, str) or not title:
        raise click.ClickException(f"rag frontmatter missing 'title': {rag_file}")

    category = _category_from_path_or_frontmatter(rag_file, frontmatter)
    entity_type = CATEGORY_TO_ENTITY_TYPE[category]

    if dry_run:
        click.echo(f"rag_file:    {rag_file}")
        click.echo(f"category:    {category}")
        click.echo(f"entity_type: {entity_type}")
        click.echo(f"slug:        {slug}")
        click.echo(f"title:       {title}")
        click.echo("dry-run: pipeline not invoked")
        sys.exit(0)

    html = _markdown_body_to_synthetic_html(title, body_markdown, rag_file)
    raw_html_path = _write_raw_artifact(
        raw_root, category, slug, html, rag_file, trust_level
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        claims_path = tmp_dir / "claims.yaml"
        source_map_path = tmp_dir / "source_map.yaml"

        _run_pipeline_step(
            pipeline_root,
            "extract_claims",
            ["--raw-html", str(raw_html_path), "--out", str(claims_path)],
        )
        _run_pipeline_step(
            pipeline_root,
            "build_source_map",
            [
                "--claims", str(claims_path),
                "--entity-type", entity_type,
                "--slug", slug,
                "--title", title,
                "--out", str(source_map_path),
            ],
        )
        _run_pipeline_step(
            pipeline_root,
            "render_proposal",
            [
                "--source-map", str(source_map_path),
                "--wiki-root", str(wiki_root),
            ],
        )

    expected_proposal = wiki_root / "proposals" / f"{slug}.md"
    if not expected_proposal.exists():
        raise click.ClickException(
            f"pipeline completed but expected proposal missing: {expected_proposal}"
        )
    click.echo(f"bridged: {rag_file} -> {expected_proposal}")
    sys.exit(0)


if __name__ == "__main__":
    main()
