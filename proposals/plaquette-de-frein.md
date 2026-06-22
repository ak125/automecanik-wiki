---
schema_version: 2.0.0
id: gamme:plaquette-de-frein
entity_type: gamme
slug: plaquette-de-frein
title: Plaquette de frein
aliases:
- plaquettes de frein
- garniture de frein
- garnitures de frein
lang: fr
created_at: '2026-04-28'
updated_at: '2026-06-15'
truth_level: L2
source_refs:
- kind: recycled
  origin_repo: automecanik-rag
  origin_path: knowledge/gammes/plaquette-de-frein.md
  captured_at: '2026-04-28'
- kind: raw
  path: sources/web-research/plaquette-de-frein/
  captured_at: '2026-06-15'
provenance:
  ingested_by: human:@fafa
  promoted_from: null
review_status: draft
reviewed_by: automecanik.seo@gmail.com
reviewed_at: '2026-06-02T16:48:48Z'
review_notes: |
  Pilote ADR-033 Phase 1 — enrichi 2026-04-29 avec diagnostic_relations[]
  + entity_data.maintenance. Bumped schema_version 1.0.0 → 2.0.0
  (ADR-033 + ADR-032).

  2026-04-30 : symptom_slug alignés sur slugs DB existants
  (brake_noise_metallic, brake_vibration_pedal — drift batch 20260308 EN
  legacy, utilisable mais NOUVEAUX slugs DB seront FR canon — voir
  feedback_french_only_for_content.md). 2 entrées retirées faute de slug
  DB (distance_freinage_allongee, voyant_freinage_allume).

  2026-05-02 (Phase 4 plan deja-verifier-existant) :
  - Sections H2 alignées sur ordre canon _templates/new-gamme.md
    (Définition / Fonction / Symptômes d'usure / Critères de choix /
    Compatibilité véhicule / Intentions SEO observées /
    Questions fréquentes / Sources et provenance / Points à vérifier)
  - aliases EN retirés (règle FR exclusif feedback_french_only_for_content.md) :
    "brake pad", "brake pads" supprimés
  - target_classes étendu KB_Knowledge → KB_Knowledge + KB_Catalog (gamme catalog)
  - diagnostic_relations[] : 2 nouvelles entrées seront ajoutées
    POST-merge PR monorepo #269 (distance_freinage_allongee +
    voyant_freinage_allume créés en DB par cette PR)
  - Section "Conseil pédagogique d'entretien" intégrée dans
    "Critères de choix" (canon ne prévoit pas section dédiée)
  - FAQ étendue de 3 → 5 questions

  2026-06-15 (enrichissement web-research RAW) :
  - Source : automecanik-raw/sources/web-research/plaquette-de-frein/
    (web-research frais via RUN_TARGETED_RAW_TO_WIKI, 5 agents read-only,
    103 faits reformulés + cités, 58 sources FR réelles OE/distributeurs,
    chaque fait noté confidence). Ajoutée en source_refs kind:raw
    (le kind 'web-research' n'existe pas dans frontmatter.schema.json →
    mappé kind:raw + path RAW ; sémantique web-research tracée ici).
  - Sections étoffées DANS l'ordre canon :
    * Définition / Fonction : étrier flottant vs fixe (Brembo), conversion
      énergie cinétique → chaleur (Mister-Auto/Brembo).
    * Critères de choix : passage de 3 paragraphes à 12 critères réels
      (matériaux NAO/semi-métal/fritté/céramique, type étrier, type de témoin
      d'usure acoustique vs électrique à usage unique, R90, dimensions/WVA/FMSI,
      accessoires de montage, remplacement par essieu, état disque, rodage).
    * Compatibilité véhicule : axes d'identification enrichis (essieu, dimensions,
      capteur, accessoires, OE, WVA, FMSI) + fait clé "même modèle = étriers de
      fabricants différents (ATE/TRW/Bosch…) → réf véhicule seule insuffisante".
    * Questions fréquentes : étoffée avec faits FAQ-symptoms + erreurs de montage.
    * 2 sous-sections H3 ajoutées sous "Critères de choix" : Erreurs fréquentes
      (common-mistakes) et Qualité & équipementiers (price-quality-brands ;
      prix TOUJOURS en conditionnel, jamais un prix unique générique).
  - 3 refs to_capture fantômes (bosch_fad_2020, oem_renault_clio_iii_workshop,
    tecdoc_15_02_01_brake_noise) REMPLACÉES comme provenance primaire par les
    sources web-research réelles (footnotes [^n] avec URL + type + confidence
    depuis source-index.json). Les slugs to_capture restent SEULEMENT dans
    diagnostic_relations[].sources (modèle diagnostic gouverné DB — NON modifié).
  - truth_level maintenu L2 (sources web secondaires citées, pas de surclaim L3).
  - review_status repassé approved → DRAFT : le contenu change matériellement,
    RE-APPROBATION HUMAINE REQUISE avant toute promotion vers wiki/gammes/.
  - exportable.seo repassé true → false (conséquence directe : l'invariant
    frontmatter.schema.json impose review_status=approved dès qu'un exportable.*
    est true ; une fiche draft en attente de re-revue ne doit pas rester
    SEO-exportable). La re-approbation humaine ré-activera seo:true.
  - confidence_score NON gonflé (richesse en hausse mais sources secondaires
    L2 + nombreux risques/contradictions tracés dans extraction-report.json).

  À reviewer humainement avant promotion vers wiki/gammes/.

  Tous les diagnostic_relations[].evidence ont reviewed=false +
  diagnostic_safe=false (défaut conservateur ADR-033 §D4).
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
diagnostic_relations:
- symptom_slug: brake_noise_metallic
  system_slug: freinage
  relation_to_part: possible_cause
  part_role: 'grincement aigu / bruit métallique au freinage — plaquette usée à
    la limite ou contaminée (huile, gravillons), ou mal montée'
  evidence:
    confidence: medium
    source_policy: 2_medium_concordant
    reviewed: false
    diagnostic_safe: false
    confidence_score_computed: 1.0
  sources:
  - bosch_fad_2020
  - oem_renault_clio_iii_workshop
