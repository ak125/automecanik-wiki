# Source Policy

> Politique de sources autorisées et de leur provenance.

## Sources autorisées (par ordre de priorité)

1. **Sources internes validées** (`automecanik-raw/sources/`)
   - CSV Google Search Console / Google Ads
   - Catalogues fournisseurs
   - Documents internes vérifiés

2. **Sources recyclées** (`automecanik-raw/recycled/`)
   - Anciens fichiers `automecanik-rag/knowledge/`
   - Anciennes notes Markdown
   - Toutes marquées `source_level: secondary`, `trust_level: to_verify`

3. **Web clips** (`automecanik-wiki/inbox/web-clips/` ou `automecanik-raw/sources/web-clips/`)
   - Captures Obsidian Web Clipper
   - Statut `inbox` jusqu'à qualification humaine

## Sources rejetées par défaut

- Wikipedia EN/US sans opt-in explicite (cf. memory `feedback_wikipedia_en_fr_site.md`)
- Sites US/UK sans validation préalable (le site AutoMecanik est FR)
- Forums sans modération
- Données scrapées sans attribution claire
- Tout fichier dans `automecanik-raw/quarantine/`

## Provenance obligatoire

Chaque fiche `wiki/` doit indiquer dans son frontmatter :

```yaml
source_refs:
  - "automecanik-raw/sources/seo-keywords/2026-04-28-gsc-keywords.csv"
  - "automecanik-raw/recycled/rag-knowledge/gammes/plaquette-de-frein.md"
provenance:
  extracted: <int>      # nombre de faits extraits directement
  inferred: <int>       # nombre de faits inférés
  ambiguous: <int>      # nombre de zones ambiguës marquées
```

## Anti-pattern : source LLM seule

Interdiction de seed du contenu uniquement depuis LLM (cf. memory `feedback_rag_vault_always_first.md`, incident breezy-eagle 2026-04-18, 350 entrées rollback).

Toute fiche doit pointer vers une source vérifiable raw/recycled, jamais LLM-only.
