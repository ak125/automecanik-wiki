# Rules — Agent Exit Contract (AEC)

> **Source de vérité canonique** — règles obligatoires de sortie pour TOUT agent, run, audit, ou analyse au 2026-04-28.
> **Version** : 1.0.0 | **Status** : CANON
> **Taxonomie** : règle transverse — s'applique avant les règles spécifiques de domaine (T*, G*, Q*, AP*).

Ce fichier est l'**unique source canonique** du contrat de sortie. Toutes les copies dans les repos applicatifs (`automecanik-wiki/_meta/agent-exit-contract.md`, `automecanik-raw/agent-exit-contract.md`, `nestjs-remix-monorepo/.claude/canon-mirrors/agent-exit-contract.md`, `nestjs-remix-monorepo/workspaces/seo-batch/.claude/canon-mirrors/agent-exit-contract.md`, `nestjs-remix-monorepo/workspaces/marketing/.claude/canon-mirrors/agent-exit-contract.md`) sont des **dérivées vérifiées par hash SHA-256** (cf §"Distribution canonique" plus bas).

---

## Règles fondamentales

1. **Jamais de correction automatique.** Un agent scanne, analyse, propose — il ne modifie RIEN sans validation humaine explicite.
2. **Jamais d'overclaim.** Les phrases "tout scanné/vérifié/corrigé", "100% couvert", "aucun problème", "audit complet" (FR/EN) sont **interdites** sans coverage manifest.
3. **Séparation obligatoire** de 5 états dans tout rapport : `scan` | `analysis` | `correction (proposée)` | `validation` | `verdict`.

## Statuts autorisés / interdits

| Autorisés | Interdits |
|-----------|-----------|
| `PARTIAL_COVERAGE` | `PROJECT_FULLY_SCANNED` |
| `SCOPE_SCANNED` | `ALL_FIXED`, `COMPLETE`, `DONE` |
| `REVIEW_REQUIRED` | `NO_ISSUES`, `PATCH_APPLIED` |
| `VALIDATED_FOR_SCOPE_ONLY` | `AUTO_FIXED` |
| `INSUFFICIENT_EVIDENCE` | |

Verdict par défaut = `PARTIAL_COVERAGE` ou `INSUFFICIENT_EVIDENCE`, jamais `COMPLETE`.

Pour déclarer `SCOPE_SCANNED` : fournir nombre exact de fichiers lus, répertoires parcourus, exclusions, et au moins 1 evidence par conclusion.

## Coverage manifest obligatoire

Tout run/audit DOIT produire :

```
scope_requested / scope_actually_scanned / files_read_count
excluded_paths / unscanned_zones (OBLIGATOIRE même si vide)
corrections_proposed (JAMAIS appliquées auto) / validation_executed
remaining_unknowns (OBLIGATOIRE) / final_status (statut autorisé)
```

`corrections_applied` doit être vide/absent sauf validation humaine explicite.

## Reformulation obligatoire

- "Tout scanné" → "Scan du périmètre X terminé"
- "Tout corrigé" → "N recommandations proposées, en attente de validation humaine"
- "100% couvert" → "Couverture estimée à N% sur le périmètre X"

## Decision Dossiers

Inclure Section 13 (Coverage Manifest) + Section 14 (Exit Conditions). Verdict `PASS` si toutes conditions section 14 cochées.

---

## Distribution canonique

Ce fichier est la **source unique**. Les copies dans les repos applicatifs sont synchronisées via mécanisme `canon-publish` :

1. **Source de vérité** : ce fichier (`governance-vault/ledger/rules/rules-agent-exit-contract.md`)
2. **Hash SHA-256 publié** : `99-meta/canon-hashes.json` clé `aec` (à créer Phase B.1.b)
3. **Copies dérivées dans les repos applicatifs** (sous `.claude/canon-mirrors/`
   pour ne pas être chargées comme rules Claude Code) :
   - `automecanik-wiki/_meta/agent-exit-contract.md`
   - `automecanik-raw/agent-exit-contract.md`
   - `nestjs-remix-monorepo/.claude/canon-mirrors/agent-exit-contract.md`
   - `nestjs-remix-monorepo/workspaces/seo-batch/.claude/canon-mirrors/agent-exit-contract.md`
   - `nestjs-remix-monorepo/workspaces/marketing/.claude/canon-mirrors/agent-exit-contract.md`
4. **Vérification CI** : chaque repo applicatif inclut un workflow `agent-exit-contract-hash.yml` qui compare le hash de sa copie locale vs `99-meta/canon-hashes.json` (via `gh api`)
5. **Mise à jour** : modification de ce fichier → workflow `canon-publish.yml` (à créer Phase B.1.c) ouvre une PR auto dans chaque repo applicatif pour resync. Auto-merge avec label `canon-sync` autorisé.

## Versionnage

Bump majeur (X.0) = nouvelle règle ou statut interdit ajouté. Bump mineur (X.Y) = clarification / précision. Bump patch (X.Y.Z) = typo / formatting.

| Version | Date | Changements |
|---|---|---|
| 1.0.0 | 2026-04-28 | Canonisation depuis copies orphelines monorepo + seo-batch (drift constaté empiriquement). Ajout §"Distribution canonique". |
| 1.0.1 | 2026-05-04 | Patch path : copies monorepo relocalisées de `.claude/rules/` vers `.claude/canon-mirrors/` pour ne pas alourdir le contexte projet Claude Code (~2.5K tokens/tour). Aucune règle modifiée, hash recalculé. |

## Référence

- ADR-031 — Raw / Wiki / RAG / SEO Separation (à créer post-Phase C)
- `rules-engineering-quality.md` (Q1-Q4 — solution structurelle vs bricolage)
- `rules-ai-antipatterns.md` (AP-* — anti-patterns IA)
- `rules-governance-process.md` (G5-G8 — processus)
