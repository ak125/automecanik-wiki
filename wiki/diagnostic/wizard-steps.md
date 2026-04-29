---
schema_version: 1.0.0
id: diagnostic:wizard-steps
entity_type: diagnostic
slug: wizard-steps
title: Wizard diagnostic — étapes et messages
aliases:
  - étapes wizard
  - loading steps
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L4
source_refs:
  - kind: snapshot
    origin_repo: nestjs-remix-monorepo
    origin_path: frontend/app/components/diagnostic-wizard/DiagnosticWizard.tsx
    origin_lines: '35-47'
    captured_at: '2026-04-29'
provenance:
  ingested_by: claude:adr-032-rg-1
  promoted_from: proposals/diagnostic-wizard-steps.md
review_status: published
reviewed_by: claude
reviewed_at: '2026-04-29'
review_notes: |
  Snapshot 1:1 des constants TS hardcodés actuels frontend.
  Pas de modification éditoriale. Promotion auto justifiée par
  ADR-032 RG-1 (snapshot existant, pas création nouvelle).
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  steps:
    - id: 1
      label: Vehicule
      description: Identifiez votre vehicule
    - id: 2
      label: Symptome
      description: Decrivez le probleme
    - id: 3
      label: Diagnostic
      description: Resultat et recommandations
  loading_steps:
    - Analyse des symptomes...
    - Evaluation des hypotheses...
    - Verification securite...
    - Consultation documentation...
    - Preparation du rapport...
---

# Wizard diagnostic — étapes et messages

Contenu UI servi à `DiagnosticWizard.tsx` (frontend Remix) via `DiagnosticContentService.getWizardSteps()` (ADR-032 PR-6).

## Steps

3 étapes du wizard interactif diagnostic. Voir `entity_data.steps` ci-dessus.

## Loading steps

5 messages affichés en rotation pendant l'analyse côté backend (entre POST `/api/diagnostic-engine/analyze` et la réponse). Voir `entity_data.loading_steps`.

## Sources

- [Source raw](../../../automecanik-raw/sources/diagnostic/wizard-steps.md)
- ADR-032 RG-1 — `governance-vault/ledger/decisions/adr/ADR-032-diagnostic-maintenance-unification.md`
