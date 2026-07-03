# GAP-1 — pipeline d'authoring automatique + auto-review déterministe (pilote disque-de-frein)

> **Shadow-only, report-only. 0 mutation `proposals/` ou `source-catalog.yaml`, 0 LLM, 0 DB, 0 promotion.**
> Décision owner 2026-07-02 : GAP-1 = **production automatique contrôlée + auto-review déterministe**,
> l'humain = fallback d'exception gouvernance (ADR-091 sécurité). PAS de reconstruction humaine comme méthode.

## Chaîne (réutilise les gates existants — verify-before-invent)

```
RAW OE buckets → author_from_raw → gen_coverage_map → [shadow_score 088 · check-coverage-map 089 ·
quality-gates] → gap1_auto_review (verdict + garde sécurité 091)
```

Nouveaux modules (`_scripts/`) ; **rien de réimplémenté** (scorer/validateur/promote/safety = existants) :

| module                | rôle                                                                                                   | invariants                                                                                                                                                                                           |
| --------------------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `author_from_raw.py`  | buckets OE `## Faits sourcés` → body H2 + `entity_data.editorial` + `related_gammes`/`commerce_intent` | 0 LLM, 0 invention (structuration de faits sourcés), aspect→section CONTRÔLÉ (fail-closed), `truth_level: sourced`, ne touche PAS `review_status`/`exportable`, `related_gammes` ∩ manifest committé |
| `gen_coverage_map.py` | coverage-map candidate 2-tiers + cap page-level                                                        | **Option A** : source FK à catalog EXISTANT → entrée valide ; source inconnue → `pending_source_validation`. **Durcissement page-level** ci-dessous                                                  |
| `gap1_auto_review.py` | driver : authoring→coverage→gates→verdict                                                              | report-only, shadow dir temporaire, verdict encode ADR-091 (sécurité → jamais auto)                                                                                                                  |

## Politique de preuve dim A — publisher-level ≠ page-level (durcissement owner 2026-07-03)

- **publisher-level** valide l'**autorité de l'éditeur** (Brembo, ATE, Textar… = fiable).
- **page-level** valide la **preuve du claim** (page/doc précis capturé + claim ancré).
- Un publisher validé n'accorde PAS `high` claim-par-claim. `claim_confidence_cap` :

| état source                                                 | confidence      | source_policy         | compte dim A                         |
| ----------------------------------------------------------- | --------------- | --------------------- | ------------------------------------ |
| publisher validé + page `captured`/`verified` + text_anchor | `high` possible | `1_high`              | fort                                 |
| publisher validé mais page `pending_capture`                | `medium` MAX    | `2_medium_concordant` | report-only (medium)                 |
| source inconnue                                             | —               | —                     | exclue (`pending_source_validation`) |

## Résultat pilote — disque-de-frein (famille freinage, sécurité)

| dim                 | avant (origin/main) |       après (auto)        | source                                                                                                                                                           |
| ------------------- | :-----------------: | :-----------------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A (preuve/coverage) |        0 ❌         |          **18**           | 27 entrées via 2 autorités OEM validées (Brembo/Delphi) — mais pages `to_capture` → **cappées `medium`** (page non prouvée) ; `check-coverage-map --strict` PASS |
| C (editorial)       |        0 ❌         |         **16.7**          | 5 sections authored depuis buckets OE (schema-valid)                                                                                                             |
| D (commerce)        |        0 ❌         |          **15**           | 7 `related_gammes` freinage (manifest-validées) + `commerce_intent`                                                                                              |
| E / F               |       10 / 1        |          10 / 1           | inchangé                                                                                                                                                         |
| **total / tier**    |     **14 / D**      |        **76 / B**         | plancher `A<22` KO (attendu : preuve page pending)                                                                                                               |
| **VERDICT**         |          —          | **`safety_auto_blocked`** | Safety Auto-Gate KO (raisons TECHNIQUES : `dim_A_floor`, `page_level_all_captured`, `no_pending_source_validation`) — PAS un besoin humain                       |

Le score **n'est PAS gonflable par une autorité trop large** : avant durcissement il montait à 91/S (dim A 30) en
traitant à tort la réutilisation publisher comme `high` ; après durcissement il tombe honnêtement à **76/B, dim A 18**,
plancher A non franchi. **Chemin légitime vers dim A fort = capturer/archiver les pages OE précises** (page-level),
alors la confidence peut passer `high`.

