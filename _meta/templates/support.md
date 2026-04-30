---
template_version: 1.0.0
template_type: support
applies_to: status in [draft, auto_reviewed, reviewed]
---

<!--
Template canonique pour fiches support / FAQ chatbot (entity_type: support).
Référence : plan rev 6 §3, quality-gates.md §3, schema v1.0.

Sections obligatoires :
1. Question
2. Réponse
3. Cas particuliers
4. Liens internes

⚠️ Risk_level CRITICAL automatique pour catégories : livraison, retour, garantie, paiement.
→ validation_mode: human_required obligatoire (cf. quality-gates.md §3, §7).
-->

```yaml
---
schema_version: 1.0.0
id: support:<kebab-case-slug>
entity_type: support
slug: <kebab-case-slug>
title: <Question utilisateur formulée — ex: "Combien de temps pour la livraison ?">
aliases: []
lang: fr
created_at: 2026-04-XX
updated_at: 2026-04-XX

# Traceability
truth_level: L1          # support contractuel = faits validés humainement
source_refs:
  - kind: manual
    note: "Réponse validée par <équipe support / direction>"
    author: "<email>"
provenance:
  ingested_by: "human:<email>"   # support critical = jamais skill seul
  promoted_from: null
  extracted: 0
  inferred: 0
  ambiguous: 0

# État opérationnel
status: draft
review_status: draft
review_status_detail: null
validation_mode: human_required   # support contractuel = humain obligatoire
risk_level: critical              # livraison/retour/garantie/paiement = critical
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

# entity_data typé support
entity_data:
  category: <livraison|retour|garantie|compatibilite|paiement|compte|service-client|seo-strategy>
  audience: client_final
  contractual: true     # true pour livraison/retour/garantie/paiement → critical
---
```

# {{ title }}

## Question

<!-- Reformulation littérale de la question utilisateur. Une seule question. -->

## Réponse

<!--
Réponse claire, courte, factuelle. Sourcée (CGV, CGU, page contact, validation interne).
PAS de promesse non couverte par contrat (commercial_promise gate).
-->

## Cas particuliers

<!--
Exceptions, cas limites, conditions à vérifier.
Exemple : "Livraison express disponible uniquement pour la France métropolitaine."
-->

- **Cas 1** — description
- **Cas 2** — description

## Liens internes

<!--
Renvoi vers fiches connexes : autres FAQ support, gammes/vehicles concernés.
-->

- \[\[<support-slug-related>\]\] — note
- \[\[<gamme-or-vehicle-slug>\]\] — note

______________________________________________________________________

<!--
Notes rédacteur :
- Toute fiche support contractuelle (livraison/retour/garantie/paiement) = risk_level: critical
- validation_mode: human_required → 100% review humaine, pas d'auto-promotion (§3 quality-gates)
- Pas de promesse commerciale ("livraison gratuite garantie sur tout") sans validation explicite
- Pas de donnée interne (paths backend, IDs DB, noms d'employés) — gate catalog_leak étendu
-->
