# Étalonnage du skill qualification-technique — 2026-11-15

Candidat d'ADR-131 (`proposed`), non câblé. Aucun code de promotion ne lit ces artefacts. Ce rapport
dit, cas par cas, ce que le skill a retrouvé. Le jeu d'étalonnage reprend le point f de la décision
de l'owner du 2026-11-14. ADR-131 D6 ne fixe pas de seuil : les chiffres ci-dessous ne valident rien.

## Conditions d'exécution

| | |
|---|---|
| Fraîcheur | WIKI `origin/main` = `67e49d821f17a73692ca0eb976791bcb092483ca` ; RAW `origin/main` = `401314c6bb349378dcd9a9b15e773795e5d5d3d3`, lu par `git archive` (le checkout partagé du RAW est sur une branche obsolète) ; contrôle à 2026-11-15T09:19:00Z |
| Qualification | `claude-opus-5-5` (famille anthropic), Claude Code CLI 2.1.325, `claude -p` sur stdin seul : `--tools ""`, `--strict-mcp-config`, `--no-session-persistence`, `--setting-sources ""`, `--disable-slash-commands`, `--system-prompt` imposé, mémoire automatique coupée |
| Contestation | voir § Contestation |
| Skill | 0.1.0 (sha256 `47abb9b6…c04473`), puis 0.2.0 (sha256 `52a78abd…8c241d`). Une révision du skill change la clé : les deux exécutions ont des clés distinctes et aucune ne remplace l'autre |
| Plancher de profondeur | calculé hors du modèle (ADR-131 D4) |
| Banc | outil de session hors dépôt : découpe en paquets de 5 000 caractères au plus, 3 appels parallèles, validation par le schéma, contrôle d'ancrage des passages. Le mandat exclut un script enveloppe : le banc n'est pas déposé |

Le rapprochement entre les artefacts et les jeux de référence est fait à la main par l'agent qui a
exécuté le skill. Il n'a pas de seconde lecture.

## Cas 1 — consignes du filtre à huile retirées le 2026-09-30

Texte : l'extrait de `proposals/filtre-a-huile.md` à `bd29675` que `678c113` (#97) a retiré.
Producteur déclaré : `skill:wiki-proposal-writer`, famille anthropic (`_meta/source-policy.md:74`).
Attendu : aucune des consignes retirées n'est conservée.

| Consigne retirée | 0.1.0 | 0.2.0 |
|---|---|---|
| « à chaque vidange » | preciser | preciser |
| by-pass ouvert par un filtre saturé | preciser | preciser |
| « ne se nettoie pas, ne se réutilise pas » | preciser + retirer | preciser |
| filtre vissé : double joint, huiler le joint, serrage d'une fraction de tour | retirer ×3 | retirer ×3 |
| cartouche : joints toriques, tube central, couple du couvercle | retirer ×3 | retirer ×3 |
| FAQ « Peut-on nettoyer et réutiliser » | preciser + retirer | preciser + retirer |

Part retrouvée : 6 sur 6 dans les deux révisions. Aucune consigne n'est conservée. Le serrage et le
couple sont retirés.

## Cas 2 — les cinq paires de la FAQ R1 du 2026-11-07

Texte : lignes 153 à 157 de la maquette `r1-atelier.html` du PC (sha256 `eb57e4ad…52e939`), hors
WIKI. Les réponses de L155 et L157 sont les formulations que le 11 a proposées le 2026-11-07.
Producteur : inconnu (`producer.provider = unknown`).

