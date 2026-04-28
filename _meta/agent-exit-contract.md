# Contrat de Sortie Obligatoire — Agents & Auto Research

> Regle non-negociable. S'applique a TOUT agent, run, audit, ou analyse.

## Regles fondamentales

1. **Jamais de correction automatique.** Un agent scanne, analyse, propose — il ne modifie RIEN sans validation humaine explicite.
2. **Jamais d'overclaim.** Les phrases "tout scanne/verifie/corrige", "100% couvert", "aucun probleme", "audit complet" (FR/EN) sont **interdites** sans coverage manifest.
3. **Separation obligatoire** de 5 etats dans tout rapport : scan | analysis | correction (proposee) | validation | verdict.

## Statuts autorises / interdits

| Autorises | Interdits |
|-----------|-----------|
| `PARTIAL_COVERAGE` | `PROJECT_FULLY_SCANNED` |
| `SCOPE_SCANNED` | `ALL_FIXED`, `COMPLETE`, `DONE` |
| `REVIEW_REQUIRED` | `NO_ISSUES`, `PATCH_APPLIED` |
| `VALIDATED_FOR_SCOPE_ONLY` | `AUTO_FIXED` |
| `INSUFFICIENT_EVIDENCE` | |

Verdict par defaut = `PARTIAL_COVERAGE` ou `INSUFFICIENT_EVIDENCE`, jamais `COMPLETE`.

Pour declarer `SCOPE_SCANNED` : fournir nombre exact de fichiers lus, repertoires parcourus, exclusions, et au moins 1 evidence par conclusion.

## Coverage manifest obligatoire

Tout run/audit DOIT produire :

```
scope_requested / scope_actually_scanned / files_read_count
excluded_paths / unscanned_zones (OBLIGATOIRE meme si vide)
corrections_proposed (JAMAIS appliquees auto) / validation_executed
remaining_unknowns (OBLIGATOIRE) / final_status (statut autorise)
```

`corrections_applied` doit etre vide/absent sauf validation humaine explicite.

## Reformulation obligatoire

- "Tout scanne" → "Scan du perimetre X termine"
- "Tout corrige" → "N recommandations proposees, en attente de validation humaine"
- "100% couvert" → "Couverture estimee a N% sur le perimetre X"

## Decision Dossiers

Inclure Section 13 (Coverage Manifest) + Section 14 (Exit Conditions). Verdict `PASS` si toutes conditions section 14 cochees.