Option A en action : **33 sources restent `pending_source_validation`** (12 proposées `équipementier_oem` :
textar/ferodo/ate/trw/hella ; 21 `unknown` : amazon/autodoc/forums) → **ne comptent pas** pour dim A. Validation
d'autorité = **1×/source**, écrite proprement dans `source-catalog.yaml` par un humain (jamais déduite par le pipeline),
puis réutilisée sur toute la famille freinage.

## Safety Auto-Gate — supprimer le goulot humain PROPREMENT (décision owner 2026-07-03)

`human_review` n'est PLUS un état cible du pipeline. Le blocage sécurité est désormais :

- **`safety_auto_blocked`** — raisons TECHNIQUES (page non capturée, source pending, plancher KO) → la machine
  dit « capture les pages OE, je re-score », **aucun humain requis**. (← disque aujourd'hui)
- **`safety_blocked_pending_gate_buildout`** — conditions du gate cible (disputed-claims, regression…) pas encore câblées (fail-closed).
- **`blocked_by_current_safety_policy`** — Safety Auto-Gate PASS mais ADR-091 impose ENCORE une revue → à lever
  par **amendement vault ADR-091** (Safety Auto-Gate), **jamais par contournement code** (flag `--adr091-amended`, défaut FALSE).
- **`safety_auto_approved`** — gate PASS + ADR-091 amendé.

**Safety Auto-Gate = conditions strictes** (câblées ✅ / à câbler ⏳, fail-closed) : ✅ `dim_A_floor` · ✅ `dim_C_floor`
· ✅ `page_level_all_captured` · ✅ `no_pending_source_validation` · ⏳ `coverage_strict_pass` · ⏳ `no_quality_gate_fail`
· ⏳ `no_disputed_claims` · ⏳ `diagnostic_safe` · ⏳ `regression_gate_pass` · ✅ `rollback_available`.

**Le code ne supprime PAS la revue sécurité en douce** : tant que ADR-091 n'est pas amendé au vault (PR G3 signée
owner), un fiche sécurité qui passerait le gate reste `blocked_by_current_safety_policy` — jamais `safety_auto_approved`.
La suppression du human spot-check se fait au niveau de la RÈGLE (amendement ADR-091 = PR vault séparée), pas du code.

## Honnêteté

1. **tier B = score structurel shadow, PAS « publiable »** : fiche reste `review_status: proposed`,
   `exportable.seo: false` ; contenu = **structuration déterministe** de faits sourcés (`truth_level: sourced`),
   pas de prose humaine-polie — LLM-polish **NO-GO** (owner 2026-07-03), à tester en couche séparée plus tard.
1. **Pré-existant, orthogonal** : `quality-gates` FAIL (`source_unresolved:pieces_marque_oes_catalog_db`) + WARN
   pollution (Brembo/Textar) existent DÉJÀ sur `origin/main:disque-de-frein` (body #71, 39 mentions de marques) —
   non introduits par le pipeline ; l'auto-review les remonte (actionnable).

## Invariants / rollback

- shadow-only : aucun fichier `proposals/` ou `_meta/source-catalog.yaml` muté ; le pilote écrit dans un dossier
  temporaire hors-repo. **Rollback = `git revert`** (0 effet runtime, 0 promotion).
- sécurité freinage : `review_status: proposed` maintenu ; verdict = **Safety Auto-Gate** (technique) ou
  `blocked_by_current_safety_policy` (gouvernance) — **jamais un goulot humain**. Zéro-humain sécurité =
  **amendement vault ADR-091**, jamais contournement code (`--adr091-amended` défaut FALSE).
- tests : `_scripts/tests/test_gap1_pipeline.py` (14 tests, auto-collectés par `wiki-quality-gates.yml`) —
  static no-LLM/no-DB, fail-closed aspect, editorial sourcé, no-promote, déterminisme, Option A (inconnu=pending),
  cap page-level (pending→medium / captured→high), related_gammes ∩ manifest, sécurité détectée, **0 verdict humain**,
  `safety_auto_blocked` sur page pending.

## Suite (owner-gated)

1. Valider 1× les publishers officiels proposés (textar/ferodo/ate/trw-zf/hella) **dans `source-catalog.yaml`**
   (domaine officiel + page technique réelle + capturable ; pas marketplace/forum/blog/revendeur).
1. **Capturer/archiver** les pages OE précises (`status: captured`) → confidence `high` → dim A franchit son plancher
   honnêtement, sans autorité trop large.
1. LLM-polish = **NO-GO** maintenant ; couche séparée plus tard (diff strict : 0 claim / 0 source_id / 0 fait modifiés).
1. **GAP-2 reste NO-GO.**
