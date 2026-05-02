---
schema_version: 1.0.0
id: vehicle:peugeot-206
entity_type: vehicle
slug: peugeot-206
title: Peugeot 206
aliases:
  - Peugeot 206 phase 1
  - Peugeot 206 phase 2
  - Peugeot 206+
  - Peugeot 206 plus
  - Peugeot 206 GTI
  - Peugeot 206 RC
  - Peugeot 206 CC
  - Peugeot 206 SW
lang: fr
created_at: '2026-04-29'
updated_at: '2026-05-02'
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/vehicles/peugeot-206.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:recycle-from-rag@v0.1
  promoted_from: null
lineage_id: 019dd8ee-daf3-74cc-9687-439ae70303de
parents: []
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: |
  Phase F batch ADR-031. Recyclé depuis automecanik-rag par
  recycle-from-rag.py. Source body sha256=
  8d75d4860580b5f0867f07b1dd76053cb5ac969e8ed25f341a0c8afed7ac1d2a.

  Phase 4 plan deja-verifier-existant 2026-05-02 :
  - Sections H2 alignées sur ordre canon _templates/new-vehicle.md
  - Titre "Fiche véhicule - Peugeot 206" → "Peugeot 206" (FR canon)
  - aliases [] → 9 entrées (variantes commerciales)
  - target_classes [] → [KB_Knowledge, KB_Catalog]
  - entity_data complété : generation unique-T1-T3, years [1998, 2013],
    motorizations[] structuré YAML, vlevel V2 (best-seller historique
    Peugeot >9M unités), low_profile_canary false
  - Wikilinks gammes ajoutés
  - Phases développées : Phase 1 (1998-2003), Phase 2 (2003-2009),
    206+ (2009-2013) — manquaient en source
  - 206 SW (break) développée — mentionnée mais pas détaillée en source
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
  make: peugeot
  model: '206'
  generation: unique-t1-t3
  years:
    - 1998
    - 2013
  type_id: null
  motorizations:
    - code: HFX
      fuel: essence
      power_hp: 60
      displacement_cc: 1124
      note: 1.1i TU1JP
    - code: KFW
      fuel: essence
      power_hp: 75
      displacement_cc: 1360
      note: 1.4i TU3JP
    - code: NFU
      fuel: essence
      power_hp: 88
      displacement_cc: 1587
      note: 1.6i TU5JP4 — variante 110 ch sur GTI
    - code: NFU
      fuel: essence
      power_hp: 110
      displacement_cc: 1587
      note: 1.6i TU5JP4 — sur 206 GTI
    - code: RFK
      fuel: essence
      power_hp: 137
      displacement_cc: 1997
      note: 2.0 GTI EW10J4
    - code: RFK
      fuel: essence
      power_hp: 177
      displacement_cc: 1997
      note: 2.0 RC EW10J4S — sportive haut de gamme
    - code: 8HX
      fuel: diesel
      power_hp: 68
      displacement_cc: 1398
      note: 1.4 HDi DV4TD
    - code: 9HY
      fuel: diesel
      power_hp: 90
      displacement_cc: 1560
      note: 1.6 HDi DV6
    - code: 9HZ
      fuel: diesel
      power_hp: 110
      displacement_cc: 1560
      note: 1.6 HDi DV6 haut de gamme
    - code: RHY
      fuel: diesel
      power_hp: 90
      displacement_cc: 1997
      note: 2.0 HDi DW10TD
  vlevel: V2
  low_profile_canary: false
content_hash: sha256:1095e93c018ed389fed2b42485af5a583a4563d64dda52ccc62fa42919e77320
confidence_score: 0.24
---

# Peugeot 206

> 📥 **Proposition Phase F** — extraite par `recycle-from-rag.py`. Sections H2 ordre canon Phase 4 plan deja-verifier-existant.

## Présentation

La **Peugeot 206** est une citadine du segment B produite par Peugeot de **1998 à 2013** (15 ans de production). Best-seller historique Peugeot avec **plus de 9 millions d'unités** vendues mondialement, succédant à la 205 et précédant la 207.

### Phases successives

- **Phase 1 (1998-2003)** : lancement, design fluide signé Murat Günak. Tous types de carrosserie introduits progressivement
- **Phase 2 (2003-2009)** : restylage face avant, intérieur amélioré, motorisations HDi
- **206+ (2009-2013)** : version low-cost prolongée pour marchés secondaires (Europe Est, Amérique Sud), face avant inspirée de la 207

### Carrosseries

