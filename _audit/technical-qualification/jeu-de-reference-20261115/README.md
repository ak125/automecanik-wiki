# Jeu de référence du skill qualification-technique (mandat AC, point 3)

Ce dossier fixe, **avant tout passage**, les verdicts attendus du skill
`qualification-technique` 0.3.0 sur des extraits de quatre fiches `wiki/gamme`.
Les captures citées sont des pages de constructeurs et d'équipementiers archivées dans RAW.

## Versions lues

| Élément               | Valeur                                                                                         |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| Fiches (texte relu)   | WIKI `origin/main` `67e49d821f17a73692ca0eb976791bcb092483ca`, lu le 2026-11-15 à 17:52:04 UTC |
| Skill et schéma v2    | tête du mandat S `a29310fc1ce52316eba1482ef3f0ac7647b55b0e` (WIKI #134), en lecture            |
| SKILL.md 0.3.0        | sha256 `bbab905fb5183582c34591fa930aa2de651b4f9f289a82f447c6c74593bb2b65`                      |
| Captures              | RAW `4b4de7180092dd5145f106ed37bbd166b6fd9fb1` (branche du mandat AC, RAW #79, non fusionnée)  |
| Définition du domaine | `publisher_class` (option I1 d'ADR-131), table `domaines-i1.yaml`                              |

## Contenu

- `cases/<gamme>.yaml` : un cas par fiche (filtre-a-huile exclu). Le corps reprend mot pour mot
  les lignes de la fiche à `67e49d8` listées dans `source_lines`, avec leurs titres de section.
  Le frontmatter est réduit à `slug`, `title` et aux captures RAW du cas. Le `cid` de chaque
  capture est le sha256 des octets du fichier : c'est ce que vérifie
  `semantic_review.load_captures`. Ce n'est pas le champ `content_hash` du frontmatter de la capture.
- `expected.yaml` : 20 cibles. Chaque cible donne son segment, la regex qui retrouve
  l'affirmation, le verdict attendu, les verdicts défendables, la corroboration attendue,
  les citations de provenance et la justification. Toutes les citations ont été vérifiées
  par ancrage (`semantic_review._normalize`) dans les octets des captures.
- `domaines-i1.yaml` : classe d'éditeur et type de chaque capture. Voir plus bas.

## Les contradictions que la règle des deux domaines doit trancher

| Contradiction (liste des manques §6)                        | Cibles                                                       |
| ----------------------------------------------------------- | ------------------------------------------------------------ |
| Bruit d'usure des plaquettes : ZF et Delphi contre Dacia    | `PF-bruit-strident`, `PF-faq-strident`                       |
| 30 000 km du filtre à air                                   | `FA-30000`, `FA-faq-30000`                                   |
| Intervalles diesel entre filtre-a-air et filtre-a-carburant | `FA-carburant-60000`, `FC-faq-intervalles`, `FC-fourchettes` |
| 90 % du filtre d'habitacle                                  | `FH-charbon-90`, et `FH-polyphenol-92`                       |
| C09, amorçage après remplacement                            | `FC-amorcage`                                                |
| C10, diagnostic express                                     | `FC-ralenti-bobine`, `FC-acceleration`                       |

Les cas positifs servent de témoin : `PF-securite`, `PF-controle`, `FC-preconisation` en
profondeur complete, `FA-nettoyage-papier` et `FC-retient-eau` en profondeur allegee.

## Domaines d'autorité

La classe d'éditeur n'existe pas dans `_meta/source-catalog.yaml` (constat du mandat S).
La table posée hors dépôt par S a été retrouvée :
`catalog-publisher-class.yaml`, sha256 `ca75e3a459c75217e68c8250fe73a1bec1868b0de55814043323a141e400fcb7`.
C'est le catalogue de `67e49d8` avec un champ `publisher_class` sur huit captures d'éditeur.
Une fois ce champ retiré, elle est identique au catalogue du dépôt (vérifié). Elle couvre trois
captures du jeu : Brembo, Delphi et ZF pour les plaquettes. Les treize autres captures sont
classées ici selon l'option I1, sous une convention de typage notée en tête de
`domaines-i1.yaml`. Cette convention est une hypothèse d'étalonnage : elle se tranche au vault.

Le banc fusionne cette table en mémoire sur le catalogue du dépôt. Aucun catalogue concurrent
n'est créé.

Conséquence assumée : le cas filtre-d-habitacle n'a aucune capture de rôle `proof`. Aucune de
ses affirmations en profondeur complete ne peut rester `conserver`.

## Ordre de production

1. Ce dossier : cas, verdicts attendus, table des domaines (commit avant tout passage).
1. Seconde lecture à l'aveugle par un modèle d'une autre famille, puis arbitrage consigné :
   `seconde-lecture/arbitrage.md` (codex `gpt-5.6-sol`, 17 accords exacts sur 20, aucun verdict
   attendu modifié).
1. Trois passages par cas avec le banc `_scripts/technical_qualification_bench.py`, puis la
   variance : `runs/` (artefacts, `manifest.yaml`, `variance.yaml`) et `variance-20261115.md`.

`SHA256SUMS` couvre les fichiers de ce dossier.

## Format des fichiers

Les cas et les verdicts attendus ont d'abord été déposés en JSON au commit `eb0f8f0`, avant tout
passage. Le test `test_technical_qualification_schema.py` du mandat S tient tout fichier `.json`
de `_audit/technical-qualification/` pour un artefact d'exécution. Ces fichiers sont des entrées,
pas des artefacts : ils sont passés en YAML sans changer une donnée (`yaml.safe_load` du YAML est
égal à `json.loads` du JSON, vérifié pour les cinq fichiers). Empreintes des versions JSON de
`eb0f8f0` :

| Fichier JSON (`eb0f8f0`)        | sha256                                                             |
| ------------------------------- | ------------------------------------------------------------------ |
| `cases/filtre-a-air.json`       | `abe87a8a76672b704c53949c20b96b4312a68f6442c3c3a1edc88d5b7b4e53f4` |
| `cases/filtre-a-carburant.json` | `0ea80a4757ac05a86acf2088a31000083e24f22d5aff25422dee9b09dda1ae10` |
| `cases/filtre-d-habitacle.json` | `cad451c2469e2b8268aa57686067809d0898bd1f365ff17612680495637b135b` |
| `cases/plaquette-de-frein.json` | `a68c06bbe8e908d79a1bedbb7a184216212c72abd98a0cf9e71dbb2ad546a50c` |
| `expected.json`                 | `842474348bd7614182f9052605eff42cbfb3204dfde9499b4b5e05424af021ee` |
