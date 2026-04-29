---
schema_version: 1.0.0
id: vehicle:citroen-c3
entity_type: vehicle
slug: citroen-c3
title: Fiche vehicule - Citroen C3
aliases: []
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/vehicles/citroen-c3.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:recycle-from-rag@v0.1
  promoted_from:
lineage_id: 019dd8ee-daef-7070-9fe6-d4c46ebaa2c9
review_status: proposed
reviewed_by:
reviewed_at:
review_notes: Phase F batch ADR-031. Recyclé depuis automecanik-rag par recycle-from-rag.py. Source body sha256=e0b8db63cb5b0185e9ad9ab7015ae44c554e8baf27f4a5ea1535d97a49797f72. À reviewer humainement avant promotion vers wiki/vehicles/.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  make: citroen
  model: c3
content_hash: sha256:1482152fe2b802621856e88ee59908d979fe3c1a6b7fa2649d4f2bf050cc0b2e
---

# Fiche vehicule - Citroen C3

> 📥 **Proposition Phase F** — extraite par `recycle-from-rag.py` depuis `knowledge/vehicles/citroen-c3.md`.
> source body sha256 : `e0b8db63cb5b0185e9ad9ab7015ae44c554e8baf27f4a5ea1535d97a49797f72`
> À reviewer manuellement avant promotion vers `wiki/vehicles/citroen-c3.md`.

## Faits extraits (source body brut, à structurer)

# Citroen C3 (2002-2024)

## Identification

### C3 I (2002-2009)

- **Code** : FC
- **Segment** : B (citadine)
- **Carrosseries** : 5 portes, Pluriel (decouvrable)

### C3 II (2009-2016)

- **Code** : A51
- **Segment** : B
- **Carrosseries** : 5 portes

### C3 III (2016-2024)

- **Code** : SX
- **Segment** : B
- **Carrosseries** : 5 portes
- **Design** : Airbumps, bi-ton

## Motorisations principales

### Essence

| Moteur       | Puissance | Code moteur | Generation |
| ------------ | --------- | ----------- | ---------- |
| 1.1i         | 60 ch     | HFZ (TU1JP) | C3 I       |
| 1.4i         | 75 ch     | KFV (TU3JP) | C3 I/II    |
| 1.6 VTi      | 120 ch    | EP6         | C3 II      |
| 1.2 PureTech | 82 ch     | EB2         | C3 II/III  |
| 1.2 PureTech | 110 ch    | EB2DT turbo | C3 III     |

### Diesel

| Moteur      | Puissance | Code moteur | Generation |
| ----------- | --------- | ----------- | ---------- |
| 1.4 HDi     | 68 ch     | 8HZ (DV4TD) | C3 I/II    |
| 1.6 HDi     | 90/92 ch  | 9HX (DV6)   | C3 I/II    |
| 1.5 BlueHDi | 100 ch    | DV5         | C3 III     |

## Pieces d'usure courantes

### Freinage

- **Plaquettes avant** : 30-40 000 km
- **Disques avant** : 60-80 000 km
- **Arriere** : Tambours (I/II), disques (certaines III)

### Filtration

- **Filtre a huile** : A chaque vidange
- **Filtre a air** : 30 000 km
- **Filtre habitacle** : 15 000 km
- **Filtre a gasoil** : 60 000 km

### Distribution

- **Moteurs TU (1.1/1.4)** : Courroie, 80 000 km ou 5 ans
- **1.4/1.6 HDi** : Courroie, 100 000 km ou 10 ans
- **PureTech EB2** : Courroie, 100 000 km ou 10 ans
- **1.6 VTi (EP6)** : Chaine

## Problemes connus

### Moteur PureTech EB2 (1.2 turbo)

- **Courroie** : Etirement premature, controle frequent
- **Poulie damper** : Eclatement possible
- **Consommation huile** : A surveiller

### Moteur EP6 (1.6 VTi/THP)

- **Chaine distribution** : Etirement (bruit demarrage)
- **Capteur arbre a cames** : Defaillant
- **Bobines allumage** : A remplacer par kit renforce

### Moteur 1.4/1.6 HDi (DV4/DV6)

- **Vanne EGR** : Encrassement frequent
- **Injecteurs** : Fuite retour, demarrage difficile
- **Poulie damper** : Controle visuel regulier

### Electricite

- **BSI** : Dysfonctionnements (essuie-glaces, centralisation)
- **Combine** : Affichage defaillant
- **Antidemarrage** : Problemes cle/transpondeur

### Chassis

- **Roulements avant** : Remplacement frequent
- **Silent-blocs** : Claquements suspension
- **Cardans** : Soufflets fragiles

## Intervalles d'entretien

### Vidange

- **Essence** : 15 000 km ou 1 an
- **Diesel** : 20 000 km ou 1 an

### Liquide de frein

- Tous les 2 ans

## References OEM courantes

| Piece                     | Reference PSA |
| ------------------------- | ------------- |
| Filtre a huile 1.4 HDi    | 1109AY        |
| Filtre a air 1.4 HDi      | 1444VJ        |
| Plaquettes avant          | 4254.22       |
| Disques avant 266mm       | 4249.34       |
| Kit distribution PureTech | 1611841580    |

## Conseils d'entretien

1. **Huile moteur essence** : 5W-30 ou 0W-30
1. **Huile moteur diesel** : 5W-30 C2 (FAP)
1. **Liquide refroidissement** : Revkogel 2000
1. **Direction** : Electrique (pas de fluide)

## Specificites par version

### C3 Pluriel (2003-2010)

- Toit amovible modulable
- Arceaux retractables : Maintenance specifique
- Joints toit : Controle annuel

### C3 Aircross (2017+)

- SUV urbain derive C3
- Garde au sol rehaussee
- Memes motorisations PureTech/BlueHDi

## Points de review

- [ ] Vérifier `entity_data` complet et aligné DB monorepo (`vehicle`)
- [ ] Compléter ou corriger les `aliases`
- [ ] Décider promotion vers `wiki/vehicles/citroen-c3.md` ou ajustement
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO>`
