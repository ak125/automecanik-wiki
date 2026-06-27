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
from pathlib import Path
from typing import Any

import click
import yaml


SCHEMA_VERSION = "1.1.0"
PROJECTION_CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "1.1.0"

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


# Placeholders déterministes quand git est indisponible / fichier non-suivi.
_COMMIT_SHA_PLACEHOLDER = "0" * 40
_GENERATED_AT_PLACEHOLDER = "1970-01-01T00:00:00+00:00"
# Séparateur d'unité ASCII (jamais présent dans un SHA / une date ISO).
_GIT_FIELD_SEP = "\x1f"


def _wiki_file_commit_meta(wiki_root: Path, source_path: Path) -> tuple[str, str]:
    """(`source_wiki_commit`, `generated_at`) du DERNIER commit touchant CE fichier.

    Renvoie le SHA + la committer-date ISO-8601 du dernier commit ayant modifié
    `source_path`, PAS le HEAD du repo. Conséquence : l'export est une **fonction
    pure du contenu canon** de la fiche — invariant aux commits non liés (commit
    d'export du bot, nightly diag-canon, etc.). Donc :

    - deux runs sur le même canon → octets identiques (drift-gate sans flapping) ;
    - l'auto-commit CI ne se ré-déclenche pas en boucle (le commit d'export ne
      touche pas `wiki/<fiche>.md`, donc ce SHA ne bouge pas).

    `source_wiki_commit` est INFORMATIONAL-ONLY (audit) per ADR-059 — l'autorité
    de replay est `exports_snapshot_hash` côté projection — donc un SHA per-fichier
    est conforme au contrat (et plus précis qu'un HEAD bruité). Pas d'horloge murale.
    """
    try:
        rel = source_path.resolve().relative_to(wiki_root.resolve())
        out = subprocess.run(
            ["git", "log", "-1", f"--format=%H{_GIT_FIELD_SEP}%cI", "--", str(rel)],
            cwd=wiki_root,
            check=True,
            capture_output=True,
            text=True,
        )
        line = out.stdout.strip()
        if line:
            sha, _, date = line.partition(_GIT_FIELD_SEP)
            if sha and date:
                return sha, date
    except Exception:
        pass
    return _COMMIT_SHA_PLACEHOLDER, _GENERATED_AT_PLACEHOLDER


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

    # `exportable` est canoniquement un mapping par audience {rag, seo, support}
    # (frontmatter.schema.json — "Gates d'export par audience. Tous false par
    # défaut. Décision humaine requise pour passer à true."). Le gate SEO lit
    # STRICTEMENT exportable.seo : une fiche {seo:false, rag:true} ne doit JAMAIS
    # entrer dans exports/seo/. Tolérance legacy : fiches v1.0.0/v0.legacy où
    # `exportable` est encore un booléen.
    if isinstance(exportable, dict):
        seo_gate = bool(exportable.get("seo"))
    elif isinstance(exportable, bool):
        seo_gate = exportable
    else:
        seo_gate = False
    if not seo_gate:
        return False, f"exportable.seo not true (exportable={exportable!r})"

    if entity_type == DIAGNOSTIC_CONDITIONAL_TYPE and not _has_r3_s2_diag_block(body):
        return (
            False,
            "diagnostic entity_type but no R3_CONSEILS/S2_DIAG block — "
            "route to exports/support/ (per ADR-027 R5 sunset)",
        )

    return True, "eligible"


def _gamme_source_id(source_refs: list) -> str:
    """1er source_ref → id PRÉFIXÉ (raw:/web:) pour les blocs éditoriaux (ADR-086)."""
    for ref in source_refs or []:
        if not isinstance(ref, dict):
            continue
        kind = (ref.get("kind") or ref.get("type") or "").lower()
        if kind in ("recycled", "raw"):
            return f"raw:{ref.get('origin_path') or ref.get('id') or 'recycled'}"
        if kind in ("web", "external_url", "specialist", "oem"):
            return f"web:{ref.get('id') or ref.get('url') or 'web'}"
    return "raw:recycled"


