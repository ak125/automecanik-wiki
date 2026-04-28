---
schema_version: "1.0.0"
id: "diagnostic:<% tp.file.title.toLowerCase().replace(/\s+/g, '-') %>"
entity_type: diagnostic
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
  - KB_Diagnostic

entity_data:
  system: ""
  symptoms: []
  probable_causes: []
  diagnostic_steps: []
  severity: medium
  audience: client
---

# <% tp.file.title %>

> ⚠️ Fiche brouillon. **Système obligatoire** dans `entity_data.system` (cf `_meta/enums.yaml#diagnostic_systems`).
> Lié aux tables `__diag_*` (13 systèmes, 62 symptômes, 30 ops entretien).

## Symptômes observables

(remplir `entity_data.symptoms[]`)

## Causes probables

(remplir `entity_data.probable_causes[]` ordonnées par fréquence)

## Étapes de diagnostic

(remplir `entity_data.diagnostic_steps[]` ordonnées)

## Gammes liées

## Sévérité

## Sources et provenance

## Points à vérifier

- [ ] `system` ∈ `_meta/enums.yaml#diagnostic_systems`
- [ ] `severity` cohérent (high = stop driving)
- [ ] Pas d'hypothèse présentée comme fait certain
- [ ] `probable_causes` avec `likelihood` et `related_gammes` slugs valides
