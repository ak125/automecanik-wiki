---
schema_version: "1.0.0"
id: "vehicle:<% tp.file.title.toLowerCase().replace(/\s+/g, '-') %>"
entity_type: vehicle
slug: "<% tp.file.title.toLowerCase().replace(/\s+/g, '-') %>"
title: "<% tp.file.title %>"
aliases: []
lang: fr
created_at: <% tp.date.now("YYYY-MM-DD") %>
updated_at: <% tp.date.now("YYYY-MM-DD") %>

truth_level: L4
source_refs: []
provenance:
  ingested_by: "human:@fafa"
  promoted_from: null
  promoted_at: null
lineage_id: null
content_hash: null
parents: []

review_status: draft
reviewed_by: null
reviewed_at: null
review_notes: ""
no_disputed_claims: true
quality_score: null

exportable:
  rag: false
  seo: false
  support: false
target_classes:
  - KB_Catalog
  - KB_Knowledge

entity_data:
  make: ""
  model: ""
  generation: ""
  years: [null, null]
  type_id: 0
  motorizations: []
  vlevel: V5
  low_profile_canary: false
---

# <% tp.file.title %>

> ⚠️ Fiche brouillon. Compléter `make`, `model`, `type_id`, `source_refs`.
> Pour **pilote R8** : positionner `low_profile_canary: true` (PAS Clio/208/Golf).
> Cf ADR-022 vault pour scope DB-only `__rag_proposals` (downstream backend, dormant).

<!--
STRUCTURE — 2 niveaux (cf. doctrine coverage_contract, automecanik-raw _schemas/completeness/vehicle.yaml).
• 4 sections OBLIGATOIRES (Gate 4 quality-gates + score, noms figés dans
  compute-confidence-score.py SECTIONS_REQUIRED["vehicle"]) : Identité · Spécificités ·
  Pièces fréquentes · FAQ. NE PAS renommer (sinon Gate 4 FAIL + score 0).
• Sections d'APPROFONDISSEMENT optionnelles (couverture exhaustive « expected », JAMAIS
  bloquantes) : à remplir dès que la connaissance sourcée existe. Une section vide = facette
  `missing`, pas un défaut. Maille = MODÈLE-GÉNÉRATION (jamais un auto_type isolé).
GARDE-FOUS (Gate 7 catalog_leak / commercial_promise, sur TOUTES les sections) :
  pas de prix · stock · SKU · référence produit précise · compatibilité pièce/véhicule exacte.
-->

## Identité

<!-- OBLIGATOIRE. Marque · modèle · génération · années · carrosserie. Source : constructeur / recyclé vérifié. -->

- **Constructeur** :
- **Modèle / génération** :
- **Années** :
- **Carrosserie** :

## Motorisations & codes moteur

<!-- OPTIONNEL (encouragé). Table des motorisations de la GÉNÉRATION + codes moteur.
  Codes moteur = DB interne `auto_type_motor_code` (provenance source.type: db, jamais inférés). -->

| Motorisation | Code(s) moteur | Carburant | Puissance | Années |
| ------------ | -------------- | --------- | --------- | ------ |
|              |                |           |           |        |

## Spécificités

<!-- OBLIGATOIRE. Particularités techniques notables (architecture, points faibles connus, sourcés). -->

## Différences par motorisation

<!-- OPTIONNEL. Ce qui change d'une motorisation à l'autre (entretien, pièces, points faibles). -->

## Pièces fréquentes

<!-- OBLIGATOIRE. Catégories couramment remplacées → wikilinks vers les fiches gamme.
  Exemple OK : « le filtre à huile [[filtre-a-huile]] est remplacé ~tous les 15 000 km ».
  INTERDIT : référence produit précise, prix, compatibilité exacte (catalog_leak gate). -->

- \[\[<gamme-slug>\]\] —

## Problèmes par système

<!-- OPTIONNEL. Pannes connues regroupées par système, sourcées (par code moteur si pertinent).
  Renvoi possible vers les fiches [[<diagnostic-slug>]]. -->

## Entretien par motorisation

<!-- OPTIONNEL. Intervalles et opérations spécifiques (sans valeurs prescriptives à risque
  non sourcées constructeur — couples/pressions/fluides = fail-closed, cf. encyclopedia-contract). -->

## Diagnostic

<!-- OPTIONNEL. Symptômes → renvoi vers fiches diagnostic [[<diagnostic-slug>]]. Pas de procédure dangereuse non sourcée. -->

## Achat occasion

<!-- OPTIONNEL. Points de vigilance à l'achat d'occasion (kilométrage, vérifications, coûts d'entretien typiques). -->

## FAQ

<!-- OBLIGATOIRE. Questions fréquentes réelles + réponses courtes sourcées. -->

### Question fréquente ?

Réponse courte.

## Sources et provenance

<!-- Remplir `source_refs:` dans le frontmatter. Hiérarchie : OEM > équipementier > presse technique. -->

## Points à vérifier

- [ ] `source_refs` non vide (≥1 source ; ≥2 source-kinds distincts encouragé)
- [ ] 4 sections obligatoires remplies : Identité · Spécificités · Pièces fréquentes · FAQ
- [ ] `type_id` aligné avec DB `__auto_type` (53959 types) ; codes moteur depuis `auto_type_motor_code`
- [ ] `make` slug aligné avec une fiche `wiki/constructeurs/<make>.md`
- [ ] Aucune fuite catalogue (prix / stock / SKU / compatibilité pièce exacte)
- [ ] Pas de Clio/208/Golf si pilote R8 stage 2
- [ ] `low_profile_canary` cohérent avec `tier=3` du constructeur