# ADR-086 §2bis — taxonomie section éditoriale gamme → rôle SEO (déterministe, contrôlé).
# Les sections DÉTERMINISTES (vehicle_selector/compatibility/related_parts) ne sont PAS ici :
# elles sont composées depuis dimensions/related_parts/DB par _map_gamme_to_facts_blocks.
_GAMME_EDITORIAL_ROLES: dict[str, str] = {
    "function": "R3_CONSEILS",
    "failure_symptoms": "R3_CONSEILS",
    "maintenance_interval": "R3_CONSEILS",
    "variants": "R4_REFERENCE",
    "selection_criteria": "R6_GUIDE_ACHAT",
    "quality_tiers": "R6_GUIDE_ACHAT",
    "standards_norms": "R4_REFERENCE",
    "replacement_guidance": "R3_CONSEILS",
    "faq": "R3_CONSEILS",  # FAQ gamme = cluster gamme (R3), PAS R0_HOME (home) — cohérent roles_allowed
}


def _map_gamme_editorial_to_blocks(ed: dict) -> list[dict]:
    """gamme `entity_data.editorial.<section>` → blocks[] role-aware (ADR-086 §2bis).
    Prose curée+sourcée niveau GAMME (1/gamme, pas de duplicate). Ordre déterministe (taxonomie).
    ZÉRO filler : section absente/invalide (sans content_md ou sans source_ids) → ignorée."""
    editorial = ed.get("editorial")
    if not isinstance(editorial, dict):
        return []
    blocks: list[dict] = []
    for section, role in _GAMME_EDITORIAL_ROLES.items():  # itère la taxonomie = ordre stable
        entry = editorial.get(section)
        if not isinstance(entry, dict):
            continue
        content = entry.get("content_md")
        sources = entry.get("source_ids")
        if not content or not isinstance(sources, list) or not sources:
            continue  # bloc invalide → non émis, jamais inventé
        blocks.append({
            "role": role,
            "section": section,
            "content_md": str(content),
            "source_ids": list(sources),
            "truth_level": entry.get("truth_level") or "editorial",
            "usefulness_target": entry.get("usefulness_target") or section,
        })
    return blocks


def _map_vehicle_to_blocks(ed: dict) -> list[dict]:
    """véhicule `entity_data.{known_issues_by_engine,maintenance_by_engine}` → blocks R8_VEHICLE
    role-aware (ADR-086 §1 surface R8). Connaissance PAR MOTORISATION = la couche qui différencie
    chaque R2 (R2 = R1 ⊕ R8). Ordre déterministe (clé moteur triée). ZÉRO filler : map absente ou
    entrée invalide (sans content_md / sans source_ids) → ignorée, jamais inventée."""
    blocks: list[dict] = []
    for field, section in (("known_issues_by_engine", "known_issues"),
                           ("maintenance_by_engine", "maintenance")):
        m = ed.get(field)
        if not isinstance(m, dict):
            continue
        for engine_key in sorted(m):  # ordre stable = déterministe / replay-safe
            entry = m[engine_key]
            if not isinstance(entry, dict):
                continue
            content = entry.get("content_md")
            sources = entry.get("source_ids")
            if not content or not isinstance(sources, list) or not sources:
                continue  # bloc invalide → non émis
            blocks.append({
                "role": "R8_VEHICLE",
                "section": section,
                "content_md": str(content),
                "source_ids": list(sources),
                "truth_level": entry.get("truth_level") or "sourced",
                "usefulness_target": engine_key,  # trace la motorisation (clé normalisée)
            })
    return blocks


