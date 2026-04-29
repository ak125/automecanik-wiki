---
schema_version: 2.0.0
id: gamme:test-no-relation
entity_type: gamme
slug: test-no-relation
title: Test no relation_to_part
aliases: []
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
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
  - symptom_slug: bruit_test
    system_slug: freinage
    # relation_to_part DELIBERATELY MISSING → expect FAIL relation_to_part_missing
    part_role: 'test'
    evidence:
      confidence: medium
      source_policy: 2_medium_concordant
      reviewed: false
      diagnostic_safe: false
    sources:
      - bosch_fad_2020
      - oem_renault_clio_iii_workshop
entity_data:
  pg_id: 999
  family: filtration
---

# Test fixture — relation_to_part missing

This fixture exists to verify the gate `relation_to_part_missing` triggers.
