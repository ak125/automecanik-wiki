# Ingestion Contract

> Contrat précisant **comment** une source devient une fiche canonique.

## Flux standard (gammes, constructeurs, support, diagnostic)

```
automecanik-raw/sources/<type>/<file>
   OR automecanik-raw/recycled/<type>/<file>
       │
       │  agent extraction (legacy-recycler / kw-classify / custom)
       ▼
automecanik-wiki/proposals/<entity_type>/<slug>.md
       │
       │  validation humaine
       │  (frontmatter complet, source_refs OK, no contradictions)
       ▼
automecanik-wiki/wiki/<entity_type>/<slug>.md
       │
       │  decision humaine d'export
       │  (quality-gates.md PASS)
       ▼
automecanik-wiki/exports/{rag,seo,support}/<slug>.<audience>.md
       │
       ▼
consommateurs : automecanik-rag, monorepo SEO, chatbot, site
```

## Cas R8 (vehicles) — exception

Les véhicules suivent **ADR-022** (governance-vault). Deux flux distincts :

### Migration des 83 fichiers existants

```
automecanik-rag/knowledge/vehicles/<modèle>.md  (existant, brut)
       │
       │  copie + frontmatter source_level=secondary, trust_level=to_verify
       ▼
automecanik-raw/recycled/rag-knowledge/vehicles/<modèle>.md
       │
       │  validation humaine (sourcing, factualité, suppression hallucinations)
       ▼
automecanik-wiki/wiki/vehicles/<modèle>.md
```

### Génération R8 future (downstream, hors scope migration)

Quand `RAG_PROPOSAL_MODE=on` et publish endpoint L4 livré :

```
VehicleRagGenerator (backend)
       │
       ▼
__rag_proposals (DB Supabase, lifecycle pending|approved|rejected|merged)
       │
       │  validation pipeline (CI L2) + humaine (L4)
       ▼
[à définir post-shipping L4]
```

**Important** : pas de `proposals/vehicles/` parallèle qui doublerait `__rag_proposals`.

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
automecanik-wiki/proposals/gammes/<slug>.md (synthèse métier enrichie)
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
- soit → proposals/<entity_type>/  (si extraction directe)
```

Aucune capture web-clip n'entre directement dans `wiki/`.

## Anti-patterns interdits

- Dual-write `automecanik-rag/knowledge/` + `automecanik-wiki/wiki/` (drift garanti)
- Génération de fiche `wiki/` depuis LLM seul, sans source raw vérifiable
- Promotion automatique `proposals/` → `wiki/` sans review humaine
- Copie massive d'un CSV dans une fiche wiki

## Référence canon

ADR-031 — Raw / Wiki / RAG / SEO Separation
ADR-022 — R8 RAG Control Plane
