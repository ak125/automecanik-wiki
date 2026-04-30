---
schema_version: 2.0.0
id: gamme:test-unknown-source
entity_type: gamme
slug: test-unknown-source
title: Test source slug absent du catalog
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
    part_role: 'test source slug unknown'
    evidence:
      confidence: medium
      source_policy: 2_medium_concordant
      reviewed: false
      diagnostic_safe: false
    sources:
      - some_inexistent_source_slug   # ❌ NOT in _meta/source-catalog.yaml
      - another_unknown_one
entity_data:
  pg_id: 996
  family: filtration
---

# Test fixture — source_slug_unknown

`sources` cite slugs absent du catalogue → expect FAIL `source_slug_unknown`.
