---
schema_version: "1.0.0"
id: "constructeur:<% tp.file.title.toLowerCase().replace(/\s+/g, '-') %>"
entity_type: constructeur
slug: "<% tp.file.title.toLowerCase().replace(/\s+/g, '-') %>"
title: "<% tp.file.title %>"
aliases: []
lang: fr
created_at: <% tp.date.now("YYYY-MM-DD") %>
updated_at: <% tp.date.now("YYYY-MM-DD") %>

truth_level: L4
source_refs: []
provenance:
  ingested_by: "human:@fafa"
  promoted_from: null
  promoted_at: null
lineage_id: null
content_hash: null
parents: []

review_status: draft
reviewed_by: null
reviewed_at: null
review_notes: ""
no_disputed_claims: true
quality_score: null

exportable:
  rag: false
  seo: false
  support: false
target_classes:
  - KB_Knowledge

entity_data:
  name: "<% tp.file.title %>"
  country: ""
  founded: 1900
  brand_aliases: []
  models: []
  tier: 3
  vlevel: V5
---

# <% tp.file.title %>

> ⚠️ Fiche brouillon. Compléter `country`, `founded`, `tier`, `models`, `source_refs`.
> Pour **pilote R7** : choisir un constructeur tier 3 (Skoda, Seat, Dacia).

## Histoire

## Gamme actuelle

## Modèles couverts par le catalogue

## Pièces les plus demandées

## Sources et provenance

(remplir `source_refs:` dans le frontmatter)

## Points à vérifier

- [ ] `source_refs` non vide (méfiance des sources US/UK — site FR)
- [ ] `tier` cohérent business
- [ ] `models` slugs alignés avec `wiki/vehicles/<model>.md`
- [ ] `brand_aliases` couvrent les variantes commerciales (ex: 'VW' pour 'volkswagen')
