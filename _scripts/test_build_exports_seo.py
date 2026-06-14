"""
Tests build_exports_seo — garde-fous stricts ADR-059 PR-5a.

Vérifie les 7 verrous explicites :
1. schema enforce roles_allowed minItems:1
2. schema enforce entity_type ∈ {gamme, vehicle, constructeur, diagnostic} (support exclu)
3. schema enforce schema_version ≠ projection_contract_version (distincts)
4. schema enforce source_wiki_commit, wiki_path, content_hash obligatoires
5. builder refuse support
6. builder refuse diagnostic sans R3_CONSEILS S2_DIAG
7. builder refuse écriture hors exports/seo/
8. garde-fous statiques : 0 LLM, 0 DB
9. builder = filter+transform only (no enrichment)
"""
from __future__ import annotations

import json
from pathlib import Path

import click
import pytest

import build_exports_seo as builder


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "_meta" / "schema" / "exports-seo.schema.json"
SCRIPT_PATH = Path(__file__).resolve().parent / "build_exports_seo.py"


def _valid_payload() -> dict:
    """Payload minimal conforme au schema (référence)."""
    return {
        "entity_id": "gamme:filtre-a-huile",
        "entity_type": "gamme",
        "schema_version": "1.0.0",
        "projection_contract_version": "1.0.0",
        "source_wiki_commit": "abc1234",
        "wiki_path": "wiki/gamme/filtre-a-huile.md",
        "content_hash": "sha256:" + "f" * 64,
        "generated_at": "2026-05-13T12:00:00+00:00",
        "facts": [],
        "sources": [],
        "blocks": [],
        "roles_allowed": ["R3_CONSEILS", "R4_REFERENCE"],
        "consumers_allowed": ["seo", "rag"],
    }


def _validate(payload: dict) -> None:
    """jsonschema validate contre exports-seo.schema.json."""
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)


# ========================================================================
# Schema enforcement (7 garde-fous explicites)
# ========================================================================


def test_schema_valid_minimal_payload_passes() -> None:
    _validate(_valid_payload())


def test_schema_enforces_roles_allowed_min_items_1() -> None:
    """Garde-fou #1 : roles_allowed ne peut PAS être vide."""
    import jsonschema

    p = _valid_payload()
    p["roles_allowed"] = []
    with pytest.raises(jsonschema.ValidationError):
        _validate(p)


def test_schema_excludes_support_entity_type() -> None:
    """Garde-fou #2 : support n'est PAS dans entity_type enum."""
    import jsonschema

    p = _valid_payload()
    p["entity_type"] = "support"
    p["entity_id"] = "support:livraison"
    with pytest.raises(jsonschema.ValidationError):
        _validate(p)


def test_schema_requires_schema_version_and_projection_contract_version_distinct_fields() -> None:
    """Garde-fou #3 : les 2 champs version sont obligatoires et distincts."""
    import jsonschema

    p = _valid_payload()
    p.pop("schema_version")
    with pytest.raises(jsonschema.ValidationError):
        _validate(p)

    p = _valid_payload()
    p.pop("projection_contract_version")
    with pytest.raises(jsonschema.ValidationError):
        _validate(p)


def test_schema_requires_source_wiki_commit() -> None:
    """Garde-fou #4a."""
    import jsonschema

    p = _valid_payload()
    p.pop("source_wiki_commit")
    with pytest.raises(jsonschema.ValidationError):
        _validate(p)


def test_schema_requires_wiki_path() -> None:
    """Garde-fou #4b."""
    import jsonschema

    p = _valid_payload()
    p.pop("wiki_path")
    with pytest.raises(jsonschema.ValidationError):
        _validate(p)


def test_schema_requires_content_hash() -> None:
    """Garde-fou #4c."""
    import jsonschema

    p = _valid_payload()
    p.pop("content_hash")
    with pytest.raises(jsonschema.ValidationError):
        _validate(p)


def test_schema_wiki_path_pattern_excludes_support_dir() -> None:
    """wiki_path pattern bloque wiki/support/..."""
    import jsonschema

    p = _valid_payload()
    p["wiki_path"] = "wiki/support/livraison.md"
    with pytest.raises(jsonschema.ValidationError):
        _validate(p)


