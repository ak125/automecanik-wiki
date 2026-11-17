# Étalonnage du skill qualification-technique — 2026-11-15

Candidat d'ADR-131 (`proposed`), non câblé. Aucun code de promotion ne lit ces artefacts. Ce rapport
dit, cas par cas, ce que le skill a retrouvé. Le jeu d'étalonnage reprend le point f de la décision
de l'owner du 2026-11-14. ADR-131 D6 ne fixe pas de seuil : les chiffres ci-dessous ne valident rien.

## Conditions d'exécution

|                            |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fraîcheur                  | WIKI `origin/main` = `67e49d821f17a73692ca0eb976791bcb092483ca` ; RAW `origin/main` = `401314c6bb349378dcd9a9b15e773795e5d5d3d3`, lu par `git archive` (le checkout partagé du RAW est sur une branche obsolète) ; contrôle à 2026-11-15T09:19:00Z                                                                                                                                                                                                                                                                                                              |
| Qualification              | `claude-opus-5-5` (famille anthropic), Claude Code CLI 2.1.325, `claude -p` sur stdin seul : `--tools ""`, `--strict-mcp-config`, `--no-session-persistence`, `--setting-sources ""`, `--disable-slash-commands`, `--system-prompt` imposé, mémoire automatique coupée                                                                                                                                                                                                                                                                                          |
| Contestation               | `gpt-5.6-sol` (famille openai), codex-cli 0.144.4, `codex exec` sur stdin seul, le 2026-11-15 vers 13:32Z : `CODEX_HOME` dédié (fichier d'authentification seul), `--ignore-user-config`, `--ignore-rules`, `--ephemeral`, `--sandbox read-only`, outils coupés par `--disable` (commande complète : `_meta/semantic-review.md` §7), `-c web_search=disabled`, `-c skills.bundled.enabled=false`. Entrée : le paquet figé de la qualification 0.2.0 (texte, captures, artefact de qualification désigné par son empreinte), paquets de 7 000 caractères au plus |
| Skill                      | 0.1.0 (sha256 `47abb9b6…c04473`), puis 0.2.0 (sha256 `52a78abd…8c241d`), puis 0.3.0 (sha256 `bbab905f…93bb2b65`). Une révision du skill change la clé : chaque exécution a sa clé et aucune ne remplace une autre                                                                                                                                                                                                                                                                                                                                               |
| Domaine d'autorité (0.3.0) | classe d'éditeur (ADR-131 D9, option I1), calculée par `_scripts/technical_qualification.py`. Le catalogue n'a pas `publisher_class` : l'étalonnage lui applique une classe posée hors du dépôt (sha256 `ca75e3a4…e400fcb7`) : Renault `constructeur` ; Filtron, MAHLE, ZF, Brembo, Delphi `equipementier` ; Wikipedia sans classe                                                                                                                                                                                                                              |
| Plancher de profondeur     | calculé hors du modèle (ADR-131 D4)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Banc                       | outil de session hors dépôt : découpe en paquets de 5 000 caractères au plus, 3 appels parallèles, validation par le schéma, contrôle d'ancrage des passages. Le mandat exclut un script enveloppe : le banc n'est pas déposé                                                                                                                                                                                                                                                                                                                                   |

Le rapprochement entre les artefacts et les jeux de référence est fait à la main par l'agent qui a
exécuté le skill. Il n'a pas de seconde lecture.

## Cas 1 — consignes du filtre à huile retirées le 2026-09-30

Texte : l'extrait de `proposals/filtre-a-huile.md` à `bd29675` que `678c113` (#97) a retiré.
Producteur déclaré : `skill:wiki-proposal-writer`, famille anthropic (`_meta/source-policy.md:74`).
Attendu : aucune des consignes retirées n'est conservée.

| Consigne retirée                                                             | 0.1.0              | 0.2.0              |
| ---------------------------------------------------------------------------- | ------------------ | ------------------ |
| « à chaque vidange »                                                         | preciser           | preciser           |
| by-pass ouvert par un filtre saturé                                          | preciser           | preciser           |
| « ne se nettoie pas, ne se réutilise pas »                                   | preciser + retirer | preciser           |
| filtre vissé : double joint, huiler le joint, serrage d'une fraction de tour | retirer ×3         | retirer ×3         |
| cartouche : joints toriques, tube central, couple du couvercle               | retirer ×3         | retirer ×3         |
| FAQ « Peut-on nettoyer et réutiliser »                                       | preciser + retirer | preciser + retirer |

Part retrouvée : 6 sur 6 dans les deux révisions. Aucune consigne n'est conservée. Le serrage et le
couple sont retirés.

## Cas 2 — les cinq paires de la FAQ R1 du 2026-11-07

Texte : lignes 153 à 157 de la maquette `r1-atelier.html` du PC (sha256 `eb57e4ad…52e939`), hors
WIKI. Les réponses de L155 et L157 sont les formulations que le 11 a proposées le 2026-11-07.
Producteur : inconnu (`producer.provider = unknown`).

| Ligne | Le 11, 2026-11-07 | 0.1.0                                                                               | 0.2.0                       |
| ----- | ----------------- | ----------------------------------------------------------------------------------- | --------------------------- |
| L153  | conserver         | preciser, retirer (« une référence d'origine permet de recouper » : aucune capture) | preciser, preciser, retirer |
| L154  | conserver         | conserver, preciser                                                                 | conserver, preciser         |
| L155  | précision         | preciser                                                                            | preciser                    |
| L156  | conserver         | preciser                                                                            | preciser                    |
| L157  | formulation       | retirer (« Consultez le guide »), preciser                                          | preciser                    |

Les verdicts du skill sont plus stricts que ceux du 11. Le 11 s'appuyait sur S01, P01, la notice
MANN et P02, qui ne sont pas des captures du RAW. Le skill ne retient que les captures citées : un
écart dans ce sens est attendu, et il ne mesure pas une erreur du 11.

## Cas 3 — `wiki/gamme/plaquette-de-frein.md` à `88f9f88`

Jeu de référence : la contre-relecture du 2026-10-21 (1 écart de sécurité, 8 lignes d'écart de
sens, écarts de formulation). 73 segments, tous au plancher `complete` (famille de sécurité).

|                             | 0.1.0                                                                             | 0.2.0                                                                                                                                                              |
| --------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Affirmations                | 108 : 67 conserver, 36 preciser, 4 reformuler, 1 retirer                          | 107 : 54 conserver, 47 preciser, 5 reformuler, 1 retirer                                                                                                           |
| Sécurité — FAQ Q5 (body:52) | **manqué** : conserver, alors que la limite décrit le contrôle professionnel omis | **retrouvé** : preciser ; la limite nomme le mauvais montage et la pression instable à la pédale, comme la référence                                               |
| Sens — 8 lignes             | 7 : la rainure (body:11) reste conservée                                          | 8 : la rainure passe en reformuler                                                                                                                                 |
| Formulation — 12 constats   | 4 : symptôme seul, « électroniques », argument de gamme, disque voilé             | 2 entiers et 2 partiels : « électroniques », argument de gamme ; partiels : symptôme seul et « en principe » (relevés dans `entity_data`, conservés dans le corps) |
| Passages non ancrés         | 0                                                                                 | 3 (body:41, body:48, body:50 : citation de l'indicateur d'usure non retrouvée mot pour mot)                                                                        |

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

Le contestataire a reçu, pour chaque cas, la qualification 0.2.0 et le même texte. Chaque artefact de
contestation désigne la qualification par son empreinte (`contests.artifact_sha256`) et partage sa
clé. Une sonde a précédé l'exécution, avec la commande retenue : aucun skill visible, aucune commande
exécutable (la lecture de `/etc/hostname` échoue faute d'outil), le lancement d'un sous-agent échoue.
Le flux `--json` de la sonde ne contient aucun élément d'exécution de commande.

| Cas                        | Affirmations | `agree` | `contest` | `undecidable`             | Oubliées (`missed`) |
| -------------------------- | ------------ | ------- | --------- | ------------------------- | ------------------- |
| filtre, consignes retirées | 11           | 4       | 0         | 7 (toutes avec `retirer`) | 0                   |
| filtre, cinq paires        | 8            | 7       | 1         | 0                         | 0                   |
| plaquette@88f9f88          | 107          | 95      | 11        | 1                         | 6                   |

Chaque affirmation de la qualification a reçu une position. Aucun passage cité par le contestataire
n'est hors des captures.

### Cas 1 et 2

- Consignes retirées : aucune n'est rendue `conserver`. Les sept `undecidable` portent sur les
  consignes que le 11 retire faute de capture (double joint, huilage, serrage, joints toriques, tube
  central, couple, nettoyage du média) ; le contestataire dit lui aussi qu'aucune capture ne les
  tranche.
- Cinq paires : L154 (body:3, c4, « ne cherchez pas à convertir le montage ») passe de `preciser` à
  `retirer` : les captures justifient un filtre adapté au moteur, pas l'interdiction de convertir.

### Cas 3 — `plaquette-de-frein@88f9f88`

- Q5 (body:52, c103) : `agree` sur `preciser`, pour le motif de la référence (mauvais montage,
  pression instable).
- Constats de formulation que la qualification 0.2.0 avait manqués :
  - **retrouvés par la contestation** (2) : « un symptôme seul ne désigne pas la plaquette » (body:16,
    c54, `undecidable` : aucune capture ne porte cette précaution) ; « ces valeurs dépendent du
    véhicule » (body:54, c106, `contest` vers `reformuler` : la capture publie une distance de rodage
    propre au Kit EV) ;
  - **manqués** (6) : « en principe » dans le corps (body:22, c64, `agree` sur `conserver`) ; « plus
    anciens » et « signal sonore » dans `entity_data` (c5, `agree`) ; garnitures (body:45, c95,
    `agree`) ; disque voilé ; « cinq pages techniques » (body:54, c104, contesté vers `reformuler` pour
    un autre motif : « chaque affirmation repose » trop absolu, procédure intitulée Kit EV ; le
    contestataire tient l'inventaire des six captures pour exact, ce que la référence conteste) ;
  - hors de portée, comme pour la qualification : `educational_advice` sans `source_ids`, slug
    `kit-de-frein-arriere`.
- Contestations hors du jeu de référence, vers un verdict plus strict : relation de diagnostic (c3,
  confiance et `diagnostic_safe` sans capture), durée et kilométrage (c15), type d'indicateur (c26,
  `retirer` : la capture parle du nombre et de la position), ECE R90 (c27), structure de la plaquette
  (c37), composant de sécurité (c38), indicateur d'usure (c53).
- Contestations vers un verdict plus souple : c68 (remplacement par essieu, `preciser` vers
  `conserver`) et c85 (durée d'usure, `reformuler` vers `conserver`). ADR-131 D3 retient le verdict le
  plus strict des deux : elles ne lèvent aucun blocage.
- Six affirmations oubliées par le 11, toutes dans des notes de fiche (`review_notes` et body:54) :
  date de révision, état de la relation de diagnostic, pages et slugs absents, licence, absence de
  valeur publiée.

### Ce que la contestation montre

- Sur les deux couches, 4 constats de formulation sur 12 sont retrouvés en entier (« électroniques »,
  argument de gamme, symptôme seul, « ces valeurs dépendent du véhicule ») et 1 en partie (« en
  principe », relevé dans `entity_data` mais pas dans le corps). « Cinq pages techniques », contesté
  pour un autre motif, reste compté comme manqué, selon la règle appliquée à 0.1.0. Le défaut resté ouvert en 0.2.0 (un `conserver` dont la limite décrit
  un écart) n'est corrigé que sur body:54 c106 ; c5 reste `agree` sur `conserver`.
- Deux contestations (c38, c53) renvoient à un segment absent de leur paquet : le banc découpe la fiche
  et le contestataire ne voit qu'un paquet à la fois. Un contestataire qui reçoit la fiche entière
  comme contexte lèverait ce biais ; c'est une propriété du banc, pas du skill.
- Un modèle par famille et une exécution : la variance n'est pas mesurée.

## Révision 0.3.0 — corroboration par un second domaine

Le skill 0.3.0 applique la règle de corroboration (ADR-131 D9) : en profondeur `complete`, `conserver`
exige une capture de rôle `proof` et un second domaine concordant ; une seule source donne
`preciser`. Les trois cas ont été relancés le 2026-11-15 entre 14:40Z et 14:54Z, même modèle, mêmes
captures, nouvelles clés. Aucun appel n'a échoué ; le contrôle `corroboration_violations` ne relève
rien sur les trois artefacts. Seul le tour 0 de la boucle de reprise est mesuré : aucune capture n'est
ajoutée.

| Cas                        | Affirmations `complete`                         | Déclassées depuis `conserver`         | Score    | Questions de reprise                    |
| -------------------------- | ----------------------------------------------- | ------------------------------------- | -------- | --------------------------------------- |
| filtre, consignes retirées | 12 : 4 `preciser`, 8 `retirer`                  | 0                                     | 0 sur 12 | 12 (8 sans capture, 4 un seul domaine)  |
| filtre, cinq paires        | 8 : 7 `preciser`, 1 `retirer`                   | 2, par le modèle ; 0 par le contrôle  | 0 sur 8  | 8 (7 un seul domaine, 1 sans capture)   |
| plaquette@88f9f88          | 93 : 90 `preciser`, 2 `retirer`, 1 `reformuler` | 40, par le modèle ; 0 par le contrôle | 0 sur 93 | 93 (91 un seul domaine, 2 sans capture) |

Toutes les questions de reprise sont rédigées par le modèle ; aucune n'est un gabarit.

### Part retrouvée

- Cas 1 : 6 sur 6. « à chaque vidange », by-pass et réutilisation en `preciser` ; « ne se nettoie
  pas » en `retirer` ; double joint, huilage et serrage en `retirer` ; joints toriques, tube central
  et couple en `retirer` ; la FAQ en `preciser` et `retirer`. Aucune affirmation ne cite la capture
  Renault.
- Cas 2 : L153 `preciser` et `retirer` (« une référence d'origine permet de recouper ») ; L154 et L155
  deux `preciser` chacune, dont une déclassée depuis `conserver` par le modèle ; L156 et L157
  `preciser`. Les deux `conserver` de L154 en 0.2.0 deviennent `preciser`.
- Cas 3 :
  - sécurité, Q5 (body:52, c90) : **en partie**. `preciser`, mais la limite nomme les essais à vitesse
    réduite et le risque d'un mauvais rodage, pas le mauvais montage ni la pression instable à la
    pédale (body:16 et body:50 en parlent ailleurs). La 0.2.0 la retrouvait en entier ;
  - sens : 8 sur 8 (rainure, argument de gamme, Q3 « plus anciens », Q4 « Oui », type contre nombre
    et position en `retirer`, trois `diagnostic_relations` en `preciser`, épaisseur et distance de
    rodage en `reformuler`) ;
  - formulation : 6 sur 12 en entier (symptôme seul, « en principe », « électroniques », argument de
    gamme, « signal sonore », « ces valeurs dépendent du véhicule ») ; manqués : « plus anciens »
    dans `entity_data`, garnitures, « cinq pages techniques », disque voilé ; hors de portée :
    `educational_advice` sans `source_ids`, `kit-de-frein-arriere`.

### Trois définitions du domaine, recalculées hors du modèle

Même artefact, mêmes passages cités ; seul change le calcul du domaine. « Confirmées » compte les
affirmations au fond `conserver` (verdict ou déclassement) qui auraient une preuve et deux domaines.

| Définition           | Domaines (filtre / plaquette) | Confirmées : cas 1 | cas 2                | cas 3                                                        |
| -------------------- | ----------------------------- | ------------------ | -------------------- | ------------------------------------------------------------ |
| I1, classe d'éditeur | 2 / 1                         | 0                  | 0                    | 0                                                            |
| I2, `source_type`    | 1 / 2                         | 0                  | 0                    | 1, avec Wikipedia pour second domaine                        |
| I3, hôte             | 3 / 4                         | 0                  | 1 (Filtron et MAHLE) | 10 : 9 par deux équipementiers concurrents, 1 avec Wikipedia |

Sous I1, aucune affirmation de ces cas ne peut être confirmée sans nouvelle capture : le cas 1 ne cite
jamais Renault, et la plaquette n'a qu'une classe d'éditeur.

### Ce que la révision 0.3.0 montre

- La règle est appliquée par le modèle lui-même : 42 déclassements, aucun laissé au contrôle.
- Le défaut resté ouvert en 0.2.0 (un `conserver` dont la limite décrit un écart) est **masqué**, pas
  corrigé. Plusieurs affirmations déclassées depuis `conserver` ont une limite qui décrit un écart de
  fond : `entity_data` c4 (« signal sonore »), c21 (« en principe »), c15, c24, et L155 c4 au cas 2.
  Elles finissent en `preciser` faute de second domaine, comme les affirmations exactes et seules.
  Le verdict ne les distingue plus ; seule la limite le fait.
- La Q5 est moins bien retrouvée qu'en 0.2.0. Un modèle et une exécution par révision ne disent pas
  si l'écart tient à la révision ou à la variance.
- La contestation de la 0.3.0 est consignée ci-dessous.

## Contestation de la 0.3.0

Même contestataire, même commande, même isolement que pour la 0.2.0 : `gpt-5.6-sol` (openai), codex-cli 0.144.4, `CODEX_HOME` dédié, outils coupés, paquet figé sur l'entrée standard. Exécution le 2026-11-15 entre 18:16Z et 18:18Z. Chaque artefact désigne la qualification 0.3.0 par son empreinte (`contests.artifact_sha256`) et partage sa clé. Aucun appel n'a échoué. Tous les passages cités sont dans les captures, et chaque affirmation qualifiée a reçu une position.

| Cas                        | Révision contestée | Affirmations | `agree` | `contest`                                              | `undecidable`             | Oubliées (`missed`) |
| -------------------------- | ------------------ | ------------ | ------- | ------------------------------------------------------ | ------------------------- | ------------------- |
| filtre, consignes retirées | 0.2.0              | 11           | 4       | 0                                                      | 7 (toutes avec `retirer`) | 0                   |
| filtre, consignes retirées | 0.3.0              | 12           | 12      | 0                                                      | 0                         | 0                   |
| filtre, cinq paires        | 0.2.0              | 8            | 7       | 1                                                      | 0                         | 0                   |
| filtre, cinq paires        | 0.3.0              | 8            | 4       | 3 : 2 plus strictes, 1 sur la limite                   | 1 (avec `retirer`)        | 1                   |
| plaquette@88f9f88          | 0.2.0              | 107          | 95      | 11                                                     | 1                         | 6                   |
| plaquette@88f9f88          | 0.3.0              | 93           | 78      | 15 : 12 plus souples, 2 plus strictes, 1 sur la limite | 0                         | 6                   |

### Défauts masqués par la 0.3.0

Les cinq affirmations relevées plus haut sont passées de `conserver` à `preciser` alors que leur limite décrit un écart de fond. La contestation les traite ainsi :

- L155 (cinq paires, body:4 c4, même modèle et même année) : **retrouvée**. Position `undecidable`, verdict `retirer` : la dépendance au moteur ne prouve pas la combinaison de critères. C'est le seul cas où le verdict se sépare d'une affirmation exacte et seule.
- `entity_data` c21 (« en principe ») : **retrouvée dans le motif, pas dans le verdict**. Position `agree` sur `preciser`, mais le motif dit que le texte « transforme en règle absolue une priorité formulée « en principe » ». Même chose pour la reprise de cette phrase dans le corps (body:22 c55).
- `entity_data` c24 (ECE R90) : `agree` sur `preciser`. Le motif reprend la limite (pas de texte réglementaire, champ de l'obligation non couvert).
- `entity_data` c4 (« signal sonore ») : **en partie**. `agree` sur `preciser`, avec une portée bornée aux systèmes munis de languettes. Le motif ne dit pas que le texte est à corriger.
- `entity_data` c15 (marques de qualité) : **non retrouvée**. Contestée vers `conserver`, au motif que le texte attribue déjà les critères à une page d'équipementier.

D'autres positions `agree` sur `preciser` décrivent elles aussi une contradiction dans leur motif : le « Oui » sur le remplacement du témoin d'usure (c9, body:51 c89 : contredit par la réutilisation d'un capteur intact admise par Brembo). La contestation voit ces écarts, mais son verdict ne les sépare pas des affirmations exactes et seules. Le défaut reste masqué dans les verdicts des deux familles.

### Autres constats

- Q5 (body:52 c90) : `agree` sur `preciser`. Le motif nomme les essais à vitesse réduite et le rodage, comme la qualification. La partie manquée (mauvais montage, pression instable) n'est pas retrouvée.
- Les 12 contestations plus souples de la plaquette demandent `conserver` pour des affirmations que le 11 a déclassées faute de second domaine. Le contestataire juge chaque affirmation sur son passage ; l'invite de contestation 0.3.0 ne lui rappelle pas la règle de D9 (une seule source donne `preciser`). ADR-131 D3 retient le verdict le plus strict : elles ne lèvent aucun blocage.
- Contestations plus strictes : cinq paires c6 et c7 (`retirer` : les captures ne montrent ni l'équivalence d'une autre marque ni le renvoi à la documentation du fabricant) ; plaquette c30 (plaque arrière et matériau de friction, `retirer`) et c46 (« relève de l'outil de diagnostic », `retirer`, déjà retrouvé par la contestation de la 0.2.0).
- Oubliées par le 11 : une consigne de la FAQ des cinq paires (« Consultez le guide du filtre à huile », `retirer`) ; six dans la plaquette, dont trois dans les notes de body:54 (date de révision, « cinq pages techniques », relation de diagnostic), comme en 0.2.0.
- `checks` (concordance, indépendance) : aucun n'est rendu. La contestation ne les demande que pour une affirmation déclarée sur plusieurs domaines, et aucune des trois qualifications n'en déclare. Ces deux contrôles ne sont pas mis à l'épreuve par cet étalonnage.
- Un modèle par famille et une exécution : la variance n'est pas mesurée.

## Contestation sous le skill 0.3.1 — l'invite rappelle D9

La 0.3.1 ne change que l'invite de contestation : elle cite à l'identique la règle d'ADR-131 D9 (`conserver` en profondeur `complete` exige une preuve et un second domaine concordant ; un seul domaine donne `preciser`). L'invite de qualification ne change pas. Décision transmise le 2026-11-15 (complément n° 4 au mandat S).

### Clé

D1 met l'empreinte du skill dans la clé. La contestation 0.3.1 a donc la clé `30d1ffcf…c004dcd`, et non celle de la qualification qu'elle conteste (`7e9eb85c…b82043a`) : seul `skill_sha256` diffère, les autres entrées de la clé sont identiques. Elle désigne la qualification 0.3.0 par son empreinte (`2e07943f…3b6d620`). Sous D3, une qualification et une contestation de clés différentes ne forment pas une paire de décision : ces artefacts sont une mesure d'étalonnage. Rien n'est remplacé : la contestation 0.3.0 (`a969cdb5…c971177`) reste en place sous sa clé.

### Exécution

Même contestataire, même commande, même isolement : `gpt-5.6-sol` (openai), codex-cli 0.144.4. Le paquet ne porte que les deux segments où se trouvent les 12 affirmations (`fm:entity_data` et `body:6`), avec leur qualification entière, soit 27 affirmations. Il tient en un seul lot. Le paquet est figé avant l'envoi : l'invite envoyée fait 133 605 octets, d'empreinte `3dd039f24687d2fb110801e2114480c569d043c28d30d1ae1e40d860388a1cc0`. Elle se reconstruit depuis le skill à ce commit, `plaquette-de-frein@88f9f88`, les captures adressées par leur `cid` et la qualification `2e07943f…`. Elle n'est pas versionnée ici : sous `_audit/`, un `.json` doit être un artefact, et les autres extensions sont refusées.

- 0.3.1, tirage 1 : 2026-11-15, de 19:43:24Z à 19:44:53Z, artefact `1c50dbb7…a67ae82`.
- Témoin, invite 0.3.0 sur le même paquet, à la citation près (JSON identique, 126 543 octets) : de 19:45:24Z à 19:46:59Z, invite d'empreinte `5c551985…afe176e`, artefact `a8e56670…158e14c` sous la clé 0.3.0.
- 0.3.1, tirage 2, même invite `3dd039f2…` : de 19:47:29Z à 19:49:09Z, artefact `7327e906…f6b0e86`.

Aucun appel n'a échoué. Tous les passages sont ancrés dans les captures. Les 27 affirmations ont chacune une position dans les trois exécutions.

### Les 12 verdicts, avant et après

| Affirmation        | Objet                                           | Qualification 0.3.0 | Contestation 0.3.0, fiche entière | Témoin : invite 0.3.0, deux segments | 0.3.1, tirage 1 | 0.3.1, tirage 2 |
| ------------------ | ----------------------------------------------- | ------------------- | --------------------------------- | ------------------------------------ | --------------- | --------------- |
| fm:entity_data c8  | remplacement par essieu, « Oui »                | `preciser`          | `contest` → `conserver`           | `agree`                              | `agree`         | `agree`         |
| fm:entity_data c10 | pression hydraulique dans l'étrier              | `preciser`          | `contest` → `conserver`           | `agree`                              | `agree`         | `agree`         |
| fm:entity_data c11 | ressorts de rappel                              | `preciser`          | `contest` → `conserver`           | `agree`                              | `agree`         | `agree`         |
| fm:entity_data c12 | contrôle à intervalles réguliers                | `preciser`          | `contest` → `conserver`           | `agree`                              | `agree`         | `agree`         |
| fm:entity_data c13 | facteurs de la vitesse d'usure                  | `preciser`          | `contest` → `conserver`           | `agree`                              | `agree`         | `agree`         |
| fm:entity_data c15 | marques de qualité (défaut masqué)              | `preciser`          | `contest` → `conserver`           | `agree`                              | `agree`         | `agree`         |
| fm:entity_data c17 | par essieu et à chaque remplacement des disques | `preciser`          | `contest` → `conserver`           | `agree`                              | `agree`         | `agree`         |
| fm:entity_data c20 | adaptée à la marque et au modèle                | `preciser`          | `contest` → `conserver`           | `agree`                              | `agree`         | `agree`         |
| fm:entity_data c25 | étrier flottant, pistons d'un seul côté         | `preciser`          | `contest` → `conserver`           | `agree`                              | `agree`         | `agree`         |
| fm:entity_data c26 | étrier flottant, le plus répandu                | `preciser`          | `contest` → `conserver`           | `agree`                              | `agree`         | `agree`         |
| fm:entity_data c27 | étrier fixe                                     | `preciser`          | `contest` → `conserver`           | `agree`                              | `agree`         | `agree`         |
| body:6 c35         | deux types d'étriers                            | `preciser`          | `contest` → `conserver`           | `agree`                              | `agree`         | `agree`         |

### Ce que la 0.3.1 montre

- Les 12 contestations plus souples ne reviennent dans aucun tirage 0.3.1. Mais le témoin donne le même résultat avec l'invite 0.3.0 : sur ces deux segments, le contestataire suit déjà la règle sans la citation. L'écart avec la contestation 0.3.0 vient du paquet (fiche entière, découpée en lots, contre deux segments) ou de la variance. La citation de D9 n'en est pas la cause démontrée.
- Motifs : au tirage 2, 10 motifs sur 12 invoquent la règle (« un seul domaine », « sans second domaine »), contre 5 sur 12 au témoin. Au tirage 1, le champ `statement` recopie le texte de chaque affirmation (27 sur 27) au lieu d'en donner le motif ; au tirage 2 et au témoin, 0 sur 27. Ni l'invite ni le schéma ne disent ce que porte `statement` pour une position.
- Défauts masqués : c15 passe de `contest` → `conserver` à `agree` sur `preciser`, avec un motif qui borne les critères à Brembo. c4, c21 et c24 restent `agree` sur `preciser`, motif inchangé sur le fond aux tirage 2 et témoin, absent au tirage 1. Le défaut reste masqué dans les verdicts.
- Autres affirmations des deux segments : 14 `agree` sur `preciser` partout ; c23 (`retirer`) est `undecidable` avec `retirer` au tirage 1, `agree` ailleurs. Oubliée : « ni durée ni kilométrage valables pour tous les véhicules », relevée `conserver` par la contestation 0.3.0, l'est de nouveau au tirage 2 avec `preciser`, pas au tirage 1 ni au témoin.
- `checks` : aucun n'est rendu, faute d'affirmation déclarée sur deux domaines. La concordance et l'indépendance ne sont toujours pas exercées ; elles le seront sur les cas du mandat AC.
- Deux tirages et un témoin, un modèle : la variance est entrevue, pas mesurée.

## Artefacts

| Cas                        | Révision                                            | Clé                | Fichier (sha256)   |
| -------------------------- | --------------------------------------------------- | ------------------ | ------------------ |
| filtre, consignes retirées | 0.1.0                                               | `968e1db0…41eb762` | `8be18ace…1f1b6a5` |
| filtre, consignes retirées | 0.2.0                                               | `0ec33159…7f24fdc` | `ff3311ed…11d1cd1` |
| filtre, cinq paires        | 0.1.0                                               | `42b11f84…26ac473` | `00775fd8…743e750` |
| filtre, cinq paires        | 0.2.0                                               | `28ffb476…c040718` | `c06d5564…01514d9` |
| plaquette@88f9f88          | 0.1.0                                               | `4261b108…8874cff` | `312a04b5…0371bff` |
| plaquette@88f9f88          | 0.2.0                                               | `410254eb…9537f3d` | `3461d4a6…04a1350` |
| filtre, consignes retirées | contestation de 0.2.0                               | `0ec33159…7f24fdc` | `da3acb46…02cb871` |
| filtre, cinq paires        | contestation de 0.2.0                               | `28ffb476…c040718` | `b32112dd…eb1a2f1` |
| plaquette@88f9f88          | contestation de 0.2.0                               | `410254eb…9537f3d` | `1dfbf385…97ab996` |
| filtre, consignes retirées | 0.3.0                                               | `50855b79…5ba6447` | `58091485…a214cac` |
| filtre, cinq paires        | 0.3.0                                               | `b95b2052…018ade1` | `eaa06224…e0afa98` |
| plaquette@88f9f88          | 0.3.0                                               | `7e9eb85c…b82043a` | `2e07943f…3b6d620` |
| filtre, consignes retirées | contestation de 0.3.0                               | `50855b79…5ba6447` | `a1202eb4…dbf7bce` |
| filtre, cinq paires        | contestation de 0.3.0                               | `b95b2052…018ade1` | `24859dc3…6c732b8` |
| plaquette@88f9f88          | contestation de 0.3.0                               | `7e9eb85c…b82043a` | `a969cdb5…c971177` |
| plaquette@88f9f88          | témoin : invite 0.3.0, deux segments                | `7e9eb85c…b82043a` | `a8e56670…158e14c` |
| plaquette@88f9f88          | contestation de 0.3.0 sous le skill 0.3.1, tirage 1 | `30d1ffcf…c004dcd` | `1c50dbb7…a67ae82` |
| plaquette@88f9f88          | contestation de 0.3.0 sous le skill 0.3.1, tirage 2 | `30d1ffcf…c004dcd` | `7327e906…f6b0e86` |

Les passages cités (`{path, cid, quote}`) suivent le même régime que `_audit/semantic-review/` : ils
recopient des captures RAW dans ce dépôt public.