- symptom_slug: brake_vibration_pedal
  system_slug: freinage
  relation_to_part: symptom_amplifier
  part_role: 'vibration dans la pédale de frein — plaquette dont la friction
    inégale aggrave un voile de disque préexistant'
  evidence:
    confidence: medium
    source_policy: 2_medium_concordant
    reviewed: false
    diagnostic_safe: false
    confidence_score_computed: 0.6
  sources:
  - bosch_fad_2020
  - tecdoc_15_02_01_brake_noise
entity_data:
  pg_id: 402
  family: freinage
  intents:
  - diagnostic
  - achat
  - entretien
  - remplacement
  vlevel: V2
  related_parts:
  - disque-de-frein
  - etrier-de-frein
  - kit-de-frein-arriere
  kw_top: []
  maintenance:
    educational_advice: Vérifier l'épaisseur minimum 3 mm avant un long trajet ; remplacer
      toujours par paire sur le même train.
    related_pages:
    - disque-de-frein
    - etrier-de-frein
confidence_score: 0.42
---

# Plaquette de frein

> 📥 **Pilote ADR-033 Phase 1** — fiche enrichie `diagnostic_relations[]` + `entity_data.maintenance` (ADR-032). Sections H2 ordre canon Phase 4 plan deja-verifier-existant.
> 🔄 **Enrichie 2026-06-15** depuis web-research RAW (`automecanik-raw/sources/web-research/plaquette-de-frein/`, 103 faits cités, 58 sources réelles). `review_status` repassé `draft` → **re-approbation humaine requise avant promotion**.

## Définition

La plaquette de frein est la garniture de friction pressée par l'étrier hydraulique contre le disque de frein pour ralentir le véhicule de manière progressive et répétable. Pièce d'usure standard, remplacée par paire sur chaque train (avant ou arrière).

Selon l'architecture de l'étrier, la plaquette travaille différemment : sur un **étrier flottant (ou coulissant)**, un ou deux pistons placés d'un seul côté du disque poussent la plaquette interne, puis le corps de l'étrier coulisse sur ses guides pour amener la plaquette externe au contact — la pression s'applique ainsi des deux côtés [^1][^2]. Sur un **étrier fixe**, le corps monobloc rigide porte des pistons opposés de chaque côté (deux ou plus) et applique les plaquettes de façon symétrique, avec une usure plus régulière [^1]. La géométrie du logement (et donc la forme de plaquette compatible) dépend directement de cette architecture.

## Fonction

Au freinage, la pression hydraulique dans l'étrier pousse les plaquettes contre le disque. La friction transforme l'**énergie cinétique en chaleur**, ralentissant la roue [^2][^3]. Les plaquettes s'usent progressivement à l'usage normal — une garniture neuve fait typiquement entre 6 et 12 mm selon le modèle ; en dessous de 3 mm, le remplacement devient nécessaire.

L'essieu avant assure l'essentiel de l'effort de freinage (souvent cité autour de 70 %), ce qui explique que les plaquettes avant s'usent généralement plus vite que les arrière [^4]. L'effort réparti, l'apport thermique et le style de conduite déterminent l'usure réelle.

## Symptômes d'usure

> Cette pièce **peut contribuer** à certains symptômes du système de freinage, sans en être systématiquement la cause unique. Le modèle diagnostic complet (causes probabilistes, vérifications) vit dans la DB `__diag_symptom` et l'outil diagnostic — pas ici.

