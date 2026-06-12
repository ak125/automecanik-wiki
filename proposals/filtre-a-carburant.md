---
schema_version: 2.0.0
id: gamme:filtre-a-carburant
entity_type: gamme
slug: filtre-a-carburant
title: Filtre à carburant
aliases:
- filtre carburant
- filtre à gazole
- filtre à essence
lang: fr
created_at: '2026-06-12'
updated_at: '2026-06-12'
truth_level: L2
source_refs:
- kind: raw
  path: recycled/rag-knowledge/gammes/filtre-a-carburant.md
- kind: raw
  path: recycled/rag-knowledge/_raw/evidence/filtre-a-carburant.yml
provenance:
  ingested_by: agent:claude-code@degrippage-wave1
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: "Wave 1 ADR-083 (2026-06-12) — proposal composée STRICTEMENT depuis\
  \ le RAW recyclé (recycled/rag-knowledge/gammes/filtre-a-carburant.md, v5_ssot\
  \ 2026-04-03, pg_id 9) + évidence multi-sources (_raw/evidence). Zéro contenu\
  \ inventé. Créée pour (1) entrer dans le funnel WIKI et (2) résoudre le wikilink\
  \ [[filtre-a-carburant]] de la fiche filtre-a-air (fratrie filtration).\n"
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
- KB_Knowledge
- KB_Catalog
confidence_score: 0.54
---

# Filtre à carburant

## Définition

Le filtre à carburant retient l'eau et les impuretés du carburant pour protéger les injecteurs et la pompe. Pièce de maintenance périodique du circuit d'alimentation, présente sur les motorisations essence comme diesel (le gazole contenant davantage d'impuretés, son filtre est remplacé plus fréquemment).

## Fonctionnement

Placé sur la ligne d'alimentation entre le réservoir et le système d'injection, le filtre piège l'eau et les particules avant qu'elles n'atteignent la pompe et les injecteurs. Un filtre saturé restreint progressivement le débit de carburant : la perte est d'abord perceptible à forte demande (montée, accélération), puis au quotidien. Actions d'entretien associées : remplacer, changer, purger (amorçage du circuit après remplacement d'un filtre diesel).

## Symptômes d'usure

- Perte de puissance progressive, surtout en montée ou à forte charge
- À-coups à l'accélération
- Démarrage difficile ou laborieux
- Cliquetis ou ratés moteur
- Odeur de carburant autour du véhicule

> Distinction utile (source RAW) : filtre = perte **progressive** ; injecteur défaillant = un cylindre mort (vibrations, fumée). La valise de diagnostic tranche.

## Choix selon véhicule

Critères de sélection : marque, modèle et année du véhicule (le sélecteur véhicule du site fait cette vérification). Intervalle : suivre la préconisation constructeur — repères usuels du corpus : diesels HDI/TDI 20 000–30 000 km, essences jusqu'à 60 000 km. Ne pas attendre la panne complète pour intervenir.

Pièces de la même famille d'entretien filtration : [[filtre-a-air]], [[filtre-a-huile]], [[filtre-d-habitacle]] (et filtre de boîte automatique le cas échéant). Chaque filtre a un rôle spécifique — vérifier le type exact avant commande.

## FAQ

### Essence vs diesel : même fréquence ?

Non. Diesels HDI/TDI : 20 000–30 000 km. Essences : jusqu'à 60 000 km. Le gazole contient plus d'impuretés.

### Comment savoir si mon filtre carburant est HS ?

Symptômes : perte de puissance en montée, à-coups à l'accélération, démarrage laborieux.

### Faut-il purger le filtre diesel neuf ?

Oui, après remplacement il faut amorcer le circuit. Pompez jusqu'à sentir une résistance.

### Filtre carburant ou injecteurs : comment distinguer ?

Filtre = perte progressive. Injecteur = un cylindre mort (vibrations, fumée). La valise de diagnostic tranche.

### Diagnostic express : ma voiture a des à-coups

1) À-coups à l'accélération = filtre suspect. 2) À-coups au ralenti = injecteur/bobine. Commencez par le filtre.

## Sources et provenance

Contenu composé exclusivement depuis le RAW recyclé (voir `source_refs`) :

- `recycled/rag-knowledge/gammes/filtre-a-carburant.md` — fiche v5 SSOT (rôle, symptômes S1–S5, critères, FAQ rendering, intervalles), pg_id 9, truth_level L2, dernière passe 2026-04-03.
- `recycled/rag-knowledge/_raw/evidence/filtre-a-carburant.yml` — évidence multi-sources web avec lineage par bloc.

## Points à vérifier

- [ ] Revue humaine du wording FAQ avant export SEO (exportable.seo reste false)
- [ ] Compléter les intervalles avec sources OEM par constructeur (Phase capture)
