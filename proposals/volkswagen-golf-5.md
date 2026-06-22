---
schema_version: 1.0.0
id: vehicle:volkswagen-golf-5
entity_type: vehicle
slug: volkswagen-golf-5
title: Volkswagen Golf 5
aliases:
  - Golf 5
  - Golf V
  - VW Golf 5
  - Golf Mk5
  - Golf 1K
  - Volkswagen Golf V
lang: fr
created_at: '2026-06-16'
updated_at: '2026-06-16'
truth_level: L3
source_refs:
  - kind: raw
    path: sources/web-research/volkswagen-golf-5-19-tdi/
    captured_at: '2026-06-16'
provenance:
  ingested_by: agent:research/web-vehicle (golf5-tdi-generous-full + enrich-golf5-tdi-vehicle-r8)
  promoted_from: null
lineage_id: 019ed024-2ea1-743f-b655-95bba9d81101
parents: []
review_status: draft
reviewed_by: null
reviewed_at: null
review_notes: |
  Fiche NEUVE 2026-06-16 — enrichissement GÉNÉREUX depuis web-research RAW frais
  (passe exhaustive 9 facettes = 280 faits cités + passe 1 = 79 faits ; engine_scope
  taggé) + faits DB AutoMecanik (codes moteur, 485 gammes compatibles). AUCUN
  recyclage automecanik-rag.
  Couverture par SYSTÈME (moteur / injection / suralimentation-EGR-FAP /
  refroidissement / électrique / transmission / train-freinage-direction) ET par
  code moteur (BKC / BXE / BLS / 90 ch BRU-BXF-BXJ / communs PD).
  Re-revue humaine REQUISE avant promotion + avant exportable.*: true.
  Tous les prix sont indicatifs/conditionnels. Voir "Points à vérifier".
no_disputed_claims: false
exportable:
  rag: false
  seo: false
  support: false
target_classes:
  - KB_Knowledge
  - KB_Catalog
entity_data:
  make: volkswagen
  model: golf-5
  generation: v
  years:
    - 2003
    - 2009
  type_id: 17484
  vlevel: V2
  low_profile_canary: false
  motorizations:
    - code: BRU
      fuel: diesel
      power_hp: 90
      displacement_cc: 1896
      note: 1.9 TDI PD 90 ch (injecteur-pompe), sans FAP (type_id 18114)
    - code: BXF
      fuel: diesel
      power_hp: 90
      displacement_cc: 1896
      note: 1.9 TDI PD 90 ch, sans FAP
    - code: BXJ
      fuel: diesel
      power_hp: 90
      displacement_cc: 1896
      note: 1.9 TDI PD 90 ch, sans FAP
    - code: BKC
      fuel: diesel
      power_hp: 105
      displacement_cc: 1896
      note: 1.9 TDI PD 105 ch (2004-2007) — la plus fiable, exempte du défaut de bielles, sans FAP (type_id 17484)
    - code: BXE
      fuel: diesel
      power_hp: 105
      displacement_cc: 1896
      note: 1.9 TDI PD 105 ch (à partir de 2007) — coussinets de bielle fragiles (conditionnel), sans FAP
    - code: BLS
      fuel: diesel
      power_hp: 105
      displacement_cc: 1896
      note: 1.9 TDI PD 105 ch — SEULE version équipée d'un FAP/DPF
    - code: BKC/BLS/BXE 4Motion
      fuel: diesel
      power_hp: 105
      displacement_cc: 1896
      note: 105 ch 4Motion (transmission intégrale Haldex, essieu AR 4 bras, type_id 18384)
  known_issues_by_engine:
    all_engines:
      - "Arbre à cames + poussoirs (PD) : usure prématurée — l'AAC actionne aussi les injecteurs-pompe (3e came, contact étroit). Claquement métallique culasse à froid, perte de puissance, fumée noire. Aggravé par huile non VW 505.01. Réfection AAC + poussoirs renforcés + coussinets : ~800-1500 €."
      - "Volant moteur bi-masse (DMF) : panne n°1, cliquetis/vibrations à l'embrayage, défaillance 150 000-250 000 km (parfois <120 000). Remplacé en kit avec embrayage (228 mm). ~1200-2500 € posé."
      - "Turbo à géométrie variable (VNT) : grippage par calamine (usage urbain) → perte de puissance + mode dégradé (P0299). Contrôler N75 + durites de dépression + débitmètre AVANT remplacement."
      - "Vanne EGR encrassée (suie/calamine) : ralenti instable, perte de puissance, fumée noire, voyant moteur. Nettoyage souvent suffisant ; refroidisseur EGR peut se fissurer (perte de liquide)."
      - "Débitmètre d'air massique (MAF/G70) : perte de puissance, fumées, surconsommation (P0101/P0102)."
      - "Faisceau électrique des injecteurs-pompe : baigne dans l'huile chaude → ratés vers 1800 tr/min, moteur 'sur 3 pattes' (codes 18074-18077 / P1666-P1669 / P0301-P0304). Faisceau ~60-80 € (150-300 € posé) = répare 90 % des cas, avant l'injecteur."
      - "Pompe tandem (pompe à vide + carburant BP) : joints qui durcissent → pédale de frein dure, démarrage difficile, fuite gazole/huile, montée du niveau d'huile. Couples remontage : grosses vis 20 Nm, petites 10 Nm."
      - "Bougies de préchauffage / relais J179 : démarrage difficile à froid (<5 °C), voyant préchauffage (P0380/P0683)."
      - "Démarrage à chaud difficile (long crank) : cartographie PD + démarreur/batterie fatigués ; remède démarreur neuf ou 'Hot Start Fix' (reprog)."
    BKC:
      - "Code 105 ch le plus fiable : NON concerné par le défaut de coussinets de bielle du BXE ; >300 000-400 000 km vérifié sur flottes/taxis (note ~8,5/10)."
      - "Capteur PMH/vilebrequin G28 : démarrages aléatoires/mode dégradé possibles (P0322), contrôler connecteur."
    BXE:
      - "Coussinets de tête de bielle fragiles (alliage sans plomb) -> risque de coulée de bielle et casse moteur, sans bruit avant-coureur (claquement soudain + témoin pression d'huile). Cas documenté à 164 000 km. CONDITIONNEL : sévérité débattue. Point discriminant vs BKC à l'achat."
    BLS:
      - "SEULE version 105 ch à FAP/DPF : colmatage sur petits trajets (régénération empêchée) -> surconsommation, perte de puissance, voyant (P2452). Régénération roulante au moins 1x/mois (60-80 km/h, 25-30 min)."
      - "Capteur de pression différentielle FAP (version d'origine réputée défaillante puis révisée par VAG) : voyant FAP + clignotement préchauffage. Référence à corroborer en catalogue."
      - "Exige une huile low-SAPS VW 507.00 (pas la 505.01 standard) pour préserver le FAP."
    BRU_BXF_BXJ:
      - "1.9 TDI 90 ch : motorisation la plus endurante/simple, pannes rares avant 250 000 km ; principal point faible = le DMF, comme sur le 105."
      - "Couverture par code 90 ch moins documentée source-par-source : les points communs PD (AAC, EGR, MAF, VNT, faisceau) s'y appliquent mais restent à confirmer (voir Points à vérifier)."
  maintenance_by_engine:
    diesel_PD_commun:
      huile: "VW 505.01 IMPÉRATIVE (5W-40 ; 5W-30 505.01 acceptée), capacité ~4,3-4,8 L. Ne PAS utiliser 504.00/507.00 LongLife sauf BLS-FAP. La spec protège l'AAC PD."
      vidange: "15 000 km / 12 mois (LongLife jusqu'à 30 000 km / 2 ans selon usage) — intervalle fixe conseillé pour l'AAC."
      distribution: "Kit complet COURROIE + galets + POMPE A EAU obligatoire (pompe entraînée par la distribution) — moteur interférentiel. ~120 000 km / 5 ans (carnet : jusqu'à 150 000 ; spécialistes : 90 000-120 000). Outillage de calage VAG requis."
      filtre_carburant: "Carnet ~90 000 km, mais 30 000-60 000 km conseillé sur PD ; purge d'eau du décanteur ~10 000 km."
      filtre_air: "~90 000 km (grand entretien)."
      filtre_habitacle: "Carnet 60 000 km ; 15 000-30 000 km en usage urbain."
      liquide_frein: "Tous les 2 ans / 60 000 km (DOT4)."
      liquide_refroidissement: "VW G12+/G12++ (rose/violet, OAT) ; ne pas mélanger au G11 bleu. Contenance ~5,6 L."
      bougies_prechauffage: "~50 000-100 000 km ou si démarrage à froid difficile (M10x1, ~10-15 Nm)."
    diesel_BLS_FAP:
      huile: "Low-SAPS VW 507.00 (5W-30 LongLife 3) OBLIGATOIRE pour préserver le FAP (remplace l'ancienne 506.01/504.00)."
      fap: "Régénération roulante au moins 1x/mois (60-80 km/h, 25-30 min) ; nettoyage avant remplacement."
    diesel_4Motion:
      haldex: "Vidange huile Haldex tous les 60 000 km max (30 000 en usage intensif) + filtre, huile spécifique G055175A2. Capacité ~0,42 L."
  validation_notes:
    - "Passe 90 ch (BRU/BXF/BXJ) à compléter : forums centrés 105 ch, pannes PD communes probables mais non confirmées source-par-source avant publication."
    - "Attribution FAP=BLS et bielles=BXE : à recouper en DB AutoMecanik (compat FAP par type). Le BKC est explicitement exempté des bielles."
    - "Capteur FAP, bougies, certaines réfs OE : mono-source à corroborer."
    - "Intervalle distribution non stabilisé (90/120/150k km) -> renvoyer au carnet."
    - "Aucun prix AutoMecanik réel : toutes fourchettes indicatives/conditionnelles (comparateurs/garages)."
