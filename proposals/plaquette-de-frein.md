---
schema_version: "1.0.0"
id: "gamme:plaquette-de-frein"
entity_type: gamme
slug: plaquette-de-frein
title: Plaquette de frein
aliases:
  - plaquettes de frein
  - brake pad
  - brake pads
  - garniture de frein
lang: fr
created_at: "2026-04-28"
updated_at: "2026-04-28"
truth_level: L3
source_refs:
  - kind: recycled
    origin_repo: automecanik-rag
    origin_path: knowledge/gammes/plaquette-de-frein.md
    captured_at: "2026-04-28"
provenance:
  ingested_by: human:@fafa
  promoted_from: null
review_status: proposed
reviewed_by: null
reviewed_at: null
review_notes: |
  Pilote ADR-031 Phase E. Source = canon freinage 13/13 dans automecanik-rag.
  À reviewer humainement avant promotion vers wiki/gamme/.
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
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
---

# Plaquette de frein

> 📥 **Proposition pilote ADR-031 Phase E** — extraite manuellement depuis `automecanik-rag/knowledge/gammes/plaquette-de-frein.md` (canon freinage 13/13).
> À reviewer manuellement avant promotion vers `wiki/gamme/plaquette-de-frein.md`.

## Résumé proposé

Garniture de friction pressée contre le disque par l'étrier hydraulique pour ralentir le véhicule de manière progressive et répétable. Pièce d'usure standard, remplacée par paire sur chaque train.

## Faits extraits

- **Famille** : freinage
- **Pièces liées** : disque de frein, étrier de frein, kit de frein arrière
- **Norme** : ECE R90 (performances freinage pièces de remplacement)
- **Doit toujours impliquer** : friction, étrier, disque

## Faits inférés

- Intents SEO observés : diagnostic, achat, entretien, remplacement
- V-Level : V2 (top 20 — `business_priority: high` + `monthly_searches: ~8000`)

## Zones ambiguës / contradictions

Aucune sur ce pilote. La fiche source automecanik-rag est canon freinage 13/13 (ref `r7-curation-method.md`).

## Points de review

- [ ] Vérifier `entity_data.pg_id: 402` aligné DB `__seo_pg_aliases` Supabase
- [ ] Confirmer `vlevel: V2` (vérifier rules-seo-vlevel.md vault)
- [ ] Compléter `aliases` si autres variantes commerciales
- [ ] Décider promotion → `wiki/gamme/plaquette-de-frein.md` ou ajustement
- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO date-time>`
