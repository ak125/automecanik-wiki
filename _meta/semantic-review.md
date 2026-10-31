# Auto-review de sens

> Norme : ADR-119 (vault, acceptée le 2026-10-30), D1 à D3 et D8. Condition `semantic_auto_review_pass` de la Safety Auto-Gate (`_meta/quality-gates.md` §7).
>
> Code : `_scripts/semantic_review.py` (découpage, clé, dépôt, verdict), `_scripts/semantic_review_executor.py` (exécuteur). Schéma : `_meta/schema/semantic-review-run.schema.json`.

______________________________________________________________________

## §1 — Objet et rôles

L'auto-review vérifie que chaque affirmation du texte publié d'une fiche dit ce que disent les captures RAW qu'elle cite, et qu'elle n'omet rien de ce qu'elles rattachent au même sujet. Elle remplace toute relecture humaine, familles de sécurité comprises (ADR-119 D1).

| Rôle                | Composant                       | Fait                                                                                                    | Ne fait jamais                                                                      |
| ------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| module déterministe | `semantic_review.py`            | découpe le texte publié, calcule la clé, produit le paquet, dépose une exécution, recalcule son verdict | appeler un modèle                                                                   |
| exécuteur           | `semantic_review_executor.py`   | lance les passes et les réfutateurs, assemble leurs réponses en une exécution et la dépose              | rendre un verdict, committer, écrire la fiche                                       |
| relecteurs          | modèles appelés par l'exécuteur | relèvent les écarts, puis les réfutent ou les confirment                                                | voir la proposition de travail, le raisonnement du producteur ou un autre relecteur |
| décideur            | `promotion_decision.py`         | lit les exécutions versionnées et calcule la condition                                                  | approuver sur la seule auto-review : la condition est nécessaire, jamais suffisante |

Pour une fiche sécurité, la condition bloque. Pour les autres, elle est calculée et tracée en report-only (`semantic_review.blocking: false` dans la décision) ; la rendre bloquante est un durcissement, par PR WIKI (ADR-119 D3).

______________________________________________________________________

## §2 — Texte relu, segments et clé

- **Texte publié** : le frontmatter de la fiche sans les cachets que la promotion ajoute (`promotion_decision._published_frontmatter`), sérialisé en YAML, puis le corps.
- **Segments** (`segments`, révision `segmenter` du protocole) : `fm:<champ>` pour chaque champ du frontmatter publié, dans l'ordre des clés, puis `body:<n>`, à partir de 1, pour chaque bloc du corps (paragraphe, titre, bloc de code, tableau, liste…). Toute ligne non blanche du corps appartient à un seul segment. Chaque segment porte le sha256 de son texte.
- **Captures citées** : les `source_refs` de kind `raw`, triées et dédoublonnées, chacune épinglée par son `cid` (`sha256:<64 hex>`) sous un chemin relatif sans `..`. Leurs octets sont relus et comparés au `cid`. Une capture sans `cid` ne lie pas la relecture à ses octets : la fiche est en `INVALID_INPUT`.
- **Clé** : sha256 du JSON canonique de `{text_sha256, captures, protocol_revision}`, où `protocol_revision` est le sha256 du JSON canonique de `PROTOCOL`. Un nouveau texte, une capture changée ou une nouvelle révision du protocole font une nouvelle clé ; les exécutions de l'ancienne clé deviennent périmées.
- **Racine RAW** : `--raw-root`, sinon `AUTOMECANIK_RAW_PATH`, sinon `automecanik-raw` à côté du WIKI, comme pour les autres contrôles du décideur.

Lire une capture citée pour contrôler une fiche n'est pas la lecture de RAW par un consommateur qu'interdit ADR-031 : c'est la lecture que fait déjà le contrôle de provenance. Aucun RAG n'entre dans la relecture (ADR-031, ADR-046).

______________________________________________________________________

## §3 — Protocole

| Clé de `PROTOCOL`      | Valeur                                      | Effet                                                                                                                                                                                                                                                                   |
| ---------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `detection_passes_min` | 2                                           | au moins deux passes de détection indépendantes ; chacune couvre tous les segments ; un candidat relevé par une seule passe suffit                                                                                                                                      |
| `refuters_min`         | 3                                           | au moins trois réfutateurs distincts par candidat                                                                                                                                                                                                                       |
| `refutation`           | `unanimous_with_capture_passage`            | un candidat n'est écarté que si tous ses réfutateurs le réfutent, chacun avec un passage retrouvé dans une capture citée                                                                                                                                                |
| `classes`              | `valeur`, `securite`, `sens`, `formulation` | valeur : chiffre, unité, intervalle, quantité ; sécurité : écart qui peut conduire à une action ou à une omission dangereuse ; sens : affirmation contredite, déformée ou sur-généralisée, divergence entre sources non déclarée ; formulation : sans effet sur le sens |
| `blocking_classes`     | `valeur`, `securite`, `sens`                | un écart confirmé de ces classes rend FAIL ; la formulation est consignée sans bloquer                                                                                                                                                                                  |
| `segmenter`            | 1                                           | révision du découpage en segments                                                                                                                                                                                                                                       |

