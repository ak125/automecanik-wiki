---
schema_version: 1.0.0
id: gamme:test-legacy
entity_type: gamme
slug: test-legacy
title: Test legacy diagnostic.symptoms[]
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
# ❌ LEGACY ANTI-PATTERN — diagnostic.symptoms[] forbidden by ADR-033 §D2
diagnostic:
  symptoms:
    - id: S1
      label: 'Vibrations au volant'
    - id: S2
      label: 'Pulsation pédale'
entity_data:
  pg_id: 997
  family: freinage
---

# Test fixture — legacy_symptoms_block

Frontmatter contains `diagnostic.symptoms[]` (legacy) → expect FAIL `legacy_symptoms_block`.