def _map_gamme_to_facts_blocks(
    ed: dict, source_refs: list
) -> tuple[list[dict], list[dict]]:
    """gamme `entity_data.{dimensions,decision_brief,maintenance,related_parts}` → facts + blocks
    role-aware. DÉTERMINISTE, LOSSLESS (champ partiel → consigné, jamais inventé), ZÉRO filler
    (aucun bloc si aucun champ structuré présent). ADR-086."""
    facts: list[dict] = []
    blocks: list[dict] = []

    # Identité (db_owned)
    if ed.get("pg_id") is not None:
        facts.append({"key": "pg_id", "value": ed["pg_id"], "source_id": "db:pieces_gamme"})
    if ed.get("family"):
        facts.append({"key": "family", "value": str(ed["family"]), "source_id": "db:pieces_gamme"})

    dims = ed.get("dimensions") or {}
    cf = dims.get("compatibility_factors") or {}
    if isinstance(cf, dict) and cf:
        pr = cf.get("power_ps_range") or {}
        yr = cf.get("year_range") or {}
        if cf.get("model_count_distinct") is not None:
            facts.append({"key": "model_count", "value": cf["model_count_distinct"], "source_id": "db:auto_type"})
        if cf.get("fuels"):
            facts.append({"key": "fuels", "value": ", ".join(map(str, cf["fuels"])), "source_id": "db:auto_type"})
        if pr.get("min") is not None and pr.get("max") is not None:
            facts.append({"key": "power_ps_range", "value": f"{pr['min']}-{pr['max']}", "source_id": "db:auto_type"})
        if yr.get("min") is not None and yr.get("max") is not None:
            facts.append({"key": "year_range", "value": f"{yr['min']}-{yr['max']}", "source_id": "db:auto_type"})
        # Bloc compatibilité (projection déterministe, jamais de la prose)
        parts: list[str] = []
        if cf.get("model_count_distinct"):
            parts.append(f"{cf['model_count_distinct']} modèle(s)")
        if cf.get("marques"):
            parts.append("marques : " + ", ".join(str(m).capitalize() for m in cf["marques"]))
        if cf.get("fuels"):
            parts.append("carburants : " + ", ".join(map(str, cf["fuels"])))
        if pr.get("min") is not None:
            parts.append(f"puissance {pr['min']}–{pr['max']} ch")
        if yr.get("min") is not None:
            parts.append(f"années {yr['min']}–{yr['max']}")
        if parts:
            blocks.append({
                "role": "R4_REFERENCE", "section": "compatibility",
                "content_md": "Compatibilité véhicule : " + " · ".join(parts) + ".",
                "source_ids": ["db:auto_type"],
                "truth_level": "db_owned" if cf.get("db_aligned_count") else "inferred",
                "usefulness_target": "compatibilite",
            })

    # Maintenance (éditorial sourcé)
    maint = ed.get("maintenance") or {}
    advice = maint.get("educational_advice") if isinstance(maint, dict) else None
    if advice:
        blocks.append({
            "role": "R3_CONSEILS", "section": "maintenance",
            "content_md": str(advice), "source_ids": [_gamme_source_id(source_refs)],
            "truth_level": "editorial", "usefulness_target": "achat",
        })

    # Maillage interne (db_owned)
    rp = ed.get("related_parts") or []
    if isinstance(rp, list) and rp:
        blocks.append({
            "role": "R4_REFERENCE", "section": "related",
            "content_md": "Pièces de la même famille d'entretien : " + ", ".join(map(str, rp)) + ".",
            "source_ids": ["db:pieces_gamme"], "truth_level": "db_owned",
            "usefulness_target": "maillage",
        })

    # decision_brief (si déjà projeté)
    db_ = ed.get("decision_brief") or {}
    if isinstance(db_, dict):
        crit = db_.get("selection_criteria_top") or []
        if crit:
            blocks.append({
                "role": "R6_GUIDE_ACHAT", "section": "selection",
                "content_md": "Critères de choix : " + " ; ".join(map(str, crit)) + ".",
                "source_ids": ["db:pieces_gamme"], "truth_level": "inferred",
                "usefulness_target": "achat",
            })
        if db_.get("function_oneliner"):
            blocks.append({
                "role": "R4_REFERENCE", "section": "definition",
                "content_md": str(db_["function_oneliner"]),
                "source_ids": ["db:pieces_gamme"], "truth_level": "inferred",
                "usefulness_target": "page_indexable",
            })

    return facts, blocks