---

# Volkswagen Golf 5

> ⚠️ **Fiche enrichie 2026-06-16 — `review_status: draft`.** Construite depuis une recherche web exhaustive (≈360 faits sourcés, taggés par système et par code moteur) + données catalogue DB AutoMecanik. **Re-revue humaine requise** avant promotion. Tous les prix sont **indicatifs/conditionnels**. Plusieurs attributions par code moteur restent à recouper en DB (voir « Points à vérifier »).

## Présentation

La **Volkswagen Golf 5** (génération V, code interne **1K**, plate-forme **PQ35**) est une compacte du segment C produite de **2003 à 2009** (lancement 31/10/2003), entre la Golf IV et la Golf VI. Carrosseries **3 et 5 portes**[^versions]. Cette fiche couvre en priorité la motorisation **1.9 TDI** (1896 cm³, bloc **PD / injecteur-pompe** « Pumpe-Düse »), de très loin la plus représentée à l'occasion et la mieux documentée.

Trois variantes diesel 1.9 TDI coexistent, et **le code moteur est décisif** :

- **90 ch** — codes **BRU / BXF / BXJ** (type_id **18114**), réputés les plus endurants[^90fiable].
- **105 ch** — codes **BKC** (2004-2007, **la plus fiable**, >400 000 km possibles)[^bkc], **BXE** (dès 2007, **coussinets de bielle fragiles** — point de vigilance)[^bxe], **BLS** (**seule version à FAP/DPF**)[^bls]. type_id **17484**.
- **105 ch 4Motion** — transmission intégrale **Haldex**, essieu arrière **à 4 bras** (vs poutre de torsion en 2 roues motrices)[^4motion][^essieu]. type_id **18384**.

> **Pourquoi vérifier le code moteur à l'achat** : à 105 ch, un **BKC** n'a pas le défaut de bielles parfois rapporté sur le **BXE**, et seul le **BLS** porte un FAP (entretien spécifique). Le code se lit sur l'étiquette du carter de distribution / la plaque constructeur[^id].

> **2.0 TDI** : la Golf 5 a aussi reçu un 2.0 TDI PD (BKD 140 ch…) — hors cœur de cette fiche. Note comparative : le **1.9 TDI PD est globalement plus robuste sur le bas-moteur** que le 2.0 TDI PD de la même époque[^20tdi].

## Motorisations (diesel 1.9 TDI, 1896 cm³, PD)

| Puissance | Codes moteur | type_id | FAP | Particularité |
|---|---|---|---|---|
| 1.9 TDI **90 ch** | BRU / BXF / BXJ | 18114 | Non | La plus endurante ; 0-100 en 12,9 s, 176 km/h[^specs90] |
| 1.9 TDI **105 ch** | **BKC** | 17484 | Non | La plus fiable (>400 000 km) ; 250 Nm à 1900 tr/min[^specs105] |
| 1.9 TDI **105 ch** | **BXE** | 17484 | Non | Coussinets de bielle fragiles *(conditionnel)*[^bxe] |
| 1.9 TDI **105 ch** | **BLS** | 17484 | **Oui (DPF)** | Seule version à FAP ; sensible au colmatage urbain[^bls] |
| 1.9 TDI **105 ch 4Motion** | BKC/BLS/BXE | 18384 | selon code | Haldex + essieu AR 4 bras[^4motion] |

