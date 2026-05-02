---
schema_version: 1.0.0
id: vehicle:citroen-c3
entity_type: vehicle
slug: citroen-c3
title: Citroën C3
aliases:
  - C3
  - Citroen C3
  - C3 II
  - C3 III
lang: fr
created_at: '2026-04-29'
updated_at: '2026-05-02'
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/vehicles/citroen-c3.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:recycle-from-rag@v0.1
  promoted_from: null
lineage_id: 019dd8ee-daef-7070-9fe6-d4c46ebaa2c9
parents: []
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: |
  Phase F batch ADR-031. Recyclé depuis automecanik-rag par
  recycle-from-rag.py. Source body sha256=
  e0b8db63cb5b0185e9ad9ab7015ae44c554e8baf27f4a5ea1535d97a49797f72.

  Phase 4 plan deja-verifier-existant 2026-05-02 :
  - Sections H2 alignées sur ordre canon _templates/new-vehicle.md
  - Titre "Fiche vehicule - Citroen C3" → "Citroën C3" (FR canon avec accent)
  - aliases [] → [C3, Citroen C3, C3 II, C3 III]
  - target_classes [] → [KB_Knowledge, KB_Catalog]
  - entity_data complété : generation (covers I/II/III), years [2002, 2024],
    motorizations[] structuré YAML, vlevel V3, low_profile_canary false
  - Wikilinks gammes ajoutés (plaquette-de-frein, filtre-a-air, etc.)
  - "C3 Aircross" REMOVED (modèle SÉPARÉ — fiche [[citroen-c3-aircross]] future,
    pas une variante C3)
  - "C3 Pluriel" gardée comme variante phase 1 légitime
  - FAQ 5 questions ajoutée (vidange, distribution, problèmes EP6/EB2/HDi,
    pièces partagées PSA)

  À reviewer humainement avant promotion vers wiki/vehicles/.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
  - KB_Knowledge
  - KB_Catalog
entity_data:
  make: citroen
  model: c3
  generation: i+ii+iii
  years:
    - 2002
    - 2024
  type_id: null
  motorizations:
    - code: HFZ
      fuel: essence
      power_hp: 60
      displacement_cc: 1124
      note: 1.1i TU1JP — C3 I
    - code: KFV
      fuel: essence
      power_hp: 75
      displacement_cc: 1360
      note: 1.4i TU3JP — C3 I/II
    - code: EP6
      fuel: essence
      power_hp: 120
      displacement_cc: 1598
      note: 1.6 VTi — C3 II (groupe PSA-BMW Prince)
    - code: EB2
      fuel: essence
      power_hp: 82
      displacement_cc: 1199
      note: 1.2 PureTech atmosphérique — C3 II/III
    - code: EB2DT
      fuel: essence
      power_hp: 110
      displacement_cc: 1199
      note: 1.2 PureTech turbo — C3 III
    - code: 8HZ
      fuel: diesel
      power_hp: 68
      displacement_cc: 1398
      note: 1.4 HDi DV4TD — C3 I/II
    - code: 9HX
      fuel: diesel
      power_hp: 90
      displacement_cc: 1560
      note: 1.6 HDi DV6 — C3 I/II
    - code: DV5
      fuel: diesel
      power_hp: 100
      displacement_cc: 1499
      note: 1.5 BlueHDi — C3 III
  vlevel: V3
  low_profile_canary: false
content_hash: sha256:1482152fe2b802621856e88ee59908d979fe3c1a6b7fa2649d4f2bf050cc0b2e
confidence_score: 0.24
---

# Citroën C3

> 📥 **Proposition Phase F** — extraite par `recycle-from-rag.py`. Sections H2 ordre canon Phase 4 plan deja-verifier-existant.

## Présentation

La **Citroën C3** est une citadine du segment B produite par Citroën depuis **2002**. Trois générations successives ont été commercialisées :

### C3 I (2002-2009) — code FC

- Carrosseries : 5 portes, **C3 Pluriel** (découvrable, 2003-2010, toit amovible modulable)
- Première génération à plate-forme PSA PF1

### C3 II (2009-2016) — code A51

- Carrosserie : 5 portes uniquement
- Plate-forme PSA PF1 modernisée
- Introduction des moteurs PureTech EB2

