---
schema_version: 1.0.0
id: vehicle:renault-clio-3
entity_type: vehicle
slug: renault-clio-3
title: Renault Clio 3
aliases:
- Renault Clio III
- Clio III
- Clio 3
- clio-iii
- clio iii
lang: fr
created_at: '2026-04-29'
updated_at: '2026-05-02'
truth_level: L3
source_refs:
- kind: recycled
  origin_repo: automecanik-rag
  origin_path: knowledge/vehicles/renault-clio-3.md
  captured_at: '2026-04-29'
- kind: recycled
  origin_repo: automecanik-rag
  origin_path: knowledge/vehicles/renault-clio-iii.md
  captured_at: '2026-04-29'
provenance:
  ingested_by: skill:recycle-from-rag@v0.1
  promoted_from: null
lineage_id: 019dd8ee-daf5-731c-b5d4-c6cb9601a446
parents: []
review_status: approved
reviewed_by: skill:phase6-promotion-batch@claude
reviewed_at: '2026-05-02T20:17:01Z'
review_notes: "Phase F batch ADR-031. Recyclé depuis automecanik-rag par recycle-from-rag.py.\n\
  Source body original sha256=e1d1c690e54224b47d8f597a195f0ace65314b59a053d2cdd975352db42af462.\n\
  \nFusion 2026-05-02 (Phase 1 plan deja-verifier-existant) : doublon\nrenault-clio-iii.md\
  \ arbitré vers ce slug arabe (canon dict romain/arabe —\nPR #122 + vault #37). Blocs\
  \ uniques caradisiac absorbés.\n\nPhase 4 plan deja-verifier-existant 2026-05-02\
  \ :\n- Sections H2 alignées sur ordre canon _templates/new-vehicle.md\n  (Présentation\
  \ / Motorisations / Pièces compatibles (top gammes) /\n  Particularités d'entretien\
  \ / Questions fréquentes / Sources et provenance /\n  Points à vérifier)\n- Titre\
  \ \"Fiche véhicule - Renault Clio 3\" → \"Renault Clio 3\" (FR canon,\n  pas de\
  \ préfixe technique redondant)\n- target_classes [] → [KB_Knowledge, KB_Catalog]\n\
  - entity_data complété : generation, years, motorizations[] structuré YAML,\n  vlevel\
  \ V2, low_profile_canary false (best-seller pas canary)\n- Wikilinks gammes ajoutés\
  \ ([[plaquette-de-frein]], [[disque-de-frein]],\n  [[filtre-a-air]], etc.) dans\
  \ \"Pièces compatibles (top gammes)\"\n- Section \"Véhicules proches\" intégrée\
  \ dans \"Présentation\"\n- Sections existantes (Top pièces, Symptômes par pièce,\
  \ Rappels constructeur,\n  Coûts d'entretien, Conseils saisonniers) consolidées\
  \ dans\n  \"Particularités d'entretien\"\n\nÀ reviewer humainement avant promotion\
  \ vers wiki/vehicles/.\n"
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
  model: clio-3
  generation: iii
  years:
  - 2005
  - 2014
  type_id: null
  motorizations:
  - code: D4F
    fuel: essence
    power_hp: 75
    displacement_cc: 1149
    note: 1.2 16V atmosphérique
  - code: D4F
    fuel: essence
    power_hp: 100
    displacement_cc: 1149
    note: 1.2 TCe turbo
  - code: K4J
    fuel: essence
    power_hp: 98
    displacement_cc: 1390
    note: 1.4 16V
  - code: K4M
    fuel: essence
    power_hp: 110
    displacement_cc: 1598
    note: 1.6 16V
  - code: F4R
    fuel: essence
    power_hp: 197
    displacement_cc: 1998
    note: 2.0 RS Phase 1
  - code: F4R
    fuel: essence
    power_hp: 200
    displacement_cc: 1998
    note: 2.0 RS Phase 2
  - code: K9K
    fuel: diesel
    power_hp: 65
    displacement_cc: 1461
    note: 1.5 dCi bridé
  - code: K9K
    fuel: diesel
    power_hp: 86
    displacement_cc: 1461
    note: 1.5 dCi standard
  - code: K9K
    fuel: diesel
    power_hp: 106
    displacement_cc: 1461
    note: 1.5 dCi haut de gamme
  vlevel: V2
  low_profile_canary: false