- 🔊 **Grincement aigu au freinage** *(possible cause, slug DB `brake_noise_metallic`)* — usure à la limite, contamination de la garniture (huile, gravillons), ou mauvaise mise en place [^d1][^d2]
- 🛑 **Vibration dans la pédale de frein** *(symptom amplifier, slug DB `brake_vibration_pedal`)* — peut s'ajouter à un voile de disque préexistant, plaquette à friction inégale [^d1][^d3]

> **Note Phase 4** : 2 manifestations supplémentaires liées à la plaquette (`distance_freinage_allongee`, `voyant_freinage_allume`) seront ajoutées en `diagnostic_relations[]` **POST-merge PR monorepo #269** qui crée les 2 slugs FR canon manquants en DB. Voir `review_notes` pour la trace.

## Critères de choix

Choisir une plaquette de frein, c'est croiser une correspondance véhicule stricte et un compromis matériau/usage. Les critères réels, du plus structurant au plus fin :

1. **Correspondance véhicule et essieu + référence d'origine (OE).** La plaquette doit correspondre exactement au véhicule et à l'essieu concerné : plaquettes avant et arrière diffèrent en dimensions et en géométrie. La référence d'origine constructeur (OE/OEM) croisée est le repère central — même une plaquette de bonne facture devient inadaptée si elle ne respecte ni la référence ni la géométrie d'origine [^5][^6].
2. **Matériau de friction** selon l'usage [^7][^8][^9] :
   - **Organique (NAO** — Non-Asbestos Organic, à base de résine, fibres, graphite) : peu agressif pour le disque, silencieux, bon mordant à froid, mais s'use plus vite et se vitrifie (glaçage) ; usage standard et modéré, tenue thermique limitée (~400 °C au plus haut).
   - **Semi-métallique** (graphite + acier/cuivre/fer) : compromis coût/performance, robuste, bonne tenue en charge, mais plus bruyant, plus poussiéreux et plus agressif pour le disque ; usage mixte.
   - **Métal fritté** : plus dur, encaisse les températures extrêmes (~600 °C), réservé à l'usage sportif intensif ; plus bruyant et transmet davantage de chaleur à l'étrier.
   - **Céramique** : silencieux, faible émission de poussière (plus claire), comportement stable sur une large plage de température ; coût plus élevé ; indiqué pour l'urbain et les hybrides.
3. **Type d'étrier** (flottant 1-2 pistons coulissant vs fixe monobloc à pistons opposés) : c'est un **axe de compatibilité**, pas un simple détail de performance — la géométrie de plaquette doit s'y adapter [^1].
4. **Type de témoin d'usure.** Deux familles : **acoustique/mécanique** (languette métallique qui produit un bruit aigu strident au contact du disque) ou **électronique** (capteur filaire qui déclenche un témoin lumineux au tableau de bord). Généralement, seules deux plaquettes par jeu intègrent un capteur, montées côté piston [^10]. Le **capteur électrique est à usage unique** : consommé au contact du disque, il se remplace avec les plaquettes, jamais ne se réutilise [^11].
5. **Homologation ECE R90** — la pièce de rechange doit offrir des performances au moins équivalentes à l'origine, dans une tolérance de l'ordre de ±15 % (coefficient de friction, résistance mécanique) [^12]. ⚠️ R90 est un **plancher de sécurité, pas un gage d'excellence** : la norme n'évalue ni le bruit, ni l'usure du disque, ni la tenue à long terme [^12][^13].
6. **Dimensions** (hauteur, largeur, épaisseur en mm) identiques à l'origine ; la forme et les échancrures doivent correspondre à l'étrier [^6].
7. **Numéro WVA et code FMSI** — repères catalogue normalisés qui décrivent les dimensions/forme/position de la garniture et accélèrent l'identification croisée [^14][^15].
8. **Accessoires de montage** (ressorts, clips, axes, vis, tôles anti-bruit / shims) : ils maintiennent la plaquette, évitent les vibrations et assurent un contact homogène ; privilégier les références livrées avec clips et ressorts neufs, et remplacer systématiquement la quincaillerie d'usure [^16].
9. **Remplacement par essieu** — obligatoirement par paire sur un même essieu pour un freinage équilibré ; jamais une seule roue [^2].
10. **État du disque associé** — à contrôler à chaque changement : remplacer en cas d'usure hors limites, fissures ou rayures profondes ; le voile doit rester sous 0,10 mm (voiture) / 0,12 mm (utilitaire) [^2].
11. **Sens de montage** — la plaquette à échancrure / ressort de piston riveté se place côté piston ; les plaquettes fléchées suivent le sens de sortie du disque. **La prescription du constructeur du véhicule prime** sur toute autre indication [^10].
12. **Rodage** après pose — environ 200 km en freinages doux et courts, sans solliciter l'ABS, pour que la garniture épouse le disque ; un mauvais rodage compromet l'efficacité du freinage [^2].

