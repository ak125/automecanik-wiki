#!/usr/bin/env python3
"""gap1_auto_review — DRIVER pipeline auto GAP-1 : authoring → coverage-map candidate → auto-review.

Chaîne (owner 2026-07-02, production auto contrôlée) :
  author_from_raw → gen_coverage_map → [gates EXISTANTS] shadow_score + check-coverage-map + quality-gates
  → VERDICT auto-review + garde sécurité ADR-091.

Report-only, 0 mutation (fiche/coverage écrites dans un dossier SHADOW temporaire, JAMAIS proposals/ réel),
0 LLM, 0 DB, 0 promotion réelle. Réutilise les scorers/validateurs existants (verify-before-invent) — ne
réimplémente rien. Le verdict encode la règle owner :
  • TIER A **non-sécurité**            → `auto_promote_eligible` (promote.py décide selon seuil owner).
  • TIER A **sécurité** (ADR-091)      → `human_spot_check_required` (JAMAIS auto — sauf amendement vault).
  • TIER B/C/D ou plancher KO          → `human_review` avec raisons par-dimension EXACTES (P4).
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


def _run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(SCRIPTS_DIR))
    return p.returncode, (p.stdout + p.stderr)


def review(slug: str, raw_root: Path, proposals_dir: Path, manifest: Path, workdir: Path) -> dict:
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

    # 4) VERDICT auto-review + garde sécurité ADR-091
    safety = _is_safety(slug, fm)
    tier = (score or {}).get("tier")
    floors_ko = (score or {}).get("floors_failed") or []
    notes = (score or {}).get("notes") or []
    promotable_tier = tier in ("S", "A")
    if promotable_tier and not safety:
        verdict, reason = "auto_promote_eligible", f"TIER {tier} non-sécurité → promote.py selon seuil owner"
    elif promotable_tier and safety:
        verdict, reason = ("human_spot_check_required",
                           f"TIER {tier} SÉCURITÉ → ADR-091 : jamais auto (Option B zéro-humain = amendement vault)")
    else:
        verdict, reason = "human_review", f"tier={tier} / planchers KO={floors_ko or 'n/a'}"

    return {
        "slug": slug,
        "safety_family": safety,
        "authoring": {"editorial_sections": author_report.get("editorial_sections"),
                      "facts_total": author_report.get("facts_total"),
                      "related_gammes": author_report.get("related_gammes"),
                      "commerce_intent": author_report.get("commerce_intent")},
        "coverage": {"valid_entries": cov_report["valid_entries"],
                     "cataloged_sources": cov_report["cataloged_sources"],
                     "candidate_sources": cov_report["candidate_sources"],
                     "authority_hint_counts": cov_report["authority_hint_counts"]},
        "score": {"total": (score or {}).get("new") or (score or {}).get("total"),
                  "tier": tier, "dims": (score or {}).get("dims"),
                  "floors_ko": floors_ko, "notes": notes},
        "sources_to_validate": cov_report["sources_to_validate"],
        "verdict": verdict,
        "verdict_reason": reason,
        "invariants": ["shadow-only (0 mutation proposals/catalog réel)", "0 LLM/0 DB/0 promotion",
                       "sources inconnues = pending_source_validation (ne comptent pas dim A)",
                       "sécurité = human (ADR-091) sauf amendement vault"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--raw-root", type=Path, default=author_mod.RAW_REPO_PATH)
    ap.add_argument("--proposals-dir", type=Path, default=author_mod.PROPOSALS_DIR)
    ap.add_argument("--manifest", type=Path, default=REPO_ROOT / "_meta" / "reality-manifest.json")
    ap.add_argument("--workdir", type=Path, required=True, help="dossier SHADOW (hors proposals/ réel)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    rep = review(args.slug, args.raw_root.resolve(), args.proposals_dir.resolve(),
                 args.manifest.resolve(), args.workdir.resolve())
    js = json.dumps(rep, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(js, encoding="utf-8")
    print(js)
    return 0


if __name__ == "__main__":
    sys.exit(main())
