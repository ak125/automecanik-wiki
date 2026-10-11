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
updated_at: '2026-10-11'
truth_level: L2
source_refs:
- kind: raw
  path: sources/auto-captures/plaquette-de-frein/aftermarket-zf-com-wl-plaquette-de-frein-zf-installation-565c00d2.md
  cid: sha256:6f4636a477d2bd398b789a80ca0443b5c8361de3c697dc3cd9b4a85cefa4eb37
  captured_at: '2026-10-10'
  confidence: high
- kind: raw
  path: sources/auto-captures/plaquette-de-frein/bremboparts-com-wl-plaquette-de-frein-brembo-etriers-c18ae549.md
  cid: sha256:05d748bc57eb1c952bb36141cc707b443b21bc4d0777356905e9a71b6aceb5a8
  captured_at: '2026-10-10'
  confidence: high
- kind: raw
  path: sources/auto-captures/plaquette-de-frein/bremboparts-com-wl-plaquette-de-frein-brembo-origine-equival-ebb13203.md
  cid: sha256:87deee38f48156b2fe7cffbf2080117358c4de7235b5b7883b78f9fa6bdeef1e
  captured_at: '2026-10-10'
  confidence: high
- kind: raw
  path: sources/auto-captures/plaquette-de-frein/bremboparts-com-wl-plaquette-de-frein-brembo-remplacement-51e9790a.md
  cid: sha256:ac179373a261661bc14b66b251c0e719803b5f045e4136da92d1260b8f51d738
  captured_at: '2026-10-10'
  confidence: high
- kind: raw
  path: sources/auto-captures/plaquette-de-frein/delphiautoparts-com-wl-plaquette-de-frein-delphi-temoins-usu-a57fe2c9.md
  cid: sha256:76b90102bc27f734d5c849b0443a3cc5c0816291831ada22dce5c6be427725bd
  captured_at: '2026-10-10'
  confidence: high
- kind: raw
  path: sources/auto-captures/plaquette-de-frein/fr-wikipedia-org-wl-plaquette-de-frein-wikipedia-fr-f3c3e816.md
  cid: sha256:9f3297f619c04853f548342a22f148c757e4373a28ed267eb471ecb54c0a7933
  captured_at: '2026-10-10'
  confidence: low
- kind: external_url
  url: https://aftermarket.zf.com/fr/portail-aftermarket/pour-les-ateliers/conseils-utiles/freins/installation-correcte-des-plaquettes-de-frein/
  captured_at: '2026-10-10'
- kind: external_url
  url: https://www.bremboparts.com/europe/fr/support/approfondissements/technologie-et-fonction-des-%C3%A9triers-de-frein-324333
  captured_at: '2026-10-10'
- kind: external_url
  url: https://www.bremboparts.com/europe/fr/support/comment-choisir-le-bon-produit/pi%C3%A8ces-de-rechange-comment-diff%C3%A9rencier-pi%C3%A8ces-d-origine-et-pi%C3%A8ces-%C3%A9quivalentes-en-10-points-219855
  captured_at: '2026-10-10'
- kind: external_url
  url: https://www.bremboparts.com/europe/fr/support/montage-auto/instructions-pour-remplacer-les-disques-et-les-plaquettes-kit-ev-280501
  captured_at: '2026-10-10'
- kind: external_url
  url: https://www.delphiautoparts.com/fra/fr/article/ce-quil-faut-savoir-sur-les-temoins-dusure-des-plaquettes-de-frein
  captured_at: '2026-10-10'
- kind: external_url
  url: https://fr.wikipedia.org/wiki/Plaquette_de_frein
  captured_at: '2026-10-10'
  confidence: low
