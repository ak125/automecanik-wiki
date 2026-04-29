---
template_version: 1.0.0-archived
template_type: diagnostic
applies_to: never (archived)
archived_at: '2026-04-29'
archived_reason: 'Conflit avec ADR-033 §D3 — fichiers-par-symptôme `wiki/diagnostic/<symptom>-*.md` interdits.'
canon: ['ADR-033']
---

<!--
ARCHIVÉ — NE PAS UTILISER POUR NOUVELLES FICHES.

Ce template a été créé le 2026-04-29 matin sur l'hypothèse (incorrecte) que
chaque symptôme méritait un fichier wiki dédié. ADR-033 §D3 interdit
explicitement les fichiers-par-symptôme `wiki/diagnostic/<symptom>-*.md`.

Modèle canon (à utiliser à la place) :
- Symptômes système → entrée `diagnostic_relations[]` dans la fiche `wiki/gamme/<slug>.md`
  (canon ADR-033 §D1, voir `_meta/templates/gamme.md` v2.0.0)
- Source de vérité du symptôme → DB `__diag_symptom` (rattachée à `__diag_system`)
- Outil diagnostic LIVE → consomme `__diag_*` directement

Ce template reste éventuellement utilisable pour des fiches macro-pédagogiques
(vocab UI, FAQ, signes diagnostic) sous `wiki/diagnostic/<vocab-slug>.md` (canon
ADR-032 §D1) — mais PAS pour des fichiers-par-symptôme. Si une telle fiche est
créée, repenser sérieusement la nécessité (la majorité des symptômes ont leur
représentation canonique en DB + section gamme R3).

Référence canon :
- ADR-033 §D2/§D3 (vault)
- ADR-032 §D1 (vault)
- _meta/templates/gamme.md v2.0.0 (template canon de remplacement)

Contenu original ci-dessous (pour archive uniquement, ne pas suivre).

----- contenu original archivé -----

Template canonique pour fiches diagnostic (entity_type: diagnostic).
Référence : plan rev 6 §3, quality-gates.md §3, schema v1.0.

Sections obligatoires :
1. Symptôme
2. Causes possibles
3. Vérifications
4. Renvoi vers gammes/vehicles
5. safety_advisory   ← OBLIGATOIRE si risk_level=high|critical

⚠️ CATÉGORIE LA PLUS RISQUÉE.
- Diagnostic freinage / direction / batterie / airbag = risk_level: high (minimum)
- Affirmation safety non sourcée (gate safety_unsourced §2 quality-gates) = FAIL humain bloquant
- Mentions de prudence obligatoires si risk_level=high|critical
-->

```yaml
---
schema_version: 1.0.0
id: diagnostic:<kebab-case-slug>
entity_type: diagnostic
slug: <kebab-case-slug>
title: <Symptôme formulé en français — ex: "Bruit de freinage strident">
aliases: []
lang: fr
created_at: 2026-04-XX
updated_at: 2026-04-XX

# Traceability
truth_level: L2          # règles métier diagnostic
source_refs:
  - kind: raw
    path: "recycled/rag-knowledge/diagnostic/<slug>.md"
    confidence: medium
  - kind: external_url
    url: "<source officielle constructeur ou pro>"
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
validation_mode: human_required   # diagnostic = humain obligatoire pour critical (freinage/direction/batterie/airbag)
                                  # validation_mode: automatic uniquement si risk_level=low (rare)
risk_level: high                  # diagnostic safety = high minimum, critical pour freinage/direction/batterie/airbag
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
target_classes: [KB_Diagnostic]

# entity_data typé diagnostic
entity_data:
  system: <freinage|alimentation|transmission|moteur|suspension|direction|electricite|...>
  severity: <low|medium|high|critical>   # gravité immédiate du symptôme
  related_gammes: []                     # slugs de gammes concernées
  related_vehicles: []                   # slugs de vehicles concernés (souvent vide = transverse)
  safety_critical: true                  # true pour freinage/direction/batterie/airbag
---
```

# {{ title }}

## Symptôme

<!--
Description précise du symptôme tel qu'il se manifeste pour l'utilisateur.
Contexte : quand apparaît-il (à froid, à chaud, en virage, au freinage…) ?
-->

## Causes possibles

<!--
Liste à puces ordonnées par fréquence ou par gravité.
Pour chaque cause : description courte + niveau de gravité + sourcée.
-->

- **Cause 1** — description ; gravité : low/medium/high/critical
- **Cause 2** — description ; gravité : low/medium/high/critical

## Vérifications

<!--
Étapes que l'utilisateur peut faire visuellement / au repos. Pas d'instruction de réparation.
Renvoi systématique vers professionnel pour intervention sur système safety.
-->

1. Vérification 1 — description
2. Vérification 2 — description

## Renvoi vers gammes / véhicules

<!--
Lien interne vers fiches gamme et/ou vehicle pertinentes pour comprendre la pièce.
-->

- [[<gamme-slug>]] — fiche gamme concernée
- [[<vehicle-slug>]] — fiche véhicule si symptôme spécifique

## safety_advisory  *(obligatoire si `risk_level` ∈ {high, critical})*

<!--
Mention de prudence explicite. Exemples :
- "Si le symptôme persiste, ne pas continuer à conduire — faire vérifier par un professionnel."
- "Un freinage altéré peut conduire à une perte de contrôle. Rendez-vous immédiatement chez un professionnel."

Cette section est REQUISE par les gates si risk_level=high|critical (cf. quality-gates.md §2).
-->

> ⚠️ **Sécurité** : ...

---

<!--
Notes rédacteur :
- TOUTE affirmation safety doit citer une source `confidence: high` (gate safety_unsourced)
- Pas d'instruction de démontage / remplacement (réservé aux pros, gate étendu)
- Pas de promesse "garantie" ou "100% efficace" (commercial_promise gate)
- Si symptôme = freinage, direction, batterie, airbag → risk_level: critical, validation_mode: human_required
-->