> **Conseil entretien** : vérifier l'épaisseur minimum 3 mm avant un long trajet ; remplacer toujours par paire sur le même train (avant ensemble OU arrière ensemble, jamais une seule plaquette).

### Erreurs fréquentes à éviter

À l'achat comme au montage, plusieurs erreurs reviennent et dégradent le freinage [^17][^18][^19][^20] :

- **Ne remplacer qu'un seul côté d'un essieu** : crée un déséquilibre de freinage dangereux. Toujours par paire sur tout l'essieu. En revanche, traiter un seul essieu (avant usé, arrière sain) est légitime — la règle de la paire vaut au sein d'un essieu, pas entre les deux [^17].
- **Mélanger marques ou matériaux entre les deux côtés d'un même essieu** : pour un freinage symétrique, les deux plaquettes d'un essieu doivent partager la même référence/matériau [^17].
- **Ignorer le rodage** : sans lui, la garniture peut se vitrifier (glazing) sous l'effet de la chaleur, réduisant le coefficient de friction et allongeant les distances d'arrêt [^18].
- **Graisser la surface de friction** : n'appliquer la graisse haute température que sur les points de contact mécaniques (oreilles, dos côté piston, coulisseaux) — **JAMAIS sur la garniture ni la piste du disque**, sous peine d'annuler le freinage [^21].
- **Repousser le piston sans précaution** : utiliser un repousse-piston adapté et surveiller le bocal de liquide de frein, dont le niveau remonte et peut déborder [^20].
- **Monter les plaquettes à l'envers** (matériau ne faisant pas face au disque) : vérifier l'orientation avant serrage [^20].
- **Suspendre l'étrier par le flexible** : met le tuyau en tension et l'endommage (pédale molle, rupture possible) ; le soutenir par un fil/crochet [^20].
- **Oublier de réamorcer la pédale** : pomper plusieurs fois moteur à l'arrêt jusqu'à pédale ferme avant de reprendre la route [^20].
- **Négliger le nettoyage/lubrification des coulisseaux** de l'étrier flottant : des guides corrodés font gripper l'étrier (usure inégale des garnitures, perte d'efficacité) [^22].
- **Choisir au seul critère du prix**, sans vérifier l'homologation R90 ni la qualité [^19].

### Qualité & équipementiers

Le marché se structure en plusieurs tiers : **première monte / qualité d'origine (OE)**, **aftermarket premium équivalent OE**, et **gammes économiques**. Ce qui fait le prix d'une plaquette, c'est surtout sa composition et son process de fabrication issus de la R&D du fabricant [^23]. Brembo décrit dix critères distinguant une pièce d'origine d'une équivalente (variété des matériaux de friction, revêtements anticorrosion, tolérances dimensionnelles strictes, traitement thermique, cales antibruit multicouches, batteries d'essais et homologation R90) que les gammes économiques appliquent rarement en totalité [^24].

