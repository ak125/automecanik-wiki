---
schema_version: 2.0.0
id: gamme:filtre-a-huile
entity_type: gamme
slug: filtre-a-huile
title: Filtre à huile
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
entity_data:
  pg_id: 995
  family: filtration
  # ❌ MISSING : entity_data.maintenance.educational_advice
  # filtre-a-huile is in KG_MAINTENANCE_INTERVAL_SLUGS → ADR-032 §D1 requires maintenance block
---

# Test fixture — maintenance_advice_missing

Slug matches `kg_nodes.MaintenanceInterval` but no `entity_data.maintenance.educational_advice`
→ expect FAIL `maintenance_advice_missing` (ADR-032 §D1).
