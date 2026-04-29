---
template_version: 1.0.0
template_type: constructeur
applies_to: status in [draft, auto_reviewed, reviewed]
---

<!--
Template canonique pour fiches constructeur (entity_type: constructeur).
Référence : plan rev 6 §3, quality-gates.md §3, schema v1.0.

Sections obligatoires :
1. Identité
2. Modèles principaux
3. Spécificités techniques
4. FAQ
-->

```yaml
---
schema_version: 1.0.0
id: constructeur:<kebab-case-slug>
entity_type: constructeur
slug: <kebab-case-slug>
title: <Nom constructeur — ex: Dacia>
aliases: []
lang: fr
created_at: 2026-04-XX
updated_at: 2026-04-XX

# Traceability
truth_level: L1          # L1=faits sourcés constructeur
source_refs:
  - kind: external_url
    url: "https://www.<constructeur>.fr/notre-marque"
    captured_at: 2026-04-XX
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

# entity_data typé constructeur
entity_data:
  tier: 2               # 1=prioritaire, 2=secondaire, 3=niche (cf. _meta/enums.yaml)
  pays_origine: <fr|de|jp|...>
  groupe: <renault-group|stellantis|vw-group|...>
---
```

# {{ title }}

## Identité

<!--
Pays d'origine, année de fondation, groupe industriel actuel, positionnement marché.
Sources : site officiel constructeur, presse spécialisée vérifiée.
-->

- **Pays d'origine** : ...
- **Fondation** : ...
- **Groupe** : ...
- **Tier** : ... (1=prioritaire, 2=secondaire, 3=niche)

## Modèles principaux

<!--
Liste des modèles emblématiques avec lien vers fiche véhicule si elle existe.
Pas d'exhaustivité — focus sur ce qui compte pour AutoMecanik.
-->

- [[<vehicle-slug-1>]] — note courte
- [[<vehicle-slug-2>]] — note courte

## Spécificités techniques

<!--
Architectures moteur récurrentes, plates-formes partagées, particularités d'entretien
caractéristiques de la marque (sourcé).
-->

## FAQ

### Question fréquente 1 ?

Réponse courte.

### Question fréquente 2 ?

Réponse courte.

---

<!--
Notes rédacteur :
- Pas de prix, stock, SKU
- Pas de comparaison commerciale ("meilleur que X")
- Pas d'affirmation EN/US sans opt-in (cf. source-policy.md §2)
-->
