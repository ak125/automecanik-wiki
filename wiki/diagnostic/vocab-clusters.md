---
schema_version: 1.0.0
id: diagnostic:vocab-clusters
entity_type: diagnostic
slug: vocab-clusters
title: Diagnostic — vocab clusters (6 catégories)
aliases:
  - clusters
  - perception channels
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L4
source_refs:
  - kind: raw
    path: sources/diagnostic/vocab-clusters.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:adr-032-rg-1@claude
  promoted_from: proposals/diagnostic-vocab-clusters.md
  promoted_at: '2026-04-29T17:00:00Z'
review_status: approved
reviewed_by: skill:adr-032-rg-1@claude
reviewed_at: '2026-04-29T17:00:00Z'
review_notes: Snapshot 1:1 des CLUSTERS + PERCEPTION_ICONS hardcodés.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  clusters:
    - id: embrayage
      label: Embrayage
      icon: Disc3
      description: Patinage, bruits, vibrations pédale
      color: from-amber-500 to-orange-600
    - id: freinage
      label: Freinage
      icon: Shield
      description: Sifflements, vibrations, efficacité réduite
      color: from-red-500 to-rose-600
    - id: moteur
      label: Moteur
      icon: Gauge
      description: Claquements, fumées, perte de puissance
      color: from-slate-600 to-slate-800
    - id: suspension
      label: Suspension
      icon: Car
      description: Cognements, tenue de route dégradée
      color: from-blue-500 to-indigo-600
    - id: electricite
      label: Électricité
      icon: Zap
      description: Voyants allumés, démarrage difficile
      color: from-yellow-500 to-amber-600
    - id: refroidissement
      label: Refroidissement
      icon: ThermometerSun
      description: Surchauffe, fuites liquide, ventilateur
      color: from-cyan-500 to-teal-600
  perception_icons:
    auditory: Volume2
    visual: Eye
    tactile: Wrench
    performance: Gauge
    electronic: Zap
    olfactory: ThermometerSun
confidence_score: 0.24
---

# Diagnostic vocab clusters

Contenu UI servi à `diagnostic-auto._index.tsx` (page hub `/diagnostic-auto`) via `DiagnosticContentService.getVocabClusters()` (ADR-032 PR-6).

## Clusters

6 catégories diagnostic présentées en grille sur la page hub. Aligné sur `__diag_system.slug` côté DB (freinage / demarrage_charge / refroidissement / etc.).

## Perception icons

Mapping `channel → lucide icon` pour rendre le canal sensoriel d'un symptôme (ex: bruit = `Volume2`, fuite visible = `Eye`).
