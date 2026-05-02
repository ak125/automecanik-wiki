---
schema_version: 1.0.0
id: vehicle:volkswagen-golf-6
entity_type: vehicle
slug: volkswagen-golf-6
title: Volkswagen Golf 6
aliases:
  - Golf 6
  - Golf VI
  - VW Golf 6
  - Golf Mk6
  - Volkswagen Golf VI
  - Golf GTI Mk6
  - Golf GTD Mk6
  - Golf R Mk6
  - Golf 5K
lang: fr
created_at: '2026-04-29'
updated_at: '2026-05-02'
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/vehicles/volkswagen-golf-6.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:recycle-from-rag@v0.1
  promoted_from: null
lineage_id: 019dd8ee-db01-78ba-82e9-2cf711cc2a59
parents: []
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: |
  Phase F batch ADR-031. Recyclé depuis automecanik-rag par
  recycle-from-rag.py. Source body sha256=
  3860e2a472439f0ed61f04d7a2cb5d5758bf4c491f83e9f857c840b6905b9313.

  Phase 4 plan deja-verifier-existant 2026-05-02 :
  - Sections H2 alignées sur ordre canon _templates/new-vehicle.md
  - Titre "Fiche vehicule - Volkswagen Golf 6" → "Volkswagen Golf 6"
    (FR canon)
  - aliases [] → 9 entrées (variantes commerciales)
  - target_classes [] → [KB_Knowledge, KB_Catalog]
  - entity_data complété : generation vi, years [2008, 2012],
    motorizations[] structuré YAML (ajout 1.2 TSI 105ch phase 2),
    vlevel V2 (Golf = best-seller historique compact EU), low_profile_canary false
  - Wikilinks gammes ajoutés
  - Section "Véhicules proches" ajoutée (plate-forme PQ35 — Audi A3 8P,
    Seat Leon Mk2, Skoda Octavia Mk2)
  - Ajout 1.2 TSI 105 ch (phase 2 Golf VI, manquait en source)
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
  make: volkswagen
  model: golf-6
  generation: vi
  years:
    - 2008
    - 2012
  type_id: null
  motorizations:
    - code: CBZB
      fuel: essence
      power_hp: 105
      displacement_cc: 1197
      note: 1.2 TSI 4-cyl turbo (phase 2 Golf VI)
    - code: CAXA
      fuel: essence
      power_hp: 122
      displacement_cc: 1390
      note: 1.4 TSI 4-cyl turbo
    - code: CAVD
      fuel: essence
      power_hp: 160
      displacement_cc: 1390
      note: 1.4 TSI 4-cyl turbo+compresseur (Twincharger)
    - code: CDAA
      fuel: essence
      power_hp: 160
      displacement_cc: 1798
      note: 1.8 TSI 4-cyl turbo
    - code: CCZB
      fuel: essence
      power_hp: 210
      displacement_cc: 1984
      note: 2.0 TSI GTI Mk6
    - code: CDLF
      fuel: essence
      power_hp: 270
      displacement_cc: 1984
      note: 2.0 TSI Golf R Mk6 (4WD 4Motion)
    - code: CAYC
      fuel: diesel
      power_hp: 90
      displacement_cc: 1598
      note: 1.6 TDI common-rail
    - code: CAYC
      fuel: diesel
      power_hp: 105
      displacement_cc: 1598
      note: 1.6 TDI common-rail
    - code: CBDB
      fuel: diesel
      power_hp: 110
      displacement_cc: 1968
      note: 2.0 TDI common-rail
    - code: CBAB
      fuel: diesel
      power_hp: 140
      displacement_cc: 1968
      note: 2.0 TDI common-rail
    - code: CFGB
      fuel: diesel
      power_hp: 170
      displacement_cc: 1968
      note: 2.0 TDI GTD Mk6
  vlevel: V2
  low_profile_canary: false
content_hash: sha256:6c01bea9d2b1eb3452a0c3e58fd061a406fe717a9e469b5e3b6d9b6740c51e01
confidence_score: 0.24
---

# Volkswagen Golf 6

> 📥 **Proposition Phase F** — extraite par `recycle-from-rag.py`. Sections H2 ordre canon Phase 4 plan deja-verifier-existant.

## Présentation

La **Volkswagen Golf 6** (génération VI, code interne 5K) est une compacte du segment C produite de **2008 à 2012**. Elle a remplacé la Golf V et fut elle-même remplacée par la Golf VII en 2012. Plate-forme PQ35 partagée avec plusieurs véhicules du groupe VAG. Disponible en 3 portes, 5 portes, Variant (break) et Cabriolet, plus versions sportives GTI, GTD et R.

### Carrosseries

- **3 portes** (sportif, GTI/R principalement)
- **5 portes** (la plus vendue, familial)
- **Variant (break)** : version familiale, coffre 505 L (1 495 L sièges rabattus)
- **Cabriolet** : lancé 2011, capote en toile (au lieu du toit rigide rétractable Golf V)

### Versions sport

- **GTI** : 2.0 TSI 210 ch (CCZB)
- **GTD** : 2.0 TDI 170 ch (CFGB), version diesel sportive
- **R** : 2.0 TSI 270 ch (CDLF), 4WD 4Motion, top de gamme performance