Parmi les équipementiers réels fréquemment cités : **Brembo** (spécialiste haute performance / sport, première monte sur de nombreux véhicules performants) [^24], **ATE** (groupe Continental, positionné haut de gamme) [^7], **Ferodo** (groupe Federal-Mogul / Tenneco, historique, souvent cité OEM) [^25], **Textar** (souvent monte d'origine sur véhicules allemands premium, travail sur le bruit — positionnement OE à confirmer modèle par modèle) [^7], **TRW** (bon équilibre prix/performance) [^7], **Bosch** (bon rapport qualité/prix), **Valeo** (gamme First présentée comme équivalente origine) [^26], ainsi que **Delphi**, **Mintex**, **Pagid** (et Hella Pagid en rechange) et **Ferodo Racing / CL Brakes** pour les usages compétition [^26][^27].

> 💶 **Prix — toujours en conditionnel.** Les fourchettes varient fortement selon véhicule, essieu et gamme : à titre purement indicatif, un jeu (un essieu) pour la pièce seule est souvent cité entre **15 € et 200 €** (moyenne ~100 €) [^4], le premier prix autour de 25-45 €/jeu et le premium autour de 60-110 €/jeu [^28]. **Ne jamais afficher un prix unique générique** : le prix réel se lit sur la fiche produit du catalogue AutoMecanik, pas sur un barème marché.

## Compatibilité véhicule

Pour vérifier la compatibilité plaquette ↔ véhicule, utiliser le sélecteur sur le site (sélection marque/modèle/année/motorisation) ou interroger la base `__seo_pg_aliases` (référence : `pg_id: 402`).

Les **axes d'identification catalogue** d'une plaquette sont [^14][^15] :

- **Essieu** (avant / arrière)
- **Dimensions** (hauteur, largeur, épaisseur en mm)
- **Présence et type de capteur d'usure** (palpeur intégré, contact inclus ou exclu)
- **Accessoires inclus** (clip de piston, tôle anti-bruit, ressorts, vis)
- **Numéro OE** (référence d'origine constructeur)
- **Numéro WVA** et **code FMSI**

⚠️ **Point clé : la référence véhicule seule ne suffit pas.** Un même modèle de véhicule peut sortir d'usine avec des **étriers de fabricants différents** (ATE/Teves, Bosch, TRW, Girling/Lucas, Bendix, Akebono — selon l'usine, l'année ou le marché). La mention du « système de freinage » sur une plaquette désigne le fabricant de l'**étrier d'origine**, pas la marque de la plaquette ; il faut souvent connaître ce système monté pour choisir la bonne référence [^29][^30]. La correspondance référence ↔ véhicule précise se vérifie via le catalogue / TecDoc, jamais par déduction éditoriale.

Pièces complémentaires fréquemment associées au remplacement :

- [[disque-de-frein]] — à inspecter systématiquement lors du changement de plaquettes
- [[etrier-de-frein]] — vérifier la liberté du piston, l'état des soufflets
- [[kit-de-frein-arriere]] — pour les véhicules à freinage arrière à disques

## Intentions SEO observées

`entity_data.intents` : `diagnostic`, `achat`, `entretien`, `remplacement` (4 intents → fiche transverse).

`vlevel: V2` (top intent : entretien + diagnostic, volume de recherche élevé).

`kw_top` : à compléter Phase 5 via DB `__seo_keywords` queries scopées sur la famille `freinage` + intents listés.

## Questions fréquentes

### Quand changer les plaquettes de frein ?

Quand l'épaisseur de la garniture descend sous environ 3 mm (le minimum toléré au contrôle technique en France est de l'ordre de 2 mm), ou plus tôt si un témoin d'usure déclenche l'alerte — bruit aigu pour le témoin acoustique, témoin lumineux au tableau de bord pour le capteur électrique [^31][^32]. À titre de repère, une garniture neuve fait souvent ~15 mm [^31].

### Comment reconnaître des plaquettes usées ?

Les premiers signes sont un **bruit anormal au freinage** (couinement, grincement, bruit aigu strident) ; un **crissement métallique persistant** traduit un stade avancé où le support métallique touche le disque — remplacement urgent [^33][^34]. S'y ajoutent un allongement de la distance de freinage, une perte d'efficacité, parfois des vibrations dans la pédale (souvent liées au disque) et l'allumage d'un témoin lumineux dédié au tableau de bord [^35][^36].

### Faut-il changer les disques en même temps que les plaquettes ?

Pas systématiquement. On conserve les disques s'ils sont en bon état, au-dessus de l'épaisseur minimale gravée et avec une surface lisse ; à l'inverse, des disques neufs imposent des plaquettes neuves [^37]. Inspecter systématiquement : épaisseur, état de surface, voile.

### Combien de temps durent des plaquettes neuves ?

Très variable selon l'usage : ordre de grandeur de **25 000 à 80 000 km**, sans kilométrage fixe qui fasse foi [^36]. La conduite urbaine (freinages fréquents) use plus vite, les longs trajets et le frein moteur prolongent la durée de vie [^4]. Plutôt qu'un kilométrage strict, contrôler visuellement l'usure régulièrement et suivre le carnet d'entretien constructeur.

### Qu'est-ce que l'homologation ECE R90 ?

Norme européenne (règlement UNECE) qui homologue les pièces de freinage de rechange : leurs performances doivent rester équivalentes à la pièce d'origine, dans une tolérance de l'ordre de ±15 % [^12][^38]. C'est un **plancher de sécurité, pas un plafond de qualité** — elle ne couvre ni le bruit, ni l'usure du disque, ni la tenue à long terme ; les bons équipementiers dépassent souvent ce socle [^12][^13].

### Est-ce normal qu'une plaquette neuve siffle ?

Oui pendant la phase de **rodage** : quelques bruits aigus légers sont normaux le temps que la garniture épouse le disque (~300-500 km en freinages doux) [^39][^40]. En revanche, un bruit de ferraille ou un crissement continu **au-delà** du rodage n'est plus normal et peut signaler un montage incorrect ou une pièce inadaptée — revérifier [^41].

### Peut-on monter des plaquettes asymétriquement (avant seul, arrière seul) ?

Oui — les plaquettes avant s'usent généralement plus vite que les arrière, et l'on peut ne traiter qu'un essieu. Mais TOUJOURS remplacer **par paire sur le même train** : avant ensemble OU arrière ensemble. Jamais une seule plaquette d'un côté, pour éviter le déséquilibre de freinage [^17].

## Sources et provenance

**Provenance primaire (enrichissement 2026-06-15)** : web-research frais collecté dans `automecanik-raw/sources/web-research/plaquette-de-frein/` (run `RUN_TARGETED_RAW_TO_WIKI`, 103 faits reformulés + cités, 58 sources FR réelles OE/distributeurs, chaque fait noté confidence). Provenance secondaire recyclée d'origine : `automecanik-rag/knowledge/gammes/plaquette-de-frein.md` (cf. `source_refs`).

Sources web-research réelles citées dans le corps (depuis `source-index.json` — `type` / `confidence`) :

[^1]: Différences entre étriers de frein fixes et flottants — Brembo. *équipementier OE*, confidence **high**. https://www.bremboparts.com/europe/fr/support/approfondissements/technologie-et-fonction-des-%C3%A9triers-de-frein-324333
[^2]: Instructions pour remplacer disques et plaquettes Kit EV — Brembo. *équipementier OE*, confidence **high**. https://www.bremboparts.com/europe/fr/support/montage-auto/instructions-pour-remplacer-les-disques-et-les-plaquettes-kit-ev-280501
[^3]: Un étrier de frein de voiture c'est quoi ? — Mister Auto. *guide distributeur*, confidence **high**. https://www.mister-auto.com/conseils-entretien/les-etriers-de-frein/
[^4]: Durée de vie moyenne des plaquettes de frein — Mister-Auto. *distributeur/guide*, confidence **high**. https://www.mister-auto.com/blog/securite/quelle-est-la-duree-de-vie-moyenne-des-plaquettes-de-frein/
[^5]: Comment choisir ses plaquettes de frein ? — Mister Auto. *distributeur/guide*, confidence **high**. https://www.mister-auto.com/conseils-entretien/comment-choisir-ses-plaquettes-de-frein/
[^6]: Guide complet pour choisir les plaquettes de frein adaptées — Tour d'Horizon. *distributeur/guide*, confidence **high**. https://tour-dhorizon.com/guide-choisir-plaquettes-de-frein/
[^7]: Comment choisir ses plaquettes de frein (Bosch, Ferodo, Textar, ATE, Brembo, TRW) — Miroirs Auto. *média/guide marques*, confidence **medium**. https://miroirs-auto2004.com/blogs/notizie/comment-choisir-les-meilleures-plaquettes-de-frein-bosch-ferodo-textar-ate-brembo-trw
[^8]: Plaquettes de frein céramiques ou métalliques : particularités, choix et prix — Vroomly. *média technique/guide*, confidence **high**. https://www.vroomly.com/blog/plaquettes-de-frein-ceramique-ou-metallique-particularites-choix-et-prix/
[^9]: Plaquettes semi-métal, métal-fritté, organiques — Plaquettemoto.fr. *média technique*, confidence **high**. https://www.plaquettemoto.fr/freinage-plaquettes-organique-metal-difference-choix.html
[^10]: Installation correcte des plaquettes de frein — ZF Aftermarket (TRW). *équipementier OE*, confidence **high**. https://aftermarket.zf.com/fr/portail-aftermarket/pour-les-ateliers/conseils-utiles/freins/installation-correcte-des-plaquettes-de-frein/
[^11]: Ce qu'il faut savoir sur les témoins d'usure des plaquettes — Delphi. *équipementier OE*, confidence **high**. https://www.delphiautoparts.com/fra/fr/article/ce-quil-faut-savoir-sur-les-temoins-dusure-des-plaquettes-de-frein
[^12]: Homologation ECE R90 : ce que cette norme garantit vraiment — Carmino. *média/blog distributeur*, confidence **high**. https://blog.carmino.fr/conseils-auto/homologation-ece-r90-ce-que-cette-norme-garantit-vraiment-sur-vos-plaquettes-et-disques-de-frein/
[^13]: Certification ECE R90 — Kavo. *équipementier OE*, confidence **high**. https://kavoparts.com/fr/certification-ece-r90-quest-ce-que-cest-et-pourquoi-est-ce-important/
[^14]: Plaquette de frein RIDEX — catalogue. *distributeur/guide*, confidence **high**. https://fr.ridex.eu/catalog/freinage/plaquette-de-frein
[^15]: Comment connaître la référence des plaquettes de frein — Autodoc. *distributeur/guide*, confidence **medium**. https://www.auto-doc.fr/info/comment-connaitre-reference-plaquettes-de-frein
[^16]: Kit d'accessoires plaquette de frein à disque — DistriAuto. *distributeur*, confidence **medium**. https://www.distriauto.fr/pieces-auto/gp1164-kit-d-accessoires-plaquette-de-frein-a-disque
[^17]: Quand et pourquoi changer des plaquettes de frein — Oscaro. *distributeur/guide*, confidence **high**. https://www.oscaro.com/fr/conseils-mecaniques/freinage/quand-comment-remplacer-plaquettes-frein
[^18]: Comment rouler après le changement de plaquettes de frein — ByMyCar. *réseau distribution auto*, confidence **high**. https://www.bymycar.fr/webzine/comment-rouler-apres-le-changement-de-plaquettes-de-frein/
[^19]: Norme ECE R90 : qualité des pièces de freinage — Motointegrator. *distributeur/guide*, confidence **high**. https://www.motointegrator.fr/blog/norme-ece-r90-les-freins-y-sont-soumis/
[^20]: Plaquettes de frein : 8 erreurs à éviter lors de leur changement — Oovango. *média/guide auto*, confidence **high**. https://www.oovango.com/plaquettes-de-frein-8-erreurs-a-eviter-lors-de-leur-changement/
[^21]: Erreurs courantes à éviter lors de l'installation — WHVoice. *média technique*, confidence **medium**. https://www.whvoice.com/plaquette-de-frein-erreurs-installation/
[^22]: Les dix principales erreurs de travail des freins — ISNCA / Safe Braking. *média technique freinage*, confidence **high**. https://isnca.org/fr/les-dix-principales-erreurs-de-travail-des-freins-pour-les-plaquettes-les-rotors-et-les-%C3%A9triers/
[^23]: Le point de vue OE pour le marché secondaire — Jurid. *équipementier OE*, confidence **medium**. https://www.jurid.com/fr-fr/blog/oe-insight-for-the-aftermarket.html
[^24]: Différencier pièces d'origine et équivalentes en 10 points — Brembo. *équipementier OE*, confidence **high**. https://www.bremboparts.com/europe/fr/support/comment-choisir-le-bon-produit/pi%C3%A8ces-de-rechange-comment-diff%C3%A9rencier-pi%C3%A8ces-d-origine-et-pi%C3%A8ces-%C3%A9quivalentes-en-10-points-219855
[^25]: Top 10 des fabricants de plaquettes de frein OEM — Kamien. *média technique/équipementier*, confidence **medium**. https://www.kamienbrake.com/fr/Top-10-des-fabricants-de-plaquettes-de-frein-OEM-en-2024/
[^26]: Plaquettes de frein Valeo First — Valeo Service. *équipementier*, confidence **medium**. https://www.valeoservice.fr/fr/voiture-de-tourisme/systeme-de-frein-pour-voiture-disque-et-plaquettes-de-frein/plaquettes-de-frein
[^27]: Plaquettes de frein compétition — AxAuto Parts. *distributeur spécialisé*, confidence **low**. https://www.axauto-parts.com/voiture/freinage/plaquettes-de-frein-competition/
[^28]: Plaquettes premium ou premier prix : coût réel sur 100 000 km — Partauto. *média technique/distributeur*, confidence **medium**. https://www.partauto.fr/blog/2026/06/02/plaquettes-premium-ou-premier-prix-quel-cout-reel-sur-100-000-km/
[^29]: Système de freinage : Teves — Carmino. *guide distributeur*, confidence **high**. https://blog.carmino.fr/conseils-auto/systeme-de-freinage-teves-ce-que-cette-mention-sur-vos-plaquettes-veut-vraiment-dire/
[^30]: Comment savoir de quelles plaquettes de frein j'ai besoin — Autodoc. *distributeur/guide*, confidence **high**. https://www.auto-doc.fr/info/quelles-plaquettes-de-frein-j-ai-besoin
[^31]: Plaquettes de frein usées : épaisseur, symptôme — AUTODOC. *distributeur/guide*, confidence **high**. https://www.auto-doc.fr/info/plaquettes-de-frein-uses-epaisseur-symptome-verifier
[^32]: Comment fonctionne le témoin d'usure des plaquettes — Fiches-auto.fr. *média technique*, confidence **high**. https://www.fiches-auto.fr/articles-auto/freinage/s-3009-comment-fonctionne-le-temoin-d-usure-des-plaquettes.php
[^33]: Plaquettes de frein usées : symptômes et dangers — Mister-Auto. *distributeur/guide*, confidence **high**. https://www.mister-auto.com/blog/securite/comment-savoir-quand-il-faut-changer-les-plaquettes-de-freins/
[^34]: Plaquette de frein usée : symptômes et conséquences — AD. *réseau garages*, confidence **high**. https://www.ad.fr/guides/guide-conseil/freinage/plaquette-de-frein-use
[^35]: Est-il dangereux de conduire avec des plaquettes usées — ByMyCar. *réseau garages*, confidence **high**. https://www.bymycar.fr/webzine/est-il-dangereux-de-conduire-avec-des-plaquettes-de-frein-usees/
[^36]: Quelle est la durée de vie des plaquettes de frein — Vroomly. *distributeur/guide*, confidence **high**. https://www.vroomly.com/blog/quelle-est-la-duree-de-vie-des-plaquettes-de-frein/
[^37]: Pourquoi remplacer disques et plaquettes ensemble — ByMyCar. *réseau garages*, confidence **high**. https://www.bymycar.fr/webzine/pourquoi-remplacer-disques-et-plaquettes-de-frein-ensemble/
[^38]: La différence entre 1ère et 2e qualité sur les pièces de freins — Alxmic. *réseau garages/distributeur*, confidence **high**. https://www.alxmic.com/difference-entre-1ere-et-2e-qualite-sur-pieces-freins-auto-rdl/
[^39]: Rodage plaquettes de frein neuves — Oscaro. *distributeur/guide*, confidence **high**. https://www.oscaro.com/fr/conseils-mecaniques/freinage/rodage-plaquettes-neuves
[^40]: Rodage des plaquettes de frein : combien de km — AUTODOC. *distributeur/guide*, confidence **high**. https://www.auto-doc.fr/info/rodage-des-plaquettes-de-frein
[^41]: Bruit au freinage après changement des plaquettes — Vroomly. *distributeur/guide*, confidence **high**. https://www.vroomly.com/blog/bruit-au-freinage-apres-changement-des-plaquettes-de-frein-que-faire/

**Sources canoniques `diagnostic_relations[].sources` (modèle diagnostic gouverné DB — NON modifié par cet enrichissement)** — restent en `status: to_capture` (Phase 7, cf. `_quality/sources-brief.md`), citées uniquement dans le bloc Symptômes d'usure :

[^d1]: `bosch_fad_2020` — Bosch FAD 2020 Brochure Réparation Freinage. Source `type: brochure`, `confidence: medium`, license `proprietary-manufacturer` — citation YAML seule (Phase 7).
[^d2]: `oem_renault_clio_iii_workshop` — Manuel d'atelier Renault Clio III, section freinage. Source `type: oem_workshop`, license `proprietary-manufacturer` — citation seule (Phase 7).
[^d3]: `tecdoc_15_02_01_brake_noise` — TecDoc fiche 15.02.01, diagnostic sonore au freinage. Source `type: tecdoc_official`, license `proprietary-manufacturer` — citation seule (Phase 7).

## Points à vérifier

- [ ] Vérifier `entity_data.pg_id: 402` aligné DB `__seo_pg_aliases` Supabase
- [ ] Confirmer `vlevel: V2` (vérifier `r7-curation-method.md` vault)
- [ ] Compléter `aliases` si autres variantes commerciales (FR uniquement — règle `feedback_french_only_for_content.md`)
- [x] **2026-04-30** : `diagnostic_relations[]` aligné sur slugs DB existants (`brake_noise_metallic`, `brake_vibration_pedal` — legacy EN drift batch 20260308, utilisable)
- [ ] **POST-PR monorepo #269 merged** : ajouter 2 entrées `diagnostic_relations[]` pour `distance_freinage_allongee` + `voyant_freinage_allume` (slugs FR canon créés par cette PR)
- [x] **2026-06-15** : provenance primaire réelle acquise — 3 ex-refs `to_capture` (`bosch_fad_2020`, `oem_renault_clio_iii_workshop`, `tecdoc_15_02_01_brake_noise`) remplacées comme provenance éditoriale par les sources web-research citées (footnotes `[^1]`..`[^41]`). Les slugs `to_capture` ne servent plus que dans `diagnostic_relations[].sources` (modèle diagnostic gouverné DB, capture Phase 7 toujours due côté diagnostic uniquement).
- [ ] **re-revue humaine du contenu enrichi 2026-06-15 avant promotion** (Critères/Compat/FAQ + sous-sections Erreurs fréquentes & Qualité étoffées depuis web-research RAW ; `review_status` repassé `draft`)
- [ ] Reconfirmer les chiffres mono-source signalés `risques` dans `extraction-report.json` avant durcissement (R90 ±15 % et dates 1999 vs 2001, seuil ~250 N/cm², plage WVA 20000-25999, épaisseurs/températures, longévités km) — présentés en conditionnel ici, à recouper sur source OE/réglementaire
- [ ] Compléter `entity_data.kw_top` via DB `__seo_keywords` (scope famille `freinage` + intents)
- [ ] Construire `_coverage/plaquette-de-frein.coverage.yaml` (Phase 5 plan parent)
- [ ] Décider promotion → `wiki/gammes/plaquette-de-frein.md` (commit message obligatoire `promotion-from-proposals: plaquette-de-frein`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
- [ ] Flip humain ciblé `evidence[*].diagnostic_safe: true` reste interdit tant que les sources ne sont pas corroborées par OEM (commit signé reviewer ≠ auteur, ADR-033 §D4)
