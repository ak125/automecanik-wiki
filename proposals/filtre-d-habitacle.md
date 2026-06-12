---
schema_version: 2.0.0
id: gamme:filtre-d-habitacle
entity_type: gamme
slug: filtre-d-habitacle
title: Filtre d'habitacle
aliases:
- filtre habitacle
- filtre de climatisation
lang: fr
created_at: '2026-06-12'
updated_at: '2026-06-12'
truth_level: L2
source_refs:
- kind: raw
  path: recycled/rag-knowledge/gammes/filtre-d-habitacle.md
provenance:
  ingested_by: agent:claude-code@degrippage-wave1
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: "Wave 1 ADR-083 (2026-06-12) — proposal composée STRICTEMENT depuis\
  \ le RAW recyclé (recycled/rag-knowledge/gammes/filtre-d-habitacle.md, v5_ssot\
  \ 2026-04-03). Zéro contenu inventé. Slug canonique DB = filtre-d-habitacle\
  \ (l'ancienne forme « filtre-habitacle » des wikilinks est corrigée vers ce\
  \ slug). Créée pour (1) entrer dans le funnel WIKI et (2) résoudre le wikilink\
  \ de la fiche filtre-a-air (fratrie filtration).\n"
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

# Filtre d'habitacle

## Définition

Le filtre d'habitacle filtre l'air entrant dans l'habitacle pour protéger les occupants des pollens, poussières et polluants. Pièce d'entretien périodique du circuit de ventilation/climatisation, distincte du filtre à air moteur ([[filtre-a-air]]).

## Fonctionnement

L'air extérieur aspiré par la ventilation traverse le filtre avant diffusion dans la cabine. Deux familles existent dans le corpus : le filtre classique (particules) et le filtre à charbon actif, qui retient aussi les odeurs et gaz nocifs (NOx, ozone) — recommandé en zone urbaine ou pour les personnes sensibles aux odeurs. Un filtre saturé réduit le débit d'air et laisse passer odeurs et humidité.

## Symptômes d'usure

- Buée persistante sur le pare-brise
- Mauvaises odeurs à la mise en route de la ventilation
- Débit d'air faible même en vitesse maximale
- Bruit de ventilation anormal ou sifflement
- Climatisation moins efficace qu'avant

## Choix selon véhicule

Critères de sélection : marque, modèle et année du véhicule (vérification via le sélecteur véhicule du site). Classique ou charbon actif : le charbon actif est recommandé en zone urbaine/polluée. Remplacement : tous les 15 000 à 20 000 km ou une fois par an — plus souvent en ville, idéalement au printemps (pollens).

Erreurs à éviter (source RAW) : ne pas monter le filtre à l'envers (sens du flux indiqué), ne pas rouler sans filtre, vérifier qu'il est bien calé dans son logement.

Pièces de la même famille d'entretien filtration : [[filtre-a-air]], [[filtre-a-huile]], [[filtre-a-carburant]].

## FAQ

### Filtre habitacle classique ou charbon actif ?

Le charbon actif filtre aussi les odeurs et gaz nocifs (NOx, ozone). Recommandé en zone urbaine ou si vous êtes sensible aux odeurs.

### Comment savoir si mon filtre habitacle est saturé ?

Mauvaises odeurs à la ventilation, buée persistante sur le pare-brise, débit d'air faible même en vitesse max, allergies en voiture.

### Tous les combien changer le filtre habitacle ?

Tous les 15 000 à 20 000 km ou 1 fois par an. Plus souvent si vous roulez en ville ou zone polluée. Idéalement au printemps (pollens).

### Peut-on changer le filtre habitacle soi-même ?

Oui, très accessible sur la plupart des véhicules. Souvent derrière la boîte à gants ou sous le pare-brise. 10 minutes sans outil.

### Quelle erreur éviter avec le filtre habitacle ?

Ne pas monter le filtre à l'envers (sens du flux indiqué). Ne pas rouler sans filtre. Vérifier qu'il est bien calé dans son logement.

## Sources et provenance

Contenu composé exclusivement depuis le RAW recyclé (voir `source_refs`) :

- `recycled/rag-knowledge/gammes/filtre-d-habitacle.md` — fiche v5 SSOT (rôle, symptômes S1–S5, critères, FAQ rendering, intervalles), truth_level L2, dernière passe 2026-04-03.

## Points à vérifier

- [ ] Revue humaine du wording FAQ avant export SEO (exportable.seo reste false)
- [ ] Ajouter une seconde source de kind distinct (évidence web dédiée) pour la diversité TIER A
