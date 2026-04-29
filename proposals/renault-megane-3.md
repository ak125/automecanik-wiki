---
schema_version: 1.0.0
id: vehicle:renault-megane-3
entity_type: vehicle
slug: renault-megane-3
title: Fiche vehicule - Renault Megane 3
aliases: []
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/vehicles/renault-megane-3.md
    captured_at: '2026-04-29'
provenance:
  ingested_by: skill:recycle-from-rag@v0.1
  promoted_from:
lineage_id: 019dd8ee-daff-7056-ae32-9e931fce9fff
review_status: proposed
reviewed_by:
reviewed_at:
review_notes: Phase F batch ADR-031. Recyclé depuis automecanik-rag par recycle-from-rag.py. Source body sha256=7d7f60d8d7915405ca6a69cf96aa77bc93a8e46ad2a9955e111de195cf6b199f. À reviewer humainement avant promotion vers wiki/vehicles/.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  make: renault
  model: megane-3
content_hash: sha256:99910db4b341b52e477f939cba9e3940b3bca7a6d8437046ce0561298a6bb382
---

# Fiche vehicule - Renault Megane 3

> 📥 **Proposition Phase F** — extraite par `recycle-from-rag.py` depuis `knowledge/vehicles/renault-megane-3.md`.
> source body sha256 : `7d7f60d8d7915405ca6a69cf96aa77bc93a8e46ad2a9955e111de195cf6b199f`
> À reviewer manuellement avant promotion vers `wiki/vehicles/renault-megane-3.md`.

## Faits extraits (source body brut, à structurer)

# Renault Megane 3 (2008-2016)

## Identification

- **Generation** : III
- **Production** : 2008 - 2016
- **Segment** : C (compacte)
- **Carrosseries** : 3 portes, 5 portes, Estate (break), Coupe, CC (cabriolet), RS

## Motorisations principales

### Essence

| Moteur  | Puissance  | Code moteur |
| ------- | ---------- | ----------- |
| 1.6 16v | 110 ch     | K4M         |
| 1.4 TCe | 130 ch     | H4J         |
| 2.0 TCe | 180 ch     | F4R         |
| 2.0 RS  | 250/265 ch | F4R         |

### Diesel

| Moteur  | Puissance  | Code moteur |
| ------- | ---------- | ----------- |
| 1.5 dCi | 90/110 ch  | K9K         |
| 1.6 dCi | 130 ch     | R9M         |
| 1.9 dCi | 130 ch     | F9Q         |
| 2.0 dCi | 150/160 ch | M9R         |

## Pieces d'usure courantes

### Freinage

- **Plaquettes avant** : 30-40 000 km
- **Disques avant** : 60-80 000 km
- **Freins arriere** : Disques ou tambours selon version

### Filtration

- **Filtre a huile** : A chaque vidange
- **Filtre a air** : 30 000 km
- **Filtre habitacle** : 15 000 km
- **Filtre a gasoil** (dCi) : 60 000 km

### Distribution

- **1.5 dCi (K9K)** : Courroie, 90 000 km ou 6 ans
- **1.6 dCi (R9M)** : Chaine (sans entretien)
- **2.0 dCi (M9R)** : Courroie, 120 000 km ou 6 ans
- **1.6 16v (K4M)** : Courroie, 120 000 km ou 6 ans
- **TCe** : Chaine (sans entretien)

## Problemes connus

### Moteur 1.5 dCi (K9K)

- Injecteurs : Defaillance frequente (claquement, fumee)
- Vanne EGR : Encrassement rapide
- Turbo : Controle huile regulier, geometrie variable

### Moteur 1.6 dCi (R9M)

- Injecteurs piezo : Couteux a remplacer
- Courroie accessoires : Galet tendeur a surveiller

### Moteur 2.0 dCi (M9R)

- Volant moteur bimasse : Bruit au ralenti
- Pompe HP : Copeaux metalliques possibles

### Electricite

- Carte main libre : Problemes de detection
- Tableau de bord : Pixels defaillants
- Feux arriere LED : Bandeaux LED HS

### Chassis

- Roulements avant : Usure normale 80-100k km
- Silent-blocs berceau : Claquements
- Cardans : Soufflets a surveiller

## Intervalles d'entretien

### Vidange

- **Essence** : 20 000 km ou 1 an
- **Diesel** : 20 000 km ou 1 an

### Liquide de frein

- Tous les 2 ans ou 60 000 km

## References OEM courantes

| Piece                    | Reference Renault |
| ------------------------ | ----------------- |
| Filtre a huile 1.5 dCi   | 8200768913        |
| Filtre a air 1.5 dCi     | 8200431051        |
| Plaquettes avant         | 410607115R        |
| Disques avant            | 402069518R        |
| Kit distribution 1.5 dCi | 130C17529R        |

## Conseils d'entretien

1. **Huile moteur** : 5W-30 C3 ou C4 selon version
1. **Liquide refroidissement** : Type D (jaune/vert)
1. **Direction assistee** : Electrique (pas de fluide)
1. **Boite EDC** : Vidange huile 60 000 km

## Specificites par version

### Megane RS (250/265 ch)

- Freinage Brembo 4 pistons
- Chassis Cup disponible (sport)
- Differentiel autobloquant (option Trophy)
- Entretien plus frequent recommande

### Megane CC

- Toit rigide retractable : Verifier joints et verins
- Hydraulique toit : Controle niveau

## Points de review

- [ ] Vérifier `entity_data` complet et aligné DB monorepo (`vehicle`)
- [ ] Compléter ou corriger les `aliases`
- [ ] Décider promotion vers `wiki/vehicles/renault-megane-3.md` ou ajustement
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO>`
