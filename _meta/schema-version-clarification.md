# Wiki Schema Version Clarification

> **Version**: 1.0.0 | **Status**: CANON | **Date**: 2026-05-13
> **Related ADR**: ADR-031 §148 (singular path), ADR-039 (Zod TS mirror canon), ADR-033 (v2.0.0 transition piste)

## Objectif

Lever 2 ambiguïtés bloquantes identifiées lors du gap analysis ADR-031 / ADR-058 :

1. Quelle version de frontmatter est canon **maintenant** (v1.0.0 vs v2.0.0) ?
2. Convention path `wiki/<entity_type_singular>/` (ADR-031) vs disk historique pluriel.

---

## Frontmatter schema canon courant : v1.0.0

| Élément | Source | Statut |
|---|---|---|
| **`_meta/schema/frontmatter.schema.json`** | Titré `"automecanik-wiki frontmatter v1.0.0"` (ligne 4) | **CANON courant** |
| **ADR-039** | Zod TS mirror du JSON Schema v1.0.0 (`@repo/wiki-frontmatter`) | LIVE |
| **v2.0.0** | Piste ADR-033 transition future (frontmatter étendu pour diag relations) | **PAS canon courant**, transition à venir |

### Règle effective pour proposals nouvelles (2026-05-13)

Toute proposal (et toute fiche wiki canonique) doit valider `frontmatter.schema.json` v1.0.0 :

- `schema_version: "1.0.0"` requis
- 11 champs obligatoires : `schema_version`, `id`, `entity_type`, `slug`, `title`, `lang`, `created_at`, `updated_at`, `truth_level`, `review_status`, `exportable`
- `entity_type` ∈ `{gamme, vehicle, constructeur, support, diagnostic}` (singulier strict)
- `additionalProperties: false` (rejet champs non-canoniques)

Les fiches actuelles utilisant `schema_version: "2.0.0"` cohabitent transitoirement, mais ne sont **pas** canon. Migration coordonnée par ADR-033 (à venir).

---

## Convention path : SINGULIER (ADR-031 §148)

ADR-031 §148 (canon proposé) impose :

> Convention de chemin figée : `wiki/<entity_type_singular>/` (relatif au repo) ou `/opt/automecanik-wiki/wiki/<entity_type_singular>/` (full path). **Pas de variantes pluriel** (`wiki/gammes/` interdit). La redondance `automecanik-wiki/wiki/` est cosmétique acceptée — schema v1.0 ancre cette structure.

### État disk 2026-05-13 (avant rename) — 5 dossiers

| Dossier disk | Conformité ADR-031 §148 |
|---|---|
| `wiki/gammes/` | NON (pluriel) — VIDE |
| `wiki/vehicles/` | NON (pluriel) — VIDE |
| `wiki/constructeurs/` | NON (pluriel) — VIDE |
| `wiki/diagnostic/` | OK (déjà singulier) |
| `wiki/support/` | OK (déjà singulier) |

### Rename effectué dans cette PR

```bash
git mv wiki/gammes      wiki/gamme
git mv wiki/vehicles    wiki/vehicle
git mv wiki/constructeurs wiki/constructeur
# diagnostic et support : déjà conformes, pas de rename
```

Safe car :
- Les 3 dossiers ciblés sont **vides** (audit empirique 2026-05-13)
- Toutes les fiches existantes (proposals + wiki/) utilisent déjà `entity_type:` au singulier dans leur frontmatter (audit `grep -rE '^entity_type:'`)
- Le script monorepo `app/scripts/wiki/wiki-readiness-check.py` est défensif (`returns "N/A — does not exist"` si dir absent) — pas de régression silencieuse

### Hits cross-repo signalés (followup non-bloquant)

Détectés par `grep -rnE 'wiki/(gammes|vehicles|constructeurs)'` au moment du rename :

| Repo | Fichier | Lignes | Type |
|---|---|---|---|
| `nestjs-remix-monorepo` | `scripts/wiki/wiki-readiness-check.py` | 28, 29, 33, 158, 161, 165, 184 | docstrings + chemins de vérification (défensif) |
| `automecanik-wiki` | `_meta/schema/exports/rag.schema.json` | 39 | description textuelle (fixé dans cette PR) |

**Followup monorepo PR** : `chore/wiki-readiness-check-singular-path-sync` (non-bloquant, le script est défensif sur dir-not-exists).

---

## Références

- [ADR-031 Four-Layer Content Architecture](https://github.com/ak125/governance-vault/blob/main/ledger/decisions/adr/ADR-031-four-layer-content-architecture.md) §148 (status: proposed)
- [ADR-039 Wiki Frontmatter Zod Canon](https://github.com/ak125/governance-vault/blob/main/ledger/decisions/adr/ADR-039-wiki-frontmatter-zod-canon.md) (LIVE)
- [ADR-033 Wiki Gamme Diagnostic Relations](https://github.com/ak125/governance-vault/blob/main/ledger/decisions/adr/ADR-033-wiki-gamme-diagnostic-relations.md) (accepted, v2.0.0 transition future)
- [ADR-031 gap analysis SEO runtime](https://github.com/ak125/governance-vault/blob/main/ledger/knowledge/adr-031-gap-analysis-seo-runtime.md) (knowledge note, 2026-05-13)
- ADR-058 SEO Runtime Projection Architecture (proposed via vault PR-1, **supplements** ADR-031)
