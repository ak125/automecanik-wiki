# Spec — `numeric_value_verification_gate` (lock valeur numérique sécurité)

> **Design spec, NON-CANON.** Étape 2 de la séquence sûre owner 2026-07-03 :
> `ratifier ADR-093 (non-sécurité) → BÂTIR ce lock → ADR sécurité-auto (Étape 3)`.
> La décision normative (autoriser `safety_auto_approved`) vit dans l'**ADR sécurité-auto**
> à naître **au vault** (Étape 3), pas ici. Ce document spécifie le gate ; il ne l'active pas.
> **Report-only** tant que l'ADR n'existe pas.

## 1. Le trou que ce lock ferme (motif = danger physique, pas bureaucratie)

ADR-093 (`PROPOSED`) automatise déjà l'auto-review NON-sécurité mais **garde la sécurité
humaine en V1 délibérément** : **aucune couche ne vérifie l'EXACTITUDE d'une VALEUR numérique.**
La barre de preuve existante prouve **provenance + structure** (dim A = coverage/source,
`check-coverage-map`, `safety_families`) — **jamais le CHIFFRE**. Sur une pièce freinage, un
couple de serrage faux, une cote mini erronée ou une tolérance auto-généralisée = risque
physique réel. Tant que ce lock n'existe pas, `safety_auto_approved` est **inacceptable**
(position ADR-093, validée owner). Ce gate est la précondition technique de l'Étape 3.

**Preuve que le trou est réel — claims numériques réels de `disque-de-frein`** (scan
`sources/web-research/disque-de-frein/*.md`, `rg` reproductible) :

| #   | Claim numérique réel (RAW OE)                                                  | Défaut d'exactitude                                                                     | Verdict cible                                   |
| --- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- | ----------------------------------------------- |
| 1   | « MIN TH = 27 mm » (exemple Zimmermann 340×30, 5×112)                          | cote **spécifique à UNE référence disque** ; généralisée = fausse sur tout autre disque | `numeric_vehicle_specific_do_not_generalize`    |
| 2   | Faux-rond après montage : Brembo `0,10 mm` · Textar `≤0,07 mm` · ZF `≤0,05 mm` | **contradiction inter-sources** sur la même grandeur                                    | `numeric_ambiguous` (+ `no_disputed_claims` KO) |
| 3   | « DTV `~12-15 µm` » / ATE « `~800 °C` »                                        | valeur **approximative** (`~`, plage) non résolue en seuil ferme                        | `numeric_ambiguous`                             |
| 4   | runout `0,05 mm` **et** `50 µm` mêlés dans le corpus                           | risque **conflit d'unité** (mm↔µm, ×1000) si une reformulation casse la conversion      | `numeric_unit_conflict`                         |
| 5   | Toute valeur ci-dessus, page source `pending_capture`                          | **provenance non capturée** → chiffre invérifiable à la source                          | `numeric_source_not_captured`                   |
| 6   | « épaisseur mini » citée sans dire de quel disque/véhicule                     | **contexte d'application absent**                                                       | `numeric_context_missing`                       |

**Conclusion honnête** : aujourd'hui, **aucun** claim numérique de `disque-de-frein` n'atteint
`numeric_verified` (pages `pending_capture` + contradictions + valeurs véhicule-spécifiques).
Le gate **bloquerait 100 % des valeurs sécurité** de cette fiche — **exactement** cohérent avec
le verdict pipeline actuel `safety_auto_blocked`. Le lock n'est donc pas un garde-fou théorique :
il attrape des défauts présents dans le corpus réel.

## 2. Où il vit — verify-before-invent (ÉTENDRE, ne pas créer une couche)

Vérifié dans le worktree `feat/gap1-auto-authoring-pipeline` :

- **`_scripts/quality-gates.py`** = 13 gates atomiques `gate_*(fm, body, path, source_catalog) -> list[str]`
  (pures, retournent des messages de violation). C'est **là** que naissent les gates atomiques.
- **`_scripts/gates/`** (ADR-059 Phase B PR-4) = couche wrapper Pydantic-typée
  (`GateResult`/`GateViolation`, 5 dimensions : source/claim/contradiction/risk/confidence).
  Principe gravé (`gates/__init__.py`) : **« aucun NOUVEAU wrapper »** — les 5 dimensions ADR-059
  sont figées. Les gates **atomiques**, eux, s'ajoutent (safety_unsourced, maintenance_advice… l'ont été).
- **`_scripts/gap1_auto_review.py`** — Safety Auto-Gate : `no_disputed_claims` est dans
  `NOT_YET_WIRED` (fail-closed). C'est le point d'ancrage du lock.