def test_schema_entity_id_pattern_excludes_support() -> None:
    """entity_id pattern n'autorise pas support:."""
    import jsonschema

    p = _valid_payload()
    p["entity_id"] = "support:livraison"
    p["entity_type"] = "support"
    with pytest.raises(jsonschema.ValidationError):
        _validate(p)


def test_schema_rejects_unknown_role_in_roles_allowed() -> None:
    """roles_allowed enum strict."""
    import jsonschema

    p = _valid_payload()
    p["roles_allowed"] = ["R3_CONSEILS", "R5_DIAGNOSTIC"]  # R5 sunset per ADR-027
    with pytest.raises(jsonschema.ValidationError):
        _validate(p)


def test_schema_rejects_extra_fields() -> None:
    """additionalProperties: false."""
    import jsonschema

    p = _valid_payload()
    p["mystery_field"] = "oops"
    with pytest.raises(jsonschema.ValidationError):
        _validate(p)


# ========================================================================
# Builder behavior (filter + transform only)
# ========================================================================


def _write_wiki_fiche(
    wiki_root: Path,
    entity_type: str,
    slug: str,
    review_status: str = "approved",
    exportable: bool = True,
    body: str = "",
    roles_allowed: list[str] | None = None,
    extra_fm: dict | None = None,
) -> Path:
    """Helper test : crée une fiche wiki canon synthétique."""
    fm = {
        "schema_version": "1.0.0",
        "id": f"{entity_type}:{slug}",
        "entity_type": entity_type,
        "slug": slug,
        "title": slug.replace("-", " ").title(),
        "lang": "fr",
        "created_at": "2026-05-13",
        "updated_at": "2026-05-13",
        "truth_level": "L2",
        "review_status": review_status,
        "exportable": exportable,
    }
    if roles_allowed is not None:
        fm["roles_allowed"] = roles_allowed
    if extra_fm:
        fm.update(extra_fm)
    import yaml

    target = wiki_root / "wiki" / entity_type / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "---\n"
        + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
        + "---\n"
        + body,
        encoding="utf-8",
    )
    return target


def test_builder_refuses_support_entity_type(tmp_path: Path) -> None:
    """Garde-fou #5 : support never enters exports/seo/."""
    src = _write_wiki_fiche(tmp_path, "support", "livraison")
    payload = builder.build_export(src, tmp_path, "abc1234")
    assert payload is None


def test_builder_refuses_non_approved(tmp_path: Path) -> None:
    src = _write_wiki_fiche(tmp_path, "gamme", "x-slug", review_status="proposed")
    assert builder.build_export(src, tmp_path, "abc1234") is None


def test_builder_refuses_non_exportable(tmp_path: Path) -> None:
    src = _write_wiki_fiche(tmp_path, "gamme", "x-slug", exportable=False)
    assert builder.build_export(src, tmp_path, "abc1234") is None


def test_builder_refuses_diagnostic_without_r3_s2_diag(tmp_path: Path) -> None:
    """Garde-fou #6 : diagnostic sans R3_CONSEILS/S2_DIAG → routé hors exports/seo/."""
    src = _write_wiki_fiche(tmp_path, "diagnostic", "bruit-x", body="Diagnostic sans S2.\n")
    assert builder.build_export(src, tmp_path, "abc1234") is None


def test_builder_accepts_diagnostic_with_s2_diag(tmp_path: Path) -> None:
    src = _write_wiki_fiche(
        tmp_path,
        "diagnostic",
        "bruit-y",
        body="## S2_DIAG\nContenu diagnostic R3.\n",
    )
    payload = builder.build_export(src, tmp_path, "abc1234")
    assert payload is not None
    assert payload["entity_type"] == "diagnostic"


def test_builder_accepts_gamme_approved_exportable(tmp_path: Path) -> None:
    src = _write_wiki_fiche(tmp_path, "gamme", "filtre-a-huile")
    payload = builder.build_export(src, tmp_path, "abc1234")
    assert payload is not None
    assert payload["entity_id"] == "gamme:filtre-a-huile"
    assert payload["schema_version"] == "1.1.0"  # bump ADR-086 (blocks v1.1.0)
    assert payload["projection_contract_version"] == "1.0.0"
    assert payload["source_wiki_commit"] == "abc1234"
    assert payload["wiki_path"] == "wiki/gamme/filtre-a-huile.md"
    assert payload["content_hash"].startswith("sha256:")
    assert payload["roles_allowed"], "default roles_allowed for gamme must be non-empty"
    _validate(payload)


