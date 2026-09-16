# `build_exports_seo.py` — Vue dérivée contractuelle wiki → exports/seo/

Référence : [ADR-059 SEO Runtime Projection](https://github.com/ak125/governance-vault/blob/main/ledger/decisions/adr/ADR-059-seo-runtime-projection.md) — Phase B PR-5a.

## Principe non-négociable

Ce builder est une **vue dérivée éphémère**. Il **filtre + transforme** le wiki canon approuvé. Il ne génère, n'enrichit, ni n'infère **jamais**.

```
automecanik-wiki/wiki/<entity_type_singular>/<slug>.md (review_status: approved, exportable.seo: true)
       ↓ filter audience SEO (entity_type ∈ {gamme, vehicle, constructeur, diagnostic-with-R3})
       ↓ transform structured JSON (facts, sources, blocks, roles_allowed)
       ↓ ajv-validable contre _meta/schema/exports-seo.schema.json
       ↓
       automecanik-wiki/exports/seo/<entity_type>/<slug>.json
```

> **Gate audience.** `exportable` est un **mapping** `{ rag, seo, support }`
> (frontmatter.schema.json) — le builder lit **strictement `exportable.seo`**.
> Une fiche `{ seo: false, rag: true }` n'entre **jamais** dans `exports/seo/`.
>
> **Déterminisme (fonction pure du canon).** L'export ne dépend QUE du contenu de
> la fiche : `source_wiki_commit` + `generated_at` = SHA/committer-date du **dernier
> commit touchant cette fiche** (`git log -1 -- <fiche>`, pas le HEAD bruité, jamais
> l'horloge murale) ; `content_hash` = sha256 des octets source ; ordre
> découverte/blocs/sources trié. Conséquence : deux runs sur le même canon →
> octets identiques, et l'auto-commit CI **ne boucle pas** (le commit d'export ne
> touche pas `wiki/`, donc ces champs ne bougent pas). `source_wiki_commit` est
> informational-only (audit) per ADR-059 — autorité de replay = `exports_snapshot_hash`.

## 9 garde-fous verrouillés (vérifiés par Pytest)

| #     | Verrou                                                             | Mécanisme                                              |
| ----- | ------------------------------------------------------------------ | ------------------------------------------------------ |
| 1     | `roles_allowed` minItems:1                                         | Schema JSON `minItems: 1` + builder skip si vide       |
| 2     | support exclu de exports/seo/                                      | Schema enum sans `support` + builder filter explicite  |
| 3     | diagnostic vers SEO seulement si block R3_CONSEILS/S2_DIAG         | Builder `_has_r3_s2_diag_block()` + filter             |
| 4     | `schema_version` ≠ `projection_contract_version` (distincts)       | Schema `required` les 2 + tests négatifs               |
| 5     | `source_wiki_commit`, `wiki_path`, `content_hash` obligatoires     | Schema `required` + tests négatifs                     |
| 6     | 0 LLM (anthropic/openai/groq/cohere/mistralai/google.generativeai) | Test statique `test_no_llm_inference_imports`          |
| 7     | 0 DB (psycopg/asyncpg/supabase/sqlalchemy/django)                  | Test statique `test_no_db_imports`                     |
| 8     | gate audience = `exportable.seo` (pas un dict truthy)              | `_is_seo_eligible` + régression `seo:false rag:true`   |
| 9     | `generated_at` + `source_wiki_commit` déterministes per-fiche      | `_wiki_file_commit_meta` + test statique no-wall-clock |
| **+** | 0 enrichissement (generate\_/enrich\_/synthesize/infer\_)          | Test statique `test_no_enrichment_logic_patterns`      |
| **+** | 0 écriture hors `exports/seo/`                                     | `_enforce_output_path_strict()` + 5 tests négatifs     |

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

## Tests

```bash
cd _scripts
pytest test_build_exports_seo.py -v
```

Couverture (sélection) : schema (valid payload, roles_allowed minItems:1, support
exclusion, champs requis, patterns, enum, additionalProperties) · builder (refuse
support / non-approved / `exportable.seo` faux / diagnostic sans S2_DIAG ; accepte
diagnostic+S2_DIAG, gamme valide ; régression `seo:false rag:true`) · déterminisme
(`generated_at` = committer-date, deux runs byte-identiques ; no-wall-clock statique)
· output path (5 refus + 1 allow) · statiques (no LLM, no DB, no enrichment).

## CI

- **Validation** — job `validate-exports-seo` dans `automecanik-wiki/.github/workflows/wiki-quality-gates.yml` : Pytest builder + schema, puis ajv-validate des `exports/seo/*/*.json` contre le schema canon.
- **Génération + commit** — job `wiki-exports-seo-generate.yml` **côté monorepo** (modèle `diag-canon-slugs-export.yml`) : checkout wiki (source ET cible) → run builder → ajv → diff idempotent → commit/push bot dans `automecanik-wiki/exports/seo/`. C'est le déclencheur qui peuple `exports/seo/` (avant, jamais exécuté → dossier vide).

## Génération automatique vs édition manuelle

`exports/seo/` est désormais **commit** (Pattern B, comme `exports/rag/`) et
produit par le job CI ci-dessus (bot). **Ne jamais éditer un fichier
`exports/seo/*.json` à la main** — c'est une projection générée ; corriger le
canon wiki puis régénérer.

## Hors scope PR-5a

- **PR-5b** (monorepo) : snapshot tar.zst immutable (replay SoT) — le job de génération couvre déjà l'exécution périodique.
- **PR-6 / 6b** : DB projection 7 tables + 2 MVs + 2 queues BullMQ (writer DARK, présent).
- **PR-6c** : feeder qui enqueue `projection-write-queue` depuis `exports/seo/` (absent).
- **PR-7** : RPC `get_active_seo_projection` + GRANT anon + adapter pages.

Ces composants attendent l'instruction explicite séparée (owner-gated : apply migration, GRANT, flag, deploy).

## Retrait et perte d'approbation

Le builder prépare le périmètre demandé avant d'écrire. Si un ancien export JSON
n'a plus de source éligible (fiche retirée, approbation perdue ou export SEO refusé),
la commande termine en erreur `UNRECONCILED` et conserve l'export comme preuve.
Aucun autre export du lot n'est écrit avant cette vérification. Le mode `--entity-id`
ne contrôle que l'export de cette entité ; le mode complet contrôle les répertoires
SEO des types supportés. Le dry-run rapporte la même incohérence sans écrire.

Ce garde ne constitue pas un tombstone ni une autorisation de supprimer : le retrait
aval, ses dépendances et l'invalidation DB/cache/index restent à réconcilier par le
parcours gouverné avant publication. Un échec de builder ne doit pas être annoncé
comme un snapshot complet fraîchement publiable.

### Observations de réconciliation en JSON

```bash
python3 _scripts/build_exports_seo.py --wiki-root <checkout-wiki> \
  --entity-id gamme:filtre-a-huile --dry-run --format json
```

Le format texte reste le défaut. En JSON, un build cohérent rend `status: OK`,
`planned` et `written` (zéro en dry-run). Un export historique sans source éligible
rend `status: UNRECONCILED`, `written: 0` et une liste `observations` sur stdout,
avec un code de sortie non nul et le diagnostic texte sur stderr. Les erreurs
préalables (racine, Git, parsing ou argument invalide) gardent le comportement
Click existant ; elles ne garantissent pas une réponse JSON.

Chaque observation contient l'identité attendue depuis le chemin de l'export,
le chemin source dérivé, les empreintes SHA-256 des octets effectivement lus et
les déclarations observées dans l'export et le frontmatter. Le chemin `wiki_path`
déclaré dans le JSON n'est jamais suivi ; les liens sortant du périmètre sont
refusés. Le hash source et ses métadonnées proviennent de la même lecture.
`source_file_sha256` désigne le fichier entier ; `observed_source.content_hash`
reste la déclaration du hash du corps, sans équivalence supposée entre les deux.
`observed_export.blocks` conserve les coordonnées natives des blocs ; il ne
calcule pas leurs identifiants DB et ne vérifie pas les consommateurs.

Les motifs principaux distinguent `SOURCE_MISSING`,
`SOURCE_PRESENT_WITHOUT_ELIGIBLE_EXPORT` et
`SOURCE_DEPRECATED_WITHOUT_WITHDRAWAL_DECISION`. Les chemins hors périmètre,
les fichiers illisibles et les métadonnées non représentables en JSON restent
signalés sans écrire ni supprimer les exports historiques.

Ces observations sont des déclarations non validées, pas une décision de retrait.
`withdrawal_authorized` reste toujours `false`. La validation/promotion WIKI est
automatique selon le moteur existant `promotion_decision.py` ; ce moteur ne
produit actuellement aucun contrat de transition de retrait. Le seul statut
`deprecated`, l'absence d'une fiche ou la perte de son gate SEO ne peuvent pas
remplacer cette décision, ni autoriser la purge des consommateurs. Le diagnostic
prépare leur réconciliation sans ajouter de moteur de décision parallèle.
