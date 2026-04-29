# Proposals — index humain

> Liste des propositions en attente de review humaine, lisible directement.
> Le fichier `_manifest.json` à côté est la version machine (schéma ADR-031 §D19).
> Une fois reviewé, une proposition est promue vers `wiki/<entity_type_pluriel>/<slug>.md` puis retirée d'ici (ADR-031 §D23 : pluriel pour les collections naturelles, singulier invariant pour `support/` et `diagnostic/`).

## Convention

- **FLAT** : aucun sous-dossier, un fichier `<slug>.md` par proposition (D19).
- **status** : `pending_review` (initial), `in_review` (humain en train de regarder), `approved` (sera promue par le skill `proposal-promoter`), `rejected` (avec note `_audit/disputes/`).
- **Slugs uniques par entity_type** — vérifié par `_scripts/check-slug-uniqueness.mjs`.

## Pilote ADR-031 Phase E (2026-04-28)

3 propositions de pilote conservées (la 4ᵉ — `lada-granta` — a été retirée en Phase F.3 : source absente sur `automecanik-rag` main, voir `_manifest.json` champ `removed[]`) :

| #   | entity_type  | slug                                        | source                                   | status         |
| --- | ------------ | ------------------------------------------- | ---------------------------------------- | -------------- |
| 1   | gamme        | [plaquette-de-frein](plaquette-de-frein.md) | automecanik-rag/knowledge/gammes/        | pending_review |
| 2   | constructeur | [dacia](dacia.md)                           | automecanik-rag/knowledge/constructeurs/ | pending_review |
| 3   | support      | [livraison](livraison.md)                   | automecanik-rag/knowledge/policies/      | pending_review |

## Phase F.3 — vehicles batch (2026-04-28)

7 propositions générées par `_scripts/recycle-from-rag.py --apply` à partir de `automecanik-rag/knowledge/vehicles/` (8 fichiers, 1 skip data quality `renault.md` brand-only misplaced) :

| #   | entity_type | slug                                          | make    | model         | status         |
| --- | ----------- | --------------------------------------------- | ------- | ------------- | -------------- |
| 1   | vehicle     | [citroen-c3](citroen-c3.md)                   | citroen | c3            | pending_review |
| 2   | vehicle     | [ford-focus-3](ford-focus-3.md)               | ford    | focus-3       | pending_review |
| 3   | vehicle     | [peugeot-206](peugeot-206.md)                 | peugeot | 206           | pending_review |
| 4   | vehicle     | [renault-clio-3](renault-clio-3.md)           | renault | clio-3        | pending_review |
| 5   | vehicle     | [renault-clio-iii](renault-clio-iii.md)       | renault | clio-iii      | pending_review |
| 6   | vehicle     | [renault-megane-3](renault-megane-3.md)       | renault | megane-3      | pending_review |
| 7   | vehicle     | [volkswagen-golf-6](volkswagen-golf-6.md)     | volkswagen | golf-6     | pending_review |

### Doublon connu à arbitrer en review

`renault-clio-3` vs `renault-clio-iii` : même véhicule, deux slugs concurrents (chiffres arabes vs romains). Décision attendue en review humaine — fusion l'un dans l'autre, choix d'un slug canonique.

### Skip data quality

`automecanik-rag/knowledge/vehicles/renault.md` — slug `renault` sans split make-model. C'est une fiche brand-only misplaced (doublon de `automecanik-rag/knowledge/constructeurs/renault.md` qui est canonique). À fixer côté source `automecanik-rag` avant Phase F.2 (constructeurs batch).

### Critères PASS Phase F.3

- 7 fichiers `.md` vehicle créés (FLAT, slug kebab-case, prefix make-model).
- Frontmatter v1.0 valide (`node _scripts/validate-frontmatter.mjs`).
- `_manifest.json` étendu de 7 entrées + 1 entrée `removed[]` (lada-granta) + 1 entrée `skipped_data_quality[]` (renault.md).
- Aucune collision de slug par entity_type (`node _scripts/check-slug-uniqueness.mjs`).

### Suite

- **Phase F.2** — constructeurs (36 fichiers) : direct via recycler tel quel.
- **Phase F.0.x** — `recycle-from-rag.py --mode enrich` pour le flux D15bis (absorption guides+reference dans gammes body).
- **Phase F.1** — reference + guides absorbables → distribué dans `wiki/gammes/<slug>.md` body sections + `entity_data.references[]`.
- **Phase F.4** — gammes (241 fichiers) : plus volumineux, peut-être à sous-découper.
- **F.tombstones** — 3 fichiers redondants → `automecanik-raw/manifests/tombstones.json` per D21.

## Références

- ADR-031 §D19 (proposals FLAT + index obligatoire), §D15bis (mapping guides/reference distribué), §D23 (path convention pluriel) — vault PRs #100, #103, #104, #106
- `_meta/schema/frontmatter.schema.json` — schema v1.0
- `_meta/schema/entity-data/<entity_type>.schema.json` — schemas typés
- Plan d'exécution `/home/deploy/.claude/plans/verifier-diagnostic-faq-policies-declarative-rain.md`
- Knowledge entry pré-Phase F : `governance-vault/ledger/knowledge/adr-031-pre-phase-f-audit-corrections-20260428.md`
