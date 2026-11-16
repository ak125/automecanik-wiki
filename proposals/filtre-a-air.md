---
schema_version: 2.0.0
id: gamme:filtre-a-air
entity_type: gamme
slug: filtre-a-air
title: Filtre à air
aliases:
- filtre à air moteur
- filtre admission
- filtre admission moteur
lang: fr
created_at: '2026-04-29'
updated_at: '2026-10-30'
truth_level: L2
source_refs:
- kind: manual
  note: Données entretien filtres depuis recommandations OEM constructeurs (Renault,
    Peugeot, Bosch). Capture web-clip Phase 7 via preset manuel-constructeur-pdf.
  author: human:@fafa
- kind: raw
  path: recycled/rag-knowledge/_raw/evidence/filtre-a-air.yml
- kind: raw
  path: recycled/rag-knowledge/gammes/filtre-a-air.md
- kind: raw
  path: sources/auto-captures/filtre-a-air/delphiautoparts-com-wl-filtre-a-air-delphi-maf-20261022-7dcb9723.md
  cid: sha256:00e8b895ce2f192c631b2620e0c258eb8ebb626116388b9637f790b931079e0d
  captured_at: '2026-10-21'
  confidence: high
- kind: raw
  path: sources/auto-captures/filtre-a-air/workshop-heroes-mahle-com-wl-filtre-a-air-mahle-turbo-202610-2c6bceb4.md
  cid: sha256:2c31e83dc90db805841b51f74d5249389eed95f13bdbf00bef4f6f6d0f7548f6
  captured_at: '2026-10-21'
  confidence: high
- kind: raw
  path: sources/auto-captures/filtre-a-air/garrettmotion-com-wl-filtre-a-air-garrett-turbo-20261022-66489c27.md
  cid: sha256:18149bcc337dc670a516e25de5aea6ef89db6bc004542ccba2b60ab4086240a3
  captured_at: '2026-10-21'
  confidence: high
- kind: raw
  path: sources/auto-captures/filtre-a-air/hella-com-wl-filtre-a-air-hella-20261022-67bfbd42.md
  cid: sha256:08ae8ce52750d10f3d8ff1a7ce42251d6bbb6203ea8d46a23d913f9227728669
  captured_at: '2026-10-21'
  confidence: medium
provenance:
  ingested_by: human:@fafa
  promoted_from: proposals/filtre-a-air.md
  promoted_at: '2026-06-13T08:16:22+00:00'
review_status: proposed
review_notes: "Pilote G6 ADR-033 — gamme non-safety (family: filtration, risk_level:\
  \ low).\nSert de cas edge pour vérifier que le gate safety_unsourced ne se déclenche\n\
  pas faussement sur une gamme non-safety.\n\nschema_version: 2.0.0 + bloc maintenance\
  \ ADR-032 §D1 (filtre-a-air ∈\nkg_nodes.MaintenanceInterval).\n\n2026-04-30 (P0(b)\
  \ sibling) : retiré diagnostic_relations[] entry car\nsymptom_slug perte_puissance_filtration\
  \ et system_slug filtration crus\nabsents DB.\n\n2026-05-02 (Phase 4 plan deja-verifier-existant)\
  \ — CORRECTION audit DB :\n- Audit MCP supabase confirme filtration system EXISTE\
  \ (id=11, créé\n  migration 20260321_diagnostic_engine_10_systems.sql)\n- perte_puissance_filtration\
  \ EXISTE en __diag_symptom (id=55,\n  signal_mode: customer_reported, urgency: moyenne)\n\
  - L'analyse 2026-04-30 était erronée (pas vérifié DB live). Slug réutilisable.\n\
  - diagnostic_relations[] RÉ-AJOUTÉ avec perte_puissance_filtration\n- Sections H2\
  \ alignées sur ordre canon _templates/new-gamme.md\n  (Définition / Fonction / Symptômes\
  \ d'usure / Critères de choix /\n  Compatibilité véhicule / Intentions SEO observées\
  \ /\n  Questions fréquentes / Sources et provenance / Points à vérifier)\n- aliases\
  \ EN retirés (règle FR exclusif feedback_french_only_for_content.md) :\n  \"air\
  \ filter\" supprimé\n- target_classes étendu KB_Knowledge → KB_Knowledge + KB_Catalog\n\
  - Section \"Conseil pédagogique d'entretien\" intégrée dans\n  \"Critères de choix\"\
  \ (canon ne prévoit pas section dédiée)\n- FAQ étendue de 2 → 5 questions\n\nÀ reviewer\
  \ humainement avant promotion vers wiki/gammes/.\n\nevidence.diagnostic_safe reste\
  \ false (défaut conservateur ADR-033 §D4).\n"
