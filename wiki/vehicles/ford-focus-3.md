---
schema_version: 1.0.0
id: vehicle:ford-focus-3
entity_type: vehicle
slug: ford-focus-3
title: Ford Focus 3
aliases:
- Focus 3
- Focus III
- Ford Focus III
- Focus C346
- Focus ST Mk3
- Focus RS Mk3
lang: fr
created_at: '2026-04-29'
updated_at: '2026-05-02'
truth_level: L3
source_refs:
- kind: recycled
  origin_repo: automecanik-rag
  origin_path: knowledge/vehicles/ford-focus-3.md
  captured_at: '2026-04-29'
provenance:
  ingested_by: skill:recycle-from-rag@v0.1
  promoted_from: null
lineage_id: 019dd8ee-daf1-7121-8b9a-8e158fec994b
parents: []
review_status: approved
reviewed_by: skill:phase6-promotion-batch@claude
reviewed_at: '2026-05-02T20:17:01Z'
review_notes: "Phase F batch ADR-031. Recyclé depuis automecanik-rag par\nrecycle-from-rag.py.\
  \ Source body sha256=\n89e64f2b6d0c635377ab946775e05f488e6fa6e8b520323f4df0db1e9fe189a4.\n\
  \nPhase 4 plan deja-verifier-existant 2026-05-02 :\n- Sections H2 alignées sur ordre\
  \ canon _templates/new-vehicle.md\n- Titre \"Fiche vehicule - Ford Focus 3\" → \"\
  Ford Focus 3\" (FR canon)\n- aliases [] → [Focus 3, Focus III, Ford Focus III, Focus\
  \ C346,\n  Focus ST Mk3, Focus RS Mk3]\n- target_classes [] → [KB_Knowledge, KB_Catalog]\n\
  - entity_data complété : generation iii, years [2011, 2018],\n  motorizations[]\
  \ structuré YAML, vlevel V3, low_profile_canary false\n- Wikilinks gammes ajoutés\
  \ (plaquette-de-frein, filtre-a-air, etc.)\n- Section \"Spécificités par version\"\
  \ ajoutée (ST/RS) — manquante en source\n- Section \"Estate (break)\" développée\
  \ — mentionnée mais pas détaillée en source\n- FAQ 5 questions ajoutée\n\nÀ reviewer\
  \ humainement avant promotion vers wiki/vehicles/.\n"
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
entity_data:
  make: ford
  model: focus-3
  generation: iii
  years:
  - 2011
  - 2018
  type_id: null
  motorizations:
  - code: M1DA
    fuel: essence
    power_hp: 100
    displacement_cc: 999
    note: 1.0 EcoBoost 3-cylindres turbo
  - code: M2DA
    fuel: essence
    power_hp: 125
    displacement_cc: 999
    note: 1.0 EcoBoost 3-cylindres turbo
  - code: PNDA
    fuel: essence
    power_hp: 105
    displacement_cc: 1596
    note: 1.6 Ti-VCT atmosphérique
  - code: JTDA
    fuel: essence
    power_hp: 150
    displacement_cc: 1596
    note: 1.6 EcoBoost turbo
  - code: R9DA
    fuel: essence
    power_hp: 250
    displacement_cc: 1999
    note: 2.0 EcoBoost ST Mk3
  - code: R9MH
    fuel: essence
    power_hp: 350
    displacement_cc: 2261
    note: 2.3 EcoBoost RS Mk3 (transmission 4WD AWD)
  - code: XWDA
    fuel: diesel
    power_hp: 95
    displacement_cc: 1499
    note: 1.5 TDCi (post 2014)
  - code: XWDA
    fuel: diesel
    power_hp: 120
    displacement_cc: 1499
    note: 1.5 TDCi (post 2014)
  - code: T1DA
    fuel: diesel
    power_hp: 95
    displacement_cc: 1560
    note: 1.6 TDCi
  - code: T1DA
    fuel: diesel
    power_hp: 115
    displacement_cc: 1560
    note: 1.6 TDCi
  - code: UFDB
    fuel: diesel
    power_hp: 140
    displacement_cc: 1997
    note: 2.0 TDCi
  - code: UFDB
    fuel: diesel
    power_hp: 163
    displacement_cc: 1997
    note: 2.0 TDCi haut de gamme
  vlevel: V3
  low_profile_canary: false
content_hash: sha256:21574f9ce771e8f73f4323e6a3e5cb05736290cf55a66a559b5c21ad4be02440
confidence_score: 0.24
---

