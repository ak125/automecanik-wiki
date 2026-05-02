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
updated_at: '2026-05-02'
truth_level: L2
source_refs:
- kind: manual
  note: Données entretien filtres depuis recommandations OEM constructeurs (Renault,
    Peugeot, Bosch). Capture web-clip Phase 7 via preset manuel-constructeur-pdf.
  author: human:@fafa
provenance:
  ingested_by: human:@fafa
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: |
  Pilote G6 ADR-033 — gamme non-safety (family: filtration, risk_level: low).
  Sert de cas edge pour vérifier que le gate safety_unsourced ne se déclenche
  pas faussement sur une gamme non-safety.

  schema_version: 2.0.0 + bloc maintenance ADR-032 §D1 (filtre-a-air ∈
  kg_nodes.MaintenanceInterval).

  2026-04-30 (P0(b) sibling) : retiré diagnostic_relations[] entry car
  symptom_slug perte_puissance_filtration et system_slug filtration crus
  absents DB.

  2026-05-02 (Phase 4 plan deja-verifier-existant) — CORRECTION audit DB :
  - Audit MCP supabase confirme filtration system EXISTE (id=11, créé
    migration 20260321_diagnostic_engine_10_systems.sql)
  - perte_puissance_filtration EXISTE en __diag_symptom (id=55,
    signal_mode: customer_reported, urgency: moyenne)
  - L'analyse 2026-04-30 était erronée (pas vérifié DB live). Slug réutilisable.
  - diagnostic_relations[] RÉ-AJOUTÉ avec perte_puissance_filtration
  - Sections H2 alignées sur ordre canon _templates/new-gamme.md
    (Définition / Fonction / Symptômes d'usure / Critères de choix /
    Compatibilité véhicule / Intentions SEO observées /
    Questions fréquentes / Sources et provenance / Points à vérifier)
  - aliases EN retirés (règle FR exclusif feedback_french_only_for_content.md) :
    "air filter" supprimé
  - target_classes étendu KB_Knowledge → KB_Knowledge + KB_Catalog
  - Section "Conseil pédagogique d'entretien" intégrée dans
    "Critères de choix" (canon ne prévoit pas section dédiée)
  - FAQ étendue de 2 → 5 questions

  À reviewer humainement avant promotion vers wiki/gammes/.

  evidence.diagnostic_safe reste false (défaut conservateur ADR-033 §D4).
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
diagnostic_relations:
- symptom_slug: perte_puissance_filtration
  system_slug: filtration
  relation_to_part: possible_cause
  part_role: 'perte de puissance moteur progressive — filtre à air colmaté
    réduisant le débit d''admission, dégradant la combustion. Symptôme typique
    après dépassement intervalle entretien ou usage en milieu poussiéreux.'
  evidence:
    confidence: medium
    source_policy: 2_medium_concordant
    reviewed: false
    diagnostic_safe: false
    confidence_score_computed: 0.6
  sources:
  - oem_filter_maintenance_general
  - bosch_fad_2020
entity_data:
  pg_id: 510
  family: filtration
  intents:
  - entretien
  - achat
  - remplacement
  vlevel: V3
  related_parts:
  - filtre-habitacle
  - filtre-a-huile
  - filtre-a-carburant
  kw_top: []
  maintenance:
    educational_advice: Remplacement typique tous les 30 000 km, plus fréquent en
      milieu poussiéreux ou usage tout-terrain.
    related_pages:
    - filtre-habitacle
    - filtre-a-huile
confidence_score: 0.48
---

# Filtre à air

> 📥 **Pilote G6 ADR-033 — cas edge non-safety** (`family: filtration`, `risk_level: low`). Valide que les gates safety ne se déclenchent pas faussement sur une gamme non-safety. Sections H2 ordre canon Phase 4 plan deja-verifier-existant.

## Définition

Le filtre à air est l'élément poreux situé sur le circuit d'admission moteur, retenant les particules solides (poussières, pollen, débris) avant que l'air n'atteigne les chambres de combustion. Pièce d'entretien standard, remplacée à intervalle planifié.

## Fonction

L'air ambiant aspiré par le moteur traverse le filtre dans le boîtier d'admission, qui retient les particules selon une porosité calibrée. Un filtre colmaté augmente la perte de charge, réduit le débit d'admission, et dégrade la combustion. Conséquences : perte de puissance, surconsommation, fumée à l'échappement dans les cas avancés.

## Symptômes d'usure

> Cette pièce **peut contribuer** à certains symptômes du système de filtration, sans en être systématiquement la cause unique. Le modèle diagnostic complet vit dans la DB `__diag_symptom` et l'outil diagnostic — pas ici.

- 🔻 **Perte de puissance moteur progressive** *(possible cause, slug DB `perte_puissance_filtration`)* — filtre colmaté réduisant le débit d'admission, dégradant la combustion. Symptôme typique après dépassement de l'intervalle entretien ou usage en milieu poussiéreux [^1][^2]

> **Note** : d'autres symptômes liés à la filtration (`surconsommation_carburant` id=56, `odeur_habitacle` id=57) sont présents en DB mais concernent surtout filtre carburant et filtre habitacle (pas filtre à air directement). Voir [[filtre-habitacle]] et [[filtre-a-carburant]] pour ces symptômes.

## Critères de choix

