# Règles automecanik-wiki

> Ce repo est la **base de connaissance métier canonique** AutoMecanik.
> Toute action d'agent IA doit respecter les règles ci-dessous.

## Principe fondamental

Tout ce qui est brut par défaut va dans `automecanik-raw`. Seul ce qui sort propre et validé entre dans `automecanik-wiki`.

La validation et la promotion WIKI sont **automatiques**, selon la décision utilisateur du 12 septembre 2026. Le décideur unique est `_scripts/promotion_decision.py` : contrôles satisfaits → éligible ; preuve insuffisante, contradictoire ou vérification indisponible → bloqué. Une validation humaine systématique ne fait plus partie du flux.

## Rôle du LLM

Le LLM peut **proposer, relier, résumer, extraire, enrichir**. La validation relève du moteur déterministe et de ses preuves, jamais de l’auto-déclaration du LLM. Publication externe et validation WIKI sont des opérations distinctes.

## Interdictions absolues

- Écrire dans `wiki/<area>/` uniquement par le promoteur après décision automatique éligible et revérification des entrées
- Écrire d'abord dans `proposals/` (FLAT — routage par frontmatter `entity_type`)
- Ne **jamais** contourner les contrôles pour passer `review_status: approved` ou rendre un contenu exportable
- Ne **jamais** supprimer une source raw
- Ne **jamais** inventer de compatibilité véhicule
- Ne **jamais** transformer une hypothèse en fait
- Ne **jamais** exporter vers RAG / SEO / chatbot sans `_meta/quality-gates.md` PASS
- Ne **jamais** stocker de secret, token, mot de passe, fichier `.env`
- Ne **jamais** modifier `_meta/entity-registry.json` manuellement (passe par `lineage-tracker` skill)

## Workflow standard — UNIFORME pour toutes les entités

### Définir le besoin avant d'extraire

Pour un article général, sélectionner uniquement les faits utiles à l'explication : rôle de la pièce, principes, variantes générales, entretien et critères de choix. Ne pas demander de code moteur, référence OE, diamètre ou couple de serrage si le texte n'en a pas besoin. Ces données restent dans RAW pour la traçabilité et dans le catalogue métier pour leur utilisation applicative.

Une erreur de compatibilité dans un passage RAW non utilisé ne bloque pas une explication indépendante et correctement sourcée. Vérifier les affirmations réellement retenues, avec leur passage source ; ne jamais attribuer une confiance globale à un document composite. Si l'erreur contamine une affirmation publiée ou remet en cause sa preuve, cette affirmation reste bloquée.

Une affirmation précise de compatibilité ou une instruction de montage garde ses contrôles propres. Le titre « éditorial » n'autorise pas à publier une donnée technique non vérifiée. Ne pas ajouter des chiffres, des sections ou des liens seulement pour augmenter un score. Voir `_meta/source-policy.md` §9.3.

Le même flux s'applique à **gammes, vehicles, constructeurs, support, diagnostic** — pas d'exception.

1. Lire la source `automecanik-raw/recycled/...` ou `automecanik-raw/sources/...`
1. Identifier les entités via `_meta/entity-registry.json`
1. Extraire les faits — marquer `extracted` / `inferred` / `ambiguous`
1. Créer ou modifier une fiche dans `proposals/<slug>.md` (FLAT, `entity_type` dans frontmatter)
1. Renseigner `source_refs:` (chemin raw + lineage)
1. Ajouter `lineage_id` (UUIDv7) + `content_hash` (SHA-256 du body)
1. Mettre à jour `index.md`
1. Ajouter une entrée dans `log.md`
1. Soumettre la proposition `in_review` au décideur automatique ; appliquer seulement une décision `ELIGIBLE`, sinon corriger les motifs puis réévaluer

## Note ADR-022 (R8 vehicles) — sujet downstream backend

Le mécanisme `__rag_proposals` (DB Supabase, ADR-022 governance-vault) est une **génération R8** côté backend, **distinct** du flux raw → wiki présent. Son activation est gouvernée par la variable d'environnement `RAG_PROPOSAL_MODE` côté NestJS (lue à `onModuleInit`).

Quand activé, ses sorties merged sont traitées comme **un input parmi d'autres** vers `automecanik-raw/recycled/`, puis suivent le flux uniforme jusqu'à `wiki/vehicles/`. Pas de cas spécial fichier — le sas markdown wiki reste l'unique source de promotion vers `wiki/<entity_type>/`.

## Note ADR-033 (gamme diagnostic_relations) — contrat wiki gamme

Pour `entity_type: gamme` (cf. ADR-033 `accepted` 2026-04-29) :

