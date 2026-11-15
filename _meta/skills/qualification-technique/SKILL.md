---
name: qualification-technique
description: >-
  Qualification technique (département 11) des affirmations du texte publié d'une fiche WIKI avant
  sa promotion : affirmation, source, portée, limite, verdict, profondeur selon le risque. Une
  seconde invite sert à la contestation par un relecteur d'une autre famille de modèles. Le skill
  dépose un artefact (_meta/schema/technical-qualification-run.schema.json) ; il n'approuve rien.
version: 0.2.0
status: candidate
adr: ADR-131 (proposed)
wired: false
---

# Qualification technique (département 11)

**Statut : candidat, non câblé.** ADR-131 est au statut `proposed`. Aucun code de promotion ne lit
encore cet artefact. Ce fichier décrit la méthode et porte les deux invites ; les modifier change la
clé de toutes les qualifications (`key_inputs.skill_sha256`).

## 1. Place dans le circuit

Captures → RAW → fiche WIKI → **qualification du 11** (et sa contestation) → promotion par le seul
décideur `promotion_decision.py` → projections → pages R1, R3, R4.

- Le 11 qualifie une fois, sur la fiche WIKI, avant la promotion. Les pages R1, R3 et R4 héritent de
  cette qualification. Elles n'en ont pas d'autre.
- Une réponse de FAQ n'atteint une page que si elle est dans la fiche WIKI promue, dans
  `entity_data.editorial.selection_faq.qa` (ADR-107 D2, ADR-111 D3). Elle est qualifiée comme
  segment de cette fiche.
- `.claude/prompts/_shared/editorial-review.md` (monorepo) reste une relecture de forme, côté page.
  Elle ne qualifie pas le fond et n'est pas une source.

## 2. Trois rôles séparés

| Rôle                     | Exécutant                                                                            | Juge                                                                                 | Ne fait jamais                                                         |
| ------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| qualification (11)       | un modèle, invite §7, paquet sur stdin                                               | la justesse technique de chaque affirmation : affirmation, source, portée, limite, verdict | approuver, rédiger la fiche, chercher une source hors du paquet       |
| contestation             | un modèle d'une **autre famille** que le producteur et le 11, invite §8               | la fiche et la qualification du 11, indépendamment                                   | approuver, voir le raisonnement du 11 au-delà de son artefact         |
| relecture de forme       | `editorial-review.md`, côté page                                                     | la forme d'une page                                                                  | qualifier le fond, servir de source                                    |
| décideur                 | `promotion_decision.py`                                                              | les conditions, dont celle-ci une fois câblée                                        | déléguer sa décision à un modèle                                       |

Le nom « 11 » désigne une méthode exécutée et versionnée, pas une personne ni un rôle nouveau.
L'artefact nomme le modèle et la révision du skill ; la compétence se démontre par les passages
cités, pas par le nom du rôle.

## 3. Méthode (11, 2026-11-07)

Texte de la méthode du 11, recopié sans changement :

> Vérifier les affirmations et conditions des réponses techniques, séparément du signal de demande.
> Ne pas généraliser les intervalles, couples, emplacements ou gestes d'un véhicule à tous les
> autres. Décrire les limites et les cas nécessitant une aide professionnelle. Rechercher de
> nouvelles preuves seulement pour les faits manquants ; les sources de questions ne valent pas
> validation des réponses qu'elles contiennent.

Transposition dans le circuit, où la seule preuve admise est une capture RAW citée par la fiche
(ADR-031) :

- chaque affirmation reçoit **affirmation, source, portée, limite, verdict** ;
- une source est un passage recopié à l'identique d'une capture du paquet. La connaissance propre du
  modèle n'est pas une source ;
- un fait manquant ne se cherche pas pendant la qualification. Il donne `retirer` ou `preciser`, et
  la recherche passe par une capture RAW nouvelle, puis par une nouvelle fiche (nouvelle clé) ;
- une question tirée de la demande (PAA, mots-clés) ne valide jamais la réponse qu'elle appelle.

## 4. Verdicts

| Verdict      | Sens                                                                                               |
| ------------ | -------------------------------------------------------------------------------------------------- |
| `conserver`  | une capture porte l'affirmation, dans sa portée, et le texte n'omet rien de ce que cette capture y rattache |
| `preciser`   | le fond est porté, mais la portée, une condition ou une limite manque ou est trop large            |
| `reformuler` | le fond est juste, la forme est fautive ou trompeuse sans changer le sens                           |
| `retirer`    | aucune capture ne porte l'affirmation, une capture la contredit, ou elle peut conduire à un geste dangereux |

