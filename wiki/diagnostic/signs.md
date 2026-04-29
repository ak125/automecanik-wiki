---
schema_version: 1.0.0
id: diagnostic:signs
entity_type: diagnostic
slug: signs
title: Diagnostic — 10 signes avant-coureurs
aliases:
  - signs
  - signes panne
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L4
source_refs:
  - kind: raw
    path: sources/diagnostic/signs.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:adr-032-rg-1@claude
  promoted_from: proposals/diagnostic-signs.md
  promoted_at: '2026-04-29T17:00:00Z'
review_status: approved
reviewed_by: skill:adr-032-rg-1@claude
reviewed_at: '2026-04-29T17:00:00Z'
review_notes: Snapshot 1:1 du SIGNS_DATA hardcodé (10 signes).
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  signs:
    - title: Bruit inhabituel au freinage
      cluster: freinage
      cluster_label: Freinage
      detail: Sifflement aigu = plaquettes usées. Grincement métallique = disques atteints ou étrier. Organe de sécurité — à traiter en priorité.
    - title: Voyant moteur allumé (check engine)
      cluster: electricite
      cluster_label: Électricité
      detail: Un code OBD est enregistré dans le calculateur. Lisez-le dans les 48h avec un scanner OBD ou entrez-le dans notre outil ci-dessus.
    - title: Vibration au volant
      cluster: suspension
      cluster_label: Suspension
      detail: À vitesse constante = pneumatiques ou géométrie. Au freinage = disques voilés. Basse vitesse = rotule ou biellette de suspension.
    - title: Démarrage difficile ou raté
      cluster: electricite
      cluster_label: Électricité
      detail: Lent = batterie faible. Clic unique = relais de démarrage. Silence total = démarreur ou sécurité moteur. Vérifiez aussi les bougies.
    - title: Surconsommation soudaine
      cluster: moteur
      cluster_label: Moteur
      detail: Augmentation > 15% sans changement de conduite. Causes — injecteurs, bougie défaillante, thermostat bloqué ouvert, fuite circuit d'air.
    - title: Fumée à l'échappement
      cluster: moteur
      cluster_label: Moteur
      detail: Blanche dense = liquide de refroidissement (joint de culasse). Noire = mélange trop riche. Bleue = huile brûlée (segments, joints spi).
    - title: Perte de puissance
      cluster: moteur
      cluster_label: Moteur
      detail: FAP obstrué (diesel, trajets courts), turbo défaillant, injecteurs encrassés ou problème de gestion moteur. Scanner OBD recommandé.
    - title: Odeur de brûlé
      cluster: embrayage
      cluster_label: Embrayage
      detail: Caoutchouc = courroie en contact. Plastique = fusible ou faisceau. Œuf pourri = catalyseur. Âcre = embrayage en patinage.
    - title: Pédale de frein molle ou spongieuse
      cluster: freinage
      cluster_label: Freinage
      detail: Air dans le circuit ou fuite de liquide de frein. Perte de freinage possible. Arrêt immédiat si la pédale touche le plancher.
    - title: Voyant ABS ou ESP allumé
      cluster: electricite
      cluster_label: Électricité
      detail: ABS orange = capteur de roue défaillant dans 60% des cas. Le freinage reste actif mais sans assistance. Contrôle sous 7 jours.
---

# Diagnostic — 10 signes avant-coureurs

Contenu UI servi à `diagnostic-auto._index.tsx` (page hub `/diagnostic-auto`, section "Signes avant-coureurs") via `DiagnosticContentService.getSigns()` (ADR-032 PR-6).

10 entrées éditoriales mises en avant pour orienter le visiteur vers le cluster pertinent (mappé sur `__diag_system.slug`).
