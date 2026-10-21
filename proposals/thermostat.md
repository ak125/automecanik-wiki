---
schema_version: 2.0.0
id: gamme:thermostat
entity_type: gamme
slug: thermostat
title: Thermostat
aliases: []
lang: fr
created_at: '2026-05-27'
updated_at: '2026-10-21'
truth_level: L2
source_refs:
- kind: raw
  path: sources/auto-captures/thermostat/hella-com-wl-thermostat-hella-20261021-65248188.md
  cid: sha256:b3bd187cda7333c5fe2b58c28ba2d4c6bb42650763bb20ddc7e9859b946c3fd3
  captured_at: '2026-10-20'
  confidence: medium
provenance:
  ingested_by: codex:wiki-candidates-repair-20261021
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: Réparation candidate 2026-10-21, sans promotion. Ancien contenu et dimensions
  recyclées conservés dans Git 9f63fc49e7d73ea9783256e5671462a61cb5621a:proposals/thermostat.md.
  La matrice de compatibilité et les mentions WEB_CONFIRMS_RAG non étayées sont retirées
  de cette proposition. Capture CAPTURED_NEEDS_REVIEW, licence unknown, aucune validation
  humaine déclarée. La capture décrit le fonctionnement, pas une liste de symptômes
  propres au thermostat. Diagnostic, choix selon véhicule, entretien, FAQ et seconde
  preuve indépendante restent à documenter. Aucun seuil numérique ajouté.
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
  pg_id: 316
  family: refroidissement
  related_parts:
  - radiateur-de-refroidissement
  - pompe-a-eau
  - durite-de-refroidissement
  - vase-d-expansion
  - ventilateur-de-refroidissement
  intents:
  - diagnostic
  - achat
  - compatibilite
  vlevel: V4
  kw_top: []
  references: []
confidence_score: 0.36
---

# Thermostat

## Définition

Le thermostat régule la circulation du liquide de refroidissement en fonction de la température. Il participe à la mise en température du moteur puis au maintien de sa température de fonctionnement. [^source]

## Fonctionnement

Pendant la mise en température, le circuit court permet au liquide de revenir au moteur sans passer par le radiateur. Le thermostat ouvre ensuite le passage vers le radiateur lorsque la température prévue par la conception est atteinte. Le radiateur évacue alors vers l’air la chaleur transportée par le liquide. [^source]

## Place dans le circuit

Le thermostat appartient à un ensemble comprenant notamment la pompe à eau, le radiateur, le vase d’expansion, les conduites et le ventilateur. La description de ce fonctionnement général ne permet pas d’attribuer à lui seul une anomalie de température au thermostat. [^source]

[^source]: HELLA TECH WORLD — [Refroidissement moteur — structure et fonctionnement](https://www.hella.com/techworld/be-fr/technique/refroidissement-du-vehicule/refroidissement-moteur/). Archive RAW : `sources/auto-captures/thermostat/hella-com-wl-thermostat-hella-20261021-65248188.md`. Source pour examen interne ; droits d’usage non confirmés.
