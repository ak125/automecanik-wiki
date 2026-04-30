---
schema_version: 2.0.0
id: gamme:test-overclaim
entity_type: gamme
slug: test-overclaim
title: Test overclaim brochure as high
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
    relation_to_part: possible_cause
    part_role: 'test overclaim'
    evidence:
      confidence: high          # ❌ INVALID — bosch_fad_2020 is brochure (max medium)
      source_policy: 1_high
      reviewed: false
      diagnostic_safe: false
    sources:
      - bosch_fad_2020          # type: brochure → max confidence: medium
entity_data:
  pg_id: 998
  family: filtration
---

# Test fixture — confidence_overclaimed

Single brochure source claiming `confidence: high` → expect FAIL `confidence_overclaimed`.
