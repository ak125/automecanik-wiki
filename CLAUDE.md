# Règles automecanik-wiki

> Ce repo est la **base de connaissance métier canonique** AutoMecanik.
> Toute action d'agent IA doit respecter les règles ci-dessous.

## Principe fondamental

Tout ce qui est brut par défaut va dans `automecanik-raw`. Seul ce qui sort propre et validé entre dans `automecanik-wiki`.

La promotion `automecanik-raw/recycled/` → `automecanik-wiki/wiki/` est **toujours** une décision humaine, jamais automatique.

## Rôle du LLM

Le LLM peut **proposer, relier, résumer, extraire, enrichir**. Il ne **valide** ni ne **publie** rien sans humain.

## Interdictions absolues

- Ne **jamais** écrire directement dans `wiki/<area>/` sans instruction humaine explicite
- Écrire d'abord dans `proposals/` (FLAT — routage par frontmatter `entity_type`)
- Ne **jamais** promouvoir une fiche en `review_status: approved` ou `exportable.<x>: true` sans validation humaine
- Ne **jamais** supprimer une source raw
- Ne **jamais** inventer de compatibilité véhicule
- Ne **jamais** transformer une hypothèse en fait
- Ne **jamais** exporter vers RAG / SEO / chatbot sans `_meta/quality-gates.md` PASS
- Ne **jamais** stocker de secret, token, mot de passe, fichier `.env`
- Ne **jamais** modifier `_meta/entity-registry.json` manuellement (passe par `lineage-tracker` skill)

## Workflow standard — UNIFORME pour toutes les entités

Le même flux s'applique à **gammes, vehicles, constructeurs, support, diagnostic** — pas d'exception.

1. Lire la source `automecanik-raw/recycled/...` ou `automecanik-raw/sources/...`
1. Identifier les entités via `_meta/entity-registry.json`
1. Extraire les faits — marquer `extracted` / `inferred` / `ambiguous`
1. Créer ou modifier une fiche dans `proposals/<slug>.md` (FLAT, `entity_type` dans frontmatter)
1. Renseigner `source_refs:` (chemin raw + lineage)
1. Ajouter `lineage_id` (UUIDv7) + `content_hash` (SHA-256 du body)
1. Mettre à jour `index.md`
1. Ajouter une entrée dans `log.md`
1. Laisser `review_status: in_review` (statut canonique défini dans `_meta/schema/frontmatter.schema.json`)

## Note ADR-022 (R8 vehicles) — sujet downstream backend

Le mécanisme `__rag_proposals` (DB Supabase, ADR-022 governance-vault) est une **génération R8** côté backend, **distinct** du flux raw → wiki présent. Son activation est gouvernée par la variable d'environnement `RAG_PROPOSAL_MODE` côté NestJS (lue à `onModuleInit`).

Quand activé, ses sorties merged sont traitées comme **un input parmi d'autres** vers `automecanik-raw/recycled/`, puis suivent le flux uniforme jusqu'à `wiki/vehicles/`. Pas de cas spécial fichier — le sas markdown wiki reste l'unique source de promotion vers `wiki/<entity_type>/`.

## Note ADR-033 (gamme diagnostic_relations) — contrat wiki gamme

Pour `entity_type: gamme` (cf. ADR-033 `accepted` 2026-04-29) :

- Les fiches wiki ne doivent **pas** recréer localement les symptômes — la DB `__diag_symptom` est SoT.
- Les relations diagnostic pointent vers le bloc `diagnostic_relations[]` du frontmatter v2.0.0 (cf. `_meta/schema/frontmatter.schema.json`).
- **Anti-pattern interdit** : `entity_data.symptoms[]` ou `diagnostic.symptoms[]` (ADR-033 §D2). Bloqué par `_scripts/quality-gates.py` `legacy_symptoms_block`.

## Validation humaine

Seul l'humain peut passer :

- `review_status: approved` (transition finale dans l'enum `frontmatter.schema.json`)
- `exportable.rag: true`
- `exportable.seo: true`
- `exportable.support: true`

> **Note** : les enums `review_status` autorisés sont `draft | proposed | in_review | approved | deprecated`
> (cf. [\_meta/schema/frontmatter.schema.json](_meta/schema/frontmatter.schema.json#L169)). Les anciens
> termes `needs_human_review`, `human_reviewed`, `status: validated` sont désormais interdits — bloqués
> par hook pre-commit `forbid-non-schema-statuses-in-docs` + validateur `_scripts/validate-frontmatter.py`.

## Coverage manifest obligatoire

Tout audit / scan / rapport produit dans ce repo doit suivre `_meta/agent-exit-contract.md` :

- statuts autorisés uniquement (pas de `COMPLETE`, `100%`, `ALL_FIXED`)
- coverage manifest obligatoire (`scope_requested`, `files_read_count`, `excluded_paths`, `unscanned_zones`, `remaining_unknowns`, `final_status`)
- séparation 5 états : scan | analysis | correction (proposée) | validation | verdict

## Skills à réutiliser (pas de duplication)

Avant de créer un nouveau script de lint / quality / extraction, vérifier les skills existants côté monorepo :

- `seo-vault-verify` (SHA256 reproductibilité, cross-refs ADR)
- `rag-lint.py` (validation frontmatter)
- `content-quality-gate` (scoring sections)
- `legacy-recycler` (recycle CSV / blog) — étendu pour `--target=wiki-proposal`
- `kw-classify` (classification keywords)

Étendre l'existant plutôt que créer un 4ème outil concurrent.

## Structure du repo

| Dossier                                                    | Rôle                                                           |
| ---------------------------------------------------------- | -------------------------------------------------------------- |
| `inbox/{web-clips,voice-notes,manual}/`                    | Captures temporaires non canoniques                            |
| `proposals/`                                               | Fiches en cours d'extraction (FLAT, routage par `entity_type`) |
| `wiki/{gammes,vehicles,constructeurs,support,diagnostic}/` | Base canonique validée                                         |
| `maps/`                                                    | MOCs Obsidian par domaine                                      |
| `glossary/`                                                | Atomic notes terminologie/synonymes                            |
| `taxonomy/`                                                | Vocabulaires contrôlés (families, intents, segments)           |
| `_meta/`                                                   | Règles, quality gates, schemas JSON, entity registry           |
| `_meta/schema/`                                            | JSON Schemas pour frontmatter + exports                        |
| `_templates/`                                              | Squelettes Obsidian (Templater compatible)                     |
| `_scripts/`                                                | Scripts repo-local (validate-frontmatter, promote, etc.)       |
| `_audit/`                                                  | Logs de promotions, deprecations, disputes                     |
| `exports/{rag,seo,support}/`                               | Sorties générées (gitignored sauf contrats)                    |

## Référence canon

- **ADR-031** — Raw / Wiki / RAG / SEO Separation (`accepted` 2026-04-28, vault PR #107)
  `ak125/governance-vault/ledger/decisions/adr/ADR-031-raw-wiki-rag-seo-separation.md`
- **ADR-032** — Diagnostic & Maintenance unification (`accepted` 2026-04-29)
  `ak125/governance-vault/ledger/decisions/adr/ADR-032-diagnostic-maintenance-unification.md`
- **ADR-033** — Wiki gamme `diagnostic_relations[]` contract (`accepted` 2026-04-29, vault PR #108)
  `ak125/governance-vault/ledger/decisions/adr/ADR-033-wiki-gamme-diagnostic-relations-contract.md`
