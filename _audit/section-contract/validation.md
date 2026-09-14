# Contrat de rubriques — validation du 14 septembre 2026

## Scan

Lecture ciblée des titres de l'auteur documentaire, du score, du modèle gamme, de la politique éditoriale et des contrôles associés. Comparaison arithmétique de 24 fiches ; elle ne constitue pas une validation de leurs faits.

## Analysis

Le score ne reconnaissait pas plusieurs titres réellement produits. Une correspondance par sous-chaîne comptait aussi « Fonction » implicitement ; les commentaires et blocs de code pouvaient être comptabilisés comme des rubriques remplies. Les contre-preuves avant/après sont dans `comparison.json`.

## Correction proposée et réalisée dans le périmètre autorisé

Poursuite demandée par l'utilisateur : titres partagés dans `editorial_sections.py`, alias exacts et exclusifs par critère, parsing CommonMark en lecture seule. « Rôle technique » vaut uniquement pour « Fonctionnement ». L'ancien « Fonction » est préservé explicitement, après vérification de son usage dans le corpus.

Les cinq critères et leurs poids restent inchangés. Les autres rôles éditoriaux n'ajoutent pas de points. Le décideur reste unique. Le contrat et les dépendances participent à son empreinte ; les changements invalident les décisions antérieures. Versions du parseur et de sa dépendance fixées pour les tests, la CI et les hooks concernés.

## Validation

- Chaîne ciblée auteur, schéma, score, pipeline, décision/promotion : 225 tests réussis avant le dernier cas de titre HTML.
- Après le dernier durcissement, les 58 tests de structure et d'explication passent ; la CI couvre la chaîne finale complète.
- Détection d'une décision périmée après modification du contrat ou du fichier de dépendances.
- 24 fiches comparées : 18 scores inchangés, 6 augmentations expliquées par les alias, aucune baisse ni franchissement à la hausse du seuil 0,85. Aucun fichier de fiche réécrit.
- Exemples adverses : commentaire et code produisaient chacun 0,06 point structurel, désormais 0. « Rôle technique » passe de 0 à 0,06 ; jamais deux critères.
- Les candidats documentaires 1.0.0 et 1.1.0 conservés sont reproduits à l'octet près par l'auteur.
- Décideur réel sur le candidat MAHLE : `BLOCKED`, score 0,30, niveau L3, un type de référence. Candidat et modèle inchangés.

## Verdict et limites

`VALIDATED_FOR_SCOPE_ONLY` sur la reconnaissance structurelle et la fraîcheur des décisions. `PARTIAL_COVERAGE` pour la chaîne complète. Les alias ne prouvent ni complétude ni fidélité factuelle ; aucune indépendance des sources n'est établie. Le comptage des liens reste historique. Aucun nouveau contenu RAW acquis, aucune promotion et aucun déploiement.

La CI du commit final est à consulter séparément ; les preuves historiques ne sont pas attribuées au nouveau HEAD.
