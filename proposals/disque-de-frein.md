---
schema_version: 2.0.0
id: gamme:disque-de-frein
entity_type: gamme
slug: disque-de-frein
title: Disque de frein
aliases:
- disques de frein
- disque frein
- disque de frein ventilé
lang: fr
created_at: '2026-06-02'
updated_at: '2026-06-20'
truth_level: L2
source_refs:
- kind: external
  origin_repo: automecanik-raw
  origin_path: sources/web-research/disque-de-frein/faq-symptoms.md
  captured_at: '2026-06-20'
- kind: external
  origin_repo: automecanik-raw
  origin_path: sources/web-research/disque-de-frein/selection-criteria.md
  captured_at: '2026-06-20'
- kind: external
  origin_repo: automecanik-raw
  origin_path: sources/web-research/disque-de-frein/compatibility-technical.md
  captured_at: '2026-06-20'
- kind: external
  origin_repo: automecanik-raw
  origin_path: sources/web-research/disque-de-frein/common-mistakes.md
  captured_at: '2026-06-20'
- kind: external
  origin_repo: automecanik-raw
  origin_path: sources/web-research/disque-de-frein/price-quality-brands.md
  captured_at: '2026-06-20'
provenance:
  ingested_by: skill:wiki-proposal-writer
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: "Reconstruite 2026-06-20 depuis le scrape web-research RUN_TARGETED_RAW_TO_WIKI\
  \ disque-de-frein (83 faits, 64 sources primaires/OE : Brembo, ATE, Textar, Ferodo,\
  \ TRW/ZF, Bosch, Delphi, Zimmermann, Hella, MAT Foundry). REMPLACE l'ancienne fiche\
  \ générée depuis recycled/rag-knowledge (RAG-recyclée, thin, cross_check NEITHER).\
  \ Axe châssis respecté : seuils (DTV, faux-rond, MIN TH) dépendent de la référence\
  \ disque + du châssis, JAMAIS du code moteur. diagnostic_relations[] laissé vide :\
  \ les symptômes (broutement, bruit, tirage) mappent vers brake_vibration_pedal /\
  \ brake_noise_grinding / brake_pulling_side, à ajouter après confirmation system_slug\
  \ via exports/diag-canon-slugs.json (pas d'invention de slug). Valeurs spécifiques\
  \ véhicule (couple Nm, cotes exactes) volontairement non généralisées (anti number-swapping)."
no_disputed_claims: true
confidence_score: 0.36
exportable:
  rag: false
  seo: true
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
diagnostic_relations:
- symptom_slug: brake_vibration_pedal
  system_slug: freinage
  relation_to_part: possible_cause
  part_role: 'vibrations et broutement ressentis au volant et à la pédale au freinage
    — disque voilé (faux-rond), variation d''épaisseur du disque (DTV) ou surchauffe
    créant des points chauds ; cause fréquente = moyeu mal nettoyé au montage'
  evidence:
    confidence: medium
    source_policy: manual_review
    reviewed: false
    diagnostic_safe: false
  sources:
  - bosch_fad_2020
- symptom_slug: brake_noise_metallic
  system_slug: freinage
  relation_to_part: possible_cause
  part_role: 'bruits, sifflement ou grincement aigu au freinage — disque trop mince,
    non-planéité (tolérance 0,1 mm) ou défaut de montage des plaquettes/anti-bruit'
  evidence:
    confidence: medium
    source_policy: manual_review
    reviewed: false
    diagnostic_safe: false
  sources:
  - bosch_fad_2020
