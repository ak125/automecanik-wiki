---
schema_version: 1.0.0
id: support:livraison
entity_type: support
slug: livraison
title: Conditions de livraison
aliases:
  - délai de livraison
  - frais de port
  - délais de livraison
  - conditions de transport
lang: fr
created_at: '2026-04-28'
updated_at: '2026-05-02'
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/policies/livraison.md
    captured_at: '2026-04-28'
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

  2026-05-02 (Phase 4 plan deja-verifier-existant) :
  - Sections H2 alignées sur ordre canon _templates/new-support.md
    (Résumé / Détail / Cas particuliers / FAQ / Sources et provenance /
    Points à vérifier)
  - Section "Résumé proposé / Faits extraits / Faits inférés / Zones ambiguës"
    (template proposal draft) supprimées et fusionnées dans sections canon
  - alias EN supprimé "shipping" — règle FR exclusif
    (feedback_french_only_for_content.md)
  - target_classes étendu [] → [KB_Knowledge]
  - entity_data.faq_questions[] peuplé avec 5 QA structurées
    (Schema.org FAQPage compatible à l'export SEO future)
  - Section "Détail" structurée en 3 sous-sections par zone (France/DOM-TOM/UE)
  - Section "Cas particuliers" ajoutée (transporteur indisponible, retour, perte)

  **Bloqueur strict promotion** (ADR-040 §5 safe-by-default) :
  legal_reviewed_by reste null tant que validation juridique externe AutoMecanik
  non obtenue. Fiche reste en proposals/, exportable.support reste false.

  À reviewer humainement avant promotion vers wiki/support/.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
  - KB_Knowledge
entity_data:
  category: livraison
  audience: client
  faq_questions:
    - q: Quels sont les délais de livraison en France métropolitaine ?
      a: 24h à 5 jours ouvrés selon le mode de transport choisi (Colissimo, Chronopost ou Mondial Relay) et la disponibilité des pièces en stock. Les commandes passées avant 14h sont expédiées le jour même (jours ouvrés).
    - q: Livrez-vous dans les DOM-TOM ?
      a: Oui, livraison disponible sur demande dans tous les DOM-TOM. Délais 7 à 15 jours ouvrés. Frais calculés selon le poids et la destination — devis personnalisé fourni au moment de la commande.
    - q: Livrez-vous en Belgique et au Luxembourg ?
      a: Oui, livraison disponible en Belgique et au Luxembourg. Délais et frais identiques à la France métropolitaine pour la majorité des destinations.
    - q: Comment suivre ma commande ?
      a: Un numéro de suivi est envoyé par email dès l'expédition. Suivi disponible directement sur le site du transporteur (Colissimo / Chronopost / Mondial Relay).
    - q: Que faire si je ne suis pas présent à la livraison ?
      a: Le transporteur dépose un avis de passage avec instructions pour récupérer le colis (point relais ou seconde présentation à domicile selon le mode choisi).
  policy_refs: []
  legal_reviewed_by: null
confidence_score: 0.24
---

# Conditions de livraison

> 📥 **Proposition pilote ADR-031 Phase E** — extraite manuellement depuis `automecanik-rag/knowledge/policies/livraison.md`. Sections H2 ordre canon Phase 4 plan deja-verifier-existant. **Promotion bloquée** tant que `legal_reviewed_by` non rempli (règle safe-by-default ADR-040 §5).

## Résumé

Politique commerciale AutoMecanik concernant les zones de livraison, transporteurs partenaires (Colissimo, Chronopost, Mondial Relay), délais et frais. Couvre **France métropolitaine** (24h-5 jours), **DOM-TOM** (7-15 jours), **Belgique** et **Luxembourg**.

Toute commande validée avant 14h (jours ouvrés) est expédiée le jour même selon disponibilité du stock.

## Détail

### France métropolitaine

- **Couverture** : 100% du territoire métropolitain
- **Transporteurs partenaires** : Colissimo, Chronopost, Mondial Relay
- **Délais** : 24h à 5 jours ouvrés selon le mode choisi
  - Chronopost express : 24h ouvré
  - Colissimo Domicile : 2 à 3 jours ouvrés
  - Mondial Relay (point relais) : 3 à 5 jours ouvrés
- **Frais** : calculés selon le poids du colis et le mode choisi (affiché au panier)

### DOM-TOM

- **Disponibilité** : sur demande, tous DOM-TOM (Guadeloupe, Martinique, Guyane, Réunion, Mayotte, Saint-Pierre-et-Miquelon, Polynésie française, Nouvelle-Calédonie, Wallis-et-Futuna)
- **Délais** : 7 à 15 jours ouvrés selon destination
- **Frais** : devis personnalisé selon poids et destination (formulaire de demande)

### Belgique et Luxembourg

- **Disponibilité** : oui, livraison directe via Colissimo International ou Mondial Relay
- **Délais** : équivalents France métropolitaine pour la majorité des destinations
- **Frais** : majoration légère par rapport à la France selon le mode choisi

## Cas particuliers

### Transporteur indisponible dans votre zone

Si l'un des transporteurs partenaires (Colissimo, Chronopost, Mondial Relay) ne dessert pas votre zone, contacter le service client pour étudier une solution alternative (transporteur tiers ou point de retrait alternatif).

### Pièce volumineuse (capot, élément de carrosserie, kit complet)

Pour les pièces volumineuses (>30 kg ou dimensions >120 cm), un transporteur spécialisé peut être requis. Délai et frais sur devis. Point de livraison à confirmer (impossible en point relais standard).

### Pièce hors stock

Si une pièce commandée n'est pas immédiatement disponible en stock, le délai d'expédition est rallongé du temps d'approvisionnement (typiquement 3-7 jours). Information notifiée par email après commande.

### Retour et rétractation

Conformément aux dispositions légales françaises (Code de la consommation), un délai de rétractation de **14 jours calendaires** s'applique à toute commande à distance. Voir les CGV pour les conditions précises de retour (état d'origine, frais de retour à charge du client sauf erreur AutoMecanik).