# Ford Focus 3

## Présentation

La **Ford Focus 3** (génération III, code C346) est une compacte du segment C produite de **2011 à 2018**. Elle a remplacé la Focus II et fut elle-même remplacée par la Focus IV en 2018. Disponible en 5 portes, 4 portes (berline, marchés EU/US), Estate (break) et versions sportives ST et RS.

### Carrosseries

- **5 portes** (la plus répandue en France)
- **4 portes berline** (peu vendue en Europe, principal marché US)
- **Estate (break)** : version familiale, coffre 476 L (1 502 L sièges rabattus), populaire en Europe pour usage pro/familial
- **ST** : 5 portes uniquement, sportive 250 ch
- **RS** : 5 portes 4WD, sportive haute performance 350 ch (Mk3 RS lancée 2016)

### Véhicules proches (plate-forme partagée / pièces partagées)

| Modèle | Années | Ce qui est partagé |
|---|---|---|
| [[ford-c-max]] (génération II) | 2010-2019 | Plate-forme Ford C1, moteurs EcoBoost/TDCi, freinage |
| [[ford-grand-c-max]] | 2010-2019 | Plate-forme C1 allongée, moteurs Focus |
| [[ford-kuga]] (génération II) | 2012-2019 | Moteurs EcoBoost/TDCi, électronique partagée |
| [[ford-escape]] (génération III, US) | 2012-2019 | Plate-forme C1, moteurs |

## Motorisations

### Essence

| Moteur | Puissance | Code moteur | Notes |
|---|---|---|---|
| 1.0 EcoBoost | 100 / 125 ch | M1DA / M2DA | 3-cylindres turbo, downsizing emblématique Ford |
| 1.6 Ti-VCT | 105 / 125 ch | PNDA | Atmosphérique, fin de carrière |
| 1.6 EcoBoost | 150 / 182 ch | JTDA | Turbo |
| 2.0 EcoBoost ST | 250 ch | R9DA | Sportive, traction avant + différentiel mécanique |
| 2.3 EcoBoost RS | 350 ch | R9MH | Sportive 4WD AWD avec mode Drift |

### Diesel

| Moteur | Puissance | Code moteur | Notes |
|---|---|---|---|
| 1.5 TDCi | 95 / 120 ch | XWDA | Post-2014, remplace 1.6 TDCi |
| 1.6 TDCi | 95 / 115 ch | T1DA | 2011-2014 principalement |
| 2.0 TDCi | 140 / 163 ch | UFDB | Haut de gamme diesel |

## Pièces compatibles (top gammes)

### Pièces d'usure principales

