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
updated_at: '2026-10-21'
truth_level: L2
source_refs:
- kind: raw
  path: sources/auto-captures/disque-de-frein/aftermarket-zf-com-wl-disque-de-frein-zf-broutement-c38b7a9a.md
  cid: sha256:46ef0642d8ac7f34b2930913a45db75b785acbcbc7b230ce3cbf0150ac81757a
  captured_at: '2026-10-10'
  confidence: high
- kind: raw
  path: sources/auto-captures/disque-de-frein/fr-wikipedia-org-wl-disque-de-frein-wikipedia-fr-88f2cfa4.md
  cid: sha256:7359136cb80c9e21948e7c393fc5a78c960d0a749ff8c08e4c16b92f1a76a296
  captured_at: '2026-10-10'
  confidence: low
- kind: external_url
  url: https://aftermarket.zf.com/us/aftermarket-portal/for-workshops/useful-tips/brakes/brake-judder/
  captured_at: '2026-10-10'
- kind: external_url
  url: https://fr.wikipedia.org/wiki/Frein_%C3%A0_disque
  captured_at: '2026-10-10'
- kind: raw
  path: sources/auto-captures/disque-de-frein/hella-com-wl-hella-disques-20261021-eb410e50.md
  cid: sha256:665683c3441e6f45ae07ef85e393f48277fb5a7981ec94a5495539c55a51f7ca
  captured_at: '2026-10-20'
  confidence: medium
- kind: raw
  path: sources/auto-captures/disque-de-frein/asia-bremboparts-com-wl-brembo-epaisseur-20261021-119a1c97.md
  cid: sha256:04d85d5782f1cf454f0d8e58eddf3b7665f697c83f57639f3a53533c52212c1b
  captured_at: '2026-10-20'
  confidence: medium
provenance:
  ingested_by: skill:wiki-proposal-writer
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: 'Réécrite 2026-10-11 : chaque affirmation repose sur l''une de deux
  pages archivées dans RAW (sources/auto-captures/disque-de-frein/, PR RAW #69) —
  une page d''atelier d''équipementier sur le broutement, rédigée en anglais et reformulée
  en français dans la fiche (la capture RAW reste dans sa langue d''origine), et un
  article d''encyclopédie en français sur le frein à disque, en corroboration seulement
  (confiance plafonnée à low). Les deux références external_url désignent les mêmes
  pages que les références raw (même document, pas une source indépendante). Retirés
  faute de preuve archivée ou par règle de sécurité : noms de marques et d''équipementiers,
  prix, cotes et tolérances chiffrées (variation d''épaisseur, voile, faux-rond, épaisseur
  minimale gravée), températures, fréquences, homologation des disques de rechange,
  couples de serrage, couronne ABS, VIN, revêtements anticorrosion, relation brake_noise_metallic
  et source bosch_fad_2020. Aucune valeur chiffrée n''est publiée. diagnostic_relations[]
  : deux hypothèses (brake_vibration_pedal, brake_noise_grinding), reviewed=false,
  diagnostic_safe=false. Complément 2026-10-21 : deux sources primaires indépendantes
  archivées pour MIN TH et remplacement par paire. Les anciennes entrées manual_review
  ne sont pas levées. Droits des captures unknown.'
no_disputed_claims: true
confidence_score: 0.65
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
diagnostic_relations:
- symptom_slug: brake_vibration_pedal
  system_slug: freinage
  relation_to_part: possible_cause
  part_role: 'hypothèse — broutement : vibrations au volant et pulsation de la pédale
    au freinage ; selon la page d''atelier, la cause principale du broutement à froid
    est la variation d''épaisseur du disque, souvent due à un faux-rond de montage
    (moyeu sale, voilé ou trop graissé)'
  evidence:
    confidence: medium
    source_policy: 1_high
    reviewed: false
    diagnostic_safe: false
  sources:
  - oem_zf_trw_brake_judder
- symptom_slug: brake_noise_grinding
  system_slug: freinage
  relation_to_part: possible_cause
  part_role: hypothèse indirecte — selon la page d'atelier, le broutement au freinage
    est en général accompagné d'un bruit sourd ; la page ne rattache ce bruit au disque
    qu'à travers le broutement (variation d'épaisseur, dépôt de matière, zones durcies)
  evidence:
    confidence: low
    source_policy: 1_high
    reviewed: false
    diagnostic_safe: false
  sources:
  - oem_zf_trw_brake_judder
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
    educational_advice: Remplacer disques et plaquettes par essieu complet ; au montage,
      veiller à un moyeu propre, plan et sans excès de graisse ; en cas de broutement,
      faire rechercher la cause pas à pas plutôt que de changer seulement les disques
      et les plaquettes.
    related_pages:
    - plaquette-de-frein
  decision_brief:
    function_oneliner: 'Le disque de frein, fixé sur le moyeu de la roue, est serré
      par les plaquettes : le frottement crée le couple de freinage et transforme
      l''énergie cinétique du véhicule en chaleur, qui doit être évacuée.'
    selection_criteria_top:
    - Plaquettes et disques se remplacent par essieu complet, pour des raisons de
      sécurité.
    - 'Les tolérances dépendent du véhicule : bien plus faibles sur les suspensions
      modernes à bras multiples.'
    - 'Au montage : moyeu propre, plan et sans excès de graisse.'
    compatibility_summary: 'Choisir le disque à partir du véhicule : les tolérances
      et les effets d''un défaut varient beaucoup d''un type de véhicule à l''autre.'
    source_kind: web_research_oe
    cross_check_status: SOURCED_OE
