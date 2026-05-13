#!/usr/bin/env python3
"""
build_exports_seo — Vue dérivée wiki canon approved → exports/seo/.

Référence : ADR-059 SEO Runtime Projection (accepted 2026-05-13), Phase B PR-5a.

**Principe non-négociable** : aucun enrichissement, aucune génération. Le builder
**filtre** + **transforme uniquement** le contenu canon déjà approuvé.

Pipeline :
    wiki/<entity_type_singular>/<slug>.md (review_status: approved + exportable: true)
        ↓ filter audience SEO (entity_type ∈ {gamme, vehicle, constructeur, diagnostic-with-R3})
        ↓ transform structured JSON (facts, sources, blocks, roles_allowed)
        ↓ ajv-validable contre _meta/schema/exports-seo.schema.json
    exports/seo/<entity_type>/<slug>.json

Garde-fous (vérifiés par tests + schema) :
- 0 LLM (aucun import LLM SDK)
- 0 écriture DB (aucun import DB SDK)
- 0 écriture hors exports/seo/ (path enforcement strict)
- 0 enrichissement (interdiction modifier facts/blocks au-delà de la lecture wiki)
- support **toujours** exclu (route vers exports/support/, hors scope PR-5a)
- diagnostic exclu **sauf si** au moins un block R3_CONSEILS section S2_DIAG (per ADR-027)
- roles_allowed minItems:1 (rejet si aucun rôle SEO ne s'applique)
- schema_version + projection_contract_version distincts obligatoires

Usage:
    build_exports_seo.py --wiki-root /opt/automecanik/automecanik-wiki
    build_exports_seo.py --wiki-root ... --entity-id gamme:filtre-a-huile
    build_exports_seo.py --wiki-root ... --dry-run  # n'écrit rien

Exit codes :
    0 — success (artefacts écrits ou skipped idempotent)
    1 — wiki source invalid (parse error, frontmatter missing)
    2 — schema canon introuvable
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
import yaml


SCHEMA_VERSION = "1.0.0"
PROJECTION_CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "1.0.0"

# entity_types autorisés dans exports/seo/. 'support' explicitement EXCLU.
SEO_ENTITY_TYPES_BASE: set[str] = {"gamme", "vehicle", "constructeur"}
DIAGNOSTIC_CONDITIONAL_TYPE = "diagnostic"

FRONTMATTER_SEPARATOR = "---"

ROLES_BY_ENTITY_TYPE_DEFAULT: dict[str, list[str]] = {
    "gamme": ["R3_CONSEILS", "R4_REFERENCE", "R6_GUIDE_ACHAT"],
    "vehicle": ["R8_VEHICLE"],
    "constructeur": ["R7_BRAND"],
    "diagnostic": ["R3_CONSEILS"],
}

CONSUMERS_BY_ENTITY_TYPE_DEFAULT: dict[str, list[str]] = {
    "gamme": ["seo", "rag"],
    "vehicle": ["seo", "rag"],
    "constructeur": ["seo", "rag"],
    "diagnostic": ["seo", "rag", "diagnostic_tool"],
}


def _parse_markdown(path: Path) -> tuple[dict[str, Any], str]:
    """Retourne (frontmatter, body)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith(FRONTMATTER_SEPARATOR):
        raise click.ClickException(f"wiki source lacks frontmatter: {path}")
    parts = text.split(f"\n{FRONTMATTER_SEPARATOR}\n", 1)
    if len(parts) != 2:
        raise click.ClickException(f"frontmatter close-fence missing: {path}")
    fm_yaml = parts[0].lstrip(FRONTMATTER_SEPARATOR).lstrip("\n")
    fm = yaml.safe_load(fm_yaml)
    if not isinstance(fm, dict):
        raise click.ClickException(f"frontmatter not a dict: {path}")
    return fm, parts[1]


