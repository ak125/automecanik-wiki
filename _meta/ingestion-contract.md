# Ingestion Contract

> Contrat précisant **comment** une source devient une fiche canonique.

## Flux uniforme — toutes les entités

Le même flux s'applique à **gammes, vehicles, constructeurs, support, diagnostic** — pas d'exception.

```
automecanik-raw/sources/<type>/<file>
   OR automecanik-raw/recycled/<type>/<file>
       │
       │  agent extraction (legacy-recycler / kw-classify / proposal-promoter)
       ▼
automecanik-wiki/proposals/<slug>.md
       │  (FLAT — routage par frontmatter `entity_type`)
       │
       │  validation humaine
       │  (frontmatter complet, source_refs OK, no contradictions, lineage_id, content_hash)
       ▼
automecanik-wiki/wiki/<entity_type>/<slug>.md
       │
       │  decision humaine d'export (review_status: human_reviewed)
       │  (quality-gates.md PASS, exportable.<x>: true)
       ▼
automecanik-wiki/exports/{rag,seo,support}/<slug>.<audience>.md
       │  (générés, gitignored sauf contrats schema)
       │
       ▼
consommateurs : automecanik-rag, monorepo SEO, chatbot, site
```

## Schema frontmatter v1.0 (référence)

Schema canonique versioné : `_meta/schema/frontmatter.schema.json` (à créer Phase B).

5 blocs obligatoires :
- **core** : `schema_version`, `id` (URN `<entity_type>:<slug>`), `entity_type`, `slug`, `title`, `aliases`, `lang`, `created_at`, `updated_at`
- **traceability** : `truth_level` (L1-L4, PAS L0), `source_refs` (kind/path/cid typés), `provenance`, `lineage_id` (UUIDv7), `content_hash` (SHA-256 body)
- **quality** : `review_status` (draft/proposed/in_review/approved/deprecated), `reviewed_by`, `reviewed_at`, `review_notes`, `no_disputed_claims`, `quality_score`
- **export-gates** : `exportable.{rag,seo,support}`, `target_classes` (Weaviate)
- **entity_data** : structure typée par `entity_type`

## Cas keywords (KW canon, PR monorepo #117/132/137)

```
CSV Google Ads
       │
       ▼
import-gads-kp.py
       │
       ▼
__seo_keywords (DB Supabase) — flux principal canon
       │
       ▼
/kw-classify (skill) → __seo_keyword_results
       │
       │  optionnel : extraction insights vers wiki
       ▼
automecanik-wiki/proposals/<slug>.md (synthèse métier enrichie)
```

DB = source de vérité KW. Wiki = synthèse métier enrichie en parallèle.

## Cas web clips

Captures via Obsidian Web Clipper :

```
inbox/web-clips/<capture>.md  (status: inbox, trust_level: unverified)
       │
       │  qualification humaine
       ▼
- soit → automecanik-raw/sources/web-clips/  (si source à conserver)
- soit → suppression (capture non retenue)
- soit → proposals/<slug>.md  (si extraction directe)
```

Aucune capture web-clip n'entre directement dans `wiki/`.

## Note ADR-022 — sujet downstream backend

Le mécanisme `__rag_proposals` (DB Supabase) est une génération R8 future côté backend. Actuellement DORMANT (`RAG_PROPOSAL_MODE=off`). Si activé plus tard, ses sorties merged seront traitées comme un input parmi d'autres vers `automecanik-raw/recycled/`, puis suivront le flux uniforme ci-dessus jusqu'à `wiki/vehicles/`. **Pas de cas spécial fichier**.

## Anti-patterns interdits

- Dual-write `automecanik-rag/knowledge/` + `automecanik-wiki/wiki/` (drift garanti)
- Génération de fiche `wiki/` depuis LLM seul, sans source raw vérifiable
- Promotion automatique `proposals/` → `wiki/` sans review humaine
- Copie massive d'un CSV dans une fiche wiki
- Direct write `wiki/<area>/` skip `proposals/`
- Suppression silencieuse sans tombstone `.MOVED.md` / `.DELETED.md`
- Modification manuelle `_meta/entity-registry.json` (passe par `lineage-tracker` skill)

## Référence canon

- ADR-031 — Raw / Wiki / RAG / SEO Separation (à créer Phase C)
- ADR-022 — R8 RAG Control Plane (DB-only scope, dormant)
- ADR-029 — RAG v2.1 state machine 7 étapes (paths à amender)
