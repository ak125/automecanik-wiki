# Source Policy

> Politique de sources autorisées, provenance obligatoire et règles d'écriture wiki.
> Référence canon : [ADR-031](../../governance-vault/ledger/decisions/adr/ADR-031-four-layer-content-architecture.md) §D14-D23.

______________________________________________________________________

## §1 — Sources autorisées (par ordre de priorité)

1. **Sources internes validées** (`automecanik-raw/sources/`)

   - CSV Google Search Console / Google Ads
   - Catalogues fournisseurs
   - Documents internes vérifiés
   - `source_kind: raw`, `source_level: primary`, `trust_level: verified`

1. **Sources recyclées** (`automecanik-raw/recycled/`)

   - Anciens fichiers `automecanik-rag/knowledge/`
   - Anciennes notes Markdown
   - `source_kind: recycled`, `source_level: secondary`, `trust_level: to_verify`

1. **Web clips** (`automecanik-wiki/inbox/web-clips/` ou `automecanik-raw/sources/web-clips/`)

   - Captures Obsidian Web Clipper
   - Statut `inbox` jusqu'à qualification humaine

______________________________________________________________________

## §2 — Sources rejetées par défaut

- Wikipedia EN/US sans opt-in explicite (cf. memory `feedback_wikipedia_en_fr_site.md`)
- Sites US/UK sans validation préalable (le site AutoMecanik est FR)
- Forums sans modération
- Données scrapées sans attribution claire
- Tout fichier dans `automecanik-raw/quarantine/`

______________________________________________________________________

## §3 — Provenance obligatoire (frontmatter)

Toute fiche `wiki/` ou `proposals/` doit pointer vers au moins 1 source vérifiable :

```yaml
source_refs:
  - kind: raw
    path: "recycled/rag-knowledge/gammes/plaquette-de-frein.md"
    confidence: medium
  - kind: external_url
    url: "https://www.constructeur.fr/manuel-utilisateur"
    captured_at: "2026-04-29"
    confidence: high
provenance:
  ingested_by: "skill:wiki-proposal-writer@v0.1"
  promoted_from: "proposals/plaquette-de-frein.md"
  promoted_at: "2026-04-29T15:00:00Z"
  extracted: 12       # nombre de faits extraits directement
  inferred: 3         # nombre de faits inférés
  ambiguous: 1        # nombre de zones ambiguës marquées
```

Schema canon : `_meta/schema/frontmatter.schema.json` §`source_refs`, §`provenance`.

______________________________________________________________________

## §4 — Anti-pattern : source LLM seule

**Interdiction stricte** de seed du contenu uniquement depuis LLM (cf. memory `feedback_rag_vault_always_first.md`, incident breezy-eagle 2026-04-18, 350 entrées rollback).

Toute fiche doit pointer vers une source vérifiable raw / recycled / external_url, **jamais LLM-only**.

Le skill `wiki-proposal-writer` est aligné sur le pattern *skills-first* : 0-LLM pour la structure (template fill, frontmatter, source_refs), Anthropic seul pour le texte rédactionnel à partir des sources.

______________________________________________________________________

## §5 — Zone temporaire `wiki/inbox/` (non canonique)

> **Règle clé** — `wiki/inbox/` est **autorisé** comme zone temporaire non canonique pour captures Web Clipper, voice-notes ou notes manuelles avant qualification.
>
> **Rien dans `inbox/` n'est exportable vers `exports/`.** Le contenu doit être promu vers `proposals/` puis `wiki/<entity_type>/` avant tout export.

Sous-dossiers prévus :

- `inbox/web-clips/` — captures Obsidian Web Clipper
- `inbox/voice-notes/` — transcriptions voice-to-text
- `inbox/manual/` — notes humaines en cours

Frontmatter type `inbox` :

```yaml
status: inbox
trust_level: unverified
exportable: { rag: false, seo: false, support: false }
```

Aucune capture `inbox/` n'entre directement dans `wiki/`.

______________________________________________________________________

## §6 — Statut par défaut `exportable: false`

> **Règle non-négociable** — toute fiche, **même validée** (`auto_reviewed` ou `reviewed`), garde par défaut :
>
> ```yaml
> exportable:
>   rag: false
>   seo: false
>   support: false
> ```
>
> **Le wiki peut être propre sans être consommé.** Le passage à `true` est une décision de Partie 3, gated par `_scripts/wiki-readiness-check.py` = READY (cf. plan rev 6 §9, critères C1-C6).

Aucun export Partie 1+2 :

- ❌ `exports/rag/` reste vide
- ❌ `exports/seo/` reste vide
- ❌ `exports/support/` reste vide

