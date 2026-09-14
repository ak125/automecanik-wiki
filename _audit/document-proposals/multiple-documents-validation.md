# Plusieurs documents RAW : résultat vérifiable du 14 septembre 2026

## Scan

Périmètre : adaptateur documentaire de WIKI PR 87, sélection JSON, tests, décideur canonique et formule de score. Les captures supplémentaires utilisent RAW PR 53 (`3134ea6`) en copie isolée sur DEV. Le corpus canonique et les environnements déployés sont exclus. Le détail figure dans `multiple-documents-coverage.json`.

## Analyse

Une seule capture par candidat empêchait de relier une affirmation à plusieurs documents. Le nouveau format résout cette limite de traçabilité. Il ne mesure pas automatiquement l'indépendance des sources ni la fidélité d'une reformulation.

Les deux captures supplémentaires ont été refusées par `submission_secret_scan_refused` avant conservation : HELLA thermostat et MAHLE guide thermostat. Ce refus ne démontre pas que les pages exposent de vrais secrets. Les résultats conservés ne contiennent aucune valeur détectée. Une première tentative avait échoué avant le réseau parce que le dossier isolé n'était pas initialisé comme dépôt Git ; le harnais a été corrigé, sans modification du moteur RAW.

L'obstacle WIKI n'est pas uniquement documentaire : le contrôle `SOURCE_DIVERSITY` compte les types de références. Deux captures RAW indépendantes restent un seul type. Le score historique attend aussi des titres partiellement différents de ceux du producteur éditorial.

## Correction proposée et appliquée

Sous l'instruction utilisateur de continuer et améliorer : ajout du format 1.1.0 dans l'adaptateur existant. Chaque affirmation lie un ou plusieurs passages à des reçus RAW épinglés par SHA-256. Références par rubrique, annexe liée au hash du candidat, refus des alias, textes identiques et documents inutilisés. Conservation du format 1.0.0, sans changement des seuils, des niveaux de vérité ou des droits d'export.

## Validation

- 39 tests ciblés verts, dont 18 nouveaux : plusieurs documents et passages, rattachement exact aux rubriques, refus atomique d'une seconde preuve invalide, sélection ambiguë ou auto-déclarée fiable.
- Témoin MAHLE : sortie 1.0.0 strictement identique à l'artefact précédent ; nouveau candidat 1.1.0 lu par le lecteur RAW réel, conforme au schéma WIKI, puis évalué par le décideur canonique réel.
- Nouveau candidat : un document réel, deux affirmations, deux passages. SHA-256 `a43d3f4863c37aec3f70fa668d8cb11b3d26f24e19ae2d059fa1f23c9fa0ed04`. Statut `BLOCKED`, score 0,24, niveau L3, un type de référence. Aucune indépendance nouvelle revendiquée.
- Formule reproduite sur des données synthétiques isolées : toutes les rubriques et liens attendus donnent 0,74 avec RAW et confiance par défaut ; 0,90 avec RAW et confiance déclarée haute ; 0,84 avec deux types et confiance par défaut. Même un score élevé ne supprime pas le contrôle de diversité. Ces entrées ne sont pas des fiches proposées au WIKI.
- Le fichier canonique de proposition thermostat est inchangé. Aucune promotion exécutée.

## Verdict

`VALIDATED_FOR_SCOPE_ONLY` pour l'adaptateur et les refus ciblés. `PARTIAL_COVERAGE` pour le parcours documentaire complet : pas de deuxième capture réelle acceptée, pas de validation sémantique ni d'indépendance, pas d'intégration au sas ou de publication.

Prochaine action : traiter les motifs du scan des nouvelles sources par une qualification précise, sans exclusion globale ; puis aligner les critères WIKI sur les preuves par affirmation et les rubriques canoniques. Ce travail doit préserver le refus en cas de preuve absente ou indéterminable.