Une omission compte comme une affirmation : la fiche laisse de côté une condition, une précaution ou une cause qu'une capture citée rattache au même sujet. Une affirmation qu'aucune capture citée ne porte est un écart, de la classe que donne sa portée. La connaissance propre d'un modèle peut lever un candidat, jamais l'écarter.

Durcir le protocole (passes ou réfutateurs plus nombreux, classe bloquante ajoutée) se fait par PR WIKI ; l'assouplir exige un ADR (ADR-119 D2). Toute modification de `PROTOCOL` change la clé. L'exécuteur accepte plus de passes ou de réfutateurs que le protocole pour une exécution donnée, jamais moins.

______________________________________________________________________

## §4 — Exécution

Une exécution suit `_meta/schema/semantic-review-run.schema.json` : clé et entrées de la clé, modèles utilisés, segments relus avec leurs affirmations (`affirmation` ou `omission`) ou la mention `no_claims`, passes avec les segments qu'elles couvrent, candidats avec la passe qui les a levés et leurs réfutations (`refuted`, `upheld` ou `undecidable`, avec un passage `{path, cid, quote}` ou `null`). Elle ne porte aucun verdict. Le champ `error` signale une exécution dont une passe ou un réfutateur a échoué.

Elle est déposée sous `_audit/semantic-review/<slug>/<clé>/<sha256 de ses octets>.json` (JSON à clés triées, indentation 2) par `semantic_review.py record` ou par l'exécuteur, après validation du schéma, des références internes (passes, segments, affirmations, modèles) et de la clé contre la fiche courante. Une exécution n'est jamais remplacée : son nom est l'empreinte de son contenu.

______________________________________________________________________

## §5 — Verdict d'une exécution

Le décideur recalcule le verdict ; le relecteur ne déclare ni verdict ni complétude.

- **Candidat écarté** : au moins trois réfutations, toutes `refuted`, chacune avec un passage dont la citation (normalisée NFC, blancs réduits) se trouve dans le texte d'une capture citée, même chemin et même `cid`.
- **Candidat confirmé** : une réfutation `upheld` ou `undecidable`, ou un passage absent ou introuvable dans la capture. Un candidat confirmé sans réfutation `upheld` ancrée est « non tranché » : aucune capture ne le tranche.
- **Candidat en attente** : moins de trois réfutations, toutes `refuted` et ancrées.
- **Relecture incomplète** : segment attendu absent, segment inconnu ou d'empreinte différente, moins de deux passes, passe qui ne couvre pas tous les segments, candidat en attente.

| Verdict      | Condition, dans cet ordre                                                                      |
| ------------ | ---------------------------------------------------------------------------------------------- |
| `FAIL`       | un écart d'une classe bloquante est confirmé, même si la relecture est incomplète ou en erreur |
| `ERROR`      | l'exécution porte `error` : elle se relance                                                    |
| `INCOMPLETE` | la relecture est incomplète : elle se relance                                                  |
| `PASS`       | relecture complète, aucun écart bloquant confirmé                                              |

______________________________________________________________________

## §6 — État de la condition

`semantic_review.review_status` lit toutes les exécutions de la clé courante. La condition n'est vraie que sur `PASS`.

| État          | Signification                                                                                                                                                                                      |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `FAIL`        | une exécution de la clé rend FAIL. Aucun PASS ne la remplace sur la même clé, quel que soit le modèle : seul un nouveau texte, de nouvelles captures ou un nouveau protocole font une nouvelle clé |
| `HISTORY_GAP` | une exécution de la clé a été versionnée puis retirée de l'arbre, ou un fichier de la clé est hors version ou modifié. Supprimer un FAIL ne débloque donc jamais la fiche                          |
| `UNREADABLE`  | un fichier de la clé est hors convention, son nom diffère de l'empreinte de son contenu, ou son JSON, son schéma, ses références ou sa clé sont invalides                                          |
| `PASS`        | une exécution de la clé rend PASS, sans FAIL, trou d'historique ni fichier illisible sur cette clé                                                                                                 |
| `INCOMPLETE`  | aucune exécution de la clé ne rend PASS, au moins une est incomplète : la relecture se relance                                                                                                     |
| `ERROR`       | aucune exécution de la clé ne rend PASS ni INCOMPLETE, au moins une est en erreur : la relecture se relance                                                                                        |
| `STALE`       | seules des exécutions d'une autre clé existent pour le slug                                                                                                                                        |
| `ABSENT`      | aucune exécution pour le slug                                                                                                                                                                      |
| `NO_CAPTURE`  | la fiche ne cite aucune capture RAW : rien ne peut porter ses affirmations                                                                                                                         |

