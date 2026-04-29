---
schema_version: 2.0.0
id: gamme:plaquette-de-frein-fixture
entity_type: gamme
slug: plaquette-de-frein-fixture
title: Plaquette de frein
aliases: []
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L2
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/gammes/plaquette-de-frein.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: 'human:fixture'
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: 'Fixture PASS — diagnostic_relations[] sourcé + maintenance bloc présent'
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: [KB_Knowledge]
diagnostic_relations:
  - symptom_slug: bruit_grincement_freinage
    system_slug: freinage
    relation_to_part: possible_cause
    part_role: 'plaquette usée, contaminée ou mal montée'
    evidence:
      confidence: medium
      source_policy: 2_medium_concordant
      reviewed: false
      diagnostic_safe: false
    sources:
      - bosch_fad_2020
      - oem_renault_clio_iii_workshop
entity_data:
  pg_id: 402
  family: freinage
  intents: [diagnostic, achat]
  related_parts: [disque-de-frein]
  maintenance:
    educational_advice: "Vérifier l'épaisseur minimum 3 mm avant un long trajet."
    related_pages: [disque-de-frein]
---

# Plaquette de frein

## Définition

La plaquette de frein est l'élément de friction qui appuie sur le disque pour ralentir le véhicule.

## Fonctionnement

Pression hydraulique → étrier → plaquette → friction sur disque → décélération.

## Symptômes système auxquels cette pièce peut contribuer

> Cette pièce peut contribuer à certains symptômes du système de freinage.

- 🔊 **Bruit de grincement au freinage** *(possible cause)* — usure ou contamination [^1][^2]

## Conseil pédagogique d'entretien

> Vérifier l'épaisseur minimum 3 mm avant un long trajet.

## Choix selon véhicule

Pour un véhicule de plus de 1500 kg, privilégier des plaquettes haute résistance thermique.

## FAQ

### Quand changer ?

Quand l'épaisseur descend sous 3 mm.

[^1]: bosch_fad_2020 — Bosch FAD 2020 p.27
[^2]: oem_renault_clio_iii_workshop — Manuel atelier Renault