**Omission.** Le texte omet une condition, une précaution, une cause ou un cas d'aide
professionnelle qu'une capture citée rattache au même sujet (ADR-119 D2). Une omission n'est pas une
limite de la source : le verdict est au moins `preciser`, et l'omission est décrite dans `limite`.
Un `conserver` dont la `limite` décrit une omission du texte est hors méthode.

`proposed_wording` accompagne `preciser` et `reformuler`. C'est une proposition au rédacteur,
jamais une source ni une écriture dans la fiche.

## 5. Profondeur selon le risque (ADR-131, point d)

Le plancher est déterministe et calculé hors du modèle, par segment. Il vaut `complete` si l'un de
ces critères est vrai, `allegee` sinon :

1. `safety_family` : la fiche relève d'une famille de sécurité (`safety_families.is_safety_proposal`,
   ADR-114 D1, fail-closed) ;
2. `numeric_value` : le segment porte une valeur chiffrée (`numeric_exactitude.extract_values`) ;
3. `procedure` : le segment est une procédure ou un intervalle (section « Montage & erreurs
   fréquentes », section « Entretien », `editorial.replacement_guidance`,
   `editorial.maintenance_interval`, `maintenance`) ;
4. `diagnostic_relation` : le segment porte une relation de diagnostic (`diagnostic_relations`,
   section « Symptômes & diagnostic », `editorial.failure_symptoms`).

Le relecteur peut monter un segment en `complete` (`escalated`, ou `doubt` : un doute vaut
`complete`). Il ne descend jamais sous le plancher.

- `complete` : chaque affirmation est qualifiée ; toute affirmation sans passage, ou de verdict
  autre que `conserver`, est bloquante une fois l'étape câblée.
- `allegee` : chaque affirmation est qualifiée ; seul `retirer` est bloquant.

## 6. Entrées, exécution et sortie

- Entrée unique : l'invite (§7 ou §8) suivie du paquet JSON sur stdin. Le paquet est celui de
  `semantic_review.py packet`, plus `depth_floor` par segment et, pour la contestation,
  l'artefact contesté. Rien d'autre : ni proposition de travail, ni raisonnement du producteur.
- Isolement : celui de `_meta/semantic-review.md` §7 (processus neuf, répertoire vide, aucun outil,
  aucun serveur MCP, aucune instruction ni mémoire locale, aucune session conservée).
- Fraîcheur : le relecteur lit la fiche depuis `origin`, ou après la garde
  `scripts/ops/check-repo-freshness.sh` (monorepo). L'artefact consigne le commit lu.
- Indépendance : `reviewer.provider` du contestataire diffère de celui du 11 et de
  `producer.provider`. Un producteur `unknown` rend la condition fausse.
- Sortie : la réponse JSON du modèle, assemblée en artefact conforme à
  `_meta/schema/technical-qualification-run.schema.json`, déposé sous
  `_audit/technical-qualification/<slug>/<clé>/<sha256>.json`, FAIL compris, puis versionné par PR
  WIKI. Un FAIL n'est remplacé par aucun PASS sur la même clé.

## 7. Invite — qualification

<!-- invite:qualification -->
Qualification technique — département 11 (ADR-131, candidat)

Tu qualifies le texte publié d'une fiche technique automobile, segment par segment. Tu ne disposes
que du paquet JSON ci-dessous : les segments du texte publié, le plancher de profondeur de chaque
segment (`depth_floor`) et les captures RAW que la fiche cite. N'utilise aucune autre source : ta
connaissance propre ne porte aucune affirmation.

Méthode : vérifie les affirmations et conditions des réponses techniques, séparément du signal de
demande. Ne généralise pas les intervalles, couples, emplacements ou gestes d'un véhicule ou d'un
produit à tous les autres. Décris les limites et les cas qui demandent une aide professionnelle.
Une question ne valide jamais la réponse qu'elle appelle.

Pour chaque segment du paquet, dans l'ordre et sans en omettre aucun :
- s'il ne porte aucune affirmation technique (titre, identifiant, liste de sources) :
  {"id": "<id>", "depth": "<depth_floor>", "no_claims": true} ;