def _wiki_commit_sha(wiki_root: Path) -> str:
    """Récupère le HEAD commit du wiki repo. Informational-only metadata."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=wiki_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return out.stdout.strip()
    except Exception:
        return "0" * 40  # placeholder si git indisponible


def _has_r3_s2_diag_block(body: str) -> bool:
    """
    Détecte la présence d'un block R3_CONSEILS section S2_DIAG dans le body.
    Heuristique stricte : cherche `S2_DIAG` ou `## S2_DIAG` ou frontmatter
    explicite. Ne fait JAMAIS d'inférence sémantique.
    """
    if "S2_DIAG" in body:
        return True
    return False


def _is_seo_eligible(fm: dict, body: str, source_path: Path) -> tuple[bool, str]:
    """
    Décide si une fiche wiki canon peut produire un export SEO.

    Retourne (eligible, reason). Si non eligible, `reason` explique pourquoi.
    """
    entity_type = fm.get("entity_type")
    review_status = fm.get("review_status")
    exportable = fm.get("exportable")

    if entity_type == "support":
        return False, "support entity_type always routed to exports/support/, never exports/seo/"

    if entity_type not in SEO_ENTITY_TYPES_BASE and entity_type != DIAGNOSTIC_CONDITIONAL_TYPE:
        return False, f"entity_type={entity_type!r} not in SEO scope"

    if review_status != "approved":
        return False, f"review_status={review_status!r} (only 'approved' fiches export)"

    if not exportable:
        return False, f"exportable={exportable!r} (must be true)"

    if entity_type == DIAGNOSTIC_CONDITIONAL_TYPE and not _has_r3_s2_diag_block(body):
        return (
            False,
            "diagnostic entity_type but no R3_CONSEILS/S2_DIAG block — "
            "route to exports/support/ (per ADR-027 R5 sunset)",
        )

    return True, "eligible"


def _extract_facts_sources_blocks(
    fm: dict, body: str, entity_type: str
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    **Filter + transform only** : lit ce qui existe déjà dans le canon wiki.
    Aucun enrichissement, aucune génération.
    """
    facts: list[dict] = []
    sources: list[dict] = []
    blocks: list[dict] = []

    # Facts : copie depuis frontmatter `entity_data.facts` si présent
    entity_data = fm.get("entity_data") or {}
    if isinstance(entity_data, dict):
        raw_facts = entity_data.get("facts")
        if isinstance(raw_facts, list):
            for f in raw_facts:
                if isinstance(f, dict) and "key" in f and "value" in f:
                    facts.append(
                        {
                            "key": str(f["key"]),
                            "value": f["value"],
                            "source_id": f.get("source_id"),
                        }
                    )

    # Sources : projection depuis `source_refs` frontmatter
    source_refs = fm.get("source_refs") or []
    if isinstance(source_refs, list):
        for idx, ref in enumerate(source_refs):
            if not isinstance(ref, dict):
                continue
            kind = ref.get("kind") or ref.get("type") or "manual"
            sources.append(
                {
                    "id": ref.get("id") or ref.get("source_id") or f"src-{idx}",
                    "type": _normalize_source_type(kind),
                    "url": ref.get("url"),
                }
            )

    # Blocks : projection depuis `entity_data.blocks` si structuré
    raw_blocks = entity_data.get("blocks") if isinstance(entity_data, dict) else None
    if isinstance(raw_blocks, list):
        for b in raw_blocks:
            if not isinstance(b, dict):
                continue
            role = b.get("role")
            content_md = b.get("content_md") or b.get("content")
            if not role or not content_md:
                continue
            blocks.append(
                {
                    "role": str(role),
                    "section": b.get("section"),
                    "content_md": str(content_md),
                }
            )

    return facts, sources, blocks


SOURCE_TYPE_NORMALIZE: dict[str, str] = {
    "manual": "manual",
    "web": "web",
    "recycled": "recycled",
    "oem": "oem",
    "specialist": "specialist",
    "specialized_reference": "specialized_reference",
    "consulting": "consulting",
    "commercial": "commercial",
    "engineer": "engineer",
}


def _normalize_source_type(raw: str) -> str:
    return SOURCE_TYPE_NORMALIZE.get(str(raw).lower(), "manual")


def _compute_roles_allowed(fm: dict, entity_type: str, blocks: list[dict]) -> list[str]:
    """
    Détermine roles_allowed depuis le frontmatter si déclaré, sinon défaut
    par entity_type. Si aucun rôle ne reste, retourne [] (export sera rejeté).
    """
    fm_roles = fm.get("roles_allowed")
    if isinstance(fm_roles, list) and fm_roles:
        return [str(r) for r in fm_roles if r]
    return list(ROLES_BY_ENTITY_TYPE_DEFAULT.get(entity_type, []))


def _compute_consumers_allowed(fm: dict, entity_type: str) -> list[str]:
    fm_cons = fm.get("consumers_allowed")
    if isinstance(fm_cons, list) and fm_cons:
        return [str(c) for c in fm_cons if c]
    return list(CONSUMERS_BY_ENTITY_TYPE_DEFAULT.get(entity_type, ["seo", "rag"]))


