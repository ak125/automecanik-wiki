---
type: sources-brief
schema_version: 1.0.0
generated_at: '2026-05-02'
generated_by: 'plan deja-verifier-existant-de-abundant-hanrahan Phase 3'
adr_reference: 'ADR-040 §1 (politique courte citation FR/UE) + ADR-040 §2 (coverage maps)'
---

# Sources brief — proposals enrichment Phase 3

> **Statut** : brief informatif. Aucune capture n'a été effectuée par l'agent (CLAUDE.md raw §"Interdictions absolues" — `sources/` append-only, write agent interdit).
>
> **Workflow capture** : humain via extension Obsidian Web Clipper avec presets du skill canon `automecanik-raw/.claude/skills/web-clip-template/`. **PR2 avancée — 4 presets livrés `_status: pinned`** :
> - `generic-article` (PR1 fallback Schema.org Article, license `unknown-review-required`)
> - `wikipedia-vehicle` (CC-BY-SA-3.0, truth_level L3, trigger `/^https:\/\/fr\.wikipedia\.org\/wiki\/.+$/`)
> - `wikipedia-brand` (CC-BY-SA-3.0, truth_level L3, trigger même que vehicle, discrimination par humain)
> - `mecanikard-article` (proprietary-citation-only, truth_level L4, trigger `/^https:\/\/(www\.)?mecanikard\.fr\/.+$/`)
>
> **Restant à livrer skill PR2/PR3** : `manuel-constructeur-pdf`, `oscaro-product`, `forum-auto-thread`, `autoplus-blog`. Pour `caradisiac.com` (pas de preset domain-specific), utiliser `generic-article` avec license override `proprietary-citation-only` au moment du clip.
>
> Une fois capturée, la source apparaît dans `sources/web-clips/<preset>/<slug>.md` (intégrale) ou `sources/citations/<slug>.yaml` (citations seules pour OEM/TecDoc/Bosch — Phase 7).
>
> **Coverage map** : chaque source listée ici alimente un `coverage_entries[]` dans `proposals/_coverage/<slug>.coverage.yaml` (Phase 5) avec `source_status: pending_capture` jusqu'à capture réelle, puis `source_status: captured`.

## Convention licence (réutilisée enum `automecanik-raw/_schemas/web-clip-frontmatter.schema.json`)

| Enum value | Quand l'utiliser |
|---|---|
| `CC-BY-SA-3.0` / `CC-BY-SA-4.0` | Wikipedia FR/EN, contenu Creative Commons partage à l'identique |
| `proprietary-citation-only` | mecanikard, caradisiac, autoplus, forum-auto — courte citation analytique FR/UE (Art. L122-5 CPI), ≤200 mots, jamais de republication intégrale |
| `proprietary-no-redistribute` | oscaro, sites e-commerce sous ToS scraping — métadonnées seules |
| `proprietary-manufacturer` | Manuels atelier OEM Renault/PSA/VAG/Ford, brochures Bosch FAD copyrightées, fiches TecDoc — citations seules ≤200 mots |
| `unknown-review-required` | Fallback pour source non identifiée — force review humaine |

## Stratégie sourcing public-first

**Phase 3 (cette campagne)** : capture des sources **publiques captables intégralement** (Wikipedia CC-BY-SA + brochures marketing constructeur publiques librement téléchargeables). ~80% des sources nécessaires sont publiques.

**Phase 7 (différé, post-skill mature)** : capture des sources OEM/TecDoc/Bosch en citations YAML via skill `web-clip-template` PR2 mergée + preset `manuel-constructeur-pdf`.

---

## Fiches gammes (2)

### `plaquette-de-frein`

**Sources publiques captables Phase 3 (humain via extension)** :

| URL candidate | preset_target | license | claim_coverage | priority |
|---|---|---|---|---|
| https://fr.wikipedia.org/wiki/Frein_à_disque | `wikipedia-tech` (à créer) ou `generic-article` | `CC-BY-SA-3.0` | plaquette-fonctionnement, plaquette-symptomes-usure | 1 |
| https://fr.wikipedia.org/wiki/Plaquette_de_frein | `wikipedia-tech` ou `generic-article` | `CC-BY-SA-3.0` | plaquette-definition, plaquette-criteres-choix | 1 |
| https://eur-lex.europa.eu/eli/reg/2009/661 (réglementation ECE R90 freinage) | `generic-article` | `proprietary-no-redistribute` (texte juridique UE — référence URL seulement) | plaquette-homologation-ECE-R90 | 2 |

**Sources OEM/TecDoc/Bosch (Phase 7 — différé)** :