def _extract_facts_sources_blocks(
    fm: dict, body: str, entity_type: str
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    **Filter + transform only** : projette le canon WIKI STRUCTURÉ (jamais la prose, ADR-059) en
    facts + blocks role-aware. v1.1.0 (ADR-086) : mappe `entity_data.{dimensions,decision_brief,
    maintenance,related_parts}` par TYPE D'ENTITÉ. LOSSLESS, ZÉRO filler (no silent fallback).
    Aucun enrichissement, aucune génération, aucune lecture de prose body.
    """
    facts: list[dict] = []
    sources: list[dict] = []
    blocks: list[dict] = []

    entity_data = fm.get("entity_data") or {}
    source_refs = fm.get("source_refs") or []

    # Sources : projection depuis `source_refs` frontmatter
    if isinstance(source_refs, list):
        for idx, ref in enumerate(source_refs):
            if not isinstance(ref, dict):
                continue
            kind = ref.get("kind") or ref.get("type") or "manual"
            sources.append({
                "id": ref.get("id") or ref.get("source_id") or f"src-{idx}",
                "type": _normalize_source_type(kind),
                "url": ref.get("url"),
            })

    if isinstance(entity_data, dict):
        # Path historique : facts/blocks déjà structurés dans le canon (rétro-compat)
        raw_facts = entity_data.get("facts")
        if isinstance(raw_facts, list):
            for f in raw_facts:
                if isinstance(f, dict) and "key" in f and "value" in f:
                    facts.append({"key": str(f["key"]), "value": f["value"], "source_id": f.get("source_id")})
        raw_blocks = entity_data.get("blocks")
        if isinstance(raw_blocks, list):
            for b in raw_blocks:
                if not isinstance(b, dict):
                    continue
                role = b.get("role")
                content_md = b.get("content_md") or b.get("content")
                if not role or not content_md:
                    continue
                blocks.append({
                    "role": str(role), "section": b.get("section"),
                    "content_md": str(content_md),
                    "source_ids": list(b.get("source_ids") or []),
                    "truth_level": b.get("truth_level") or "editorial",
                    "usefulness_target": b.get("usefulness_target"),
                })

        # Path v1.1.0 : mapping par type d'entité (le contenu structuré devient projetable)
        if entity_type == "gamme":
            ef, eb = _map_gamme_to_facts_blocks(entity_data, source_refs)
            facts.extend(ef)
            blocks.extend(eb)
            # Path v2.3.0 (ADR-086 §2bis) : sections éditoriales gamme → blocks role-aware
            blocks.extend(_map_gamme_editorial_to_blocks(entity_data))
        elif entity_type == "vehicle":
            # Surface R8 (ADR-086 §1) : known_issues/maintenance PAR MOTORISATION → blocks R8_VEHICLE
            blocks.extend(_map_vehicle_to_blocks(entity_data))
        # (diagnostic: symptoms[]/probable_causes[] — même pattern, ajouté en suite.)

    if not blocks:
        click.echo(
            f"WARN {fm.get('entity_type')}:{fm.get('slug')} — aucun bloc structuré projetable "
            "(0 dimensions/decision_brief/maintenance/related_parts) ; export sans bloc, AUCUN filler généré.",
            err=True,
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
    source_path: Path,
    wiki_root: Path,
    commit_sha: str,
    commit_date: str = _GENERATED_AT_PLACEHOLDER,
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
        # Déterministe : committer-date du dernier commit touchant CETTE fiche
        # (pas d'horloge murale, pas le HEAD bruité) — voir _wiki_file_commit_meta.
        # Deux runs sur le même canon = byte-identiques.
        "generated_at": commit_date,
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
        commit_sha, commit_date = _wiki_file_commit_meta(wiki_root, src)
        payload = build_export(src, wiki_root, commit_sha, commit_date)
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
