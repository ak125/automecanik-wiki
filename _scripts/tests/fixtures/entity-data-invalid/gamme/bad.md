---
# FIXTURE NÉGATIVE — ne jamais promouvoir, ne jamais exporter.
# Le frontmatter ci-dessous est VALIDE au regard de _meta/schema/frontmatter.schema.json ;
# seul le bloc `entity_data` viole _meta/schema/entity-data/gamme.schema.json, et
# volontairement, de trois façons évidentes et indépendantes :
#
#   1. pg_id: 0            → viole `minimum: 1` (properties.pg_id.minimum)
#   2. family: "Filtration" → viole `pattern: ^[a-z][a-z-]*[a-z]$` (majuscule interdite)
#   3. champ_inexistant     → viole `additionalProperties: false` (racine du schéma gamme)
#
# Cette fixture est la PREUVE NÉGATIVE de la résolution des schémas entity-data :
# tant que `ajv.getSchema()` ne retrouvait pas gamme.schema.json, ce fichier passait
# avec 0 erreur. Si un jour il repasse, la résolution est de nouveau cassée.
schema_version: 2.0.0
id: gamme:bad
entity_type: gamme
slug: bad
title: Fixture négative entity_data (gamme)
lang: fr
created_at: '2026-09-16'
updated_at: '2026-09-16'
truth_level: L4
review_status: draft
exportable:
  rag: false
  seo: false
  support: false
entity_data:
  pg_id: 0
  family: Filtration
  champ_inexistant: true
---

# Fixture négative — entity_data invalide (gamme)

Fichier de test consommé par `.github/workflows/lint.yml` (job `validate-frontmatter`)
et par `_scripts/validate-frontmatter.mjs --strict-entity-data`. Aucun contenu éditorial.
