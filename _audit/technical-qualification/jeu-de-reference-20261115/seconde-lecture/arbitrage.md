# Seconde lecture à l'aveugle et arbitrage (mandat AC, point 3)

Les verdicts attendus ont été déposés au commit `eb0f8f0`, avant cette lecture et avant tout
passage du skill. Le second relecteur est d'une autre famille de modèles que l'auteur du jeu
(Anthropic). Il n'a rien reçu des verdicts attendus.

## Relecteur et entrées

| Élément          | Valeur                                                                                                                                                                                                                          |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Modèle           | `gpt-5.6-sol`, famille OpenAI                                                                                                                                                                                                   |
| Outil            | `codex exec` de codex-cli 0.144.4, commande du mandat S (`--ignore-user-config --ignore-rules --ephemeral --sandbox read-only`, outils coupés par `--disable`, `-c web_search=disabled`), `CODEX_HOME` propre, invite sur stdin |
| Horodatage       | 2026-11-15, de 18:03:52 à 18:05:41 UTC, un seul appel, 46 031 jetons                                                                                                                                                            |
| Invite           | `consigne.yaml` (champ `text`) + SKILL.md 0.3.0 (sha256 `bbab905f…`) + paquet JSON ; invite complète sha256 `2256f250…64de`                                                                                                     |
| Paquet           | sha256 `89c17950…ba61` : segments et planchers des quatre cas, captures avec éditeur, domaine et rôle, et `cibles.yaml`                                                                                                         |
| Réponse brute    | `reponse-codex-gpt-5.6-sol.yaml`, champ `text` : octets reçus mot pour mot, sha256 `9d32c878…b67`                                                                                                                               |
| Exclus du paquet | `expected`, `defensible`, `expected_corroboration`, `provenance`, `rationale` (vérifié par recherche dans le paquet)                                                                                                            |

La consigne et la réponse sont déposées en YAML : le dépôt refuse l'extension `.txt`. Le
champ `text` de chacun, lu par `yaml.safe_load`, redonne les octets d'origine (sha256 consigné
dans le fichier, vérifié à la conversion).

Le paquet est rebâti par le banc (`technical_qualification_bench.prepare`) sur les cas,
`domaines-i1.yaml` et RAW `4b4de71`. Quatre affirmations sont une proposition dans une phrase
plus longue : leur texte a été pris mot pour mot dans le segment (`cibles.yaml`).

## Résultat

- Accord exact sur 17 cibles sur 20.
- Les 20 verdicts du second relecteur sont dans l'ensemble attendu ou défendable.
- Ses 33 citations sont toutes ancrées mot pour mot dans les captures désignées.

| Cible                 | Attendu   | Second relecteur | Lecture du second relecteur                                                                                          | Arbitrage                                    |
| --------------------- | --------- | ---------------- | -------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| `FA-nettoyage-papier` | conserver | preciser         | Profondeur élevée à complete ; Filtron ne borne pas le constat aux filtres papier ; un domaine.                      | Attendu maintenu ; preciser déjà défendable. |
| `FC-retient-eau`      | conserver | preciser         | L'eau n'est portée que pour le diesel ; injecteurs et pompe ne sont pas nommés ensemble.                             | Attendu maintenu ; preciser déjà défendable. |
| `FC-amorcage`         | preciser  | retirer          | Renault : réamorçage après panne sèche ; Delphi : « quand pré-remplir… et quand ne pas » ; discordance de procédure. | Attendu maintenu ; retirer déjà défendable.  |

Aucun verdict attendu n'est modifié. Les trois écarts portent sur la frontière entre `preciser`
et un verdict voisin, que le jeu avait déjà déclarée défendable.

## Constat pour le point 6

Douze cibles ont un segment au plancher calculé `allegee`. Le second relecteur en a élevé onze
à `complete` avec le motif `escalated` : intervalle d'entretien chiffré en km, procédure
(amorçage, nettoyage) ou relation de diagnostic. Ces contenus échappent au plancher calculé :

- `numeric_exactitude.extract_values` ne connaît pas le km ;
- les motifs `procedure` et `diagnostic_relation` ne se lisent que sous les titres
  « ## Montage », « ## Entretien » et « ## Symptômes ». Les sections « FAQ », « Choix selon
  véhicule », « Compatibilité véhicule » et « Définition » n'en relèvent pas.

La seule cible restée `allegee` chez lui est `FC-retient-eau`, une définition. La règle des deux
domaines ne s'applique donc à ces cibles que si le relecteur élève lui-même la profondeur. Les
passages de qualification du point 4 diront si le relecteur du skill le fait aussi.

Précision sur le jeu : le README et la justification de `FC-preconisation` le rangent en
profondeur complete, mais son plancher calculé est `allegee`. Le verdict attendu `conserver` tient
dans les deux cas : en complete, deux domaines dont un `proof` sont attendus ; en allegee, la
règle des deux domaines ne s'applique pas. Rien n'est modifié dans le jeu.
