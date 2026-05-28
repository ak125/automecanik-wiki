# `build_exports_seo.py` — Vue dérivée contractuelle wiki → exports/seo/

Référence : [ADR-059 SEO Runtime Projection](https://github.com/ak125/governance-vault/blob/main/ledger/decisions/adr/ADR-059-seo-runtime-projection.md) — Phase B PR-5a.

## Principe non-négociable

Ce builder est une **vue dérivée éphémère**. Il **filtre + transforme** le wiki canon approuvé. Il ne génère, n'enrichit, ni n'infère **jamais**.

```
automecanik-wiki/wiki/<entity_type_singular>/<slug>.md (review_status: approved, exportable: true)
       ↓ filter audience SEO (entity_type ∈ {gamme, vehicle, constructeur, diagnostic-with-R3})
       ↓ transform structured JSON (facts, sources, blocks, roles_allowed)
       ↓ ajv-validable contre _meta/schema/exports-seo.schema.json
       ↓
       automecanik-wiki/exports/seo/<entity_type>/<slug>.json
```

## 7 garde-fous verrouillés (vérifiés par 28 tests Pytest)

| #     | Verrou                                                             | Mécanisme                                             |
| ----- | ------------------------------------------------------------------ | ----------------------------------------------------- |
| 1     | `roles_allowed` minItems:1                                         | Schema JSON `minItems: 1` + builder skip si vide      |
| 2     | support exclu de exports/seo/                                      | Schema enum sans `support` + builder filter explicite |
| 3     | diagnostic vers SEO seulement si block R3_CONSEILS/S2_DIAG         | Builder `_has_r3_s2_diag_block()` + filter            |
| 4     | `schema_version` ≠ `projection_contract_version` (distincts)       | Schema `required` les 2 + tests négatifs              |
| 5     | `source_wiki_commit`, `wiki_path`, `content_hash` obligatoires     | Schema `required` + tests négatifs                    |
| 6     | 0 LLM (anthropic/openai/groq/cohere/mistralai/google.generativeai) | Test statique `test_no_llm_inference_imports`         |
| 7     | 0 DB (psycopg/asyncpg/supabase/sqlalchemy/django)                  | Test statique `test_no_db_imports`                    |
| **+** | 0 enrichissement (generate\_/enrich\_/synthesize/infer\_)          | Test statique `test_no_enrichment_logic_patterns`     |
| **+** | 0 écriture hors `exports/seo/`                                     | `_enforce_output_path_strict()` + 5 tests négatifs    |

## Schema JSON contractuel

`_meta/schema/exports-seo.schema.json` (draft-07, ajv-validable) :

- `entity_id` pattern `^(gamme|vehicle|constructeur|diagnostic):[a-z0-9-]+$` (support exclu)
- `entity_type` enum `{gamme, vehicle, constructeur, diagnostic}`
- `wiki_path` pattern `^wiki/(gamme|vehicle|constructeur|diagnostic)/...\.md$` (singulier ADR-031 §148)
- `roles_allowed.items.enum` enum canonique R-codes (R5 sunset, exclu)
- `consumers_allowed.minItems: 1` + enum {seo, rag, support, diagnostic_tool}
- `additionalProperties: false` — refuse champs non-canon

## Usage

```bash
# Build tous les exports éligibles
python3 _scripts/build_exports_seo.py --wiki-root /opt/automecanik/automecanik-wiki

# Build un seul entity
python3 _scripts/build_exports_seo.py \
  --wiki-root /opt/automecanik/automecanik-wiki \
  --entity-id gamme:filtre-a-huile

# Dry-run (n'écrit rien)
python3 _scripts/build_exports_seo.py --wiki-root ... --dry-run
```

## Tests (28/28 PASS)

```bash
cd _scripts
pytest test_build_exports_seo.py -v
```

Couverture :

- **11 tests schema** : valid payload, roles_allowed minItems:1, support exclusion, schema_version/projection_contract_version requis, source_wiki_commit/wiki_path/content_hash requis, wiki_path pattern, entity_id pattern, role enum, additionalProperties false
- **7 tests builder** : refuse support, refuse non-approved, refuse non-exportable, refuse diagnostic sans S2_DIAG, accepte diagnostic avec S2_DIAG, accepte gamme valide, skip roles_allowed vide
- **6 tests output path** : refuse wiki canon dir, refuse exports/rag, refuse exports/support, refuse proposals, refuse outside wiki_root, allow exports/seo
- **4 tests statiques** : no LLM, no DB, no enrichment patterns, schema path referenced

## CI

Job `validate-exports-seo` dans `.github/workflows/wiki-quality-gates.yml` :

1. Pytest builder + schema (28 tests)
1. ajv-validate de tous les `exports/seo/*/*.json` existants contre le schema canon

## Hors scope PR-5a

- **PR-5b** (monorepo) : cron systemd timer + sd_notify pour exécution périodique du builder + snapshot tar.zst immutable
- **PR-6** : DB projection 7 tables + 2 MVs + 2 queues BullMQ + replay_projection.py
- **PR-7** : RPC + adapter pages + depcruise/ast-grep guards

Ces composants attendent l'instruction explicite séparée.
