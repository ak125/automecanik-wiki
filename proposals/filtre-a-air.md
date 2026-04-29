---
schema_version: 2.0.0
id: gamme:filtre-a-air
entity_type: gamme
slug: filtre-a-air
title: Filtre à air
aliases:
- filtre à air moteur
- air filter
- filtre admission
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L2
source_refs:
- kind: manual
  note: Données entretien filtres depuis recommandations OEM constructeurs (Renault,
    Peugeot, Bosch). Web-clip à archiver.
  author: human:@fafa
provenance:
  ingested_by: human:@fafa
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: 'Pilote G6 ADR-033 — gamme non-safety (family: filtration, risk_level:
  low). Sert de cas

  edge pour vérifier que le gate safety_unsourced ne se déclenche pas faussement.

  diagnostic_relations[] minimal (1 entrée, source_policy 2_medium_concordant).

  schema_version: 2.0.0 + bloc maintenance ADR-032 §D1 (filtre-a-air ∈ kg_nodes.MaintenanceInterval).

  '
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
diagnostic_relations:
- symptom_slug: perte_puissance_filtration
  system_slug: filtration
  relation_to_part: possible_cause
  part_role: filtre à air colmaté limitant le débit d'admission, induit perte de puissance
    progressive
  evidence:
    confidence: medium
    source_policy: 2_medium_concordant
    reviewed: false
    diagnostic_safe: false
    confidence_score_computed: 1.0
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
  maintenance:
    educational_advice: Remplacement typique tous les 30 000 km, plus fréquent en
      milieu poussiéreux ou usage tout-terrain.
    related_pages:
    - filtre-habitacle
    - filtre-a-huile
---

# Filtre à air

> 📥 **Pilote G6 ADR-033 — cas edge non-safety** (`family: filtration`, `risk_level: low`). Valide que les gates safety ne se déclenchent pas faussement sur une gamme non-safety.

## Définition

Le filtre à air est l'élément poreux situé sur le circuit d'admission moteur, retenant les particules solides (poussières, pollen, débris) avant que l'air n'atteigne les chambres de combustion. Pièce d'entretien standard, remplacée à intervalle planifié.

## Fonctionnement

L'air ambiant aspiré par le moteur traverse le filtre dans le boîtier d'admission, qui retient les particules selon une porosité calibrée. Un filtre colmaté augmente la perte de charge, réduit le débit d'admission, et dégrade la combustion.

## Symptômes système auxquels cette pièce peut contribuer

> Cette pièce peut contribuer à un symptôme de filtration. Pour les symptômes système moteur étendus, voir le modèle diagnostic complet en DB.

- 🐌 **Perte de puissance progressive** *(possible cause)* — colmatage limitant le débit d'admission [^1][^2]

## Conseil pédagogique d'entretien

> Remplacement typique tous les 30 000 km, plus fréquent en milieu poussiéreux ou usage tout-terrain.

Voir aussi : [[filtre-habitacle]], [[filtre-a-huile]].

## Choix selon véhicule

Privilégier un filtre conforme aux dimensions du boîtier d'admission constructeur. Pour usage tout-terrain ou environnement poussiéreux, des filtres à porosité progressive (cellulose imprégnée + grille support) offrent une autonomie supérieure mais doivent être remplacés selon les indications constructeur.

## FAQ

### À quelle fréquence remplacer le filtre à air ?

Typiquement tous les 30 000 km. Plus fréquent en milieu poussiéreux, usage urbain intensif ou tout-terrain [^1].

### Peut-on nettoyer un filtre à air au lieu de le remplacer ?

Non pour les filtres papier standard (perte de porosité après nettoyage). Oui pour les filtres réutilisables type coton huilé, mais selon procédure constructeur stricte [^2].

---

[^1]: `oem_filter_maintenance_general` — Compilation des recommandations OEM concernant les intervalles d'entretien des filtres. Source `type: oem_manual`, `confidence: medium` (à corroborer pour atteindre `high`).
[^2]: `bosch_fad_2020` — Bosch FAD 2020, sections filtration. Source `type: brochure`, `confidence: medium`.

## Points de review (à compléter avant promotion)

- [ ] Capturer le catalogue OEM constructeurs filtres dans `automecanik-raw/sources/catalogues/` (actuellement source `kind: manual`)
- [ ] Vérifier `entity_data.pg_id: 510` aligné DB `__seo_pg_aliases` Supabase
- [ ] Confirmer `vlevel: V3`
- [ ] Décider promotion → `wiki/gamme/filtre-a-air.md` (commit message obligatoire `promotion-from-proposals: filtre-a-air`)
