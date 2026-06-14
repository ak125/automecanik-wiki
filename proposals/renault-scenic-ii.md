---
schema_version: 1.0.0
id: vehicle:renault-scenic-ii
entity_type: vehicle
slug: renault-scenic-ii
title: Renault Scénic II
aliases:
- Renault Scénic 2
- Scénic II
- scenic-2
- Grand Scénic II
lang: fr
created_at: '2026-06-14'
updated_at: '2026-06-14'
truth_level: L2
source_refs:
- kind: manual
  note: Assemblé depuis la DB Supabase interne — motorisations réelles (auto_type,
    modele_id 140088) et pannes par famille moteur (kg_engine_families, curé interne).
    Provenance interne vérifiable, structurée en proposal R8 (ADR-086 §1).
  author: Deploy Bot — r8-motorization-canon@v0.1
provenance:
  ingested_by: manual:r8-motorization-canon@v0.1
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: 'Proposal R8 construite Internal-DB-first (ADR-086 §1 surface R8) :
  motorisations réelles depuis auto_type (modele_id 140088), pannes par moteur depuis
  kg_engine_families (curé interne). known_issues_by_engine / maintenance_by_engine
  = clés normalisées (engine_family:/fuel:). À reviewer humainement avant promotion
  vers wiki/vehicle/.'
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
entity_data:
  make: renault
  model: scenic-ii
  generation: ii
  years:
  - 2003
  - 2009
  motorizations:
  - code: 1.5 dCi
    fuel: diesel
    power_hp: 106
  - code: 1.9 dCi
    fuel: diesel
    power_hp: 131
  - code: 1.9 D
    fuel: diesel
    power_hp: 116
  - code: 2.0 dCi
    fuel: diesel
    power_hp: 150
  - code: 1.4 16V
    fuel: essence
    power_hp: 98
  - code: 1.6 16V
    fuel: essence
    power_hp: 113
  - code: 2.0 16V
    fuel: essence
    power_hp: 135
  - code: 2.0 16V TURBO
    fuel: essence
    power_hp: 163
  known_issues_by_engine:
    engine_family:k9k:
      axis_key_type: engine_family
      content_md: 'Moteur 1.5 dCi (famille K9K, Renault-Nissan) : vanne EGR sujette
        à l''encrassement (perte de puissance, fumées noires), injecteurs sensibles
        (fuite de retour), turbo dont les paliers s''usent prématurément si les intervalles
        de vidange ne sont pas respectés.'
      source_ids:
      - db:kg_engine_families
      - db:auto_type
      truth_level: sourced
      validation_notes:
      - Pannes K9K confirmées par kg_engine_families (curé interne) ; lien type→famille
        inféré (auto_type sans code moteur). À valider avant promotion.
    engine_family:f4r:
      axis_key_type: engine_family
      content_md: 'Moteur essence 2.0 16V (famille F4R) : bobines d''allumage et joints
        spi (fuite d''huile) à surveiller.'
      source_ids:
      - db:kg_engine_families
      truth_level: sourced
      validation_notes:
      - Pannes F4R depuis kg_engine_families ; lien type→famille inféré.
  maintenance_by_engine:
    fuel:diesel:
      axis_key_type: fuel
      content_md: 'Diesel : vidange + filtre à huile tous les 15 000 à 20 000 km ou
        1 an ; filtre à gasoil environ 60 000 km ; contrôler la distribution selon
        la motorisation.'
      source_ids:
      - db:auto_type
      truth_level: sourced
      validation_notes:
      - Axe carburant DB-fiable ; valeurs km à confirmer (carnet constructeur).
    fuel:essence:
      axis_key_type: fuel
      content_md: 'Essence : vidange + filtre à huile tous les 15 000 à 20 000 km
        ou 1 an selon préconisation ; filtre à air environ 30 000 km.'
      source_ids:
      - db:auto_type
      truth_level: sourced
      validation_notes:
      - Axe carburant DB-fiable ; valeurs km à confirmer.
  low_profile_canary: false
confidence_score: 0.3
---

# Renault Scénic II

> 📥 **Proposal R8 (ADR-086 §1)** — motorisations réelles depuis `auto_type`, pannes par moteur depuis `kg_engine_families` (Internal-DB-first). `review_status: proposed` — à reviewer avant promotion.

## Présentation

Le **Renault Scénic II** (génération II) est un monospace compact produit de **2003 à 2009**, sur la plate-forme de la Mégane II. Décliné en Scénic et Grand Scénic (7 places).

## Motorisations

| Motorisation | Carburant | Puissance (max) |
|---|---|---|
| 1.5 dCi | Diesel | 106 ch |
| 1.9 dCi | Diesel | 131 ch |
| 1.9 D | Diesel | 116 ch |
| 2.0 dCi | Diesel | 150 ch |
| 1.4 16V | Essence | 98 ch |
| 1.6 16V | Essence | 113 ch |
| 2.0 16V | Essence | 135 ch |
| 2.0 16V Turbo | Essence | 163 ch |

> Source : `auto_type` (DB, modèle-génération `140088`).

## Problèmes connus par motorisation

### 1.5 dCi (famille K9K)

Vanne EGR sujette à l'encrassement (perte de puissance, fumées noires), injecteurs sensibles (fuite de retour), turbo dont les paliers s'usent prématurément si les vidanges sont espacées.

### 2.0 16V essence (famille F4R)

Bobines d'allumage et joints spi (fuite d'huile) à surveiller.

> Source : `kg_engine_families` (connaissance interne curée). Lien type→famille **inféré** (auto_type ne porte pas le code moteur).

## Particularités d'entretien

- **Diesel** : vidange + filtre à huile 15 000–20 000 km ou 1 an ; filtre à gasoil ~60 000 km.
- **Essence** : vidange + filtre à huile 15 000–20 000 km ou 1 an ; filtre à air ~30 000 km.

## Sources et provenance

- `auto_type` (Supabase) — motorisations réelles indexables du modèle-génération.
- `kg_engine_families` (Supabase) — pannes connues par famille moteur (curé interne).

## Points à vérifier

- [ ] Confirmer `vlevel` (omis — classification V-Level non figée pour ce modèle).
- [ ] Valider humainement les `known_issues_by_engine` (lien type→famille inféré) avant promotion.
- [ ] Confirmer les valeurs km d'entretien (carnet constructeur).
- [ ] Enrichir les familles moteur non curées (F9Q 1.9 dCi, M9R 2.0 dCi, K4J/K4M essence) — chantier sourcing.
- [ ] Décider promotion → `wiki/vehicle/renault-scenic-ii.md` (porte ADR-083).
