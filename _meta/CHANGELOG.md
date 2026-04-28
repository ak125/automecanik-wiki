# CHANGELOG `_meta/schema`

> Versionnage du schema canonique frontmatter + exports + entity-data.
> Bump majeur (X.0) = breaking change. Bump mineur (X.Y) = ajout rétrocompatible. Bump patch (X.Y.Z) = clarification.

## \[1.0.0\] — 2026-04-28 (Phase B.2)

Premier schema canonique livré. État de référence pour migration des 4650 fiches existantes (95.7% sans `source_refs`) en mode `schema_version: "0.legacy"` puis bump vers `1.0.0` après validation.

**Schemas JSON livrés** :

- `_meta/schema/frontmatter.schema.json` — schema racine, 5 blocs (core / traceability / quality / export-gates / entity_data)
  - `id` URN-style `<entity_type>:<slug>`
  - `truth_level` enum L1-L4 (PAS L0, aligné `rag_config.yml` weights)
  - `source_refs` typés (kind: raw | external_url | manual | recycled)
  - `lineage_id` UUIDv7 + `content_hash` SHA-256 body-only
  - `exportable.{rag,seo,support}` gates par audience
  - Conditional rules : truth_level L1-L3 ⇒ source_refs minItems=1 ; exportable=true ⇒ review_status=approved + reviewed_by + no_disputed_claims=true
- `_meta/schema/entity-data/gamme.schema.json` — pg_id, family, intents, vlevel, kw_top
- `_meta/schema/entity-data/vehicle.schema.json` — make, model, generation, type_id, motorizations, low_profile_canary
- `_meta/schema/entity-data/constructeur.schema.json` — name, country, founded, brand_aliases, models, tier
- `_meta/schema/entity-data/support.schema.json` — category, audience, faq_questions, legal_reviewed_by
- `_meta/schema/entity-data/diagnostic.schema.json` — system, symptoms, probable_causes, severity
- `_meta/schema/exports/rag.schema.json` — manifest contrat `wiki_ingester.py`
- `_meta/schema/exports/seo.schema.json` — JSON-LD Schema.org typés
- `_meta/schema/exports/support.schema.json` — chatbot client filtré

**Enums centralisés** : `_meta/enums.yaml`

- truth_levels, review_status, entity_types, target_classes (Weaviate)
- families (22 catégories métier), intents, vlevels, support_categories, diagnostic_systems
- source_kinds

**Templates Obsidian** : `_templates/new-{gamme,vehicle,constructeur,support,diagnostic,proposal}.md`

- Templater-compatible (`<% tp.file.title %>`, `<% tp.date.now() %>`)
- Frontmatter pré-rempli avec valeurs sûres (`review_status: draft`, `exportable.*: false`, `truth_level: L4`)
- Checklist de review intégrée

**Versions futures prévues** :

- v1.1 : extension `target_classes` si `namespace_guard.py` rag/ ajoute `KB_Constructeur` (PR rag/ pending)
- v1.0.1+ : clarifications / typos
- v2.0 : breaking change (ex: refactor `provenance` ou `lineage_id` format)

## \[0.0.1\] — 2026-04-28 (Phase 1+3)

- Squelette initial pushed (commit `e57218f9`)
- Structure layout v1 (4 layers raw → wiki → exports → consumers)
- `_meta/quality-gates.md`, `source-policy.md`, `ingestion-contract.md`, `entity-registry.json`, `agent-exit-contract.md`

## Politique de bump

- Avant publication d'une nouvelle version : entrée dans ce changelog avec date + détail
- Toute fiche existante doit indiquer son `schema_version` dans le frontmatter
- Migration majeure : script `_scripts/migrate-schema-vX-to-vY.mjs` obligatoire
- Version `0.legacy` réservée aux 4650 fiches importées de `automecanik-rag/knowledge/` (95.7% sans `source_refs`)