no_disputed_claims: true
exportable:
  rag: false
  seo: true
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
diagnostic_relations:
- symptom_slug: perte_puissance_filtration
  system_slug: filtration
  cause_slug: filtre_air_colmate
  relation_to_part: possible_cause
  part_role: Un filtre à air colmaté ou sale restreint l'air admis ; la perte de puissance
    compte parmi ses signes moteur tournant, et sur moteur suralimenté le turbo ne
    peut plus atteindre la pleine pression de suralimentation.
  evidence:
    confidence: high
    source_policy: 1_high
    reviewed: false
    diagnostic_safe: false
    confidence_score_computed: 0.8
  sources:
  - delphi_filtre_air_debitmetre_20261022
  - mahle_turbo_perte_puissance_20261022
  - garrett_diagnostic_turbo_20261022
  citations:
  - source: delphi_filtre_air_debitmetre_20261022
    start: 2317
    end: 2525
    quote_sha256: sha256:47eb77f23ab00bd2767e28725e43325bc6785c19913cea8883d5942e7a5026b8
  - source: mahle_turbo_perte_puissance_20261022
    start: 2018
    end: 2200
    quote_sha256: sha256:9c71fa20b6f72e6ae14d2ebc47b3d30a420d78fb66c3f1862ad02f98a4641be0
  - source: garrett_diagnostic_turbo_20261022
    start: 3953
    end: 4161
    quote_sha256: sha256:9e867a3039bcd38f9d6f97180934875004ae87e18aab2ed2e4156be5b4c24e11
entity_data:
  pg_id: 8
  family: filtration
  intents:
  - entretien
  - achat
  - remplacement
  vlevel: V3
  related_parts:
  - filtre-d-habitacle
  - filtre-a-huile
  - filtre-a-carburant
  kw_top: []
  maintenance:
    educational_advice: Remplacer au kilométrage préconisé par le carnet d'entretien
      du véhicule, plus souvent en cas de roulage fréquent sur chemins de terre ou de
      gravier, ou en environnement poussiéreux, sableux ou pollué.
    related_pages:
    - filtre-d-habitacle
    - filtre-a-huile
confidence_score: 0.91
revision_of:
  path: wiki/gamme/filtre-a-air.md
  sha256: 3217ce282740ae50f5caadef5b78b9a8fd994680890bf09a926d632440eb8671
---

# Filtre à air

> 📥 **Pilote G6 ADR-033 — cas edge non-safety** (`family: filtration`, `risk_level: low`). Valide que les gates safety ne se déclenchent pas faussement sur une gamme non-safety. Sections H2 ordre canon Phase 4 plan deja-verifier-existant.

## Définition

Le filtre à air est l'élément poreux situé sur le circuit d'admission moteur, retenant les particules solides (poussières, pollen, débris) avant que l'air n'atteigne les chambres de combustion. Pièce d'entretien standard, remplacée à intervalle planifié.

## Fonction

L'air ambiant aspiré par le moteur traverse le filtre dans le boîtier d'admission, qui retient poussière, suie, pollen et débris avant la chambre de combustion [^4]. Sur de nombreux véhicules récents, un débitmètre d'air placé en aval du filtre mesure l'air admis et transmet cette mesure au calculateur, qui dose le carburant pour obtenir le bon mélange air/carburant [^1]. Avec le temps, le filtre se colmate et restreint le passage de l'air : la combustion se dégrade, le moteur perd en vivacité et la consommation de carburant augmente [^4].