provenance:
  ingested_by: skill:wiki-proposal-writer
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: "Révisée 2026-10-11 : chaque affirmation repose sur l'une de six pages\
  \ archivées dans RAW (sources/auto-captures/plaquette-de-frein/, PR RAW #69) :\
  \ cinq pages d'équipementiers de freinage (montage des plaquettes, technologie\
  \ des étriers, pièces d'origine et équivalentes, procédure de remplacement,\
  \ témoins d'usure) et l'article Wikipédia, utilisé seulement en corroboration\
  \ (plafond low). Les six sources restent to_capture jusqu'à leur activation par\
  \ le propriétaire. Les six références external_url désignent les mêmes pages que\
  \ les références raw (même document, pas une source indépendante). Retirés faute\
  \ de preuve archivée : anciennes références recycled et web-research, épaisseur\
  \ minimale chiffrée, distance de rodage, contrôle avant un long trajet, causes de\
  \ grincement par contamination de la garniture, relation de vibration dans la\
  \ pédale (voile de disque), conversion de l'énergie cinétique en chaleur et\
  \ familles de matériaux de friction (attestées par Wikipédia seul), hiérarchie de\
  \ marques. Aucune valeur de couple, de pression, de cote, de température ni de\
  \ distance n'est publiée. Les pages disque-de-frein, etrier-de-frein et\
  \ kit-de-frein-arriere n'existent pas encore dans wiki/ : aucun lien n'y pointe,\
  \ les relations restent dans entity_data. diagnostic_relations[] : une relation\
  \ (grincement aigu au freinage) en confiance moyenne, 2_medium_concordant,\
  \ reviewed=false, diagnostic_safe=false. L'allumage du témoin d'usure au tableau\
  \ de bord (plaquettes à témoin électronique) est décrit dans le corps mais n'est\
  \ pas modélisé en relation : le référentiel diagnostic n'a aucun slug de ce type\
  \ en freinage, et aucun slug n'est inventé. Licence de l'article Wikipédia : le\
  \ catalogue indiquait CC-BY-SA-3.0, la capture RAW porte license null\
  \ (license_status unknown) ; à trancher par le propriétaire."