### C3 III (2016-2024) — code SX

- Carrosserie : 5 portes
- Plate-forme PSA EMP1
- Design distinctif : Airbumps latéraux (option), bi-ton toit/caisse

> **Important** : la **Citroën C3 Aircross** (SUV urbain dérivé, 2017+) est un **modèle séparé**, pas une variante C3. Voir fiche [[citroen-c3-aircross]] (à créer).

### Véhicules proches (plate-forme partagée / pièces partagées)

| Modèle | Années | Ce qui est partagé |
|---|---|---|
| [[peugeot-208]] (génération I) | 2012-2019 | Plate-forme PF1, moteurs EB2/DV6, freinage, train roulant |
| [[peugeot-2008]] (génération I) | 2013-2019 | Moteurs EB2/PureTech, freinage |
| [[citroen-ds3]] | 2009-2019 | Plate-forme PF1, moteurs EB2/EP6/DV6 |

## Motorisations

### Essence

| Moteur | Puissance | Code moteur | Génération |
|---|---|---|---|
| 1.1i | 60 ch | HFZ (TU1JP) | C3 I |
| 1.4i | 75 ch | KFV (TU3JP) | C3 I/II |
| 1.6 VTi | 120 ch | EP6 (groupe PSA-BMW Prince) | C3 II |
| 1.2 PureTech | 82 ch | EB2 atmosphérique | C3 II/III |
| 1.2 PureTech | 110 ch | EB2DT turbo | C3 III |

### Diesel

| Moteur | Puissance | Code moteur | Génération |
|---|---|---|---|
| 1.4 HDi | 68 ch | 8HZ (DV4TD) | C3 I/II |
| 1.6 HDi | 90 / 92 ch | 9HX (DV6) | C3 I/II |
| 1.5 BlueHDi | 100 ch | DV5 | C3 III |

## Pièces compatibles (top gammes)

### Pièces d'usure principales

