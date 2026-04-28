# hot.md

> Mémoire chaude des agents — synthèse des règles critiques à charger au début de session.

## Architecture active

- `automecanik-raw` = sources brutes immuables + recyclées
- `automecanik-wiki` = connaissance canonique (CE REPO)
- `automecanik-rag` = pipeline RAG, chunks, chatbot
- `nestjs-remix-monorepo` = application + SEO R0-R8 + publication
- `governance-vault` = ADR, règles, décisions

## Règles critiques

- Ne jamais confondre raw et wiki
- Ne jamais importer un CSV complet dans wiki
- Ne jamais exporter vers chatbot / RAG / SEO sans `_meta/quality-gates.md` PASS
- Ne jamais inventer une compatibilité véhicule
- Ne jamais marquer `validated` ou `human_reviewed` sans validation humaine

## R8 spécial

- Génération R8 future : `__rag_proposals` DB (ADR-022)
- Migration R8 existante : raw/recycled → validation → wiki/vehicles/
- Pas de `proposals/vehicles/` parallèle

## État actuel (2026-04-28)

Phase pilote — squelette créé, aucune fiche canonique encore.
4 propositions pilote prévues : gammes + constructeurs + support + 1 vehicle.
