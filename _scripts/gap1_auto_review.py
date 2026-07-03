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


def _safety_auto_gate(dims: dict, cov_report: dict) -> dict:
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
    blocking = [k for k, ok in computable.items() if not ok]
    return {"computable": computable, "blocking": blocking, "not_yet_wired": list(NOT_YET_WIRED)}


def compute_verdict(safety: bool, score: dict, cov_report: dict, adr091_amended: bool = False) -> dict:
    """Verdict auto-review PUR (testable). Aucun `human_review` : sécurité = auto-gate, pas goulot humain."""
    dims = (score or {}).get("dims") or {}
    tier = (score or {}).get("tier")
    floors_ko = (score or {}).get("floors_failed") or []
    if not safety:
        if not floors_ko and tier in ("S", "A"):
            return {"verdict": "auto_promote_eligible",
                    "reason": f"non-sécurité, tier {tier}, planchers OK → promote.py selon seuil owner"}
        return {"verdict": "auto_blocked", "reason": f"non-sécurité, planchers KO={floors_ko or 'n/a'}"}
    gate = _safety_auto_gate(dims, cov_report)
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

    # 4) VERDICT auto-review — Safety Auto-Gate (0 `human_review` ; goulot humain remplacé par gate auto)
    safety = _is_safety(slug, fm)
    tier = (score or {}).get("tier")
    floors_ko = (score or {}).get("floors_failed") or []
    v = compute_verdict(safety, score, cov_report, adr091_amended)

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
