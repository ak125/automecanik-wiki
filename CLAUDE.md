# Règles automecanik-wiki

> Ce repo est la **base de connaissance métier canonique** AutoMecanik.
> Toute action d'agent IA doit respecter les règles ci-dessous.

## Principe fondamental

Tout ce qui est brut par défaut va dans `automecanik-raw`. Seul ce qui sort propre et validé entre dans `automecanik-wiki`.

La promotion `automecanik-raw/recycled/` → `automecanik-wiki/wiki/` est **toujours** une décision humaine, jamais automatique.

## Rôle du LLM

Le LLM peut **proposer, relier, résumer, extraire, enrichir**. Il ne **valide** ni ne **publie** rien sans humain.

## Interdictions absolues

- Ne **jamais** écrire directement dans `wiki/` sans instruction humaine explicite
- Écrire d'abord dans `proposals/` (sauf véhicules R8 — voir `_meta/ingestion-contract.md`)
- Ne **jamais** marquer une fiche `validated` ou `human_reviewed` sans validation humaine
- Ne **jamais** supprimer une source raw
- Ne **jamais** inventer de compatibilité véhicule
- Ne **jamais** transformer une hypothèse en fait
- Ne **jamais** exporter vers RAG / SEO / chatbot sans `quality-gates.md` PASS
- Ne **jamais** stocker de secret, token, mot de passe, fichier `.env`

## Workflow standard (gammes, constructeurs, support, diagnostic)

1. Lire la source `automecanik-raw/recycled/...` ou `automecanik-raw/sources/...`
2. Identifier les entités via `_meta/entity-registry.json`
3. Extraire les faits — marquer `extracted` / `inferred` / `ambiguous`
4. Créer ou modifier une fiche dans `proposals/<entity_type>/<slug>.md`
5. Renseigner `source_refs:` (chemin raw + lineage)
6. Mettre à jour `index.md`
7. Ajouter une entrée dans `log.md`
8. Laisser `review_status: needs_human_review`

## Workflow R8 (vehicles) — différent

Les véhicules suivent **ADR-022** (governance-vault) :
- Génération R8 future : passe par `__rag_proposals` (DB Supabase) quand activée
- Migration R8 existante : `automecanik-rag/knowledge/vehicles/` → `automecanik-raw/recycled/rag-knowledge/vehicles/` → validation humaine → `wiki/vehicles/`
- Pas de dossier `proposals/vehicles/` parallèle

Voir `_meta/ingestion-contract.md` §"Cas R8".

## Validation humaine

Seul l'humain peut passer :
- `review_status: human_reviewed`
- `status: validated`
- `exportable.rag: true`
- `exportable.seo: true`
- `exportable.support: true`

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
- `legacy-recycler` (recycle CSV / blog)
- `kw-classify` (classification keywords)

Étendre l'existant plutôt que créer un 4ème outil concurrent.

## Référence canon

ADR-031 — Raw / Wiki / RAG / SEO Separation
`ak125/governance-vault/ledger/decisions/adr/ADR-031-raw-wiki-rag-seo-separation.md`