| source_slug | license | claim_coverage |
|---|---|---|
| `oem_renault_clio_iii_workshop` | `proprietary-manufacturer` | plaquette-grincement-causes (corroboration) |
| `tecdoc_15_02_01_brake_noise` | `proprietary-manufacturer` | plaquette-vibration-pedale-cause |
| `bosch_fad_2020` | `proprietary-manufacturer` | plaquette-fonctionnement, plaquette-recommandations |

**Action humaine attendue Phase 3** :
- [ ] Capturer 2 Wikipedia FR (frein à disque + plaquette de frein) via extension Obsidian Web Clipper preset `generic-article` ou `wikipedia-tech`
- [ ] Référencer URL EUR-Lex ECE R90 dans `_coverage/plaquette-de-frein.coverage.yaml` (capture intégrale non requise pour texte juridique public)

---

### `filtre-a-air`

**Sources publiques captables Phase 3** :

| URL candidate | preset_target | license | claim_coverage | priority |
|---|---|---|---|---|
| https://fr.wikipedia.org/wiki/Filtre_à_air | `wikipedia-tech` ou `generic-article` | `CC-BY-SA-3.0` | filtre-air-definition, filtre-air-fonctionnement | 1 |
| https://fr.wikipedia.org/wiki/Filtration | `wikipedia-tech` ou `generic-article` | `CC-BY-SA-3.0` | filtre-air-principe-filtration | 2 |

**Sources OEM Phase 7** :

| source_slug | license | claim_coverage |
|---|---|---|
| `oem_filter_maintenance_general` | `proprietary-manufacturer` | filtre-air-intervalles-entretien |
| `bosch_fad_2020` (sections filtration) | `proprietary-manufacturer` | filtre-air-types-cellulose-coton |

**Action humaine Phase 3** :
- [ ] Capturer Wikipedia FR Filtre à air via extension preset `generic-article`

---

## Fiche constructeur (1)

### `dacia`

**Sources publiques captables Phase 3** :

| URL candidate | preset_target | license | claim_coverage | priority |
|---|---|---|---|---|
| https://fr.wikipedia.org/wiki/Dacia | `wikipedia-brand` (PR2 livré) ou `generic-article` | `CC-BY-SA-3.0` | dacia-histoire, dacia-renault-group-1999 | 1 |
| https://www.dacia.fr/ (page d'accueil corporate) | `manuel-constructeur-pdf` ou `generic-article` | `proprietary-manufacturer` (capture intégrale autorisée — site marketing public) | dacia-gamme-actuelle | 2 |
| https://fr.wikipedia.org/wiki/Renault_Group (section AvtoVAZ) | `wikipedia-brand` | `CC-BY-SA-3.0` | dacia-groupe-renault-historique | 3 |

**Action humaine Phase 3** :
- [ ] Capturer Wikipedia Dacia via preset `wikipedia-brand` (à créer Phase 2 skill) ou `generic-article`
- [ ] Capturer page d'accueil Dacia.fr (si capture autorisée par robots.txt — vérifier)

---

## Fiche support (1)

### `livraison`

**Sources internes Phase 3 (CGV AutoMecanik)** :

| Source | preset_target | license | claim_coverage | priority |
|---|---|---|---|---|
| `automecanik_legal_cgv_2026` (interne) | `legal` (sources/legal/) | `proprietary-citation-only` (interne — redistribuable selon CGV) | livraison-conditions-france, livraison-conditions-domtom, livraison-conditions-belgique-luxembourg | 1 |
| https://www.colissimo.fr/conditions-generales-vente | `generic-article` | `proprietary-citation-only` | livraison-transporteur-colissimo-delais | 2 |
| https://www.chronopost.fr/conditions-generales | `generic-article` | `proprietary-citation-only` | livraison-transporteur-chronopost-delais | 2 |
| https://www.mondialrelay.fr/conditions-generales | `generic-article` | `proprietary-citation-only` | livraison-transporteur-mondialrelay | 2 |

**Action humaine Phase 3** :
- [ ] Stocker CGV AutoMecanik 2026 dans `automecanik-raw/sources/legal/automecanik_legal_cgv_2026.md` (source interne, pas via Web Clipper)
- [ ] Capturer 3 pages CGV transporteurs via extension preset `generic-article`

**Bloqueur Phase 6** : `legal_reviewed_by` doit être renseigné (revue juridique externe AutoMecanik) avant promotion vers `wiki/support/livraison.md`. Sinon fiche reste `proposals/` (règle safe-by-default ADR-040 §5).

---

## Fiches vehicles (6)

### `citroen-c3`

