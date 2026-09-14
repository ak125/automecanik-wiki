# Comprendre le score d'une proposition documentaire

Le score historique peut être expliqué sans modifier la proposition :

```bash
python3 -B _scripts/compute-confidence-score.py --explain /chemin/du/candidat.md
```

`--all` sélectionne les fiches habituelles du dépôt. La sortie JSON indique le score calculé, l'état du score déclaré et les quatre contributions : confiance des références, rubriques, liens internes et diversité des types de référence. Les rubriques attendues, détectées et non comptabilisées sont exposées. Les trois modes `--check`, `--fix` et `--explain` sont mutuellement exclusifs.

`--explain` est une lecture de la formule, pas une décision de promotion. Son code de sortie est nul si le calcul a pu être expliqué ; un score déclaré absent, invalide ou différent reste décrit comme tel. Utiliser `--check` pour contrôler cette valeur et `promotion_decision.py` pour la décision complète. Une entrée illisible ou malformée produit un code non nul et un diagnostic sans contenu du fichier.

Le calcul et l'explication partagent la même implémentation. Les poids, la formule, les rubriques requises et les seuils restent ceux du moteur historique. Les valeurs non finies et les booléens sont refusés par `--check`. La réparation d'une valeur déclarée reste réservée au mode explicite `--fix`.

## Lecture du candidat thermostat conservé

Sur le candidat isolé MAHLE, SHA-256 `a43d3f4863c37aec3f70fa668d8cb11b3d26f24e19ae2d059fa1f23c9fa0ed04` :

| Contribution             | Résultat mesuré                         | Points |
| ------------------------ | --------------------------------------- | ------ |
| Confiance des références | Moyenne par défaut : 0,6                | 0,24   |
| Rubriques historiques    | Aucune des cinq rubriques comptabilisée | 0      |
| Liens internes           | Aucun lien interne détecté              | 0      |
| Diversité des types      | Un seul type : RAW                      | 0      |
| Score calculé            | Formule historique                      | 0,24   |

Le texte contient « Rôle technique ». Le score attend « Définition », « Fonctionnement », « Symptômes d'usure », « Choix selon véhicule » et « FAQ ». Un zéro dans cette composante ne signifie donc pas que le candidat est vide. Les trois références du candidat ne sont pas trois documents indépendants : elles proviennent d'une seule capture conservée.

Le décideur réel, réexécuté après ce changement, maintient `BLOCKED` : `SOURCE_DIVERSITY`, `SUBSTANCE_SCORE` (0,24 pour un seuil de 0,85), `TRUTH_LEVEL` (L3). Ni le candidat isolé ni sa proposition de référence n'ont été modifiés.

## Limites de l'explication

Le matcher historique de rubriques reste une heuristique de titres et de longueur. Il ne prouve ni présence de faits, ni validité du Markdown, ni fidélité à la source. Les titres de l'auteur documentaire, du modèle gamme et du score divergent ; aucune équivalence sémantique n'est inventée ici.

La diversité mesure les `kind` des références, pas l'indépendance de leurs éditeurs. Ajouter des alias de références, des rubriques vides, des liens artificiels ou déclarer une confiance supérieure ne constitue pas une correction des preuves.

Le défaut `NaN` reproduit concernait le contrôle de la valeur déclarée ; il ne démontre pas une promotion indue, puisque le décideur recalcule le score. La CI historique traite encore le contrôle global du score en mode tolérant : les tests de ce lot sont bloquants dans la suite pytest, mais cette modification n'active pas une nouvelle politique globale.

Validation et couverture : `_audit/score-explanation/validation.md` et `coverage.json`.
