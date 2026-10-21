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
updated_at: '2026-10-21'
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
  vers wiki/vehicle/. Réparation 2026-10-21 : champs et texte de défauts par famille
  inférée et intervalles non sourcés retirés ; historique conservé dans _audit/candidates-repair-20261021/scenic-unproven-fields.json
  et Git. Aucune preuve DB nouvelle ni promotion.'
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
  low_profile_canary: false
confidence_score: 0.24
content_hash: sha256:afe9630c515f616ffc7bec8852b6ec8b3356db1ed0fc602116347a126fa7b341
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

## État des preuves d’entretien

Les liens entre ces motorisations et les familles moteur n’ont pas été établis par une preuve archivée. Aucun défaut ni intervalle d’entretien propre à cette génération n’est donc retenu ici. La liste de motorisations ci-dessus reste candidate jusqu’à vérification de sa provenance.

## Sources et provenance

- `auto_type` (Supabase) — motorisations réelles indexables du modèle-génération.
- `kg_engine_families` (Supabase) — pannes connues par famille moteur (curé interne).

## Points à vérifier

- [ ] Confirmer `vlevel` (omis — classification V-Level non figée pour ce modèle).
- [ ] Établir et archiver le lien exact entre les types véhicule et les familles moteur avant de réintroduire des défauts contextualisés.
- [ ] Confirmer les valeurs km d'entretien (carnet constructeur).
- [ ] Enrichir les familles moteur non curées (F9Q 1.9 dCi, M9R 2.0 dCi, K4J/K4M essence) — chantier sourcing.
- [ ] Décider promotion → `wiki/vehicle/renault-scenic-ii.md` (porte ADR-083).