entity_data:
  pg_id: 82
  family: freinage
  related_parts:
  - plaquette-de-frein
  - etrier-de-frein
  intents:
  - diagnostic
  - achat
  - entretien
  - remplacement
  vlevel: V4
  kw_top: []
  references: []
  maintenance:
    educational_advice: "Contrôler l'épaisseur du disque à chaque changement de plaquettes\
      \ et vérifier le voile si des vibrations apparaissent ; remplacer dès que l'épaisseur\
      \ atteint la cote MIN TH gravée sur le disque, toujours par paire sur l'essieu."
    related_pages:
    - plaquette-de-frein
  decision_brief:
    function_oneliner: "Le disque de frein transforme l'énergie cinétique du véhicule\
      \ en chaleur par friction avec les plaquettes, pour ralentir de façon stable\
      \ et répétable sur chaque essieu."
    selection_criteria_top:
    - "Compatibilité dimensionnelle OE exacte (diamètre, épaisseur neuve/mini, hauteur de bol, PCD, trous, alésage central)."
    - "Type de structure (ventilé/plein) et de surface (lisse/percé/rainuré) conformes au montage d'origine."
    - "Épaisseur mini MIN TH gravée + homologation ECE R90 + remplacement par paire d'essieu."
    compatibility_summary: "Pièce châssis : apparier la référence/les cotes au véhicule (VIN/type), jamais le code moteur."
    source_kind: web_research_oe
    cross_check_status: SOURCED_OE
---

## Rôle technique

Le disque de frein transforme l'énergie cinétique du véhicule en **chaleur par friction** avec les plaquettes, afin de ralentir le véhicule de façon stable et répétable sur chaque essieu. C'est une pièce de **châssis** : son choix dépend de la compatibilité dimensionnelle et dynamique avec le montage d'origine — jamais du code moteur.

## En bref (facettes décisionnelles)

- **Fonction** : convertir le mouvement en chaleur, dissipée par la masse et la ventilation du disque.
- **Critères de choix prioritaires** : compatibilité dimensionnelle OE exacte · structure ventilé/plein et surface lisse/percé · épaisseur mini `MIN TH` gravée · homologation **ECE R90** · remplacement **par paire d'essieu**.
- **Compatibilité** : pièce châssis — apparier la **référence et les cotes au véhicule** (VIN/type), pas au code moteur.
- _Matière sourcée OE/équipementier (Brembo, ATE, Textar, Ferodo, TRW/ZF, Bosch, Delphi, Zimmermann, Hella). Chaque seuil chiffré ci-dessous dépend de la référence disque + du châssis._

## Fonctionnement

À chaque freinage, les plaquettes serrent le disque et la friction convertit l'énergie cinétique en chaleur, qui doit être évacuée pour éviter le *fading*. Deux structures principales :