- Les fiches wiki ne doivent **pas** recréer localement les symptômes — la DB `__diag_symptom` est SoT.
- Les relations diagnostic pointent vers le bloc `diagnostic_relations[]` du frontmatter v2.0.0 (cf. `_meta/schema/frontmatter.schema.json`).
- **Anti-pattern interdit** : `entity_data.symptoms[]` ou `diagnostic.symptoms[]` (ADR-033 §D2). Bloqué par `_scripts/quality-gates.py` `legacy_symptoms_block`.

## Validation automatique

Le promoteur renseigne `review_status: approved`, `validation_mode: automatic`, le validateur, la date et les preuves de décision. Le seuil atteignable est 0.85, avec tous les contrôles obligatoires ; il ne représente pas une probabilité de vérité. Une erreur, une source absente, une régression ou une preuve non vérifiable interdit la promotion. Les cas bloqués restent `in_review`, sans tâche humaine obligatoire.

Le mode `--apply` exécute la décision existante après contrôle de fraîcheur. Il ne contourne aucun contrôle. Les exports conservent leurs contrats propres ; approbation WIKI ne prouve pas publication effective.

> **Note** : les enums `review_status` autorisés sont `draft | proposed | in_review | approved | deprecated`
> (cf. [\_meta/schema/frontmatter.schema.json](_meta/schema/frontmatter.schema.json#L169)). Les anciens
> termes `needs_human_review`, `human_reviewed`, `status: validated` sont désormais interdits — bloqués
> par hook pre-commit `forbid-non-schema-statuses-in-docs` + validateur `_scripts/validate-frontmatter.py`.

## Coverage manifest obligatoire

Tout audit / scan / rapport produit dans ce repo doit suivre `_meta/agent-exit-contract.md` :

- statuts autorisés uniquement (pas de `COMPLETE`, `100%`, `ALL_FIXED`)
- coverage manifest obligatoire (`scope_requested`, `files_read_count`, `excluded_paths`, `unscanned_zones`, `remaining_unknowns`, `final_status`)
- séparation 5 états : scan | analysis | correction (proposée) | validation | verdict

## Skills à réutiliser (pas de duplication)

Avant de créer un nouveau script de lint / quality / extraction, vérifier les skills existants côté monorepo :

- `seo-vault-verify` (SHA256 reproductibilité, cross-refs ADR)
- `rag-lint.py` (validation frontmatter)
- `content-quality-gate` (scoring sections)
- `legacy-recycler` (recycle CSV / blog) — étendu pour `--target=wiki-proposal`
- `kw-classify` (classification keywords)

Étendre l'existant plutôt que créer un 4ème outil concurrent.

## Structure du repo

| Dossier                                                    | Rôle                                                           |
| ---------------------------------------------------------- | -------------------------------------------------------------- |
| `inbox/{web-clips,voice-notes,manual}/`                    | Captures temporaires non canoniques                            |
| `proposals/`                                               | Fiches en cours d'extraction (FLAT, routage par `entity_type`) |
| `wiki/{gammes,vehicles,constructeurs,support,diagnostic}/` | Base canonique validée                                         |
| `maps/`                                                    | MOCs Obsidian par domaine                                      |
| `glossary/`                                                | Atomic notes terminologie/synonymes                            |
| `taxonomy/`                                                | Vocabulaires contrôlés (families, intents, segments)           |
| `_meta/`                                                   | Règles, quality gates, schemas JSON, entity registry           |
| `_meta/schema/`                                            | JSON Schemas pour frontmatter + exports                        |
| `_templates/`                                              | Squelettes Obsidian (Templater compatible)                     |
| `_scripts/`                                                | Scripts repo-local (validate-frontmatter, promote, etc.)       |
| `_audit/`                                                  | Logs de promotions, deprecations, disputes                     |
| `exports/{rag,seo,support}/`                               | Sorties générées (gitignored sauf contrats)                    |

## Référence canon

- **ADR-031** — Raw / Wiki / RAG / SEO Separation (`accepted` 2026-04-28, vault PR #107)
  `ak125/governance-vault/ledger/decisions/adr/ADR-031-raw-wiki-rag-seo-separation.md`
- **ADR-032** — Diagnostic & Maintenance unification (`accepted` 2026-04-29)
  `ak125/governance-vault/ledger/decisions/adr/ADR-032-diagnostic-maintenance-unification.md`
- **ADR-033** — Wiki gamme `diagnostic_relations[]` contract (`accepted` 2026-04-29, vault PR #108)
  `ak125/governance-vault/ledger/decisions/adr/ADR-033-wiki-gamme-diagnostic-relations-contract.md`
