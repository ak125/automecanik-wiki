---
schema_version: "1.0.0"
id: "support:<% tp.file.title.toLowerCase().replace(/\s+/g, '-') %>"
entity_type: support
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
  category: ""
  audience: client
  faq_questions: []
  policy_refs: []
  legal_reviewed_by: null
---

# <% tp.file.title %>

> ⚠️ Fiche brouillon. **Catégorie obligatoire** dans `entity_data.category` (cf `_meta/enums.yaml#support_categories`).
> Pour `exportable.support: true` (chatbot client) : `legal_reviewed_by` doit être renseigné.

## Résumé

## Détail

## Cas particuliers

## FAQ

(remplir `entity_data.faq_questions[]` dans le frontmatter)

## Sources et provenance

(remplir `source_refs:` — exemple : CGV, mentions légales internes)

## Points à vérifier

- [ ] `category` ∈ `_meta/enums.yaml#support_categories`
- [ ] `audience: client` si destiné au chatbot
- [ ] `legal_reviewed_by` rempli si export prévu
- [ ] Pas de promesse commerciale non validée
- [ ] Pas de donnée interne (paths, IDs internes, etc.)
