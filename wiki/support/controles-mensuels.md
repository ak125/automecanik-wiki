---
schema_version: 1.0.0
id: support:controles-mensuels
entity_type: support
slug: controles-mensuels
title: Contrôles mensuels véhicule (6 vérifications client)
aliases:
  - vérifications mensuelles
  - check mensuel
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L4
source_refs:
  - kind: raw
    path: sources/support/controles-mensuels.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:adr-032-rg-1@claude
  promoted_from: proposals/support-controles-mensuels.md
  promoted_at: '2026-04-29T17:00:00Z'
review_status: approved
reviewed_by: skill:adr-032-rg-1@claude
reviewed_at: '2026-04-29T17:00:00Z'
review_notes: |
  Snapshot 1:1 du CONTROLES_MENSUELS hardcodé. Entity_type=support choisi
  (pas diagnostic) car conseil client générique non interactif.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: true
target_classes: []
entity_data:
  items:
    - element: Niveau d'huile moteur
      icon: Droplets
      detail: Verifier a froid, moteur a l'horizontale. Completer si sous le repere MIN.
    - element: Liquide de refroidissement
      icon: Thermometer
      detail: Niveau entre MIN et MAX sur le vase d'expansion. Ne jamais ouvrir a chaud.
    - element: Pression des pneus
      icon: Gauge
      detail: Verifier a froid. Valeurs sur l'etiquette montant de porte conducteur. +0.2 bar si charge lourde.
    - element: Eclairage
      icon: Sun
      detail: Feux de croisement, de route, clignotants, feux de recul, feux stop. Remplacer par paire.
    - element: Lave-glace
      icon: Droplets
      detail: Completer avec du liquide lave-glace (pas d'eau seule en hiver).
    - element: Essuie-glaces
      icon: Wrench
      detail: Verifier les traces. Remplacer si trainees ou bruit au passage.
---

# Contrôles mensuels véhicule

Contenu UI servi à `blog-pieces-auto.calendrier-entretien.tsx` (page calendrier entretien) via `DiagnosticContentService.getControlesMensuels()` (ADR-032 PR-6 + endpoint agrégé `/api/diagnostic-engine/calendar` D9).

6 vérifications simples que le conducteur peut faire lui-même, mappées sur des icônes lucide. Différent du calendrier `kg_get_smart_maintenance_schedule` (intervalles entretien périodique fuel-aware) — c'est ici du conseil client générique mensuel.

## Pourquoi `entity_type: support` (pas `diagnostic`)

ADR-031 distingue 5 entity_types :

- `diagnostic` = pages diagnostic interactif (wizard, signs, faq).
- `support` = conseil client générique sans interaction (pas de symptôme spécifique).

Les contrôles mensuels sont du conseil générique → `support`.