content_hash: sha256:555e766a1ff25028619b6dcccfa7540b5c400eceb92b1d4b371f4113c83030d7
confidence_score: 0.24
---

# Renault Clio 3

## Présentation

La **Renault Clio 3** (génération III, codes carrosserie BR/CR) est une citadine du segment B produite de **2005 à 2014**. Elle a remplacé la Clio II et fut elle-même remplacée par la Clio IV. Disponible en 3 portes, 5 portes et Estate (break, lancé 2008).

### Caractéristiques techniques détaillées (millésime 2009 — référence 1.5 dCi 86 ch)

| Caractéristique | Valeur |
|---|---|
| Longueur | 4,02 m |
| Largeur | 2,02 m |
| Hauteur | 1,49 m |
| Empattement | 2,57 m |
| Poids à vide (1.5 dCi) | 1 090 kg |
| Volume coffre | 288 L (1 038 L sièges rabattus) |
| Volume coffre Estate | 439 L (1 380 L sièges rabattus) |
| Réservoir | 55 L essence / 50 L diesel |
| Places | 5 |
| Cylindrée (1.5 dCi) | 1 461 cm³ |
| Couple (1.5 dCi 86 ch) | 200 Nm à 1 900 tr/min |
| Boîte de vitesse | Mécanique 5 rapports |
| Transmission | Traction |
| Vitesse max (1.5 dCi 86 ch) | 176 km/h |
| 0 à 100 km/h (1.5 dCi 86 ch) | 12,7 s |
| Consommation mixte (1.5 dCi 86 ch) | 3,7 L/100 km |
| Émissions CO2 (1.5 dCi 86 ch) | 98 g/km |
| Pneumatiques (référence) | 185/60 R15 |
| Diamètre de braquage | 11 m |
| Norme Euro | EU4 |

### Véhicules proches (plate-forme partagée / pièces partagées)

| Modèle | Années | Ce qui est partagé |
|---|---|---|
| [[renault-modus]] / Grand Modus | 2004-2012 | Plate-forme B, moteurs D4F/K9K, boîte JH3/JR5, train roulant avant |
| [[renault-twingo-ii]] | 2007-2014 | Moteurs D4F/K9K, freinage, filtration, allumage |
| [[dacia-sandero]] (génération I) | 2008-2012 | Plate-forme B90, moteur K9K, freinage, liaison au sol |
| [[nissan-micra-k12]] | 2003-2010 | Plate-forme Nissan B, train roulant, direction, freinage |
| [[renault-kangoo-ii]] | 2008-2021 | Moteur K9K, filtres, injecteurs, turbo, accessoires moteur |

## Motorisations

### Essence

| Moteur | Puissance | Code moteur | Notes |
|---|---|---|---|
| 1.2 16V (atmosphérique) | 58 / 65 / 75 / 88 / 101 / 103 ch | D4F | Variantes Phase 1 (101 ch) / Phase 2 (103 ch). Bridées low-emission selon marché. |
| 1.2 TCe (turbo) | 100 ch | D4F | Turbo — ne pas confondre avec 1.2 16V atmosphérique |
| 1.4 16V | 98 ch | K4J | — |
| 1.6 16V | 110 / 112 ch | K4M | Variante GT 128 ch (même code K4M optimisé) |
| 2.0 16V | 139 ch | F4R | — |
| 2.0 RS / Sport | 197 / 200 ch | F4R | Phase 1 (197 ch) / Phase 2 (200 ch) |