**Specs 105 ch (BKC)** : 105 ch (77 kW) à 4000 tr/min, 250 Nm à 1900 tr/min ; 0-100 km/h en **11,3 s**, 187 km/h ; conso mixte **5,0 L/100** (CO2 135 g/km)[^specs105]. **Dimensions** : 4204 × 1759 × 1485 mm, empattement 2578 mm, réservoir 55 L, coffre 350 L, poids à vide ~1287 kg[^dims].

## Pièces compatibles (catalogue AutoMecanik)

La DB AutoMecanik recense **485 gammes** de pièces compatibles avec ce véhicule (volumes relevés pour le 105 ch, type_id 17484). Aperçu par famille — chaque système renvoie à sa gamme catalogue :

**Moteur / distribution** : [[turbo]] (2200 réfs) · [[gaine-de-turbo]] (278) · [[volant-moteur]] (239) · [[pompe-a-eau]] (216) · [[radiateur-d-huile]] (205) · [[pompe-a-huile]] (191) · [[corps-papillon]] (189) · [[vanne-egr]] (262)
**Injection / alimentation** : [[filtre-a-carburant]] (229) · [[sonde-lambda]] (259)
**Freinage** : [[plaquette-de-frein]] (1228) · [[disque-de-frein]] (817) · [[etrier-de-frein]] (610)
**Liaison au sol** : [[bras-de-suspension]] (1655) · [[amortisseur]] (546) · [[kit-de-butee-de-suspension]] (293) · [[butee-elastique-d-amortisseur]] (282) · [[ressort-de-suspension]] (271) · [[rotule-de-suspension]] (195) · [[roulement-de-roue]] (189) · [[soufflet-de-cardan]] (232) · [[cardan]] (409)
**Transmission** : [[kit-d-embrayage]] (584) · [[emetteur-d-embrayage]] (392) · [[recepteur-d-embrayage]] (309)
**Électrique** : [[alternateur]] (1504) · [[demarreur]] (1259) · [[capteur-abs]] (527) · [[ampoule-feu-avant]] (390) · [[ampoule-feu-clignotant]] (203)
**Refroidissement / clim** : [[radiateur-de-refroidissement]] (698) · [[compresseur-de-climatisation]] (590) · [[ventilateur-de-refroidissement]] (173) · [[bride-de-liquide-de-refroidissement]] (183)
**Filtration / habitacle / carrosserie** : [[filtre-a-air]] (282) · [[filtre-d-habitacle]] (325) · [[pulseur-d-air-d-habitacle]] (219) · [[leve-vitre]] (531) · [[serrure-de-porte]] (208) · [[retroviseur-exterieur]] (241) · [[balais-d-essuie-glace]] (342) · [[support-moteur]] (297) · [[tube-d-echappement]] (362) · [[catalyseur]] (246) · [[pneus]] (261)

> **Plate-forme PQ35** partagée avec [[audi-a3]] (8P), [[seat-leon]] (Mk2), [[skoda-octavia]] (Mk2), [[volkswagen-touran]] et Golf Plus : trains roulants, supports moteur, EGR, refroidisseurs largement mutualisés — large disponibilité, prix compétitifs[^pq35].
> ➡️ **Références exactes par motorisation/année : voir le catalogue du site.**

## Particularités d'entretien — problèmes connus PAR SYSTÈME ET PAR MOTEUR

### Moteur interne
- **Arbre à cames + poussoirs (PD)** → [[arbre-a-cames]]. LE défaut interne récurrent du PD 8 soupapes : l'AAC actionne soupapes **et** injecteurs-pompe (3e came, contact étroit), d'où usure (came rongée, poussoir perforé) si lubrification insuffisante. Symptômes : claquement « poum-poum »/métallique à froid, perte de puissance, fumée noire. Réfection (AAC + 8 poussoirs renforcés + coussinets + joints) : **~800-1500 €**[^aac1][^aac2][^aac3].
- **Coussinets de bielle (BXE)** → bas moteur. Alliage sans plomb fragile → coulée de bielle, casse **sans signe avant-coureur** (claquement soudain + témoin pression d'huile). Cas documenté à 164 000 km. **Conditionnel** (sévérité débattue). **BKC non concerné**[^bxe][^bielle].
- **Volant bi-masse (DMF)** → [[volant-moteur]] / [[kit-d-embrayage]]. Voir Transmission.
- **Pompe tandem** (pompe à vide + carburant BP, en bout de culasse) : joints qui fuient → pédale de frein dure, démarrage difficile, gazole dans l'huile. Couples : 20 Nm / 10 Nm[^tandem1][^tandem2].
- **Fuites d'huile** : joint spi de vilebrequin (côté distribution) et carter inférieur (étanché à la pâte) suintent fréquemment[^spi].
- **Poulie damper de vilebrequin** : le caoutchouc se détériore → claquement à froid + fatigue de la courroie d'accessoires[^damper].
- **Joint de culasse** : perte de liquide, fumée blanche, pressurisation du vase — à différencier d'une durite ou d'un radiateur[^culasse].

### Injection & carburant
- **Système injecteur-pompe (PD)** : >2000 bar, un ensemble pompe+injecteur par cylindre[^pd1]. Injecteurs **très robustes** (≈30 cas sur 877 avis) → la plupart des « pannes injecteur » viennent en fait du faisceau ou du débitmètre[^injfiab].
- **Faisceau injecteurs** → ratés vers 1800 tr/min, « 3 pattes », voyant. Codes **18074-18077 / P1666-P1669 / P0301-P0304**. Faisceau ~60-80 € (150-300 € posé) = 90 % des cas[^faisceau1][^faisceau2].
- **Joints d'injecteur** : bague cuivre en pied + joints toriques à remplacer systématiquement. Pose : 12 Nm + 270°[^joints][^couple].
- **Filtre à gasoil / décanteur** → [[filtre-a-carburant]]. ~30 000-60 000 km ; **purger l'eau ~10 000 km** (l'eau tue les injecteurs)[^gasoil1][^gasoil2].
- **Préchauffage** (bougies + relais J179) : démarrage froid difficile, **P0380/P0683**[^prech].
- **Fumées** : noire = injecteur/MAF/EGR ; blanche = injecteur/préchauffage/eau ; bleue = segments/turbo[^fumees].

