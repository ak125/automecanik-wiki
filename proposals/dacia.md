---
schema_version: 1.0.0
id: constructeur:dacia
entity_type: constructeur
slug: dacia
title: Dacia
aliases:
- DACIA
- Automobile Dacia
lang: fr
created_at: '2026-04-28'
updated_at: '2026-10-21'
truth_level: L3
source_refs:
- kind: raw
  path: sources/auto-captures/divers/fr-wikipedia-org-wl-dacia-wikipedia-fr-e3d3d4e6.md
  cid: sha256:5c560f87ab0025e803985ebe0e465c01f9dea19c903db4c7cb1c3dcd83eaa41d
  captured_at: '2026-10-10'
  confidence: low
- kind: raw
  path: sources/auto-captures/divers/dacia-fr-wl-dacia-site-constructeur-464e5258.md
  cid: sha256:c67d0c659b36310fa5a5f2f4ae04932316b71e7e96d020977b6623f85122c4c7
  captured_at: '2026-10-10'
  confidence: medium
- kind: external_url
  url: https://fr.wikipedia.org/wiki/Dacia
  captured_at: '2026-10-10'
  confidence: low
- kind: external_url
  url: https://www.dacia.fr
  captured_at: '2026-10-10'
  confidence: medium
- kind: raw
  path: sources/auto-captures/divers/dacia-fr-wl-dacia-histoire-20261021-6e686270.md
  cid: sha256:bab11f800ca9099cbcdb25a14c6d27152a998716c46b134e9b1d698c22a468a9
  captured_at: '2026-10-20'
  confidence: medium
provenance:
  ingested_by: skill:wiki-proposal-writer
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: "Révisée 2026-10-11 : chaque affirmation repose sur l'une des deux pages\n\
  archivées dans RAW (sources/auto-captures/divers/, PR RAW #69) : l'article\nWikipédia\
  \ « Dacia », utilisé en corroboration seulement (plafond low), et la\npage d'accueil\
  \ de dacia.fr capturée le 10 octobre 2026 (site constructeur,\nplafond medium).\
  \ Les deux références external_url désignent les mêmes pages\nque les références\
  \ raw (même document, pas une source indépendante).\n\nAucune des deux n'est une\
  \ source de preuve (manuel ou documentation atelier\ndu constructeur) : toutes les\
  \ entrées du registre de couverture sont en\nmanual_review, et la fiche ne peut\
  \ pas être promue sur ces seules sources.\n\nRetirés faute de preuve archivée :\
  \ l'ancienne référence recycled/rag-knowledge ;\nl'initiative attribuée à Nicolae\
  \ Ceaușescu ; l'origine du nom (province\nantique), absente de la capture ; une\
  \ production de la Dacia 1300 « jusqu'en\n2004 » et son record de longévité (l'article\
  \ donne 1969-2006) ; le prix\nd'entrée de la Logan ; le « millésime 2024 » ; la\
  \ Sandero « la plus vendue en\nEurope aux particuliers depuis 2017 » ; toute la\
  \ section des pièces les plus\ndemandées (intervalles et kilométrages) ; le partage\
  \ de pièces avec Clio,\nModus, Twingo et Micra ; l'identifiant de marque interne\
  \ ; une part de 55 %\ndétenue par Renault, que l'article contredit lui-même (cession\
  \ de 51,005 % du\ncapital, puis acquisition des huit sociétés du groupe). L'alias\
  \ « Dacia Auto »\nn'est attesté par aucune capture : retiré.\n\nNon repris de dacia.fr\
  \ : prix, offres et loyers ; le modèle « STRIKER », cité\nsans description ; les\
  \ mentions « full hybrid », que la mise en page ne permet\npas de rattacher à un\
  \ modèle précis.\n\nL'article se contredit sur l'année de fondation (1966 dans l'encadré\
  \ et\nl'introduction, « fondée en 1968 » dans une section) : la fiche date de 1966\n\
  la création de l'UAP et de 1968 la première voiture, ce qui concilie les deux.\n\
  \nSections alignées sur le gabarit _meta/templates/constructeur.md (Identité,\n\
  Modèles principaux, Spécificités techniques, FAQ), celui qu'appliquent\ncompute-confidence-score.py\
  \ et le contrat d'ingestion ; la version précédente\nsuivait _templates/new-constructeur.md,\
  \ qui propose un autre découpage.\nAucune page véhicule ni constructeur n'existe\
  \ dans wiki/ : aucun lien n'est\nposé, les modèles restent dans entity_data.models\
  \ (liste inchangée, chaque\nmodèle y figurant est attesté par l'article). Tier :\
  \ 3 conservé (runbook\nPhase E) ; l'exemple de _meta/enums.yaml, qui classe Dacia\
  \ en 2, n'est qu'une\nillustration.\n\nLicences : le catalogue indiquait CC-BY-SA-3.0\
  \ (Wikipédia) et\nproprietary_manufacturer (dacia.fr) ; les deux captures portent\
  \ license null\n(license_status unknown). Valeur alignée sur les autres captures\
  \ (revue\ninterne).\n Lot 2 : page historique officielle archivee ; dates de creation,\
  \ rachat et lancement Logan limitees aux annees effectivement indiquees. Truth_level\
  \ L3 conserve, aucune confiance globale ni preuve technique deduite."
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
entity_data:
  name: Dacia
  country: RO
  founded: 1966
  brand_aliases:
  - DACIA
  - Automobile Dacia
  models:
  - dacia-sandero
  - dacia-logan
  - dacia-duster
  - dacia-spring
  - dacia-jogger
  - dacia-lodgy
  - dacia-dokker
  tier: 3
  vlevel: V3