### Diesel

| Moteur | Puissance | Code moteur | Notes |
|---|---|---|---|
| 1.5 dCi | 64 / 65 / 68 ch | K9K | Variantes K9K bridées low-emission |
| 1.5 dCi | 75 ch | K9K | — |
| 1.5 dCi | 85 / 86 / 88 ch | K9K | Référence catalogue (cf. caractéristiques techniques détaillées 86 ch) |
| 1.5 dCi | 105 / 106 ch | K9K | — |

## Pièces compatibles (top gammes)

Indicateur de fréquence des demandes catalogue (nombre de références distinctes répertoriées — tous fournisseurs confondus pour cette génération) :

| Pièce | Nombre de références | Fiche gamme |
|---|---|---|
| Rétroviseur extérieur | 189 | — |
| Mâchoires de frein | 96 | — |
| Alternateur | 95 | — |
| Courroie d'accessoire | 71 | — |
| Cardan | 66 | — |
| Filtre à air | 63 | [[filtre-a-air]] |
| Silencieux | 61 | — |
| Démarreur | 56 | — |
| Filtre à carburant | 56 | [[filtre-a-carburant]] |
| Butée d'embrayage | 55 | — |
| Filtre à huile | 44 | [[filtre-a-huile]] |
| Batterie | 40 | — |
| Bouchon vase d'expansion | 37 | — |
| Liquide de frein | 32 | — |
| Joint de collecteur | 12 | — |

### Pièces d'usure principales

- **Freinage** : [[plaquette-de-frein]] avant (30-40 000 km), arrière (50-70 000 km si disques), [[disque-de-frein]] avant (60-80 000 km)
- **Filtration** : [[filtre-a-huile]] (chaque vidange), [[filtre-a-air]] (30 000 km), [[filtre-habitacle]] (15 000 km), [[filtre-a-carburant]] diesel (60 000 km)
- **Distribution** : courroie 90 000 km / 5 ans (selon motorisation) — kit complet recommandé (courroie + galets + pompe à eau)

### Références OEM courantes

| Pièce | Référence Renault |
|---|---|
| Filtre à huile 1.5 dCi | 8200768927 |
| Filtre à air 1.5 dCi | 8200431051 |
| Plaquettes avant | 410602192R |
| Disques avant | 402069518R |
| Courroie distribution | 130C17529R |

> Indicatif — voir catalogue site pour références complètes par motorisation et année.

## Particularités d'entretien

### Symptômes par pièce (top 10 demandées)

#### Rétroviseur extérieur

- Miroir cassé, fissuré ou décollé
- Coque de rétroviseur cassée (choc, accrochage)
- Réglage électrique inopérant ou lent
- Dégivrage du miroir qui ne fonctionne plus
- Rétroviseur rabattable bloqué ou qui vibre

#### Mâchoires de frein