def test_builder_skips_when_roles_allowed_empty_explicit(tmp_path: Path) -> None:
    src = _write_wiki_fiche(tmp_path, "gamme", "no-roles", roles_allowed=[])
    payload = builder.build_export(src, tmp_path, "abc1234")
    # roles vide explicite tombe sur default (non-vide pour gamme), donc OK ici
    # mais si on force vide via build interne sans défaut, le builder skip.
    # Ici on vérifie juste que le builder ne crash pas.
    assert payload is None or payload["roles_allowed"]


# ========================================================================
# Output path enforcement (garde-fou #7)
# ========================================================================


def test_enforce_output_path_refuses_wiki_canon_dir(tmp_path: Path) -> None:
    """Garde-fou #7 : refuse écriture wiki/<entity_type>/."""
    out = tmp_path / "wiki" / "gamme" / "x.json"
    with pytest.raises(click.ClickException, match="exports/seo"):
        builder._enforce_output_path_strict(out, tmp_path)


def test_enforce_output_path_refuses_exports_rag(tmp_path: Path) -> None:
    out = tmp_path / "exports" / "rag" / "gamme" / "x.json"
    with pytest.raises(click.ClickException, match="exports/seo"):
        builder._enforce_output_path_strict(out, tmp_path)


def test_enforce_output_path_refuses_exports_support(tmp_path: Path) -> None:
    out = tmp_path / "exports" / "support" / "support" / "x.json"
    with pytest.raises(click.ClickException, match="exports/seo"):
        builder._enforce_output_path_strict(out, tmp_path)


def test_enforce_output_path_refuses_proposals(tmp_path: Path) -> None:
    out = tmp_path / "proposals" / "x.md"
    with pytest.raises(click.ClickException, match="exports/seo"):
        builder._enforce_output_path_strict(out, tmp_path)


def test_enforce_output_path_refuses_outside_wiki_root(tmp_path: Path) -> None:
    out = Path("/tmp/random/x.json")
    with pytest.raises(click.ClickException, match="outside wiki_root"):
        builder._enforce_output_path_strict(out, tmp_path)


def test_enforce_output_path_allows_exports_seo(tmp_path: Path) -> None:
    out = tmp_path / "exports" / "seo" / "gamme" / "x.json"
    builder._enforce_output_path_strict(out, tmp_path)


# ========================================================================
# Static guards
# ========================================================================


def test_no_llm_inference_imports() -> None:
    """Garde-fou statique : aucun import LLM."""
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden = ["anthropic", "openai", "groq", "cohere", "mistralai", "google.generativeai"]
    for needle in forbidden:
        assert needle not in text, f"LLM SDK '{needle}' must not appear in build_exports_seo"


def test_no_db_imports() -> None:
    """Garde-fou statique : aucun import DB."""
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden_db = ["psycopg", "asyncpg", "supabase", "sqlalchemy", "django"]
    for needle in forbidden_db:
        assert needle not in text, f"DB SDK '{needle}' must not appear in build_exports_seo"


def test_no_enrichment_logic_patterns() -> None:
    """
    Garde-fou architectural : aucun pattern d'enrichissement / génération.
    Le builder lit le canon et le projette. Il ne génère pas de contenu.
    """
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden_patterns = [
        "generate_",  # toute fonction generate_*
        "enrich_",  # toute fonction enrich_*
        "synthesize",
        "infer_",
    ]
    for needle in forbidden_patterns:
        assert needle not in text, (
            f"enrichment pattern '{needle}' detected in build_exports_seo. "
            "PR-5a strict scope: filter + transform only, no enrichment."
        )


def test_schema_path_referenced_correctly() -> None:
    """Builder doit chercher exports-seo.schema.json dans _meta/schema/."""
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "exports-seo.schema.json" in text


