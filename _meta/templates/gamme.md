---
template_version: 2.0.0
template_type: gamme
applies_to: status in [draft, auto_reviewed, reviewed]
canon: ['ADR-031', 'ADR-032', 'ADR-033']
---

<!--
Template canonique pour fiches gamme R3/R4 (entity_type: gamme).
v2.0.0 — alignement ADR-031 (4-layer) + ADR-032 (entity_data.maintenance) + ADR-033 (diagnostic_relations[]).

Sections obligatoires :
1. Définition
2. Fonctionnement
3. Symptômes système auxquels cette pièce peut contribuer    ← ADR-033 §D1
4. Conseil pédagogique d'entretien                            ← ADR-032 §D1
5. Choix selon véhicule
6. FAQ

⚠️ Anti-patterns interdits ADR-033 §D3 :
- PAS de bloc `diagnostic.symptoms[]` (utiliser diagnostic_relations[] top-level)
- PAS de fichier `wiki/diagnostic/<symptom>-*.md` (les symptômes vivent dans __diag_symptom DB)
- PAS de répertoire `wiki/systemes/<slug>.md` (DB __diag_system est SoT)
-->

```yaml
---
schema_version: 2.0.0                      # ADR-033 + ADR-032 = breaking change vs 1.0.0
id: gamme:<kebab-case-slug>
entity_type: gamme
slug: <kebab-case-slug>
title: <Titre humain FR>
aliases: []
lang: fr
created_at: 2026-04-XX
updated_at: 2026-04-XX

# Traceability (schema v1.0+)
truth_level: L2                            # L1=faits sourcés, L2=règles métier (défaut gamme)
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/gammes/<slug>.md
    captured_at: 2026-04-XX
provenance:
  ingested_by: 'skill:wiki-proposal-writer@v0.1'
  promoted_from: null

# État opérationnel
review_status: proposed                    # draft | proposed | in_review | approved | deprecated
reviewed_by: null
reviewed_at: null
review_notes: ''
no_disputed_claims: true

# Export gates (Partie 3 — false par défaut, ne PAS flipper)
exportable:
  rag: false
  seo: false
  support: false
target_classes: [KB_Knowledge]

# Canon ADR-033 §D1 — diagnostic_relations[] TOP-LEVEL (pas sous entity_data)
# Une fiche gamme déclare uniquement les symptômes système auxquels la pièce
# peut contribuer. La pièce ne possède pas le symptôme — elle y contribue.
diagnostic_relations:
  - symptom_slug: bruit_freinage           # FK __diag_symptom.slug (validation Phase 2 ADR-033)
    system_slug: freinage                   # FK __diag_system.slug
    relation_to_part: possible_cause        # possible_cause | symptom_amplifier | secondary_effect
    part_role: 'plaquette usée, contaminée ou mal montée'   # 1 phrase, comment la pièce intervient
    evidence:
      confidence: medium                    # low | medium | high (max selon source_type, cf. source-policy.md §9.1)
      source_policy: 2_medium_concordant    # 1_high | 2_medium_concordant | manual_review
      reviewed: false                       # défaut conservateur ADR-033 §D4
      diagnostic_safe: false                # défaut conservateur ADR-033 §D4 — flip humain ciblé uniquement
    sources:
      - bosch_fad_2020                      # slug stable de _meta/source-catalog.yaml
      - oem_renault_clio_iii_workshop

# entity_data typé gamme (canon ADR-032 §D1)
entity_data:
  pg_id: <integer>                          # FK Supabase __seo_pg_aliases
  family: <freinage|filtration|...>         # cf. _meta/enums.yaml families
  intents: []                               # cf. enums.yaml intents
  vlevel: null                              # V1-V5 (Partie 3)
  related_parts: []                         # slugs gammes liées

  # Bloc maintenance (canon ADR-032 §D1) — REQUIS pour gammes liées à un kg_nodes.MaintenanceInterval
  # (filtre-a-huile, filtre-a-air, filtre-habitacle, plaquettes, distribution, etc.)
  # Joint runtime via kg_nodes.node_alias ↔ filename wiki gamme.
  maintenance:
    educational_advice: 'Vérifier l''épaisseur minimum 3 mm avant un long trajet.'
    related_pages:                          # slugs d'autres pages wiki/gamme/ liées
      - disque-de-frein
      - etrier-de-frein
---
```

# {{ title }}

## Définition

<!-- 2-4 phrases. Définir la gamme en termes simples. Sourcé. -->

## Fonctionnement

<!-- Comment ça marche. Schéma de principe en français. Sourcé. -->

## Symptômes système auxquels cette pièce peut contribuer

> Cette pièce **peut contribuer** à certains symptômes du système, sans en être systématiquement la cause unique. Le modèle diagnostic complet (causes, probabilités, vérifications) vit dans la DB `__diag_symptom` et l'outil diagnostic — pas ici.

<!--
Pour chaque entrée `diagnostic_relations[]` du frontmatter, ajouter une ligne narrative
avec footnote `[^N]` reliée aux `sources[]` du frontmatter. Le `relation_to_part` est
ré-explicité en italique (possible cause / amplifier / secondary effect).
-->

- 🔊 **Bruit de grincement au freinage** *(possible cause)* — lorsque la garniture est usée, contaminée ou mal montée [^1][^2]
- 🛑 **Vibrations dans la pédale** *(symptom amplifier)* — peut s'ajouter à un voile de disque [^1]

## Conseil pédagogique d'entretien

<!--
Section alimentée par `entity_data.maintenance.educational_advice` (ADR-032 §D1).
1-2 lignes max. Marketing court, pas paragraphe.
-->

> Vérifier l'épaisseur minimum 3 mm avant un long trajet.

Voir aussi : [[disque-de-frein]], [[etrier-de-frein]].

## Choix selon véhicule

<!--
Critères généraux uniquement. PAS d'affirmation produit/véhicule précis (catalog_leak gate §2).
Exemple OK : "Pour un véhicule de plus de 1500 kg, privilégier des plaquettes haute résistance thermique."
Exemple INTERDIT : "La référence Bosch BP-1234 est compatible avec la Renault Clio 3."
-->

## FAQ

### Question fréquente 1 ?

Réponse courte sourcée [^3].

### Question fréquente 2 ?

Réponse courte.

---

[^1]: `bosch_fad_2020` — Bosch FAD 2020 Brochure Réparation Freinage, p.27/p.31. Source `type: brochure`, `confidence: medium` (cf. `_meta/source-catalog.yaml`).
[^2]: `oem_renault_clio_iii_workshop` — Manuel d'atelier Renault Clio III, section freinage. Source `type: oem_workshop`, `confidence: medium`.
[^3]: <slug source canon catalogue>

<!--
Notes rédacteur (à supprimer avant promotion) :
- Sources : raw/recycled/external_url uniquement, slugs stables `_meta/source-catalog.yaml`
- Anti-pattern : pas de seed LLM-only (cf. source-policy.md §4)
- Pas de prix, stock, SKU, compatibilité exacte (gate catalog_leak §2 quality-gates)
- Pas de promesse commerciale (gate commercial_promise §2)
- Pour family safety (freinage, direction, distribution) : exiger ≥ 1 source confidence: high
  (ou 2 medium concordants) sur chaque symptôme. Sinon gate safety_unsourced.
- diagnostic_safe: false par défaut. Ne PAS flipper sans revue humaine ciblée (ADR-033 §D4).
-->
