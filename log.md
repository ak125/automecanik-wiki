# Log

> Journal append-only de toutes les opérations sur ce repo. Pas de modifications rétroactives.

## \[2026-04-28\] init | Création repo `automecanik-wiki`

- Squelette initial créé : `inbox/`, `proposals/`, `wiki/`, `maps/`, `_meta/`, `exports/`
- Règles `CLAUDE.md` + principes raw → wiki posés
- Quality gates `_meta/quality-gates.md` initial
- `agent-exit-contract.md` hérité du monorepo
- Aucune fiche canonique encore — phase pilote à venir (Phase 4 ADR-031)

## 2026-04-28 — feat/phase-e-pilot-proposals (auto)

- **Branche** : `feat/phase-e-pilot-proposals`
- **Décision** : feat(phase-e): pilot proposals (4) + schema bug fix + validator _*.md skip
- **Sortie** : PR #3 | commits 9b61e5d

## 2026-04-28 — feat/phase-e-pilot-proposals (auto)

- **Branche** : `feat/phase-e-pilot-proposals`
- **Décision** : fix(phase-e): apply mdformat + skip _*.md in validator argv path (+2 other commits)
- **Sortie** : PR #3 | commits 1b42110 1d0092e 9b61e5d

## 2026-04-29 — feat/phase-f3-vehicles-batch (auto)

- **Branche** : `feat/phase-f3-vehicles-batch`
- **Décision** : feat(phase-f3): vehicles batch — 7 proposals + 1 skip + lada-granta cleanup
- **Sortie** : PR #6 | commits ab66984

## 2026-04-30 — feat/mvp-g2-g10-bootstrap (auto)

- **Branche** : `feat/mvp-g2-g10-bootstrap`
- **Décision** : fix(ci): exclude wiki/ + proposals/ from mdformat to preserve Obsidian syntax (+2 other commits)
- **Sortie** : PR #8 | commits 399c0eb 768abd9 baa5793

## 2026-05-01 — feat/p5-confidence-drift-gate (auto)

- **Branche** : `feat/p5-confidence-drift-gate`
- **Décision** : feat(p5): wire wiki-symptom-confidence pre-commit + mark field readOnly in schema
- **Sortie** : PR #12 | commits 61dfa38

## 2026-05-03 — fix/claude-md-adr-status-refresh (auto)

- **Branche** : `fix/claude-md-adr-status-refresh`
- **Décision** : docs(claude): refresh ADR refs (031 accepted, 022 conditional, 033 added)
- **Sortie** : PR aucune | commits 4ae9237

## 2026-06-12 — feat/proposals-enrich-tierA-wave1 (auto)

- **Branche** : `feat/proposals-enrich-tierA-wave1`
- **Décision** : feat(proposals): enrichissement sourcé filtre-a-air → TIER A + 2 proposals sœurs (ADR-083 wave 1)
- **Sortie** : PR #39 | commits da9c16d

## 2026-06-12 — feat/proposals-enrich-tierA-wave1 (auto)

- **Branche** : `feat/proposals-enrich-tierA-wave1`
- **Décision** : feat(proposals): boucle scraping wave 1 — 3/3 TIER A (filtre-a-carburant + filtre-d-habitacle rejoignent filtre-a-air) (+2 other commits)
- **Sortie** : PR #39 | commits 74ac0b3 f7db4d3 da9c16d

## 2026-06-13 — fix/promote-move-semantics (auto)

- **Branche** : `fix/promote-move-semantics`
- **Décision** : fix(wiki): promote.py move-semantics — supprime la proposal après écriture du canon
- **Sortie** : PR #41 | commits 2ca8d62

## 2026-06-17 — feat/gate-anti-inflation-phase0 (auto)

- **Branche** : `feat/gate-anti-inflation-phase0`
- **Décision** : feat(_scripts): anti-inflation advisory report (Phase 0, report-only)
- **Sortie** : PR #49 | commits e627438

## 2026-06-17 — feat/gate-anti-inflation-phase0 (auto)

- **Branche** : `feat/gate-anti-inflation-phase0`
- **Décision** : feat(_scripts): Phase 1 — conformance schéma autoritaire (report-only) (+2 other commits)
- **Sortie** : PR #49 | commits 4319aac 52679aa e627438

## 2026-06-17 — feat/gate-anti-inflation-phase0 (auto)

- **Branche** : `feat/gate-anti-inflation-phase0`
- **Décision** : fix(_scripts): anti-inflation report — robustesse report-only (no-crash fiche malformée) (+4 other commits)
- **Sortie** : PR #49 | commits 68b5247 c4a4eed 4319aac 52679aa e627438

## 2026-06-18 — feat/citation-readiness-phase1a (auto)

