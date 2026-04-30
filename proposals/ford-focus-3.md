---
schema_version: 1.0.0
id: vehicle:ford-focus-3
entity_type: vehicle
slug: ford-focus-3
title: Fiche vehicule - Ford Focus 3
aliases: []
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/vehicles/ford-focus-3.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:recycle-from-rag@v0.1
  promoted_from:
lineage_id: 019dd8ee-daf1-7121-8b9a-8e158fec994b
review_status: proposed
reviewed_by:
reviewed_at:
review_notes: Phase F batch ADR-031. Recyclé depuis automecanik-rag par recycle-from-rag.py. Source body sha256=89e64f2b6d0c635377ab946775e05f488e6fa6e8b520323f4df0db1e9fe189a4. À reviewer humainement avant promotion vers wiki/vehicles/.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  make: ford
  model: focus-3
content_hash: sha256:21574f9ce771e8f73f4323e6a3e5cb05736290cf55a66a559b5c21ad4be02440
confidence_score: 0.24
---

# Fiche vehicule - Ford Focus 3

> 📥 **Proposition Phase F** — extraite par `recycle-from-rag.py` depuis `knowledge/vehicles/ford-focus-3.md`.
> source body sha256 : `89e64f2b6d0c635377ab946775e05f488e6fa6e8b520323f4df0db1e9fe189a4`
> À reviewer manuellement avant promotion vers `wiki/vehicles/ford-focus-3.md`.

## Faits extraits (source body brut, à structurer)

# Ford Focus 3 (2011-2018)

## Identification

- **Generation** : III (C346)
- **Production** : 2011 - 2018
- **Segment** : C (compacte)
- **Carrosseries** : 5 portes, 4 portes (berline), Estate (break), ST, RS

## Motorisations principales

### Essence

| Moteur       | Puissance  | Code moteur |
| ------------ | ---------- | ----------- |
| 1.0 EcoBoost | 100/125 ch | M1DA/M2DA   |
| 1.6 Ti-VCT   | 105/125 ch | PNDA        |
| 1.6 EcoBoost | 150/182 ch | JTDA        |
| 2.0 ST       | 250 ch     | R9DA        |
| 2.3 RS       | 350 ch     | -           |

### Diesel

| Moteur   | Puissance  | Code moteur |
| -------- | ---------- | ----------- |
| 1.5 TDCi | 95/120 ch  | XWDA        |
| 1.6 TDCi | 95/115 ch  | T1DA        |
| 2.0 TDCi | 140/163 ch | UFDB        |

## Pieces d'usure courantes

### Freinage

- **Plaquettes avant** : 30-40 000 km
- **Disques avant** : 60-80 000 km
- **Arriere** : Disques sur toutes versions

### Distribution

- **1.0 EcoBoost** : Courroie, 150 000 km ou 10 ans
- **1.6 EcoBoost** : Chaine
- **1.6 TDCi** : Courroie, 125 000 km ou 10 ans
- **2.0 TDCi** : Courroie, 150 000 km ou 10 ans

## Problemes connus

### Moteur 1.0 EcoBoost

- **Durite liquide refroidissement** : Fuite, rappel constructeur
- **Surchauffe** : Liee aux fuites durites
- **Joint de culasse** : Sur versions affectees

### Boite Powershift (DCT)

- **Embrayages** : Usure prematuree
- **A-coups** : En ville, basse vitesse
- **Solution** : Mise a jour logiciel, remplacement embrayages

### Electricite

- **Sync** : Problemes ecran tactile
- **Batterie** : Decharge si arret prolonge

## Intervalles d'entretien

### Vidange

- **Essence** : 20 000 km ou 1 an
- **Diesel** : 20 000 km ou 1 an

## Conseils d'entretien

1. **Huile moteur** : 5W-20 (EcoBoost), 5W-30 (autres)
1. **Liquide refroidissement** : Organique Ford
1. **Boite Powershift** : Vidange recommandee 50 000 km

## Points de review

- [ ] Vérifier `entity_data` complet et aligné DB monorepo (`vehicle`)
- [ ] Compléter ou corriger les `aliases`
- [ ] Décider promotion vers `wiki/vehicles/ford-focus-3.md` ou ajustement
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO>`
