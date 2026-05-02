---
schema_version: 1.0.0
id: vehicle:renault-megane-3
entity_type: vehicle
slug: renault-megane-3
title: Renault Mégane 3
aliases:
  - Mégane 3
  - Mégane III
  - Renault Mégane III
  - Megane 3
  - Mégane Coupé III
  - Mégane Estate III
  - Mégane CC III
  - Mégane RS III
  - Mégane Trophy
lang: fr
created_at: '2026-04-29'
updated_at: '2026-05-02'
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/vehicles/renault-megane-3.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:recycle-from-rag@v0.1
  promoted_from: null
lineage_id: 019dd8ee-daff-7056-ae32-9e931fce9fff
parents: []
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: |
  Phase F batch ADR-031. Recyclé depuis automecanik-rag par
  recycle-from-rag.py. Source body sha256=
  7d7f60d8d7915405ca6a69cf96aa77bc93a8e46ad2a9955e111de195cf6b199f.

  Phase 4 plan deja-verifier-existant 2026-05-02 :
  - Sections H2 alignées sur ordre canon _templates/new-vehicle.md
  - Titre "Fiche vehicule - Renault Megane 3" → "Renault Mégane 3"
    (FR canon avec accent)
  - aliases [] → 9 entrées (variantes commerciales avec accents)
  - target_classes [] → [KB_Knowledge, KB_Catalog]
  - entity_data complété : generation iii, years [2008, 2016],
    motorizations[] structuré YAML, vlevel V3, low_profile_canary false
  - Wikilinks gammes ajoutés
  - Section "Véhicules proches" ajoutée (plate-forme partagée Scénic 3 + Fluence)
  - Précision F9Q 1.9 dCi : fin de carrière, early phase 2008-2010
  - FAQ 5 questions ajoutée

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
  make: renault
  model: megane-3
  generation: iii
  years:
    - 2008
    - 2016
  type_id: null
  motorizations:
    - code: K4M
      fuel: essence
      power_hp: 110
      displacement_cc: 1598
      note: 1.6 16V atmosphérique
    - code: H4J
      fuel: essence
      power_hp: 130
      displacement_cc: 1397
      note: 1.4 TCe turbo
    - code: F4R
      fuel: essence
      power_hp: 180
      displacement_cc: 1998
      note: 2.0 TCe turbo
    - code: F4R
      fuel: essence
      power_hp: 250
      displacement_cc: 1998
      note: 2.0 RS Phase 1
    - code: F4R
      fuel: essence
      power_hp: 265
      displacement_cc: 1998
      note: 2.0 RS Trophy
    - code: K9K
      fuel: diesel
      power_hp: 90
      displacement_cc: 1461
      note: 1.5 dCi entrée de gamme
    - code: K9K
      fuel: diesel
      power_hp: 110
      displacement_cc: 1461
      note: 1.5 dCi haut de gamme
    - code: R9M
      fuel: diesel
      power_hp: 130
      displacement_cc: 1598
      note: 1.6 dCi (chaîne distribution)
    - code: F9Q
      fuel: diesel
      power_hp: 130
      displacement_cc: 1870
      note: 1.9 dCi — fin de carrière (early phase 2008-2010)
    - code: M9R
      fuel: diesel
      power_hp: 150
      displacement_cc: 1995
      note: 2.0 dCi entrée de gamme
    - code: M9R
      fuel: diesel
      power_hp: 160
      displacement_cc: 1995
      note: 2.0 dCi haut de gamme
  vlevel: V3
  low_profile_canary: false
content_hash: sha256:99910db4b341b52e477f939cba9e3940b3bca7a6d8437046ce0561298a6bb382
confidence_score: 0.24
---

# Renault Mégane 3

> 📥 **Proposition Phase F** — extraite par `recycle-from-rag.py`. Sections H2 ordre canon Phase 4 plan deja-verifier-existant.

## Présentation

La **Renault Mégane 3** (génération III) est une compacte du segment C produite de **2008 à 2016**. Elle a remplacé la Mégane II et fut elle-même remplacée par la Mégane IV en 2016. Disponible en 5 portes (la plus vendue), Coupé 3 portes, Estate (break), Coupé-Cabriolet (CC), et version sportive RS.

### Carrosseries

- **5 portes** (la plus répandue, lancement 2008)
- **Coupé 3 portes** (lancement 2009, ligne dynamique)
- **Estate (break)** (lancement 2009, version familiale)
- **CC (Coupé Cabriolet)** : toit rigide rétractable, lancement 2010
- **RS (Renault Sport)** : Coupé 3 portes 250 ch puis Trophy 265 ch

