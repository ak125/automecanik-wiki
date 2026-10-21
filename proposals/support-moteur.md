---
schema_version: 2.0.0
id: gamme:support-moteur
entity_type: gamme
slug: support-moteur
title: Support moteur
aliases: []
lang: fr
created_at: '2026-05-27'
updated_at: '2026-10-21'
truth_level: L2
source_refs:
- kind: raw
  path: sources/auto-captures/support-moteur/aftermarket-zf-com-wl-support-moteur-zf-20261021-9f6d624a.md
  cid: sha256:57c884bc6e09b7eddde754b1cace92a5160dcf960d928c5685cd9b6cfc96233c
  captured_at: '2026-10-20'
  confidence: medium
provenance:
  ingested_by: codex:wiki-candidates-repair-20261021
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: 'Réparation candidate 2026-10-21, sans promotion. Ancien contenu et
  dimensions recyclées conservés dans Git 9f63fc49e7d73ea9783256e5671462a61cb5621a:proposals/support-moteur.md.
  La matrice de compatibilité et les mentions WEB_CONFIRMS_RAG non étayées sont retirées
  de cette proposition. Capture CAPTURED_NEEDS_REVIEW, licence unknown, aucune validation
  humaine déclarée. La page ZF est une présentation produit : corroboration descriptive
  seulement, aucune preuve de diagnostic ou de compatibilité. Symptômes, choix, entretien,
  FAQ et preuves d’atelier indépendantes restent à obtenir.'
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
diagnostic_relations: []
entity_data:
  pg_id: 247
  family: support_moteur
  related_parts:
  - support-de-boite-vitesse
  - silent-bloc
  - berceau-moteur
  - biellette-de-reprise-de-couple
  intents:
  - diagnostic
  - achat
  - compatibilite
  vlevel: V4
  kw_top: []
  references: []
confidence_score: 0.36
---

# Support moteur

## Définition

Le support moteur relie le moteur à la structure du véhicule. Il porte la charge statique du moteur et limite ses mouvements. [^source]

## Fonctionnement

Un support conventionnel utilise une liaison élastique associant du caoutchouc à du métal ou à du plastique. Un support hydraulique ajoute un amortissement par circulation de liquide. Certaines conceptions permettent de modifier les caractéristiques d’amortissement selon le fonctionnement du véhicule. [^source]

## Distinction avec le support de boîte

Le support de boîte relie la transmission à la carrosserie. La fonction générale de ces liaisons n’établit aucune interchangeabilité entre leurs références. [^source]

[^source]: ZF Aftermarket (LEMFÖRDER) — [Driveline Components — fonctions et types de supports](https://aftermarket.zf.com/en/aftermarket-portal/our-portfolio/passenger-cars/products/driveline-components/). Archive RAW : `sources/auto-captures/support-moteur/aftermarket-zf-com-wl-support-moteur-zf-20261021-9f6d624a.md`. Source pour examen interne ; droits d’usage non confirmés.