- **3 portes** (sportif, GTI/RC, CC)
- **5 portes** (familial, la plus vendue)
- **CC (Coupé Cabriolet)** : toit rigide rétractable, lancé 2000, succès commercial
- **SW (Station Wagon, break)** : lancé 2002, version familiale étendue (4,03 m)
- **RC** : 2.0 16V 177 ch (2003-2007)
- **GTI** : 1.6 16V 110 ch ou 2.0 16V 137 ch (selon génération)

### Véhicules proches (plate-forme partagée / pièces partagées)

| Modèle | Années | Ce qui est partagé |
|---|---|---|
| [[citroen-c2]] | 2003-2009 | Plate-forme PSA PF1, moteurs TU/HDi, freinage |
| [[citroen-c3]] (génération I) | 2002-2009 | Plate-forme PF1, moteurs TU/HDi, train roulant |
| [[peugeot-1007]] | 2005-2009 | Moteurs TU/HDi, électronique partagée |

## Motorisations

### Essence

| Moteur | Puissance | Code moteur | Notes |
|---|---|---|---|
| 1.1i | 60 ch | HFX (TU1JP) | Entrée de gamme, atmosphérique |
| 1.4i | 75 ch | KFW (TU3JP) | Atmosphérique, le plus répandu |
| 1.6i 16V | 88 ch | NFU (TU5JP4) | Atmosphérique |
| 1.6i 16V | 110 ch | NFU (TU5JP4) | Sur 206 GTI essence |
| 2.0 GTI 16V | 137 ch | RFK (EW10J4) | Sportive |
| 2.0 RC 16V | 177 ch | RFK (EW10J4S) | Sportive haut de gamme (2003-2007) |

### Diesel

| Moteur | Puissance | Code moteur | Notes |
|---|---|---|---|
| 1.4 HDi | 68 ch | 8HX (DV4TD) | Diesel entrée de gamme |
| 1.6 HDi | 90 / 110 ch | 9HY / 9HZ (DV6) | 110 ch = haut de gamme HDi |
| 2.0 HDi | 90 ch | RHY (DW10TD) | Plus ancien, fin de carrière phase 1 |

## Pièces compatibles (top gammes)

### Pièces d'usure principales

- **Freinage** : [[plaquette-de-frein]] avant (30-40 000 km), [[disque-de-frein]] avant (60-80 000 km), tambours arrière (standard plupart versions), kit frein arrière (mâchoires + cylindres)
- **Filtration** : [[filtre-a-huile]] (chaque vidange), [[filtre-a-air]] (30 000 km), [[filtre-habitacle]] (15 000 km), [[filtre-a-carburant]] HDi (60 000 km)
- **Distribution** : selon motorisation
  - Essence TU (1.1/1.4/1.6) : courroie 80 000 km / 5 ans
  - HDi DV4/DV6 (1.4/1.6) : courroie 100 000 km / 10 ans
  - HDi DW10 (2.0) : courroie 120 000 km

### Références OEM courantes

| Pièce | Référence Peugeot |
|---|---|
| Filtre à huile 1.4 HDi | 1109AY |
| Filtre à air 1.4 HDi | 1444VJ |
| Plaquettes avant | 4254.22 |
| Disques avant | 4249.G5 |
| Kit distribution 1.4 HDi | 0831V4 |

> Indicatif — voir catalogue site pour références complètes par motorisation et année.

## Particularités d'entretien

### Problèmes connus

#### Moteur 1.4 HDi (DV4)

- **Injecteurs** : encrassement, démarrage difficile
- **Vanne EGR** : colmatage fréquent (perte de puissance, fumée noire)
- **Poulie damper** : éclatement (bruit moteur caractéristique)

#### Moteur 1.6 HDi (DV6)

- **Volant moteur bimasse** : usure prématurée (bruit au ralenti)
- **Turbo** : contrôle régulier huile (vidanges respectées impératives)

#### Électricité

- **BSI (Boîtier de Servitude Intelligent)** : dysfonctionnements (essuie-glaces, centralisation, ventilation)
- **Antidémarrage** : problèmes transpondeur clé (clé qui n'ouvre plus, antidémarrage qui s'enclenche)

#### Train roulant

- **Cardans** : soufflets à surveiller
- **Roulements avant** : usure normale 100 000 km
- **Triangles de suspension** : silent-blocs

### Intervalles d'entretien

| Opération | Fréquence |
|---|---|
| Vidange essence | 15 000 km / 1 an |
| Vidange diesel | 20 000 km / 1 an |
| Liquide de frein | 2 ans |
| Filtre habitacle | 15 000 km / 1 an |

### Conseils propriétaire

