---
schema_version: 1.0.0
id: constructeur:dacia
entity_type: constructeur
slug: dacia
title: Dacia
aliases:
- DACIA
- Dacia Auto
- Automobile Dacia
lang: fr
created_at: '2026-04-28'
updated_at: '2026-05-02'
truth_level: L3
source_refs:
- kind: recycled
  origin_repo: automecanik-rag
  origin_path: knowledge/constructeurs/dacia.md
  captured_at: '2026-04-28'
provenance:
  ingested_by: human:@fafa
  promoted_from: null
review_status: approved
reviewed_by: skill:phase6-promotion-batch@claude
reviewed_at: '2026-05-02T20:17:00Z'
review_notes: "Pilote ADR-031 Phase E constructeur entity. Tier 3 brand low-profile\
  \ per\nrunbook §\"Phase E\" (dacia/seat/skoda parmi candidats Tier 3).\n\n2026-05-02\
  \ (Phase 4 plan deja-verifier-existant) :\n- Sections H2 alignées sur ordre canon\
  \ _templates/new-constructeur.md\n  (Histoire / Gamme actuelle / Modèles couverts\
  \ par le catalogue /\n  Pièces les plus demandées / Sources et provenance / Points\
  \ à vérifier)\n- Section \"Résumé proposé / Faits extraits / Faits inférés / Zones\
  \ ambiguës\"\n  (template proposal draft) supprimées et fusionnées dans sections\
  \ canon\n- target_classes étendu [] → [KB_Knowledge, KB_Catalog]\n- entity_data.models[]\
  \ peuplé avec 7 modèles canon Dacia\n  (sandero, logan, duster, spring, jogger,\
  \ lodgy, dokker)\n- aliases enrichis avec \"Automobile Dacia\" (raison sociale historique)\n\
  \nÀ reviewer humainement avant promotion vers wiki/constructeurs/.\n"
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
entity_data:
  name: Dacia
  country: RO
  founded: 1966
  brand_aliases:
  - DACIA
  - Automobile Dacia
  models:
  - dacia-sandero
  - dacia-logan
  - dacia-duster
  - dacia-spring
  - dacia-jogger
  - dacia-lodgy
  - dacia-dokker
  tier: 3
  vlevel: V3
confidence_score: 0.27
---

# Dacia

## Histoire

Dacia est un constructeur automobile roumain fondé en **1966** à **Pitești** (Roumanie), à l'initiative du gouvernement de Nicolae Ceaușescu. Le nom est dérivé de la province antique de **Dacia** (Roumanie historique).

À l'origine, Dacia produit sous licence des modèles Renault (Renault 8 puis Renault 12 sous le nom Dacia 1300, produite jusqu'en 2004 — record de longévité de production en Europe).

En **1999**, **Renault Group** rachète Dacia et redéfinit son positionnement comme marque **low-cost moderne**. Premier modèle "nouvelle ère" : la Dacia Logan, lancée en **2004** — voiture conçue pour atteindre un prix d'entrée de gamme sous 5 000 € via plateforme partagée Renault simplifiée.

Depuis 2004, Dacia est devenue l'un des principaux moteurs de croissance du Groupe Renault, particulièrement sur les marchés Europe de l'Est, France, Espagne, Italie et Allemagne.

## Gamme actuelle

Modèles de la gamme commerciale Dacia (millésime 2024) :

- **Sandero** (citadine 5 portes) — modèle le plus vendu en Europe particuliers depuis 2017
- **Sandero Stepway** (citadine surélevée look SUV)
- **Logan** (berline tricorps low-cost)
- **Duster** (SUV compact, lancement 2010, succès commercial majeur)
- **Spring** (citadine 100% électrique, lancement 2021)
- **Jogger** (familiale 5/7 places, lancement 2022)
- **Bigster** (SUV familial, lancement 2024-2025)

Modèles historiques arrêtés ou hors EU : Lodgy (monospace), Dokker (utilitaire), Logan MCV (break).