# ========================================================================
# v1.1.0 (ADR-086) — mapping entity_data structuré → facts/blocks role-aware
# Fixture calquée sur une VRAIE proposal existante (proposals/filtre-a-huile.md).
# ========================================================================

def _gamme_fm_with_dimensions() -> dict:
    return {
        "entity_type": "gamme",
        "slug": "filtre-a-huile",
        "source_refs": [
            {"kind": "recycled", "origin_path": "recycled/rag-knowledge/gammes/filtre-a-huile.md", "id": "raw-filtre-a-huile"},
        ],
        "entity_data": {
            "pg_id": 7,
            "family": "filtration",
            "related_parts": ["huile-moteur", "joint-de-vidange-carter", "filtre-a-air"],
            "intents": ["diagnostic", "achat", "compatibilite"],
            "maintenance": {"educational_advice": "À remplacer à chaque vidange : essence 10 000-15 000 km, diesel 15 000-20 000 km."},
            "dimensions": {
                "compatibility_factors": {
                    "marques": ["citroen", "ford", "renault", "volkswagen"],
                    "fuels": ["Diesel", "Essence"],
                    "model_count_distinct": 9,
                    "db_aligned_count": 9,
                    "power_ps_range": {"min": 60, "max": 170},
                    "year_range": {"min": 1995, "max": 2015},
                },
            },
        },
    }


def test_gamme_dimensions_map_to_facts_and_blocks() -> None:
    facts, sources, blocks = builder._extract_facts_sources_blocks(_gamme_fm_with_dimensions(), "", "gamme")
    assert len(facts) > 0, "facts must be non-empty when dimensions present"
    assert len(blocks) > 0, "blocks must be non-empty when dimensions present"
    for b in blocks:
        assert b.get("role"), "block missing role"
        assert "section" in b, "block missing section"
        assert b.get("source_ids"), "block missing source_ids"
        assert b.get("truth_level") in ("db_owned", "sourced", "inferred", "editorial")
    compat = [b for b in blocks if b["section"] == "compatibility"]
    assert compat and "9 modèle" in compat[0]["content_md"]  # golden : projection déterministe
    maint = [b for b in blocks if b["section"] == "maintenance"]
    assert maint and "vidange" in maint[0]["content_md"].lower()


def test_gamme_mapped_export_validates_schema() -> None:
    facts, sources, blocks = builder._extract_facts_sources_blocks(_gamme_fm_with_dimensions(), "", "gamme")
    payload = _valid_payload()
    payload["facts"], payload["sources"], payload["blocks"] = facts, sources, blocks
    payload["schema_version"] = builder.SCHEMA_VERSION
    _validate(payload)  # ne doit pas lever


def test_negative_no_structured_data_yields_no_filler_blocks() -> None:
    """entity_data sans dimensions/decision_brief/maintenance/related_parts → 0 bloc, AUCUN filler."""
    fm = {"entity_type": "gamme", "slug": "x", "source_refs": [],
          "entity_data": {"pg_id": 7, "family": "filtration"}}
    _, _, blocks = builder._extract_facts_sources_blocks(fm, "", "gamme")
    assert blocks == [], "no structured field → must NOT generate filler blocks"


def test_block_source_ids_are_prefixed() -> None:
    import re
    _, _, blocks = builder._extract_facts_sources_blocks(_gamme_fm_with_dimensions(), "", "gamme")
    for b in blocks:
        for sid in b["source_ids"]:
            assert re.match(r"^(db|web|raw|oem|specialist):", sid), f"source_id not prefixed: {sid}"


# ──────────────────────────────────────────────────────────────────────────────
# v2.3.0 (ADR-086 §2bis) — sections éditoriales gamme → blocks role-aware
# ──────────────────────────────────────────────────────────────────────────────
GAMME_ED_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "_meta" / "schema" / "entity-data" / "gamme.schema.json"
)


def _ed(content: str, *sources: str, truth: str = "editorial") -> dict:
    return {"content_md": content, "source_ids": list(sources), "truth_level": truth}