### Véhicules proches (plate-forme partagée / pièces partagées)

| Modèle | Années | Ce qui est partagé |
|---|---|---|
| [[renault-scenic-3]] | 2009-2016 | Plate-forme C, moteurs K4M/K9K/R9M/M9R, train roulant, électronique |
| [[renault-fluence]] | 2009-2016 | Plate-forme C, moteurs essence/diesel, freinage |
| [[renault-laguna-3]] | 2007-2015 | Moteurs M9R/F4R, électronique partagée |
| [[nissan-qashqai]] (génération I) | 2007-2013 | Moteurs K9K/R9M, alliance Renault-Nissan |

## Motorisations

### Essence

| Moteur | Puissance | Code moteur | Notes |
|---|---|---|---|
| 1.6 16V | 110 ch | K4M | Atmosphérique, le plus répandu |
| 1.4 TCe | 130 ch | H4J | Turbo |
| 2.0 TCe | 180 ch | F4R | Turbo, haut de gamme essence |
| 2.0 RS | 250 ch | F4R | Sportive Phase 1 |
| 2.0 RS Trophy | 265 ch | F4R | Sportive haut de gamme avec différentiel |

### Diesel

| Moteur | Puissance | Code moteur | Notes |
|---|---|---|---|
| 1.5 dCi | 90 / 110 ch | K9K | Le plus vendu |
| 1.6 dCi | 130 ch | R9M | **Chaîne distribution** (sans entretien) |
| 1.9 dCi | 130 ch | F9Q | Fin de carrière, early phase 2008-2010 uniquement |
| 2.0 dCi | 150 / 160 ch | M9R | Haut de gamme diesel |

## Pièces compatibles (top gammes)

### Pièces d'usure principales

- **Freinage** : [[plaquette-de-frein]] avant (30-40 000 km), [[disque-de-frein]] avant (60-80 000 km), arrière selon version (disques RS/CC, tambours base)
- **Filtration** : [[filtre-a-huile]] (chaque vidange), [[filtre-a-air]] (30 000 km), [[filtre-habitacle]] (15 000 km), [[filtre-a-carburant]] dCi (60 000 km)
- **Distribution** : selon motorisation
  - 1.5 dCi (K9K) : courroie 90 000 km / 6 ans
  - 1.6 dCi (R9M) : **chaîne (sans entretien normal)**
  - 2.0 dCi (M9R) : courroie 120 000 km / 6 ans
  - 1.6 16V (K4M) : courroie 120 000 km / 6 ans
  - TCe : chaîne (sans entretien normal)

### Références OEM courantes

| Pièce | Référence Renault |
|---|---|
| Filtre à huile 1.5 dCi | 8200768913 |
| Filtre à air 1.5 dCi | 8200431051 |
| Plaquettes avant | 410607115R |
| Disques avant | 402069518R |
| Kit distribution 1.5 dCi | 130C17529R |

> Indicatif — voir catalogue site pour références complètes par motorisation et année.

## Particularités d'entretien

### Problèmes connus

#### Moteur 1.5 dCi (K9K)

- **Injecteurs** : défaillance fréquente (claquement, fumée)
- **Vanne EGR** : encrassement rapide
- **Turbo** : contrôle huile régulier, géométrie variable

#### Moteur 1.6 dCi (R9M)

- **Injecteurs piezo** : coûteux à remplacer (~400 €/injecteur)
- **Courroie accessoires** : galet tendeur à surveiller

#### Moteur 2.0 dCi (M9R)

- **Volant moteur bimasse** : bruit au ralenti
- **Pompe haute pression (HP)** : copeaux métalliques possibles (point sensible — vidange régulière obligatoire)

#### Électricité

- **Carte main libre** : problèmes de détection (clé qui ne reconnaît plus)
- **Tableau de bord** : pixels défaillants
- **Feux arrière LED** : bandeaux LED HS (remplacement du bloc complet ~250 €)

#### Châssis

- **Roulements avant** : usure normale 80-100 000 km
- **Silent-blocs berceau** : claquements
- **Cardans** : soufflets à surveiller

### Intervalles d'entretien

| Opération | Fréquence |
|---|---|
| Vidange essence | 20 000 km / 1 an |
| Vidange diesel | 20 000 km / 1 an |
| Liquide de frein | 2 ans / 60 000 km |
| Boîte EDC (double-embrayage) | Vidange huile 60 000 km |