no_disputed_claims: true
confidence_score: 0.89
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
  part_role: "plaquette en fin d'usure, dont l'indicateur mécanique ou les languettes\
    \ métalliques émettent un son strident au contact du disque (signal voulu) ;\
    \ plaquette ou accessoires mal montés, ou plaquette directionnelle du mauvais\
    \ côté, causes de bruit au freinage"
  evidence:
    confidence: medium
    source_policy: 2_medium_concordant
    reviewed: false
    diagnostic_safe: false
  sources:
  - zf_installation_plaquettes
  - delphi_temoins_usure
  - bremboparts_oe_vs_equivalent
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
  related_gammes:
  - disque-de-frein
  - etrier-de-frein
  - kit-de-freins-arriere
  - liquide-de-frein
  commerce_intent:
  - remplacement_piece
  - entretien_preventif
  - diagnostic_avant_achat
  maintenance:
    educational_advice: "Contrôler les plaquettes à intervalles réguliers et les\
      \ remplacer par essieu à la limite d'usure ou quand le témoin d'usure s'allume,\
      \ en suivant les prescriptions du constructeur du véhicule."
    related_pages:
    - disque-de-frein
    - etrier-de-frein
  editorial:
    function:
      content_md: >-
        Dans l'étrier, la pression hydraulique venue du maître-cylindre agit sur les pistons, qui
        poussent les plaquettes contre le disque pour ralentir ou arrêter le véhicule. Après le
        freinage, des ressorts ramènent les plaquettes en position de repos et les maintiennent contre
        leurs pistons.
      source_ids: [oem:bremboparts_technologie_etriers]
      truth_level: sourced
    variants:
      content_md: >-
        L'étrier flottant a ses pistons d'un seul côté : ils poussent une plaquette, et l'autre est
        poussée par le corps de l'étrier, qui glisse sur des guides. C'est le type le plus répandu sur
        les véhicules d'entrée et de milieu de gamme et sur les utilitaires légers. L'étrier fixe porte
        des pistons opposés ; on le trouve sur les véhicules sportifs de milieu à haut de gamme.
      source_ids: [oem:bremboparts_technologie_etriers]
      truth_level: sourced
    failure_symptoms:
      content_md: >-
        Un symptôme seul ne désigne pas la plaquette. En fin d'usure, les languettes métalliques et les
        indicateurs d'usure mécaniques émettent un son strident au contact du disque ; sur les
        plaquettes à témoin électronique, le témoin s'allume au tableau de bord. Une plaquette ou des
        accessoires mal montés causent dans la plupart des cas des bruits de freinage ou une
        performance réduite des freins.
      source_ids: [oem:delphi_temoins_usure, oem:zf_installation_plaquettes]
      truth_level: sourced
    selection_criteria:
      content_md: >-
        Le choix part du véhicule : la plaquette doit être adaptée à sa marque et à son modèle, et les
        prescriptions du constructeur priment sur toute autre indication. Il existe de nombreux
        matériaux de friction, adaptés à chaque véhicule et à chaque style de conduite. Le type
        d'indicateur d'usure, mécanique ou électrique, dépend de la conception du système de freinage.
      source_ids: [oem:bremboparts_remplacement_kit, oem:zf_installation_plaquettes, oem:bremboparts_oe_vs_equivalent, oem:delphi_temoins_usure]
      truth_level: sourced
    quality_tiers:
      content_md: >-
        Les pièces d'origine portent le logo « OE supplier ». Une page d'équipementier cite comme marques
        de qualité un traitement thermique de surface qui limite la perte d'efficacité à chaud, un shim
        antibruit multicouche et des essais sur bancs puis sur route. Cette fiche ne classe pas les
        marques.
      source_ids: [oem:bremboparts_oe_vs_equivalent]
      truth_level: sourced
    standards_norms:
      content_md: >-
        En Europe, l'homologation ECE R90 est obligatoire pour commercialiser des disques et des
        plaquettes de frein.
      source_ids: [oem:bremboparts_oe_vs_equivalent]
      truth_level: sourced
    maintenance_interval:
      content_md: >-
        Les plaquettes s'usent et doivent être contrôlées à intervalles réguliers. La vitesse d'usure
        dépend des conditions de la route, du style de conduite, de la vitesse, de la charge et du type
        de plaquettes et de disques. Cette fiche ne donne ni durée ni kilométrage valables pour tous
        les véhicules.
      source_ids: [oem:bremboparts_remplacement_kit, oem:delphi_temoins_usure]
      truth_level: sourced
    replacement_guidance:
      content_md: >-
        Composants de sécurité, les plaquettes ne doivent être remplacées que par un personnel
        compétent. Elles se remplacent par essieu, et à chaque remplacement des disques. Le matériau de
        friction se monte tourné vers le disque ; il ne doit pas toucher de graisse. Les témoins
        d'usure, conçus pour rompre, se remplacent avec les plaquettes.
      source_ids: [oem:bremboparts_remplacement_kit, oem:delphi_temoins_usure]
      truth_level: sourced
    faq:
      content_md: >-
        Quand remplacer les plaquettes ? À la limite d'usure, quand le témoin d'usure s'allume, ou en
        cas d'usure différenciée, de fissures ou de profondes rayures. Faut-il changer les deux côtés ?
        Oui, les plaquettes se remplacent par essieu. Faut-il changer le témoin d'usure ? Oui, il est
        conçu pour rompre et se remplace avec les plaquettes.
      source_ids: [oem:bremboparts_remplacement_kit, oem:delphi_temoins_usure]
      truth_level: sourced
---

## Définition

La plaquette de frein est l'élément de friction du frein à disque : l'étrier la presse contre le disque pour ralentir ou arrêter le véhicule. Elle associe une plaque arrière et un matériau de friction, monté tourné vers le disque.

Les plaquettes sont des composants de sécurité du système de freinage.

## Rôle technique

Dans l'étrier, la pression hydraulique venue du maître-cylindre agit sur les pistons, qui poussent les plaquettes contre le disque. L'étrier transforme ainsi l'énergie hydraulique en force mécanique. Les pistons sont faits d'une matière isolante qui limite la chaleur transmise de la plaquette au liquide de frein. Après le freinage, des ressorts ramènent les plaquettes en position de repos et les maintiennent contre leurs pistons.

Deux types d'étriers actionnent les plaquettes :

- **Étrier flottant** — les pistons sont d'un seul côté : ils poussent une plaquette, et l'autre est poussée par le corps de l'étrier, qui glisse sur des guides. C'est le type le plus répandu sur les véhicules d'entrée et de milieu de gamme et sur les utilitaires légers.
- **Étrier fixe** — son corps porte des pistons opposés qui actionnent les plaquettes. On le trouve sur les véhicules sportifs de milieu à haut de gamme.

Une plaquette peut être livrée avec plusieurs accessoires :

