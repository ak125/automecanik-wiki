# hot.md

> Mémoire chaude des agents — synthèse des règles critiques à charger au début de session.

## Architecture active

- `automecanik-raw` = sources brutes immuables + recyclées
- `automecanik-wiki` = connaissance canonique (CE REPO)
- `automecanik-rag` = pipeline RAG, chunks, chatbot
- `nestjs-remix-monorepo` = application + SEO R0-R8 + publication
- `governance-vault` = ADR, règles, décisions

## Règles critiques

- Ne jamais confondre raw et wiki
- Ne jamais importer un CSV complet dans wiki
- Ne jamais exporter vers chatbot / RAG / SEO sans `_meta/quality-gates.md` PASS
- Ne jamais inventer une compatibilité véhicule
- Ne jamais marquer `validated` ou `human_reviewed` sans validation humaine

## Workflow uniforme (tous les R)

```
automecanik-raw/sources/ ou recycled/
  → proposals/<slug>.md (FLAT, entity_type dans frontmatter)
  → validation humaine
  → wiki/<entity_type>/<slug>.md
  → exports/{rag,seo,support}/ (générés, gitignored)
```

Pas d'exception R8 — voir CLAUDE.md §"Note ADR-022".

## Schema frontmatter v1.0

5 blocs obligatoires : `core` / `traceability` / `quality` / `export-gates` / `entity_data` typé.
Référence : `_meta/schema/frontmatter.schema.json` (à créer Phase B).

## État actuel (2026-04-28)

Phase pilote — squelette créé, aucune fiche canonique encore.
4 propositions pilote prévues : gammes + constructeurs + support + 1 vehicle.
