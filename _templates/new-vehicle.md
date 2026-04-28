---
schema_version: "1.0.0"
id: "vehicle:<% tp.file.title.toLowerCase().replace(/\s+/g, '-') %>"
entity_type: vehicle
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
  - KB_Catalog
  - KB_Knowledge

entity_data:
  make: ""
  model: ""
  generation: ""
  years: [null, null]
  type_id: 0
  motorizations: []
  vlevel: V5
  low_profile_canary: false
---

# <% tp.file.title %>

> ⚠️ Fiche brouillon. Compléter `make`, `model`, `type_id`, `source_refs`.
> Pour **pilote R8** : positionner `low_profile_canary: true` (PAS Clio/208/Golf).
> Cf ADR-022 vault pour scope DB-only `__rag_proposals` (downstream backend, dormant).

## Présentation

## Motorisations

## Pièces compatibles (top gammes)

## Particularités d'entretien

## Questions fréquentes

## Sources et provenance

(remplir `source_refs:` dans le frontmatter)

## Points à vérifier

- [ ] `source_refs` non vide
- [ ] `type_id` aligné avec DB `__auto_type` (53959 types)
- [ ] `make` slug aligné avec une fiche `wiki/constructeurs/<make>.md`
- [ ] Pas de Clio/208/Golf si pilote R8 stage 2
- [ ] `low_profile_canary` cohérent avec `tier=3` du constructeur
