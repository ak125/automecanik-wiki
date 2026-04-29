---
schema_version: 1.0.0
id: vehicle:volkswagen-golf-6
entity_type: vehicle
slug: volkswagen-golf-6
title: Fiche vehicule - Volkswagen Golf 6
aliases: []
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/vehicles/volkswagen-golf-6.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:recycle-from-rag@v0.1
  promoted_from:
lineage_id: 019dd8ee-db01-78ba-82e9-2cf711cc2a59
review_status: proposed
reviewed_by:
reviewed_at:
review_notes: Phase F batch ADR-031. Recyclé depuis automecanik-rag par recycle-from-rag.py. Source body sha256=3860e2a472439f0ed61f04d7a2cb5d5758bf4c491f83e9f857c840b6905b9313. À reviewer humainement avant promotion vers wiki/vehicles/.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  make: volkswagen
  model: golf-6
content_hash: sha256:6c01bea9d2b1eb3452a0c3e58fd061a406fe717a9e469b5e3b6d9b6740c51e01
---

# Fiche vehicule - Volkswagen Golf 6

> 📥 **Proposition Phase F** — extraite par `recycle-from-rag.py` depuis `knowledge/vehicles/volkswagen-golf-6.md`.
> source body sha256 : `3860e2a472439f0ed61f04d7a2cb5d5758bf4c491f83e9f857c840b6905b9313`
> À reviewer manuellement avant promotion vers `wiki/vehicles/volkswagen-golf-6.md`.

## Faits extraits (source body brut, à structurer)

# Volkswagen Golf 6 (2008-2012)

## Identification

- **Generation** : VI (5K)
- **Production** : 2008 - 2012
- **Segment** : C (compacte)
- **Carrosseries** : 3 portes, 5 portes, Variant (break), Cabriolet
- **Versions sport** : GTI, GTD, R

## Motorisations principales

### Essence

| Moteur      | Puissance | Code moteur |
| ----------- | --------- | ----------- |
| 1.4 TSI     | 122 ch    | CAXA        |
| 1.4 TSI     | 160 ch    | CAVD        |
| 1.8 TSI     | 160 ch    | CDAA        |
| 2.0 TSI GTI | 210 ch    | CCZB        |
| 2.0 TSI R   | 270 ch    | CDLF        |

### Diesel

| Moteur      | Puissance | Code moteur |
| ----------- | --------- | ----------- |
| 1.6 TDI     | 90/105 ch | CAYC        |
| 2.0 TDI     | 110 ch    | CBDB        |
| 2.0 TDI     | 140 ch    | CBAB        |
| 2.0 TDI GTD | 170 ch    | CFGB        |

## Pieces d'usure courantes

### Freinage

- **Plaquettes avant** : 30-50 000 km
- **Disques avant** : 60-80 000 km
- **Freins arriere** : Disques sur toutes versions

### Filtration

- **Filtre a huile** : A chaque vidange
- **Filtre a air** : 40 000 km
- **Filtre habitacle** : 20 000 km
- **Filtre a gasoil** (TDI) : 60 000 km

### Distribution

- **1.4 TSI** : Chaine (attention etirement)
- **1.6 TDI** : Courroie, 120 000 km ou 5 ans
- **2.0 TDI** : Courroie, 120 000 km ou 5 ans
- **2.0 TSI** : Chaine (sans entretien normal)

## Problemes connus

### Moteur 1.4 TSI (CAXA/CAVD)

- Chaine distribution : Etirement premature (symptome: bruit au demarrage froid)
- Tendeur chaine : Defaillant, a remplacer preventivement
- Solution : Kit chaine complet (tendeur + guides + chaine)

### Moteur 2.0 TDI (CR)

- Injecteurs piezo : Defaillance possible apres 150k km
- Vanne EGR : Encrassement, nettoyage ou suppression
- FAP : Regenerations frequentes en ville

### Boite DSG

- Mecatronique : Defaillances possibles (a-coups, passage neutre)
- Embrayages : Usure si conduite urbaine
- Vidange huile : Tous les 60 000 km obligatoire

### Electricite

- Module confort : Problemes vitres, centralisation
- Pompe a eau electrique (TSI) : Defaillante apres 100k km

## Intervalles d'entretien

### Vidange (selon service VAG)

- **Service flexible** : 15-30 000 km selon usage
- **Recommande** : 15 000 km ou 1 an

### Liquide de frein

- Tous les 2 ans

## References OEM courantes

| Piece                    | Reference VAG   |
| ------------------------ | --------------- |
| Filtre a huile 2.0 TDI   | 03L115562       |
| Filtre a air 2.0 TDI     | 1K0129620D      |
| Plaquettes avant         | 5K0698151       |
| Disques avant            | 5K0615301       |
| Kit distribution 2.0 TDI | Gates/Contitech |

## Conseils d'entretien

1. **Huile moteur** : 5W-30 504.00/507.00 (Long Life)
1. **Alternative recommandee** : 5W-40 non Long Life + vidanges 15k km
1. **Liquide refroidissement** : G12++ (rose/violet)
1. **Boite DSG** : Vidange stricte 60 000 km

## Specificites par version

### Golf GTI

- Freinage plus gros (312mm)
- Differentiel XDS (freinage selectif)
- Mode sport selectable
- Huile 5W-40 recommandee

### Golf R

- Transmission 4Motion
- Freinage 345mm avant
- Entretien renforce recommande

### Golf GTD

- Performances diesel
- FAP et AdBlue selon annee
- Huile specifique FAP

## Points de review

- [ ] Vérifier `entity_data` complet et aligné DB monorepo (`vehicle`)
- [ ] Compléter ou corriger les `aliases`
- [ ] Décider promotion vers `wiki/vehicles/volkswagen-golf-6.md` ou ajustement
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO>`
