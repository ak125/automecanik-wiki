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
       │  decision humaine d'export (review_status: approved)
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

## Mapping vocabulaires (legacy schema v1.0 ↔ plan rev 6)

Le schema canonique `_meta/schema/frontmatter.schema.json` v1.0.0 reste la **référence d'autorité**. Le plan rev 6 introduit des champs additionnels orientés validation automatique. Pendant la phase de transition, les deux vocabulaires coexistent.

| Concept plan rev 6                | Champ legacy                                                      | Champ ajouté                                                                           | Notes                                                          |
| --------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| État canonique                    | `review_status: draft\|proposed\|in_review\|approved\|deprecated` | —                                                                                      | reste la source d'autorité pour les exports                    |
| État opérationnel détaillé        | —                                                                 | `status: draft\|auto_reviewed\|human_review_required\|reviewed\|rejected\|quarantined` | piloté par les gates `_scripts/quality-gates.py`               |
| Sous-état review                  | —                                                                 | `review_status_detail` ABANDONNÉ — un seul vocabulaire `review_status` (cf. schema)    | la sous-granularité passe par `validation_mode` + `risk_level` |
| Mode validation                   | —                                                                 | `validation_mode: automatic\|sampled\|human_required`                                  | trace la voie suivie                                           |
| Niveau de risque                  | —                                                                 | `risk_level: low\|medium\|high\|critical`                                              | drive l'auto-promotion §7 quality-gates                        |
| Score confiance                   | `quality_score`                                                   | `confidence_score`                                                                     | alias — la formule §4 quality-gates s'applique aux deux        |
| Raisons de blocage                | —                                                                 | `blocked_reasons: []`                                                                  | enum fermé §5 quality-gates                                    |
| Marqueurs à vérifier sans bloquer | —                                                                 | `to_verify: []`                                                                        | granularité section/claim                                      |
| Version du template               | —                                                                 | `template_version: 1.0.0`                                                              | semver §3.7 plan rev 6                                         |
| Provenance source                 | `source_refs[].kind` (`raw\|external_url\|manual\|recycled`)      | —                                                                                      | détaillé schema canon                                          |
| Confiance source                  | —                                                                 | `source_refs[].confidence: high\|medium\|low`                                          | facultatif ; alimente la formule §4 quality-gates              |

**Règle d'or** : un champ ajouté ne contredit jamais un champ legacy. En cas de conflit perçu, le schema canon `_meta/schema/frontmatter.schema.json` gagne. La convergence sera documentée dans un ADR ultérieur (transition Partie 3, §C5 plan rev 6).

## Sections obligatoires par `entity_type` (plan rev 6 §3)

Esquisse à finaliser dans les 5 templates `_meta/templates/<type>.md` :

| `entity_type`  | Sections obligatoires                                                                                                               |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `gamme`        | Définition, Fonctionnement, Symptômes d'usure, Choix selon véhicule, FAQ                                                            |
| `vehicle`      | Identité (marque/modèle/motorisation), Spécificités, Pièces fréquentes, FAQ                                                         |
| `constructeur` | Identité, Modèles principaux, Spécificités techniques, FAQ                                                                          |
| `support`      | Question, Réponse, Cas particuliers, Liens internes                                                                                 |
| `diagnostic`   | Symptôme, Causes possibles, Vérifications, Renvoi vers gammes/vehicles, **`safety_advisory` requis si `risk_level=high\|critical`** |

## Anti-patterns interdits

- Dual-write `automecanik-rag/knowledge/` + `automecanik-wiki/wiki/` (drift garanti)
- Génération de fiche `wiki/` depuis LLM seul, sans source raw vérifiable
- Promotion automatique `proposals/` → `wiki/` sans gates §7 quality-gates **OU** review humaine
- Copie massive d'un CSV dans une fiche wiki
- Direct write `wiki/<area>/` skip `proposals/` (refusé par hook `commit-msg` §3.8 plan + `wiki-protected-paths.yml` CI)
- Suppression silencieuse sans tombstone `.MOVED.md` / `.DELETED.md`
- Modification manuelle `_meta/entity-registry.json` (passe par script de promotion ou `lineage-tracker` skill)
- Flip `exportable.{rag,seo,support}: true` tant que `_scripts/wiki-readiness-check.py` ≠ READY (gated Partie 3)

## Référence canon

- ADR-031 — Raw / Wiki / RAG / SEO Separation (vault)
- Plan rev 6 — *verifier-dans-existant-si-starry-feigenbaum* §3, §6
- ADR-022 — R8 RAG Control Plane (DB-only scope, dormant)
- ADR-029 — RAG v2.1 state machine 7 étapes (paths à amender)