______________________________________________________________________

## §7 — Niveaux de confiance source (`source_level`)

| Niveau      | Définition                                 | Exemple                                                          |
| ----------- | ------------------------------------------ | ---------------------------------------------------------------- |
| `primary`   | Source originale, non transformée          | CSV GSC brut, catalogue fournisseur PDF                          |
| `secondary` | Source dérivée d'une autre source vérifiée | Ancien fichier `automecanik-rag/knowledge/`, blog advice recyclé |
| `tertiary`  | Source dérivée non vérifiable directement  | Forum, Wikipedia EN sans validation                              |

`tertiary` → généralement `automecanik-raw/quarantine/` jusqu'à validation humaine.

______________________________________________________________________

## §8 — Niveaux de vérification (`trust_level`)

| Niveau      | Définition                                      |
| ----------- | ----------------------------------------------- |
| `verified`  | Validé humainement, source reconnue             |
| `to_verify` | Reçu, en attente de validation                  |
| `disputed`  | Validation a échoué, contradictions connues     |
| `rejected`  | Décision humaine de rejet (motif dans manifest) |

Default à l'ajout : `to_verify`.

______________________________________________________________________

## §9 — Confidence par source (`source_refs[].confidence` + `diagnostic_relations[].evidence.confidence`)

Pour le calcul de `confidence_score` (cf. `quality-gates.md` §4) :

| Confidence | Numeric | Cas typique                                     |
| ---------- | ------- | ----------------------------------------------- |
| `high`     | 1.0     | OEM, fournisseur certifié, source officielle    |
| `medium`   | 0.6     | Recyclé vérifié, blog métier, web clip qualifié |
| `low`      | 0.3     | Tertiary, à corroborer, en attente validation   |

### §9.1 — `source_type` → max confidence autorisée (canon ADR-033)

Le champ `evidence.confidence` ne peut atteindre `high` que si le `source_type` (catalogue `_meta/source-catalog.yaml`) le permet. Une brochure pédagogique (Bosch FAD, Valeo formation) ≠ source `high`, peu importe la marque.

| `source_type`          | Max `confidence` | Exemples                                                |
| ---------------------- | ---------------- | ------------------------------------------------------- |
| `oem_manual`           | `high`           | Manuel utilisateur constructeur, doc atelier officielle |
| `oem_workshop`         | `high`           | Manuel d'atelier OEM, fiches techniques constructeur    |
| `tecdoc_official`      | `high`           | Fiches TecDoc officielles                               |
| `normative_standard`   | `high`           | NF, ISO, ECE-R                                          |
| `parts_feed_certified` | `high`           | Catalogue fournisseur certifié                          |
| `brochure`             | `medium` (max)   | Bosch FAD, Valeo formation, ATE pédagogique             |
| `formation`            | `medium` (max)   | Manuel de formation, support pédagogique                |
| `marketing`            | `medium` (max)   | Brochure marketing fabricant                            |
| `blog_pro`             | `medium` (max)   | Blog atelier reconnu, retours pro vérifiés              |
| `forum`                | `low` (max)      | Forum technique, groupe d'utilisateurs                  |
| `wiki_externe`         | `low` (max)      | Wikipedia, wikis tiers                                  |
| `blog_consumer`        | `low` (max)      | Blog grand public, retours d'utilisateur                |

**Application** :

- `evidence.confidence: high` + `source_type: brochure` → `blocked_reasons: [confidence_overclaimed]`
- Pour atteindre `confidence: high` sur un claim cité par une brochure, **corroborer avec ≥ 1 source `oem_manual` ou `tecdoc_official`** (i.e. `source_policy: 2_medium_concordant` minimum, idéalement `1_high` via OEM).

### §9.2 — Catalogue canon des slugs sources

Tout slug cité dans `diagnostic_relations[].sources[]` (et autres champs `sources[]` typés slug) DOIT exister dans **`_meta/source-catalog.yaml`** (registre canonique).

Règle d'enforcement : `_scripts/quality-gates.py` lit `source-catalog.yaml` et bloque (`blocked_reasons: [source_slug_unknown]`) toute citation d'un slug absent.

Ajout d'une nouvelle source : PR éditoriale avec entrée minimale (`slug`, `title`, `type`, `archived_at`, `license`).

______________________________________________________________________

## Référence canon

- ADR-031 — Raw / Wiki / RAG / SEO Separation (vault)
- Plan rev 6 — *verifier-dans-existant-si-starry-feigenbaum* §5
- Memory : `feedback_wikipedia_en_fr_site.md`, `feedback_rag_vault_always_first.md`, `skills-first-architecture.md`
