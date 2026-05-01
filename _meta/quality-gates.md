# Quality Gates

> Conditions obligatoires avant promotion d'une fiche `proposals/` → `wiki/`,
> et avant export `wiki/` → `exports/`.
>
> Schema canonique : `_meta/schema/frontmatter.schema.json` (v1.0.0).
> Plan canon : [ADR-031](../../governance-vault/ledger/decisions/adr/ADR-031-four-layer-content-architecture.md) §D14-D23, plan rev 6 (verifier-dans-existant).

______________________________________________________________________

## §1 — Modèle de validation : automatique par défaut, humain ciblé

> *« On ne valide pas tout à la main. On automatise la qualité et on réserve l'humain aux cas où il apporte une vraie sécurité. »*

La validation humaine systématique n'est pas scalable. Le système applique :

1. **Validation automatique** par défaut (gates §2 + score §4 + risk_level §3)
1. **Échantillonnage** sur fiches auto-validées (§5)
1. **Validation humaine obligatoire** uniquement pour critical (§3) ou bloqué par gates (§2)

______________________________________________________________________

## §2 — Gates automatiques (lecture seule, aucune écriture DB)

Sur chaque fiche `proposals/<slug>.md`, le pipeline `_scripts/quality-gates.py` vérifie :

| #   | Contrôle                             | Méthode                                                                                 | Verdict            |
| --- | ------------------------------------ | --------------------------------------------------------------------------------------- | ------------------ |
| 1   | Frontmatter valide                   | Schema v1.0 (`_meta/schema/frontmatter.schema.json`, JSON Schema 2020-12)               | PASS / FAIL        |
| 2   | Sources présentes                    | `source_refs ≥ 1` (sauf `truth_level: L4`)                                              | PASS / FAIL        |
| 3   | Sources résolvables                  | Fichier `automecanik-raw/<path>` existe ou URL accessible                               | PASS / WARN        |
| 4   | Sections obligatoires                | Cf. template `_meta/templates/<entity_type>.md`                                         | PASS / FAIL        |
| 5   | Slug unique                          | Comparaison `_meta/entity-registry.json`                                                | PASS / FAIL        |
| 6   | Pas de pollution scrape              | Skill `pollution-scanner` mode lint read-only (Textar, Brembo, "Skip to main content"…) | PASS / WARN        |
| 7   | Pas de mélange catalogue             | Heuristique : prix, stock, SKU, compatibilité exacte produit/véhicule                   | PASS / FAIL        |
| 8   | Liens internes valides               | Résolution dans `wiki/`                                                                 | PASS / WARN        |
| 9   | Anti-duplication                     | Comparaison fingerprint vs fiches existantes                                            | PASS / WARN        |
| 10  | Cohérence avec raw                   | `source_refs` pointent vers `automecanik-raw/sources/` ou `recycled/`                   | PASS / WARN        |
| 11  | Pas de promesse commerciale          | Heuristique : « meilleur », « garanti », « le moins cher »…                             | PASS / FAIL        |
| 12  | Pas d'affirmation safety non sourcée | Mots-clés safety + source `confidence: high` requis                                     | PASS / FAIL humain |
| 13  | `confidence_score` ≥ seuil           | Formule §4 calculée par `_scripts/compute-confidence-score.py`                          | PASS / WARN        |

Les rapports vivent dans `_meta/qa-reports/<date>/`. **Artefacts d'audit ; ne remplacent pas les fiches ni les manifests raw.**

______________________________________________________________________

## §3 — Classification du risque (`risk_level`)

| Niveau       | Exemples                                                                                                | Action par défaut                                                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **low**      | glossaire, synonymes, descriptions générales, KW non critiques                                          | auto-promotion possible                                                                                                                 |
| **medium**   | gammes, constructeurs, vehicles généraux, FAQ non contractuelle                                         | auto-promotion possible si score §4 ≥ 0.85 + sampling périodique                                                                        |
| **high**     | diagnostic freinage/direction/batterie, conseil pouvant influencer une réparation, support sensible     | promotion possible **uniquement** si sources solides ET mentions de prudence présentes ; sinon `human_review_required`. Export `false`. |
| **critical** | paiement, retour, garantie, livraison contractuelle, compatibilité exacte, prix, stock, sécurité légale | humain obligatoire **ou blocage**                                                                                                       |

______________________________________________________________________

## §4 — Formule `confidence_score` (déterministe)