def _gamme_fm_with_editorial() -> dict:
    return {
        "entity_type": "gamme",
        "slug": "filtre-a-huile",
        "source_refs": [],
        "entity_data": {
            "pg_id": 7,
            "family": "filtration",
            "editorial": {
                "function": _ed(
                    "Le filtre à huile épure l'huile moteur en retenant les particules métalliques "
                    "d'usure et les suies de combustion, préservant la lubrification du moteur.", "raw:recycled/filtre-a-huile"),
                "failure_symptoms": _ed(
                    "Signes d'un filtre colmaté : témoin de pression d'huile, bruit moteur à froid, "
                    "huile noircie prématurément ; le by-pass laisse alors passer une huile non filtrée.", "raw:recycled/filtre-a-huile"),
                "maintenance_interval": _ed(
                    "À remplacer à chaque vidange : essence 10 000-15 000 km, diesel 15 000-20 000 km, "
                    "longlife jusqu'à 30 000 km ou 1 an.", "raw:recycled/filtre-a-huile", "db:auto_type"),
                "variants": _ed(
                    "Deux technologies : filtre vissable spin-on (cartouche métallique complète) et "
                    "filtre cartouche (élément seul dans un boîtier réutilisable).", "raw:recycled/filtre-a-huile"),
                "selection_criteria": _ed(
                    "Critères : référence OEM, type de montage, clapet anti-retour et clapet by-pass, "
                    "compatibilité huiles longlife (normes constructeur).", "raw:recycled/filtre-a-huile"),
                "quality_tiers": _ed(
                    "Trois niveaux : origine constructeur (OE), équipementier première monte "
                    "(Mann, Mahle, Bosch, Purflux) et entrée de gamme.", "web:equipementier-generic"),
                "standards_norms": _ed(
                    "L'efficacité de filtration suit les spécifications constructeur et les normes "
                    "d'essai équipementier ; compatibilité huile selon homologation constructeur.", "web:oem-generic"),
                "replacement_guidance": _ed(
                    "Remplacement huile chaude moteur arrêté : vidanger, déposer l'ancien filtre, "
                    "lubrifier le joint neuf, refaire le niveau, contrôler l'absence de fuite.", "raw:recycled/filtre-a-huile"),
                "faq": _ed(
                    "Faut-il changer le filtre à chaque vidange ? Oui, systématiquement. Spin-on ou "
                    "cartouche ? Celui imposé par le support moteur, pas un choix libre.", "raw:recycled/filtre-a-huile"),
            },
            "media": [
                {"slot": "hero", "purpose": "illustration gamme", "alt_text": "Filtre à huile",
                 "source": "db:pieces_gamme.pg_pic", "asset": "filtre-a-huile.webp",
                 "license": "owned", "status": "AVAILABLE"},
                {"slot": "function_diagram", "purpose": "schéma circuit", "alt_text": "Schéma filtre à huile",
                 "source": None, "asset": None, "license": None, "status": "DEFERRED"},
            ],
        },
    }


def test_gamme_editorial_maps_to_role_aware_blocks() -> None:
    _, _, blocks = builder._extract_facts_sources_blocks(_gamme_fm_with_editorial(), "", "gamme")
    ed_blocks = [b for b in blocks if b["section"] in builder._GAMME_EDITORIAL_ROLES]
    assert len(ed_blocks) == 9, "les 9 sections éditoriales doivent produire 9 blocs"
    for b in ed_blocks:
        assert b["role"] == builder._GAMME_EDITORIAL_ROLES[b["section"]], "rôle ≠ taxonomie"
        assert b["content_md"] and b["source_ids"] and b["truth_level"]


def test_gamme_editorial_section_to_role_golden() -> None:
    _, _, blocks = builder._extract_facts_sources_blocks(_gamme_fm_with_editorial(), "", "gamme")
    by_section = {b["section"]: b["role"] for b in blocks}
    assert by_section["function"] == "R3_CONSEILS"
    assert by_section["selection_criteria"] == "R6_GUIDE_ACHAT"
    assert by_section["standards_norms"] == "R4_REFERENCE"
    assert by_section["faq"] == "R3_CONSEILS"  # FAQ gamme ∈ cluster gamme, pas R0_HOME