- **Disque ventilé** (canaux internes) : évacue mieux la chaleur et limite le fading ; équipe généralement l'essieu le plus sollicité ([Textar](https://textar.com/usa/brake-disc-range/)).
- **Disque plein** : adapté aux charges thermiques plus faibles (souvent l'essieu arrière) ([Textar](https://textar.com/usa/brake-disc-range/)).

La **surface percée** (perforée) reprend le design OE des sportives : elle empêche l'eau de former un coussin entre disque et plaquette → freinage plus réactif sous la pluie ([Ferodo](https://www.ferodo.com/products/light-vehicles/brake-discs/perforated-discs.html)). À réserver aux véhicules qui en étaient équipés d'origine.

## Symptômes & diagnostic

> Axe châssis : les seuils (DTV, faux-rond) dépendent de la **référence disque** et du **châssis**, pas du code moteur.

**Vibrations au volant / pédale au freinage (voile, broutement, « judder »)** — vibration ressentie dans le volant et la pédale à certaines vitesses/pressions ([Ferodo](https://www.ferodo.com/support/light-vehicles/technical-tips/Brake-Judder.html)). Trois causes réelles (le disque n'est pas forcément « voilé ») :
- **faux-rond** (runout) moyeu/disque,
- **surchauffe** créant des points chauds (taches bleues),
- **variation d'épaisseur du disque (DTV)** ([Ferodo](https://www.ferodo.com/support/light-vehicles/technical-tips/Brake-Judder.html)).

Seuils chiffrés (différenciation OE) : la **DTV ne doit pas dépasser 0,015 mm (15 µm)**, abaissée à **0,008 mm sur châssis sensibles** ; le **faux-rond après montage ≤ 0,07 mm** (0,04 mm sensibles) ([Textar](https://textar.com/en/dont-be-victim-of-dtv-problems-solutions-prevention/)). Les disques **TRW/ZF** sortent d'usine à ≤ 10 µm de variation d'épaisseur et ≤ 30 µm de faux-rond ([ZF](https://press.zf.com/press/en/releases/release_87619.html)). Effet de levier clé : une **particule de rouille de 0,05 mm** sur le moyeu peut générer **> 0,1 mm de faux-rond** sur la piste — d'où le broutement après pose sur moyeu sale ([Delphi](https://www.delphiautoparts.com/resource-center/article/how-to-prevent-brake-judder)).

**Bruits au freinage** — classement par fréquence : **broutement < 300 Hz**, **sifflement 300–5000 Hz**, **crissement aigu > 5 kHz** ([Ferodo](https://www.ferodo.com/support/light-vehicles/technical-tips/Brake-Noise.html)). Un sifflement vient souvent d'un piston d'étrier collant, d'une **non-planéité du disque (tolérance 0,1 mm)**, de plaquettes/anti-bruit mal montés ou d'un **disque trop mince** ; les axes de guidage d'étrier mal lubrifiés se grippent (usure conique + bruit) — **l'entretien de l'étrier fait partie du remplacement du disque** ([Ferodo](https://www.ferodo.com/support/light-vehicles/technical-tips/Brake-Noise.html)).

## Quand remplacer le disque ?

Remplacer dès qu'un de ces critères est atteint ([Brembo](https://www.bremboparts.com/america/en/support/maintenance/indications-and-bedding-in-90374)) :
- épaisseur **≤ MIN TH** (valeur gravée en mm sur le diamètre extérieur ou le bol ; mesurer en **≥ 4 points**, retenir la plus basse — au point le plus mince entre canaux pour un ventilé) ([Brembo MIN TH](https://www.bremboparts.com/europe/en/support/maintenance/minimum-brake-disc-thickness-212337)) ;
- **rayures/sillons circulaires profonds** ou **fissures radiales** ;
- **taches sombres / points bleus** (surchauffe) ;
- **déformation** de la piste.

Sous le MIN TH : moindre dissipation thermique, **fissures thermiques**, déformation, course pédale allongée, risque de **vapor-lock (fluide > 200 °C)** et de fading ([Brembo MIN TH](https://www.bremboparts.com/europe/en/support/maintenance/minimum-brake-disc-thickness-212337)). Au-delà de **650 °C**, la fonte se transforme en cémentite (usure inégale) ([Delphi](https://www.delphiautoparts.com/resource-center/article/how-to-prevent-brake-judder)).

**Toujours par paire d'essieu** : remplacer les deux disques d'un même essieu ensemble (même si un seul est sous le minimum), avec **plaquettes neuves** et un montage identique des deux côtés (équilibre de freinage, anti-tirage) ([Brembo](https://www.bremboparts.com/europe/en/support/car-fitting/instructions-for-replacement-of-brake-disc-278446), [Hella](https://www.hella.com/techworld/en/ti/testing-the-minimum-thickness-of-a-brake-disc/)).

## Critères de choix selon le véhicule

Pièce **châssis** : la sélection repose sur la compatibilité dimensionnelle exacte et la conformité au montage d'origine.

1. **Référence OE / compatibilité exacte** — apparier 7 paramètres : diamètre extérieur, épaisseur neuve, épaisseur mini, hauteur (déport du bol), **PCD**, nombre de trous, alésage central ([ATE](https://www.ate.co.za/assets/documents/public/Brake%20disc%20DIAMETER%20listing-2-3.pdf), [wheel-size](https://www.wheel-size.com/articles/pcd-pitch-circle-diameter/)). Valider par VIN/type.
2. **Structure ventilé vs plein** — selon la charge thermique de l'essieu ([Textar](https://textar.com/usa/brake-disc-range/)).
3. **Surface lisse vs percé/rainuré** — réserver le percé aux applications qui en avaient d'origine ([Ferodo](https://www.ferodo.com/products/light-vehicles/brake-discs/perforated-discs.html)).
4. **Diamètre & épaisseur neuve** — à apparier à l'origine (ex. Zimmermann AV 340×30 mm, 5×112, ventilé percé — [AUTODOC](https://www.autodoc.de/info/zimmermann-bremsscheiben)).
5. **Épaisseur mini MIN TH** — cote gravée ; sous cette valeur → remplacement ([Brembo](https://www.bremboparts.com/europe/en/support/maintenance/minimum-brake-disc-thickness-212337)).
6. **PCD / nombre de trous / alésage central** — identiques à l'origine pour le montage ([ATE](https://www.ate.co.za/assets/documents/public/Brake%20disc%20DIAMETER%20listing-2-3.pdf)).
7. **Couronne ABS** — sur applications concernées, anneau ABS de type OE requis ([Bosch](https://www.amazon.com/Bosch-BD1083-Brake-Discs-Certified/dp/B00BHINZDI)).
8. **Traitement anticorrosion** — vernis UV base eau Brembo, **Coat Z** Zimmermann, **COAT+** Ferodo, Geomet aftermarket ([Brembo Prime](https://www.bremboparts.com/europe/en/products/prime/brake-discs), [Zimmermann](https://www.zimmermann-bremsentechnik.eu/info/faq.html?language=en)).
9. **Homologation ECE R90** — obligatoire depuis **nov. 2016** pour les disques de rechange des modèles nouvellement immatriculés ; marquage E-mark + n° + code pays ([ATE](https://www.ate-brakes.com/products/disc-brakes/ece-r90-for-brake-discs/)). Matière **haute teneur en carbone (HC)** = freinage plus silencieux ([Brembo](https://www.bremboparts.com/europe/en/products/prime/brake-discs)).
10. **Remplacement par paire d'essieu** + plaquettes neuves ([Hella](https://www.hella.com/techworld/en/ti/testing-the-minimum-thickness-of-a-brake-disc/)).
11. **Tolérances de montage** — voile latéral **< 0,05 mm** (jusqu'à 0,10 mm sur anciens), **DTV ≤ ~12-15 µm** ([ZF/TRW](https://aftermarket.zf.com/us/aftermarket-portal/for-workshops/useful-tips/brakes/brake-judder/)).
12. **Couple de serrage & propreté du moyeu** — couple prescrit dans l'ordre correct, moyeu propre sans rouille ni lubrifiant, contrôle du voile après pose ([Zimmermann](https://www.zimmermann-bremsentechnik.eu/info/faq.html?language=en)). _Le couple en Nm est spécifique au véhicule — se référer à la fiche véhicule._

## Compatibilité technique avancée (ABS, ventilation, VIN)

Au-delà des cotes, trois spécificités des disques modernes conditionnent la compatibilité — toujours sur l'axe châssis, jamais le code moteur :

- **Couronne ABS intégrée — du même type que l'origine, impérativement.** Sur beaucoup de modèles français (ex. **Peugeot 308 arrière**), le disque arrière intègre le roulement de roue **et** la couronne ABS en un seul ensemble ([Hella](https://www.hella.com/techworld/sg/ti/brake-discs-with-wheel-bearing-and-impulse-ring/), [Textar](https://textar.com/en/brake-disc-range/)). Deux technologies **non interchangeables** : couronne **dentée** (capteur passif inductif) ou **bague magnétique multipôles** (capteur actif Hall, lit jusqu'à très basse vitesse). Un disque à la bonne géométrie OE mais au **mauvais type de couronne** provoque une **panne ABS** post-montage ([Apec](https://apecautomotive.co.uk/techmate-guides/abs-sensors/)). La bague magnétique attire la limaille : couronne propre, segments intacts, orientation selon la notice, remplacement **par paire** ([TRW/ZF](https://www.trwaftermarket.com/en/magnetic/)).
- **Ventilation directionnelle → référence gauche ≠ droite.** Les disques ventilés à **ailettes courbes orientées** existent en deux références G/D (le sens des ailettes pompe l'air selon la rotation) ; la ventilation **à plots (Brembo PVT)** est non directionnelle → une seule référence pour les deux côtés ([Brembo](https://www.bremboparts.com/europe/fr/support/comment-choisir-le-bon-produit/disques-de-frein-avec-ventilation-%C3%A0-ailettes-et-%C3%A0-plots-les-diff%C3%A9rences-204921)).
- **Le VIN n'encode pas le diamètre du disque.** Il renseigne moteur/année/finition, qui _corrèlent_ avec la taille de frein, mais un même modèle reçoit **plusieurs diamètres** selon le pack de freinage ou des révisions en cours d'année. Méthode fiable : VIN → **référence OE constructeur** puis cross-référence TecDoc, ou **mesurer le disque existant** — jamais déduire la taille du seul VIN ([stat.vin](https://stat.vin/blog/how-to-check-rotor-size-by-vin-number)).
- **Monobloc vs composite.** Un disque **composite deux pièces** (piste fonte + bol aluminium, OE sur certaines premium, −15 à −20 % de masse) ne se substitue pas librement à un monobloc fonte sans validation de fitment ([Textar](https://textar.com/en/brake-disc-range/)).

## Marques & équipementiers

- **Premium / OE** : Brembo (gamme Prime, matière HC), ATE, Textar, Ferodo, TRW (groupe ZF), Bosch (dont **iDisc** revêtu, ~90 % de poussières en moins et anticorrosion — utile sur VE), Zimmermann (Coat Z).
- **Fonte / fonderie** : MAT Foundry (corrosion fonte).
- Privilégier une référence **homologuée ECE R90** quelle que soit la marque.

## Prix & niveaux de qualité

> Ordres de grandeur marché FR — **indicatifs** (par disque, sources secondaires : TTC/HT et « par disque vs paire » pas toujours explicites), pas des prix de vente.

- **Tiers de qualité.** Peloton OE/première monte resserré : ATE, Textar, Brembo, TRW, Bosch, Zimmermann (notes utilisateurs AutoDoc 2025 de 8,60 à 8,99 — [AutoDoc](https://club.auto-doc.fr/review/parts/disques-de-frein)). Bosch revendique ~1 400 références couvrant 99 % du parc, fonte HC depuis 1983 ([Bosch](https://www.actu-automobile.com/2017/03/16/disques-et-plaquettes-de-frein-bosch-pour-un-freinage-maitrise/)).
- **Fourchettes indicatives (par disque, FR).** Plein nu ~10-20 € · rainuré ~20-30 € · percé ~25-30 € · ventilé ~25-45 € · paire avant ~40-150 € selon Ø ([Vroomly](https://www.vroomly.com/blog/quel-est-le-prix-dun-changement-de-disque-de-frein/)) ; Brembo ~80 € en moyenne, amplitude ~26-322 € ([AutoDoc](https://club.auto-doc.fr/magazin/disques-de-frein-les-meilleures-marques)). Repère coût total : un freinage avant complet (disques + plaquettes + pose) ~440 € en moyenne FR 2025 ([idGarages](https://www.idgarages.com/fr-fr/a-propos/barometre-entretien-auto-2025)).
- **Le vrai différenciateur = le revêtement anticorrosion, pas la marque seule.** Delphi annonce **720 h en brouillard salin contre ~24 h** pour un disque nu (revendication équipementier Delphi, Geomet sur tout le disque — [Delphi](https://www.delphiautoparts.com/fr-fr/centre-de-documentation/article/disques-de-frein-peints.-ils-ne-sont-pas-tous-pareils-!)). Côté OE : Zimmermann **Coat Z** (pose immédiate sans retrait — [Zimmermann](https://www.otto-zimmermann.de/en/products/coat-z-coated-brake-discs/)), Hella zinc lamellaire sans chrome ([Hella](https://www.hella.com/techworld/us/ti/coated-brake-disc/)), Brembo Prime UV homologué ECE R90 ([Brembo Prime](https://www.bremboparts.com/europe/fr/produits/prime/disques-frein)). Un disque **nu** n'offre aucune protection (oxydation accélérée l'hiver, sel).
- **Durée de vie (ordre de grandeur).** ~60 000-120 000 km, l'avant (60-70 % de l'effort) s'usant plus vite que l'arrière ; usage intensif dès ~40 000 km — mais le critère reste le **MIN TH** gravé, pas le kilométrage ([ATE](https://ate-freinage.fr/blog/duree-vie-disque-frein/)).
- **Sport (percé/rainuré) = coût caché.** Percé (Brembo Xtra, mordant initial, look) et rainuré (Brembo Max, dissipation, racing) sont homologués route mais **plus agressifs sur l'usure des plaquettes** qu'un disque nu ([Brembo](https://www.bremboparts.com/europe/fr/support/comment-choisir-le-bon-produit/disque-brembo-max-ou-disque-brembo-xtra-quelle-est-la-meilleure-solution-pour-ma-voiture-93372)).

## Entretien & corrosion

- **Rodage d'un disque neuf** : nettoyer la portée du moyeu, vérifier le faux-rond (≤ 0,10 mm voiture, mesuré à 5 mm du bord), puis rouler **~200 km** en freinages doux, **sans freinage brusque > 3 s**, pour transférer un film de friction homogène ([Brembo](https://www.bremboparts.com/europe/en/support/car-fitting/instructions-for-replacement-of-brake-disc-278446)).
- **Surfacer/rectifier** : déconseillé en pratique — la DTV vient le plus souvent d'un **moyeu mal nettoyé** et réapparaît si la cause n'est pas traitée ([Textar](https://textar.com/en/dont-be-victim-of-dtv-problems-solutions-prevention/)) ; un disque sous MIN TH ne peut pas être rectifié.
- **Corrosion** : la rouille de surface part en roulant et ne justifie pas un remplacement ; une corrosion sévère provoque usure inégale, vibrations/bruit et peut allonger les distances d'arrêt ([MAT Foundry](https://www.matfoundrygroup.com/blog/why-brake-disc-rust-happens-and-how-to-prevent-it)).

## Erreurs fréquentes (achat & montage)

> Axe châssis : la vérité est la **référence pièce + sa dynamique** (Ø, épaisseur, ventilé/plein, MIN TH, voile, couronne ABS), jamais le code moteur.

**À l'achat**
- **Se tromper de géométrie** : un disque **ventilé** et un **plein** ne sont pas interchangeables sans changer l'étrier/le support ([PowerStop](https://www.powerstop.com/resources/solid-vented-rotors-which-type/)).
- **Oublier l'homologation ECE R90** (obligatoire depuis nov. 2016) ou **la couronne ABS intégrée** (cf. compatibilité avancée — [Hella Pagid](https://www.hella-pagid.com/hellapagid/assets/media/Brake_Disc_ABS_PAGID_EN.pdf)).

**Au montage**
- **Ne pas nettoyer le moyeu** : un point de rouille crée un micro-décalage amplifié vers l'extérieur → **voile** ; décaper jusqu'au métal brillant ([ATE](https://ate-freinage.fr/blog/disque-voile/)).
- **Garder des plaquettes usées sur un disque neuf** : transfert inégal → bruit, vibration, **DTV** dès le premier jour ([Brembo](https://www.bremboparts.com/europe/fr/support/montage-auto/instructions-de-remplacement-du-disque-de-frein-278446)).
- **Mal gérer le revêtement** : disque protégé à l'**huile** → dégraisser au nettoyant frein ; disque à **revêtement intégré** (Textar PRO, Coat-Z, ATE) → **ne PAS dégraisser** (il disparaît aux premiers freinages) ([Textar](https://textar.com/usa/brake-disc-range/)).
- **Graisser le contact moyeu/disque** : interdit (fausse le placage, favorise le voile thermique) — aucune graisse sur la piste de friction ([TRW/ZF](https://www.trwaftermarket.com/en/passenger-cars-and-lcv/disc-brake-systems/brake-discs/)).
- **Serrer de travers ou au pistolet** : pré-serrage **en étoile** puis serrage final **au couple constructeur à la clé dynamométrique** — un couple inégal déforme le disque ([ATE](https://ate-freinage.fr/blog/montage-disque-frein/)).
- **Laisser pendre l'étrier par le flexible** : toujours le **soutenir au châssis** ([Brembo](https://www.bremboparts.com/europe/fr/support/montage-auto/instructions-de-remplacement-du-disque-de-frein-278446)).

**Après montage**
- **Sauter le rodage** : ~200-300 km en freinages doux et courts (< 3 s, **sans déclencher l'ABS**) pour établir la couche de transfert ([Brembo](https://www.bremboparts.com/europe/fr/support/entretien/indications-et-rodage-90374)).

## FAQ

**Le volant tremble au freinage, mon disque est-il voilé ?** Pas nécessairement : le broutement vient surtout d'un **faux-rond**, d'une **surchauffe** ou d'une **DTV** (variation d'épaisseur), souvent causée par un moyeu mal nettoyé au montage ([Ferodo](https://www.ferodo.com/support/light-vehicles/technical-tips/Brake-Judder.html), [Textar](https://textar.com/en/dont-be-victim-of-dtv-problems-solutions-prevention/)).

**Faut-il changer les deux disques de l'essieu ?** Oui, toujours par paire, avec plaquettes neuves ([Brembo](https://www.bremboparts.com/europe/en/support/car-fitting/instructions-for-replacement-of-brake-disc-278446)).

**La rouille sur mes disques est-elle grave ?** La rouille de surface part en roulant ; seule une corrosion sévère impose un contrôle ([MAT Foundry](https://www.matfoundrygroup.com/blog/why-brake-disc-rust-happens-and-how-to-prevent-it)).

**Combien de temps dure un disque ?** Ordre de grandeur **~48 000 à 112 000 km**, contrôle conseillé vers 100 000 km et inspection plaquettes+disques chaque année ; SUV/véhicules lourds usent plus vite ([Autodoc](https://www.autodoc.co.uk/info/how-long-should-brake-pads-and-discs-last-in-the-uk-in-miles)) — _ordre de grandeur, dépend du véhicule et de la conduite._

## Conformité de la pièce de rechange

En Europe, les disques de rechange relèvent d'**ECE R90 (R90-02)** : obligatoire pour les voitures immatriculées après **nov. 2016** ; marquage code **E** ([ECE R90](https://en.wikipedia.org/wiki/ECE_Regulation_90)).

## Provenance & qualité

Fiche **reconstruite le 2026-06-20** depuis le scrape web-research (`automecanik-raw/sources/web-research/disque-de-frein/`, 83 faits / 64 sources primaires/OE). **Remplace** l'ancienne fiche dérivée de `recycled/rag-knowledge` (RAG-recyclée, non sourcée). Chaque affirmation porte sa source OE/équipementier. Les valeurs spécifiques véhicule (couple Nm, cotes exactes) ne sont **pas** généralisées (anti number-swapping). `review_status: proposed` — revue humaine requise avant promotion vers `wiki/gamme/`. Les 5 champs scrapés sont désormais intégrés (faq-symptoms, selection-criteria, compatibility-technical, common-mistakes, price-quality-brands), chacun sourcé OE/équipementier. Les valeurs de prix et durée de vie sont données en **ordres de grandeur** (sources secondaires) ; le chiffre 720 h vs 24 h brouillard salin est une **revendication équipementier** (Delphi), pas un test indépendant.
