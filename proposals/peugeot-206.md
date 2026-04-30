---
schema_version: 1.0.0
id: vehicle:peugeot-206
entity_type: vehicle
slug: peugeot-206
title: Fiche véhicule - Peugeot 206
aliases: []
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/vehicles/peugeot-206.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:recycle-from-rag@v0.1
  promoted_from:
lineage_id: 019dd8ee-daf3-74cc-9687-439ae70303de
review_status: proposed
reviewed_by:
reviewed_at:
review_notes: Phase F batch ADR-031. Recyclé depuis automecanik-rag par recycle-from-rag.py. Source body sha256=8d75d4860580b5f0867f07b1dd76053cb5ac969e8ed25f341a0c8afed7ac1d2a. À reviewer humainement avant promotion vers wiki/vehicles/.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  make: peugeot
  model: '206'
content_hash: sha256:1095e93c018ed389fed2b42485af5a583a4563d64dda52ccc62fa42919e77320
confidence_score: 0.32
---

# Fiche véhicule - Peugeot 206

> 📥 **Proposition Phase F** — extraite par `recycle-from-rag.py` depuis `knowledge/vehicles/peugeot-206.md`.
> source body sha256 : `8d75d4860580b5f0867f07b1dd76053cb5ac969e8ed25f341a0c8afed7ac1d2a`
> À reviewer manuellement avant promotion vers `wiki/vehicles/peugeot-206.md`.

## Faits extraits (source body brut, à structurer)

# Peugeot 206 (1998-2012)

## Identification

- **Génération** : Unique (T1/T3)
- **Production** : 1998 - 2012
- **Segment** : B (citadine)
- **Carrosseries** : 3 portes, 5 portes, CC (cabriolet), SW (break), RC/GTI

## Motorisations principales

### Essence

| Moteur  | Puissance | Code moteur   |
| ------- | --------- | ------------- |
| 1.1i    | 60 ch     | HFX (TU1JP)   |
| 1.4i    | 75 ch     | KFW (TU3JP)   |
| 1.6i    | 88/110 ch | NFU (TU5JP4)  |
| 2.0 GTI | 137 ch    | RFK (EW10J4)  |
| 2.0 RC  | 177 ch    | RFK (EW10J4S) |

### Diesel

| Moteur  | Puissance | Code moteur   |
| ------- | --------- | ------------- |
| 1.4 HDi | 68 ch     | 8HX (DV4TD)   |
| 1.6 HDi | 90/110 ch | 9HY/9HZ (DV6) |
| 2.0 HDi | 90 ch     | RHY (DW10TD)  |

## Pièces d'usure courantes

### Freinage

- **Plaquettes avant** : 30-40 000 km
- **Disques avant** : 60-80 000 km
- **Tambours arrière** : Standard sur la plupart des versions
- **Kit frein arrière** : Mâchoires + cylindres

### Filtration

- **Filtre à huile** : À chaque vidange
- **Filtre à air** : 30 000 km
- **Filtre habitacle** : 15 000 km
- **Filtre à gasoil** (HDi) : 60 000 km

### Distribution

- **Essence TU** : Courroie, 80 000 km ou 5 ans
- **HDi DV4/DV6** : Courroie, 100 000 km ou 10 ans
- **HDi DW10** : Courroie, 120 000 km

## Problèmes connus

### Moteur 1.4 HDi (DV4)

- Injecteurs : Encrassement, démarrage difficile
- Vanne EGR : Colmatage fréquent
- Poulie damper : Éclatement (bruit moteur)

### Moteur 1.6 HDi (DV6)

- Volant moteur bimasse : Usure prématurée (bruit au ralenti)
- Turbo : Contrôle régulier huile

### Électricité

- BSI (Boîtier de Servitude Intelligent) : Dysfonctionnements
- Antidémarrage : Problèmes transpondeur clé

### Train roulant

- Cardans : Soufflets à surveiller
- Roulements avant : Usure normale
- Triangles de suspension : Silent-blocs

## Intervalles d'entretien

### Vidange

- **Essence** : 15 000 km ou 1 an
- **Diesel** : 20 000 km ou 1 an

### Liquide de frein

- Tous les 2 ans

## Références OEM courantes

| Pièce                    | Référence Peugeot |
| ------------------------ | ----------------- |
| Filtre à huile 1.4 HDi   | 1109AY            |
| Filtre à air 1.4 HDi     | 1444VJ            |
| Plaquettes avant         | 4254.22           |
| Disques avant            | 4249.G5           |
| Kit distribution 1.4 HDi | 0831V4            |

## Conseils d'entretien

1. **Huile moteur diesel** : 5W-30 spéciale FAP si équipé
1. **Essence** : 10W-40 ou 5W-40 selon préconisation
1. **Liquide refroidissement** : Type Revkogel 2000 (vert)
1. **LHM** : Si direction assistée hydraulique (citadines anciennes)

## Spécificités par version

### 206 RC

- Freinage renforcé (disques ventilés 4 pistons)
- Distribution renforcée
- Entretien plus fréquent recommandé

### 206 CC

- Vérins de capote : Contrôle annuel
- Joints de capote : Entretien spécifique

## Points de review

- [ ] Vérifier `entity_data` complet et aligné DB monorepo (`vehicle`)
- [ ] Compléter ou corriger les `aliases`
- [ ] Décider promotion vers `wiki/vehicles/peugeot-206.md` ou ajustement
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO>`