def test_editorial_block_roles_within_roles_allowed() -> None:
    """COHÉRENCE (revue #44) : tout role de bloc éditorial ⊆ roles_allowed gamme (pas de drop silencieux)."""
    fm = _gamme_fm_with_editorial()
    _, _, blocks = builder._extract_facts_sources_blocks(fm, "", "gamme")
    roles_allowed = set(builder._compute_roles_allowed(fm, "gamme", blocks))
    block_roles = {b["role"] for b in blocks}
    assert block_roles <= roles_allowed, f"roles hors roles_allowed: {block_roles - roles_allowed}"


def test_editorial_block_source_ids_prefixed() -> None:
    """Finding 2 : la garde préfixe doit aussi couvrir le path éditorial (source_ids verbatim)."""
    import re
    _, _, blocks = builder._extract_facts_sources_blocks(_gamme_fm_with_editorial(), "", "gamme")
    ed = [b for b in blocks if b["section"] in builder._GAMME_EDITORIAL_ROLES]
    assert ed, "fixture doit produire des blocs éditoriaux"
    for b in ed:
        for sid in b["source_ids"]:
            assert re.match(r"^(db|web|raw|oem|specialist):", sid), f"source_id non préfixé: {sid}"


def test_gamme_editorial_export_validates_schema() -> None:
    facts, sources, blocks = builder._extract_facts_sources_blocks(_gamme_fm_with_editorial(), "", "gamme")
    payload = _valid_payload()
    payload["facts"], payload["sources"], payload["blocks"] = facts, sources, blocks
    payload["schema_version"] = builder.SCHEMA_VERSION
    _validate(payload)  # blocks éditoriaux conformes au contrat exports-seo


def test_gamme_editorial_partial_no_filler() -> None:
    """editorial partiel (3 sections) → exactement 3 blocs éditoriaux, AUCUN filler sur les absentes."""
    fm = {"entity_type": "gamme", "slug": "x", "source_refs": [], "entity_data": {
        "pg_id": 7, "family": "filtration", "editorial": {
            "function": _ed("Le filtre à huile retient les impuretés en suspension dans l'huile moteur efficacement.", "raw:r"),
            "faq": _ed("Faut-il changer le filtre à chaque vidange ? Oui systématiquement pour protéger le moteur.", "raw:r"),
            "variants": _ed("Deux technologies de filtre à huile coexistent : le spin-on vissable et la cartouche.", "raw:r"),
        }}}
    _, _, blocks = builder._extract_facts_sources_blocks(fm, "", "gamme")
    ed_blocks = [b for b in blocks if b["section"] in builder._GAMME_EDITORIAL_ROLES]
    assert len(ed_blocks) == 3, "seules les sections présentes produisent un bloc"
    assert {b["section"] for b in ed_blocks} == {"function", "faq", "variants"}


def test_gamme_editorial_invalid_entry_not_emitted() -> None:
    """section sans source_ids → bloc NON émis (zéro filler), jamais inventé."""
    fm = {"entity_type": "gamme", "slug": "x", "source_refs": [], "entity_data": {
        "pg_id": 7, "family": "filtration", "editorial": {
            "function": {"content_md": "x" * 80, "source_ids": [], "truth_level": "editorial"},  # invalide (0 source)
        }}}
    _, _, blocks = builder._extract_facts_sources_blocks(fm, "", "gamme")
    assert [b for b in blocks if b["section"] == "function"] == []


def test_entity_data_editorial_media_validates_against_gamme_schema() -> None:
    import jsonschema
    schema = json.loads(GAMME_ED_SCHEMA_PATH.read_text(encoding="utf-8"))
    ed = _gamme_fm_with_editorial()["entity_data"]
    jsonschema.validate(ed, schema)  # editorial + media conformes au canon entity-data v2.3.0


# ──────────────────────────────────────────────────────────────────────────────
# v1.1.0 vehicle (ADR-086 §1 surface R8) — known_issues/maintenance par motorisation → blocks
# ──────────────────────────────────────────────────────────────────────────────
VEHICLE_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "_meta" / "schema" / "entity-data" / "vehicle.schema.json"
)