### Perte ou détérioration colis

En cas de perte ou détérioration constatée à la réception, contacter le service client sous 48h. Une enquête transporteur est ouverte ; remboursement ou ré-expédition selon le résultat.

## FAQ

> Voir `entity_data.faq_questions[]` dans le frontmatter pour la version structurée Schema.org FAQPage compatible à l'export SEO future.

### Quels sont les délais de livraison en France métropolitaine ?

24h à 5 jours ouvrés selon le mode de transport choisi (Colissimo, Chronopost ou Mondial Relay) et la disponibilité des pièces en stock. Les commandes passées avant 14h sont expédiées le jour même (jours ouvrés).

### Livrez-vous dans les DOM-TOM ?

Oui, livraison disponible sur demande dans tous les DOM-TOM. Délais 7 à 15 jours ouvrés. Frais calculés selon le poids et la destination — devis personnalisé fourni au moment de la commande.

### Livrez-vous en Belgique et au Luxembourg ?

Oui, livraison disponible en Belgique et au Luxembourg. Délais et frais identiques à la France métropolitaine pour la majorité des destinations.

### Comment suivre ma commande ?

Un numéro de suivi est envoyé par email dès l'expédition. Suivi disponible directement sur le site du transporteur (Colissimo / Chronopost / Mondial Relay).

### Que faire si je ne suis pas présent à la livraison ?

Le transporteur dépose un avis de passage avec instructions pour récupérer le colis (point relais ou seconde présentation à domicile selon le mode choisi).

## Sources et provenance

Sources canoniques utilisées (cf. `_quality/sources-brief.md` Phase 3) :

- **CGV AutoMecanik 2026** (source interne) — à stocker dans `automecanik-raw/sources/legal/automecanik_legal_cgv_2026.md` (license `proprietary-citation-only` interne, redistribuable selon CGV). Action humaine Phase 3 : édition manuelle directe (pas via Web Clipper).
- **Conditions Colissimo** : https://www.colissimo.fr/conditions-generales-vente (license `proprietary-citation-only`, capture intégrale via preset `generic-article` avec license override)
- **Conditions Chronopost** : https://www.chronopost.fr/conditions-generales (idem)
- **Conditions Mondial Relay** : https://www.mondialrelay.fr/conditions-generales (idem)

`policy_refs[]` à compléter avec URLs CGV/Mentions Légales AutoMecanik après revue juridique.

## Points à vérifier

- [ ] Vérifier la mise à jour des transporteurs (Mondial Relay → InPost rebranding 2024 ?)
- [x] **2026-05-02** : `entity_data.faq_questions[]` peuplé avec 5 QA structurées (Schema.org FAQPage compatible)
- [ ] Lier `entity_data.policy_refs[]` vers CGV / mentions légales site (URLs canoniques `automecanik.com/cgv` + `automecanik.com/mentions-legales`)
- [ ] Stocker CGV AutoMecanik 2026 dans `automecanik-raw/sources/legal/` (action humaine, pas via agent — append-only `sources/`)
- [ ] Capturer 3 conditions transporteurs (Colissimo, Chronopost, Mondial Relay) via extension Obsidian preset `generic-article` (cf. `_quality/sources-brief.md`)
- [ ] Construire `_coverage/livraison.coverage.yaml` (Phase 5 plan parent)
- [ ] **BLOQUEUR PROMOTION** : `legal_reviewed_by` doit être renseigné (revue juridique externe AutoMecanik) avant toute promotion vers `wiki/support/livraison.md`. Sans ce champ, fiche reste en `proposals/` (règle safe-by-default ADR-040 §5)
- [ ] Si promotion (post legal review) : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`, `legal_reviewed_by: <legal:@nom>`
- [ ] Si promotion : commit message obligatoire `promotion-from-proposals: livraison`
- [ ] `truth_level` peut basculer L3 → L1 après review juridique + corroboration sources transporteurs
