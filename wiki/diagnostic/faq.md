---
schema_version: 1.0.0
id: diagnostic:faq
entity_type: diagnostic
slug: faq
title: Diagnostic — FAQ (7 questions)
aliases:
  - questions fréquentes
  - faq panne auto
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L4
source_refs:
  - kind: raw
    path: sources/diagnostic/faq.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:adr-032-rg-1@claude
  promoted_from: proposals/diagnostic-faq.md
  promoted_at: '2026-04-29T17:00:00Z'
review_status: approved
reviewed_by: skill:adr-032-rg-1@claude
reviewed_at: '2026-04-29T17:00:00Z'
review_notes: |
  Snapshot 1:1 du FAQ_DATA hardcodé (7 Q/A consommées par schema_org JSON-LD FAQPage côté SEO).
no_disputed_claims: true
exportable:
  rag: false
  seo: true
  support: true
target_classes: []
entity_data:
  faq:
    - question: Comment savoir quel est le problème de ma voiture ?
      answer: |
        Commencez par observer les symptômes sensoriels — voyants allumés, bruits inhabituels, vibrations, odeurs. Si un voyant moteur est allumé, lisez le code OBD avec un scanner ou entrez-le directement dans notre outil ci-dessus. Pour les pannes sans voyant, décrivez le symptôme dans le champ de recherche (ex « bruit au freinage », « vibration volant »).
      link:
    - question: Comment identifier une panne de démarreur ?
      answer: |
        Un démarreur défaillant se manifeste par un clic unique sans démarrage du moteur (relais ou solénoïde), un grincement bref lors de la mise en route, ou une absence totale de réaction alors que la batterie est chargée (tension > 12.4V). Pour confirmer, mesurez la tension aux bornes du démarreur lors de la sollicitation.
      link:
        href: /diagnostic-auto?cluster=electricite
        label: Voir les diagnostics électricité
    - question: Qu'est-ce qu'une panne voyant ABS ?
      answer: |
        Le voyant ABS orange indique que le système antiblocage est désactivé. Le freinage normal reste fonctionnel. Cause la plus fréquente — capteur ABS de roue défaillant (50 à 80 EUR la pièce). La lecture d'un code OBD Cxxxx confirme le capteur concerné. Rouler sans ABS est dangereux en freinage d'urgence.
      link:
    - question: Comment lire un code panne OBD ?
      answer: |
        Branchez un scanner OBD2 sur le port situé sous le tableau de bord côté conducteur (sous la colonne de direction). Le scanner lit les codes du type P0300 (raté d'allumage), C0031 (capteur ABS), etc. Vous pouvez également entrer le code dans notre outil Scanner en haut de page. N'effacez un code qu'après réparation.
      link:
    - question: Voiture en panne qui ne démarre pas — par où commencer ?
      answer: |
        Vérifiez dans cet ordre — 1) Batterie tension > 12.4V au repos, bornes non oxydées. 2) Démarreur clic = relais OK, silence = démarreur ou sécurité. 3) Allumage bougies, bobines si le moteur tourne mais cale. 4) Alimentation pompe à carburant (bruit 2 sec au contact). Un code OBD précise souvent la piste.
      link:
    - question: Panne mécanique ou électrique — comment savoir ?
      answer: |
        Une panne mécanique est progressive — bruits, vibrations, odeurs, aggravée par la température. Une panne électronique est souvent soudaine avec voyant allumé et sans symptôme sonore. Le scanner OBD identifie les défauts électroniques ; une inspection physique révèle les pannes mécaniques.
      link:
    - question: Que faire si un voyant rouge s'allume en conduisant ?
      answer: |
        Un voyant rouge impose l'arrêt immédiat sécurisé du véhicule (huile, température, frein). Garez-vous dès que possible, coupez le moteur. Relancer un moteur surchauffé ou en manque de pression d'huile cause des dommages irréversibles. Appelez de l'assistance.
      link:
        href: /diagnostic-auto?cluster=moteur
        label: Diagnostics moteur urgents
confidence_score: 0.24
---

# Diagnostic FAQ

Contenu UI servi à `diagnostic-auto._index.tsx` (page hub `/diagnostic-auto`, section FAQ) via `DiagnosticContentService.getFaq()` (ADR-032 PR-6).

Egalement injecté dans le `schema_org` JSON-LD (`@type: FAQPage`) côté `meta()` Remix loader pour SEO.
