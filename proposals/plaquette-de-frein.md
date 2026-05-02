---
schema_version: 2.0.0
id: gamme:plaquette-de-frein
entity_type: gamme
slug: plaquette-de-frein
title: Plaquette de frein
aliases:
- plaquettes de frein
- garniture de frein
- garnitures de frein
lang: fr
created_at: '2026-04-28'
updated_at: '2026-05-02'
truth_level: L2
source_refs:
- kind: recycled
  origin_repo: automecanik-rag
  origin_path: knowledge/gammes/plaquette-de-frein.md
  captured_at: '2026-04-28'
provenance:
  ingested_by: human:@fafa
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: |
  Pilote ADR-033 Phase 1 — enrichi 2026-04-29 avec diagnostic_relations[]
  + entity_data.maintenance. Bumped schema_version 1.0.0 → 2.0.0
  (ADR-033 + ADR-032).

  2026-04-30 : symptom_slug alignés sur slugs DB existants
  (brake_noise_metallic, brake_vibration_pedal — drift batch 20260308 EN
  legacy, utilisable mais NOUVEAUX slugs DB seront FR canon — voir
  feedback_french_only_for_content.md). 2 entrées retirées faute de slug
  DB (distance_freinage_allongee, voyant_freinage_allume).

  2026-05-02 (Phase 4 plan deja-verifier-existant) :
  - Sections H2 alignées sur ordre canon _templates/new-gamme.md
    (Définition / Fonction / Symptômes d'usure / Critères de choix /
    Compatibilité véhicule / Intentions SEO observées /
    Questions fréquentes / Sources et provenance / Points à vérifier)
  - aliases EN retirés (règle FR exclusif feedback_french_only_for_content.md) :
    "brake pad", "brake pads" supprimés
  - target_classes étendu KB_Knowledge → KB_Knowledge + KB_Catalog (gamme catalog)
  - diagnostic_relations[] : 2 nouvelles entrées seront ajoutées
    POST-merge PR monorepo #269 (distance_freinage_allongee +
    voyant_freinage_allume créés en DB par cette PR)
  - Section "Conseil pédagogique d'entretien" intégrée dans
    "Critères de choix" (canon ne prévoit pas section dédiée)
  - FAQ étendue de 3 → 5 questions

  À reviewer humainement avant promotion vers wiki/gammes/.

  Tous les diagnostic_relations[].evidence ont reviewed=false +
  diagnostic_safe=false (défaut conservateur ADR-033 §D4).
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
diagnostic_relations:
- symptom_slug: brake_noise_metallic
  system_slug: freinage
  relation_to_part: possible_cause
  part_role: 'grincement aigu / bruit métallique au freinage — plaquette usée à
    la limite ou contaminée (huile, gravillons), ou mal montée'
  evidence:
    confidence: medium
    source_policy: 2_medium_concordant
    reviewed: false
    diagnostic_safe: false
    confidence_score_computed: 1.0
  sources:
  - bosch_fad_2020
  - oem_renault_clio_iii_workshop
- symptom_slug: brake_vibration_pedal
  system_slug: freinage
  relation_to_part: symptom_amplifier
  part_role: 'vibration dans la pédale de frein — plaquette dont la friction
    inégale aggrave un voile de disque préexistant'
  evidence:
    confidence: medium
    source_policy: 2_medium_concordant
    reviewed: false
    diagnostic_safe: false
    confidence_score_computed: 0.6
  sources:
  - bosch_fad_2020
  - tecdoc_15_02_01_brake_noise
entity_data:
  pg_id: 402
  family: freinage
  intents:
  - diagnostic
  - achat
  - entretien
  - remplacement
  vlevel: V2
  related_parts:
  - disque-de-frein
  - etrier-de-frein
  - kit-de-frein-arriere
  kw_top: []
  maintenance:
    educational_advice: Vérifier l'épaisseur minimum 3 mm avant un long trajet ; remplacer
      toujours par paire sur le même train.
    related_pages:
    - disque-de-frein
    - etrier-de-frein