## Symptômes d'usure

> Cette pièce **peut contribuer** à certains symptômes du système de filtration, sans en être systématiquement la cause unique. Le modèle diagnostic complet vit dans la DB `__diag_symptom` et l'outil diagnostic — pas ici.

- 🔻 **Perte de puissance moteur** *(possible cause, slug DB `perte_puissance_filtration`)* — la perte de puissance figure parmi les signes, moteur tournant, d'un filtre sale à remplacer [^1]. Sur moteur suralimenté, un filtre colmaté empêche le turbo d'atteindre la pleine pression de suralimentation [^2]. Avant de remplacer un turbo pour manque de puissance, un filtre à air restreint ou bouché fait partie des causes à écarter [^3]

> **Note** : d'autres symptômes liés à la filtration (`surconsommation_carburant` id=56, `odeur_habitacle` id=57) sont présents en DB. La consommation de carburant en hausse est citée comme signe d'un filtre à air sale [^1][^4], mais ce lien n'est pas déclaré en relation diagnostic : deux éditeurs seulement, la règle de relecture en exige trois. Voir [[filtre-d-habitacle]] et [[filtre-a-carburant]] pour ces symptômes.

## Choix selon véhicule

Choisir un filtre correspondant au véhicule : la référence d'origine (OE) figure en général sur la pièce elle-même ou dans les documents du véhicule [^4]. Rouler souvent sur chemins de terre ou de gravier [^1], ou dans un environnement poussiéreux, sableux ou pollué [^4], encrasse le filtre plus vite.

> **Conseil entretien** : remplacer le filtre au kilométrage préconisé dans le carnet d'entretien du véhicule, et plus souvent dans ces conditions sévères [^1][^4]. Les techniciens l'inspectent couramment lors de la vidange [^1].

Filtres « haute performance » à revêtement huilé : l'équipementier conseille de les éviter, car le débitmètre d'air placé en aval du filtre est sensible à la moindre trace de saleté, d'huile ou de poussière [^1].

## Compatibilité véhicule

Pour vérifier la compatibilité filtre à air ↔ véhicule, utiliser le sélecteur sur le site (sélection marque/modèle/année/motorisation) ou interroger la base `__seo_pg_aliases` (référence : `pg_id: 8`).

Pièces complémentaires fréquemment associées au programme entretien filtration :

- [[filtre-d-habitacle]] — filtre poussières/pollen circuit ventilation cabine
- [[filtre-a-huile]] — filtre lubrification moteur
- [[filtre-a-carburant]] — filtre injection essence/diesel

## Intentions SEO observées

`entity_data.intents` : `entretien`, `achat`, `remplacement` (3 intents → fiche entretien planifié).

`vlevel: V3` (top intent : entretien planifié, volume de recherche modéré, peu de diagnostic).

`kw_top` : à compléter Phase 5 via DB `__seo_keywords` queries scopées sur la famille `filtration` + intents listés.

## FAQ

### À quelle fréquence remplacer le filtre à air ?

Au kilométrage préconisé dans le carnet d'entretien du véhicule, et plus souvent en cas de roulage fréquent sur chemins de terre ou de gravier [^1] ou en conditions sévères (poussière, sable, pollution) [^4]. Les sources citées ne donnent pas de kilométrage chiffré commun à tous les véhicules.

### Peut-on nettoyer un filtre à air au lieu de le remplacer ?

Les sources citées parlent de remplacement, pas de nettoyage : remplacer le filtre au kilométrage du carnet d'entretien, ou plus tôt en conditions sévères [^1][^4]. Pour les filtres « haute performance » à revêtement huilé, voir la mise en garde de la section [Choix selon véhicule](#choix-selon-véhicule).

### Quels sont les symptômes d'un filtre à air encrassé ?

