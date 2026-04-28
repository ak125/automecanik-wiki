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
| `inbox/` | Captures temporaires (web clips, notes rapides) — non canonique |
| `proposals/` | Fiches en cours d'extraction depuis `automecanik-raw`, avant validation humaine |
| `wiki/` | Base canonique validée (gammes, vehicles, constructeurs, support, diagnostic, seo) |
| `maps/` | MOCs Obsidian par domaine |
| `_meta/` | Règles, quality gates, registry d'entités, contrats d'ingestion |
| `exports/` | Sorties contrôlées par audience (rag, seo, content, support) |

## Gouvernance

- ADR canon : `ak125/governance-vault/ledger/decisions/adr/ADR-031-raw-wiki-rag-seo-separation.md`
- Règles agents : voir `CLAUDE.md` + `_meta/agent-exit-contract.md`
- Quality gates : voir `_meta/quality-gates.md`

## Repos liés

| Repo | Rôle |
|---|---|
| `ak125/automecanik-raw` | Sources brutes, recyclées, normalisées |
| `ak125/automecanik-rag` | Pipeline RAG, chunks, embeddings, chatbot |
| `ak125/nestjs-remix-monorepo` | Application + logique SEO R0-R8 + publication |
| `ak125/governance-vault` | ADR, règles, décisions, preuves |