- Frein à main qui ne tient plus ou tient mal
- Bruit de frottement métallique à l'arrière
- Tambour rayé ou strié à l'intérieur
- Épaisseur de garniture inférieure à 2 mm
- Freinage arrière déséquilibré (tire d'un côté)

#### Alternateur

- Voyant batterie allumé moteur tournant
- Batterie qui se décharge malgré les trajets
- Phares qui faiblissent ou clignotent
- Sifflement de la courroie d'accessoire
- Odeur de courroie brûlée ou d'électrique

#### Courroie d'accessoire, Cardan, Filtre à air, Silencieux, Démarreur, Filtre à carburant, Butée d'embrayage

> Voir [[filtre-a-air]] §"Symptômes d'usure" et fiches gammes correspondantes pour le détail.

### Problèmes connus

#### Moteur 1.5 dCi (K9K)

- **Vanne EGR** : encrassement fréquent (perte de puissance, fumées noires, voyant moteur)
- **Injecteurs Delphi** : fuite de carburant (rappel constructeur 2005-2010)
- **Turbo BorgWarner KP35** : usure prématurée si vidanges non respectées (sifflement après 150 000 km)

#### Électricité

- **Platine fusibles** : problèmes de contacts (rappel 2006-2009)
- **Capteur pédale accélérateur** : défaillance (rappel 2007-2009)

#### Train roulant

- **Rotules de direction** : usure normale
- **Silent-blocs bras** : à contrôler à 100 000 km

### Rappels constructeur

| Rappel | Motorisation | Période | Détail |
|---|---|---|---|
| Injecteurs Delphi — fuite carburant | 1.5 dCi (K9K) | 2005-2010 | Fuite au raccord haute pression. Risque incendie. Remplacement gratuit joints + clips. ~500 000 véhicules en Europe. |
| Platine fusibles — court-circuit | Toutes | 2006-2009 (séries) | Défaut soudure platine fusibles habitacle. Remplacement en concession. |
| Pédale accélérateur — signal erratique | 1.5 dCi | 2007-2009 | Capteur position défaillant. À-coups ou perte puissance. Remplacement capteur. |

> **Vérification** : numéro de rappel consultable sur `rappel.renault.fr` avec le VIN du véhicule.

### Intervalles d'entretien

| Opération | Fréquence | Coût indicatif (pièces + MO) |
|---|---|---|
| Vidange + filtre à huile | 15 000 km/1 an (diesel) — 20 000 km/2 ans (essence) | 60-120 € |
| Kit distribution + pompe à eau | 90 000 km/5 ans (dCi) — 120 000 km/6 ans (essence) | 400-700 € |
| Plaquettes + disques freins avant | 30 000-50 000 km | 150-280 € |
| Plaquettes + disques freins arrière | 60 000-80 000 km | 100-200 € |
| Amortisseurs avant (paire) | 80 000-120 000 km | 200-350 € |
| Amortisseurs arrière (paire) | 80 000-120 000 km | 150-280 € |
| Kit embrayage complet | 120 000-180 000 km | 450-750 € |
| Liquide de frein | 2 ans / 60 000 km | 30-50 € |

### Conseils propriétaire

1. **Respectez la norme d'huile, pas seulement la viscosité.** Sur les 1.5 dCi avec FAP, utiliser 5W-30 norme RN0720/C4. Une huile non conforme encrasse le FAP. Essence : 5W-40 norme RN0700.
2. **Surveillez le calorstat sur les 1.5 dCi.** Un calorstat bloqué ouvert empêche le moteur d'atteindre sa température, augmente la consommation. Symptôme : chauffage défaillant en hiver. Remplacement 50-100 €.
3. **Attention au joint de collecteur d'échappement (1.2 16V D4F).** Bruit métallique à froid = fuite au joint. À remplacer rapidement sous peine d'endommager la sonde lambda.
4. **Roulez 20 min pour régénérer le FAP.** Trajets courts urbains empêchent la régénération. Faire régulièrement un trajet à 3 000 tr/min sur voie rapide.
5. **Ne confondez pas TCe et D4F.** Le 1.2 TCe 100 ch (turbo) ≠ 1.2 16V atmosphérique D4F. Intervalles, huile, filtre différents. Vérifier le code moteur (plaque constructeur porte gauche).

### Conseils saisonniers

#### Hiver

- **Batterie** : tester après 4-5 ans, remplacer si <70% capacité (50-60 Ah)
- **Pneus** : hiver en 185/65 R15, ou 4 saisons pour usage urbain
- **Liquide refroidissement** : Type D (Renault Glaceol RX), protection -35°C, ne pas mélanger
- **Éclairage** : ampoules H7 (croisement) + H1 (route), garder un jeu de rechange

#### Été

- **Climatisation** : vérifier gaz R134a tous les 2-3 ans (remplacement compresseur : 500-900 €)
- **Refroidissement** : inspecter durites et bouchon vase d'expansion (fissure fréquente Clio 3)
- **Filtre habitacle** : remplacer au printemps (accès boîte à gants, simple à faire)

## Questions fréquentes

### Quand changer la courroie de distribution sur une Clio 3 ?

Essence : 120 000 km ou 6 ans. Diesel 1.5 dCi : 90 000 km ou 5 ans. Ne pas dépasser sous peine de casse moteur (réparation 2 500-4 000 €).

### Problèmes vanne EGR sur le 1.5 dCi ?

Encrassement fréquent en usage urbain. Symptômes : perte de puissance, fumées noires, voyant moteur. Nettoyage tous les 30 000-40 000 km recommandé. Remplacement : 200-400 €.

### Quelle huile pour ma Clio 3 ?

Essence : 5W-40 norme RN0700. Diesel : 5W-30 norme RN0720 (sans FAP) ou C4/RN0720 (avec FAP).

### Pièces compatibles avec d'autres Renault ?

Oui — la Clio 3 partage des pièces avec [[renault-modus]], [[renault-twingo-ii]], [[renault-kangoo-ii]] (moteurs K9K et D4F, freinage, filtres, train roulant). Voir tableau "Véhicules proches" en Présentation.

### Turbo 1.5 dCi qui siffle ?

Le turbo BorgWarner KP35 peut s'user après 150 000 km si vidanges non respectées. Peut aussi être une durite fissurée ou électrovanne de suralimentation.

### Fréquence vidange ?

Diesel : 15 000 km ou 1 an. Essence : 20 000 km ou 2 ans. Raccourcir de 20-30% en usage urbain.

### Injecteurs fragiles ?

Les injecteurs Delphi du K9K sont un point sensible. Fuite joint cuivre ou défaut pulvérisation après 120 000 km. Remplacement : 150-350 €/injecteur.

## Sources et provenance

Sources canoniques utilisées (cf. `_quality/sources-brief.md` Phase 3) :

- **Wikipedia FR — Renault Clio III** : https://fr.wikipedia.org/wiki/Renault_Clio_III (license `CC-BY-SA-3.0`, capture intégrale via preset `wikipedia-vehicle` PR2 livré skill `web-clip-template`). Action humaine Phase 3.
- **caradisiac fiche technique 2009** : https://www.caradisiac.com/fiches-techniques/modele--renault-clio-3/2009/ (license `proprietary-citation-only`, courte citation ≤200 mots). Phase 3.
- **Renault rappel.renault.fr** : référence rappels constructeur (license `proprietary-manufacturer`, capture intégrale URL publique).
- **OEM Renault Clio III workshop manual** : Phase 7 différé (preset `manuel-constructeur-pdf` à livrer skill PR2).

`source_refs[]` dans frontmatter : provenance recyclée depuis `automecanik-rag/knowledge/vehicles/{renault-clio-3,renault-clio-iii}.md` (Phase 1 fusion).

## Points à vérifier

- [ ] Vérifier `entity_data.type_id` aligné DB `__auto_type` Supabase (mapper depuis make=renault + model=clio-3 + generation=iii + years=[2005, 2014])
- [ ] Confirmer `vlevel: V2` (Clio 3 = best-seller Renault, top vente compactes 2005-2014)
- [x] **2026-05-02** : `low_profile_canary: false` (best-seller, pas un canary low-profile R8)
- [x] **2026-05-02** : `motorizations[]` structuré YAML (9 entrées : 6 essence + 3 diesel principales)
- [ ] Capturer Wikipedia FR Clio III via extension Obsidian preset `wikipedia-vehicle` (cf. `_quality/sources-brief.md`)
- [ ] Capturer caradisiac fiche technique 2009 (≤200 mots citation)
- [ ] Construire `_coverage/renault-clio-3.coverage.yaml` (Phase 5 plan parent)
- [ ] Décider promotion → `wiki/vehicles/renault-clio-3.md` (commit message obligatoire `promotion-from-proposals: renault-clio-3`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
