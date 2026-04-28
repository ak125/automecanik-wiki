# CHANGELOG `_meta/schema`

> Versionnage du schema canonique frontmatter + exports + entity-data.
> Bump majeur (X.0) = breaking change. Bump mineur (X.Y) = ajout rétrocompatible. Bump patch (X.Y.Z) = clarification.

## [unreleased]

À livrer Phase B :
- `_meta/schema/frontmatter.schema.json` v1.0.0 — JSON Schema 5 blocs (core / traceability / quality / export-gates / entity_data)
- `_meta/schema/entity-data/{gamme,vehicle,constructeur,support,diagnostic}.schema.json` v1.0.0
- `_meta/schema/exports/{rag,seo,support}.schema.json` v1.0.0
- `_meta/enums.yaml` v1.0.0 (truth_level, target_classes Weaviate, families, intents, segments)

## [0.0.1] — 2026-04-28

- Squelette initial pushed (commit `e57218f9`)
- Structure layout v1 (4 layers raw → wiki → exports → consumers)
- `_meta/quality-gates.md`, `source-policy.md`, `ingestion-contract.md`, `entity-registry.json`, `agent-exit-contract.md`

## Politique de bump

- Avant publication d'une nouvelle version : entrée dans ce changelog avec date + détail
- Toute fiche existante doit indiquer son `schema_version` dans le frontmatter
- Migration majeure : script `_scripts/migrate-schema-vX-to-vY.mjs` obligatoire
- Version `0.legacy` réservée aux 4650 fiches importées de `automecanik-rag/knowledge/` (95.7% sans `source_refs`)