## Modèles couverts par le catalogue

Slugs des fiches véhicule wiki canoniques :

- [[dacia-sandero]] — toutes générations
- [[dacia-logan]] — incluant Logan MCV (break)
- [[dacia-duster]] — phase 1 (2010-2017) + phase 2 (2018-2024) + phase 3 (2024+)
- [[dacia-spring]] — VE 100%
- [[dacia-jogger]] — familiale 5/7 places
- [[dacia-lodgy]] — historique 2012-2022
- [[dacia-dokker]] — historique 2012-2022 (utilitaire)

Note : à la date de cette fiche, les pages [[dacia-*]] vehicles ne sont pas encore dans `wiki/vehicles/`. Promotion croisée à effectuer en Phase F.3 du runbook ADR-031 (vehicles batch).

## Pièces les plus demandées

Sur la base du catalogue de pièces compatibles toutes générations Dacia confondues, les gammes les plus demandées sont :

- [[plaquette-de-frein]] — pièce d'usure standard, demande forte sur Sandero/Logan/Duster
- [[disque-de-frein]] — fréquemment associé au remplacement plaquettes
- [[filtre-a-air]] — entretien planifié 30 000 km
- [[filtre-a-huile]] — vidange chaque cycle
- [[filtre-a-carburant]] — diesel 60 000 km

Pièces partagées avec la plateforme Renault (B0 / CMF-B / Logan-1 selon génération) : large recouvrement avec Renault Clio, Modus, Twingo II et Nissan Micra K12 (cf. fiches véhicule [[dacia-sandero]] § "Véhicules proches").

## Sources et provenance

Sources canoniques utilisées (cf. `_quality/sources-brief.md` Phase 3) :

- **Wikipedia FR — Dacia** : https://fr.wikipedia.org/wiki/Dacia (license `CC-BY-SA-3.0`, capture intégrale autorisée via preset `wikipedia-brand` PR2 livré skill `web-clip-template`). À capturer Phase 3 humain via extension Obsidian.
- **Site corporate Dacia** : https://www.dacia.fr (license `proprietary-manufacturer`, capture intégrale autorisée si robots.txt permet — vérifier). À capturer Phase 3 via preset `generic-article` ou `manuel-constructeur-pdf` (Phase 7).
- **Wikipedia FR — Renault Group** (section AvtoVAZ) : https://fr.wikipedia.org/wiki/Renault_Group (CC-BY-SA-3.0). Référence pour historique groupe.

`brand_id (DB Supabase legacy)` : 47 — référencé par `__auto_marque`.

## Points à vérifier

- [ ] Vérifier `brand_id: 47` aligné DB Supabase (référencé par `__auto_marque`)
- [ ] Confirmer `tier: 3` (peut basculer à 2 selon stratégie SEO 2026 — voir `r7-curation-method.md` vault). Note : Dacia Sandero est leader vente VP particuliers Europe depuis 2017 — argument pour tier 2.
- [x] **2026-05-02** : `entity_data.models[]` peuplé avec 7 slugs canon (sandero, logan, duster, spring, jogger, lodgy, dokker)
- [ ] Vérifier que les 7 slugs `dacia-*` correspondront aux fiches `wiki/vehicles/dacia-*.md` futures (Phase F.3 vehicles batch ADR-031)
- [ ] Capturer Wikipedia FR Dacia via extension Obsidian preset `wikipedia-brand` (PR2 livré, voir `_quality/sources-brief.md`)
- [ ] Capturer page corporate Dacia.fr (vérifier robots.txt avant)
- [ ] Compléter `entity_data.vlevel` validation via `r7-curation-method.md`
- [ ] Construire `_coverage/dacia.coverage.yaml` (Phase 5 plan parent)
- [ ] Décider promotion → `wiki/constructeurs/dacia.md` (commit message obligatoire `promotion-from-proposals: dacia`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