### Conseils propriétaire

1. **Huile moteur** : 5W-30 norme C3 ou C4 selon version (FAP)
2. **Liquide refroidissement** : type D (Glaceol RX, jaune/vert) — ne pas mélanger
3. **Direction assistée** : électrique (pas de fluide à contrôler)
4. **Boîte EDC** : vidange huile 60 000 km strictement obligatoire (sinon usure embrayages accélérée)

### Spécificités par version

#### Renault Mégane RS Mk3 (250 / 265 ch)

- 2.0 F4R turbo, traction avant
- **Freinage Brembo 4 pistons** avant (340 mm)
- **Châssis Cup** disponible (pack sport renforcé)
- **Différentiel autobloquant** mécanique (option Trophy)
- Mode sport sélectable
- Entretien plus fréquent recommandé

#### Renault Mégane CC Mk3

- Toit rigide rétractable
- **Vérins de toit** : vérifier joints + niveau hydraulique
- **Hydraulique toit** : contrôle niveau biennal

## Questions fréquentes

### Quand changer la courroie de distribution sur ma Mégane 3 ?

Selon motorisation : 1.5 dCi K9K = 90 000 km / 6 ans. 1.6 16V K4M = 120 000 km / 6 ans. 2.0 dCi M9R = 120 000 km / 6 ans. **1.6 dCi R9M et 2.0 TCe : chaîne (sans entretien normal)**, mais surveiller bruit anormal.

### Quels sont les points sensibles du 2.0 dCi M9R ?

Volant moteur bimasse (bruit ralenti), pompe HP (copeaux métalliques possibles si vidanges non respectées). Vidange tous les 20 000 km strictement, huile 5W-30 C3/C4 norme Renault uniquement.

### La Mégane RS Trophy 265 ch est-elle plus rapide que la 250 ch ?

Oui — 265 ch + différentiel autobloquant + suspensions Cup + freinage renforcé. Record Nürburgring détenu par Trophy 2014 (8 min 8 s — record voitures à traction avant pendant 2 ans).

### Pièces compatibles avec d'autres Renault ?

Oui, large recouvrement avec [[renault-scenic-3]] (plate-forme C identique), [[renault-fluence]], [[renault-laguna-3]] : moteurs K4M/K9K/R9M/M9R/F4R, freinage, électronique.

### Le 1.9 dCi F9Q est-il à éviter ?

Pas à éviter mais fin de carrière (early phase 2008-2010 uniquement sur Mégane 3). Architecture ancienne (2 valves), couple correct mais consommation supérieure aux nouveaux dCi. Préférer 1.5 dCi K9K ou 1.6 dCi R9M pour rapport efficacité/fiabilité.

## Sources et provenance

Sources canoniques utilisées (cf. `_quality/sources-brief.md` Phase 3) :

- **Wikipedia FR — Renault Mégane III** : https://fr.wikipedia.org/wiki/Renault_Mégane_III (license `CC-BY-SA-3.0`, capture intégrale via preset `wikipedia-vehicle` PR2 livré). Action humaine Phase 3.
- **caradisiac fiche technique Mégane 3** : https://www.caradisiac.com/fiches-techniques/modele--renault-megane-3/ (license `proprietary-citation-only`, ≤200 mots citation).
- **OEM Renault Mégane III workshop manual** : Phase 7 différé (preset `manuel-constructeur-pdf` à livrer skill PR2).

## Points à vérifier

- [ ] Vérifier `entity_data.type_id` aligné DB `__auto_type` (Mégane III millésimes 2008-2016, multiple type_id par phase + variants probable)
- [ ] Confirmer `vlevel: V3` (Mégane = vente moyenne, segment C populaire)
- [x] **2026-05-02** : `low_profile_canary: false` (volume notable)
- [x] **2026-05-02** : `motorizations[]` structuré YAML (11 entrées : 5 essence + 6 diesel)
- [x] **2026-05-02** : F9Q 1.9 dCi marqué fin de carrière early phase 2008-2010
- [x] **2026-05-02** : "Véhicules proches" ajouté (Scénic 3, Fluence, Laguna 3, Nissan Qashqai)
- [ ] Capturer Wikipedia FR Renault Mégane III via extension Obsidian preset `wikipedia-vehicle`
- [ ] Construire `_coverage/renault-megane-3.coverage.yaml` (Phase 5 plan parent)
- [ ] Décider promotion → `wiki/vehicles/renault-megane-3.md` (commit message obligatoire `promotion-from-proposals: renault-megane-3`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
