# Quality Gates

> Conditions obligatoires avant promotion d'une fiche `proposals/` → `wiki/`,
> et avant export `wiki/` → `exports/`.

## Promotion `proposals/` → `wiki/`

Une fiche peut être promue uniquement si :

- `review_status: human_reviewed`
- Frontmatter complet : `title`, `slug`, `entity_type`, `status`, `truth_level`, `source_refs`, `provenance`
- `source_refs:` non vide et chemins vérifiables sous `automecanik-raw/`
- `truth_level: L1` minimum (sourced)
- Aucune contradiction non marquée
- Slug unique dans `_meta/entity-registry.json`

## Export `wiki/` → `exports/rag/`

Autorisé uniquement si :

- `exportable.rag: true` (positionné par humain)
- `truth_level >= L1`
- `no_disputed_claims: true`
- Pas de notes internes
- Pas de promesse commerciale non validée
- Pas de compatibilité véhicule inventée

## Export `wiki/` → `exports/seo/`

Autorisé uniquement si :

- `exportable.seo: true` (positionné par humain)
- `entity_type` valide (gamme, vehicle, constructeur)
- Slug canonique présent dans `_meta/entity-registry.json`
- Intentions SEO documentées (extracted ou inferred)
- Pas de duplication massive cross-fiches

## Export `wiki/` → `exports/support/` (chatbot)

Autorisé uniquement si :

- `exportable.support: true` (positionné par humain)
- Contenu sûr pour client final
- Pas de promesse commerciale non validée
- Pas de compatibilité véhicule inventée
- Pas de donnée interne (paths, IDs internes, etc.)

## Réutilisation des skills existants

Plutôt que créer de nouveaux outils, étendre :

- `seo-vault-verify` (audit reproductible vault, SHA256, cross-refs ADR)
- `content-quality-gate` (scoring sections, verdicts WRITE/REVIEW/BLOCK)
- `rag-lint.py` (validation frontmatter)
- `v5-guardian` (anti-régression pipeline)

Voir `CLAUDE.md` §"Skills à réutiliser".
