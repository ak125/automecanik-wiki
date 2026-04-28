# Proposals — index humain

> Liste des propositions en attente de review humaine, lisible directement.
> Le fichier `_manifest.json` à côté est la version machine (schéma ADR-031 §D19).
> Une fois reviewé, une proposition est promue vers `wiki/<entity_type>/<slug>.md` puis retirée d'ici.

## Convention

- **FLAT** : aucun sous-dossier, un fichier `<slug>.md` par proposition (D19).
- **status** : `pending_review` (initial), `in_review` (humain en train de regarder), `approved` (sera promue par le skill `proposal-promoter`), `rejected` (avec note `_audit/disputes/`).
- **Slugs uniques par entity_type** — vérifié par `_scripts/check-slug-uniqueness.mjs`.

## Pilote ADR-031 Phase E (2026-04-28)

4 propositions de pilote pour valider le flux raw → wiki, une par entity_type stratégique :

| # | entity_type | slug | source | status |
|---|---|---|---|---|
| 1 | gamme | [plaquette-de-frein](plaquette-de-frein.md) | automecanik-rag/knowledge/gammes/ | pending_review |
| 2 | vehicle | [lada-granta](lada-granta.md) | automecanik-rag/knowledge/vehicles/ | pending_review |
| 3 | constructeur | [dacia](dacia.md) | automecanik-rag/knowledge/constructeurs/ | pending_review |
| 4 | support | [livraison](livraison.md) | automecanik-rag/knowledge/policies/ | pending_review |

### Critères PASS Phase E

- 4 fichiers `.md` créés (FLAT).
- Frontmatter v1.0 valide (`node _scripts/validate-frontmatter.mjs proposals/`).
- `_manifest.json` à 4 entrées, schéma D19.
- Aucune collision de slug par entity_type (`node _scripts/check-slug-uniqueness.mjs`).

### Suite

Phase F (batch métier 5 catégories) déclenchera `skill:legacy-recycler` pour générer en masse (gamme + vehicle + constructeur + guides + reference). Phase E sert de point de référence humain pour calibrer la qualité avant batch.

## Références

- ADR-031 §D19 (proposals FLAT + index obligatoire) — vault PR #100
- `_meta/schema/frontmatter.schema.json` — schema v1.0
- `_meta/schema/entity-data/<entity_type>.schema.json` — schemas typés
- Plan d'exécution `/home/deploy/.claude/plans/verifier-diagnostic-faq-policies-declarative-rain.md`
