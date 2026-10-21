---
schema_version: 2.0.0
id: gamme:courroie-d-accessoire
entity_type: gamme
slug: courroie-d-accessoire
title: Courroie d'accessoire
aliases: []
lang: fr
created_at: '2026-05-27'
updated_at: '2026-10-21'
truth_level: L2
source_refs:
- kind: raw
  path: sources/auto-captures/courroie-d-accessoire/hella-com-wl-hella-poulie-20261021-bd0c1873.md
  cid: sha256:fb485f82f9e87e17c47146ee141771b483d3d0c41f98382301696b3c157b59ac
  captured_at: '2026-10-20'
  confidence: medium
provenance:
  ingested_by: script:promote-raw-gammes-to-wiki@v0.1
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: 'Réparation candidate 2026-10-21 : ancien corps RAG et matrice de compatibilité
  conservés dans Git 9f63fc49. Faux paragraphe de symptômes retiré. Texte limité au
  fonctionnement documenté de la transmission vers l’alternateur. Une seule preuve,
  droits inconnus, aucune relation diagnostic inventée ; choix, entretien et couverture
  du reste des accessoires à compléter. Pas de promotion.'
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
  pg_id: 10
  family: distribution
  related_parts:
  - courroie-de-distribution
  - kit-de-distribution
  - galet-tendeur-de-courroie-de-distribution
  - galet-enrouleur-de-courroie-de-distribution
  - pompe-a-eau
  intents:
  - diagnostic
  - achat
  - compatibilite
  vlevel: V4
  kw_top: []
  references: []
confidence_score: 0.36
content_hash: sha256:dbc4507d345d90fa5bdcf0fd428bc616e098764758937e192b515d55fb506887
---

# Courroie d’accessoire

## Définition

La courroie transmet le mouvement du moteur au système d’entraînement des accessoires. La documentation HELLA étudiée décrit le cas de l’alternateur et de sa poulie ; elle ne permet pas d’établir la liste des accessoires entraînés sur chaque véhicule.

## Fonctionnement

La rotation du vilebrequin n’est pas uniforme pendant le cycle de combustion. L’inertie de l’alternateur soumet alors la transmission par courroie à des variations de charge. Une poulie à roue libre, montée sur l’arbre de l’alternateur, réduit la transmission de ces irrégularités au système.

## Limites pour le choix et le montage

La poulie à roue libre transmet l’entraînement dans un sens de rotation. Ce principe ne suffit pas à choisir une référence de courroie ou de poulie. La documentation renvoie aux instructions du constructeur du véhicule et réserve le montage aux professionnels qualifiés.