**Décision de design (RÉVISÉE pendant le build — TDD « écoute le test »)** : la logique a besoin
de `source_status` + `family_ranges` — données que les gates **fiche-seule** de `quality-gates.py`
ne portent pas. Forcer un gate à dépendance-coverage dans `quality-gates.py` (ou threader la
coverage-map dans le wrapper `contradiction_gate`) serait plus couplé, pas moins. Le **précédent
propre** est `safety_families.py` : module PUR autonome, même pipeline GAP-1, même `test_*.py`.

1. **Module pur** `_scripts/numeric_exactitude.py` (précédent `safety_families.py`) — fonctions
   déterministes `extract_values` / `detect_quantity` / `classify` / `gate_numeric_value_exactitude`,
   plages **injectées** (jamais lues dans le module). 0 LLM/DB/réseau. **PAS** de nouveau `gates/` wrapper
   (principe « aucun nouveau wrapper » respecté), **PAS** de pollution de `quality-gates.py` fiche-seule.
1. **Donnée gouvernée** `_meta/numeric-plausibility.yaml` (précédent `source-catalog.yaml`), Option A.
1. **Câblage Safety Auto-Gate** : `gap1_auto_review` appelle le module (comme il appelle déjà
   `safety_families` et `shadow_score`) et produit **un** signal computable `numeric_exactitude_verified`
   consommé par `_safety_auto_gate()` → `compute_verdict()` — True ⇔ toutes les valeurs sécurité
   `numeric_verified`. Fail-closed : KO → `safety_auto_blocked` (raison **technique**, pas humaine).

`no_disputed_claims` **reste dans `NOT_YET_WIRED`** : la détection de la contradiction **inter-sources**
(comparer 0,10 vs 0,07 vs 0,05 pour la MÊME grandeur) n'est **pas** V1 — ces valeurs sont bloquées
`numeric_ambiguous` (grandeur non identifiée / isolée), pas comme contradiction explicite. Vraie
détection de contradiction = V2 (voir §8).

## 3. Entrées

| Entrée                                  | Source                                                                                       | Statut                                         |
| --------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| claims numériques + phrase-hôte         | body H2 authored + `entity_data.editorial[*].content_md`                                     | existant                                       |
| statut page-level de la source du claim | `coverage-map` (`source_status` ∈ pending_capture/captured/verified) + `source-catalog.yaml` | existant (`gen_coverage_map.py`)               |
| contexte d'application                  | frontmatter (`gamme`, `related_gammes`) + tokens véhicule/réf/moteur dans la phrase-hôte     | existant (reality-manifest pour la validation) |
| **plage plausible par famille**         | **`_meta/numeric-plausibility.yaml` (NOUVELLE donnée gouvernée)**                            | **à créer, owner-gated (§7)**                  |

## 4. Les 6 verdicts (spec owner) — sémantique exacte

Fail-closed : en cas de doute, **bloquer** (jamais fail-open). Chaque verdict bloquant = une
chaîne de violation `"<verdict>: <valeur>"` renvoyée par `gate_numeric_value_exactitude`
(sauf `numeric_verified` = pass, aucune violation).