1. **Huile moteur diesel** : 5W-30 spéciale FAP si équipé (DV6 9HZ avec FAP fin phase 2)
2. **Essence** : 10W-40 ou 5W-40 selon préconisation constructeur
3. **Liquide refroidissement** : type Revkogel 2000 (vert) — ne pas mélanger autres types
4. **LHM** : si direction assistée hydraulique (citadines anciennes phase 1, fluide vert spécifique)

### Spécificités par version

#### Peugeot 206 RC (2003-2007)

- 2.0 16V 177 ch (RFK EW10J4S)
- Freinage renforcé : disques ventilés 4 pistons avant
- Distribution renforcée
- Suspensions Bilstein
- Entretien plus fréquent recommandé

#### Peugeot 206 CC (2000-2007)

- Coupé Cabriolet, toit rigide rétractable
- **Vérins de capote** : contrôle annuel (point sensible — fuite hydraulique)
- **Joints de capote** : entretien spécifique annuel
- **Bouchon de coffre** : verrouillage électrique fragile

#### Peugeot 206 SW (2002-2010)

- Break (Station Wagon), 4,03 m
- Coffre 365 L (1 230 L sièges rabattus)
- Familial, popularité moindre que la 5 portes mais usage pratique reconnu

#### Peugeot 206+ (2009-2013)

- Version low-cost prolongée pour marchés Europe Est + Amérique Sud
- Face avant inspirée de la 207
- Motorisations restreintes (1.1i, 1.4i, 1.4 HDi)

## Questions fréquentes

### Quand changer la courroie de distribution sur ma 206 ?

Essence TU : 80 000 km / 5 ans. HDi DV4/DV6 : 100 000 km / 10 ans. HDi DW10 : 120 000 km. Ne pas dépasser sous peine de casse moteur.

### Le 1.4 HDi est-il fiable ?

Globalement oui, mais points sensibles : vanne EGR (encrassement), injecteurs (encrassement), poulie damper. Entretien régulier indispensable. ~2 000 € moyenne réparation EGR + injecteurs.

### Quelle huile pour ma 206 1.6 HDi ?

5W-30 norme PSA si équipée FAP (DV6 9HZ avec FAP). Sinon 5W-30 ou 5W-40 standard PSA.

### Pièces compatibles avec d'autres PSA ?

Oui, large recouvrement avec [[citroen-c2]], [[citroen-c3]] (génération I), [[peugeot-1007]] : moteurs TU/HDi, freinage, train roulant.

### La 206 RC est-elle une bonne voiture sportive d'occasion ?

Oui, l'une des meilleures GTI françaises de l'époque (177 ch / 1 100 kg = excellent rapport poids/puissance). Mais entretien rigoureux requis (distribution, freinage, suspensions). Cote stable depuis 2018 grâce au statut "youngtimer".

## Sources et provenance

Sources canoniques utilisées (cf. `_quality/sources-brief.md` Phase 3) :

- **Wikipedia FR — Peugeot 206** : https://fr.wikipedia.org/wiki/Peugeot_206 (license `CC-BY-SA-3.0`, capture intégrale via preset `wikipedia-vehicle` PR2 livré). Action humaine Phase 3.
- **caradisiac fiche technique 206** : https://www.caradisiac.com/fiches-techniques/modele--peugeot-206/ (license `proprietary-citation-only`, ≤200 mots citation).
- **OEM PSA Peugeot 206 workshop manual** : Phase 7 différé (preset `manuel-constructeur-pdf` à livrer skill PR2).

## Points à vérifier

- [ ] Vérifier `entity_data.type_id` aligné DB `__auto_type` (206 millésimes 1998-2013, multiple type_id par phase probablement)
- [ ] Confirmer `vlevel: V2` (best-seller historique Peugeot, 9M unités, top vente FR années 2000)
- [x] **2026-05-02** : `low_profile_canary: false` (best-seller, pas canary R8)
- [x] **2026-05-02** : `motorizations[]` structuré YAML (10 entrées : 6 essence + 4 diesel)
- [x] **2026-05-02** : Phases (Phase 1, Phase 2, 206+) développées (manquaient en source)
- [x] **2026-05-02** : 206 SW (break) développée (manquait en source)
- [ ] Capturer Wikipedia FR Peugeot 206 via extension Obsidian preset `wikipedia-vehicle`
- [ ] Construire `_coverage/peugeot-206.coverage.yaml` (Phase 5 plan parent)
- [ ] Décider promotion → `wiki/vehicles/peugeot-206.md` (commit message obligatoire `promotion-from-proposals: peugeot-206`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
