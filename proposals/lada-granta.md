---
schema_version: 2.0.0
id: vehicle:lada-granta
entity_type: vehicle
slug: lada-granta
title: Lada Granta
aliases:
  - LADA Granta
  - ВАЗ-2190
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L3
source_refs:
  - kind: manual
    note: 'Données identité et motorisation depuis catalogue constructeur AvtoVAZ (Groupe Renault) ; à confirmer par capture web-clip'
    author: 'human:@fafa'
provenance:
  ingested_by: 'human:@fafa'
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: |
  Pilote G6 vehicle ADR-031. Constructeur AvtoVAZ (groupe Renault, tier 3 low-profile).
  Schema 2.0.0 — pas de diagnostic_relations[] ni maintenance bloc (réservés entity_type gamme).
  À capturer le catalogue AvtoVAZ officiel dans automecanik-raw/sources/web-clips/ avant promotion.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes:
  - KB_Knowledge
entity_data:
  make: lada
  model: granta
---

# Lada Granta

> 📥 **Pilote G6 Phase E ADR-031** — fiche vehicle pour valider le flux end-to-end sur entity_type non-gamme.
> À reviewer humainement avant promotion vers `wiki/vehicles/lada-granta.md`.

## Identité

- **Constructeur** : AvtoVAZ (groupe Renault depuis 2008)
- **Modèle** : Granta
- **Code interne** : ВАЗ-2190 (sedan), ВАЗ-2191 (liftback), ВАЗ-2192 (hatchback), ВАЗ-2194 (universal)
- **Production** : 2011 → présent (génération initiale lancée 2011, restylage 2018)
- **Segment** : B (compacte familiale, marché Russie/CIS principalement)
- **Carrosseries** : berline 4 portes, liftback 5 portes, hatchback 5 portes, break

## Spécificités

- Plate-forme partagée avec la Lada Kalina (génération précédente AvtoVAZ).
- Moteurs 4-cylindres essence atmosphériques carter aluminium (architecture VAZ historique).
- Conçue pour usage routes dégradées : suspensions plus longues, garde au sol relevée par rapport aux compactes occidentales équivalentes.
- Compatibilité pièces : large recouvrement avec Kalina et Priora pour pièces d'usure (filtration, freinage, distribution).

## Motorisations principales

| Moteur | Puissance | Code moteur | Carburant |
|---|---|---|---|
| 1.6 8V | 87 ch | ВАЗ-11186 | Essence |
| 1.6 16V | 98 ch | ВАЗ-21127 | Essence |
| 1.6 16V Sport | 106 ch | ВАЗ-21126 | Essence |

## Pièces fréquentes

Catégories de pièces couramment remplacées sur cette plate-forme. Aucune référence produit précise — voir le catalogue.

- [[filtre-a-air]] — entretien régulier, milieu poussiéreux requiert remplacement plus fréquent
- [[filtre-a-huile]] — vidange typique 10 000-15 000 km
- [[plaquette-de-frein]] — usure normale 30 000-60 000 km selon usage
- [[liquide-de-frein]] — remplacement biennal recommandé

## FAQ

### Le réseau pièces de rechange est-il disponible hors Russie ?

Disponibilité limitée hors marchés CIS/Europe de l'Est. Vérifier la disponibilité catalogue avant intervention pour pièces spécifiques moteur (ВАЗ-11186/21127).

### Compatibilité avec pièces Renault ?

Recouvrement partiel sur certains éléments depuis le rachat AvtoVAZ par Renault (2008), mais la majorité des pièces moteur reste spécifique à la plate-forme VAZ. Confirmer compatibilité au cas par cas.

---

## Points de review (à compléter avant promotion)

- [ ] Capturer le catalogue officiel AvtoVAZ Granta dans `automecanik-raw/sources/web-clips/` (actuellement source `kind: manual`)
- [ ] Confirmer codes moteur ВАЗ-* contre source OEM
- [ ] Vérifier disponibilité des pièces dans `__seo_pg_aliases` Supabase
- [ ] Décider promotion → `wiki/vehicles/lada-granta.md` (commit message obligatoire `promotion-from-proposals: lada-granta`)
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