| Ligne | Le 11, 2026-11-07 | 0.1.0 | 0.2.0 |
|---|---|---|---|
| L153 | conserver | preciser, retirer (« une référence d'origine permet de recouper » : aucune capture) | preciser, preciser, retirer |
| L154 | conserver | conserver, preciser | conserver, preciser |
| L155 | précision | preciser | preciser |
| L156 | conserver | preciser | preciser |
| L157 | formulation | retirer (« Consultez le guide »), preciser | preciser |

Les verdicts du skill sont plus stricts que ceux du 11. Le 11 s'appuyait sur S01, P01, la notice
MANN et P02, qui ne sont pas des captures du RAW. Le skill ne retient que les captures citées : un
écart dans ce sens est attendu, et il ne mesure pas une erreur du 11.

## Cas 3 — `wiki/gamme/plaquette-de-frein.md` à `88f9f88`

Jeu de référence : la contre-relecture du 2026-10-21 (1 écart de sécurité, 8 lignes d'écart de
sens, écarts de formulation). 73 segments, tous au plancher `complete` (famille de sécurité).

| | 0.1.0 | 0.2.0 |
|---|---|---|
| Affirmations | 108 : 67 conserver, 36 preciser, 4 reformuler, 1 retirer | 107 : 54 conserver, 47 preciser, 5 reformuler, 1 retirer |
| Sécurité — FAQ Q5 (body:52) | **manqué** : conserver, alors que la limite décrit le contrôle professionnel omis | **retrouvé** : preciser ; la limite nomme le mauvais montage et la pression instable à la pédale, comme la référence |
| Sens — 8 lignes | 7 : la rainure (body:11) reste conservée | 8 : la rainure passe en reformuler |
| Formulation — 12 constats | 4 : symptôme seul, « électroniques », argument de gamme, disque voilé | 2 entiers et 2 partiels : « électroniques », argument de gamme ; partiels : symptôme seul et « en principe » (relevés dans `entity_data`, conservés dans le corps) |
| Passages non ancrés | 0 | 3 (body:41, body:48, body:50 : citation de l'indicateur d'usure non retrouvée mot pour mot) |

Lignes de sens retrouvées en 0.2.0 : argument de gamme (body:23, `entity_data`), Q3 « plus anciens »
(body:50), Q4 « Oui » (body:51, body:42, `entity_data`), type contre nombre et position
(`entity_data`), `diagnostic_relations` (trois relations en preciser), épaisseur et distance de
rodage « faute de preuve » (`review_notes`, body:54), rainure (body:11).

Constats de formulation manqués en 0.2.0 : « plus anciens » dans `entity_data` (conservé, l'écart
n'est noté que dans la limite), garnitures (body:45), vocabulaire (« signal sonore » devenu « son
strident »), `educational_advice` sans `source_ids`, « cinq pages techniques » (body:54, conservé
alors que sa limite le dit contredit par body:50), disque voilé, « ces valeurs dépendent du
véhicule », `kit-de-frein-arriere`. Le disque voilé et le symptôme seul dans le corps, retrouvés en
0.1.0, sont perdus en 0.2.0.

Correction de comptage : avant ce rapport, le constat « cinq pages techniques » était compté comme
retrouvé en 0.1.0. La limite de 0.1.0 le signale pour un autre motif (la procédure Kit EV présentée
comme un guide général), pas pour celui de la référence (une page commerciale, trois éditeurs). Il
est compté comme manqué.

## Ce que l'étalonnage montre

- La révision 0.2.0 a corrigé le défaut de méthode que la 0.1.0 a fait apparaître : une omission
  rattachée par une capture conduisait au verdict `conserver`, avec l'omission écrite dans la limite.
  L'écart de sécurité de la Q5 est retrouvé ; c'est le seul que le jeu de référence contienne.
- Le défaut reste ouvert sous une autre forme : un `conserver` dont la limite décrit une
  contradiction (body:54) ou un écart de vocabulaire (`entity_data` c5). La contestation d'une autre
  famille est le mécanisme prévu pour ces cas (ADR-131 D2, D3). Un nouveau durcissement du skill
  passera par une PR WIKI et un nouvel étalonnage.
- Un modèle et deux exécutions ne mesurent pas la variance d'une exécution à l'autre : les pertes
  observées entre 0.1.0 et 0.2.0 (disque voilé, symptôme seul) peuvent tenir à cette variance autant
  qu'à la révision.
- Les écarts de formulation non textuels (`source_ids` absent, slug incohérent entre deux champs)
  sont hors de portée du skill, qui lit le texte publié et les captures.

## Contestation

À compléter : le contestataire de la famille openai (Codex CLI) a atteint sa limite d'usage pendant
la session ; sa contestation sera exécutée dès la fin de cette limite.

## Artefacts

| Cas | Révision | Clé | Fichier (sha256) |
|---|---|---|---|
| filtre, consignes retirées | 0.1.0 | `968e1db0…41eb762` | `8be18ace…1f1b6a5` |
| filtre, consignes retirées | 0.2.0 | `0ec33159…7f24fdc` | `ff3311ed…11d1cd1` |
| filtre, cinq paires | 0.1.0 | `42b11f84…26ac473` | `00775fd8…743e750` |
| filtre, cinq paires | 0.2.0 | `28ffb476…c040718` | `c06d5564…01514d9` |
| plaquette@88f9f88 | 0.1.0 | `4261b108…8874cff` | `312a04b5…0371bff` |
| plaquette@88f9f88 | 0.2.0 | `410254eb…9537f3d` | `3461d4a6…04a1350` |

Les passages cités (`{path, cid, quote}`) suivent le même régime que `_audit/semantic-review/` : ils
recopient des captures RAW dans ce dépôt public.
