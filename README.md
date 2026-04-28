# automecanik-wiki

Base de connaissance métier canonique AutoMecanik — Markdown / Obsidian, sourcée, versionnée, maintenue par LLM sous validation humaine.

## Rôle

Couche **wiki** dans l'architecture documentaire 4 layers :

```
automecanik-raw  →  automecanik-wiki  →  exports  →  consommateurs
   (brut)             (canonique)          (filtré)    (RAG / SEO / chatbot / site)
```

## Principe fondamental

> **Tout ce qui est brut par défaut va dans `automecanik-raw`.
> Seul ce qui sort propre et validé entre dans `automecanik-wiki`.**

La promotion `raw/recycled/` → `wiki/` est **toujours une décision humaine**, jamais automatique.

## Structure

| Dossier | Rôle |
|---|---|
| `inbox/{web-clips,voice-notes,manual}/` | Captures temporaires non canoniques |
| `proposals/` | Fiches en cours d'extraction (FLAT — routage par frontmatter `entity_type`) |
| `wiki/{gammes,vehicles,constructeurs,support,diagnostic}/` | Base canonique validée |
| `maps/` | MOCs Obsidian par domaine |
| `glossary/` | Atomic notes terminologie / synonymes |
| `taxonomy/` | Vocabulaires contrôlés (families, intents, segments) |
| `_meta/` | Règles, quality gates, registry, contrats d'ingestion |
| `_meta/schema/` | JSON Schemas versionés (frontmatter + exports + entity-data) |
| `_templates/` | Squelettes Obsidian (Templater compatible) |
| `_scripts/` | Scripts repo-local (validate-frontmatter, promote, etc.) |
| `_audit/` | Logs de promotions, deprecations, disputes |
| `exports/{rag,seo,support}/` | Sorties générées (gitignored sauf contrats schema) |

## Workflow uniforme — tous les R

Le même flux s'applique à **gammes, vehicles, constructeurs, support, diagnostic** — pas d'exception.

Voir `_meta/ingestion-contract.md` pour le détail.

## Gouvernance

- ADR canon : `ak125/governance-vault/ledger/decisions/adr/ADR-031-raw-wiki-rag-seo-separation.md` (à créer Phase C)
- Règles agents : voir `CLAUDE.md` + `_meta/agent-exit-contract.md`
- Quality gates : voir `_meta/quality-gates.md`
- Schema frontmatter : `_meta/schema/frontmatter.schema.json` (à créer Phase B)

## Repos liés

| Repo | Rôle |
|---|---|
| `ak125/automecanik-raw` | Sources brutes, recyclées, normalisées |
| `ak125/automecanik-rag` | Pipeline RAG, chunks, embeddings, chatbot |
| `ak125/nestjs-remix-monorepo` | Application + logique SEO R0-R8 + publication |
| `ak125/governance-vault` | ADR, règles, décisions, preuves |
