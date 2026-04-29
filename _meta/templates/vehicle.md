---
template_version: 1.0.0
template_type: vehicle
applies_to: status in [draft, auto_reviewed, reviewed]
---

<!--
Template canonique pour fiches véhicule (entity_type: vehicle).
Référence : plan rev 6 §3, quality-gates.md §3, schema v1.0.

Sections obligatoires :
1. Identité (marque/modèle/motorisation)
2. Spécificités
3. Pièces fréquentes
4. FAQ

⚠️ R8 : page véhicule = modèle/motorisation/type_id. JAMAIS dériver vers gamme (catalogue pièces R3/R4).
Cf. memory feedback_r8_is_vehicle_not_gamme.md
-->

```yaml
---
schema_version: 1.0.0
id: vehicle:<kebab-case-slug>
entity_type: vehicle
slug: <kebab-case-slug>
title: <Titre humain FR — ex: Renault Clio III 1.5 dCi 85>
aliases: []
lang: fr
created_at: 2026-04-XX
updated_at: 2026-04-XX

# Traceability
truth_level: L1          # L1=faits sourcés constructeur (défaut vehicle)
source_refs:
  - kind: raw
    path: "sources/catalogues/<constructeur>/<modele>.json"
    confidence: high
provenance:
  ingested_by: "skill:wiki-proposal-writer@v0.1"
  promoted_from: null
  extracted: 0
  inferred: 0
  ambiguous: 0

# État opérationnel
status: draft
review_status: draft
review_status_detail: null
validation_mode: automatic
risk_level: medium
confidence_score: 0.0
quality_score: null
blocked_reasons: []
to_verify: []
template_version: 1.0.0

# Export gates
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: [KB_Knowledge]

# entity_data typé vehicle
entity_data:
  constructeur: <renault|peugeot|...>
  modele: <clio-iii|208|...>
  motorisation: <1.5-dci-85|...>
  type_id: null         # ID interne SEO V-Level (Partie 3)
  annees: { debut: null, fin: null }
---
```

# {{ title }}

## Identité

<!--
Marque, modèle, motorisation, années de production, type carrosserie.
Sources : catalogues constructeur (raw) ou recyclé vérifié.
-->

- **Constructeur** : ...
- **Modèle** : ...
- **Motorisation** : ... (cylindrée, puissance, type carburant)
- **Années** : ... – ...
- **Carrosserie** : ...

## Spécificités

<!--
Particularités techniques notables : architecture moteur, particularités d'entretien,
points faibles connus (sourcés constructeur ou retours techniques vérifiés).
-->

## Pièces fréquentes

<!--
Catégories de pièces couramment remplacées sur ce véhicule, **sans référence produit précise**.
Lien interne vers les fiches gamme correspondantes.
Exemple OK : "Sur cette motorisation, le filtre à huile [[filtre-a-huile]] est souvent remplacé tous les 15 000 km."
Exemple INTERDIT : "Utiliser la référence Bosch BP-1234." (catalog_leak gate)
-->

- [[<gamme-slug-1>]] — note courte
- [[<gamme-slug-2>]] — note courte

## FAQ

### Question fréquente 1 ?

Réponse courte.

### Question fréquente 2 ?

Réponse courte.

---

<!--
Notes rédacteur :
- Pas de prix, stock, SKU (catalog_leak gate)
- Pas de promesse commerciale (commercial_promise gate)
- Pas de compatibilité pièce/véhicule exacte (réservé au catalogue, jamais au wiki)
-->
