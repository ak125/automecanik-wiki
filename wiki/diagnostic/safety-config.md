---
schema_version: 1.0.0
id: diagnostic:safety-config
entity_type: diagnostic
slug: safety-config
title: Diagnostic — Safety / Risk / Urgency config
aliases:
  - safety gate
  - risk levels
  - urgency labels
lang: fr
created_at: '2026-04-29'
updated_at: '2026-04-29'
truth_level: L4
source_refs:
  - kind: snapshot
    origin_repo: nestjs-remix-monorepo
    origin_path: frontend/app/routes/diagnostic-auto.$slug.tsx
    origin_lines: '124-205'
    captured_at: '2026-04-29'
provenance:
  ingested_by: claude:adr-032-rg-1
  promoted_from: proposals/diagnostic-safety-config.md
review_status: published
reviewed_by: claude
reviewed_at: '2026-04-29'
review_notes: |
  Snapshot 1:1 des constants TS hardcodés (SAFETY_GATE_CONFIG, RISK_CONFIG,
  URGENCY_CONFIG, SKILL_CONFIG, CTX_PHASE/TEMP/FREQ_LABELS).
no_disputed_claims: true
exportable:
  rag: false
  seo: false
  support: false
target_classes: []
entity_data:
  safety_gate:
    none: { icon: CheckCircle, color: text-green-600, bg: bg-green-50, label: '' }
    warning: { icon: AlertTriangle, color: text-yellow-600, bg: bg-yellow-50, label: '⚠️ À surveiller' }
    stop_soon: { icon: AlertOctagon, color: text-cta, bg: bg-cta-50, label: '⚠️ Contrôle sous 24h' }
    stop_immediate: { icon: XCircle, color: text-red-600, bg: bg-red-50, label: '⛔ NE PAS ROULER' }
  risk_levels:
    critique: { label: Critique, color: 'bg-red-100 text-red-800 border-red-300' }
    securite: { label: Sécurité, color: 'bg-cta-50 text-cta-hover border-cta-light' }
    confort: { label: Confort, color: 'bg-blue-100 text-blue-800 border-blue-300' }
  urgency:
    immediate: { label: Immédiat, color: text-red-600 }
    soon: { label: Sous 48h, color: text-cta }
    scheduled: { label: Planifier, color: text-blue-600 }
  skill:
    diy: { label: Bricoleur, icon: Wrench }
    amateur: { label: Amateur, icon: Wrench }
    professional: { label: Professionnel, icon: ScanLine }
  ctx_phase:
    demarrage: 🔵 Démarrage
    ralenti: 🔵 Ralenti
    acceleration: 🔵 Accélération
    freinage: 🔵 Freinage
    virage: 🔵 Virage
    vitesse_stable: 🔵 Vitesse stable
    arret: 🔵 À l'arrêt
  ctx_temp:
    froid: ❄️ Moteur froid
    chaud: 🔥 Moteur chaud
  ctx_freq:
    intermittent: '🟡 Intermittent (probable: capteur/électronique)'
    permanent: '🔴 Permanent (probable: mécanique/usure)'
    progressif: '🟠 Progressif (probable: usure/fuite)'
    sporadique: '⚪ Sporadique (probable: électronique/température)'
---

# Diagnostic Safety / Risk / Urgency config

Contenu UI servi à `diagnostic-auto.$slug.tsx` via `DiagnosticContentService.getSafetyConfig()` (ADR-032 PR-6).

## Safety gate

4 gates ordonnés du moins critique (`none`) au plus critique (`stop_immediate` = ⛔ NE PAS ROULER). Voir `entity_data.safety_gate`.

## Risk levels

3 niveaux de risque côté UI (badge couleur). `critique` = casse moteur potentielle, `securite` = tenue de route dégradée, `confort` = pas dangereux mais gênant.

## Urgency, skill, context labels

Voir `entity_data.urgency`, `entity_data.skill`, `entity_data.ctx_*` pour les autres mappings.
