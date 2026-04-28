---
schema_version: "1.0.0"
id: "support:livraison"
entity_type: support
slug: livraison
title: Conditions de livraison
aliases:
  - délai de livraison
  - frais de port
  - shipping
lang: fr
created_at: "2026-04-28"
updated_at: "2026-04-28"
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/policies/livraison.md
    captured_at: "2026-04-28"
provenance:
  ingested_by: human:@fafa
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: |
  Pilote ADR-031 Phase E support entity. Politique simple, pas de variabilité
  technique — bon candidat pour valider le flux support.
  La source est verification_status: verified (L1) côté automecanik-rag mais
  on garde L3 ici car le contenu n'est pas encore reviewé selon la grille v1.0.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  category: livraison
  audience: client
  faq_questions: []
  policy_refs: []
---

# Conditions de livraison

> 📥 **Proposition pilote ADR-031 Phase E** — extraite manuellement depuis `automecanik-rag/knowledge/policies/livraison.md`.
> À reviewer avant promotion vers `wiki/support/livraison.md`.

## Résumé proposé

Politique commerciale AutoMecanik pour les zones de livraison, transporteurs partenaires (Colissimo, Chronopost, Mondial Relay), délais et frais. Couvre France métropolitaine (24h-5j), DOM-TOM (7-15j), Belgique / Luxembourg.

## Faits extraits

- **France métropolitaine** : 100% du territoire, transporteurs Colissimo/Chronopost/Mondial Relay, 24h à 5 jours selon mode
- **DOM-TOM** : disponible sur demande, 7 à 15 jours ouvrés, frais selon poids et destination
- **Belgique & Luxembourg** : disponible

## Faits inférés

- Aucun (politique factuelle, pas d'inférence nécessaire)

## Zones ambiguës / contradictions

- `faq_questions` à enrichir : la source ne contient pas de QA structurée. À constituer lors de la promotion à partir des questions support fréquentes.
- `policy_refs` vide : à lier aux CGV / mentions légales lors de la promotion.

## Points de review

- [ ] Compléter `faq_questions` avec 3-5 QA support fréquentes (Schema.org FAQPage à l'export)
- [ ] Lier `policy_refs` vers CGV / mentions légales site
- [ ] Vérifier la mise à jour des transporteurs (Mondial Relay → InPost, etc. si applicable)
- [ ] Faire reviewer par `legal_reviewed_by` avant `truth_level: L1`
- [ ] Décider promotion → `wiki/support/livraison.md` ou ajustement