content_hash: sha256:8b97f26fbe48c3281e9ca7c3f33ecd4ac380c0adeb3e498d355bdc44402f5698
---

## Définition

Le disque de frein est l'élément du frein à disque contre lequel frottent les plaquettes. Dans ce système, le disque, fixé sur le moyeu de la roue, est serré par des plaquettes qui viennent frotter de chaque côté. Les plaquettes sont maintenues dans un étrier (frein fixe) ou une chape (frein coulissant), fixés au véhicule.

Le frein à disque transforme l'énergie cinétique du véhicule en chaleur, qui doit être évacuée le plus rapidement possible.

## Rôle technique

Un ou plusieurs pistons, en général soumis à une pression hydraulique sur les véhicules de tourisme, poussent les plaquettes contre le disque. La force de frottement entre les plaquettes et le disque crée le couple de freinage, mais aussi de la chaleur. Cette chaleur doit être évacuée le plus rapidement possible pour éviter une déformation du disque.

## Fonctionnement

Une chaleur trop élevée, ou mal évacuée, expose le disque à deux défauts :

- **Disque voilé** — le disque se déforme.
- **Disque glacé** — son état de surface est altéré par une chaleur excessive : il prend une couleur légèrement bleutée et le mordant au freinage diminue.

Deux conceptions de disque répondent à des contraintes particulières :

- **Disque ventilé** — il est formé de deux disques légèrement séparés par des entretoises : l'air circule entre eux et refroidit le disque de l'intérieur.
- **Disque perforé** — de petits trous à sa surface rompent le film d'eau qui se forme entre le disque et la plaquette sous la pluie. En contrepartie, la puissance de freinage diminue un peu par temps sec, car la surface de friction est légèrement réduite, et ces disques sont relativement fragiles.

La fonte est de loin le matériau le plus utilisé pour les disques : elle rouille facilement et elle est assez lourde, mais elle est très économique et efficace à l'emploi.

## Symptômes & diagnostic

> Un symptôme seul ne désigne pas le disque de frein : le broutement a souvent plusieurs causes. La recherche de la cause relève de l'outil de diagnostic, pas de cette fiche.

**Broutement au freinage** — le broutement désigne des vibrations de rotation du volant qui apparaissent au freinage, en général accompagnées d'un bruit sourd. Selon leur cause, on distingue le broutement thermique, qui apparaît en décélérant depuis une vitesse élevée, et le broutement à froid, qui peut apparaître à toute vitesse.

**Broutement thermique** — il se manifeste par un bruit sourd, dont l'intensité peut varier pendant la décélération, par des vibrations dans le volant et par une pulsation dans la pédale de frein. Son intensité dépend de la force de freinage exercée sur la pédale. Il se reconnaît en général à des taches disposées en cercle sur les faces de friction du disque. Les pics de température locaux au freinage provoquent un dépôt de matière de la plaquette sur le disque, ou une modification durable de la structure du matériau du disque. La matière déposée part en général lors des freinages normaux. Les zones dont la structure a changé sont plus dures que le reste du disque et ne s'enlèvent que par usinage. Pour écarter tout risque, le mieux est de remplacer le disque.

