---
schema_version: 2.0.0
id: gamme:vanne-egr
entity_type: gamme
slug: vanne-egr
title: Vanne EGR
aliases: []
lang: fr
created_at: '2026-05-27'
updated_at: '2026-10-21'
truth_level: L2
source_refs:
- kind: raw
  path: sources/auto-captures/vanne-egr/hella-com-wl-vanne-egr-hella-techworld-20261021-f554b26e.md
  cid: sha256:c5677fb24a31ddd751268b856812e5920d908cb501d8790499b03277f88e3907
  captured_at: '2026-10-20'
  confidence: medium
provenance:
  ingested_by: codex:wiki-candidates-repair-20261021
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: Réparation candidate 2026-10-21, sans promotion. Ancien contenu et dimensions
  recyclées conservés dans Git 9f63fc49e7d73ea9783256e5671462a61cb5621a:proposals/vanne-egr.md.
  La matrice de compatibilité et les mentions WEB_CONFIRMS_RAG non étayées sont retirées
  de cette proposition. Capture CAPTURED_NEEDS_REVIEW, licence unknown, aucune validation
  humaine déclarée. Une seconde preuve indépendante, les droits d’usage, les critères
  de choix et les symptômes contextualisés restent à qualifier. Aucune relation diagnostic
  DB ni compatibilité précise ajoutée.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
diagnostic_relations: []
entity_data:
  pg_id: 1145
  family: alimentation
  related_parts:
  - catalyseur
  - fap
  - silencieux
  - sonde-lambda
  - tube-d-echappement
  - collecteur-d-echappement
  intents:
  - diagnostic
  - achat
  - compatibilite
  vlevel: V4
  kw_top: []
  references: []
confidence_score: 0.36
---

# Vanne EGR

## Définition

La vanne EGR règle le passage d’une partie des gaz d’échappement vers l’admission. Ce recyclage contribue à réduire la formation d’oxydes d’azote en abaissant la température de combustion. [^source]

## Fonctionnement

Dans un système EGR externe, une conduite relie l’échappement à l’admission. La vanne en commande le passage. Selon la conception, elle est actionnée par dépression ou électriquement ; certains dispositifs transmettent aussi leur position au calculateur. [^source]

## Conseil pédagogique d’entretien

Le contrôle doit porter sur le système et ses raccordements. Les valeurs et les branchements de contrôle dépendent du véhicule : les exemples généraux de la documentation ne remplacent pas ses données techniques. [^source]

[^source]: HELLA TECH WORLD — [Recirculation des gaz d’échappement — structure et diagnostic](https://www.hella.com/techworld/be-fr/technique/electricite-et-electronique/recyclage-des-gaz-d-echappement/). Archive RAW : `sources/auto-captures/vanne-egr/hella-com-wl-vanne-egr-hella-techworld-20261021-f554b26e.md`. Source pour examen interne ; droits d’usage non confirmés.
