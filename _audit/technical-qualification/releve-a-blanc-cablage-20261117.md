# Relevé à blanc du câblage de `technical_qualification_pass` (ADR-131 D3)

Date : 2026-11-17, 14:18 UTC. Mandat S, complément n° 7. Lecture seule : aucun fichier WIKI ni RAW n'a été écrit par le relevé.

## 1. Ce qui a été évalué

| Élément           | Valeur                                                                                                              |
| ----------------- | ------------------------------------------------------------------------------------------------------------------- |
| WIKI, arbre A     | `origin/main` `a8368b6d331f220ae1bae6e50a57a38c8cf527b0`, worktree détaché                                          |
| WIKI, arbre B     | branche de cette PR (base #134 `2e3fd6dc974a0cc94816bc0c6a548450b7101138`, plus le câblage non commité)             |
| Fiches            | `wiki/**` et `proposals/*.md` hors `_*`, identiques sur A et B (`git diff` vide sur `wiki`, `proposals`, `exports`) |
| RAW               | `origin/main` `b097ca48a393e0cddaec54be1765038cfa8ec733`, extrait par `git archive` dans un dossier jetable         |
| Code              | `_scripts/` de cette branche                                                                                        |
| Décision complète | `canonical_promotion_decision`, constante vide puis `"ADR-131"` posée en mémoire (aucune écriture)                  |

L'arbre A n'a ni le skill du 11, ni le schéma d'artefact, ni le module : sur A, chaque fiche vaut `UNAVAILABLE` (`_meta/skills/qualification-technique/SKILL.md` absent). C'est le comportement attendu tant que #134 n'est pas fusionnée : une entrée absente donne `UNAVAILABLE`, jamais un succès. L'arbre B est celui qui sera en place une fois #134 puis cette PR fusionnées.

## 2. Relevé par fiche

« Arbre A » et « Arbre B » : statut de `technical_qualification` dans la trace. « Décision » : statut de promotion avec la constante vide, puis levée ; codes ajoutés par la levée. Les fiches de `wiki/` ne passent pas par `promote.py --all` (il ne lit que `proposals/`).

| Fiche                                | Revue    | Exports      | Sécurité | Arbre A     | Arbre B       | Motif (arbre B)                                 | Décision (arbre B)                                  |
| ------------------------------------ | -------- | ------------ | -------- | ----------- | ------------- | ----------------------------------------------- | --------------------------------------------------- |
| `wiki/diagnostic/faq.md`             | approved | seo, support | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | —                                                   |
| `wiki/diagnostic/safety-config.md`   | approved | aucun        | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | —                                                   |
| `wiki/diagnostic/signs.md`           | approved | aucun        | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | —                                                   |
| `wiki/diagnostic/vocab-clusters.md`  | approved | aucun        | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | —                                                   |
| `wiki/diagnostic/wizard-steps.md`    | approved | aucun        | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | —                                                   |
| `wiki/gamme/filtre-a-air.md`         | approved | seo          | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[1] sans cid` | —                                                   |
| `wiki/gamme/filtre-a-carburant.md`   | approved | seo          | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | —                                                   |
| `wiki/gamme/filtre-a-huile.md`       | approved | seo          | non      | UNAVAILABLE | ABSENT        | aucun artefact sous la clé courante             | —                                                   |
| `wiki/gamme/filtre-d-habitacle.md`   | approved | seo          | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | —                                                   |
| `wiki/gamme/plaquette-de-frein.md`   | approved | seo          | oui      | UNAVAILABLE | ABSENT        | aucun artefact sous la clé courante             | —                                                   |
| `wiki/support/controles-mensuels.md` | approved | support      | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | —                                                   |
| `proposals/citroen-c3.md`            | proposed | aucun        | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |
| `proposals/courroie-d-accessoire.md` | proposed | aucun        | oui      | UNAVAILABLE | ABSENT        | aucun artefact sous la clé courante             | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |
| `proposals/dacia.md`                 | proposed | aucun        | non      | UNAVAILABLE | ABSENT        | aucun artefact sous la clé courante             | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |
| `proposals/disque-de-frein.md`       | proposed | aucun        | oui      | UNAVAILABLE | ABSENT        | aucun artefact sous la clé courante             | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |
| `proposals/ford-focus-3.md`          | proposed | aucun        | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |
| `proposals/peugeot-206.md`           | proposed | aucun        | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |
| `proposals/renault-clio-3.md`        | proposed | aucun        | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |
| `proposals/renault-megane-3.md`      | proposed | aucun        | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |
| `proposals/renault-scenic-ii.md`     | proposed | aucun        | non      | UNAVAILABLE | NO_CAPTURE    | aucune capture RAW citée                        | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |
| `proposals/support-moteur.md`        | proposed | aucun        | non      | UNAVAILABLE | ABSENT        | aucun artefact sous la clé courante             | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |
| `proposals/thermostat.md`            | proposed | aucun        | non      | UNAVAILABLE | ABSENT        | aucun artefact sous la clé courante             | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |
| `proposals/vanne-egr.md`             | proposed | aucun        | non      | UNAVAILABLE | ABSENT        | aucun artefact sous la clé courante             | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |
| `proposals/volkswagen-golf-6.md`     | proposed | aucun        | non      | UNAVAILABLE | INVALID_INPUT | `capture_ref_unpinned: source_refs[0] sans cid` | BLOCKED → BLOCKED, + `TECHNICAL_QUALIFICATION_FAIL` |

Sur l'arbre A, la levée ajoute `TECHNICAL_QUALIFICATION_UNAVAILABLE` (UNKNOWN_FAIL_CLOSED) au lieu de `TECHNICAL_QUALIFICATION_FAIL`, pour les 13 candidates.

## 3. Comptes

| Mesure                                             | Valeur                                                                         |
| -------------------------------------------------- | ------------------------------------------------------------------------------ |
| Fiches promues (`wiki/`)                           | 11 (5 gamme, 5 diagnostic, 1 support)                                          |
| Candidates (`proposals/`)                          | 13                                                                             |
| `PASS`                                             | 0 sur 24                                                                       |
| Arbre A : `UNAVAILABLE`                            | 24                                                                             |
| Arbre B : `INVALID_INPUT` (référence RAW sans cid) | 15 (9 promues, 6 candidates)                                                   |
| Arbre B : `ABSENT`                                 | 8 (2 promues, 6 candidates)                                                    |
| Arbre B : `NO_CAPTURE`                             | 1 (candidate)                                                                  |
| Candidates `ELIGIBLE`, constante vide              | 0 sur 13                                                                       |
| Candidates `ELIGIBLE`, constante levée             | 0 sur 13                                                                       |
| Décisions changées par le câblage en report-only   | 0 sur 13 (même statut, mêmes codes que le code de #134 et que celui de `main`) |

`ABSENT` sur `filtre-a-huile` et `plaquette-de-frein` : les artefacts de l'étalonnage de #134 sont rangés sous `_audit/technical-qualification/calibration-20261115/<slug>/`, pas sous `_audit/technical-qualification/<slug>/` que lit le décideur, et leurs clés portent les versions 0.2.0 et 0.3.0 du skill. Le décideur ne les compte pas, et ne doit pas les compter.

## 4. Effet sur les exports

- **Constante vide (état de cette PR)** : aucun. Aucun motif n'est ajouté, aucune décision ne change (0 sur 13, comparaison faite avec le code de #134 et le code de `main`, chacun sur son arbre).
- **Constante levée (PR ultérieure, hors de ce mandat)** :
  - exports servis par `build_exports_seo.py`, `build_exports_diagnostic.py` et les exports RAG constructeurs : ils n'appellent pas le décideur. Les 5 exports SEO gamme, les 5 exports diagnostic gamme et les 36 exports RAG constructeurs ne changent pas ;
  - `build_exports_content.py` appelle `canonical_promotion_decision` sur chaque `wiki/gamme/*.md` dont `exportable.content` vaut `true`. Aucune fiche ne le déclare aujourd'hui, et `exports/content/` n'existe pas. Après la levée, une fiche sans `PASS` ne pourra pas entrer dans cet export (`CANONICAL_DECISION_BLOCKED`) ;
  - fiches de `wiki/` : le décideur ne les retire pas. Un retrait reste le rollback manuel du §10.
- **Aucune fiche servie ne disparaît**, ni avec la constante vide, ni avec la constante levée.

Dès la fusion, le changement des fichiers `_scripts/*.py` modifie `content_revision` et `decision_engine_revision`. Toute décision déjà rendue devient `STALE_DECISION`, comme à chaque changement du moteur. Aucune décision n'est consignée aujourd'hui pour un export content.

## 5. Constats hors câblage (signalés, non corrigés)

- **P11, RAG comme source** : `wiki/gamme/filtre-a-air.md`, `filtre-a-carburant.md` et `filtre-d-habitacle.md` (exportées en SEO) citent `recycled/rag-knowledge/**` comme source RAW. Les candidates `citroen-c3`, `ford-focus-3`, `peugeot-206`, `renault-clio-3`, `renault-megane-3` et `volkswagen-golf-6` le font aussi. Le câblage ne les compte pas comme preuve : ces références n'ont pas de cid (`INVALID_INPUT`), et une capture absente du catalogue n'a pas de domaine d'autorité (`capture_domains`). Leur re-sourçage relève d'un autre mandat.
- **Banc de #136** : `liste-des-manques.md` classe déjà `recycled/rag-knowledge/**` comme « non (bootstrap) » : il ne compte pas comme autorité.
- **Montage du relevé** : les gates historiques (`quality-gates.py`, `load_registry`) lisent `_meta/entity-registry.json` depuis le dépôt du code, pas depuis la racine WIKI évaluée. Un code lancé sur l'arbre d'un autre worktree voit donc chaque slug « déjà au registre » (`GATE_CLAIM`). Les comparaisons du §3 lancent chaque code sur son propre arbre.

## 6. Reproduction

Script lancé hors du dépôt (`dryrun_tq.py SCRIPTS_DIR WIKI_ROOT RAW_ROOT LABEL --decide`) : pour chaque fiche, `promotion_decision._technical_qualification_local`, puis `canonical_promotion_decision` avec `TECHNICAL_QUALIFICATION_ADR` à `None` puis à `"ADR-131"`, posé sur le module chargé en mémoire.