| Verdict                                      | Condition                                                                                                                                                                                                                                                  | Effet                                                              |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `numeric_verified`                           | valeur + unité extraites · rattachée au claim exact · source page-level **`captured`/`verified`** · contexte d'application présent · unité cohérente · **dans la plage plausible famille** · (si critique) **corroborée ≥2 sources indépendantes captées** | **PASS** — seul état autorisant (plus tard) `safety_auto_approved` |
| `numeric_ambiguous`                          | valeur approximative (`~`, plage `12-15`, « environ ») **non résolue en seuil ferme**, OU deux sources donnent des seuils différents non réconciliés                                                                                                       | BLOCK                                                              |
| `numeric_context_missing`                    | valeur sans contexte d'application (quel disque / véhicule / réf / moteur / condition « moderne vs ancien »)                                                                                                                                               | BLOCK                                                              |
| `numeric_unit_conflict`                      | même grandeur exprimée en unités incompatibles sans conversion correcte (mm↔µm, Nm↔daNm), OU unité absente sur une grandeur qui en exige une                                                                                                               | BLOCK                                                              |
| `numeric_source_not_captured`                | page source `pending_capture` (jamais capturée/archivée) → chiffre invérifiable                                                                                                                                                                            | BLOCK                                                              |
| `numeric_vehicle_specific_do_not_generalize` | valeur liée à UNE réf/UN véhicule (ex. MIN TH d'un disque coté) présentée comme **règle générale** de la gamme                                                                                                                                             | BLOCK                                                              |

**Ordre d'évaluation (fail-closed, premier bloquant gagne — CORRIGÉ par TDD)** :
`source_not_captured` → `unit_conflict` → `vehicle_specific` → `context_missing` →
`ambiguous` (plage/approx/isolation) → (sinon) `numeric_verified`.

> `vehicle_specific` **avant** `context_missing` : une cote réf-spécifique énoncée en règle
> générale est une erreur plus précise que « contexte absent » (sinon « l'épaisseur minimale est
> de 27 mm » sortirait `context_missing` au lieu de `vehicle_specific`).

## 5. Checks (spec owner) → décomposition mécanisable

1. **Extraction valeur + unité** — regex sur grandeurs+unités connues
   (`mm|µm|μm|cm|Nm|N·m|daNm|bar|kPa|MPa|°C|%|mm²|kg`). Normalisation décimale FR (`0,05`→`0.05`).
   Une valeur **sans unité** sur une grandeur dimensionnée → `numeric_unit_conflict` (unité manquante).
1. **Rattachement au claim exact** — la valeur doit vivre dans la phrase-hôte du claim (fenêtre
   bornée), pas « quelque part dans la fiche ». Réutilise le mapping claim→phrase de `gen_coverage_map.py`.
1. **Source page-level captured/verified** — lookup `source_status` de l'entrée coverage-map du claim.
   `pending_capture` → `numeric_source_not_captured`. (Cohérent avec le cap page-level dim A déjà en place.)
1. **Contexte d'application** — la phrase-hôte doit porter au moins un qualificatif :
   gamme (`related_gammes`), référence/cote (`340×30`, `5×112`), véhicule/moteur (token validé
   reality-manifest), ou condition (« moderne/ancien », « essieu avant »). Absent → `numeric_context_missing`.
1. **Non-généralisation** — si la valeur est rattachée à une réf/un véhicule **spécifique** (cote
   MIN TH, entraxe) ET la phrase la formule comme règle de gamme (absence de qualificatif restrictif)
   → `numeric_vehicle_specific_do_not_generalize`. **Liste des grandeurs « toujours réf-spécifiques »**
   gouvernée dans `numeric-plausibility.yaml` (ex. `min_thickness`, `disc_diameter`, `bolt_pattern`).
1. **Corroboration multi-source (si valeur critique)** — grandeurs marquées `critical: true`
   (couple de serrage, cote mini) exigent **≥2 sources indépendantes captées concordantes**.
   1 seule source, ou sources divergentes → `numeric_ambiguous`. Concordance = même valeur à la
   tolérance déclarée près.
1. **Plage plausible par famille** — la valeur doit tomber dans `[min,max]` de la grandeur pour la
   famille (`freinage`, `direction`…). Hors plage → BLOCK (`numeric_ambiguous` avec message « hors plage
   plausible famille »). **Grandeur sans plage définie → BLOCK** (fail-closed : on ne sait pas vérifier).

**Blocage automatique (spec owner, littéral)** : valeur **absente**, **ambiguë**, **isolée** ou
**contradictoire** → gate FAIL. Encodé par les verdicts ci-dessus ; aucun fail-open possible.

## 6. Câblage & effet sur le verdict pipeline

```
numeric_exactitude.gate_numeric_value_exactitude(claims, family, ranges) → list[str] violations
        │  (appelé par gap1_auto_review._numeric_exactitude sur TOUS les claims authored)
        ├── 0 violation           → numeric_exactitude_verified = True
        └── ≥1 violation          → numeric_exactitude_verified = False → _safety_auto_gate.blocking
                                       →  compute_verdict → safety_auto_blocked (raison TECHNIQUE)
```

- Ajoute `numeric_exactitude_verified` aux checks **computables** du Safety Auto-Gate.
  `no_disputed_claims` **reste** dans `NOT_YET_WIRED` (contradiction inter-sources = V2, §8).
- **N'autorise JAMAIS** `safety_auto_approved` à lui seul : même toutes valeurs `numeric_verified`,
  le verdict reste `blocked_by_current_safety_policy` tant que l'**ADR sécurité-auto (Étape 3)**
  n'est pas ratifié au vault (flag `--adr091-amended` défaut FALSE, inchangé). Le lock **débloque
  techniquement** ; la **règle** débloque juridiquement.

## 7. Ce qui est mécanisable maintenant vs donnée gouvernée (owner-gated)

**Mécanisable dès le build (0 humain)** : extraction valeur+unité, rattachement, lookup page-status,
détection contexte-absent, détection unité-conflit, détection formulation-générale, comptage sources.

**Donnée gouvernée requise — `_meta/numeric-plausibility.yaml`** : par famille × grandeur,
`{unit, min, max, critical, always_ref_specific}`. C'est de la **connaissance domaine sécurité** :
comme la validation d'autorité de source (Option A), **la machine PROPOSE** des plages depuis les
sources OE captées / normes citées (ECE R90), mais **un humain valide 1×** avant qu'une plage compte
comme référence — sinon une plage fausse auto-générée déplace le risque au lieu de le fermer.
**Fail-closed** : grandeur sans entrée validée → BLOCK (jamais « on suppose OK »).

## 8. Non-goals / limites (honnêteté)

- Ne « comprend » pas la physique : vérifie extraction, unité, provenance, contexte, plage, concordance
  — **pas** la justesse conceptuelle d'un claim. La plage plausible reste le garde-fou domaine.
- Ne remplace pas le jugement humain sur une valeur **genuinely nouvelle** hors de toute plage connue :
  ce cas → BLOCK → reste `safety_auto_blocked` (technique), l'humain reste le fallback d'exception.
- La qualité du lock **plafonne à la qualité de `numeric-plausibility.yaml`** — le vrai goulot est la
  couverture de cette table, remplie incrémentalement par famille (freinage en premier, disque comme pilote).
- **Report-only** jusqu'à l'ADR sécurité-auto : le gate calcule et remonte, il n'auto-approuve rien.

**Durcissement auto-review 2026-07-03** (2 BLOQUANT + 4 HAUTE trouvés par 2 agents adversariaux,
tous corrigés en TDD — voir §11) : unité de la valeur réconciliée avec l'unité canonique de la plage
(°C ≠ mm) ; grandeur liée **par clause locale** (plus « une grandeur par phrase ») ; cote réf-spécifique
énoncée « en général » reste réf-spécifique ; chiffre non extrait sur grandeur dimensionnée (unité
manquante / épelée) **bloque** au lieu de s'évader ; corroboration ≥2 exigée pour **toute** plage validée ;
`_resolve_status` applique le **même** gate `section ∈ valid_sections` que `generate()` (plus de copie laxiste).

**Limites V1 assumées restantes (toutes fail-SAFE : elles BLOQUENT, ne laissent jamais passer à tort)** :

1. **Contradiction inter-sources non détectée** : le V1 classe chaque valeur indépendamment. Le cas
   Brembo/Textar/ZF (0,10 / 0,07 / 0,05 pour le faux-rond) sort `numeric_ambiguous` (grandeur non
   identifiée dans la phrase / valeur isolée), **pas** `disputed_claim` explicite. `no_disputed_claims`
   reste donc `NOT_YET_WIRED`. Vraie corrélation multi-claims même-grandeur = **V2**.
1. **Grandeur liée par clause** (`,` `;` `:` « et ») : robuste sur les phrases multi-grandeurs, mais une
   grandeur et sa valeur séparées par une virgule sans mot-clé dans la clause de la valeur peuvent manquer
   → alors `numeric_ambiguous`/`unit_conflict` (fail-safe), jamais un faux PASS. Segmentation sémantique = V2.
1. **Seed `numeric-plausibility.yaml` = 100 % `proposed`** : le pilote confère donc **0 `numeric_verified`**
   même sur page capturée, jusqu'à ce qu'un humain valide une plage 1× (Option A). C'est l'état sûr voulu.
   En prod, la corroboration réelle n'est pas encore comptée (défaut 1) → `numeric_verified` reste **inatteignable
   en prod** tant que (a) une plage n'est pas `validated` ET (b) le comptage corroboration n'est pas câblé (V2).
1. **Extraction dimensionnée + garde anti-évasion** : les valeurs unitées sont extraites ; un chiffre nu sur
   une grandeur dimensionnée (unité manquante) ou une unité épelée (« newton-mètres ») est désormais **détecté
   et bloqué** (`numeric_unit_conflict`) — plus d'évasion silencieuse. Dates/comptes hors clause dimensionnée
   restent ignorés (pas de sur-blocage).

## 9. Plan de test (disque = fixture réelle)

Chaque verdict a un cas réel disque (§1) → une fonction de test :
`test_min_th_is_vehicle_specific` (27 mm → `numeric_vehicle_specific_do_not_generalize`),
`test_runout_cross_source_ambiguous` (Brembo/Textar/ZF → `numeric_ambiguous` + `no_disputed_claims` KO),
`test_dtv_tilde_range_ambiguous` (`~12-15 µm`), `test_unit_conflict_mm_um` (mm↔µm),
`test_pending_capture_blocks` (page pending → `numeric_source_not_captured`),
`test_context_missing_blocks`, `test_no_range_fails_closed` (grandeur hors table → BLOCK),
`test_verified_requires_captured_plus_corroboration` (le seul chemin PASS).
Invariant global : **sur disque tel quel aujourd'hui, 0 valeur ne PASS** → `safety_auto_blocked` inchangé.

## 10. Séquence (respecte la décision owner) — état réel

1. **Spec** (Étape 2, design) → revue owner. ✅
1. **Build report-only** ✅ **FAIT & PROUVÉ** (2026-07-03, worktree `feat/gap1-auto-authoring-pipeline`) :
   - `_scripts/numeric_exactitude.py` (module PUR, précédent `safety_families.py`) — 0 LLM/DB/réseau.
   - `_scripts/tests/test_numeric_exactitude.py` (24 tests, TDD) + 4 tests câblage `test_gap1_pipeline.py`.
   - `_meta/numeric-plausibility.yaml` (freinage, 6 grandeurs dont couple, **toutes `proposed`** — Option A).
   - Câblé dans `gap1_auto_review._safety_auto_gate` → nouveau computable `numeric_exactitude_verified`.
   - **Preuve pilote disque** : 83 claims scannés → 72 valeurs `numeric_source_not_captured` (pages
     pending) → `numeric_exactitude_verified: false` → contribue à `safety_auto_blocked` (technique).
     Contrefactuel (page capturée) : MIN TH 27 mm → `vehicle_specific`, DTV `~12-15 µm` → `ambiguous`,
     runout `0,05 mm` propre → `verified` **seulement** si la plage passe `validated`.
   - **77 tests verts, 0 régression, 0 runtime, rollback = git revert.**
1. **Remplir/valider `numeric-plausibility.yaml`** freinage (machine a proposé ; **owner valide 1×** →
   `status: validated` + source OE capturée). ⏳ owner-gated.
1. **Étape 3** — ADR sécurité-auto **au vault** (governance-vault-ops, PR G3 owner) référençant ce lock
   comme précondition, autorisant `safety_auto_approved` quand `numeric_exactitude_verified` + gate complet PASS. ⏳

**Le code n'auto-approuve rien** : report-only, fail-closed. `#77` reste draft.

## 11. Auto-review adversariale 2026-07-03 (verify-the-proof)

Deux agents indépendants (silent-failure-hunter + correctness) ont attaqué le module. Verdict initial
**REQUEST CHANGES** — 2 BLOQUANT + 4 HAUTE (aucun exploitable *aujourd'hui* car toutes plages `proposed` +
`--adr091-amended` défaut False, mais **latents dès qu'une plage passe `validated`**). Tous corrigés en TDD,
chaque correctif prouvé sur le scénario d'attaque exact :

| #   | Faille                                                                       | Correctif                                                                                | Preuve                                                           |
| --- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| B1  | unité valeur jamais réconciliée avec l'unité de la plage (°C certifié en mm) | `nv.unit == qdef.unit` (µm/μm normalisé)                                                 | `300 °C` (grandeur diamètre) → `numeric_unit_conflict`           |
| B2  | grandeur détectée par phrase → toutes valeurs sur 1 grandeur                 | grandeur liée **par clause locale**                                                      | `120 Nm` → torque, `300 mm` → disc_diameter (plus de croisement) |
| H1  | `_has_ref_qualifier` faux positif (`5×112`/« référence » discours)           | `_GENERALIZING_RE` override + `réf`→code                                                 | « en général… 27 mm (5×112) » → `vehicle_specific`               |
| H2  | branche `unit==""` morte → valeur sans unité s'évade                         | garde `_unverifiable_tokens` (clause dimensionnée + chiffre sans unité, ou unité épelée) | « 27 sur ce disque », « 120 newton-mètres » → `unit_conflict`    |
| H3  | corroboration morte pour non-critique validé (`corr=1` en prod)              | corroboration ≥2 exigée pour **toute** plage validée                                     | `800 °C` corr=1 → `ambiguous`                                    |
| H4  | `_resolve_status` copie laxiste (sans gate section)                          | même prédicat `section ∈ valid_sections` que `generate()`                                | test `test_resolve_status_requires_valid_section`                |

Verdict après correctifs : **report-only, fail-closed, 0 faux PASS reproductible** ; les 2 BLOQUANT et 4 HAUTE
sont fermés, contrôle « une valeur propre se vérifie » intact. Résidu documenté §8 (contradiction inter-sources
= V2 ; comptage corroboration réel = V2). SUGGESTION restantes non bloquantes : plages-mots « X à Y » entre deux
unités (`12 µm à 15 µm`), `340` de `340×30 mm` non extrait (dimensionné-seul, safe).
