# Filtre à huile — candidat éditorial général

## Scan

Périmètre : la proposition `proposals/filtre-a-huile.md`, sa carte de preuves et les passages de sources utilisés. Révision de départ : `01cea8deda48d84b6a2993cd4bdefe8280082c0b`. Aucun autre article, source RAW, catalogue applicatif ou consommateur modifié.

## Analyse et sources

Les informations nécessaires à ce guide sont le rôle du filtre, ses architectures générales, la fonction des clapets et l'orientation vers la documentation applicable pour le choix et l'entretien. Les anciennes affirmations de diagnostic, normes, classement de marques et gestes de montage ne sont pas nécessaires à cette réponse et ne sont pas réutilisées.

| Source et passage consulté le 12 septembre 2026                                                                                                                                           | Affirmations retenues / blocs                                                                                                                                           |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [MANN-FILTER — Oil filters](https://www.mann-filter.com/en/parts/oil-filter.html), « Frictionless functionality », « Find the perfect type », « Spin-on Oil Filter », « Filter Elements » | Rétention des impuretés et protection ; filtre vissé et élément remplaçable. Blocs `function`, `variants`.                                                              |
| [FILTRON — Valves in oil filters](https://filtron.eu/en/insights/filter-guide/spin-on-oil-filter-valves.html), paragraphes anti-drain-back et bypass                                      | Fonctions générales et présence selon conception, sans pression ni application moteur. Bloc `function`.                                                                 |
| RAW `sources/web-research/filtre-a-huile/selection-criteria.md`, **Critère 4 seulement**                                                                                                  | Provenance historique de l'explication anti-retour, recoupée sur FILTRON. SHA-256 du fichier dans `source_refs[].cid`. Les autres paragraphes ne servent pas de preuve. |

Les identifiants `oem:mann_filter_oem_filtre_huile` et `oem:filtron_oem_clapets_filtre_huile` renvoient aux entrées existantes du catalogue de sources ; les URL et passages ci-dessus précisent la sous-source effectivement utilisée. Leur statut canonique reste `to_capture`, la coverage indique `pending_capture`. La consultation en ligne ne constitue pas une activation ni un archivage canonique. Les deux marques appartiennent au même groupe ; elles ne sont pas revendiquées comme preuves indépendantes.

La coverage attribue `high` aux seules affirmations directement appuyées par ces pages fabricant, selon la politique existante `1_high`. Cela ne change pas la confiance globale des `source_refs`, maintenue à `medium`, ni les statuts des sources. Les blocs choix, entretien et FAQ portent `truth_level: editorial` : ils orientent vers catalogue et notices sans certifier une compatibilité ni fixer une procédure ou un intervalle.

## Correction proposée

La proposition et ses blocs structurés racontent maintenant la même chose. `diagnostic_relations` est vide ; le résumé décisionnel ancien et les blocs diagnostic, normes, qualité de marque et montage sont retirés. Cible `KB_Knowledge` seule, intentions guide/achat/entretien. L'identité gamme et ses métadonnées existantes sont conservées. La provenance et le hash du corps sont renseignés.

La version complète précédente reste dans Git. Les données RAW restent intactes. Il ne s'agit ni d'une suppression de connaissances catalogue ni d'une invalidation globale des passages exclus : ils ne sont simplement pas qualifiés ou nécessaires dans ce périmètre. Aucun remplissage pour obtenir une meilleure note.

## Validation

- Schéma frontmatter : PASS.
- Carte de preuves : 4 entrées, schéma / références / sections PASS.
- Cinq contrôles natifs : source, claim, contradiction, risk, confidence PASS.
- Calcul de score : 0,58 ; comparaison au prédécesseur 0,46, verdict `IMPROVED`.
- Décision automatique complète avec RAW : `BLOCKED`, seul motif `SUBSTANCE_SCORE`, seuil 0,85.
- La formule actuelle donne 0,24 pour les sources, 0,24 pour quatre rubriques attendues sur cinq, zéro pour les liens internes absents et 0,10 pour les types de référence RAW/URL. Ces types ne prouvent aucune indépendance éditoriale. La rubrique symptômes ne sera pas remplie artificiellement.
- Le score secondaire d'observation annonce 93/S, mais son manifest est `stale`. Il ne remplace pas la décision et n'est pas utilisé pour autoriser cette fiche.

Le contrôle des sources vérifie des structures et de la provenance disponible ; il ne démontre pas automatiquement la vérité des pages externes. Les passages retenus ont été consultés pour cette rédaction. Le score, même vert, ne constituerait pas une probabilité de vérité.

## Verdict

`VALIDATED_FOR_SCOPE_ONLY` pour la structure et la cohérence du candidat. Promotion automatique bloquée, aucune publication, aucun export. La suite doit qualifier le calcul de pertinence sur plusieurs exemples représentatifs avant tout changement de moteur ; ni abaissement ponctuel du seuil, ni activation du score secondaire sur la foi de ce seul article.

## Coverage manifest

- scope_requested : produire et évaluer un candidat éditorial général filtre à huile.
- scope_actually_scanned : proposition, coverage, passages fabricant et RAW sélectionnés, schémas et validateurs nécessaires.
- files_read_count : 3 documents de contenu du dépôt (proposition, coverage, RAW), 2 pages fabricant ; lectures techniques de gouvernance et de validation ciblées supplémentaires.
- excluded_paths : autres propositions, modifications RAW, catalogue Massdoc, wiki canonique, exports.
- unscanned_zones : corpus RAW exhaustif, bases applicatives, consommateurs.
- corrections_proposed : remplacement de la proposition et de sa coverage dans une branche isolée, intégration en brouillon.
- validation_executed : schéma, coverage stricte, cinq gates, score, comparaison et décision native avec RAW.
- remaining_unknowns : qualification du score pour les contenus éditoriaux généraux ; matérialisation canonique des captures fabricant ; comportement aval sur contenu publié.
- final_status : VALIDATED_FOR_SCOPE_ONLY ; décision de promotion BLOCKED.