- **Shim** — élément d'amortissement fixé sur la plaque arrière de la plaquette.
- **Rainure** — elle permet d'évacuer rapidement l'eau, la saleté et la poussière.
- **Tôle de guidage** — elle maintient la plaquette en position, évite les cliquetis et la ramène en position initiale quand le frein est relâché.
- **Ressort de piston** — il maintient la plaquette en position, côté piston.
- **Indicateur d'usure** — il signale que la plaquette est usée (voir la section suivante).

## Symptômes & diagnostic

> Un symptôme seul ne désigne pas la plaquette de frein. La recherche de la cause relève de l'outil de diagnostic, pas de cette fiche.

**Signal de fin d'usure** — les languettes métalliques des systèmes de freinage plus anciens émettent un son strident en frottant contre le disque, quand les plaquettes ont atteint leur usure maximale. L'indicateur d'usure mécanique émet lui aussi un signal sonore au contact du disque quand les plaquettes sont usées. C'est un signal voulu, qui demande de remplacer les plaquettes.

**Témoin d'usure électronique** — une boucle de fil traversée par un faible courant est mise à nu par l'usure de la plaquette ; au contact du disque, le circuit s'ouvre et le témoin s'allume au tableau de bord. Les témoins à deux niveaux estiment en plus la durée de vie restante de la plaquette.

**Montage incorrect** — une plaquette ou des accessoires mal montés causent dans la plupart des cas des bruits de freinage ou une performance réduite des freins. Une plaquette directionnelle montée du mauvais côté augmente le bruit au freinage et l'usure des plaquettes, et réduit les performances du freinage.

Pour situer un bruit au freinage parmi les signes d'alerte du véhicule, voir [[signs]].

## Critères de choix selon le véhicule

- **Pièce prévue pour le véhicule** — avant le remplacement, s'assurer que la plaquette est adaptée à la marque et au modèle du véhicule. Les prescriptions du constructeur du véhicule priment sur toute autre indication.
- **Matériau de friction** — il existe de nombreux matériaux de friction, adaptés à chaque véhicule et à chaque style de conduite.
- **Type d'indicateur d'usure** — mécanique ou électrique. Le nombre de capteurs et leur position varient selon la conception du système de freinage ; les plus courants sont intégrés au matériau de la plaquette et ne sont pas amovibles, d'autres sont montés sur la plaquette.
- **Par essieu** — les plaquettes se remplacent par essieu, et à chaque remplacement des disques, les plaquettes sont remplacées aussi.
- **Homologation** — en Europe, l'homologation ECE R90 est obligatoire pour commercialiser disques et plaquettes.

## Montage & erreurs fréquentes

Les plaquettes ne doivent être remplacées que par un personnel compétent : un travail mal exécuté risque de rendre le système de freinage totalement inefficace.

- **Sens de montage** — si une flèche figure sur le shim ou la plaque arrière, elle doit coïncider avec le sens de sortie du disque. Sur les plaquettes asymétriques, la flèche est orientée dans le sens de rotation du disque en marche avant.
- **Côté piston** — avec les étriers à griffe et flottants, la plaquette dotée d'une échancrure en quart-de-rond ou d'un ressort de piston riveté se place côté piston. Les indicateurs d'usure équipent normalement deux des quatre plaquettes d'un jeu, côté piston des plaquettes symétriques, car c'est là que l'usure la plus importante est à craindre.
- **Tôles de guidage** — pour beaucoup d'entre elles, la position de montage ne peut pas être déduite de leur forme : il faut se reporter à la documentation correspondante.
- **Étrier flottant** — vérifier le coulissement du corps de l'étrier sur ses tiges de guidage.
- **Graisses** — éviter tout contact de graisse ou de lubrifiant avec les surfaces de freinage du disque et des plaquettes, qui risquerait de rendre le freinage inefficace.
- **Serrage** — respecter le couple de serrage conseillé par le constructeur du véhicule ; cette fiche n'en donne aucune valeur.
- **Après le montage** — actionner la pédale de frein jusqu'à ce que sa course se stabilise, et contrôler le niveau du liquide de frein.
- **Rodage** — les premiers freinages peuvent être moins efficaces. Ne pas freiner avec une force excessive ni de façon continue pour accélérer le rodage, et toujours respecter les instructions de rodage du constructeur du véhicule : un mauvais rodage risque de compromettre l'efficacité du freinage.
- **Nettoyage** — ne pas nettoyer les composants du frein à l'air comprimé ni à la brosse dure : les poussières soulevées peuvent être nocives à l'inhalation.

