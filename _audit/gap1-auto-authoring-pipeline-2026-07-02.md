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

| module | rôle | invariants |
|---|---|---|
| `author_from_raw.py` | buckets OE `## Faits sourcés` → body H2 + `entity_data.editorial` + `related_gammes`/`commerce_intent` | 0 LLM, 0 invention (structuration de faits sourcés), aspect→section CONTRÔLÉ (fail-closed), `truth_level: sourced`, ne touche PAS `review_status`/`exportable`, `related_gammes` ∩ manifest committé |
| `gen_coverage_map.py` | coverage-map candidate 2-tiers | **Option A** : source FK à catalog EXISTANT → entrée valide (compte dim A) ; source inconnue → `pending_source_validation` (liste + type proposé, NE compte pas, jamais écrite au catalog). `1_high` seulement si type catalog autoritaire |
| `gap1_auto_review.py` | driver : authoring→coverage→gates→verdict | report-only, shadow dir temporaire, verdict encode ADR-091 (sécurité → jamais auto) |

## Résultat pilote — disque-de-frein (famille freinage, sécurité)

| dim | avant (origin/main) | après (auto) | source |
|---|:-:|:-:|---|
| A (preuve/coverage) | 0 ❌ | **30** | 27 entrées via **2 autorités OEM déjà validées** (Brembo, Delphi — validées 1× pour plaquette, réutilisées) ; `check-coverage-map --strict` PASS |
| C (editorial) | 0 ❌ | **16.7** | 5 sections authored depuis buckets OE (schema-valid) |
| D (commerce) | 0 ❌ | **15** | 7 `related_gammes` freinage (manifest-validées) + `commerce_intent` |
| E / F | 10 / 1 | 10 / 1 | inchangé |
| **total / tier** | **14 / D** | **91 / S** | tous planchers OK |
| **VERDICT** | — | **`human_spot_check_required`** | **TIER S SÉCURITÉ → ADR-091, jamais auto** |

Option A en action : **33 sources restent `pending_source_validation`** (12 proposées `équipementier_oem` :
textar/ferodo/ate/trw/hella ; 21 `unknown` : amazon/autodoc/forums) → **ne comptent pas** pour dim A.
Aucun forum promu en OE. Validation d'autorité = **1×/source**, ensuite réutilisée sur toute la famille freinage.

## Honnêteté (ne pas surinterpréter le tier S)

1. **tier S = score structurel** (dims remplies), **PAS « publié »** : la fiche reste `review_status: proposed`,
   `exportable.seo: false` ; la promotion sécurité reste **humaine** (verdict). Le contenu est une **structuration
   déterministe** de faits sourcés (`truth_level: sourced`), pas de la prose humaine-polie — décision LLM-polish
   = **après**, sur données.
2. **dim A** repose sur la réutilisation d'autorité au niveau **publisher** (Brembo/Delphi), `source_status:
   pending_capture` pour les pages disque non capturées individuellement. Intention owner (anti-goulot), transparent.
3. **Pré-existant, orthogonal** : `quality-gates` FAIL (`source_unresolved:pieces_marque_oes_catalog_db`) + WARN
   pollution (Brembo/Textar) existent DÉJÀ sur `origin/main:disque-de-frein` (body #71, 39 mentions de marques) —
   non introduits par le pipeline ; l'auto-review les remonte (actionnable).

## Invariants / rollback

- shadow-only : aucun fichier `proposals/` ou `_meta/source-catalog.yaml` muté ; le pilote écrit dans un dossier
  temporaire hors-repo. **Rollback = `git revert`** (0 effet runtime, 0 promotion).
- sécurité freinage : `review_status: proposed` maintenu, `human_spot_check` (ADR-091). Option B (zéro-humain
  sécurité) = **amendement vault**, jamais contournement code.
- tests : `_scripts/tests/test_gap1_pipeline.py` (9 tests, auto-collectés par `wiki-quality-gates.yml`) —
  static no-LLM/no-DB, fail-closed aspect, editorial sourcé, no-promote, déterminisme, Option A (inconnu=pending /
  catalogué=réutilisé), related_gammes ∩ manifest, sécurité détectée.

## Suite (owner-gated)

1. Valider 1× les sources OE proposées (textar/ferodo/ate/trw/hella) → dim A monte sans nouvelle curation.
2. Décision **LLM-polish** (qualité prose editorial) = evidence-based, après ce pilote déterministe.
3. Étendre aux autres gammes à buckets OE (colonne-de-direction après création proposal). **GAP-2 reste NO-GO.**