### Véhicules proches (plate-forme PQ35 partagée)

| Modèle | Années | Ce qui est partagé |
|---|---|---|
| [[audi-a3]] (8P) | 2003-2012 | Plate-forme PQ35, moteurs TSI/TDI, freinage, train roulant |
| [[audi-tt]] (8J) | 2006-2014 | Plate-forme PQ35, moteurs 2.0 TSI/TDI |
| [[seat-leon]] (Mk2) | 2005-2012 | Plate-forme PQ35, moteurs TSI/TDI |
| [[seat-altea]] | 2004-2015 | Plate-forme PQ35, moteurs |
| [[skoda-octavia]] (Mk2) | 2004-2013 | Plate-forme PQ35, moteurs TSI/TDI |
| [[skoda-superb]] (Mk2) | 2008-2015 | Plate-forme PQ35 allongée, moteurs |
| [[volkswagen-passat-b6]] | 2005-2010 | Plate-forme partielle, moteurs TSI/TDI |
| [[volkswagen-tiguan]] (Mk1) | 2007-2016 | Plate-forme PQ35 SUV, moteurs |

## Motorisations

### Essence

| Moteur | Puissance | Code moteur | Notes |
|---|---|---|---|
| 1.2 TSI | 105 ch | CBZB | 4-cyl turbo, phase 2 Golf VI |
| 1.4 TSI | 122 ch | CAXA | 4-cyl turbo |
| 1.4 TSI | 160 ch | CAVD | Twincharger (turbo + compresseur volumétrique) |
| 1.8 TSI | 160 ch | CDAA | 4-cyl turbo |
| 2.0 TSI GTI | 210 ch | CCZB | Sportive Mk6 |
| 2.0 TSI Golf R | 270 ch | CDLF | Sportive 4WD 4Motion |

### Diesel

| Moteur | Puissance | Code moteur | Notes |
|---|---|---|---|
| 1.6 TDI | 90 / 105 ch | CAYC | Common-rail |
| 2.0 TDI | 110 ch | CBDB | Common-rail entrée de gamme |
| 2.0 TDI | 140 ch | CBAB | Common-rail le plus vendu |
| 2.0 TDI GTD | 170 ch | CFGB | Sportive diesel |

## Pièces compatibles (top gammes)

### Pièces d'usure principales

- **Freinage** : [[plaquette-de-frein]] avant (30-50 000 km — usure plus longue Golf VI grâce ABS optimisé), [[disque-de-frein]] avant (60-80 000 km), arrière disques sur toutes versions
- **Filtration** : [[filtre-a-huile]] (chaque vidange), [[filtre-a-air]] (40 000 km — intervalle plus long), [[filtre-habitacle]] (20 000 km), [[filtre-a-carburant]] TDI (60 000 km)
- **Distribution** : selon motorisation
  - 1.4 TSI (CAXA/CAVD) : **chaîne (mais étirement prématuré fréquent — voir Particularités)**
  - 1.6 TDI : courroie 120 000 km / 5 ans
  - 2.0 TDI : courroie 120 000 km / 5 ans
  - 2.0 TSI : chaîne (sans entretien normal)

### Références OEM courantes

| Pièce | Référence VAG |
|---|---|
| Filtre à huile 2.0 TDI | 03L115562 |
| Filtre à air 2.0 TDI | 1K0129620D |
| Plaquettes avant | 5K0698151 |
| Disques avant | 5K0615301 |
| Kit distribution 2.0 TDI | Gates / Contitech (selon fournisseur) |

> Indicatif — voir catalogue site pour références complètes par motorisation et année.

## Particularités d'entretien

### Problèmes connus

#### Moteur 1.4 TSI (CAXA / CAVD)

- **Chaîne distribution** : étirement prématuré (symptôme : bruit type claquement au démarrage à froid)
- **Tendeur chaîne** : défaillant — à remplacer préventivement même en l'absence de symptôme
- **Solution** : kit chaîne complet (tendeur + guides + chaîne), ~1 200-1 800 € MO incluse

#### Moteur 2.0 TDI (common-rail CR)

- **Injecteurs piezo** : défaillance possible après 150 000 km
- **Vanne EGR** : encrassement, nettoyage ou suppression (selon législation marché)
- **FAP (Filtre à Particules)** : régénérations fréquentes en ville (trajets courts dégradent le FAP)

#### Boîte DSG (DQ250 ou DQ200 selon motorisation)

- **Mécatronique** : défaillances possibles (à-coups, passage neutre intempestif)
- **Embrayages** : usure si conduite urbaine pure (boîte secs DQ200) ou mauvais entretien (boîte humides DQ250)
- **Vidange huile** : tous les 60 000 km **strictement obligatoire** (sinon usure mécatronique accélérée)

#### Électricité

- **Module confort** : problèmes vitres électriques, centralisation, alarme
- **Pompe à eau électrique (TSI)** : défaillante après 100 000 km (point sensible documenté)

### Intervalles d'entretien