| URL candidate | preset_target | license | claim_coverage | priority |
|---|---|---|---|---|
| https://fr.wikipedia.org/wiki/Citroën_C3 | `wikipedia-vehicle` (PR2 livré) ou `generic-article` | `CC-BY-SA-3.0` | c3-identification-generations, c3-motorisations | 1 |
| https://www.citroen.fr/univers-citroen/heritage-citroen/c3.html (corporate heritage) | `generic-article` | `proprietary-manufacturer` | c3-histoire-3-generations | 2 |
| https://www.caradisiac.com/fiches-techniques/modele--citroen-c3/ | `generic-article` | `proprietary-citation-only` (≤200 mots) | c3-caracteristiques-techniques | 3 |

**OEM Phase 7** :
- `oem_psa_citroen_c3_workshop` (`proprietary-manufacturer`) — problèmes connus moteur EP6/HDi, références OEM PSA

---

### `ford-focus-3`

| URL candidate | preset_target | license | claim_coverage | priority |
|---|---|---|---|---|
| https://fr.wikipedia.org/wiki/Ford_Focus | `wikipedia-vehicle` ou `generic-article` | `CC-BY-SA-3.0` | focus-3-identification-c346, focus-3-motorisations | 1 |
| https://www.ford.fr/voitures-anciennes/focus-3 (si page existe) ou archive | `generic-article` | `proprietary-manufacturer` | focus-3-versions-st-rs | 2 |
| https://www.caradisiac.com/fiches-techniques/modele--ford-focus/ | `generic-article` | `proprietary-citation-only` | focus-3-caracteristiques-techniques | 3 |

**OEM Phase 7** :
- `oem_ford_focus_iii_workshop` — problèmes 1.0 EcoBoost, boîte Powershift DCT

---

### `peugeot-206`

| URL candidate | preset_target | license | claim_coverage | priority |
|---|---|---|---|---|
| https://fr.wikipedia.org/wiki/Peugeot_206 | `wikipedia-vehicle` ou `generic-article` | `CC-BY-SA-3.0` | 206-identification-T1-T3, 206-motorisations | 1 |
| https://www.peugeot.fr/marque-et-technologie/heritage/peugeot-206 (heritage) ou archive | `generic-article` | `proprietary-manufacturer` | 206-versions-RC-CC-GTI | 2 |
| https://www.caradisiac.com/fiches-techniques/modele--peugeot-206/ | `generic-article` | `proprietary-citation-only` | 206-caracteristiques-techniques | 3 |

**OEM Phase 7** :
- `oem_psa_peugeot_206_workshop` — problèmes 1.4 HDi DV4, BSI fusibles

---

### `renault-clio-3`

> Note : déjà enrichi en Phase 1 avec blocs caradisiac fusionnés depuis ex-doublon clio-iii. Sources existantes sont citées dans `review_notes`.

| URL candidate | preset_target | license | claim_coverage | priority |
|---|---|---|---|---|
| https://fr.wikipedia.org/wiki/Renault_Clio_III | `wikipedia-vehicle` ou `generic-article` | `CC-BY-SA-3.0` | clio-3-identification-BR-CR, clio-3-motorisations-D4F-K9K-K4M-F4R | 1 |
| https://www.caradisiac.com/fiches-techniques/modele--renault-clio-3/2009/ | `generic-article` | `proprietary-citation-only` | clio-3-caracteristiques-techniques-detaillees (DÉJÀ référencé fiche, à capturer formellement) | 1 (déjà cité) |
| https://www.renault.fr/heritage/clio-iii (heritage) ou archive | `generic-article` | `proprietary-manufacturer` | clio-3-rappels-constructeur, clio-3-injecteurs-delphi | 2 |
| https://rappel.renault.fr/ (page rappels constructeur) | `generic-article` | `proprietary-manufacturer` | clio-3-rappels-injecteurs-platine-pedale | 2 |

**OEM Phase 7** :
- `oem_renault_clio_iii_workshop` — vanne EGR, turbo BorgWarner KP35, FAP régénération
- `oem_renault_glaceol_rx_spec` — liquide refroidissement Type D

---

### `renault-megane-3`

| URL candidate | preset_target | license | claim_coverage | priority |
|---|---|---|---|---|
| https://fr.wikipedia.org/wiki/Renault_Mégane_III | `wikipedia-vehicle` ou `generic-article` | `CC-BY-SA-3.0` | megane-3-identification, megane-3-motorisations-K4M-H4J-F4R-K9K-R9M-F9Q-M9R | 1 |
| https://www.renault.fr/heritage/megane-iii (heritage) ou archive | `generic-article` | `proprietary-manufacturer` | megane-3-versions-rs-cc-coupe | 2 |
| https://www.caradisiac.com/fiches-techniques/modele--renault-megane-3/ | `generic-article` | `proprietary-citation-only` | megane-3-caracteristiques-techniques | 3 |

**OEM Phase 7** :
- `oem_renault_megane_iii_workshop` — boîte EDC vidange, carte main libre, tableau bord pixels

---

### `volkswagen-golf-6`