Privilégier un filtre conforme aux dimensions du boîtier d'admission constructeur. Pour usage tout-terrain ou environnement poussiéreux, des filtres à porosité progressive (cellulose imprégnée + grille support) offrent une autonomie supérieure mais doivent être remplacés selon les indications constructeur.

> **Conseil entretien** : remplacement typique tous les 30 000 km, plus fréquent en milieu poussiéreux ou usage tout-terrain.

Filtres réutilisables (type coton huilé K&N et équivalents) : permettent un nettoyage selon procédure stricte constructeur, mais coût initial 3-5× supérieur à un filtre papier standard.

## Compatibilité véhicule

Pour vérifier la compatibilité filtre à air ↔ véhicule, utiliser le sélecteur sur le site (sélection marque/modèle/année/motorisation) ou interroger la base `__seo_pg_aliases` (référence : `pg_id: 510`).

Pièces complémentaires fréquemment associées au programme entretien filtration :

- [[filtre-habitacle]] — filtre poussières/pollen circuit ventilation cabine
- [[filtre-a-huile]] — filtre lubrification moteur, remplacé à chaque vidange
- [[filtre-a-carburant]] — filtre injection essence/diesel, intervalle 60 000 km diesel

## Intentions SEO observées

`entity_data.intents` : `entretien`, `achat`, `remplacement` (3 intents → fiche entretien planifié).

`vlevel: V3` (top intent : entretien planifié, volume de recherche modéré, peu de diagnostic).

`kw_top` : à compléter Phase 5 via DB `__seo_keywords` queries scopées sur la famille `filtration` + intents listés.

## Questions fréquentes

### À quelle fréquence remplacer le filtre à air ?

Typiquement tous les 30 000 km. Plus fréquent en milieu poussiéreux, usage urbain intensif ou tout-terrain [^1].

### Peut-on nettoyer un filtre à air au lieu de le remplacer ?

Non pour les filtres papier standard (perte de porosité après nettoyage). Oui pour les filtres réutilisables type coton huilé, mais selon procédure constructeur stricte (nettoyant + huile dédiés) [^2].

### Quels sont les symptômes d'un filtre à air encrassé ?

Perte de puissance progressive à l'accélération, surconsommation de carburant, fumée noire à l'échappement (diesel surtout), parfois sifflement à l'admission. Voir [Symptômes d'usure](#symptômes-dusure) pour le détail.

### Est-il dangereux de rouler avec un filtre à air encrassé ?

Pas immédiatement dangereux pour la sécurité (contrairement aux plaquettes de frein), mais nuisible à long terme : combustion dégradée, encrassement des injecteurs, surconsommation chronique. À traiter dans le cadre de l'entretien planifié.

### Quelle différence entre filtre à air moteur et filtre habitacle ?

- **Filtre à air moteur** (cette fiche) : retient les particules dans l'air aspiré par le moteur pour la combustion.
- **Filtre d'habitacle** ([[filtre-habitacle]]) : retient les particules dans l'air ventilé dans la cabine pour les passagers.

Deux pièces distinctes, deux intervalles d'entretien différents (15 000 km habitacle vs 30 000 km moteur).

## Sources et provenance

Voir `source_refs` dans le frontmatter pour la provenance manuelle (compilation OEM constructeurs).

Sources canoniques utilisées dans `diagnostic_relations[].sources` (toutes en `status: to_capture` — voir `_quality/sources-brief.md`) :

[^1]: `oem_filter_maintenance_general` — Compilation des recommandations OEM concernant les intervalles d'entretien des filtres. Source `type: oem_manual`, `confidence: medium`. License `proprietary-manufacturer` — capture en citations YAML uniquement (Phase 7, preset `manuel-constructeur-pdf` à livrer skill PR2).
[^2]: `bosch_fad_2020` — Bosch FAD 2020 Brochure Réparation, sections filtration. Source `type: brochure`, `confidence: medium`. License `proprietary-manufacturer` — citation seule (Phase 7).

## Points à vérifier

- [ ] Vérifier `entity_data.pg_id: 510` aligné DB `__seo_pg_aliases` Supabase
- [ ] Confirmer `vlevel: V3` (vérifier `r7-curation-method.md` vault)
- [ ] Compléter `aliases` si autres variantes commerciales (FR uniquement — règle `feedback_french_only_for_content.md`)
- [x] **2026-05-02** : `diagnostic_relations[]` ré-ajouté avec `perte_puissance_filtration` (slug DB existant id=55, audit MCP supabase confirmé ; correction de l'analyse erronée du 2026-04-30)
- [ ] Capturer 2 sources `to_capture` (cf. `_quality/sources-brief.md` + Phase 7) : `oem_filter_maintenance_general`, `bosch_fad_2020`
- [ ] Compléter `entity_data.kw_top` via DB `__seo_keywords` (scope famille `filtration` + intents)
- [ ] Construire `_coverage/filtre-a-air.coverage.yaml` (Phase 5 plan parent)
- [ ] Décider promotion → `wiki/gammes/filtre-a-air.md` (commit message obligatoire `promotion-from-proposals: filtre-a-air`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
- [ ] Flip humain ciblé `evidence[*].diagnostic_safe: true` reste interdit tant que les sources ne sont pas corroborées par OEM (commit signé reviewer ≠ auteur, ADR-033 §D4)
