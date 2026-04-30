---
schema_version: 2.0.0
id: gamme:plaquette-de-frein
entity_type: gamme
slug: plaquette-de-frein
title: Plaquette de frein
aliases:
- plaquettes de frein
- brake pad
- brake pads
- garniture de frein
lang: fr
created_at: '2026-04-28'
updated_at: '2026-04-30'
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
review_notes: 'Pilote ADR-033 Phase 1 — enrichi 2026-04-29 avec diagnostic_relations[]
  + entity_data.maintenance.

  Bumped schema_version 1.0.0 → 2.0.0 (ADR-033 + ADR-032).

  2026-04-30 : symptom_slug alignés sur convention DB __diag_symptom (anglais
  snake_case brake_*). 4 → 2 diagnostic_relations[] : 2 remaps validés contre
  inventaire DB (brake_noise_metallic, brake_vibration_pedal), 2 retirés faute
  de slug DB existant (distance_freinage_allongee, voyant_freinage_allume).

  À reviewer humainement avant promotion vers wiki/gamme/.

  Tous les diagnostic_relations[].evidence ont reviewed=false + diagnostic_safe=false
  (défaut conservateur ADR-033 §D4).

  '
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
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
  maintenance:
    educational_advice: Vérifier l'épaisseur minimum 3 mm avant un long trajet ; remplacer
      toujours par paire sur le même train.
    related_pages:
    - disque-de-frein
    - etrier-de-frein
confidence_score: 0.48
---

# Plaquette de frein

> 📥 **Pilote ADR-033 Phase 1** — fiche enrichie 2026-04-29 avec `diagnostic_relations[]` + `entity_data.maintenance` (ADR-032). Schema bumped to 2.0.0.

## Définition

La plaquette de frein est la garniture de friction pressée par l'étrier hydraulique contre le disque de frein pour ralentir le véhicule de manière progressive et répétable. Pièce d'usure standard, remplacée par paire sur chaque train.

## Fonctionnement

Au freinage, la pression hydraulique dans l'étrier pousse les plaquettes contre le disque. La friction transforme l'énergie cinétique en chaleur, ralentissant la roue. Les plaquettes s'usent progressivement à l'usage normal — une garniture neuve fait typiquement entre 6 et 12 mm selon le modèle ; en dessous de 3 mm, le remplacement devient nécessaire.

## Symptômes système auxquels cette pièce peut contribuer

> Cette pièce **peut contribuer** à certains symptômes du système de freinage, sans en être systématiquement la cause unique. Le modèle diagnostic complet (causes probabilistes, vérifications) vit dans la DB `__diag_symptom` et l'outil diagnostic — pas ici.

- 🔊 **Grincement aigu au freinage** *(possible cause, slug DB `brake_noise_metallic`)* — usure à la limite, contamination de la garniture (huile, gravillons), ou mauvaise mise en place [^1][^2]
- 🛑 **Vibration dans la pédale de frein** *(symptom amplifier, slug DB `brake_vibration_pedal`)* — peut s'ajouter à un voile de disque préexistant, plaquette à friction inégale [^1][^3]

(Note hors body : 2 manifestations supplémentaires liées à la plaquette ne sont pas exposées ici car elles ne disposent pas encore d'un slug `__diag_symptom` en DB — voir `review_notes` du frontmatter pour la trace.)

## Conseil pédagogique d'entretien

> Vérifier l'épaisseur minimum 3 mm avant un long trajet ; remplacer toujours par paire sur le même train.

Voir aussi : [[disque-de-frein]], [[etrier-de-frein]].

## Choix selon véhicule

Pour un véhicule de plus de 1500 kg ou un usage urbain intensif, privilégier des plaquettes haute résistance thermique homologuées **ECE R90** (performances minimales pour pièces de remplacement). Le couple plaquette/disque doit être cohérent — éviter de mélanger une plaquette céramique haute performance avec un disque ventilé d'origine bas de gamme, sous peine de dégradation accélérée du disque.

## FAQ

### Quand changer les plaquettes de frein ?

Quand l'épaisseur de la garniture descend sous 3 mm, ou plus tôt si un capteur d'usure déclenche l'alerte tableau de bord [^1].

### Faut-il changer les disques en même temps que les plaquettes ?

Pas systématiquement. Inspecter les disques : épaisseur minimum gravée sur le moyeu, état de surface, voile au comparateur. Remplacement disque + plaquette si disque usé ou voilé [^1][^3].

### Combien de temps durent des plaquettes neuves ?

Très variable selon usage : 30 000 à 80 000 km en moyenne. Conduite urbaine intensive ou véhicule lourd → durée réduite [^1].

---

[^1]: `bosch_fad_2020` — Bosch FAD 2020 Brochure Réparation Freinage, p.27 et p.31. Source `type: brochure`, `confidence: medium` (cf. `_meta/source-catalog.yaml`).
[^2]: `oem_renault_clio_iii_workshop` — Manuel d'atelier Renault Clio III, section freinage. Source `type: oem_workshop`, à corroborer pour atteindre `high`.
[^3]: `tecdoc_15_02_01_brake_noise` — TecDoc fiche 15.02.01 — Diagnostic sonore au freinage. Source `type: tecdoc_official`.

## Points de review (à compléter avant promotion)

- [ ] Vérifier `entity_data.pg_id: 402` aligné DB `__seo_pg_aliases` Supabase
- [ ] Confirmer `vlevel: V2` (vérifier rules-seo-vlevel.md vault)
- [ ] Compléter `aliases` si autres variantes commerciales
- [x] **2026-04-30** : aligné `diagnostic_relations[]` sur convention `__diag_symptom.slug` DB (anglais snake_case `brake_*`). 2 entrées remappées (`bruit_grincement_freinage` → `brake_noise_metallic`, `vibration_pedale_frein` → `brake_vibration_pedal`), 2 entrées orphelines retirées (`distance_freinage_allongee`, `voyant_freinage_allume`) — à proposer en DB via PR séparée avant ré-ajout dans la fiche.
- [ ] Capturer le manuel atelier Renault Clio III réel dans `automecanik-raw/sources/web-clips/` (`oem_renault_clio_iii_workshop` reste `status: to_capture` dans `_meta/source-catalog.yaml`)
- [ ] Capturer/archiver les 3 autres sources `status: to_capture` (`bosch_fad_2020`, `tecdoc_15_02_01_brake_noise`, `oem_filter_maintenance_general`) avant promotion canonique
- [ ] Décider promotion → `wiki/gamme/plaquette-de-frein.md` (commit message obligatoire `promotion-from-proposals: plaquette-de-frein`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
- [ ] Flip humain ciblé `evidence[*].diagnostic_safe: true` reste interdit tant que les sources ne sont pas corroborées par OEM (commit signé reviewer ≠ auteur, ADR-033 critère §9)
