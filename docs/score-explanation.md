# Comprendre le score d'une proposition documentaire

Le score historique peut être expliqué sans modifier la proposition :

```bash
python3 -B _scripts/compute-confidence-score.py --explain /chemin/du/candidat.md
```

`--all` sélectionne les fiches habituelles du dépôt. La sortie JSON indique le score calculé, l'état du score déclaré et les quatre contributions : confiance des références, rubriques, liens internes et diversité des types de référence. Les rubriques attendues, détectées et non comptabilisées sont exposées. Les trois modes `--check`, `--fix` et `--explain` sont mutuellement exclusifs.

`--explain` est une lecture de la formule, pas une décision de promotion. Son code de sortie est nul si le calcul a pu être expliqué ; un score déclaré absent, invalide ou différent reste décrit comme tel. Utiliser `--check` pour contrôler cette valeur et `promotion_decision.py` pour la décision complète. Une entrée illisible ou malformée produit un code non nul et un diagnostic sans contenu du fichier.

Le calcul et l'explication partagent la même implémentation. Les poids, les cinq critères gamme et les seuils restent ceux du moteur historique. Leurs correspondances de titres sont maintenant explicites et la structure est lue par un parseur Markdown. Les valeurs non finies et les booléens sont refusés par `--check`. La réparation d'une valeur déclarée reste réservée au mode explicite `--fix`.

## Lecture du candidat thermostat conservé

Sur le candidat isolé MAHLE, SHA-256 `a43d3f4863c37aec3f70fa668d8cb11b3d26f24e19ae2d059fa1f23c9fa0ed04` :

| Contribution             | Résultat mesuré                                      | Points |
| ------------------------ | ---------------------------------------------------- | ------ |
| Confiance des références | Moyenne par défaut : 0,6                             | 0,24   |
| Rubriques reconnues      | Fonctionnement via « Rôle technique » : une sur cinq | 0,06   |
| Liens internes           | Aucun lien interne détecté                           | 0      |
| Diversité des types      | Un seul type : RAW                                   | 0      |
| Score calculé            | Formule historique, titres alignés                   | 0,30   |

Le texte contient « Rôle technique », désormais reconnu uniquement comme « Fonctionnement ». Il ne remplit pas aussi « Définition ». Le score était de 0,24 avant cet alignement ; l'ajout de 0,06 mesure la structure reconnue, sans apporter de nouveau fait ni de source. Les trois références du candidat proviennent d'une seule capture conservée.

Le décideur réel maintient `BLOCKED` : `SOURCE_DIVERSITY`, `SUBSTANCE_SCORE` (0,30 pour un seuil de 0,85), `TRUTH_LEVEL` (L3). Les six scores déclarés du corpus devenus obsolètes ont été recalculés avec `--fix`, sans changer les textes, sources, statuts ou exports.

L'ancienne sélection documentaire est correctement refusée après ce changement d'empreinte du modèle. Une nouvelle sélection isolée référence le modèle vérifié ; son candidat porte l'empreinte `cb846d8c5bc418e4a00823aafa53e98cd16e98ddce6f11494a2fad0debcbbcd2`. Sa prose et ses autres métadonnées restent identiques ; son annexe de preuve et son hash sont renouvelés. La nouvelle décision réelle reste `BLOCKED` à 0,30.

## Limites de l'explication

Le contrat `editorial_sections.py` partage les titres de l'auteur et les correspondances du score. Les alias sont fermés et propres aux gammes : « Rôle technique » et l'ancien « Fonction » vers « Fonctionnement » ; « Symptômes & diagnostic » et le titre système du modèle gamme vers le critère historique « Symptômes d'usure » ; « Critères de choix selon le véhicule » vers « Choix selon véhicule ». Ces regroupements sont structurels : ils ne certifient pas la nature ni l'exactitude des faits. Les rubriques optionnelles ne créent pas de points supplémentaires.

Le parseur reconnaît les vrais H2 de premier niveau et leur prose, avec au moins 20 caractères hors espaces. Un alias et son titre historique ne comptent qu'une fois. Les commentaires, blocs de code, titres seuls, images seules et HTML ne remplissent pas une rubrique. Les H3 restent des sous-titres ; leur prose peut contribuer, leur titre seul ne suffit pas. Les versions de dépendances sont imposées ; une version non prise en charge bloque le calcul.

Installer le runtime avec `python3 -m pip install -r _scripts/requirements-scoring.txt`. Le parseur déjà utilisé par l'outillage de formatage est déclaré directement, avec sa dépendance, pour les tests et hooks concernés. Le code du contrat et le fichier de dépendances participent à l'empreinte du décideur : une décision antérieure devient périmée s'ils changent. Source technique : [API de parsing markdown-it-py](https://markdown-it-py.readthedocs.io/en/latest/using.html).

Ce contrôle de structure ne prouve ni présence de faits utiles ni fidélité à la source. Les autres titres hors contrat restent non reconnus. Le comptage historique des liens internes n'est pas modernisé par ce lot.

La diversité mesure les `kind` des références, pas l'indépendance de leurs éditeurs. Ajouter des alias de références, des rubriques vides, des liens artificiels ou déclarer une confiance supérieure ne constitue pas une correction des preuves.

Le défaut `NaN` reproduit concernait le contrôle de la valeur déclarée ; il ne démontre pas une promotion indue, puisque le décideur recalcule le score. La CI historique traite encore le contrôle global du score en mode tolérant : les tests de ce lot sont bloquants dans la suite pytest, mais cette modification n'active pas une nouvelle politique globale.

Validation du diagnostic initial : `_audit/score-explanation/`. Alignement des rubriques et comparaison du corpus : `_audit/section-contract/`.