- **Freinage** : [[plaquette-de-frein]] avant (30-40 000 km), arrière selon génération (tambours C3 I/II, disques certaines C3 III), [[disque-de-frein]] avant (60-80 000 km)
- **Filtration** : [[filtre-a-huile]] (chaque vidange), [[filtre-a-air]] (30 000 km), [[filtre-habitacle]] (15 000 km), [[filtre-a-carburant]] diesel (60 000 km)
- **Distribution** : selon motorisation
  - Moteurs TU (1.1/1.4) : courroie 80 000 km / 5 ans
  - HDi DV4/DV6 (1.4/1.6) : courroie 100 000 km / 10 ans
  - PureTech EB2 (1.2) : courroie 100 000 km / 10 ans (attention étirement prématuré, voir Particularités d'entretien)
  - 1.6 VTi (EP6) : chaîne (mais étirement fréquent)

### Références OEM courantes

| Pièce | Référence PSA |
|---|---|
| Filtre à huile 1.4 HDi | 1109AY |
| Filtre à air 1.4 HDi | 1444VJ |
| Plaquettes avant | 4254.22 |
| Disques avant 266 mm | 4249.34 |
| Kit distribution PureTech | 1611841580 |

> Indicatif — voir catalogue site pour références complètes par motorisation et année.

## Particularités d'entretien

### Problèmes connus

#### Moteur 1.2 PureTech turbo (EB2DT)

- **Courroie de distribution** : étirement prématuré, contrôle fréquent recommandé
- **Poulie damper** : éclatement possible
- **Consommation huile** : à surveiller

#### Moteur 1.6 VTi/THP (EP6)

- **Chaîne distribution** : étirement (bruit démarrage à froid)
- **Capteur arbre à cames** : défaillant
- **Bobines allumage** : à remplacer par kit renforcé

#### Moteur 1.4/1.6 HDi (DV4/DV6)

- **Vanne EGR** : encrassement fréquent
- **Injecteurs** : fuite retour, démarrage difficile
- **Poulie damper** : contrôle visuel régulier

#### Électricité

- **BSI (Boîtier de Servitude Intelligent)** : dysfonctionnements (essuie-glaces, centralisation)
- **Combiné instrument** : affichage défaillant
- **Antidémarrage** : problèmes clé/transpondeur

#### Châssis

- **Roulements avant** : remplacement fréquent
- **Silent-blocs** : claquements suspension
- **Cardans** : soufflets fragiles

### Intervalles d'entretien

| Opération | Fréquence |
|---|---|
| Vidange essence | 15 000 km / 1 an |
| Vidange diesel | 20 000 km / 1 an |
| Liquide de frein | 2 ans |
| Filtre habitacle | 15 000 km / 1 an |

### Conseils propriétaire

1. **Huile moteur essence** : 5W-30 ou 0W-30
2. **Huile moteur diesel** : 5W-30 C2 (FAP)
3. **Liquide refroidissement** : Revkogel 2000
4. **Direction** : électrique (pas de fluide)

### Spécificités par version

#### C3 Pluriel (2003-2010)

- Toit amovible modulable
- Arceaux rétractables : maintenance spécifique
- Joints toit : contrôle annuel

## Questions fréquentes

### Quand changer la courroie de distribution sur une C3 PureTech ?

Officiellement 100 000 km / 10 ans, mais étirement prématuré observé sur EB2DT turbo : contrôle visuel recommandé tous les 60 000 km. Remplacement préventif 80 000 km en cas de signes (bruit, jeu).

### Le moteur 1.6 VTi (EP6) a-t-il vraiment des problèmes de chaîne ?

Oui — étirement fréquent surtout si vidanges non respectées. Symptôme : bruit type "claquement" au démarrage à froid. Remplacement kit chaîne complet : 1 200-2 000 €.

### Quelle huile pour ma C3 1.4 HDi ?

5W-30 norme C2 si équipée FAP (DV4TD avec FAP sur fin de C3 II). Sinon 5W-30 ou 5W-40 standard PSA.

### Pièces compatibles avec d'autres PSA ?

Oui, large recouvrement avec [[peugeot-208]] (génération I), [[peugeot-2008]] (génération I), [[citroen-ds3]] : moteurs EB2/EP6/DV6, freinage, train roulant.

### Différence entre C3 et C3 Aircross ?

La **C3 Aircross** (lancée 2017) est un **SUV urbain séparé**, pas une variante C3. Carrosserie distincte, garde au sol rehaussée, motorisations PureTech/BlueHDi mais châssis et identité commerciale propres. Voir fiche [[citroen-c3-aircross]].

## Sources et provenance

Sources canoniques utilisées (cf. `_quality/sources-brief.md` Phase 3) :

- **Wikipedia FR — Citroën C3** : https://fr.wikipedia.org/wiki/Citroën_C3 (license `CC-BY-SA-3.0`, capture intégrale via preset `wikipedia-vehicle` PR2 livré). Action humaine Phase 3.
- **Site corporate Citroën heritage C3** : https://www.citroen.fr/univers-citroen/heritage-citroen/c3.html (license `proprietary-manufacturer`, capture intégrale autorisée site marketing public).
- **caradisiac fiche technique C3** : https://www.caradisiac.com/fiches-techniques/modele--citroen-c3/ (license `proprietary-citation-only`, ≤200 mots citation).
- **OEM PSA Citroën C3 workshop manual** : Phase 7 différé (preset `manuel-constructeur-pdf` à livrer skill PR2).

## Points à vérifier

- [ ] Vérifier `entity_data.type_id` aligné DB `__auto_type` (mapper 3 générations C3 I/II/III)
- [ ] Confirmer `vlevel: V3` (C3 = vente moyenne, segment B intermédiaire)
- [x] **2026-05-02** : `low_profile_canary: false` (C3 = volume notable, pas canary)
- [x] **2026-05-02** : `motorizations[]` structuré YAML (8 entrées : 5 essence + 3 diesel)
- [x] **2026-05-02** : C3 Aircross retiré (modèle séparé, fiche dédiée à créer)
- [ ] Capturer Wikipedia FR Citroën C3 via extension Obsidian preset `wikipedia-vehicle`
- [ ] Construire `_coverage/citroen-c3.coverage.yaml` (Phase 5 plan parent)
- [ ] Décider promotion → `wiki/vehicles/citroen-c3.md` (commit message obligatoire `promotion-from-proposals: citroen-c3`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
