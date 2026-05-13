# bridge_rag_to_pipeline.py — Adaptateur rag → pipeline PR-3a

Pont **ultra-minimal** entre les fichiers source `automecanik-rag/knowledge/<cat>/<slug>.md`
et le pipeline canonique PR-3a (`automecanik-app/scripts/wiki_promotion/`).

Référence : [ADR-059 SEO Runtime Projection](https://github.com/ak125/governance-vault/blob/main/ledger/decisions/adr/ADR-059-seo-runtime-projection.md) — Phase B PR-3b.

## Principe non-négociable

Ce script est un **simple adaptateur d'entrée**, pas un pipeline parallèle.
Toute extraction (Schema.org JSON-LD, Readability, Trafilatura, DOM selectors)
est déléguée au pipeline PR-3a via **subprocess invocation**.

```
rag/knowledge/<cat>/<slug>.md
       ↓ parse frontmatter (category, slug, title)
       ↓ body markdown → HTML synthétique minimal (<article><pre>)
       ↓ sha256(body) = filename
       ↓ écrit raw/recycled/rag-knowledge/<cat>/<sha256>.html + .manifest.yaml
       ↓ subprocess: scripts.wiki_promotion.extract_claims → claims.yaml
       ↓ subprocess: scripts.wiki_promotion.build_source_map → source_map.yaml
       ↓ subprocess: scripts.wiki_promotion.render_proposal → proposals/<slug>.md
       ↓
       automecanik-wiki/proposals/<slug>.md     ← seule destination autorisée
```

## Garde-fous (vérifiés par tests statiques)

- **0 LLM** : aucun import LLM dans le bridge
- **0 DB** : aucun import DB dans le bridge
- **0 logique d'extraction parallèle** : aucun import direct de `readability` / `trafilatura` / lib markdown — le bridge wrappe simplement le body en `<article><pre>` pour préserver le contenu littéral, et invoque PR-3a qui fait l'extraction
- **0 écriture wiki canon** : aucun chemin `wiki/<entity_type>/` dans le bridge (héritage transitif via `render_proposal._refuse_wiki_canon_write` du pipeline PR-3a)

## Mapping category → entity_type canon (ADR-031 §148)

| rag category | entity_type canon |
|---|---|
| `gammes`         | `gamme` |
| `vehicles`       | `vehicle` |
| `constructeurs`  | `constructeur` |
| `support`/`policies`/`faq`/`faqs` | `support` |
| `diagnostic`     | `diagnostic` |

## Usage

```bash
# Pré-requis : pipeline PR-3a installé dans le monorepo
cd /opt/automecanik/app/scripts/wiki_promotion
pip install -r requirements.txt
python3 -m playwright install chromium  # nécessaire pour capture_web_to_raw, pas pour bridge

# Bridge un fichier rag
cd /opt/automecanik/automecanik-wiki
python3 _scripts/bridge_rag_to_pipeline.py \
  --rag-file /opt/automecanik/rag/knowledge/gammes/plaquette-de-frein.md
# → écrit automecanik-wiki/proposals/plaquette-de-frein.md

# Dry-run (mapping calculé sans invocation pipeline)
python3 _scripts/bridge_rag_to_pipeline.py \
  --rag-file ... --dry-run
```

## Pas de pipelines concurrents

Le script `recycle-from-rag.py` (existant dans ce repo, écrit avant ADR-059)
contient sa propre logique d'extraction in-place. **Il sera déprécié dans une
PR séparée** une fois le bridge canon stabilisé. En attendant, les deux
coexistent mais **seul le bridge est canon ADR-059**.

## Tests

```bash
cd _scripts
pip install pytest pyyaml click
pytest test_bridge_rag_to_pipeline.py -v
```

Couverture :
- mapping category → entity_type singular
- parsing frontmatter rag
- conversion synthetic HTML (préserve contenu littéral, pas de lib markdown)
- garde-fous statiques (no LLM, no DB, no parallel extraction, no direct wiki canon write)

## Ordre robuste PR (ADR-059 Phase B)

```
PR-3a (monorepo) ✅  — pipeline canon raw → proposal
PR-3b (wiki, ce PR)  — bridge rag → pipeline PR-3a (cette PR)
PR-4                  — quality gates wrappers
PR-5a / PR-5b         — exports SEO + cron systemd
PR-6                  — DB projection 7 tables + replay
PR-7                  — RPC + adapter pages + guards
```
