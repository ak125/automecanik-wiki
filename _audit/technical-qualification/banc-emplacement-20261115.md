# Banc d'étalonnage du skill qualification-technique : emplacement (mandat AC, point 5)

Le banc du 2026-11-15 (mandat S) était un script hors dépôt, `tq_run.py`. Il est repris dans
`_scripts/technical_qualification_bench.py`, avec ses tests hors ligne dans
`_scripts/test_technical_qualification_bench.py`. Le skill lu est la tête du mandat S
`a29310fc1ce52316eba1482ef3f0ac7647b55b0e` (WIKI #134, non fusionnée).

## Deux emplacements comparés

| Critère                  | Sous-commande de `semantic_review_executor.py`                                                                                      | Module `_scripts/technical_qualification_bench.py`                                         |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Protocole                | Celui d'ADR-119 : passes de détection, réfutateurs, vote. Schéma `semantic-review-run`.                                             | Celui du skill : qualification, contestation. Schéma `technical-qualification-run` v2.     |
| Couplage                 | Mêlerait deux protocoles et deux schémas dans un exécutant qu'ADR-119 décrit.                                                       | Réutilise sans les modifier `build_packet`, `ask`, `enforce`, `capture_domains`.           |
| Conflit avec le mandat S | Fichier présent dans le diff de WIKI #134 : une modification ici entrerait en conflit avec une branche que ce mandat lit seulement. | Fichier nouveau, aucun conflit.                                                            |
| Rôle                     | Un exécutant dont la sortie peut alimenter une décision.                                                                            | Un banc de mesure : il n'est branché sur aucune décision (`promotion_decision.py` intact). |
| Tests                    | Aucun test dédié à l'exécutant aujourd'hui.                                                                                         | Dix tests hors ligne avec un relecteur simulé.                                             |

Choix : le module. Aucun enrobage (wrapper) n'est ajouté : le banc appelle directement les
fonctions existantes, et la commande du relecteur reste celle passée en argument.

## Ce que le banc reproduit

- Découpage en paquets : `semantic_review.build_packet`, puis lots de segments consécutifs sous
  `--shard-chars` caractères (5 000 par défaut, valeur du passage du mandat S). Même entrée,
  mêmes lots.
- Plancher de profondeur : SKILL §5, calculé hors du modèle (famille de sécurité, valeur chiffrée
  au sens de `numeric_exactitude.extract_values`, procédure, relation de diagnostic).
- Domaines : `technical_qualification.capture_domains` sur le catalogue du dépôt, auquel
  `--domains` fusionne en mémoire une table de classes d'éditeur. Les empreintes du catalogue et
  de la table sont consignées dans `key_inputs.domain_basis`.
- Appels : `semantic_review_executor.ask`, un processus neuf par lot dans un répertoire vide.
- Règle du skill : `technical_qualification.enforce` sur chaque affirmation, puis
  `retake_questions` et `corroboration_violations`.
- Validation de schéma : Draft 2020-12 contre `_meta/schema/technical-qualification-run.schema.json`
  avant toute écriture.
- Ancrage des citations : chaque passage cité est cherché, normalisé, dans le texte de la capture
  désignée par son chemin et son `cid`. Un passage non ancré est noté, sans être corrigé.
- Écriture : `OUT/<slug>/run-NN/<clé>/<sha256>.json`. Chaque passage a son répertoire, et le
  parent immédiat de l'artefact reste sa clé, comme l'exige le test de dépôt du mandat S. Deux
  passages aux réponses identiques donnent deux artefacts, comptés deux fois par la variance.
  Le script hors dépôt les écrasait l'un par l'autre, ce que le test de variance a montré.

`variance` lit un `expected.json` de jeu de référence et rend, par cible, les verdicts observés,
la part retrouvée, la part défendable et le nombre de verdicts distincts. Aucun seuil (ADR-131 D6).

## Constat relevé au premier paquet

`numeric_exactitude.extract_values` ne reconnaît que des unités de cote, de couple, de pression, de
température, de masse et le pourcentage (mm, µm, cm, Nm, daNm, bar, kPa, °C, kg, %) : pas le km. « 30 000 km » et « 20 000–30 000 km » n'y sont pas des valeurs chiffrées. Les
segments d'intervalle des filtres restent donc au plancher `allegee`, et la règle des deux domaines
ne s'y applique que si le relecteur élève lui-même la profondeur. Le banc suit le skill tel qu'il
est écrit. Le constat est versé au point 6.