**Broutement à froid** — il survient lors des freinages normaux et se reconnaît à une pulsation dans la pédale de frein, à des à-coups de couple dans le volant ou à des vibrations des éléments d'essieu et de châssis. À la différence du broutement thermique, il peut survenir presque à chaque freinage, quelle que soit la température. Sa cause principale est la variation d'épaisseur du disque. Des pièces de roulement défectueuses et un balourd des roues peuvent aussi en accentuer l'effet.

**D'où vient la variation d'épaisseur du disque ?**

- Un faux-rond dû à un mauvais montage met la plaquette en contact local avec le disque à chaque tour de roue, même sans freiner : le disque perd de la matière à cet endroit, ce qui finit par provoquer le broutement.
- Des plaquettes ou des pistons légèrement grippés, qui laissent la plaquette frotter en partie sur le disque, sont souvent en cause.
- Autres causes : un montage incorrect (saleté, corrosion, serrage excessif à la clé à chocs), les conditions d'utilisation, le style de conduite et les conditions de circulation.
- De longs trajets sur autoroute avec des freinages très légers peuvent créer une variation d'épaisseur ; sur la plupart des disques, quelques freinages plus appuyés permettent de la résorber.

**Rechercher la cause pas à pas** — le broutement a le plus souvent plusieurs causes, ce qui rend difficile d'en isoler une seule. Il faut donc procéder par étapes :

- déterminer d'abord si le broutement vient de l'essieu avant ou de l'essieu arrière ;
- contrôler ensuite les éléments de freinage, de la pédale au servofrein, au maître-cylindre, aux conduites et aux flexibles de frein, jusqu'aux freins de roue ;
- contrôler aussi l'équilibrage des roues, leur voile, leur faux-rond et l'état de la bande de roulement des pneus ;
- vérifier enfin la géométrie des trains, les suspensions de roue et les éléments de direction, puis les régler ou les réparer si nécessaire.

## Critères de choix selon le véhicule

- **Par essieu complet** — pour des raisons de sécurité, afin d'éviter un freinage inégal, les plaquettes et les disques de frein se remplacent toujours par essieu complet.
- **Des tolérances propres au véhicule** — les suspensions modernes à bras multiples offrent plus de confort et une meilleure dynamique de conduite, mais n'admettent que des tolérances bien plus faibles sur chaque composant : la tolérance de voile latéral y a été réduite de plus de moitié par rapport aux anciens trains avant à triangles. Cette fiche ne donne aucune cote ni tolérance chiffrée : elles dépendent du véhicule.
- **Des véhicules plus exigeants** — les véhicules sont de plus en plus puissants, donc plus rapides, et de plus en plus lourds avec la multiplication des équipements de sécurité et de confort : leurs systèmes de freinage doivent être de plus en plus résistants. Certains véhicules sont plus sujets au broutement en raison de la forte sollicitation de leur système de freinage.
- **Même défaut, effets différents** — les effets d'une variation d'épaisseur du disque varient beaucoup d'un type de véhicule à l'autre, selon la capacité d'amortissement des pièces d'essieu, de direction et de châssis.

## Montage & erreurs fréquentes