## Entretien & bonnes pratiques

- **Contrôle** — les plaquettes s'usent : elles doivent être contrôlées à intervalles réguliers. Cette fiche ne donne ni durée ni kilométrage valables pour tous les véhicules.
- **Vitesse d'usure** — le temps qu'une plaquette met à s'user varie beaucoup : il dépend des conditions de la route, du style de conduite, de la vitesse, de la charge du véhicule et du type de plaquettes et de disques.
- **Quand remplacer** — il faut impérativement remplacer les plaquettes quand le matériau de friction atteint sa limite d'usure ou quand le témoin de l'indicateur d'usure s'allume. Elles se remplacent aussi, par essieu, en cas d'usure différenciée, de fissures ou de profondes rayures.
- **Témoins d'usure** — conçus pour rompre, ils se remplacent chaque fois que des plaquettes neuves sont posées. Il est conseillé de les inspecter régulièrement entre deux changements de plaquettes : la chaleur des freins peut endommager leur câblage et leurs clips, et ils peuvent être abîmés lors d'autres interventions, comme la pose de disques neufs.

## Marques & qualité

Les pièces d'origine (première monte) se reconnaissent au logo « OE supplier » qu'elles portent.

Une page d'équipementier de première monte cite plusieurs marques de qualité d'une plaquette : un traitement thermique de surface (scorching) qui élimine les gaz et limite la perte d'efficacité aux températures élevées (fading), un shim antibruit multicouche en caoutchouc, acier et caoutchouc, un matériau de friction qui assure le confort et l'absence de bruit gênant, et des essais sur bancs statiques et dynamiques, puis sur route. La qualité des garnitures fait partie des facteurs décisifs d'une réponse rapide et précise du freinage.

Cette fiche ne classe pas les marques : la page source est la présentation d'un équipementier. Dans tous les cas, la plaquette doit d'abord être celle prévue pour le véhicule.

## FAQ

**Quand faut-il remplacer les plaquettes de frein ?** Quand le matériau de friction atteint sa limite d'usure, quand le témoin de l'indicateur d'usure s'allume, ou en cas d'usure différenciée, de fissures ou de profondes rayures. Elles doivent être contrôlées à intervalles réguliers.

**Faut-il changer les plaquettes des deux côtés ?** Oui. Les plaquettes se remplacent par essieu, et à chaque remplacement des disques.

**Pourquoi une plaquette usée fait-elle un son strident ?** Sur beaucoup de systèmes, c'est le signal de fin d'usure : une languette métallique ou un indicateur d'usure mécanique frotte contre le disque. Un montage incorrect peut aussi causer des bruits de freinage ; la recherche de la cause relève de l'outil de diagnostic.

**Faut-il remplacer le témoin d'usure avec les plaquettes ?** Oui. Les témoins d'usure étant conçus pour rompre, ils se remplacent chaque fois que des plaquettes neuves sont posées.

**Pourquoi le freinage semble-t-il moins efficace juste après le remplacement ?** Lors des premiers freinages, l'efficacité du frein peut être inférieure. Il ne faut pas freiner fort ni de façon continue pour forcer le rodage, et il faut suivre les instructions de rodage du constructeur du véhicule.

## Provenance & qualité

Fiche **révisée le 2026-10-11**. Chaque affirmation repose sur l'une de six pages archivées dans RAW : cinq pages techniques d'équipementiers de freinage (montage des plaquettes, technologie des étriers, pièces d'origine et équivalentes, procédure de remplacement, témoins d'usure) et un article encyclopédique, utilisé seulement en corroboration. Ces six sources attendent l'activation par le propriétaire. Ont été **retirés**, faute de preuve archivée : l'épaisseur minimale chiffrée, la distance de rodage, les causes de bruit par contamination de la garniture, le lien avec un disque voilé, les familles de matériaux de friction et toute hiérarchie de marques. Aucune valeur de couple, de pression, de cote ni de distance n'est publiée : ces valeurs dépendent du véhicule et relèvent de sa documentation. `review_status: proposed`, exports désactivés ; relation diagnostic en confiance moyenne, `reviewed: false`, `diagnostic_safe: false`.