- **Freinage** : [[plaquette-de-frein]] avant (30-40 000 km), arrière (disques sur toutes versions, 60-80 000 km), [[disque-de-frein]] avant (60-80 000 km — plus gros sur ST/RS)
- **Filtration** : [[filtre-a-huile]] (chaque vidange), [[filtre-a-air]] (40 000 km), [[filtre-habitacle]] (20 000 km), [[filtre-a-carburant]] diesel (60 000 km)
- **Distribution** : selon motorisation
  - 1.0 EcoBoost : courroie 150 000 km / 10 ans (courroie wet belt sur certaines versions — point d'attention)
  - 1.6 EcoBoost : chaîne (sans entretien normal)
  - 1.6 TDCi : courroie 125 000 km / 10 ans
  - 2.0 TDCi : courroie 150 000 km / 10 ans
  - 2.3 EcoBoost RS : chaîne renforcée

## Particularités d'entretien

### Problèmes connus

#### Moteur 1.0 EcoBoost

- **Durite liquide refroidissement** : fuite, **rappel constructeur** (durite plastique sous turbo, remplacement gratuit selon série)
- **Surchauffe** : liée aux fuites durites (joint culasse à risque si non traité)
- **Joint de culasse** : sur versions affectées par surchauffe

#### Boîte Powershift (DCT 6 rapports double-embrayage à sec)

- **Embrayages** : usure prématurée (boîte conçue pour conduite mixte, dégrade vite en urbain pur)
- **À-coups** : en ville, basse vitesse — symptomatique
- **Solution** : mise à jour logiciel (TCM update) + remplacement embrayages (~1 500-2 500 €)

#### Électricité

- **Sync (1, 2, 3)** : problèmes écran tactile et reconnaissance vocale
- **Batterie** : décharge si arrêt prolongé (consommateurs cachés)

### Intervalles d'entretien

| Opération | Fréquence |
|---|---|
| Vidange essence | 20 000 km / 1 an |
| Vidange diesel | 20 000 km / 1 an |
| Vidange Powershift DCT | **50 000 km obligatoire** (sinon usure embrayages accélérée) |
| Liquide de frein | 2 ans |

### Conseils propriétaire

1. **Huile moteur** : 5W-20 (EcoBoost spécifique norme Ford WSS-M2C948-B), 5W-30 (autres)
2. **Liquide refroidissement** : organique Ford WSS-M97B44-D (rouge, ne pas mélanger)
3. **Boîte Powershift** : vidange recommandée 50 000 km, OBLIGATOIRE pour limiter usure embrayages

### Spécificités par version

#### Ford Focus ST Mk3 (2012-2018, 250 ch)

- 2.0 EcoBoost (R9DA), 0-100 km/h en 6,5 s
- Freinage renforcé (disques 320 mm avant)
- Différentiel mécanique avant (Quaife) sur certaines séries
- Chassis surbaissé (10 mm), suspensions raffermies
- Sièges Recaro de série

#### Ford Focus RS Mk3 (2016-2018, 350 ch)

- 2.3 EcoBoost (R9MH), 0-100 km/h en 4,7 s
- **Transmission 4WD AWD** (Ford Performance AWD)
- Mode **Drift** (couple arrière maximal pour glissades contrôlées)
- Freinage Brembo 350 mm avant
- Chassis ultra-rigidifié + amortisseurs adaptatifs
- Modes de conduite (Normal/Sport/Track/Drift)

## Questions fréquentes

### Le 1.0 EcoBoost est-il fiable ?

Oui en grande majorité, mais **rappel constructeur** sur durite liquide refroidissement (séries 2012-2014). Vérifier que le rappel a été effectué (numéro VIN sur site Ford). Sinon point sensible.

### La boîte Powershift est-elle à éviter ?

À éviter en usage urbain pur (embrayages secs s'usent vite). Adaptée pour usage mixte (route + ville). Vidange tous les 50 000 km strictement obligatoire pour limiter l'usure.

### Quelle huile pour ma Focus 1.0 EcoBoost ?

5W-20 norme Ford WSS-M2C948-B uniquement. Une huile non conforme dégrade le tendeur de chaîne et la pompe à huile.

### Pièces compatibles avec d'autres Ford ?

Oui, large recouvrement avec [[ford-c-max]], [[ford-kuga]], [[ford-escape]] : moteurs EcoBoost/TDCi, freinage, électronique partagée.

### Différence ST et RS ?

Le **ST** est une sportive traction (250 ch, ~30 000 € neuf), le **RS** est une 4WD performance (350 ch, ~40 000 € neuf, série limitée). Le RS Mk3 est l'unique 4WD de la gamme Focus, héritage Focus RS Mk1/Mk2.

## Sources et provenance

Sources canoniques utilisées (cf. `_quality/sources-brief.md` Phase 3) :

- **Wikipedia FR — Ford Focus** : https://fr.wikipedia.org/wiki/Ford_Focus (license `CC-BY-SA-3.0`, capture intégrale via preset `wikipedia-vehicle` PR2 livré). Action humaine Phase 3.
- **caradisiac fiche technique Focus** : https://www.caradisiac.com/fiches-techniques/modele--ford-focus/ (license `proprietary-citation-only`, ≤200 mots citation).
- **OEM Ford Focus III workshop manual** : Phase 7 différé (preset `manuel-constructeur-pdf` à livrer skill PR2).

## Points à vérifier

- [ ] Vérifier `entity_data.type_id` aligné DB `__auto_type` (Focus C346 millésimes 2011-2018)
- [ ] Confirmer `vlevel: V3` (Focus = vente moyenne, segment C populaire)
- [x] **2026-05-02** : `low_profile_canary: false` (Focus = volume notable EU/US)
- [x] **2026-05-02** : `motorizations[]` structuré YAML (12 entrées : 6 essence + 6 diesel)
- [x] **2026-05-02** : Spécificités ST/RS ajoutées (manquaient en source)
- [ ] Capturer Wikipedia FR Ford Focus via extension Obsidian preset `wikipedia-vehicle`
- [ ] Construire `_coverage/ford-focus-3.coverage.yaml` (Phase 5 plan parent)
- [ ] Décider promotion → `wiki/vehicles/ford-focus-3.md` (commit message obligatoire `promotion-from-proposals: ford-focus-3`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
