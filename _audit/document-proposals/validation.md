# Capture RAW vers candidat WIKI : résultat vérifié

14 septembre 2026. Base WIKI vérifiée : `01cea8deda48d84b6a2993cd4bdefe8280082c0b` ; lecteur RAW : `3134ea6292078f196180031a511eab6168adbe0b`.

## Scan

Inspection du contrat WIKI courant, du producteur `author_from_raw.py`, du décideur automatique, des schémas et des chemins historiques. L'ancien checkout WIKI `277c2de` était périmé ; ses règles de validation humaine ne décrivent plus `main`. La référence courante a été vérifiée via GitHub depuis le poste local, après des échecs DNS depuis DEV. Le travail a été isolé dans `/home/deploy/worktrees/wiki-document-proposals-20260914`.

## Analyse

Le producteur courant lit des faits déjà structurés dans `sources/web-research/<slug>/`. Il ne savait pas consommer les reçus documentaires de la PR RAW 53. Les anciens convertisseurs RAG et la skill `legacy-recycler` inspectée n'offrent pas ce contrat. Étendre le producteur actuel permet de conserver le même point d'entrée et les sections WIKI existantes.

## Correction proposée et réalisée

Ajout du mode explicite `--document-selection`, d'un adaptateur et d'un schéma de sélection. Lecture par le contrat RAW natif, identité de la fiche d'entrée fixée par empreinte, passages exacts et positions vérifiés, rendu des reformulations fournies dans des blocs `inferred`. L'ancien contenu et les validations de la fiche modèle ne sont pas hérités. L'annexe de preuves fait partie du corps dont l'empreinte est calculée.

Le candidat est écrit exclusivement dans un dossier isolé. Aucun changement du décideur, du catalogue des sources, des propositions existantes, du registre d'entités ou du corpus canonique. Le registre consulté ne référence pas thermostat ; l'identité du candidat reste celle de la proposition thermostat existante, fixée par son empreinte, sans inventer une nouvelle gamme.

## Validation

21 tests ciblés couvrent les passages et leurs bornes Unicode, les modifications d'entrée, doublons, sections inconnues, références de traçabilité, dates, refus RAW, absence d'héritage des validations, schémas, rendu de données HTML, écriture exclusive, répertoires protégés, erreurs CLI et maintien du dispatch historique. La suite WIKI concernée comptait 163 tests verts avant les deux derniers contre-exemples ; les 21 tests ciblés passent sur le candidat final. La CI exécute la suite finale.

L'intégration réelle, hors réseau, réutilise la capture MAHLE du refroidissement moteur. Deux passages du paragraphe sur la régulation thermique alimentent deux reformulations françaises dans le candidat thermostat. Aucune puissance de pompe, promesse de réduction d'émissions, compatibilité véhicule ou procédure de montage n'est ajoutée. Le lecteur RAW et les évaluateurs de promotion ne sont pas simulés pour cet essai. Le schéma natif accepte le candidat.

Le décideur retourne **BLOCKED** avec trois motifs : `SOURCE_DIVERSITY` (un seul type de référence), `SUBSTANCE_SCORE` (0,24 pour un seuil de 0,85) et `TRUTH_LEVEL` (L3). Le score est un calcul interne, pas une probabilité de vérité. Aucun seuil ni type de source n'a été modifié pour obtenir un succès.

## Verdict

`VALIDATED_FOR_SCOPE_ONLY` pour la préparation traçable d'un candidat documentaire. **Le candidat de contenu reste bloqué par le décideur WIKI.** La concordance des passages est vérifiée ; la fidélité des reformulations et la suffisance des preuves ne sont pas démontrées par cet adaptateur.

La dépendance RAW est encore dans la PR 53. La CI WIKI teste le comportement de préparation et ses schémas avec un lecteur substitué ; la preuve DEV séparée exerce le lecteur réel sur les fichiers conservés. Aucun dépôt automatique dans le sas WIKI, aucune promotion ni publication effective n'a été effectué. Les prochaines améliorations doivent apporter les preuves manquantes, puis réévaluer le candidat avec le même décideur.