- **Moyeu propre et plan** — les surfaces d'appui et les portées doivent être propres et en parfait état. Un réglet posé sur la face d'appui du moyeu permet de la contrôler vite et simplement : si un jour de lumière apparaît, le moyeu doit être remplacé sans attendre. Le disque ne peut être monté sereinement que si la surface du moyeu est plane.
- **Le moyeu peut causer le voile** — le moyeu peut lui aussi être responsable d'un voile excessif du disque ; il se mesure, et en cas d'écart trop important, le moyeu ou le roulement de roue doit être examiné et remplacé si nécessaire.
- **Conséquences d'un moyeu voilé ou sale** — disque voilé, broutement, disque chargé d'un seul côté, répartition inégale de la température, usure accrue des rotules et des roulements de roue, risque de desserrage des boulons de roue.
- **Pas d'excès de graisse** — si, après le remplacement des disques, on applique trop de graisse sur le moyeu nettoyé, le disque ne repose pas bien à plat sur la bride : un léger voile apparaît et s'accentue avec le temps, jusqu'à ce que le conducteur en ressente les symptômes.
- **Contrôle du voile** — le voile du disque se contrôle frein monté, au comparateur, sur plusieurs tours de roue. Placer le disque sur le moyeu, par rapport aux trous de fixation, de façon à obtenir la valeur mesurée la plus faible ; si nécessaire, échanger ou combiner les pièces en cause (moyeu, disque, roulement).
- **Idée reçue** — il est faux qu'un disque doive avoir un léger voile pour que les plaquettes s'en écartent après le freinage.
- **Erreur fréquente** — souvent, seuls les disques et les plaquettes sont remplacés, alors que mesurer les composants, et les remplacer si besoin, permettrait dans une large mesure de localiser et de supprimer le défaut.

## FAQ

**Le volant tremble au freinage : le disque est-il voilé ?** Pas forcément. Le broutement a le plus souvent plusieurs causes : variation d'épaisseur du disque, dépôt de matière ou zones durcies dues à des pics de température au freinage, faux-rond dû au montage, pièces de roulement défectueuses, balourd des roues. Il faut rechercher la cause pas à pas.

**Faut-il changer les deux disques d'un même essieu ?** Oui. Pour des raisons de sécurité, les plaquettes et les disques de frein se remplacent toujours par essieu complet.

**Un disque doit-il avoir un léger voile pour que les plaquettes se dégagent ?** Non. C'est une idée reçue répandue, mais fausse.

**Changer disques et plaquettes suffit-il à supprimer le broutement ?** Pas toujours. Souvent, seuls les disques et les plaquettes sont remplacés, alors que mesurer les composants, et les remplacer si besoin, permettrait de localiser et de supprimer le défaut.

**À quoi sert un disque perforé ?** Ses petits trous rompent le film d'eau qui se forme entre le disque et la plaquette sous la pluie. En contrepartie, il freine un peu moins par temps sec et il est relativement fragile.

## Entretien et limite d’usure

Le disque s’use lui aussi : l’usure des plaquettes ne suffit donc pas à évaluer l’état du freinage. La documentation technique précise que l’amincissement du disque réduit sa résistance mécanique et sa capacité à dissiper la chaleur.

La mesure s’effectue en plusieurs points de la piste ; la plus faible épaisseur mesurée est comparée à la limite MIN TH indiquée sur le disque. Si elle est inférieure à cette limite, le disque doit être remplacé. Cette règle est décrite par deux équipementiers indépendants ; aucune valeur universelle en millimètres n’est déduite.

Les deux documents demandent le remplacement des disques par paire sur le même essieu. Le guide de réparation réserve les interventions à un personnel qualifié, avec les consignes de sécurité et de maintenance du constructeur et les instructions propres au produit.

## Provenance & qualité

Fiche **réécrite le 2026-10-11**. Chaque affirmation repose sur l'une de deux pages archivées dans RAW : une page d'atelier d'un équipementier consacrée au broutement, rédigée en anglais et reformulée ici en français, et un article d'encyclopédie en ligne sur le frein à disque, qui ne sert que de corroboration (confiance faible). Ont été **retirés**, faute de preuve archivée ou par règle de sécurité : les noms de marques et d'équipementiers, les prix, les cotes et tolérances chiffrées (variation d'épaisseur, voile, faux-rond, épaisseur minimale gravée), les températures et fréquences, l'homologation des disques de rechange, les couples de serrage, la compatibilité couronne ABS et VIN, les revêtements anticorrosion, et la relation `brake_noise_metallic`. Aucune valeur chiffrée n'est publiée. `review_status: proposed`, exports désactivés ; relations diagnostic à l'état d'hypothèses, `reviewed: false`, `diagnostic_safe: false`.

Complément du 2026-10-21 : trois passages d’entretien ajoutés à partir des deux nouvelles captures de documentation technique. Les réserves et contrôles des passages historiques restent applicables.