L'état de la fiche suit l'ordre du tableau. Le décideur ajoute trois états qui ne jugent pas le contenu : `UNAVAILABLE` (racine RAW ou capture absente, historique git du WIKI superficiel ou illisible), `INVALID_INPUT` (référence de capture malformée ou non épinglée, octets différents du `cid`, slug invalide) et `EVALUATOR_ERROR`. Le contrôle des trous d'historique exige un clone complet du WIKI : sur un clone superficiel, la condition est `UNAVAILABLE`.

Les fichiers de `_audit/semantic-review/<slug>/` et les captures citées entrent dans le manifeste de la décision : une exécution ajoutée ou retirée après la décision la rend `STALE_DECISION`.

La trace de la décision (`semantic_review`) porte la clé et ses entrées, l'état, l'exécution qui le fixe (`verdict_run`), et pour chaque exécution son verdict, les écarts confirmés par classe, les candidats écartés et en attente, la part des écarts confirmés qu'aucune capture ne tranche (`unsettled_share`) et les modèles (ADR-119 D8).

______________________________________________________________________

## §7 — Usage

```bash
# 1. Relire : chaque passe et chaque réfutateur tourne dans un processus neuf, dans un répertoire
#    vide, avec pour seule entrée son invite et le paquet sur stdin. L'exécution est déposée,
#    FAIL compris, et son évaluation affichée.
python3 _scripts/semantic_review_executor.py wiki/gamme/<slug>.md \
  --command "claude --bare -p --model {model} --tools '' --strict-mcp-config --no-session-persistence" \
  --model <modèle> [--model <autre modèle>] [--jobs 4]

# 2. Versionner l'exécution déposée par PR WIKI, quel que soit son verdict. Non versionnée, elle
#    met la condition en HISTORY_GAP.

# 3. Lire l'état de la condition sur l'arbre versionné (code 0 seulement si PASS).
python3 _scripts/semantic_review.py verdict wiki/gamme/<slug>.md
```

- `--command` est obligatoire et doit contenir `{model}` ; il n'existe ni commande ni modèle par défaut. Les modèles passés par `--model` sont répartis à tour de rôle entre les passes, puis entre les réfutateurs, et consignés dans l'exécution.
- La commande doit donner au relecteur son entrée standard pour seule entrée : aucun outil, aucun serveur MCP, aucune instruction ni mémoire locale, aucune session conservée. Avec le CLI `claude`, `--bare` écarte les instructions et la mémoire locales mais exige une clé d'API. L'étalonnage (ADR-119 D4 e) vérifie la commande retenue et la consigne dans sa PR.
- `--passes` et `--refuters` valent par défaut le minimum du protocole ; une valeur plus basse est refusée. `--timeout` borne chaque appel ; `--jobs` règle le parallélisme.
- Sorties de l'exécuteur : 0 si l'exécution est déposée (verdict affiché, FAIL compris) ; 2 si rien n'est déposé (commande sans `{model}`, protocole assoupli, fiche sans capture, entrée illisible).
- Sans exécuteur : `semantic_review.py packet FICHE` écrit le paquet remis aux relecteurs ; `semantic_review.py record FICHE RUN.json` dépose une exécution assemblée ailleurs, aux mêmes contrôles. Sorties de `semantic_review.py` : 0 succès, 1 état autre que PASS (`verdict`), 2 entrée invalide ou indisponible.

______________________________________________________________________

## §8 — Limites connues

- **Versionnement** : l'exécuteur dépose l'exécution dans l'arbre de travail. Une exécution supprimée avant son premier commit ne laisse aucune trace ; versionnée, elle ne peut plus disparaître sans `HISTORY_GAP`.
- **Pertinence du passage** : le décideur vérifie qu'un passage cité figure dans une capture citée, pas qu'il tranche le candidat. L'unanimité de trois réfutateurs et la confirmation de tout autre vote bornent ce risque.
- **Indépendance** : elle est mécanique (processus et répertoire séparés, aucune sortie partagée). Deux passes du même modèle restent corrélées : plusieurs `--model` la renforcent.
- **Invites et commande** : les invites de l'exécuteur et la commande de lancement n'entrent pas dans la clé ; seuls les modèles sont consignés. Modifier les invites est une modification du code de l'exécuteur, par PR WIKI.
- **Relances** : une exécution `INCOMPLETE` ou `ERROR` se relance sur la même clé ; chaque relance reste visible dans l'historique.
- **`no_disputed_claims`** reste une déclaration du frontmatter. L'auto-review la complète : une divergence non déclarée entre sources est un écart de sens (ADR-119 D3).
