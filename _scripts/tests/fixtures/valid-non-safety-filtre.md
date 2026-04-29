---
schema_version: 2.0.0
id: gamme:filtre-test-non-safety
entity_type: gamme
slug: filtre-test-non-safety
title: Filtre test non-safety
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
# Pas de diagnostic_relations[] — gate dormant pour family non-safety
entity_data:
  pg_id: 994
  family: filtration       # NON-safety family
---

# Test fixture — non-safety PASS

Family non-safety + pas de symptômes implicites → gates safety dormants → PASS.
