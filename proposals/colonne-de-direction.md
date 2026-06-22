---
schema_version: 2.0.0
id: gamme:colonne-de-direction
entity_type: gamme
slug: colonne-de-direction
title: Colonne de direction
aliases: [colonne direction, arbre de direction]
lang: fr
created_at: 2026-06-04
updated_at: 2026-06-04

truth_level: L2
source_refs:
  - kind: sources
    origin_repo: automecanik-raw
    origin_path: sources/web-research/colonne-de-direction/selection-criteria.md
    captured_at: 2026-06-04
  - kind: sources
    origin_repo: automecanik-raw
    origin_path: sources/web-research/colonne-de-direction/common-mistakes.md
    captured_at: 2026-06-04
  - kind: sources
    origin_repo: automecanik-raw
    origin_path: sources/web-research/colonne-de-direction/compatibility-technical.md
    captured_at: 2026-06-04
  - kind: sources
    origin_repo: automecanik-raw
    origin_path: sources/web-research/colonne-de-direction/faq-symptoms.md
    captured_at: 2026-06-04
  - kind: sources
    origin_repo: automecanik-raw
    origin_path: sources/web-research/colonne-de-direction/source-index.json
    captured_at: 2026-06-04
provenance:
  ingested_by: 'skill:wiki-proposal-writer@v0.1'
  promoted_from: null

review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: >-
  Matière issue d'une recherche web ciblée (31 sources FR, voir source-index.json du RAW).
  Les slugs sources des diagnostic_relations (web_vroomly_colonne, web_piecesetpneus_colonne,
  web_idgarages_colonne) ne sont PAS encore enregistrés dans _meta/source-catalog.yaml —
  à enregistrer (PR catalogue séparée) avant promotion. evidence.diagnostic_safe reste false
  (famille direction = safety, validation humaine reviewer != auteur requise).
no_disputed_claims: true
confidence_score: 0.48

exportable:
  rag: false
  seo: false
  support: false
target_classes: [KB_Knowledge]

diagnostic_relations:
  - symptom_slug: jeu_volant
    system_slug: direction
    relation_to_part: possible_cause
    part_role: "usure des cardans/roulements de la colonne ou de l'arbre intermédiaire = jeu ressenti au volant"
    evidence:
      confidence: medium
      source_policy: 2_medium_concordant
      reviewed: false
      diagnostic_safe: false
    sources:
      - web_piecesetpneus_colonne
      - web_idgarages_colonne
  - symptom_slug: bruit_direction
    system_slug: direction
    relation_to_part: possible_cause
    part_role: "croisillon/cardan de colonne usé provoque craquements ou grincements en braquant"
    evidence:
      confidence: medium
      source_policy: 2_medium_concordant
      reviewed: false
      diagnostic_safe: false
    sources:
      - web_piecesetpneus_colonne
      - web_vroomly_colonne
  - symptom_slug: direction_lourde
    system_slug: direction
    relation_to_part: symptom_amplifier
    part_role: "défaut du moteur/capteurs EPS intégrés à la colonne peut réduire ou couper l'assistance"
    evidence:
      confidence: medium
      source_policy: 2_medium_concordant
      reviewed: false
      diagnostic_safe: false
    sources:
      - web_idgarages_colonne
      - web_vroomly_colonne

entity_data:
  pg_id: 1211
  family: direction
  intents: [achat, diagnostic, entretien, remplacement]
  vlevel: null
  related_parts: [cremaillere-de-direction, rotule-de-direction, cardan-de-direction]
  maintenance:
    educational_advice: "Faire contrôler tout jeu, bruit ou point dur au volant sans attendre — la colonne est une pièce de sécurité."
    related_pages:
      - cremaillere-de-direction
      - rotule-de-direction
---

# Colonne de direction

## Définition

La colonne de direction relie le volant au boîtier ou à la crémaillère de direction et transmet la rotation du conducteur jusqu'aux roues. Selon le véhicule, elle peut intégrer la direction assistée électrique (EPS), un capteur d'angle de braquage, l'antivol de direction et le contacteur tournant de l'airbag. Son fourreau est conçu pour se rétracter en cas de choc (sécurité passive). [^1]

## Fonctionnement

La rotation du volant est transmise par l'arbre de direction et ses joints de cardan, qui absorbent les variations d'angle jusqu'à la crémaillère. Trois architectures d'assistance coexistent : mécanique (sans assistance), hydraulique (pompe + circuit de fluide) et électrique (EPS). Sur une colonne EPS, un moteur électrique piloté par un calculateur module l'assistance à partir des capteurs de couple et d'angle ; ces composants électroniques ne sont pas interchangeables d'un véhicule à l'autre. [^1][^2]

## Symptômes système auxquels cette pièce peut contribuer

