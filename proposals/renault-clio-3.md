---
schema_version: 1.0.0
id: vehicle:renault-clio-3
entity_type: vehicle
slug: renault-clio-3
title: Fiche véhicule - Renault Clio 3
aliases:
  - Renault Clio III
  - Clio III
  - Renault Clio 3
  - clio-iii
  - clio iii
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/vehicles/renault-clio-3.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:recycle-from-rag@v0.1
  promoted_from:
lineage_id: 019dd8ee-daf5-731c-b5d4-c6cb9601a446
review_status: proposed
reviewed_by:
reviewed_at:
review_notes: |
  Phase F batch ADR-031. Recyclé depuis automecanik-rag par recycle-from-rag.py.
  Source body original sha256=e1d1c690e54224b47d8f597a195f0ace65314b59a053d2cdd975352db42af462.

  Fusion 2026-05-02 (Phase 1 plan deja-verifier-existant) : doublon `renault-clio-iii.md`
  arbitré vers ce slug arabe (canon dict romain/arabe — PR #122 + vault #37).
  Blocs uniques caradisiac absorbés depuis clio-iii :
    - Section "Caractéristiques techniques détaillées" (table dimensions/conso/CO2/Euro phase 2009)
    - Variantes motorisation supplémentaires (essence Phase 1/2, dCi 64/68/86/88/106 ch)
    - "Top pièces les plus demandées" (top 14 avec nb références catalogue)
    - "Symptômes par pièce" (10 pièces × 5 symptômes diagnostiques)
  Source caradisiac (à capturer Phase 3 sources-brief) :
  https://www.caradisiac.com/fiches-techniques/modele--renault-clio-3/2009/

  À reviewer humainement avant promotion vers wiki/vehicles/.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  make: renault
  model: clio-3
content_hash: sha256:555e766a1ff25028619b6dcccfa7540b5c400eceb92b1d4b371f4113c83030d7
confidence_score: 0.32
---

# Fiche véhicule - Renault Clio 3

> 📥 **Proposition Phase F** — extraite par `recycle-from-rag.py` depuis `knowledge/vehicles/renault-clio-3.md`.
> source body sha256 : `e1d1c690e54224b47d8f597a195f0ace65314b59a053d2cdd975352db42af462`
> À reviewer manuellement avant promotion vers `wiki/vehicles/renault-clio-3.md`.

## Faits extraits (source body brut, à structurer)

# Renault Clio 3 (2005-2014)

## Identification

- **Génération** : III (BR/CR)
- **Production** : 2005 - 2014
- **Segment** : B (citadine)
- **Carrosseries** : 3 portes, 5 portes, Estate (break)

## Caractéristiques techniques détaillées (millésime 2009 — référence 1.5 dCi 86 ch)

| Caractéristique | Valeur |
|---|---|
| Longueur | 4,02 m |
| Largeur | 2,02 m |
| Hauteur | 1,49 m |
| Empattement | 2,57 m |
| Poids à vide (référence 1.5 dCi) | 1 090 kg |
| Volume coffre | 288 L (1 038 L sièges rabattus) |
| Réservoir | 55 L |
| Places | 5 |
| Cylindrée (référence 1.5 dCi) | 1 461 cm³ |
| Couple (1.5 dCi 86 ch) | 200 Nm à 1 900 tr/min |
| Boîte de vitesse | Mécanique 5 rapports |
| Transmission | Traction |
| Vitesse max (1.5 dCi 86 ch) | 176 km/h |
| 0 à 100 km/h (1.5 dCi 86 ch) | 12,70 s |
| Consommation mixte (1.5 dCi 86 ch) | 3,70 L/100 km |
| Émissions CO2 (1.5 dCi 86 ch) | 98 g/km |
| Pneumatiques (référence) | 185/60 R15 |
| Diamètre de braquage | 11 m |
| Norme Euro | EU4 |

> Source : caradisiac.com — fiches techniques Renault Clio 3 millésime 2009. Spécifications variant selon motorisation (cf. tableau "Poids à vide" ci-dessous pour autres versions).

## Motorisations principales

### Essence

| Moteur | Puissance | Code moteur | Notes |
|---|---|---|---|
| 1.2 16V (atmosphérique) | 58 / 65 / 75 / 88 / 101 / 103 ch | D4F | Variantes Phase 1 (101 ch) / Phase 2 (103 ch). Bridées low-emission selon marché. |
| 1.2 TCe (turbo) | 100 ch | D4F | Turbo — ne pas confondre avec 1.2 16V atmosphérique (cf. conseil propriétaire #5) |
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

## Pièces d'usure courantes

### Freinage

- **Plaquettes avant** : Remplacement 30-40 000 km
- **Disques avant** : Remplacement 60-80 000 km
- **Plaquettes arrière** : 50-70 000 km (si disques)
- **Tambours** : Contrôle à 100 000 km

### Filtration

- **Filtre à huile** : À chaque vidange
- **Filtre à air** : 30 000 km ou 2 ans
- **Filtre habitacle** : 15 000 km ou 1 an
- **Filtre à carburant** (diesel) : 60 000 km

### Distribution

- **Type** : Courroie
- **Intervalle** : 90 000 km ou 5 ans (selon motorisation)
- **Kit complet** : Courroie + galets + pompe à eau recommandé

## Top pièces les plus demandées (catalogue)

Indicateur de fréquence des demandes catalogue (nombre de références distinctes en stock — tous fournisseurs confondus pour cette génération) :

| Pièce | Nombre de références |
|---|---|
| Rétroviseur extérieur | 189 |
| Mâchoires de frein | 96 |
| Alternateur | 95 |
| Courroie d'accessoire | 71 |
| Cardan | 66 |
| Filtre à air | 63 |
| Silencieux | 61 |
| Démarreur | 56 |
| Filtre à carburant | 56 |
| Butée d'embrayage | 55 |
| Filtre à huile | 44 |
| Batterie | 40 |
| Bouchon vase d'expansion | 37 |
| Liquide de frein | 32 |
| Joint de collecteur | 12 |

## Symptômes par pièce

Symptômes diagnostiques typiques pour les pièces les plus demandées sur Clio 3.

### Rétroviseur extérieur

- Miroir cassé, fissuré ou décollé
- Coque de rétroviseur cassée (choc, accrochage)
- Réglage électrique inopérant ou lent
- Dégivrage du miroir qui ne fonctionne plus
- Rétroviseur rabattable bloqué ou qui vibre

### Mâchoires de frein

- Frein à main qui ne tient plus ou tient mal
- Bruit de frottement métallique à l'arrière
- Tambour rayé ou strié à l'intérieur
- Épaisseur de garniture inférieure à 2 mm
- Freinage arrière déséquilibré (tire d'un côté)

### Alternateur

- Voyant batterie allumé moteur tournant
- Batterie qui se décharge malgré les trajets
- Phares qui faiblissent ou clignotent
- Sifflement de la courroie d'accessoire
- Odeur de courroie brûlée ou d'électrique

### Courroie d'accessoire

- Sifflement au démarrage ou à l'accélération
- Courroie fissurée ou effilochée visible
- Voyant batterie allumé (alternateur non entraîné)
- Perte de direction assistée si sur même courroie
- Odeur de caoutchouc brûlé

### Cardan

- Claquement en braquant / accélérant en marche arrière
- Vibrations ressenties à vitesse constante
- Graisse noire visible sur la jante (passage de roue)
- Soufflet de cardan déchiré ou fendu
- Bruit de roulement variable selon l'angle

### Filtre à air

- Perte de puissance à l'accélération
- Surconsommation de carburant anormale
- Fumée noire à l'échappement
- Sifflement anormal à l'admission
- Odeur de carburant non brûlé

### Silencieux

- Bruit excessif à l'échappement
- Vibrations sous le véhicule
- Corrosion / perforation visible

### Démarreur

- Claquement au contact (solénoïde)
- Démarreur qui tourne mais moteur non lancé
- Aucune réaction au contact (moteur électrique HS)
- Grincement ou bruit anormal au démarrage
- Odeur de brûlé électrique au démarrage

### Filtre à carburant

- Perte de puissance progressive
- À-coups à l'accélération
- Démarrage difficile ou laborieux
- Cliquetis ou ratés moteur
- Odeur de carburant autour du véhicule

### Butée d'embrayage

- Bruit de roulement à l'appui sur la pédale
- Sifflement / grondement qui disparaît en relâchant la pédale
- Pédale d'embrayage qui vibre sous le pied
- Embrayage qui accroche par à-coups
- Difficulté à passer les vitesses (butée grippée)

## Problèmes connus

### Moteur 1.5 dCi (K9K)

- Vanne EGR : Encrassement fréquent
- Injecteurs : Fuite de carburant (rappel)
- Turbo : Usure prématurée (huile de qualité importante)

### Électricité

- Platine fusibles : Problèmes de contacts
- Capteur pédale accélérateur : Défaillance

### Train roulant

- Rotules de direction : Usure normale
- Silent-blocs bras : À contrôler à 100 000 km

## Rappels constructeur

| Rappel                                 | Motorisation         | Période                      | Détail                                                                                                                                                        |
| -------------------------------------- | -------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Injecteurs Delphi — fuite carburant    | 1.5 dCi (K9K)        | 2005-2010                    | Fuite au raccord haute pression des injecteurs. Risque incendie. Remplacement gratuit des joints et clips de fixation. Concerne ~500 000 véhicules en Europe. |
| Platine fusibles — court-circuit       | Toutes motorisations | 2006-2009 (certaines séries) | Défaut de soudure sur la platine fusibles habitacle pouvant provoquer un dysfonctionnement électrique. Remplacement platine en concession.                    |
| Pédale accélérateur — signal erratique | 1.5 dCi              | 2007-2009                    | Capteur de position pédale accélérateur défaillant pouvant causer des à-coups ou une perte de puissance. Remplacement du capteur.                             |

> **Vérification** : le numéro de rappel est consultable sur rappel.renault.fr avec le VIN du véhicule.

## Intervalles d'entretien

### Vidange

- **Essence** : 15 000 km ou 1 an
- **Diesel** : 20 000 km ou 1 an

### Contrôle général

- Tous les 20 000 km ou 1 an

## Références OEM courantes

| Pièce                  | Référence Renault |
| ---------------------- | ----------------- |
| Filtre à huile 1.5 dCi | 8200768927        |
| Filtre à air 1.5 dCi   | 8200431051        |
| Plaquettes avant       | 410602192R        |
| Disques avant          | 402069518R        |
| Courroie distribution  | 130C17529R        |

## Conseils propriétaire

1. **Respectez la norme d'huile, pas seulement la viscosité.** Sur les 1.5 dCi avec FAP, utiliser 5W-30 norme RN0720/C4. Une huile non conforme encrasse le FAP. Essence : 5W-40 norme RN0700.
1. **Surveillez le calorstat sur les 1.5 dCi.** Un calorstat bloqué ouvert empêche le moteur d'atteindre sa température, augmente la consommation et favorise l'encrassement. Symptôme : chauffage défaillant en hiver. Remplacement 50-100€.
1. **Attention au joint de collecteur d'échappement (1.2 16V D4F).** Bruit métallique à froid = fuite au joint. À remplacer rapidement sous peine d'endommager la sonde lambda.
1. **Roulez 20 min pour régénérer le FAP.** Trajets courts urbains empêchent la régénération. Faire régulièrement un trajet à 3000 tr/min sur voie rapide.
1. **Ne confondez pas TCe et D4F.** Le 1.2 TCe 100ch (turbo) ≠ 1.2 16V atmosphérique D4F. Intervalles, huile, filtre différents. Vérifier le code moteur (plaque constructeur porte gauche).

## Coûts d'entretien

| Opération                           | Fourchette (pièces + MO) | Fréquence                                     |
| ----------------------------------- | ------------------------ | --------------------------------------------- |
| Vidange + filtre à huile            | 60-120€                  | 15000km/1an (diesel) — 20000km/2ans (essence) |
| Kit distribution + pompe à eau      | 400-700€                 | 90000km/5ans (dCi) — 120000km/6ans (essence)  |
| Plaquettes + disques freins avant   | 150-280€                 | 30000-50000km                                 |
| Plaquettes + disques freins arrière | 100-200€                 | 60000-80000km                                 |
| Amortisseurs avant (paire)          | 200-350€                 | 80000-120000km                                |
| Amortisseurs arrière (paire)        | 150-280€                 | 80000-120000km                                |
| Kit embrayage complet               | 450-750€                 | 120000-180000km                               |

## Spécifications techniques

### Dimensions

| Paramètre   | 3/5 portes | Estate |
| ----------- | ---------- | ------ |
| Longueur    | 3990mm     | 4235mm |
| Largeur     | 1720mm     | 1720mm |
| Hauteur     | 1498mm     | 1470mm |
| Empattement | 2472mm     | 2587mm |

### Poids à vide

| Motorisation            | Poids       |
| ----------------------- | ----------- |
| 1.2 16V 75ch (D4F)      | 1010-1060kg |
| 1.4 16V 98ch (K4J)      | 1090kg      |
| 1.6 16V 110ch (K4M)     | 1110kg      |
| 2.0 RS 197/200ch (F4R)  | 1240-1280kg |
| 1.5 dCi 65/68ch (K9K)   | 1090-1120kg |
| 1.5 dCi 85/86ch (K9K)   | 1100-1140kg |
| 1.5 dCi 105/106ch (K9K) | 1140-1170kg |

### Volumes et capacités

| Paramètre            | Valeur                       |
| -------------------- | ---------------------------- |
| Coffre 5 portes      | 288L (1038L sièges rabattus) |
| Coffre Estate        | 439L (1380L sièges rabattus) |
| Réservoir essence    | 55L                          |
| Réservoir diesel     | 50L                          |
| Huile moteur 1.2 16V | 3.3L                         |
| Huile moteur 1.5 dCi | 4.5L (avec filtre)           |
| Huile moteur 2.0 RS  | 5.2L                         |

## FAQ véhicule

**Q1 : Quand changer la courroie de distribution sur une Clio 3 ?**
Essence : 120000km ou 6 ans. Diesel 1.5 dCi : 90000km ou 5 ans. Ne pas dépasser sous peine de casse moteur.

**Q2 : Problèmes vanne EGR 1.5 dCi ?**
Encrassement fréquent en usage urbain. Symptômes : perte de puissance, fumées noires, voyant moteur. Nettoyage tous les 30000-40000km recommandé. Remplacement : 200-400€.

**Q3 : Quelle huile pour ma Clio 3 ?**
Essence : 5W-40 norme RN0700. Diesel : 5W-30 norme RN0720 (sans FAP) ou C4/RN0720 (avec FAP).

**Q4 : Pièces compatibles avec d'autres Renault ?**
Oui. La Clio 3 partage pièces avec Modus, Twingo II, Kangoo II (moteurs K9K et D4F, freinage, filtres, train roulant).

**Q5 : Turbo 1.5 dCi qui siffle ?**
Le turbo BorgWarner KP35 peut s'user après 150000km si vidanges non respectées. Peut aussi être une durite fissurée ou électrovanne de suralimentation.

**Q6 : Fréquence vidange ?**
Diesel : 15000km ou 1 an. Essence : 20000km ou 2 ans. Raccourcir de 20-30% en usage urbain.

**Q7 : Injecteurs fragiles ?**
Les injecteurs Delphi du K9K sont un point sensible. Fuite joint cuivre ou défaut pulvérisation après 120000km. Remplacement : 150-350€/injecteur.

## Conseils saisonniers

### Hiver

- **Batterie** : tester après 4-5 ans, remplacer si \<70% capacité (50-60Ah)
- **Pneus** : hiver en 185/65 R15, ou 4 saisons pour usage urbain
- **Liquide refroidissement** : Type D (Renault Glaceol RX), protection -35°C, ne pas mélanger
- **Éclairage** : ampoules H7 (croisement) + H1 (route), garder un jeu de rechange

### Été

- **Climatisation** : vérifier gaz R134a tous les 2-3 ans (remplacement compresseur : 500-900€)
- **Refroidissement** : inspecter durites et bouchon vase expansion (fissure fréquente Clio 3)
- **Filtre habitacle** : remplacer au printemps (accès boîte à gants, simple à faire)

## Véhicules proches (même plateforme / pièces partagées)

| Modèle                      | Années    | Ce qui est partagé                                                |
| --------------------------- | --------- | ----------------------------------------------------------------- |
| Renault Modus / Grand Modus | 2004-2012 | Plateforme B, moteurs D4F/K9K, boîte JH3/JR5, train roulant avant |
| Renault Twingo II           | 2007-2014 | Moteurs D4F/K9K, freinage, filtration, allumage                   |
| Dacia Sandero I             | 2008-2012 | Plateforme B90, moteur K9K, freinage, liaison au sol              |
| Nissan Micra K12            | 2003-2010 | Plateforme Nissan B, train roulant, direction, freinage           |
| Renault Kangoo II           | 2008-2021 | Moteur K9K, filtres, injecteurs, turbo, accessoires moteur        |

## Points de review

- [ ] Vérifier `entity_data` complet et aligné DB monorepo (`vehicle`)
- [ ] Compléter ou corriger les `aliases`
- [ ] Décider promotion vers `wiki/vehicles/renault-clio-3.md` ou ajustement
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO>`
