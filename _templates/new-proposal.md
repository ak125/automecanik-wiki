---
schema_version: "1.0.0"
id: "<% tp.system.prompt('entity_type (gamme/vehicle/constructeur/support/diagnostic)') %>:<% tp.file.title.toLowerCase().replace(/\s+/g, '-') %>"
entity_type: "<% tp.system.prompt('entity_type') %>"
slug: "<% tp.file.title.toLowerCase().replace(/\s+/g, '-') %>"
title: "<% tp.file.title %>"
aliases: []
lang: fr
created_at: <% tp.date.now("YYYY-MM-DD") %>
updated_at: <% tp.date.now("YYYY-MM-DD") %>

# Truth level initial selon source
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: "knowledge/<% tp.file.title.toLowerCase().replace(/\s+/g, '-') %>.md"
    captured_at: <% tp.date.now("YYYY-MM-DD") %>

provenance:
  ingested_by: "skill:legacy-recycler@v0.4"
  promoted_from: null
  promoted_at: null
lineage_id: null      # généré par lineage-tracker skill au commit
content_hash: null    # calculé par _scripts/compute-content-hash.mjs

parents: []

review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: "Fiche extraite automatiquement, à reviewer humainement avant promotion vers wiki/."
no_disputed_claims: true
quality_score: null

# Tous false par défaut — pas exportable depuis proposals/
exportable:
  rag: false
  seo: false
  support: false

target_classes: []

entity_data:
  # Remplir selon entity_type — voir _meta/schema/entity-data/<type>.schema.json
---

# <% tp.file.title %>

> 📥 **Proposition** — extraite par agent depuis `automecanik-raw/recycled/`.
> À reviewer manuellement avant promotion vers `wiki/<entity_type>/<slug>.md`.

## Résumé proposé

## Faits extraits

## Faits inférés

## Zones ambiguës / contradictions

## Points de review

- [ ] Vérifier `source_refs.origin_path` existe encore
- [ ] Compléter `entity_data` selon le schema entity-data/<type>.schema.json
- [ ] Décider promotion ou rejet (avec note dans `_audit/disputes/` si rejet)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: ...`, `reviewed_at: ...`
- [ ] Le skill `proposal-promoter` (Phase D) automatise la copie vers wiki/<entity_type>/