| URL candidate | preset_target | license | claim_coverage | priority |
|---|---|---|---|---|
| https://fr.wikipedia.org/wiki/Volkswagen_Golf_VI | `wikipedia-vehicle` ou `generic-article` | `CC-BY-SA-3.0` | golf-6-identification-5K, golf-6-motorisations-TSI-TDI | 1 |
| https://www.volkswagen.fr/heritage/golf (heritage) ou archive | `generic-article` | `proprietary-manufacturer` | golf-6-versions-gti-r-gtd | 2 |
| https://www.caradisiac.com/fiches-techniques/modele--volkswagen-golf-6/ | `generic-article` | `proprietary-citation-only` | golf-6-caracteristiques-techniques | 3 |

**OEM Phase 7** :
- `oem_vag_golf_vi_workshop` — chaîne 1.4 TSI étirement, mécatronique DSG, pompe à eau électrique

---

## Récap actions humaines Phase 3

**Sources publiques à capturer humainement via extension Obsidian Web Clipper** (~13 captures) :

- **Wikipedia FR (CC-BY-SA-3.0)** — preset `generic-article` ou `wikipedia-vehicle` / `wikipedia-brand` / `wikipedia-tech` (à créer Phase 2 skill) :
  1. https://fr.wikipedia.org/wiki/Frein_à_disque
  2. https://fr.wikipedia.org/wiki/Plaquette_de_frein
  3. https://fr.wikipedia.org/wiki/Filtre_à_air
  4. https://fr.wikipedia.org/wiki/Dacia
  5. https://fr.wikipedia.org/wiki/Citroën_C3
  6. https://fr.wikipedia.org/wiki/Ford_Focus
  7. https://fr.wikipedia.org/wiki/Peugeot_206
  8. https://fr.wikipedia.org/wiki/Renault_Clio_III
  9. https://fr.wikipedia.org/wiki/Renault_Mégane_III
  10. https://fr.wikipedia.org/wiki/Volkswagen_Golf_VI

- **CGV AutoMecanik 2026** — fichier interne dans `automecanik-raw/sources/legal/automecanik_legal_cgv_2026.md` (humain édite directement le fichier — source interne, pas via Web Clipper)

- **caradisiac fiche technique Renault Clio 3 2009** — déjà référencée dans clio-3.md, à capturer formellement avec citation courte ≤200 mots

**Skill PR2 avancée** : `wikipedia-vehicle` + `wikipedia-brand` + `mecanikard-article` livrés `_status: pinned`. `wikipedia-tech` (pour pages techniques transverses comme "frein à disque", "filtre à air") **non livré** — workaround : utiliser `wikipedia-vehicle` (truth_level L3) ou `generic-article` (L4 + override `license: CC-BY-SA-3.0` manuel au clip).

**Restant à livrer skill PR2/PR3 avant Phase 7** : `manuel-constructeur-pdf` (OEM workshops), `oscaro-product`, `forum-auto-thread`, `autoplus-blog`. Pour `caradisiac.com` : pas de preset domain-specific prévu — `generic-article` avec license override `proprietary-citation-only`.

---

## Récap sources OEM/TecDoc différées Phase 7

À capturer via skill mature (PR1 + PR2 mergées) avec preset `manuel-constructeur-pdf` (license `proprietary-manufacturer`, citations YAML ≤200 mots) :

- `oem_renault_clio_iii_workshop`, `oem_renault_megane_iii_workshop` (Renault)
- `oem_psa_citroen_c3_workshop`, `oem_psa_peugeot_206_workshop` (PSA)
- `oem_ford_focus_iii_workshop` (Ford)
- `oem_vag_golf_vi_workshop` (VAG)
- `oem_filter_maintenance_general` (compilation OEM filtration)
- `tecdoc_15_02_01_brake_noise` (TecDoc fiche)
- `bosch_fad_2020` (Bosch FAD brochure freinage)

Quand ces 9 sources seront capturées Phase 7, les fiches concernées passeront de `confidence_score ~0.84-0.94` à `~0.95+` (cible `high` atteignable selon ADR-040 §4 `2_medium_concordant` → `1_high` upgrade).

---

## Références

- ADR-040 — Wiki Proposal Evidence & Conditional Promotion Contract (vault PR pending)
- Plan exécution : `/home/deploy/.claude/plans/deja-verifier-existant-de-abundant-hanrahan.md`
- Skill canon : `automecanik-raw/.claude/skills/web-clip-template/` + `_internal/obsidian-clipper-spec.md`
- License enum canon : `automecanik-raw/_schemas/web-clip-frontmatter.schema.json`
- Memory : `feedback_french_only_for_content.md` (règle FR exclusif contenus)
- CLAUDE.md raw §"Interdictions absolues" (append-only `sources/`)
