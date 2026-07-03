#!/usr/bin/env python3
"""gap1_auto_review — DRIVER pipeline auto GAP-1 : authoring → coverage-map candidate → auto-review.

Chaîne (owner 2026-07-02, production auto contrôlée) :
  author_from_raw → gen_coverage_map → [gates EXISTANTS] shadow_score + check-coverage-map + quality-gates
  → VERDICT auto-review + garde sécurité ADR-091.

Report-only, 0 mutation (fiche/coverage écrites dans un dossier SHADOW temporaire, JAMAIS proposals/ réel),
0 LLM, 0 DB, 0 promotion réelle. Réutilise les scorers/validateurs existants (verify-before-invent) — ne
réimplémente rien.

VERDICT — Safety Auto-Gate (cible owner 2026-07-03) : le goulot « revue humaine obligatoire » n'est PLUS un
état cible. Le blocage sécurité devient :
  • `auto_promote_eligible`               — non-sécurité, planchers OK (promote.py selon seuil owner).
  • `auto_blocked`                        — non-sécurité, planchers KO (raisons exactes).
  • `safety_auto_blocked`                 — sécurité, Safety Auto-Gate KO = raisons TECHNIQUES (page non
                                            capturée, source pending, plancher KO) → capturer puis re-score.
                                            PAS un besoin humain.
  • `safety_blocked_pending_gate_buildout`— sécurité, gate PASS sur le calculable mais conditions restantes
                                            (disputed/regression…) pas encore câblées (fail-closed).
  • `blocked_by_current_safety_policy`    — sécurité, Safety Auto-Gate PASS mais ADR-091 impose encore une
                                            revue → lever par AMENDEMENT VAULT (jamais contournement code).
  • `safety_auto_approved`                — sécurité, gate PASS + ADR-091 amendé (`--adr091-amended`).
Sources inconnues → `pending_source_validation` (Option A) : listées, ne comptent pas pour dim A.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import author_from_raw as author_mod  # noqa: E402
import gen_coverage_map as cov_mod     # noqa: E402

NUMERIC_RANGES_PATH = REPO_ROOT / "_meta" / "numeric-plausibility.yaml"


def _load_numeric_ranges() -> dict:
    """{family: {quantity: {...}}} depuis numeric-plausibility.yaml.

    Absent → {} (fail-closed : toute valeur → numeric_ambiguous, rien ne se vérifie).
    Malformé → {} + message OBSERVABLE sur stderr (fail-closed, pas de repli silencieux)."""
    if not NUMERIC_RANGES_PATH.exists():
        return {}
    import yaml
    try:
        data = yaml.safe_load(NUMERIC_RANGES_PATH.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        print(f"[numeric-lock] numeric-plausibility.yaml ILLISIBLE ({exc}) → 0 plage chargée, "
              f"toute valeur numérique BLOQUÉE (fail-closed).", file=sys.stderr)
        return {}
    return data.get("families", {}) if isinstance(data, dict) else {}


def _resolve_status(c: dict, catalog: dict, valid_sections: set) -> str:
    """source_status d'un claim via la MÊME logique que gen_coverage_map.generate (page-level, Option A).

    Gate IDENTIQUE à generate() : cataloged **ET** `section ∈ valid_sections` **ET** type autoritaire
    **ET** `is_page_proven` (catalog status: active) → token coverage `captured` ; sinon pending_capture.
    Ne PAS relâcher ce prédicat (auto-review 2026-07-03 : une copie laxiste sans le gate section = dérive fail-open)."""
    cat_slug = catalog["domain_to_slug"].get(c["domain"])
    if not cat_slug or c.get("section") not in valid_sections:
        return "pending_capture"
    entry = catalog["slugs"][cat_slug]
    authoritative = str(entry.get("type", "")) in cov_mod.CATALOG_AUTHORITATIVE
    if authoritative and cov_mod.is_page_proven(entry):
        return "captured"                         # status catalog `active` → token coverage prouvé (source_status)
    return "pending_capture"


def _numeric_exactitude(slug: str, raw_root: Path, family: str | None, ranges: dict,
                        valid_sections: set) -> tuple[bool, list[str], int]:
    """Lock valeur numérique sécurité sur TOUS les claims authored (texte complet, tous buckets),
    chaque valeur jointe à son source_status résolu ET son source_id (réutilise gen_coverage_map —
    0 réimplémentation).

    `source_id` = slug source catalogué distinct (sinon domaine) → la corroboration est comptée depuis
    les sources CAPTÉES distinctes concordantes (plus de stub à 1). Aujourd'hui toutes les pages sont
    `pending_capture` → 0 source prouvée → corroboration 0 → toute plage validée reste ambiguë (état sûr).

    Retourne (all_verified, violations, claims_scanned). all_verified True ⇔ 0 violation (vacuel si 0
    valeur). Résidu V2 documenté : contradiction inter-sources (`no_disputed_claims`) non-câblée,
    fail-closed ; grandeur liée par clause locale + corroboration réelle (durcis auto-review 2026-07-03).
    """
    import numeric_exactitude as NE
    catalog = cov_mod._load_catalog()
    claims = cov_mod._collect_claims(slug, raw_root)
    resolved = [{
        "text": c["claim"],
        "source_status": _resolve_status(c, catalog, valid_sections),
        "source_id": catalog["domain_to_slug"].get(c["domain"]) or c.get("domain") or None,
    } for c in claims]
    violations = NE.gate_numeric_value_exactitude(resolved, family=family or "", ranges=ranges)
    return (not violations), violations, len(resolved)


def _is_safety(slug: str, fm: dict) -> bool:
    try:
        import safety_families as sf
        return sf.is_safety_proposal({**fm, "slug": slug})
    except Exception:
        return True  # fail-closed


DIM_A_FLOOR = 22.0
DIM_C_FLOOR = 15.0

# Safety Auto-Gate (cible owner 2026-07-03) — REMPLACE le human spot-check obligatoire par une porte
# AUTOMATIQUE stricte. `human_review` n'est PLUS un état cible ; le blocage sécurité devient soit un
# `safety_auto_blocked` TECHNIQUE (conditions de preuve KO → capture les pages, je re-score), soit un
# `blocked_by_current_safety_policy` (gouvernance : ADR-091 impose encore une revue → lever par amendement
# vault, JAMAIS par contournement code). Fail-closed : toute condition non satisfaite bloque.
NOT_YET_WIRED = ["coverage_strict_pass", "no_quality_gate_fail", "no_disputed_claims",
                 "diagnostic_safe", "regression_gate_pass"]


def _safety_auto_gate(dims: dict, cov_report: dict,
                      numeric_exactitude_verified: bool | None = None) -> dict:
    """Conditions AUTO-vérifiables ici (les autres = à câbler avant tout auto-approve, fail-closed)."""
    A = float(dims.get("A", 0.0) or 0.0)
    C = float(dims.get("C", 0.0) or 0.0)
    computable = {
        "dim_A_floor": A >= DIM_A_FLOOR,
        "dim_C_floor": C >= DIM_C_FLOOR,
        "page_level_all_captured": (cov_report.get("valid_entries", 0) > 0
                                    and cov_report.get("entries_page_pending_capped", 0) == 0),
        "no_pending_source_validation": cov_report.get("candidate_sources", 0) == 0,
    }
    # lock valeur numérique sécurité (numeric_exactitude.py) — ADR-093 numeric-exactitude hole.
    # None = non évalué (compat tests unitaires) ; bool = toutes valeurs sécurité `numeric_verified`.
    if numeric_exactitude_verified is not None:
        computable["numeric_exactitude_verified"] = bool(numeric_exactitude_verified)
    blocking = [k for k, ok in computable.items() if not ok]
    return {"computable": computable, "blocking": blocking, "not_yet_wired": list(NOT_YET_WIRED)}


def compute_verdict(safety: bool, score: dict, cov_report: dict, adr091_amended: bool = False,
                    numeric_exactitude_verified: bool | None = None) -> dict:
    """Verdict auto-review PUR (testable). Aucun `human_review` : sécurité = auto-gate, pas goulot humain."""
    dims = (score or {}).get("dims") or {}
    tier = (score or {}).get("tier")
    floors_ko = (score or {}).get("floors_failed") or []
    if not safety:
        if not floors_ko and tier in ("S", "A"):
            return {"verdict": "auto_promote_eligible",
                    "reason": f"non-sécurité, tier {tier}, planchers OK → promote.py selon seuil owner"}
        return {"verdict": "auto_blocked", "reason": f"non-sécurité, planchers KO={floors_ko or 'n/a'}"}
    gate = _safety_auto_gate(dims, cov_report, numeric_exactitude_verified)
    if gate["blocking"]:
        return {"verdict": "safety_auto_blocked", "gate": gate,
                "reason": "Safety Auto-Gate KO (raisons techniques, PAS besoin humain) : "
                          + ", ".join(gate["blocking"]) + " → capturer les pages OE puis re-score auto"}
    if gate["not_yet_wired"]:
        return {"verdict": "safety_blocked_pending_gate_buildout", "gate": gate,
                "reason": "conditions gate définies mais pas encore câblées : " + ", ".join(gate["not_yet_wired"])}
    if not adr091_amended:
        return {"verdict": "blocked_by_current_safety_policy", "gate": gate,
                "reason": "Safety Auto-Gate PASS ; ADR-091 impose encore une revue → lever par AMENDEMENT VAULT "
                          "(Safety Auto-Gate), jamais par contournement code"}
    return {"verdict": "safety_auto_approved", "gate": gate,
            "reason": "Safety Auto-Gate PASS + ADR-091 amendé → auto-approuvé sans humain"}


def _run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(SCRIPTS_DIR))
    return p.returncode, (p.stdout + p.stderr)


def review(slug: str, raw_root: Path, proposals_dir: Path, manifest: Path, workdir: Path,
           adr091_amended: bool = False) -> dict:
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "_coverage").mkdir(exist_ok=True)
    fiche_path = workdir / f"{slug}.md"
    cov_path = workdir / "_coverage" / f"{slug}.coverage.yaml"

    # 1) AUTHORING
    md, author_report = author_mod.author(slug, raw_root, proposals_dir, manifest)
    fiche_path.write_text(md, encoding="utf-8")
    import yaml
    fm, _ = author_mod._split_fm(md)

    # 2) COVERAGE-MAP CANDIDATE (Option A : valides = catalog existant ; candidates = pending_source_validation)
    cov, cov_report = cov_mod.generate(slug, md, raw_root)
    if cov:
        cov_path.write_text(yaml.safe_dump(cov, allow_unicode=True, sort_keys=False), encoding="utf-8")

    # 3) GATES EXISTANTS (réutilisés) — shadow_score sur le dossier shadow
    rc_s, out_s = _run([sys.executable, "shadow_score.py", str(fiche_path),
                        "--proposals-dir", str(workdir), "--format", "json"])
    score = None
    try:
        start = out_s.index("[")  # tolère un header avant le JSON
        arr = json.loads(out_s[start:])
        score = arr[0] if isinstance(arr, list) and arr else arr
    except Exception:
        score = {"raw": out_s[-800:]}

    # 3-bis) LOCK VALEUR NUMÉRIQUE SÉCURITÉ (numeric_exactitude) — ferme le trou ADR-093 (exactitude
    #        du chiffre, jamais vérifiée par la barre provenance/structure). Report-only, fail-closed.
    safety = _is_safety(slug, fm)
    numeric_ranges = _load_numeric_ranges()
    family = author_mod._family_of(slug, fm)
    valid_sections = set(cov_mod._fiche_h2h3(author_mod._split_fm(md)[1]))  # même gate que generate()
    numeric_verified, numeric_violations, numeric_scanned = _numeric_exactitude(
        slug, raw_root, family, numeric_ranges, valid_sections)
    # None si non-sécurité (le lock ne gate que la sécurité) ; bool sinon → alimente la Safety Auto-Gate.
    numeric_gate_input = numeric_verified if safety else None

    # 4) VERDICT auto-review — Safety Auto-Gate (0 `human_review` ; goulot humain remplacé par gate auto)
    tier = (score or {}).get("tier")
    floors_ko = (score or {}).get("floors_failed") or []
    v = compute_verdict(safety, score, cov_report, adr091_amended, numeric_gate_input)

    return {
        "slug": slug,
        "safety_family": safety,
        "adr091_amended": adr091_amended,
        "authoring": {"editorial_sections": author_report.get("editorial_sections"),
                      "facts_total": author_report.get("facts_total"),
                      "related_gammes": author_report.get("related_gammes"),
                      "commerce_intent": author_report.get("commerce_intent")},
        "coverage": {"valid_entries": cov_report["valid_entries"],
                     "cataloged_sources": cov_report["cataloged_sources"],
                     "candidate_sources": cov_report["candidate_sources"],
                     "entries_page_pending_capped": cov_report["entries_page_pending_capped"],
                     "authority_hint_counts": cov_report["authority_hint_counts"]},
        "score": {"total": (score or {}).get("new") or (score or {}).get("total"),
                  "tier": tier, "dims": (score or {}).get("dims"),
                  "floors_ko": floors_ko, "notes": (score or {}).get("notes") or []},
        "sources_to_validate": cov_report["sources_to_validate"],
        "numeric_exactitude": {"family": family, "all_verified": numeric_verified,
                               "claims_scanned": numeric_scanned,
                               "violations_total": len(numeric_violations),
                               "sample": numeric_violations[:8],
                               "ranges_loaded": bool(numeric_ranges)},
        "verdict": v["verdict"],
        "verdict_reason": v["reason"],
        "safety_auto_gate": v.get("gate"),
        "invariants": ["shadow-only (0 mutation proposals/catalog réel)", "0 LLM/0 DB/0 promotion",
                       "sources inconnues = pending_source_validation (ne comptent pas dim A)",
                       "sécurité : blocage = gate AUTO (technique) ou policy ADR-091 (gouvernance) — "
                       "jamais un goulot humain ; zéro-humain sécurité = amendement vault ADR-091"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--raw-root", type=Path, default=author_mod.RAW_REPO_PATH)
    ap.add_argument("--proposals-dir", type=Path, default=author_mod.PROPOSALS_DIR)
    ap.add_argument("--manifest", type=Path, default=REPO_ROOT / "_meta" / "reality-manifest.json")
    ap.add_argument("--workdir", type=Path, required=True, help="dossier SHADOW (hors proposals/ réel)")
    ap.add_argument("--adr091-amended", action="store_true",
                    help="ADR-091 amendé au vault (Safety Auto-Gate ratifié) → autorise safety_auto_approved. "
                         "Défaut FALSE = ne JAMAIS auto-approuver sécurité par code (anti-contournement).")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    rep = review(args.slug, args.raw_root.resolve(), args.proposals_dir.resolve(),
                 args.manifest.resolve(), args.workdir.resolve(), args.adr091_amended)
    js = json.dumps(rep, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(js, encoding="utf-8")
    print(js)
    return 0


if __name__ == "__main__":
    sys.exit(main())