| Opération | Fréquence |
|---|---|
| Vidange Service flexible | 15-30 000 km selon usage et capteur d'huile |
| Vidange Recommandé | 15 000 km / 1 an |
| Liquide de frein | 2 ans |
| Boîte DSG | **60 000 km strictement** |

### Conseils propriétaire

1. **Huile moteur** : 5W-30 norme **VW 504.00 / 507.00** (Long Life)
2. **Alternative recommandée** : 5W-40 non Long Life + vidanges 15 000 km (mieux pour usage urbain pur, évite encrassement)
3. **Liquide refroidissement** : **G12++ (rose/violet)** — ne pas mélanger avec G11 (vert) ni G13 (lila)
4. **Boîte DSG** : vidange stricte 60 000 km, huile spécifique (G 052 182 A2 pour DQ250, G 052 512 A2 pour DQ200)

### Spécificités par version

#### Golf GTI Mk6 (210 ch)

- 2.0 TSI CCZB
- Freinage plus gros (disques 312 mm avant)
- **Différentiel XDS** (freinage sélectif électronique sur roue intérieure)
- Mode sport sélectable
- Huile **5W-40** recommandée (non Long Life)
- Châssis surbaissé, suspensions raffermies
- Sièges sport tartan emblématique

#### Golf R Mk6 (270 ch)

- 2.0 TSI CDLF
- **Transmission 4WD 4Motion** (Haldex génération 4)
- Freinage 345 mm avant
- Entretien renforcé recommandé (huile changée plus fréquemment)
- 0-100 km/h en 5,7 s

#### Golf GTD Mk6 (170 ch)

- 2.0 TDI CFGB
- Performances diesel
- FAP standard, AdBlue selon année
- Huile spécifique FAP (504.00 / 507.00)
- Conso mixte 5,3 L/100 km (excellent rapport perfs/conso)

## Questions fréquentes

### Le 1.4 TSI Golf 6 est-il fiable ?

Point sensible majeur : étirement prématuré de la chaîne distribution (CAXA/CAVD). Surveiller bruit au démarrage à froid. Remplacement préventif kit chaîne ~1 200-1 800 € recommandé entre 100 000 et 150 000 km.

### La boîte DSG est-elle à éviter ?

Non, mais respecter strictement la vidange 60 000 km (huile spécifique). Boîte humide DQ250 plus fiable que sèche DQ200 en usage urbain.

### Quelle huile pour ma Golf 6 ?

5W-30 norme VW 504.00 / 507.00 (Long Life) si vidange étendue 30 000 km. Mieux : 5W-40 non Long Life + vidanges 15 000 km en usage urbain pour limiter encrassement.

### Pièces compatibles avec d'autres VAG ?

Très large recouvrement avec [[audi-a3]] (8P), [[seat-leon]] (Mk2), [[skoda-octavia]] (Mk2), [[volkswagen-tiguan]] (Mk1) : moteurs TSI/TDI, freinage, électronique, train roulant — plate-forme PQ35 commune.

### Différence GTI / GTD / R ?

- **GTI** : essence sportive 210 ch traction (badge tartan emblématique)
- **GTD** : diesel sportif 170 ch traction (perfs proches GTI mais conso 5,3 L/100 km)
- **R** : essence top performance 270 ch 4WD 4Motion (la plus rapide Golf 6, série limitée)

## Sources et provenance

Sources canoniques utilisées (cf. `_quality/sources-brief.md` Phase 3) :

- **Wikipedia FR — Volkswagen Golf VI** : https://fr.wikipedia.org/wiki/Volkswagen_Golf_VI (license `CC-BY-SA-3.0`, capture intégrale via preset `wikipedia-vehicle` PR2 livré). Action humaine Phase 3.
- **caradisiac fiche technique Golf 6** : https://www.caradisiac.com/fiches-techniques/modele--volkswagen-golf-6/ (license `proprietary-citation-only`, ≤200 mots citation).
- **OEM VAG Golf VI workshop manual** : Phase 7 différé (preset `manuel-constructeur-pdf` à livrer skill PR2).

## Points à vérifier

- [ ] Vérifier `entity_data.type_id` aligné DB `__auto_type` (Golf VI 5K millésimes 2008-2012, multiple type_id par motorisation/carrosserie)
- [ ] Confirmer `vlevel: V2` (Golf = best-seller historique compact EU, top 3 ventes Allemagne)
- [x] **2026-05-02** : `low_profile_canary: false` (best-seller, pas canary R8)
- [x] **2026-05-02** : `motorizations[]` structuré YAML (11 entrées : 6 essence + 5 diesel)
- [x] **2026-05-02** : 1.2 TSI 105 ch (phase 2) ajouté (manquait en source)
- [x] **2026-05-02** : "Véhicules proches" ajouté (8 modèles VAG plate-forme PQ35)
- [ ] Capturer Wikipedia FR Volkswagen Golf VI via extension Obsidian preset `wikipedia-vehicle`
- [ ] Construire `_coverage/volkswagen-golf-6.coverage.yaml` (Phase 5 plan parent)
- [ ] Décider promotion → `wiki/vehicles/volkswagen-golf-6.md` (commit message obligatoire `promotion-from-proposals: volkswagen-golf-6`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