```
confidence_score =
    0.40 × moyenne(source_refs[].confidence_numeric)   # high=1.0, medium=0.6, low=0.3
  + 0.30 × (sections_remplies / sections_obligatoires)
  + 0.20 × (links_internes_resolus / max(links_internes_total, 1))
  + 0.10 × (1.0 si ≥ 2 source_refs avec types distincts sinon 0.0)
```

- Calculée par `_scripts/compute-confidence-score.py`
- **Mode `--check`** (par défaut au pre-commit) : vérifie que la valeur écrite est cohérente avec la formule. FAIL si l'auteur a triché.
- **Mode `--fix`** explicite : l'auteur lance le script pour réécrire le score. Pas de magie automatique au commit.
- Idempotent : recalcul sur même contenu = même score.
- Seuils par `risk_level` : low ≥ 0.70, medium ≥ 0.85, high ≥ 0.95.

______________________________________________________________________

## §5 — `blocked_reasons` (vocabulaire fermé)

Valeurs autorisées dans `blocked_reasons[]` :

```
schema_invalid             — frontmatter ou template invalide
sources_missing            — source_refs vide
sources_unresolvable       — au moins 1 source_ref ne résout pas
sections_missing           — sections obligatoires manquantes
slug_collision             — slug déjà présent dans entity-registry
pollution_detected         — pollution scrape (Textar, Brembo, fragments HTML)
catalog_leak               — prix/stock/SKU/compatibilité exacte détectés
commercial_promise         — promesse commerciale détectée
safety_unsourced           — affirmation sécurité critique sans source haute confiance
duplication_detected       — fiche fingerprint très proche d'une fiche existante
source_conflict            — sources contradictoires
confidence_below_threshold — score < seuil pour le risk_level
post_hoc_source_disproven  — source devenue fausse après promotion (rollback §7)
human_review_pending       — fiche critical en attente d'examen humain

# Gates ADR-033 §D1-§D3 (canon diagnostic_relations[])
relation_to_part_missing   — entrée diagnostic_relations[] sans relation_to_part
symptom_unstructured       — symptôme implicite dans le corps non miroité dans diagnostic_relations[]
confidence_overclaimed     — evidence.confidence: high mais source_type ne le permet pas (cf. source-policy.md §9.1)
source_policy_violated     — source_policy: 1_high mais aucune source confidence: high ;
                             ou source_policy: 2_medium_concordant mais < 2 sources medium concordantes
legacy_symptoms_block      — présence de diagnostic.symptoms: (bloc legacy interdit ADR-033 §D2)
forbidden_systemes_dir     — fichier dans wiki/systemes/ (anti-pattern ADR-033 §D3)
forbidden_per_symptom_file — fichier wiki/diagnostic/<symptom>-*.md matchant pattern interdit (ADR-033 §D3) ;
                             le dossier wiki/diagnostic/ lui-même reste autorisé (ADR-032 §D1)
source_slug_unknown        — slug cité dans diagnostic_relations[].sources[] absent de _meta/source-catalog.yaml
maintenance_advice_missing — fiche gamme matchant un kg_nodes.MaintenanceInterval
                             mais sans entity_data.maintenance.educational_advice (ADR-032 §D1)
```

Tout autre valeur fait échouer le gate `schema_invalid`.

## §5.bis — Gates spécifiques ADR-033 (canon `diagnostic_relations[]`)

### Validation granulaire par symptôme (ADR-033 §D1, source_policy)

Pour **chaque** entrée `diagnostic_relations[]` :

