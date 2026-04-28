---
schema_version: "1.0.0"
id: "vehicle:lada-granta"
entity_type: vehicle
slug: lada-granta
title: Lada Granta
aliases:
  - LADA GRANTA
  - granta
lang: fr
created_at: "2026-04-28"
updated_at: "2026-04-28"
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/vehicles/lada-granta.md
    captured_at: "2026-04-28"
provenance:
  ingested_by: human:@fafa
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: |
  Pilote ADR-031 Phase E vehicle entity. Modèle low-profile Lada (NOT Clio/208/Golf
  per ADR-022 §"Stage 2 canary low-risk"). 42 fiches Lada disponibles dans le
  corpus, granta retenu comme représentatif standard.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  make: lada
  model: granta
  low_profile_canary: true
  motorizations:
    - code: "1.6 82 ch"
      fuel: essence
    - code: "1.6 87 ch"
      fuel: essence
    - code: "1.6 90 ch"
      fuel: essence
    - code: "1.6 98 ch"
      fuel: essence
    - code: "1.6 106 ch"
      fuel: essence
    - code: "1.6 Sport 118 ch"
      fuel: essence
---

# Lada Granta

> 📥 **Proposition pilote ADR-031 Phase E** — extraite manuellement depuis `automecanik-rag/knowledge/vehicles/lada-granta.md`.
> Modèle low-profile retenu pour Stage 2 canary (ADR-022). À reviewer avant promotion vers `wiki/vehicle/lada-granta.md`.

## Résumé proposé

Lada Granta — berline / hatchback / liftback du constructeur russe Lada (groupe AvtoVAZ). Plateforme commune avec d'autres modèles de la gamme. Présente dans le corpus AutoMecanik avec 11 motorisations recensées (essence 82-118 ch).

## Faits extraits

- **Make** : lada
- **Model** : granta
- **Variantes carrosserie** : berline, hatchback (2191), liftback, break
- **Motorisations essence 1.6** : 82, 87, 90, 98, 106, 118 ch (Sport)

## Faits inférés

- Modèle Stage 2 canary (low_profile_canary: true) — non Clio/208/Golf, marge sûre pour piloter le flux R8
- Marque tier 3 (Lada hors top constructeurs FR) → trafic SEO modéré, validation à faible risque

## Zones ambiguës / contradictions

- La source automecanik-rag mentionne aussi des motorisations Hybrid 145/136 et e-210/e-230, qui correspondent plutôt à d'autres modèles Lada (data quality du seed automatique). À retirer en review humaine.
- `motorisations[].code` source utilise un mélange de chiffres et de descriptions ; standardisation `code` strict + `fuel` recommandée avant promotion.

## Points de review

- [ ] Vérifier `type_id` Supabase pour granta (FK `__auto_type_motor`)
- [ ] Compléter `years` (plage de production)
- [ ] Compléter `generation` (Granta I, II)
- [ ] Filtrer les motorisations qui n'appartiennent pas à granta (Hybrid/e-* = autres modèles)
- [ ] Décider promotion → `wiki/vehicle/lada-granta.md` ou ajustement