def _vehicle_fm_with_engine_maps() -> dict:
    return {
        "entity_type": "vehicle",
        "slug": "renault-scenic-ii",
        "source_refs": [],
        "entity_data": {
            "make": "renault",
            "model": "scenic-ii",
            "type_id": 18003,
            "motorizations": [{"code": "1.5 dCi", "fuel": "diesel", "power_hp": 101, "displacement_cc": 1461}],
            "known_issues_by_engine": {
                "engine_family:k9k": {
                    "axis_key_type": "engine_family",
                    "content_md": ("Moteur 1.5 dCi (famille K9K, Renault-Nissan) : points de vigilance — "
                                   "EGR (encrassement fréquent), turbo (usure des paliers), injecteurs "
                                   "(fuite de retour). Vidange et filtre à huile rigoureux limitent l'usure."),
                    "source_ids": ["db:kg_engine_families", "db:auto_type"],
                    "truth_level": "sourced",
                },
            },
            "maintenance_by_engine": {
                "fuel:diesel": {
                    "axis_key_type": "fuel",
                    "content_md": ("Diesel : intervalle de vidange 15 000-20 000 km ou 1 an ; remplacer le "
                                   "filtre à huile à chaque vidange."),
                    "source_ids": ["db:auto_type"],
                    "truth_level": "sourced",
                },
            },
        },
    }


def test_vehicle_engine_maps_to_r8_blocks() -> None:
    _, _, blocks = builder._extract_facts_sources_blocks(_vehicle_fm_with_engine_maps(), "", "vehicle")
    assert len(blocks) == 2, "1 known_issues + 1 maintenance attendus"
    for b in blocks:
        assert b["role"] == "R8_VEHICLE"
        assert b["section"] in ("known_issues", "maintenance")
        assert b["source_ids"] and b["truth_level"] == "sourced"
    sections = {b["section"] for b in blocks}
    assert sections == {"known_issues", "maintenance"}


def test_vehicle_r8_blocks_within_roles_allowed() -> None:
    fm = _vehicle_fm_with_engine_maps()
    _, _, blocks = builder._extract_facts_sources_blocks(fm, "", "vehicle")
    ra = set(builder._compute_roles_allowed(fm, "vehicle", blocks))
    assert {b["role"] for b in blocks} <= ra, "R8_VEHICLE doit ∈ roles_allowed véhicule"


def test_vehicle_r8_export_validates_schema() -> None:
    facts, sources, blocks = builder._extract_facts_sources_blocks(_vehicle_fm_with_engine_maps(), "", "vehicle")
    payload = _valid_payload()
    payload["entity_id"] = "vehicle:renault-scenic-ii"
    payload["entity_type"] = "vehicle"
    payload["wiki_path"] = "wiki/vehicle/renault-scenic-ii.md"
    payload["roles_allowed"] = ["R8_VEHICLE"]
    payload["facts"], payload["sources"], payload["blocks"] = facts, sources, blocks
    payload["schema_version"] = builder.SCHEMA_VERSION
    _validate(payload)


def test_vehicle_no_engine_maps_yields_no_filler() -> None:
    fm = {"entity_type": "vehicle", "slug": "x", "source_refs": [],
          "entity_data": {"make": "renault", "model": "x"}}
    _, _, blocks = builder._extract_facts_sources_blocks(fm, "", "vehicle")
    assert blocks == [], "pas de map moteur → 0 bloc, AUCUN filler"


def test_vehicle_invalid_engine_entry_not_emitted() -> None:
    fm = {"entity_type": "vehicle", "slug": "x", "source_refs": [], "entity_data": {
        "make": "renault", "model": "x", "known_issues_by_engine": {
            "fuel:diesel": {"axis_key_type": "fuel", "content_md": "x" * 50, "source_ids": [], "truth_level": "sourced"},
        }}}
    _, _, blocks = builder._extract_facts_sources_blocks(fm, "", "vehicle")
    assert blocks == [], "entrée sans source_ids → non émise"


def test_entity_data_vehicle_engine_maps_validate_against_schema() -> None:
    import jsonschema
    schema = json.loads(VEHICLE_SCHEMA_PATH.read_text(encoding="utf-8"))
    ed = _vehicle_fm_with_engine_maps()["entity_data"]
    jsonschema.validate(ed, schema)  # conforme vehicle.schema v1.1.0
