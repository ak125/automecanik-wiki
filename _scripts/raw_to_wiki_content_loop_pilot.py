#!/usr/bin/env python3
"""raw_to_wiki_content_loop_pilot — ORCHESTRATEUR de la boucle contenu (PAS un scorer).

Exécute la trajectoire COMPLÈTE sur UNE entité pilote et émet UN rapport unique qui prouve
(ou réfute) chaque maillon, avec `remaining_blockers` explicites :

    RAW source  →  WIKI proposal  →  SHADOW SCORE (before/after)  →  CITATION-READINESS
    →  PROMOTION (dry)  →  EXPORT SEO  →  CONSUMER (monorepo)  →  OUTCOME (observe)

RÈGLE DURE (anti-overclaim, ADR-088 §F) : on NE déclare PAS « pipeline aligné / opérationnel »
sans ce rapport montrant `loop_closed: true`. Le score est une CONDITION de boucle :
`tier_after != A` ⇒ blocker `score_insufficient → retour scraping/enrichissement`.

Réutilise les briques existantes (0 réinvention, 0 mutation, 0 LLM, 0 DB) via leurs CLI :
shadow_score.py · citation-readiness-report.py · promote.py (--dry-run) · build_exports_seo.py.
Les maillons CONSUMER/OUTCOME sont vérifiés par présence d'artefact (lecture seule monorepo)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
TIER_A_OK = {"A", "S"}


def _run(cmd: list[str], timeout: int = 180) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as exc:  # noqa: BLE001 — un maillon KO devient un blocker, jamais un crash du runner
        return -1, "", str(exc)


def _extract_json(s: str):
    """Extrait le JSON même si des lignes WARN/log le précèdent sur stdout (cas citation-readiness)."""
    lines = s.splitlines()
    for i, ln in enumerate(lines):
        st = ln.lstrip()
        if st.startswith("{") or st.startswith("["):
            return json.loads("\n".join(lines[i:]))
    raise ValueError("aucun JSON dans la sortie")


def _shadow(proposal: Path, wiki_root: Path, proposals_dir: Path) -> dict:
    rc, out, err = _run([sys.executable, str(SCRIPTS_DIR / "shadow_score.py"), str(proposal),
                         "--wiki-root", str(wiki_root), "--proposals-dir", str(proposals_dir),
                         "--format", "json"])
    try:
        r = json.loads(out)[0]
        return {"tier": r["tier"], "total": r["total"], "floors_failed": r.get("floors_failed", [])}
    except Exception:  # noqa: BLE001
        return {"tier": None, "total": None, "floors_failed": [f"err:{(err or out)[:120]}"]}


def _score_at_ref(ref: str, slug: str, wiki_root: Path, tmp: Path) -> dict:
    """Score la fiche TELLE QU'ELLE EST à `ref` (git show) avec le scorer COURANT → isole l'effet CONTENU."""
    pdir = tmp / "proposals"
    (pdir / "_coverage").mkdir(parents=True, exist_ok=True)
    for src, dst in ((f"proposals/{slug}.md", pdir / f"{slug}.md"),
                     (f"proposals/_coverage/{slug}.coverage.yaml", pdir / "_coverage" / f"{slug}.coverage.yaml")):
        rc, out, _ = _run(["git", "-C", str(wiki_root), "show", f"{ref}:{src}"])
        if rc == 0:
            dst.write_text(out, encoding="utf-8")
    p = pdir / f"{slug}.md"
    if not p.is_file():
        return {"tier": None, "total": None, "floors_failed": [f"absente@{ref}"]}
    return _shadow(p, wiki_root, pdir)


def stage_raw(slug: str, raw_root: Path) -> dict:
    d = raw_root / "sources" / "web-research" / slug
    mds = sorted(d.glob("*.md")) if d.is_dir() else []
    has_idx = d.is_dir() and any(d.glob("*source-index*.json"))
    return {"ok": bool(mds), "dir": str(d), "md_files": len(mds), "has_source_index": has_idx}


def stage_wiki(slug: str, wiki_root: Path) -> dict:
    import yaml
    p = wiki_root / "proposals" / f"{slug}.md"
    if not p.is_file():
        return {"ok": False, "path": None, "reason": "proposal absente"}
    fm = yaml.safe_load(p.read_text(encoding="utf-8").split("---", 2)[1])
    ed = fm.get("entity_data") or {}
    structured = bool(ed.get("editorial") or ed.get("known_issues_by_engine")
                      or ed.get("maintenance_by_engine") or ed.get("related_gammes"))
    return {"ok": structured, "path": str(p.relative_to(wiki_root)), "entity_type": fm.get("entity_type"),
            "review_status": fm.get("review_status"), "structured_entity_data": structured}


def stage_citation(entity_id: str, slug: str, wiki_root: Path) -> dict:
    rc, out, err = _run([sys.executable, str(SCRIPTS_DIR / "citation-readiness-report.py"),
                         "--wiki-root", str(wiki_root), "--format", "json"])
    try:
        data = _extract_json(out)
        rows = data.get("reports", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        for row in rows:
            if row.get("entity_id") == entity_id:
                v = row.get("status") or row.get("verdict") or "?"
                return {"ok": v == "READY", "verdict": v, "substance_tier": row.get("substance_tier")}
        return {"ok": False, "verdict": "NOT_FOUND_IN_REPORT"}
    except Exception:  # noqa: BLE001
        return {"ok": False, "verdict": f"err:{(err or out)[:120]}"}


def stage_promotion(entity_id: str, wiki_root: Path, threshold: float) -> dict:
    rc, out, err = _run([sys.executable, str(SCRIPTS_DIR / "promote.py"), "--wiki-root", str(wiki_root),
                         "--entity-id", entity_id, "--threshold", str(threshold), "--dry-run", "--format", "json"])
    try:
        data = _extract_json(out)
        rows = data.get("report", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        row = rows[0] if rows else {}
        tier = row.get("tier")
        reasons = row.get("blocking_reasons") or []
        return {"ok": tier in TIER_A_OK, "tier": tier, "threshold": threshold, "blocking_reasons": reasons}
    except Exception:  # noqa: BLE001
        return {"ok": False, "tier": None, "threshold": threshold, "blocking_reasons": [f"err:{(err or out)[:160]}"]}


def stage_export(entity_id: str, wiki_root: Path) -> dict:
    rc, out, err = _run([sys.executable, str(SCRIPTS_DIR / "build_exports_seo.py"),
                         "--entity-id", entity_id, "--dry-run", "--wiki-root", str(wiki_root)])
    blob = (out + err)
    would = ("would-write" in blob.lower()) or ("dry_run would-write" in blob.lower())
    blocked = "canon source absent" in blob.lower()
    detail = "canon promu absent (fiche non promue vers wiki/<type>/)" if blocked else blob.strip().splitlines()[-1:] or []
    return {"ok": would, "would_write": would, "detail": detail}


def stage_consumer(slug: str, monorepo_root: Path) -> dict:
    """CONSUMER = writer forward exports/seo → __seo_* DB (ADR-059 PR-6). Vérif présence (0-DB)."""
    proj = monorepo_root / "scripts" / "seo-projection"
    writer = None
    if proj.is_dir():
        for f in proj.glob("*.py"):
            if f.name.startswith("replay") or f.name.startswith("test") or f.name == "__init__.py":
                continue
            txt = f.read_text(encoding="utf-8", errors="ignore")
            if "exports/seo" in txt and ("INSERT" in txt.upper() or "__seo_entity_facts" in txt):
                writer = f.name
                break
    return {"ok": bool(writer), "forward_writer": writer,
            "detail": "writer exports/seo→DB présent" if writer else "AUCUN writer forward (replay-only) → ADR-059 PR-6 non bâti"}


def stage_outcome(monorepo_root: Path) -> dict:
    """OUTCOME = boucle OBSERVE 7/14/28j (mesure post-publication). Vérif merge sur main (0-DB)."""
    rc, out, _ = _run(["git", "-C", str(monorepo_root), "log", "origin/main", "--oneline", "-n", "400"])
    merged = any(k in out.lower() for k in ("seo-action-outcome", "command_center_seo_outcomes"))
    return {"ok": merged, "detail": "OBSERVE loop mergée sur main" if merged else "OBSERVE loop (PR #1025) non mergée / draft owner-gated"}


def run(entity_id: str, wiki_root: Path, raw_root: Path, monorepo_root: Path,
        baseline_ref: str, threshold: float) -> dict:
    etype, _, slug = entity_id.partition(":")
    proposal = wiki_root / "proposals" / f"{slug}.md"

    raw = stage_raw(slug, raw_root)
    wiki = stage_wiki(slug, wiki_root)
    after = _shadow(proposal, wiki_root, wiki_root / "proposals") if proposal.is_file() else {"tier": None, "total": None, "floors_failed": ["absente"]}
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        before = _score_at_ref(baseline_ref, slug, wiki_root, Path(td))
    citation = stage_citation(entity_id, slug, wiki_root)
    promotion = stage_promotion(entity_id, wiki_root, threshold)
    export = stage_export(entity_id, wiki_root)
    consumer = stage_consumer(slug, monorepo_root)
    outcome = stage_outcome(monorepo_root)

    score_ok = after.get("tier") in TIER_A_OK
    blockers = []

    def block(stage, reason, owner_gated):
        blockers.append({"stage": stage, "reason": reason, "owner_gated": owner_gated})

    if not raw["ok"]:
        block("raw", "aucune source web-research scrapée", False)
    if not wiki["ok"]:
        block("wiki_proposal", "proposal absente ou entity_data non structuré", False)
    if not score_ok:
        block("score", f"tier_after={after.get('tier')} < A (planchers {after.get('floors_failed')}) → retour scraping/enrichissement", False)
    if not citation["ok"]:
        block("citation", f"verdict={citation['verdict']} (≠ READY)", False)
    if not promotion["ok"]:
        block("promotion", f"promote.py dry-run tier={promotion['tier']} (gate sur l'ANCIEN confidence_score, pas le 6-dim ; seuil no-op 1.01) → CUTOVER requis", True)
    if not export["ok"]:
        block("seo_export", "export impossible tant que la fiche n'est pas PROMUE (build lit wiki/<type>/, pas proposals/)", True)
    if not consumer["ok"]:
        block("consumer", "writer forward exports/seo→DB absent (ADR-059 PR-6 non bâti + follow-up §C1-C4)", True)
    if not outcome["ok"]:
        block("outcome", "boucle OBSERVE (mesure 7/14/28j) non mergée (draft owner-gated)", True)

    loop_closed = not blockers
    return {
        "entity": entity_id,
        "raw_sources": raw,
        "wiki_proposal": wiki,
        "shadow_score_before": before.get("total"),
        "tier_before": before.get("tier"),
        "shadow_score_after": after.get("total"),
        "tier_after": after.get("tier"),
        "score_is_loop_condition": {"threshold_tier": "A", "passed": score_ok},
        "citation_ready": citation["verdict"],
        "promotion_would": promotion,
        "seo_export_written": export["ok"],
        "consumer_seen": consumer["ok"],
        "consumer_detail": consumer["detail"],
        "outcome_measured": outcome["ok"],
        "outcome_detail": outcome["detail"],
        "loop_closed": loop_closed,
        "remaining_blockers": blockers,
        "baseline_ref": baseline_ref,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Orchestrateur boucle contenu — rapport de trajectoire (report-only).")
    ap.add_argument("--entity", required=True, help="type:slug, ex. gamme:plaquette-de-frein")
    ap.add_argument("--wiki-root", type=Path, default=SCRIPTS_DIR.parent)
    ap.add_argument("--raw-root", type=Path, default=Path("/opt/automecanik/automecanik-raw"))
    ap.add_argument("--monorepo-root", type=Path, default=Path("/opt/automecanik/app"))
    ap.add_argument("--baseline-ref", default="origin/main", help="ref git pour le score 'before' (effet contenu)")
    ap.add_argument("--threshold", type=float, default=0.80, help="seuil promotion simulé (dry-run)")
    ap.add_argument("--strict", action="store_true", help="exit 1 si loop_closed=false")
    args = ap.parse_args(argv)

    report = run(args.entity, args.wiki_root, args.raw_root, args.monorepo_root, args.baseline_ref, args.threshold)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.strict and not report["loop_closed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