### Suralimentation · admission · EGR · FAP
- **Turbo VNT** → [[turbo]] (2200 réfs). Grippage par calamine → **P0299** + mode dégradé. Avant remplacement : contrôler **électrovanne N75** (peu coûteuse), durites de dépression, fuite d'admission, débitmètre[^turbo1][^n75]. Remplacement ~800-1800 € (échange standard ~245 €)[^turbocout].
- **Débitmètre MAF (G70)** → P0101/P0102 : perte de puissance, fumées[^maf].
- **Vanne EGR** → [[vanne-egr]] (262). Encrassement suie/calamine ; **nettoyage avant remplacement** (~266-600 €). **Refroidisseur EGR** peut se fissurer (perte de liquide)[^egr1][^egr2].
- **FAP (BLS uniquement)** → [[filtre-a-particules]]. Colmatage urbain (P2452), capteur de pression différentielle ; nettoyage ~65 € avant remplacement (500-1600 €). Huile **507.00** obligatoire[^fap1][^fap2].

### Refroidissement
- **Pompe à eau** → [[pompe-a-eau]]. **Entraînée par la distribution** → à changer AVEC le kit. Roue à aubes plastique qui s'érode/casse → surchauffe malgré niveau correct ; préférer une turbine **métallique**[^pae1][^pae2].
- **Thermostat** (ouvre ~87 °C) : bloqué ouvert (moteur tiède, **P0128**, encrasse FAP/EGR) ou fermé (surchauffe). Versions pilotées : P0597/P0598/P0599[^thermo1][^thermo2].
- **Sonde de température (G62)** : la d'origine **noire** tombe souvent en panne → la remplacer par une **verte** (00522 / P0116-P0118)[^g62].
- **Vase d'expansion** (plastique, se fissure ; bouchon 1,4-1,5 bar), **durites** craquelées, **ventilateur (GMV)** (résistance de petite vitesse qui grille), **pompe à eau additionnelle V51** (post-arrêt turbo)[^vase][^gmv][^v51].

### Électrique & électronique
- **Alternateur** → [[alternateur]] (poulie roue libre qui grippe/casse), **démarreur** → [[demarreur]] (démarrage chaud difficile sur BKC)[^alt][^dem].
- **ABS/ESP** → [[capteur-abs]]. Capteurs de roue (00287 AR-D / 00290 AR-G…) ; après intervention, calibrage dynamique parfois requis[^abs1][^abs2].
- **Capteurs moteur** : PMH/vilebrequin **G28** (P0322, outil de calage T10134), arbre à cames **G40** (P0341), pédale **G79** (P0227), température **G62** (P0116)[^g28][^g40][^g79].
- **Calculateur EDC16** : erreur EEPROM **01314/P1640** → non-démarrage ; immobiliseur IMMO IV (clé/antenne de colonne)[^edc][^immo].
- **Module confort (BCM)** : lève-vitres, verrouillage, feux, clim — pannes croisées[^bcm]. **Contacteur de feux stop F** (P0571 : coupe le régulateur de vitesse + décharge batterie)[^stop]. **Éclairage arrière** (corrosion porte-ampoules)[^feux].

### Transmission & embrayage
- **Volant bi-masse (DMF)** → [[volant-moteur]]. **Panne n°1** (34 cas) : 150 000-250 000 km (parfois <120 000), cliquetis/vibrations[^dmf1][^dmf2].
- **Embrayage** → [[kit-d-embrayage]] (disque **228 mm**, refs Sachs/LuK). Changé 150 000-250 000 km ; **à coupler au DMF** (éviter une 2e dépose de boîte). Ensemble **~1200-2500 €**, 3-6 h de MO[^emb1][^emb2][^emb3]. **Retrofit volant rigide (SMF)** possible (kit à disque longue course — jamais un disque standard sur volant rigide)[^smf].
- **Commande hydraulique** → [[emetteur-d-embrayage]] / [[recepteur-d-embrayage]] : fuite → pédale molle au plancher[^hydro].
- **Boîte manuelle 5** (codes GQQ/JCR…) : **synchros de 3e** parfois faibles (réfection coûteuse)[^boite].

