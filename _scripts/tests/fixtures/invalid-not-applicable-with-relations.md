---
schema_version: 2.0.0
id: gamme:filtre-test-not-applicable-with-relations
entity_type: gamme
slug: filtre-test-not-applicable-with-relations
title: Constat sans relation contredit
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
diagnostic_relations:
  - symptom_slug: perte_puissance_filtration
    system_slug: filtration
    cause_slug: filtre_colmate
    relation_to_part: possible_cause
    part_role: Un filtre colmaté restreint le débit et prive le moteur d'air ou de carburant.
    vehicle_scope:
      fuel: diesel
    evidence:
      confidence: medium
      strength: parfois
      source_policy: 1_high
      reviewed: false
      diagnostic_safe: false
    sources: [filtron_oem_clapets_filtre_huile]
    citations:
      - source: filtron_oem_clapets_filtre_huile
        start: 120
        end: 184
        quote_sha256: 'sha256:0000000000000000000000000000000000000000000000000000000000000000'
diagnostic:
  quick_checks:
    - cause_slug: filtre_colmate
      check: Contrôler visuellement l'état et la date de remplacement de l'élément filtrant.
      evidence:
        confidence: medium
        source_policy: 1_high
        reviewed: false
        diagnostic_safe: false
      sources: [filtron_oem_clapets_filtre_huile]
diagnostic_not_applicable:
  reason: Pièce sans lien avec un symptôme du vocabulaire.
  reviewed: false
entity_data:
  pg_id: 994
  family: filtration
---

# Test fixture — Constat sans relation contredit

Constat « sans relation » et relations présentes → diagnostic_not_applicable_with_relations.
