---
schema_version: 1.0.0
id: constructeur:dacia
entity_type: constructeur
slug: dacia
title: Dacia
aliases:
  - DACIA
  - Dacia Auto
lang: fr
created_at: '2026-04-28'
updated_at: '2026-04-28'
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/constructeurs/dacia.md
    captured_at: '2026-04-28'
provenance:
  ingested_by: human:@fafa
  promoted_from:
review_status: proposed
reviewed_by:
reviewed_at:
review_notes: |
  Pilote ADR-031 Phase E constructeur entity. Tier 3 brand low-profile per
  runbook §"Phase E" (dacia/seat/skoda parmi candidats Tier 3).
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  name: Dacia
  country: RO
  founded: 1966
  brand_aliases:
    - DACIA
  tier: 3
  models: []
confidence_score: 0.24
---

# Dacia

> 📥 **Proposition pilote ADR-031 Phase E** — extraite manuellement depuis `automecanik-rag/knowledge/constructeurs/dacia.md`.
> Marque Tier 3 retenue comme low-profile pour piloter le flux constructeur. À reviewer avant promotion vers `wiki/constructeur/dacia.md`.

## Résumé proposé

Dacia — constructeur automobile roumain fondé en 1966, filiale du groupe Renault depuis 1999. Hub de navigation pour pièces détachées DACIA : sélection par modèle, année et motorisation, avec filtrage par gamme de pièces compatibles.

## Faits extraits

- **Pays** : Roumanie (RO)
- **Fondé** : 1966
- **Groupe** : Renault Group (depuis 1999)
- **brand_id (DB Supabase legacy)** : 47

## Faits inférés

- Tier 3 (niche / low-profile) — volume de recherche modéré côté FR vs Renault/Peugeot/Citroën (Tier 1)
- Pas encore de liste de modèles dans `models` — à remplir lors de la promotion croisée avec les fiches `wiki/vehicle/dacia-*`

## Zones ambiguës / contradictions

Aucune sur ce pilote. La fiche source automecanik-rag est `verification_status: draft` mais les faits clés (pays, groupe) sont publics et vérifiables.

## Points de review

- [ ] Vérifier `brand_id: 47` aligné DB Supabase (référencé par `__auto_marque`)
- [ ] Lister `models` complets (Sandero, Logan, Duster, Spring, Jogger, etc.) après promotion des fiches `wiki/vehicle/dacia-*`
- [ ] Confirmer `tier: 3` (peut basculer à 2 selon la stratégie SEO 2026 — voir vault `r7-curation-method.md`)
- [ ] Décider promotion → `wiki/constructeur/dacia.md` ou ajustement