confidence_score: 0.48
---

# Plaquette de frein

> 📥 **Pilote ADR-033 Phase 1** — fiche enrichie `diagnostic_relations[]` + `entity_data.maintenance` (ADR-032). Sections H2 ordre canon Phase 4 plan deja-verifier-existant.

## Définition

La plaquette de frein est la garniture de friction pressée par l'étrier hydraulique contre le disque de frein pour ralentir le véhicule de manière progressive et répétable. Pièce d'usure standard, remplacée par paire sur chaque train (avant ou arrière).

## Fonction

Au freinage, la pression hydraulique dans l'étrier pousse les plaquettes contre le disque. La friction transforme l'énergie cinétique en chaleur, ralentissant la roue. Les plaquettes s'usent progressivement à l'usage normal — une garniture neuve fait typiquement entre 6 et 12 mm selon le modèle ; en dessous de 3 mm, le remplacement devient nécessaire.

## Symptômes d'usure

> Cette pièce **peut contribuer** à certains symptômes du système de freinage, sans en être systématiquement la cause unique. Le modèle diagnostic complet (causes probabilistes, vérifications) vit dans la DB `__diag_symptom` et l'outil diagnostic — pas ici.

- 🔊 **Grincement aigu au freinage** *(possible cause, slug DB `brake_noise_metallic`)* — usure à la limite, contamination de la garniture (huile, gravillons), ou mauvaise mise en place [^1][^2]
- 🛑 **Vibration dans la pédale de frein** *(symptom amplifier, slug DB `brake_vibration_pedal`)* — peut s'ajouter à un voile de disque préexistant, plaquette à friction inégale [^1][^3]

> **Note Phase 4** : 2 manifestations supplémentaires liées à la plaquette (`distance_freinage_allongee`, `voyant_freinage_allume`) seront ajoutées en `diagnostic_relations[]` **POST-merge PR monorepo #269** qui crée les 2 slugs FR canon manquants en DB. Voir `review_notes` pour la trace.

## Critères de choix