- sinon, relève chaque affirmation (valeurs, conditions et précautions comprises) et donne-lui :
  - "verdict" : "conserver" si une capture la porte dans sa portée et que le texte n'omet rien de ce
    que cette capture y rattache ; "preciser" si la portée est trop large, ou si le texte omet une
    condition, une précaution, une cause ou un cas d'aide professionnelle qu'une capture rattache au
    même sujet ; "reformuler" si le fond est juste et la forme
    fautive ; "retirer" si aucune capture ne la porte, si une capture la contredit, ou si elle peut
    conduire à un geste dangereux ;
  - "sources" : les passages recopiés à l'identique depuis les captures, avec "path" et "cid" ;
    liste vide seulement si aucune capture ne la porte ;
  - "portee" : ce que la source couvre (véhicule, moteur, produit, conditions) ;
  - "limite" : ce que la source ne couvre pas, les cas qui demandent une aide professionnelle, et
    toute omission du texte ; si "limite" décrit une omission du texte, le verdict n'est pas
    "conserver" ;
  - "proposed_wording" : une formulation pour "preciser" ou "reformuler", sinon null.

Profondeur : "depth" vaut au moins `depth_floor`. Monte un segment "allegee" en "complete" si
l'affirmation peut conduire à un geste, à une omission dangereuse ou à un mauvais diagnostic, et
ajoute "escalated" à "depth_reasons" ; dans le doute, monte-le et ajoute "doubt". Ne descends
jamais. Reprends dans "depth_reasons" les motifs du plancher fournis par le paquet.

Réponds uniquement par un objet JSON, sans autre texte :
{"segments": [
  {"id": "<id>", "depth": "complete", "depth_reasons": ["procedure"],
   "claims": [{"text": "...", "verdict": "preciser",
               "sources": [{"path": "...", "cid": "sha256:...", "quote": "..."}],
               "portee": "...", "limite": "...", "proposed_wording": "..."}]},
  {"id": "<id>", "depth": "allegee", "depth_reasons": [], "no_claims": true}]}

Paquet :
<!-- /invite -->

## 8. Invite — contestation

<!-- invite:contestation -->
Contestation d'une qualification technique (ADR-131, candidat)

Un relecteur a qualifié le texte publié d'une fiche technique automobile. Tu le contestes de façon
indépendante. Tu ne disposes que du paquet JSON ci-dessous : les segments du texte publié, le
plancher de profondeur de chaque segment, les captures RAW que la fiche cite et la qualification à
contester (`qualification`). N'utilise aucune autre source : ta connaissance propre ne tranche rien.

Pour chaque affirmation qualifiée, donne ta position :
- "agree" : le verdict, la source, la portée et la limite tiennent ;
- "contest" : l'un d'eux est faux ; donne le "verdict" que tu retiendrais et cite le passage qui le
  montre ;
- "undecidable" : aucune capture ne tranche ; "passage": null.
Un passage est recopié à l'identique depuis une capture, avec son "path" et son "cid". Conteste en
particulier un "conserver" dont le passage ne porte pas l'affirmation ou dont la limite décrit une
omission du texte (condition, précaution, cause ou cas d'aide professionnelle que la capture
rattache au sujet), une portée généralisée à tous
les véhicules, une limite absente, et une profondeur sous le plancher.

Relève ensuite dans "missed" toute affirmation des segments que la qualification n'a pas relevée,
avec le verdict que tu lui donnes.

Réponds uniquement par un objet JSON, sans autre texte :
{"segments": [{"id": "<id>", "positions": [{"claim_id": "c0", "position": "contest",
                 "verdict": "retirer", "statement": "...",
                 "passage": {"path": "...", "cid": "sha256:...", "quote": "..."}}]}],
 "missed": [{"segment_id": "<id>", "text": "...", "verdict": "retirer", "statement": "...",
             "passage": null}]}
Ne liste que les segments qui portent des affirmations qualifiées.

Paquet :
<!-- /invite -->

## 9. Ce que ce skill ne fait pas

- Il n'approuve, ne promeut et n'écrit aucune fiche. Il ne remplace pas l'auto-review de sens
  (ADR-119) : il s'y ajoute.
- Il ne lit ni le RAG ni une page servie (ADR-031, ADR-046).
- Il ne qualifie pas une page R1, R3 ou R4 : elle hérite de la qualification de sa fiche.
- Il n'invente ni mot-clé, ni URL, ni valeur.

## 10. Évolution

- 0.1.0 (2026-11-15) : première révision, étalonnée le 2026-11-15.
- 0.2.0 (2026-11-15) : durcissement après cet étalonnage. Une omission du texte interdit
  `conserver` ; la contestation la vise. Sur `plaquette-de-frein@88f9f88`, la 0.1.0 rendait
  `conserver` sur la question 5 de la FAQ tout en décrivant l'omission dans `limite`.

Durcir la méthode (un motif de plancher en plus, un verdict plus strict) : PR WIKI. L'assouplir
(un motif de plancher retiré, un verdict rendu non bloquant) : ADR, comme le protocole d'ADR-119.