Une inspection visuelle montre si le filtre est sale. Moteur tournant, la source cite notamment la consommation de carburant en hausse et la perte de puissance [^1]. Sur moteur turbo, la pression de suralimentation n'atteint plus son maximum [^2]. Voir [Symptômes d'usure](#symptômes-dusure) pour le détail.

### Est-il dangereux de rouler avec un filtre à air encrassé ?

Les sources citées ne traitent pas de la sécurité routière. Elles décrivent des effets mécaniques : un filtre sale ou de mauvaise qualité peut laisser passer des contaminants qui abîment le débitmètre d'air [^1] ; sans filtration suffisante, poussière et débris peuvent endommager des pièces internes du moteur, comme les parois des cylindres [^4] ; sur moteur turbo, remplacer régulièrement le filtre aide à éviter des dommages coûteux au compresseur causés par des corps étrangers [^2]. À traiter dans le cadre de l'entretien planifié.

### Quelle différence entre filtre à air moteur et filtre habitacle ?

- **Filtre à air moteur** (cette fiche) : retient les particules dans l'air aspiré par le moteur pour la combustion.
- **Filtre d'habitacle** ([[filtre-d-habitacle]]) : retient les particules dans l'air ventilé dans la cabine pour les passagers.

Deux pièces distinctes, chacune avec son propre intervalle de remplacement dans le carnet d'entretien.

## Sources et provenance

Voir `source_refs` dans le frontmatter pour la provenance : quatre captures RAW du 2026-10-21 et la compilation manuelle d'origine.

Sources des notes (fiches au catalogue `_meta/source-catalog.yaml`) :

[^1]: `delphi_filtre_air_debitmetre_20261022` — Delphi Technologies, protéger le débitmètre d'air (MAF) par un filtre à air propre. Source `type: oem_manual`.
[^2]: `mahle_turbo_perte_puissance_20261022` — MAHLE Aftermarket, pourquoi un turbocompresseur perd de la puissance. Source `type: oem_manual`.
[^3]: `garrett_diagnostic_turbo_20261022` — Garrett Motion, diagnostic d'un turbocompresseur avant remplacement. Source `type: oem_workshop`.
[^4]: `hella_techworld_filtres_air_gamme_20261022` — HELLA TECH WORLD, page de gamme filtres à air. Source `type: marketing` : corroboration, jamais preuve seule.

Les deux sources de la version précédente (`oem_filter_maintenance_general`, `bosch_fad_2020`) n'ont jamais été capturées ; elles ne sont plus citées.

## Points à vérifier

- [x] **2026-10-30** : `entity_data.pg_id` corrigé de 510 en 8 (lecture `pieces_gamme`, alias `filtre-a-air`)
- [ ] Confirmer `vlevel: V3` (vérifier `r7-curation-method.md` vault)
- [ ] Compléter `aliases` si autres variantes commerciales (FR uniquement — règle `feedback_french_only_for_content.md`)
- [x] **2026-05-02** : `diagnostic_relations[]` ré-ajouté avec `perte_puissance_filtration` (slug DB existant id=55, audit MCP supabase confirmé ; correction de l'analyse erronée du 2026-04-30)
- [x] **2026-10-30** : sources remplacées par quatre captures RAW (Delphi, MAHLE, Garrett, HELLA) ; `oem_filter_maintenance_general` et `bosch_fad_2020`, jamais capturées, ne sont plus citées
- [ ] Compléter `entity_data.kw_top` via DB `__seo_keywords` (scope famille `filtration` + intents)
- [x] `_coverage/filtre-a-air.coverage.yaml` : chaque affirmation sourcée y est reliée à sa source
- [ ] Décider promotion → `wiki/gammes/filtre-a-air.md` (commit message obligatoire `promotion-from-proposals: filtre-a-air`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
- [ ] Flip humain ciblé `evidence[*].diagnostic_safe: true` reste interdit tant que les sources ne sont pas corroborées par OEM (commit signé reviewer ≠ auteur, ADR-033 §D4)