def build_export(
    source_path: Path, wiki_root: Path, commit_sha: str
) -> dict[str, Any] | None:
    """
    Construit l'export JSON pour un fichier wiki canon.

    Retourne None si la fiche n'est pas éligible (support, non-approved, etc.).
    Retourne dict conforme exports-seo.schema.json sinon.
    """
    fm, body = _parse_markdown(source_path)
    eligible, reason = _is_seo_eligible(fm, body, source_path)
    if not eligible:
        click.echo(f"SKIP {source_path.name}: {reason}", err=True)
        return None

    entity_type = fm["entity_type"]
    slug = fm.get("slug")
    if not isinstance(slug, str) or not slug:
        raise click.ClickException(f"frontmatter missing slug: {source_path}")

    facts, sources, blocks = _extract_facts_sources_blocks(fm, body, entity_type)
    roles_allowed = _compute_roles_allowed(fm, entity_type, blocks)
    consumers_allowed = _compute_consumers_allowed(fm, entity_type)

    if not roles_allowed:
        click.echo(
            f"SKIP {source_path.name}: roles_allowed empty after compute — "
            "schema enforces minItems:1. Route to exports/support/ if applicable.",
            err=True,
        )
        return None

    rel_path = source_path.resolve().relative_to(wiki_root.resolve())
    wiki_path = str(rel_path).replace("\\", "/")

    raw_bytes = source_path.read_bytes()
    content_hash = f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}"

    return {
        "entity_id": f"{entity_type}:{slug}",
        "entity_type": entity_type,
        "schema_version": SCHEMA_VERSION,
        "projection_contract_version": PROJECTION_CONTRACT_VERSION,
        "source_wiki_commit": commit_sha,
        "wiki_path": wiki_path,
        "content_hash": content_hash,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "builder_version": BUILDER_VERSION,
        "facts": facts,
        "sources": sources,
        "blocks": blocks,
        "roles_allowed": roles_allowed,
        "consumers_allowed": consumers_allowed,
    }


def _enforce_output_path_strict(out_path: Path, wiki_root: Path) -> None:
    """
    GARDE-FOU STRICT : refuse toute écriture hors `wiki_root/exports/seo/`.

    Toute tentative de write ailleurs (wiki/<entity_type>/, exports/rag/,
    exports/support/, proposals/...) déclenche ClickException.
    """
    try:
        rel = out_path.resolve().relative_to(wiki_root.resolve())
    except ValueError:
        raise click.ClickException(
            f"refused: output path {out_path} is outside wiki_root {wiki_root}"
        )
    parts = rel.parts
    if not (len(parts) >= 2 and parts[0] == "exports" and parts[1] == "seo"):
        raise click.ClickException(
            f"refused: build_exports_seo writes only to exports/seo/, "
            f"got {rel} (PR-5a strict scope)"
        )


def _write_export(payload: dict, wiki_root: Path) -> Path:
    entity_type = payload["entity_type"]
    slug = payload["entity_id"].split(":", 1)[1]
    out_path = wiki_root / "exports" / "seo" / entity_type / f"{slug}.json"
    _enforce_output_path_strict(out_path, wiki_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out_path


def _iter_canon_files(wiki_root: Path) -> list[Path]:
    """Itère wiki/<entity_type_singular>/*.md (4 entity_types SEO + diagnostic conditional)."""
    wiki_dir = wiki_root / "wiki"
    if not wiki_dir.is_dir():
        return []
    candidates: list[Path] = []
    for entity in SEO_ENTITY_TYPES_BASE | {DIAGNOSTIC_CONDITIONAL_TYPE}:
        sub = wiki_dir / entity
        if sub.is_dir():
            candidates.extend(sorted(sub.glob("*.md")))
    return candidates


@click.command()
@click.option(
    "--wiki-root",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("/opt/automecanik/automecanik-wiki"),
    show_default=True,
)
@click.option(
    "--entity-id",
    default=None,
    help="Si fourni, builde un seul export (format <entity_type>:<slug>). Sinon, tous les canon files éligibles.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="N'écrit rien sur disque, affiche ce qui serait écrit",
)
def main(wiki_root: Path, entity_id: str | None, dry_run: bool) -> None:
    """
    Filter + transform wiki canon approved → exports/seo/<entity_type>/<slug>.json.

    AUCUN enrichissement. AUCUN LLM. AUCUNE DB. AUCUNE écriture hors exports/seo/.
    """
    if not (wiki_root / "_meta" / "schema" / "exports-seo.schema.json").exists():
        click.echo(
            f"schema canon introuvable: {wiki_root}/_meta/schema/exports-seo.schema.json",
            err=True,
        )
        sys.exit(2)

    commit_sha = _wiki_commit_sha(wiki_root)

    if entity_id:
        m = re.match(r"^([a-z]+):([a-z0-9][a-z0-9-]*[a-z0-9])$", entity_id)
        if not m:
            raise click.ClickException(f"--entity-id invalid: {entity_id!r}")
        entity_type, slug = m.group(1), m.group(2)
        source = wiki_root / "wiki" / entity_type / f"{slug}.md"
        if not source.exists():
            raise click.ClickException(f"canon source absent: {source}")
        candidates = [source]
    else:
        candidates = _iter_canon_files(wiki_root)

    written = 0
    skipped = 0
    for src in candidates:
        payload = build_export(src, wiki_root, commit_sha)
        if payload is None:
            skipped += 1
            continue
        if dry_run:
            click.echo(
                f"DRY_RUN would-write exports/seo/{payload['entity_type']}/{payload['entity_id'].split(':', 1)[1]}.json"
            )
        else:
            out = _write_export(payload, wiki_root)
            click.echo(f"OK {out.relative_to(wiki_root)}")
        written += 1

    click.echo(f"\ntotal: candidates={len(candidates)} written={written} skipped={skipped}")
    sys.exit(0)


if __name__ == "__main__":
    main()