> Cette pièce **peut contribuer** à certains symptômes du système de direction, sans en être systématiquement la cause unique. Le modèle diagnostic complet vit dans la DB `__diag_symptom` et l'outil diagnostic — pas ici.

- 🎯 **Jeu dans le volant** *(possible cause)* — l'usure des cardans ou roulements de la colonne, ou de l'arbre intermédiaire, crée un jeu ressenti au volant [^2][^3]
- 🔊 **Bruits en braquant** *(possible cause)* — un croisillon ou cardan de colonne usé provoque craquements ou grincements lors des manœuvres [^2][^1]
- 🛞 **Direction lourde** *(symptom amplifier)* — un défaut du moteur ou des capteurs EPS intégrés à la colonne peut réduire ou couper l'assistance [^3][^1]

## Conseil pédagogique d'entretien

> Faire contrôler tout jeu, bruit ou point dur au volant sans attendre — la colonne est une pièce de sécurité.

Voir aussi : [[cremaillere-de-direction]], [[rotule-de-direction]].

## Choix selon véhicule

Le choix d'une colonne de direction repose d'abord sur la compatibilité exacte avec le véhicule (marque, modèle, motorisation, année), confirmée idéalement par la référence d'origine du constructeur. Le type d'assistance (mécanique, hydraulique ou électrique EPS) doit correspondre à l'équipement d'origine. Sur les colonnes électriques, il faut vérifier la présence et le type de capteur d'angle, la connectique électrique et l'antivol intégré, autant d'éléments souvent spécifiques au modèle. Selon le besoin, la pièce peut être une colonne complète ou un simple arbre/cardan intermédiaire. Point essentiel : sur une colonne EPS ou équipée d'un capteur d'angle, un calibrage électronique à l'outil de diagnostic est nécessaire après le montage, faute de quoi l'assistance et l'ESP restent défaillants. [^4][^3]

## FAQ

### Comment savoir si une colonne de direction est défectueuse ?

Les contributions les plus fréquentes de la colonne sont un jeu au volant, des bruits en braquant et une direction devenue lourde (voir la section « Symptômes système » ci-dessus). Comme il s'agit d'une pièce de sécurité, un contrôle par un professionnel est recommandé dès l'apparition de ces signes. [^3][^1]

### Quelle différence entre colonne de direction et crémaillère ?

La colonne relie le volant à la crémaillère et transmet la rotation ; un bruit ou un jeu ressenti sous le volant pointe plutôt vers la colonne. La crémaillère, située près du train avant, transforme cette rotation en braquage des roues ; un effort ou un bruit côté avant oriente plutôt vers elle. [^5]

### Peut-on remplacer une colonne de direction soi-même ?

C'est fortement déconseillé : l'opération touche à l'airbag, nécessite la dépose d'éléments d'habitacle et, sur les versions électroniques, un recalibrage du capteur d'angle à l'outil de diagnostic après pose. L'intervention relève d'un professionnel. [^3][^4]

### Faut-il recalibrer le capteur d'angle après le remplacement ?

Oui sur les véhicules concernés : après dépose du volant ou de la colonne, le capteur d'angle doit généralement être recalibré via le système ABS/ESP, sinon un défaut est signalé par le calculateur et l'assistance peut être perturbée. La procédure dépend du constructeur. [^4]

______________________________________________________________________

[^1]: `web_vroomly_colonne` — Vroomly, « Colonne de direction : fonctionnement, entretien et prix » (source `type: external_url`, `confidence: medium`). À enregistrer dans `_meta/source-catalog.yaml` avant promotion.
[^2]: `web_piecesetpneus_colonne` — Pièces et Pneus, « Colonne de direction : détecter jeux et bruits » (source `type: external_url`, `confidence: medium`).
[^3]: `web_idgarages_colonne` — idGarages, « Colonne de direction : rôle, anomalies, changement » (source `type: external_url`, `confidence: medium`).
[^4]: `web_delphi_calibrage_sas` — Delphi, « Calibrage des capteurs d'angle de direction » (source `type: oem_workshop`, `confidence: medium`).
[^5]: `web_powersteeringrack_colonne_vs_cremaillere` — PowerSteeringRack, « Colonne vs crémaillère » (source `type: external_url`, `confidence: medium`).

<!--
Notes rédacteur (à supprimer avant promotion) :
- Sources web (RAW automecanik-raw/sources/web-research/colonne-de-direction/) — 31 sources tracées dans source-index.json.
- Slugs sources à enregistrer dans _meta/source-catalog.yaml (PR catalogue séparée) avant flip exportable.
- Aucun prix / SKU / compatibilité véhicule exacte (gate catalog_leak respecté).
- diagnostic_safe: false sur les 3 relations — famille direction (safety) → validation reviewer != auteur requise (ADR-033 §D4).
-->
