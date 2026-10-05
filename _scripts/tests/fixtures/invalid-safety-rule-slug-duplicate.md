---
schema_version: 2.0.0
id: diagnostic:regles-securite
entity_type: diagnostic
slug: regles-securite
title: Règles de sécurité (fixture)
aliases: []
lang: fr
created_at: '2026-10-05'
updated_at: '2026-10-05'
truth_level: L2
source_refs:
  - kind: manual
    note: fixture
    author: test
provenance:
  ingested_by: 'human:fixture'
  promoted_from: null
review_status: draft
reviewed_by: null
reviewed_at: null
review_notes: ''
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: [KB_Knowledge]
safety_rules:
  - rule_slug: regle_fixture
    system_slug: filtration
    condition: Fixture — règle de sécurité dont l'identifiant est déclaré deux fois.
    evidence:
      confidence: medium
      source_policy: manual_review
      reviewed: false
      diagnostic_safe: false
    sources: [filtron_oem_clapets_filtre_huile]
  - rule_slug: regle_fixture
    system_slug: filtration
    condition: Fixture — règle de sécurité dont l'identifiant est déclaré deux fois.
    evidence:
      confidence: medium
      source_policy: manual_review
      reviewed: false
      diagnostic_safe: false
    sources: [filtron_oem_clapets_filtre_huile]
---

# Test fixture — règle dupliquée

Deux entrées partagent le même rule_slug → safety_rule_slug_duplicate.