confidence_score: 0.59
content_hash: sha256:b8fd3ca705301efdfadbac779e20029d6daf79d56c8f7ef9bd25a9b66c60538a
---

# Dacia

## Identité

Dacia est un constructeur automobile roumain dont le siège social est situé à Mioveni, en Roumanie.

L’histoire de la marque commence en Roumanie en 1966.

Renault rachète Dacia en 1999.

La marque est positionnée sur des modèles financièrement plus accessibles.

En 2022, les véhicules Dacia étaient commercialisés dans 44 pays, en Europe, au Maghreb, en Turquie, en Israël et au Liban. Ailleurs dans le monde, ils sont rebadgés sous la marque Renault.

En France, Renault est l'importateur de la marque Dacia.

En avril 2022, Dacia a annoncé avoir atteint dix millions de véhicules produits.

## Modèles principaux

Les premières Dacia sont des Renault produites sous licence à Pitești. La Dacia 1100, copie de la Renault 8, voit le jour le 3 août 1968 ; toutes ses pièces sont produites en France et assemblées en Roumanie. La Dacia 1300, identique à la Renault 12 aux logos et enjoliveurs près, est assemblée à partir du 20 août 1969.

Entre 1969 et 2006, 2 278 691 Dacia 1300 et dérivés ont été produites. La 1300 représente plus de 90 % des Dacia produites avant la Logan.

La Logan est lancée en 2004 et arrive en Europe occidentale en 2005. Sa version break, la Logan MCV, produite en 2007, propose jusqu'à sept places.

La Sandero, citadine à cinq portes, sort au Brésil en 2007 et en Europe en 2008. Le SUV Duster est lancé en 2010. En 2012, Dacia présente le Lodgy, son premier monospace, et le Dokker, son premier ludospace. La Spring, disponible depuis l'automne 2021, est le premier véhicule électrique de la marque.

La gamme actuelle décrite par l'article encyclopédique comprend :

- Logan III (depuis 2020), berline tricorps compacte, qui n'est plus distribuée en France depuis la troisième génération ;
- Sandero III (depuis 2020), citadine à cinq portes, déclinée en version Stepway à châssis surélevé ;
- Duster III (depuis 2024), SUV compact à cinq portes ;
- Spring (depuis 2021), citadine électrique ;
- Jogger (depuis 2021), break surélevé à cinq ou sept places ;
- Bigster (depuis 2025), version rallongée du Duster III.

La page d'accueil de dacia.fr présente, le 10 octobre 2026, les modèles Spring, Sandero, Sandero Stepway, Jogger, Duster et Bigster ; la Logan n'y figure pas.

Au 1er mars 2022, les modèles les plus vendus depuis la création de la marque sont la Sandero (2 518 976 exemplaires), la Dacia 1300 et ses dérivés (2 278 691), le Duster (2 032 669) et la Logan avec la Logan MCV (1 944 080).

## Spécificités techniques

La Sandero est dérivée de la Logan, avec laquelle elle partage la plateforme et les motorisations. Le premier Duster (2010) reprend le châssis de la Logan.

Depuis 2020, la Logan III et la Sandero III reposent sur la plateforme de la Renault Clio de cinquième génération. Le Jogger (2021) hérite de cette plateforme et dispose des mêmes motorisations que la Logan et la Sandero.

Le Bigster repose sur le même châssis que le Duster III et dispose des mêmes finitions et moteurs. Le Duster III est disponible en deux ou quatre roues motrices.

La Spring est une Renault City K-ZE rebadgée, assemblée en Chine à l'usine Dongfeng de Shiyan : c'est la première Dacia produite hors des usines roumaines ou marocaines.

Dacia possède quatre usines : Pitești en Roumanie, Tanger et Casablanca au Maroc, et Shiyan en Chine.

Renault a développé une boîte de vitesses pilotée, dénommée Easy-R, qui remplace le pilotage hydraulique contrôlé par l'électronique par des éléments électromécaniques. Dacia la propose en Europe à partir de 2015 ; son nombre de pièces a été réduit d'un quart.

Sur la page d'accueil de dacia.fr du 10 octobre 2026, les versions d'entrée affichées portent les désignations TCe 100 (Sandero), Eco-G 120 (Sandero Stepway, Jogger et Duster) et mild hybrid-G 140 (Bigster) ; la Spring y est présentée comme électrique.

## FAQ

### Quand Dacia a-t-elle été créée ?

L’histoire de la marque commence en Roumanie en 1966. La première voiture de la marque, la Dacia 1100, a vu le jour le 3 août 1968.

### Quel est le lien entre Dacia et Renault ?

Les premières Dacia étaient des Renault produites sous licence (Renault 8, puis Renault 12). Renault rachète Dacia en 1999. En France, Renault est l'importateur de Dacia.

### Où sont fabriquées les Dacia ?

Dacia possède quatre usines : Pitești en Roumanie, Tanger et Casablanca au Maroc, et Shiyan en Chine, où est assemblée la Spring.

### Quelles Dacia partagent leur plateforme avec d'autres modèles ?

La Logan III, la Sandero III et le Jogger reposent sur la plateforme de la Renault Clio de cinquième génération. Le Bigster reprend le châssis du Duster III. La Spring est une Renault City K-ZE rebadgée.
