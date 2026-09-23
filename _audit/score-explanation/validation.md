# Validation du diagnostic de score — 14 septembre 2026

## Scan

Lecture ciblée du score, de ses consommateurs, de l'auteur documentaire, du modèle gamme, des règles et des tests. Comparaison automatique des scores sur 24 fiches Markdown du corpus ; ce comptage n'est pas un audit sémantique de ces fiches.

## Analysis

Le score unique masquait les contributions et le décalage de titres. Le contrôle numérique acceptait une valeur YAML `.nan` : une comparaison avec NaN ne déclenchait pas le refus. Contre-preuve réelle avant/après dans `counterproof.json`.

## Correction proposée et réalisée dans le périmètre autorisé

Poursuite demandée par l'utilisateur : ajout de `--explain` JSON en lecture seule dans l'outil existant et refus des valeurs non finies/booléennes. Une seule implémentation du calcul alimente le score et son explication. Aucun changement de seuil, de niveau de vérité, de politique de diversité ou de fiche.

## Validation

- 149 tests ciblés réussis : 20 nouveaux diagnostics et cas numériques, contrat de schéma, auteur documentaire, décideur et promoteur.
- 24 fiches comparées avant/après : aucune variation de score.
- Contre-preuve NaN : acceptée par l'ancien contrôle, refusée par le nouveau.
- Candidat MAHLE réel réévalué par le décideur canonique, sans mocks : `BLOCKED`, score 0,24, mêmes trois motifs. Candidat et proposition de référence inchangés.
- Réseau non utilisé pour ce lot WIKI ; lecture des preuves RAW déjà conservées.
- La CI du nouveau commit doit être contrôlée séparément ; aucune ancienne CI n'est attribuée à ce changement.

## Verdict

`VALIDATED_FOR_SCOPE_ONLY` pour le calcul explicable et le contrôle numérique. `PARTIAL_COVERAGE` pour le parcours documentaire complet. Le matcher de titres reste historique, les deux captures supplémentaires restent refusées et l'indépendance des sources n'est pas validée.