- **Branche** : `feat/citation-readiness-phase1a`
- **Décision** : feat(_scripts): citation-readiness-report — AI citation readiness (report-only, Phase 1a)
- **Sortie** : PR aucune | commits 0e00f33

## 2026-06-18 — feat/citation-readiness-phase1a (auto)

- **Branche** : `feat/citation-readiness-phase1a`
- **Décision** : refactor(_scripts): citation-readiness v2.0 — couche FORME citable, substance déléguée à shadow_score (no parallel (+2 other commits)
- **Sortie** : PR #51 | commits bcd7358 9545820 0e00f33

## 2026-06-18 — feat/citation-readiness-phase1a (auto)

- **Branche** : `feat/citation-readiness-phase1a`
- **Décision** : test(_scripts): citation-readiness — tests hermétiques au câblage shadow_score (+4 other commits)
- **Sortie** : PR #51 | commits a8b85c2 da22df2 bcd7358 9545820 0e00f33

## 2026-06-18 — feat/adr088-engineblock-schema (auto)

- **Branche** : `feat/adr088-engineblock-schema`
- **Décision** : feat(schema): ADR-088 — engineBlock factuel + related_gammes/commerce_intent (additif)
- **Sortie** : PR #50 | commits f9a65ed

## 2026-06-18 — feat/adr088-engineblock-schema (auto)

- **Branche** : `feat/adr088-engineblock-schema`
- **Décision** : feat(_scripts): ADR-088 Phase 3.2 — reality-manifest framework (generateur ops + reader 0-DB) (+2 other commits)
- **Sortie** : PR #50 | commits b11a156 684caba f9a65ed

## 2026-06-27 — fix/build-exports-seo-exportable-audience-gate (auto)

- **Branche** : `fix/build-exports-seo-exportable-audience-gate`
- **Décision** : fix(exports-seo): gate SEO export sur exportable.seo (mapping audience), pas truthy
- **Sortie** : PR #70 | commits 4b700c3

## 2026-09-13 — candidat editorial filtre-a-huile

Correction proposee du passage sur la presence des clapets, appuyee sur une capture RAW FILTRON dans le candidat isole raw-filtre-pilot-20260913. Source-catalog et coverage relies aux manifest/hash natifs; une archive disponible ne vaut pas validation factuelle. Deux formulations non justifiees par cette source retirees des passages corriges. Frontmatter, coverage et raw_ref cibles PASS. Score0.46 inchange, promotion dry-run BLOCKED; exports false. Evidence et coverage au vault: ledger/audit-trail/editorial-pipeline-evidence-20260912/filtre-pilot-verification.md. Aucune promotion ni export.

## 2026-09-14 — candidat filtre-a-huile : preuve MAHLE de conception

- Capture RAW native immuable, passage technique Spin-on oil filter mix up rattache au catalogue/coverage ; deux affirmations captured, sans verified.
- Remplacement de la hierarchie universelle de medias fondee sur transmission ; criteres Markdown, resume et bloc structure alignees. Ancien claim remplace, pas conserve comme preuve.
- Proprietes selon moteur seulement ; aucune valeur de pression, intervalle, compatibilite exacte ou performance marketing extrapolee. Provenance historique distinguee de la validation actuelle.
- Validation native et limites : voir preuves mahle-pilot-* du dossier editorial. Proposition et exports inchanges ; aucune promotion appliquee.

## 2026-09-14 — candidat claims-pilot : ancrage réel et échéance constructeur

- Validateur coverage natif : text_anchor déclaré doit exister dans un bloc de prose de sa section H2/H3 unique. Parsing CommonMark, exclusions code/commentaires/URL, normalisation Unicode/espaces ; pas de similarité sémantique ni preuve factuelle implicite. Champ absent reste optionnel selon schéma canon.
- Dépendance markdown-it-py 3.0.0 utilisée et déclarée dans les exigences déjà installées par CI. Aucune nouvelle règle canon ni workflow parallèle.
- Filtre à huile : échéance constructeur remplace chaque-vidange et raccourci huile synthétique/intervalle long. Réemploi MAHLE immuable ; carte 14 déclarations dont 4 captured, aucune verified. Les 12 anciennes entrées pending examinées et dispositions dans les preuves du lot.
- 197 tests ciblés PASS ; schéma fiche et score0.46 PASS. Promotion BLOCKED avec COVERAGE_STRICT_FAIL (10 ancres restantes) et SUBSTANCE_SCORE. Contrôle structurel 15 propositions : 1PASS/6WARN/8FAIL ; corpus non corrigé artificiellement. Aucun export/DB/site modifié.

## 2026-09-14 — candidat architecture-pilot : architectures et clapets

- Architecture vissé/cartouche réécrite selon MAHLE, structure variants et résumé alignés ; généralisation clapets-cartouche dans boîtier moteur retirée faute de preuve, retrait tracé.
- Anti-retour lié à l'orientation sans généraliser une position ambiguë ; by-pass expliqué sur colmatage/froid selon FILTRON. Réglage selon moteur rattaché à MAHLE, sans chiffres ou extrapolation diagnostique validés.
- Quatre déclarations ciblées reliées aux passages des archives existantes ; aucune capture ni mutation RAW. Carte14déclarations,8captured,0verified ;6ancres encore en échec (ISO3, réglementaire2, diagnostic1).
- Schéma, calcul0.46, SHA et raw_ref cibles PASS. Promotion native BLOCKED : COVERAGE_STRICT_FAIL et SUBSTANCE_SCORE. Shadow89/tierA ne vaut pas publication :6page_unproven et reality stale. Code/test/dépendance du lot197tests précédent inchangés par hash ; validations de données rejouées.

## 2026-09-14 — candidat iso-pilot : portée des méthodes d'essai

- Trois mentions ISO reliées aux notices officielles par édition ; section de lecture des résultats et bloc structuré alignés. Retrait des formules normalisée et du raccourci bêta non étayé dans le bloc.
- Les notices établissent des objets d'essai, pas une certification, une compatibilité ou une performance produit. Texte intégral des normes non lu. Ambiguïté 2007/2008 du résumé ISO-9 tracée, édition du titre conservée.
- Capture native de la première notice : HTTP403 ; aucun contournement ou archive fabriquée. Les trois déclarations restent pending_capture et les sources to_capture. Demandes de capture préparées uniquement dans le candidat RAW.
- Résultats et limites : iso-pilot-* dans le dossier de preuves du vault. Pas de promotion ou export appliqué.

## 2026-09-14 — candidat proof-gate : preuve indépendante du score

- Contre-preuve : sept cas sans preuve suffisante étaient ELIGIBLE avec score injecté0.99, évaluateurs couverture/provenance réels. Quatre autres contre-preuves montrent archive supprimée/modifiée, hash inventaire absent et archive changée avant application acceptés auparavant.
- Extension des contrôles natifs : couverture de promotion exige carte non vide, ancre, état de capture et page active avec hash ; la préparation conserve les états pending. Le gate RAW lit et hache les archives référencées, refuse chemins hors RAW et ambiguïtés. Le snapshot inclut leurs octets ; racines explicites/environnement alignées entre évaluation et application.
- 232tests ciblés PASS dont23nouveauxcas ; modes legacy/6dim éprouvés sans bascule runtime. Schéma/code py_compile et diff ciblé PASS. Pas de nouvel outil, dépendance ou changement des poids/seuils.
- Filtre à huile : six preuves en attente deviennent des motifs explicites de refus, en plus de trois ancres existantes ; score0.46/shadow89 inchangés. Deux archives existantes liées au snapshot ; aucune mutation documentaire/RAW. Prochain travail : pertinence des passages, OE/OES, diagnostic. Preuves proof-gate-* au vault. Aucun commit/export/déploiement.

## 2026-09-14 — candidat oe-quality : définitions et critères de choix

- Classement universel OE/OES/équivalent et liste globale de marques retirés du corps et du bloc structuré. Deux anciennes déclarations retirées avec motif, deux définitions européennes bornées aux paragraphes 19-20 de la consolidation 2023 ; aucun retrait compté comme preuve acquise.
- Source réglementaire historique rectifiée, nouvelle référence EUR-Lex précise, sans archive inventée. Capture native unsupported_mime : aucune archive ; deux déclarations restent pending_capture.
- Recommandations de justificatifs par référence et d'affectation catalogue ; pas de certification ou identité universelle inférée. Score et droits de promotion inchangés. Contrôles et limites : oe-quality-* dans le dossier de preuves du vault.

## 2026-09-14 — candidat diag-pilot : symptômes et conduite à tenir

- Retrait de la chaîne by-pass ouvert/perte de puissance et des fréquences de causes non établies ; corps, FAQ, bloc failure_symptoms et notes de revue alignés. Relations historiques conservées comme hypothèses low, reviewed=false/diagnostic_safe=false ; aucun identifiant ou lien DB modifié.
- Une capture native Renault Clio5phase1 apporte deux affirmations contextualisées de conduite à tenir ; pas de preuve de causalité du filtre. Catalogue content-addressed et carte reliés à l'archive ; ancien claim retiré séparément des deux nouveaux.
- Aucun seuil, code ou statut de publication changé. Données candidates et contrôles : diag-pilot-* au vault. Aucun export/DB/runtime modifié.
