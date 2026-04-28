---
schema_version: "1.0.0"
id: "gamme:<% tp.file.title.toLowerCase().replace(/\s+/g, '-') %>"
entity_type: gamme
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
  pg_id: 0
  family: ""
  related_parts: []
  intents: []
  vlevel: V5
  kw_top: []
---

# <% tp.file.title %>

> ⚠️ Fiche brouillon. Compléter `source_refs`, `family`, `pg_id`, puis remplir les sections.
> Ne **PAS** marquer `review_status: approved` sans validation humaine. Voir `_meta/quality-gates.md`.

## Définition

## Fonction

## Symptômes d'usure

## Critères de choix

## Compatibilité véhicule

## Intentions SEO observées

## Questions fréquentes

## Sources et provenance

(remplir `source_refs:` dans le frontmatter)

## Points à vérifier

- [ ] `source_refs` non vide
- [ ] `pg_id` aligné avec DB `__seo_pg_aliases`
- [ ] `family` dans `_meta/enums.yaml`
- [ ] `lineage_id` UUIDv7 généré (par `lineage-tracker` skill, pas à la main)
- [ ] `content_hash` calculé (par script `_scripts/compute-content-hash.mjs`)