| `source_policy`       | Règle                                                                                                            |
| --------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `1_high`              | ≥ 1 source `confidence: high` ET son `source_type` autorise `high` (cf. `source-policy.md §9.1`)                 |
| `2_medium_concordant` | ≥ 2 sources `confidence: medium`, citant des **références distinctes** (pas simplement deux pages d'un même PDF) |
| `manual_review`       | Fiche bloquée → `status: human_review_required` jusqu'à validation humaine                                       |

Sinon → `blocked_reasons: [source_policy_violated]`.

### Détection des symptômes implicites (gate `symptom_unstructured`)

Si le corps de la fiche contient un lexique de symptôme français (« bruit », « grincement », « vibration », « voyant », « fumée », « surchauffe », « fuite », « jeu », « broute », « claquement », « sifflement », « usure anormale ») **et** qu'aucune entrée `diagnostic_relations[]` ne couvre ce symptôme → `blocked_reasons: [symptom_unstructured]`.

Le rédacteur doit soit retirer la mention textuelle, soit ajouter une entrée structurée correspondante.

### Anti-patterns ADR-033 §D3

| Anti-pattern                                                                                                                                                             | Gate                         |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------- |
| Fichier sous `wiki/systemes/`                                                                                                                                            | `forbidden_systemes_dir`     |
| Fichier `wiki/diagnostic/<symptom>-*.md` matchant regex `(bruit\|grincement\|vibration\|voyant\|fumee\|surchauffe\|fuite\|usure\|symptome\|claquement\|sifflement)-*.md` | `forbidden_per_symptom_file` |
| `diagnostic.symptoms:` dans frontmatter (legacy)                                                                                                                         | `legacy_symptoms_block`      |

> **Note** : Le dossier `wiki/diagnostic/` lui-même reste **autorisé** pour fiches macro-pédagogiques (vocab UI, FAQ, signes diagnostic) per ADR-032 §D1.

### `evidence.diagnostic_safe` (séparation preuve SEO vs preuve diagnostic-live)

| `diagnostic_safe`            | Conséquence                                                                                                                              |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `false` (défaut ADR-033 §D4) | La relation peut enrichir la fiche wiki (SEO/contenu), mais **n'est pas autorisée à influencer le moteur diagnostic LIVE** (`__diag_*`). |
| `true`                       | Autorisé à alimenter le moteur diagnostic. **Flip humain ciblé uniquement** (commit signé reviewer ≠ auteur, cf. ADR-033 critère §9).    |

Le défaut conservateur est non-négociable : pas de flip automatique en bulk possible.

______________________________________________________________________

## §6 — Échantillonnage QA continu

| `risk_level` | Taux d'échantillonnage humain |
| ------------ | ----------------------------- |
| low          | 1-2 %                         |
| medium       | 5 %                           |
| high         | 20 %                          |
| critical     | 100 % ou blocage              |

______________________________________________________________________

## §7 — Promotion automatique `proposals/` → `wiki/<entity_type>/`

Une fiche peut être promue **automatiquement** si **toutes** ces conditions sont vraies :

- `risk_level` ∈ {`low`, `medium`}
- `confidence_score` ≥ 0.85
- `source_refs` ≥ 1 (résolvables)
- frontmatter valide (schema v1.0)
- template complet (sections obligatoires)
- aucune pollution détectée
- aucune contradiction détectée
- aucun contenu catalogue interdit
- aucun contenu contractuel sensible
- aucun diagnostic sécurité critique
- aucune promesse commerciale détectée

**Sinon** : la fiche reste dans `proposals/` avec :

- `status: human_review_required` + `blocked_reasons` rempli, **OU**
- `status: quarantined` (selon gravité, §8)

> *Automatique ne veut pas dire « sans contrôle ».*
> *Automatique veut dire : **contrôlé par des gates, traçable, réversible, avec blocage des cas risqués**.*

Pipeline complet :

```
raw → normalized → proposal → automated quality gates
                                ├── PASS  + low/medium + score ≥ 0.85 → auto_reviewed wiki
                                ├── WARN  + low/medium                → sampled wiki (audit ultérieur)
                                ├── FAIL  ou high/critical            → human_review_required dans proposals/
                                └── pollution / contradiction critique → quarantined dans proposals/
```

______________________________________________________________________

## §8 — Frontmatter post-promotion

```yaml
# Voie automatique (gates §2 PASS, low/medium, score ≥ 0.85)
status: auto_reviewed
review_status: auto_passed
validation_mode: automatic
confidence_score: 0.91
risk_level: medium
blocked_reasons: []
exportable: { rag: false, seo: false, support: false }   # toujours false — Partie 3 décide
```

```yaml
# Voie humaine (critical, blocked, sampling §6)
status: reviewed
review_status: approved
validation_mode: human_required
confidence_score: 0.94
risk_level: high
blocked_reasons: []
reviewer: <handle>
review_date: 2026-04-XX
exportable: { rag: false, seo: false, support: false }
```

> **Mapping legacy → plan rev 6** : le champ `review_status` du schema v1.0 (`draft|proposed|in_review|approved|deprecated`) reste valide pour identifier l'état canonique. Les fiches mergées récemment portent ces deux vocabulaires en parallèle pendant la phase de transition. Cf. `ingestion-contract.md` §"Mapping vocabulaires".

______________________________________________________________________

## §9 — Quarantine `status: quarantined` (frontmatter, pas de move Git)

> **Distinction stricte** :
>
> | Mécanisme                           | Niveau | Contenu               | Localisation physique            |
> | ----------------------------------- | ------ | --------------------- | -------------------------------- |
> | `automecanik-raw/quarantine/`       | RAW    | source brute douteuse | dossier dédié                    |
> | `status: quarantined` (frontmatter) | WIKI   | proposal douteuse     | reste dans `proposals/<slug>.md` |

Une proposal qui échoue gravement reste dans `proposals/<slug>.md` avec `status: quarantined`. Pas de déplacement physique.

```yaml
status: quarantined
review_status: in_review
validation_mode: human_required
blocked_reasons: [pollution_detected, source_conflict]
quarantined_at: 2026-04-29T14:23:00Z
```

Avantages : historique Git linéaire, recovery `quarantined → human_review_required` après correction, compat sampling §6.

______________________________________________________________________

## §10 — Rollback (rétrogradation in-place + audit log JSONL)

Si une fiche promue dans `wiki/<entity_type>/` est ensuite identifiée problématique :

1. **Rétrogradation in-place** (pas de `git revert` — préserve la généalogie) :
   ```yaml
   status: human_review_required
   review_status: in_review
   blocked_reasons: [post_hoc_source_disproven]
   rollback_from_commit: <sha>
   rollback_reason: <free_text_short>
   rollback_at: 2026-04-29T14:23:00Z
   ```
1. **Move Git** : `wiki/<entity_type>/<slug>.md` → `proposals/<slug>.md` (commit *rollback*)
1. **Audit log append-only** dans `_meta/audit-log.jsonl` :
   ```json
   {"ts":"2026-04-29T14:23:00Z","action":"rollback","slug":"plaquette-de-frein","entity_type":"gamme","from_status":"auto_reviewed","to_status":"human_review_required","commit":"<sha>","reason":"source_disproven","actor":"<handle>"}
   ```
1. **CI re-run** : `wiki-quality-gates.yml` ré-évalue depuis `proposals/`.

Idempotent et traçable sans réécrire l'histoire Git.

______________________________________________________________________

## §11 — Export `wiki/` → `exports/{rag,seo,support}/` (Partie 3 — différé)

> **Statut Partie 1+2** : tous les `exportable.*: false` par défaut. Aucun flip autorisé tant que `_scripts/wiki-readiness-check.py` ≠ READY (cf. plan rev 6 §9).

Conditions futures (Partie 3) :

### Export RAG

- `exportable.rag: true`, `truth_level >= L1`, `no_disputed_claims: true`
- Pas de notes internes, pas de promesse commerciale, pas de compatibilité véhicule inventée

### Export SEO

- `exportable.seo: true`, `entity_type` ∈ {gamme, vehicle, constructeur}
- Slug canonique présent dans `_meta/entity-registry.json`
- Intentions SEO documentées (extracted ou inferred)

### Export Support (chatbot)

- `exportable.support: true`
- Contenu sûr pour client final, pas de donnée interne

______________________________________________________________________

## §12 — Enforcement (défense en profondeur)

| Niveau               | Outil                                                                | Trigger              | Effet                                                                                                                           |
| -------------------- | -------------------------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **Local pre-commit** | [`pre-commit`](https://pre-commit.com) via `.pre-commit-config.yaml` | `git commit`         | Refuse commit si gates FAIL                                                                                                     |
| **CI bloquant**      | `.github/workflows/wiki-quality-gates.yml`                           | PR / push branche    | Re-execute gates, bloque merge si FAIL                                                                                          |
| **CI scheduled**     | `.github/workflows/wiki-quality-audit.yml` (P3)                      | Cron lundi 02:00 UTC | Audit complet, rapport `_meta/qa-reports/<date>/`                                                                               |
| **Path protection**  | `.github/workflows/wiki-protected-paths.yml`                         | Tout commit          | Refuse écriture directe `wiki/<entity_type>/` sauf `promotion-from-proposals:`, `rollback:`, `template-migration:` dans message |

______________________________________________________________________

## Référence canon

- ADR-031 — Raw / Wiki / RAG / SEO Separation (vault)
- Plan rev 6 — *verifier-dans-existant-si-starry-feigenbaum* §5, §6, §9
- Skills à réutiliser : `pollution-scanner` (lint read-only), `seo-vault-verify`, `content-quality-gate`
