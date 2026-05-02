# Proposals — index humain

> Liste des propositions en attente de review humaine, lisible directement.
> Le fichier `_manifest.json` à côté est la version machine (schéma ADR-031 §D19).
> Une fois reviewé, une proposition est promue vers `wiki/<entity_type_pluriel>/<slug>.md` puis retirée d'ici (ADR-031 §D23 : pluriel pour les collections naturelles, singulier invariant pour `support/` et `diagnostic/`).

## Convention

- **FLAT** : aucun sous-dossier, un fichier `<slug>.md` par proposition (D19).
- **status** : `pending_review` (initial), `in_review` (humain en train de regarder), `approved` (sera promue par le skill `proposal-promoter`), `rejected` (avec note `_audit/disputes/`).
- **Slugs uniques par entity_type** — vérifié par `_scripts/check-slug-uniqueness.mjs`.

## État actuel — 2026-05-02

**0 proposition en attente.** 9/9 fiches du batch plan deja-verifier-existant ont été promues vers `wiki/` lors de la Phase 6 (cf. `_manifest.json` champ `promoted[]`).

## Phase 6 — promotions du 2026-05-02

| #   | entity_type  | slug                | wiki target                                    |
| --- | ------------ | ------------------- | ---------------------------------------------- |
| 1   | gamme        | filtre-a-air        | wiki/gammes/filtre-a-air.md                    |
| 2   | gamme        | plaquette-de-frein  | wiki/gammes/plaquette-de-frein.md              |
| 3   | constructeur | dacia               | wiki/constructeurs/dacia.md                    |
| 4   | vehicle      | citroen-c3          | wiki/vehicles/citroen-c3.md                    |
| 5   | vehicle      | ford-focus-3        | wiki/vehicles/ford-focus-3.md                  |
| 6   | vehicle      | peugeot-206         | wiki/vehicles/peugeot-206.md                   |
| 7   | vehicle      | renault-clio-3      | wiki/vehicles/renault-clio-3.md                |
| 8   | vehicle      | renault-megane-3    | wiki/vehicles/renault-megane-3.md              |
| 9   | vehicle      | volkswagen-golf-6   | wiki/vehicles/volkswagen-golf-6.md             |

`plaquette-de-frein` a reçu 2 entrées `diagnostic_relations[]` supplémentaires (slugs FR canon `distance_freinage_allongee` + `voyant_freinage_allume`) après merge PR monorepo #269 qui a créé ces symptomes en DB.

## Suite — backlog Phase F (étapes restantes ADR-031)

- **Phase F.2** — constructeurs (36 fichiers restants) : direct via recycler.
- **Phase F.0.x** — `recycle-from-rag.py --mode enrich` pour D15bis (absorption guides+reference dans gammes body).
- **Phase F.1** — reference + guides absorbables → `wiki/gammes/<slug>.md` body sections + `entity_data.references[]`.
- **Phase F.4** — gammes (241 fichiers) : plus volumineux, à sous-découper.
- **F.tombstones** — 3 fichiers redondants → `automecanik-raw/manifests/tombstones.json` per D21.

## Doublons / Skip historiques

- `renault-clio-iii` (chiffres romains) fusionné dans `renault-clio-3` 2026-05-02 — voir `_manifest.json` champ `removed[]`. Blocs uniques caradisiac absorbés. aliases enrichis pour résoudre toute requête `clio-iii` vers la fiche canon.
- `livraison` retirée 2026-05-02 — déjà figée système commercial AutoMecanik (CGV juridiques + conditions transporteurs API + page légale site).
- `lada-granta` skip — slug introuvable côté source automecanik-rag.
- `automecanik-rag/knowledge/vehicles/renault.md` — slug brand-only misplaced (doublon de `constructeurs/renault.md`). À fixer côté source avant Phase F.2.

## Références

- ADR-031 §D19 (proposals FLAT + index obligatoire), §D15bis (mapping guides/reference distribué), §D23 (path convention pluriel) — vault PRs #100, #103, #104, #106
- `_meta/schema/frontmatter.schema.json` — schema v1.0
- `_meta/schema/entity-data/<entity_type>.schema.json` — schemas typés
- Plan d'exécution `/home/deploy/.claude/plans/verifier-diagnostic-faq-policies-declarative-rain.md`
- Knowledge entry pré-Phase F : `governance-vault/ledger/knowledge/adr-031-pre-phase-f-audit-corrections-20260428.md`