Pour un véhicule de plus de 1500 kg ou un usage urbain intensif, privilégier des plaquettes haute résistance thermique homologuées **ECE R90** (norme européenne minimale pour pièces de remplacement, garantissant performance équivalente aux pièces d'origine).

Le couple plaquette/disque doit être cohérent — éviter de mélanger une plaquette céramique haute performance avec un disque ventilé d'origine bas de gamme, sous peine de dégradation accélérée du disque.

> **Conseil entretien** : vérifier l'épaisseur minimum 3 mm avant un long trajet ; remplacer toujours par paire sur le même train (avant ensemble OU arrière ensemble, jamais une seule plaquette).

## Compatibilité véhicule

Pour vérifier la compatibilité plaquette ↔ véhicule, utiliser le sélecteur sur le site (sélection marque/modèle/année/motorisation) ou interroger la base `__seo_pg_aliases` (référence : `pg_id: 402`).

Pièces complémentaires fréquemment associées au remplacement :

- [[disque-de-frein]] — à inspecter systématiquement lors du changement de plaquettes
- [[etrier-de-frein]] — vérifier la liberté du piston, l'état des soufflets
- [[kit-de-frein-arriere]] — pour les véhicules à freinage arrière à disques

## Intentions SEO observées

`entity_data.intents` : `diagnostic`, `achat`, `entretien`, `remplacement` (4 intents → fiche transverse).

`vlevel: V2` (top intent : entretien + diagnostic, volume de recherche élevé).

`kw_top` : à compléter Phase 5 via DB `__seo_keywords` queries scopées sur la famille `freinage` + intents listés.

## Questions fréquentes

### Quand changer les plaquettes de frein ?

Quand l'épaisseur de la garniture descend sous 3 mm, ou plus tôt si un capteur d'usure déclenche l'alerte tableau de bord [^1].

### Faut-il changer les disques en même temps que les plaquettes ?

Pas systématiquement. Inspecter les disques : épaisseur minimum gravée sur le moyeu, état de surface, voile au comparateur. Remplacement disque + plaquette si disque usé ou voilé [^1][^3].

### Combien de temps durent des plaquettes neuves ?

Très variable selon usage : 30 000 à 80 000 km en moyenne. Conduite urbaine intensive ou véhicule lourd → durée réduite [^1].

### Qu'est-ce que l'homologation ECE R90 ?

Norme européenne minimale pour pièces de remplacement de freinage. Garantit que la plaquette de remplacement offre une performance équivalente à la pièce d'origine constructeur. Obligatoire pour la sécurité — privilégier toujours des plaquettes ECE R90.

### Peut-on monter des plaquettes asymétriquement (avant seul, arrière seul) ?

Oui — les plaquettes avant s'usent généralement plus vite que les arrière. Mais TOUJOURS remplacer **par paire sur le même train** : avant ensemble OU arrière ensemble. Jamais une seule plaquette d'un côté pour éviter le déséquilibre de freinage.

## Sources et provenance

Voir `source_refs` dans le frontmatter pour la provenance recyclée (origine `automecanik-rag/knowledge/gammes/plaquette-de-frein.md`).

Sources canoniques utilisées dans `diagnostic_relations[].sources` (toutes en `status: to_capture` actuellement — voir `_quality/sources-brief.md` + Phase 7 plan parent) :

[^1]: `bosch_fad_2020` — Bosch FAD 2020 Brochure Réparation Freinage, p.27 et p.31. Source `type: brochure`, `confidence: medium`. License `proprietary-manufacturer` — capture en citations YAML uniquement (Phase 7, preset `manuel-constructeur-pdf` à livrer).
[^2]: `oem_renault_clio_iii_workshop` — Manuel d'atelier Renault Clio III, section freinage. Source `type: oem_workshop`, à corroborer pour atteindre `confidence: high`. License `proprietary-manufacturer` — citation seule (Phase 7).
[^3]: `tecdoc_15_02_01_brake_noise` — TecDoc fiche 15.02.01 — Diagnostic sonore au freinage. Source `type: tecdoc_official`. License `proprietary-manufacturer` (sous licence partenariat TecDoc) — citation seule (Phase 7).

## Points à vérifier

- [ ] Vérifier `entity_data.pg_id: 402` aligné DB `__seo_pg_aliases` Supabase
- [ ] Confirmer `vlevel: V2` (vérifier `r7-curation-method.md` vault)
- [ ] Compléter `aliases` si autres variantes commerciales (FR uniquement — règle `feedback_french_only_for_content.md`)
- [x] **2026-04-30** : `diagnostic_relations[]` aligné sur slugs DB existants (`brake_noise_metallic`, `brake_vibration_pedal` — legacy EN drift batch 20260308, utilisable)
- [ ] **POST-PR monorepo #269 merged** : ajouter 2 entrées `diagnostic_relations[]` pour `distance_freinage_allongee` + `voyant_freinage_allume` (slugs FR canon créés par cette PR)
- [ ] Capturer 3 sources `to_capture` (cf. `_quality/sources-brief.md` + Phase 7) : `bosch_fad_2020`, `oem_renault_clio_iii_workshop`, `tecdoc_15_02_01_brake_noise`
- [ ] Compléter `entity_data.kw_top` via DB `__seo_keywords` (scope famille `freinage` + intents)
- [ ] Construire `_coverage/plaquette-de-frein.coverage.yaml` (Phase 5 plan parent)
- [ ] Décider promotion → `wiki/gammes/plaquette-de-frein.md` (commit message obligatoire `promotion-from-proposals: plaquette-de-frein`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
- [ ] Flip humain ciblé `evidence[*].diagnostic_safe: true` reste interdit tant que les sources ne sont pas corroborées par OEM (commit signé reviewer ≠ auteur, ADR-033 §D4)