### Train · freinage · direction
- **Essieu AR** : poutre de torsion (2WD) / **4 bras** (4Motion)[^essieu]. **Roulements de roue** → [[roulement-de-roue]] (~150 000 km, par paire, ~370 €)[^roul]. **Triangles** → [[bras-de-suspension]] (100-150k), **silentblocs**, **biellettes de barre stabilisatrice** (claquements), **amortisseurs** → [[amortisseur]] (par paire), **coupelles/butées** → [[kit-de-butee-de-suspension]][^triangle][^biell][^amort].
- **Freinage** : disque AV **ventilé 280 mm × 22**, disque AR **plein 255-256 mm × 10-12** (mini 7), entraxe 5×112 ; plaquettes AR ~87×53×17. Étriers qui se grippent (usure dissymétrique). Frein à main **manuel** à câbles[^disqueav][^disquear][^etrier][^fam].
- **Direction** électromécanique (assistance colonne ; voyant si <60 %) ; **crémaillère** ~1300 € (calibrage VCDS de l'angle de braquage après remplacement) ; rotules/biellettes de direction (claquements)[^direction][^crem].
- **Pneus** : 195/65 R15, 205/55 R16 (montes courantes), jusqu'à 225/45 R17 ; entraxe 5×112[^pneus].

## Calendrier d'entretien complet (1.9 TDI PD)

| Opération | Intervalle indicatif | Note |
|---|---|---|
| Vidange huile + filtre | 15 000 km / 12 mois (LongLife 30 000) | Capacité ~4,3-4,8 L[^vid] |
| **Huile (norme)** | **VW 505.01** 5W-40 ; **BLS-FAP → 507.00** | Impérative pour l'AAC PD[^huile][^huilebls] |
| Kit distribution **+ pompe à eau** | ~120 000 km / 5 ans | Kit complet, moteur interférentiel, outillage de calage[^distrib1][^distrib2] |
| Filtre à carburant | 30 000-90 000 km | Purger l'eau ~10 000 km[^gasoil1] |
| Filtre à air | ~90 000 km | Grand entretien[^air] |
| Filtre d'habitacle | 60 000 km (15-30k en ville) | [^hab] |
| Liquide de frein | 2 ans / 60 000 km | DOT4[^lfrein] |
| Liquide de refroidissement | G12+/G12++ (rose) | Ne pas mélanger G11 bleu[^lr] |
| Bougies de préchauffage | 50 000-100 000 km | M10x1, ~10-15 Nm[^prechentr] |
| Huile Haldex (4Motion) | 60 000 km (30k intensif) | + filtre[^haldex] |

## Coûts & temps de main d'œuvre (indicatifs / conditionnels)

| Opération | Fourchette (pièces + MO) | MO |
|---|---|---|
| Kit distribution + pompe à eau | ~400-800 € | 2-5 h[^distribcout] |
| Embrayage + volant bi-masse | ~1200-2500 € | 3-6 h[^embcout] |
| Turbo (échange std → neuf) | ~800-1800 € (échange ~245 €) | 3-5 h[^turbocout] |
| Vanne EGR | ~266-600 € | quelques h[^egr1] |
| Arbre à cames + poussoirs | ~800-1500 € | lourd (dépose culasse)[^aac3] |
| Injecteur-pompe (unité) | ~180-290 € recond. / 450-770 € neuf | [^injcout] |
| FAP (BLS) | ~500-1600 € neuf / ~65 € nettoyage | [^fap1] |

## Diagnostic (symptôme → cause probable → pièce / code)

| Symptôme | Cause probable | Pièce / action |
|---|---|---|
| Perte de puissance + mode dégradé (**P0299**) | VNT grippé | [[turbo]] (dégrippage) ; **contrôler N75 + durites + MAF avant**[^turbo1] |
| Mode dégradé, coût faible | Électrovanne N75 / durites de dépression | N75, durites — avant le turbo[^n75] |
| À-coups, ralenti instable, fumée noire (**P0101**) | Débitmètre encrassé | MAF (test débranchement)[^maf] |
| Ratés ~1800 tr/min, « 3 pattes » (**18074-18077**) | Faisceau injecteurs | Faisceau (~60-80 €)[^faisceau1] |
| Claquement « tic tic » à froid | AAC + poussoirs usés | [[arbre-a-cames]] + poussoirs[^aac1] |
| Claquement soudain + témoin pression huile (BXE) | Coussinet de bielle | Bas moteur (souvent casse) — STOP[^bielle] |
| Vibrations / claquement à l'embrayage | DMF usé | [[volant-moteur]] + [[kit-d-embrayage]][^dmf1] |
| Pédale d'embrayage molle au plancher | Émetteur/récepteur | [[emetteur-d-embrayage]]/[[recepteur-d-embrayage]][^hydro] |
| Pédale de frein dure + démarrage difficile | Pompe tandem (vide) | Pompe tandem / joints[^tandem1] |
| Surchauffe, niveau OK | Pompe à eau (turbine cassée) | [[pompe-a-eau]] (+ kit distribution)[^pae1] |
| Moteur reste tiède (**P0128**) | Thermostat bloqué ouvert | Thermostat + joint[^thermo1] |
| Jauge temp. fantaisiste, démarrage froid dur | Sonde G62 (noire) | Sonde verte[^g62] |
| Démarrage à froid difficile (**P0380**) | Bougies de préchauffage / J179 | [[bougie-de-prechauffage]], relais[^prech] |
| Voyants ABS+ESP (**00287/00290**) | Capteur de roue | [[capteur-abs]][^abs1] |
| Bourdonnement qui croît avec la vitesse | Roulement de roue | [[roulement-de-roue]] (par paire)[^roul] |
| Non-démarrage, pas de comm. calculateur (**01314**) | EEPROM EDC16 / immobiliseur | Réparation calculateur / VCDS[^edc] |
| Voyant FAP + surconso (BLS, **P2452**) | FAP colmaté / capteur pression diff. | [[filtre-a-particules]][^fap1] |

## Guide d'achat occasion (1.9 TDI)

1. **Identifier le code moteur** (carter de distribution) : **BKC** privilégié ; sur **BXE** exiger un historique d'entretien rigoureux (bielles) ; **BLS** = entretien FAP/507.00, à réserver aux trajets pas trop courts[^id][^achat].
2. **Démarrage à chaud** (long crank = démarreur/injecteurs fatigués), **fumées** à l'accélération, **claquement** moteur à froid (AAC).
3. **Historique** : distribution + pompe à eau, EGR/FAP, embrayage/DMF, injecteurs ; **diagnostic VCDS** (codes moteur/ABS/BCM)[^achat][^vcds].
4. **Train avant** : jeux rotules/triangles/biellettes (bruits dos-d'âne), état pneus (usure en facettes = géométrie).
5. **Fuites** : huile (joint spi/carter), liquide de refroidissement (vase/durites/pompe).

## Différences 105 / 90 / 4Motion · versions · tuning

- **105 ch (BKC/BLS/BXE)** : turbo plus sollicité (plus de cas turbo), bonne disponibilité de pièces. **BKC** = référence fiabilité/coût ; **BXE** = vigilance bielles ; **BLS** = FAP.
- **90 ch (BRU/BXF/BXJ)** : moins de contrainte, **la plus endurante**, mêmes points PD communs.
- **4Motion** : Haldex + essieu AR 4 bras → poids et **entretien Haldex** spécifiques (souvent négligé)[^4motion][^haldex].
- **Versions/millésimes** : 105 ch dès 2003, 90 ch dès juin 2004, DSG et 4Motion dès fin 2004 ; finitions Trendline / Confortline / Sportline / Carat[^versions][^finitions].
- **Tuning** : Stage 1 ~144-145 ch (+~40 ch) / 324-336 Nm, dans les marges ; **risque DMF/embrayage** (prévoir renforcé au-delà du Stage 1)[^tuning1][^tuning2].
- **Rappels** : pompe d'injection 2004 (fuite), conduites d'injection (risque incendie), durite d'huile boîte auto ZF[^rappels].

## Questions fréquentes

### Quel 1.9 TDI Golf 5 choisir ?
Sur le 105 ch, privilégier un **BKC** (le plus fiable, sans défaut de bielles, sans FAP). Le **90 ch (BRU/BXF/BXJ)** est réputé le plus endurant. **BXE** : surveiller les bielles. **BLS** : seul FAP, à réserver aux trajets pas trop courts[^bkc][^90fiable][^bxe][^bls].

### Quelle huile ?
**VW 505.01** (5W-40) impérative pour tous les PD sans FAP — elle protège les cames des injecteurs-pompe. Sur **BLS (FAP)** : low-SAPS **VW 507.00**[^huile][^huilebls].

### Quand changer la distribution ?
~**120 000 km / 5 ans** (carnet jusqu'à 150 000 ; spécialistes 90 000-120 000). Kit **complet + pompe à eau**, moteur interférentiel. **Le carnet prime**[^distrib1].

### Le BXE casse-t-il forcément vers 100 000 km ?
Non. Le défaut de coussinets de bielle est documenté mais sa **fréquence est débattue** ; un entretien rigoureux (505.01, vidanges) réduit le risque. Le **BKC en est exempt**[^bxe][^bielle].

### Mon moteur claque à froid, est-ce grave ?
Un claquement métallique à froid qui s'intensifie évoque l'**usure AAC/poussoirs** (PD) — faire un diagnostic avant de rouler[^aac1]. Un **claquement soudain + témoin de pression d'huile** (surtout BXE) impose l'**arrêt immédiat** (bielle)[^bielle].

### Comment savoir si le turbo est mort ?
Souvent ce n'est pas le turbo : P0299 vient fréquemment d'un **VNT grippé** (dégrippable), de la **N75**, de **durites** ou du **débitmètre** — à contrôler d'abord[^turbo1][^n75].

### Pourquoi ma pédale de frein est dure / l'embrayage au plancher ?
Pédale de frein dure = perte de dépression (**pompe tandem**)[^tandem1]. Pédale d'embrayage au plancher = **émetteur/récepteur** hydraulique[^hydro].

### Quelles pièces communes avec les autres VAG ?
Plate-forme **PQ35** : [[audi-a3]] (8P), [[seat-leon]] (Mk2), [[skoda-octavia]] (Mk2), [[volkswagen-touran]] — trains, freinage, EGR, supports largement mutualisés[^pq35].

## Sources et provenance

Toutes les sources proviennent des passes **web-research** RAW `sources/web-research/volkswagen-golf-5-19-tdi/` (2026-06-16, ~360 faits taggés `system/engine_scope/obd`). **Aucune** source recyclée `automecanik-rag`.

[^versions]: Versions, millésimes, carrosseries — https://fr.wikipedia.org/wiki/Volkswagen_Golf_V
[^finitions]: Finitions Golf 5 — https://www.caradisiac.com/fiches-techniques/modele--volkswagen-golf-5/
[^90fiable]: 1.9 TDI 90 ch endurant — https://www.fiches-auto.fr/essai-volkswagen/moteur-essai-120-13-volkswagen-golf-v-_-1l9-tdi-_-90.php
[^bkc]: BKC le plus fiable, exempt bielles — https://objectifmeca.fr/guides-techniques/moteur-bkc-19-tdi-105-fiabilite/
[^bxe]: BXE coussinets de bielle fragiles — https://objectifmeca.fr/guides-techniques/moteur-bkc-19-tdi-105-fiabilite/
[^bielle]: Casse de bielle BXE (cas 164 000 km) — https://forum.quechoisir.org/casse-bielle-golf-v-1-9-tdi-105-t17621.html
[^bls]: BLS seule version à FAP — https://www.my-procar.com/decalaminage-moteur/colmatage-fap--diesel_volkswagen_golf-1-9-tdi-90
[^4motion]: 4Motion Haldex + essieu AR 4 bras — https://www.largus.fr/fiche-technique/Volkswagen/Golf/V/2005/Berline+5+Portes/19+Tdi+105+Sport+4m+5p-835172.html
[^essieu]: Essieu AR poutre (2WD) vs 4 bras (4Motion) — https://www.golfmanuel.com/essieu_arri_re_nbsp_vue_d_ensemble-2059.html
[^id]: Identification code moteur — https://objectifmeca.fr/guides-techniques/moteur-bkc-19-tdi-105-fiabilite/
[^20tdi]: Comparaison 2.0 TDI — https://www.fiches-auto.fr/fiabilite-volkswagen/fiabilite-120-pannes-volkswagen-golf-v.php
[^specs90]: Specs 90 ch — https://www.ultimatespecs.com/car-specs/Volkswagen/1258/Volkswagen-Golf-5-19-TDI-90.html
[^specs105]: Specs 105 ch — https://www.ultimatespecs.com/car-specs/Volkswagen/1259/Volkswagen-Golf-5-19-TDI-105.html
[^dims]: Dimensions/poids/coffre — https://www.ultimatespecs.com/car-specs/Volkswagen/1259/Volkswagen-Golf-5-19-TDI-105.html
[^pq35]: Plate-forme PQ35 — https://www.fiches-auto.fr/articles-auto/plateformes-modulaires/s-3408-plateforme-pq35-groupe-vw.php
[^aac1]: Usure AAC/poussoirs PD — https://forum-auto.caradisiac.com/topic/309175-usure-abre-%C3%A0-cames-et-poussoir-perfor%C3%A9-golf-5-tdi/
[^aac2]: Kit AAC PD — https://idpartsblog.com/2024/05/03/pd-camshaft-wear-101-everything-you-need-to-know/
[^aac3]: Coût réfection AAC — https://www.auto-platinium.com/blogs/393-fiabilite-1-9-tdi
[^tandem1]: Pompe tandem, symptômes — https://www.vroomly.com/blog/pompe-tandem-fonctionnement-usure-et-prix/
[^tandem2]: Couples pompe tandem — https://lehangardunord.com/volkswagen/volkswagen-golf-4/changer-joints-pompe-a-vide-tandem-sur-golf-4-1-9-tdi/
[^spi]: Fuites joint spi / carter — https://vag-repair.com/remplacement-joint-spi-villebrequin-tdi-vw/
[^damper]: Poulie damper vilebrequin — https://www.ad.fr/guides/guide-conseil/tout-savoir-sur-l-allumage-et-le-moteur-de-votre-voiture/bruit-poulie-damper
[^culasse]: Joint de culasse — http://www.golf5forum.fr/index.php?topic=36926.0
[^pd1]: Système injecteur-pompe PD — https://strperformance.com/fr/blog/guides/preparation-19-tdi-arbre-a-cames-dbilas-272-poussoirs-ina-noir-glyco
[^injfiab]: Injecteurs robustes (~30/877) — https://www.fiches-auto.fr/articles-auto/fiabilite-moteurs-diesel/s-2436-fiabilite-des-19-tdi.php
[^faisceau1]: Faisceau injecteurs, ~60-80 € — https://objectifmeca.fr/guides-techniques/moteur-bkc-19-tdi-105-fiabilite/
[^faisceau2]: Codes faisceau 18074-18077 — https://www.vagdiscount.com/faisceau-injecteurs-golf-4-5-a3-a4-19-tdi-100-105-115-130-150-p-4191.html
[^joints]: Kit joints injecteur cuivre — https://injecteurland.com/fr/1613-kit-joints-injecteurs-pompes-1417010997-14-tdi-19-tdi.html
[^couple]: Couple pose injecteur — https://www.ntn-snr.com/sites/default/files/2017-03/KD457.37%20Pr%C3%A9conisations%20montage%20d%C3%A9montage_FR.pdf
[^gasoil1]: Filtre gasoil / décanteur — https://forum-auto.caradisiac.com/topic/329566-golf-5-filtre-gasoil-golf-5-19tdi-105/
[^gasoil2]: Filtre gasoil réf — https://www.auto-doc.fr/pieces-detachees/filtre-a-carburant-10361/vw/golf/golf-v-1k1/17484-1-9-tdi
[^prech]: Préchauffage J179, P0380/P0683 — https://vag-repair.com/controle-du-relais-de-prechauffage-j179-et-des-bougies-de-prechauffage/
[^fumees]: Fumées, causes — https://www.fiches-auto.fr/articles-auto/fiabilite-moteurs-diesel/s-2436-fiabilite-des-19-tdi.php
[^turbo1]: VNT, P0299, causes — https://p0299.fr/moteurs/p0299-1-9-tdi
[^n75]: Électrovanne N75 — https://p0299.fr/marques/vw
[^turbocout]: Coût turbo — https://www.goodmecano.com/reparation-automobile-par-marque/volkswagen/golf-5/remplacement-turbo-1409236
[^maf]: Débitmètre MAF G70 P0101 — https://vag-repair.com/16485-p0101-debitmetre-dair-massique-g70-signal-non-plausible/
[^egr1]: EGR coût/symptômes — https://www.idgarages.com/fr-fr/vehicules/volkswagen/volkswagen-golf-5-vanne-egr
[^egr2]: Refroidisseur EGR fissuré — https://www.piecesauto24.com/vw/golf-v-1k1/17484/13337/radiateur-reaspiration-des-gaz-dechappement
[^fap1]: FAP BLS nettoyage/remplacement — https://www.auto-doc.fr/pieces-detachees/nettoyage-filtre-a-particules-a-suie-15078/vw/golf/golf-v-1k1/17484-1-9-tdi
[^fap2]: Capteur pression diff. FAP — https://vag-repair.com/controler-capteur-pression-differentielle-g-450/
[^pae1]: Pompe à eau (turbine) — https://www.fiches-auto.fr/articles-auto/savoir-trouver-une-panne/s-1498-symptomes-d-une-pompe-a-eau-hs.php
[^pae2]: Pompe à eau (turbine métal) — https://www.vagdiscount.com/pompe-eau-golf-5-a3-19-tdi-105-14-tdi-p-2676.html
[^thermo1]: Thermostat 87 °C, P0128 — https://www.fiche-auto.com/code-defaut-p0597/
[^thermo2]: Thermostat bloqué fermé — https://forum-auto.caradisiac.com/topic/354544-golf-5-la-temp%C3%A9rature-liquide-de-refroidissement-ne-monte-pas-%C3%A0-90%C2%B0c/
[^g62]: Sonde G62 noire → verte — https://vag-repair.com/la-sonde-de-liquide-de-refroidissement-g2-g62/
[^vase]: Vase d'expansion / bouchon — https://www.vag-technique.fr/threads/fuite-ldr-et-surpression-vase-dexpansion.3869/
[^gmv]: Ventilateur GMV / résistance — https://vag-repair.com/tuto-reparation-bloc-ventilateur-moteur-audi-a3-golf-5/
[^v51]: Pompe à eau additionnelle V51 — https://forums.audipassion.com/topic/85268-tuto-r%C3%A9paration-pompe-%C3%A0-eau-secondaire-turbo-v51/
[^alt]: Poulie d'alternateur roue libre — https://www.alsapieces.fr/blog/102-poulie-debrayable-alternateur-symptome
[^dem]: Démarreur / démarrage chaud — https://www.largus.fr/forum-auto/panne-auto-mecanique-et-entretien/volkswagen/golf-5/le-demarreur-ne-tourne-pas/369241-1303.html
[^abs1]: Capteurs ABS/ESP 00287/00290 — https://vag-repair.com/00283-00285-00287-00290-abs-capteur-de-vitesse-de-roue-g-47-g-45-g46-g44/
[^abs2]: Calibrage ABS/ESP — https://www.vag-technique.fr/threads/panne-abs-esp-et-direction-assist%C3%A9.509/
[^g28]: Capteur PMH G28 — https://www.vag-technique.fr/threads/moteur-tdi-remplacement-cible-du-g28-capteur-vilebrequin-%C3%A0-laide-de-loutil-t10134.225/
[^g40]: Capteur AAC G40 — https://vag-repair.com/16725-p0341-000833-capteur-de-position-de-larbre-a-cames-g40-signal-improbable/
[^g79]: Capteur pédale G79 — https://vag-repair.com/transmetteurs-position-accelerateur-g79-g185/
[^edc]: EDC16 EEPROM 01314/P1640 — https://www.auto73.fr/reparation-calculateur-moteur/1214-reparation-calculateur-golf-v-et-golf-plus-pas-de-demarrage.html
[^immo]: Immobiliseur IMMO IV — https://www.plan-relance-autoroutier.fr/2025/12/29/probleme-anti-demarrage-sur-golf-5-causes-et-solutions-pour-debloquer-votre-volkswagen/
[^bcm]: Module confort BCM — https://www.cotrolia.com/produit/bcm-volkswagen-passat-golf-v-caddy-touran-2003-2009/
[^stop]: Contacteur feux stop F (P0571) — https://vag-repair.com/defaut-16955-p0571-001393-contacteur-de-feu-stop-f/
[^feux]: Éclairage arrière — https://www.techniconnexion.com/t43753-vw-golf-5-feux-arg-et-clignotant-arg-ne-fontionne-plus
[^dmf1]: DMF panne n°1 — https://ovoko.fr/blog/golf-5-1-9-tdi-105-probleme
[^dmf2]: DMF parfois <120 000 km — https://obd2.fr/2025/01/14/volkswagen-golf-5-quelles-sont-les-pannes-les-plus-frequentes/
[^emb1]: Embrayage 228 mm — https://www.ebay.co.uk/itm/254595814030
[^emb2]: Coût embrayage+DMF — https://www.ad.fr/guides/guide-conseil/tout-savoir-sur-l-embrayage-de-votre-voiture/embrayage-golf-5
[^emb3]: MO embrayage+DMF — https://www.vroomly.com/vehicules/volkswagen/golf-5/changement-d-embrayage/
[^smf]: Retrofit volant rigide — https://www.urotuning.com/products/single-mass-flywheel-clutch-kit-vw-tdi-mk6-golf-jetta-mk5-jetta-52405623
[^hydro]: Commande hydraulique embrayage — https://www.goodmecano.com/reparation-automobile-par-marque/volkswagen/golf-5/diagnostic-embrayage-ma-pedale-d-embrayage-s-ecrase-jusqu-au-sol-4337965
[^boite]: Boîte 5 (synchros 3e) — https://www.largus.fr/forum-auto/panne-auto-mecanique-et-entretien/volkswagen/golf-5/problemes-boite-de-vitesses-synchro-3eme-golf-v-2007-boite-5/229021-1303-boite-de-vitesse.html
[^roul]: Roulements de roue — https://www.vroomly.com/vehicules/volkswagen/golf-5-variant/changement-de-roulements-de-roue/
[^triangle]: Triangles/silentblocs — https://www.fiches-auto.fr/fiabilite-volkswagen/fiabilite-120-pannes-volkswagen-golf-v.php
[^biell]: Biellettes barre stabilisatrice — https://www.goodmecano.com/reparation-automobile-par-marque/volkswagen/golf-5/remplacement-jeu-biellette-barre-stabilisatrice-avant-65
[^amort]: Amortisseurs (par paire) — https://blog.piecesetpneus.com/comment-reconnaitre-un-amortisseur-defectueux-5-signes-qui-ne-trompent-pas/
[^disqueav]: Disque AV ventilé 280×22 — https://www.auto-doc.fr/pieces-detachees/disque-de-frein-10132/vw/golf/golf-v-1k1/17484-1-9-tdi
[^disquear]: Disque AR plein 255-256 — https://www.piecesauto24.com/vw/golf-v-1k1/17484/10132/disque-de-frein
[^etrier]: Étriers qui se grippent — https://www.fiches-auto.fr/fiabilite-volkswagen/fiabilite-120-pannes-volkswagen-golf-v.php
[^fam]: Frein à main manuel — https://www.golfmanuel.com/frein_main_nbsp_r_glage-1851.html
[^direction]: Direction électromécanique — https://forum-auto.caradisiac.com/topic/302755-voyant-direction-esp-allum%C3%A9-sur-golf-5/
[^crem]: Crémaillère, calibrage VCDS — https://vag-repair.com/parametragevcds-et-remplacement-cremaillere-de-direction-golf-5-leon-a3-octavia-etc-2/
[^pneus]: Pneus / entraxe 5×112 — https://www.allopneus.com/vehicule/volkswagen/golf/golf-v
[^vid]: Vidange 15 000 km — https://www.vroomly.com/vehicules/volkswagen/golf-5/revision/
[^huile]: Huile 505.01 impérative — https://www.arno-conduite.fr/huile-pour-golf-5-1-9-tdi-105/
[^huilebls]: BLS-FAP huile 507.00 — https://www.piecesauto.fr/marque-automobile/pieces-detachees-volkswagen/golf-v-1k1/17484/12094/huile-moteur.html
[^distrib1]: Distribution ~120 000 km — https://courroie2distribution.com/courroie-de-distribution-golf-5/
[^distrib2]: Distribution outillage calage — https://www.bolid.be/interventions/changement-courroie-de-distribution/volkswagen/golf-5
[^distribcout]: Coût distribution — https://www.idgarages.com/fr-fr/vehicules/volkswagen/volkswagen-golf-5-courroie-kit-de-distribution
[^air]: Filtre à air — https://www.idgarages.com/fr-fr/entretien/volkswagen/carnet-entretien-volkswagen-golf-5
[^hab]: Filtre habitacle — https://www.idgarages.com/fr-fr/entretien/volkswagen/carnet-entretien-volkswagen-golf-5
[^lfrein]: Liquide de frein — https://www.idgarages.com/fr-fr/entretien/volkswagen/carnet-entretien-volkswagen-golf-5
[^lr]: Liquide G12+/G12++ — https://www.blauparts.com/blog/types-of-vw-coolant-antifreeze-specs.html
[^prechentr]: Bougies préchauffage entretien — https://vag-repair.com/golf-5-tdi-105-changer-bougies-de-pre-chauffage/
[^haldex]: Huile Haldex / filtre — https://vag-perf.fr/tutoriels/entretien-mecanique-tfsi-vag-tutoriels/entretenir-son-haldex/
[^embcout]: MO embrayage+DMF — https://www.vroomly.com/vehicules/volkswagen/golf-5/changement-d-embrayage/
[^injcout]: Injecteur-pompe coût — https://www.auto-doc.fr/pieces-detachees/soupape-dinjection-injecteur-porte-injecteur-upi-12899/vw/golf/golf-v-1k1/17484-1-9-tdi
[^achat]: Check-list achat occasion — https://careco.fr/actu/pannes-golf-5-golf-6-symptomes-solutions-pieces-occasion/
[^vcds]: VCDS diagnostic VAG — https://vag-repair.com/controle-capteur-de-pedale-daccelerateur-g79-g175/
[^tuning1]: Stage 1 ~144 ch — https://www.puissance-injection.fr/reprogrammation-moteur/volkswagen/golf/golf-5/volkswagen-golf-1-9-tdi-105/
[^tuning2]: Tuning risque DMF/embrayage — https://www.vag-perf.fr/reprogrammation/reprogrammation-moteur-stage-1-volkswagen-golf-golf-5-2003-2008-1-9-tdi-105hp/
[^rappels]: Rappels constructeur — https://www.fiches-auto.fr/articles-auto/rappels-constructeurs/s-410-rappels-volkswagen.php

## Points à vérifier (avant promotion wiki / activation R8)

- [ ] **(a) Passe 90 ch (BRU/BXF/BXJ)** : confirmer source-par-source les points PD communs sur le 90 ch avant de publier la différenciation 90 vs 105.
- [ ] **(b) Recoupement DB** : valider **FAP = BLS uniquement** et **bielles = BXE** (BKC exempté) contre la DB AutoMecanik (compat par type).
- [ ] **(c) Prix conditionnels** : aucune valeur AutoMecanik réelle ; fourchettes indicatives (comparateurs/garages).
- [ ] **(d) Réfs mono-source à corroborer** : capteur pression différentielle FAP, certaines réfs pièces, bougies.
- [ ] **(e) Intervalle distribution** : 90/120/150k km selon source → renvoyer au carnet.
- [ ] **(f) Slugs wikilinks** : vérifier que [[arbre-a-cames]], [[filtre-a-particules]], [[bougie-de-prechauffage]], [[pneus]] résolvent vers les gammes catalogue (sinon slug canonique).
- [ ] **(g) `no_disputed_claims: false`** délibéré (bielles BXE conditionnel + FAP à recouper) → `true` après arbitrage humain.
- [ ] **(h) Promotion** → `wiki/vehicles/volkswagen-golf-5.md` (commit `promotion-from-proposals: volkswagen-golf-5`) ; si promo : `review_status: approved` + `exportable.seo: true`.
