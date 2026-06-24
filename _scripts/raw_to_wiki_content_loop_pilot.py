#!/usr/bin/env python3
"""raw_to_wiki_content_loop_pilot — ORCHESTRATEUR de la boucle contenu (PAS un scorer).

Exécute la trajectoire COMPLÈTE sur UNE entité pilote et émet UN rapport unique qui prouve
(ou réfute) chaque maillon, avec `remaining_blockers` explicites :

    RAW source  →  WIKI proposal  →  SHADOW SCORE (before/after)  →  CITATION-READINESS
    →  PROMOTION (dry)  →  EXPORT SEO  →  CONSUMER (projection DB)  →  OUTCOME (observe)

RÈGLE DURE (anti-overclaim, ADR-088 §F) : on NE déclare PAS « pipeline aligné / opérationnel »
sans ce rapport. Le score est une CONDITION de boucle : `tier_after != A` ⇒ blocker.

3A — PREUVES STATIQUES À SÉMANTIQUE STRICTE (mesurer le runtime réel, pas des mots dans git) :
chaque maillon renvoie un `state` ∈ {PASS, FAIL, PENDING, UNKNOWN, NOT_APPLICABLE} :
  • PASS              : preuve trouvée.
  • FAIL             : surface EXACTE (bon repo+commit) inspectée, preuve ABSENTE.
                       Une absence déterministe dans le code inspecté est un FAIL, pas un UNKNOWN.
  • PENDING          : changement PLANIFIÉ (PR en vol) mais pas encore mergé / câblé.
  • UNKNOWN          : repo / ref / fichier INACCESSIBLE — jamais transformé en faux `false`.
  • NOT_APPLICABLE   : contrôle hors périmètre de cette phase.

Le CONSUMER détecte le writer **TypeScript** réel
(`backend/src/modules/seo-projection/seo-projection-writer.service.ts`) — fallback legacy `*.py`.

3B — PREUVES RUNTIME : fournies par artefact `--evidence <json>` (séparation WIKI↔runtime, aucun
credential embarqué). Sans evidence → UNKNOWN (jamais PASS/FAIL inventé).

DEUX VERDICTS (ne pas lier l'opérationnel à la mesure 7/14/28j) :
  • projection_operational : chaîne technique (writer→wired→rpc→consumer + projection rendue) prouvée.
  • business_loop_closed   : projection_operational ET outcome_observed (7/14/28j) daté.

Réutilise les briques existantes (0 réinvention, 0 mutation, 0 LLM, 0 DB) via leurs CLI."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
TIER_A_OK = {"A", "S"}

PASS, FAIL, PENDING, UNKNOWN, NA = "PASS", "FAIL", "PENDING", "UNKNOWN", "NOT_APPLICABLE"


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


def _state_from_ok(ok: bool, errored: bool = False) -> str:
    """Maille runnable (live) : erreur d'accès → UNKNOWN, sinon PASS/FAIL déterministe."""
    if errored:
        return UNKNOWN
    return PASS if ok else FAIL


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
    if not raw_root.is_dir():
        return {"state": UNKNOWN, "dir": str(d), "detail": "raw-root inaccessible"}
    mds = sorted(d.glob("*.md")) if d.is_dir() else []
    has_idx = d.is_dir() and any(d.glob("*source-index*.json"))
    return {"state": _state_from_ok(bool(mds)), "dir": str(d), "md_files": len(mds), "has_source_index": has_idx}


def stage_wiki(slug: str, wiki_root: Path) -> dict:
    import yaml
    p = wiki_root / "proposals" / f"{slug}.md"
    if not p.is_file():
        return {"state": FAIL, "path": None, "reason": "proposal absente"}
    fm = yaml.safe_load(p.read_text(encoding="utf-8").split("---", 2)[1])
    ed = fm.get("entity_data") or {}
    structured = bool(ed.get("editorial") or ed.get("known_issues_by_engine")
                      or ed.get("maintenance_by_engine") or ed.get("related_gammes"))
    return {"state": _state_from_ok(structured), "path": str(p.relative_to(wiki_root)),
            "entity_type": fm.get("entity_type"), "review_status": fm.get("review_status"),
            "structured_entity_data": structured}


def stage_citation(entity_id: str, slug: str, wiki_root: Path) -> dict:
    rc, out, err = _run([sys.executable, str(SCRIPTS_DIR / "citation-readiness-report.py"),
                         "--wiki-root", str(wiki_root), "--format", "json"])
    try:
        data = _extract_json(out)
        rows = data.get("reports", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        for row in rows:
            if row.get("entity_id") == entity_id:
                v = row.get("status") or row.get("verdict") or "?"
                return {"state": _state_from_ok(v == "READY"), "verdict": v, "substance_tier": row.get("substance_tier")}
        return {"state": FAIL, "verdict": "NOT_FOUND_IN_REPORT"}
    except Exception:  # noqa: BLE001
        return {"state": UNKNOWN, "verdict": f"err:{(err or out)[:120]}"}


def stage_promotion(entity_id: str, wiki_root: Path, threshold: float) -> dict:
    rc, out, err = _run([sys.executable, str(SCRIPTS_DIR / "promote.py"), "--wiki-root", str(wiki_root),
                         "--entity-id", entity_id, "--threshold", str(threshold), "--dry-run", "--format", "json"])
    try:
        data = _extract_json(out)
        rows = data.get("report", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        row = rows[0] if rows else {}
        tier = row.get("tier")
        reasons = row.get("blocking_reasons") or []
        return {"state": _state_from_ok(tier in TIER_A_OK), "tier": tier, "threshold": threshold, "blocking_reasons": reasons}
    except Exception:  # noqa: BLE001
        return {"state": UNKNOWN, "tier": None, "threshold": threshold, "blocking_reasons": [f"err:{(err or out)[:160]}"]}


def stage_export(entity_id: str, wiki_root: Path) -> dict:
    rc, out, err = _run([sys.executable, str(SCRIPTS_DIR / "build_exports_seo.py"),
                         "--entity-id", entity_id, "--dry-run", "--wiki-root", str(wiki_root)])
    blob = (out + err)
    would = ("would-write" in blob.lower()) or ("dry_run would-write" in blob.lower())
    blocked = "canon source absent" in blob.lower()
    detail = "canon promu absent (fiche non promue vers wiki/<type>/)" if blocked else (blob.strip().splitlines()[-1:] or [])
    return {"state": _state_from_ok(would), "would_write": would, "detail": detail}


# ── 3A : PREUVES STATIQUES (monorepo, sémantique stricte) ──────────────────────────────────

def static_proofs(monorepo_root: Path) -> dict:
    """Preuves statiques de la chaîne projection (writer→wired→rpc→consumer). FS = branche checkout."""
    backend = monorepo_root / "backend"
    if not backend.is_dir():
        u = {"state": UNKNOWN, "detail": "monorepo backend/ inaccessible"}
        return {"writer_code_present": dict(u), "module_wired_in_source": dict(u),
                "read_rpc_declared": dict(u), "page_consumer_code_present": dict(u)}

    # 1) writer_code_present — TS réel, fallback legacy py
    ts_writer = backend / "src/modules/seo-projection/seo-projection-writer.service.ts"
    if ts_writer.is_file():
        txt = ts_writer.read_text(encoding="utf-8", errors="ignore")
        ok = ("SeoProjectionWriterService" in txt or "projectExports" in txt) and "__seo_entity_facts" in txt
        writer = {"state": PASS if ok else FAIL, "kind": "typescript",
                  "detail": "writer TS SeoProjectionWriterService présent" if ok
                            else "writer TS présent mais marqueurs (projectExports/__seo_entity_facts) absents"}
    else:
        legacy = None
        proj = monorepo_root / "scripts" / "seo-projection"
        if proj.is_dir():
            for f in proj.glob("*.py"):
                if f.name.startswith(("replay", "test")) or f.name == "__init__.py":
                    continue
                t = f.read_text(encoding="utf-8", errors="ignore")
                if "exports/seo" in t and ("INSERT" in t.upper() or "__seo_entity_facts" in t):
                    legacy = f.name
                    break
        writer = ({"state": PASS, "kind": "python_legacy", "detail": f"writer legacy py {legacy}"} if legacy
                  else {"state": FAIL, "kind": None, "detail": "AUCUN writer (ni TS ni legacy py)"})
    writer_built = writer["state"] == PASS

    # 2) module_wired_in_source — AppModule importe SeoProjectionModule
    appmod = backend / "src/app.module.ts"
    if appmod.is_file():
        wired = "SeoProjectionModule" in appmod.read_text(encoding="utf-8", errors="ignore")
        if wired:
            module = {"state": PASS, "detail": "AppModule importe SeoProjectionModule"}
        elif writer_built:
            module = {"state": PENDING, "detail": "writer bâti mais AppModule non câblé — feeder/wire PR-6c (#1033) non mergé"}
        else:
            module = {"state": FAIL, "detail": "SeoProjectionModule ni bâti ni importé"}
    else:
        module = {"state": UNKNOWN, "detail": "app.module.ts inaccessible"}

    # 3) read_rpc_declared — migration déclare get_active_seo_projection
    migs = backend / "supabase/migrations"
    rpc_found = False
    if migs.is_dir():
        for f in migs.glob("*.sql"):
            t = f.read_text(encoding="utf-8", errors="ignore")
            if "get_active_seo_projection" in t and ("create or replace function" in t.lower() or "create function" in t.lower()):
                rpc_found = True
                break
        rpc = ({"state": PASS, "detail": "RPC get_active_seo_projection déclarée (migration)"} if rpc_found
               else {"state": PENDING, "detail": "RPC lecture get_active_seo_projection absente de main — PR-7a (#1040) non mergée"})
    else:
        rpc = {"state": UNKNOWN, "detail": "backend/supabase/migrations inaccessible"}

    # 4) page_consumer_code_present — un VRAI appelant du read-path PAGE R1/R8 invoque la RPC.
    # Mot dans un commentaire / nom de flag / service admin ≠ consommation par la page rendue
    # (c'est exactement le piège « mot dans le code ≠ câblage réel » que l'orchestrateur traque).
    srcdir = backend / "src"
    caller, admin_ref = None, None
    if srcdir.is_dir():
        rc, out, _ = _run(["grep", "-rn", "get_active_seo_projection", str(srcdir), "--include=*.ts"])
        for line in out.splitlines():
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            path, _lineno, content = parts
            stripped = content.lstrip()
            if stripped.startswith(("*", "//", "/*")):        # commentaire → ignore
                continue
            if "/migrations/" in path or "seo-projection-writer" in path \
                    or "feature-flags" in path or path.endswith("seo-projection.module.ts"):
                continue
            if "/admin/" in path:                              # brief admin ≠ page publique R1/R8
                admin_ref = admin_ref or Path(path).name
                continue
            caller = f"{Path(path).name}:{parts[1]}"
            break
    if caller:
        consumer = {"state": PASS, "detail": f"appelant read-path page présent: {caller}"}
    else:
        detail = "overlay lecture R1/R8 (PR-7b) non bâti — aucune page publique ne consomme la projection"
        if admin_ref:
            detail += f" (réf. admin {admin_ref} = brief, pas le rendu page)"
        consumer = {"state": PENDING, "detail": detail}

    return {"writer_code_present": writer, "module_wired_in_source": module,
            "read_rpc_declared": rpc, "page_consumer_code_present": consumer}


# ── 3B : PREUVES RUNTIME (injectées par artefact --evidence) ───────────────────────────────

RUNTIME_KEYS = ["export_generated", "projection_run_succeeded", "active_version_present",
                "projection_rpc_readable", "page_render_consumed_projection", "outcome_observed"]
# clés qui gouvernent projection_operational (l'outcome 7/14/28j est SÉPARÉ)
PROJECTION_RUNTIME_KEYS = RUNTIME_KEYS[:-1]


def _coerce_state(v) -> str:
    if v is True or (isinstance(v, str) and v.upper() == PASS):
        return PASS
    if v is False or (isinstance(v, str) and v.upper() == FAIL):
        return FAIL
    if isinstance(v, str) and v.upper() in {PENDING, UNKNOWN, NA}:
        return v.upper()
    return UNKNOWN


def runtime_proofs(evidence: dict | None) -> dict:
    out = {}
    ev = evidence or {}
    for k in RUNTIME_KEYS:
        if k in ev:
            out[k] = {"state": _coerce_state(ev[k]), "detail": "via --evidence (3B)"}
        else:
            # absence de donnée ⇒ jamais un faux `false` → UNKNOWN, en attente d'evidence runtime
            out[k] = {"state": UNKNOWN, "detail": "aucune evidence runtime fournie (fournir --evidence, 3B)"}
    return out


def compute_page_quality_ready(tier: str | None, blockers: list) -> tuple[object, dict]:
    """ADR-094 — verdict de PAGE composite (ADDITIF). N'altère PAS les 3 verdicts orchestrateur.

    Réutilise/référence des mesures EXISTANTES (tier substance ADR-092, blockers déjà calculés) ;
    ne crée AUCUN scoreur parallèle. Les composants externes (surface monorepo, SSR, diversité
    ADR-066/067, lineage ADR-059) ne sont pas encore livrés ⇒ UNKNOWN ⇒ `page_quality_ready=HOLD`
    (fail-closed : un composant manquant n'est jamais transformé en faux `False`/`True`).
    Étiquettes forgées ici pour la composition ; chacune consommera la mesure d'un domaine existant.
    """
    components = {
        "content_substance_pass": tier in TIER_A_OK,  # ⟵ ADR-092 (tier S/A)
        "seo_surface_pass": UNKNOWN,        # scoreur surface monorepo — pas encore livré
        "ssr_runtime_pass": UNKNOWN,        # rendu SSR — pas mesuré ici
        "cluster_diversity_pass": UNKNOWN,  # ADR-066/067 intra+cross — pas branché
        "lineage_pass": UNKNOWN,            # soft jusqu'à extension schéma ADR-059
        "no_hard_blocker": not blockers,    # dérivé des blockers déjà calculés
    }
    if any(v == UNKNOWN for v in components.values()):
        return "HOLD", components               # fail-closed : composant manquant ≠ faux verdict
    return all(components.values()), components


def run(entity_id: str, wiki_root: Path, raw_root: Path, monorepo_root: Path,
        baseline_ref: str, threshold: float, evidence: dict | None = None) -> dict:
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
    static = static_proofs(monorepo_root)
    runtime = runtime_proofs(evidence)

    score_ok = after.get("tier") in TIER_A_OK
    score_state = _state_from_ok(score_ok, errored=after.get("tier") is None)

    # ── Verdicts (deux niveaux, plan §5) ──
    static_chain_pass = all(static[k]["state"] == PASS for k in static)
    projection_runtime_pass = all(runtime[k]["state"] == PASS for k in PROJECTION_RUNTIME_KEYS)
    projection_operational = static_chain_pass and projection_runtime_pass
    outcome_status = runtime["outcome_observed"]["state"]
    business_loop_closed = projection_operational and outcome_status == PASS

    # ── Blockers (FAIL = bloquant) vs pending (PENDING = planifié, non bloquant) vs unknown ──
    blockers, pending, unknown = [], [], []
    stage_map = {
        "raw": (raw["state"], "aucune source web-research scrapée", False),
        "wiki_proposal": (wiki["state"], "proposal absente ou entity_data non structuré", False),
        "score": (score_state, f"tier_after={after.get('tier')} < A (planchers {after.get('floors_failed')}) → retour scraping/enrichissement", False),
        "citation": (citation["state"], f"verdict={citation.get('verdict')} (≠ READY)", False),
        "promotion": (promotion["state"], f"promote.py dry-run tier={promotion.get('tier')} (cutover moteur 6-dim requis ; seuil no-op 1.01)", True),
        "seo_export": (export["state"], "export impossible tant que la fiche n'est pas PROMUE (build lit wiki/<type>/)", True),
        "consumer_writer": (static["writer_code_present"]["state"], static["writer_code_present"]["detail"], True),
        "consumer_wired": (static["module_wired_in_source"]["state"], static["module_wired_in_source"]["detail"], True),
        "read_rpc": (static["read_rpc_declared"]["state"], static["read_rpc_declared"]["detail"], True),
        "page_consumer": (static["page_consumer_code_present"]["state"], static["page_consumer_code_present"]["detail"], True),
    }
    for k in PROJECTION_RUNTIME_KEYS:
        stage_map[f"runtime:{k}"] = (runtime[k]["state"], runtime[k]["detail"], True)
    stage_map["outcome"] = (outcome_status, runtime["outcome_observed"]["detail"], True)

    for stage, (state, reason, owner_gated) in stage_map.items():
        rec = {"stage": stage, "state": state, "reason": reason, "owner_gated": owner_gated}
        if state == FAIL:
            blockers.append(rec)
        elif state == PENDING:
            pending.append(rec)
        elif state == UNKNOWN:
            unknown.append(rec)

    # back-compat : loop_closed = business_loop_closed (anti-overclaim conservé)
    loop_closed = business_loop_closed

    # ADR-094 — verdict de PAGE composite (ADDITIF ; n'altère pas les 3 verdicts ci-dessus)
    page_quality_ready, page_quality_components = compute_page_quality_ready(after.get("tier"), blockers)

    return {
        "entity": entity_id,
        "raw_sources": raw,
        "wiki_proposal": wiki,
        "shadow_score_before": before.get("total"),
        "tier_before": before.get("tier"),
        "shadow_score_after": after.get("total"),
        "tier_after": after.get("tier"),
        "score_is_loop_condition": {"threshold_tier": "A", "state": score_state, "passed": score_ok},
        "citation_ready": citation.get("verdict"),
        "promotion_would": promotion,
        "seo_export": export,
        "static_proofs": static,
        "runtime_proofs": runtime,
        "verdicts": {
            "projection_operational": projection_operational,
            "outcome_status": outcome_status,
            "business_loop_closed": business_loop_closed,
        },
        "loop_closed": loop_closed,
        "page_quality_ready": page_quality_ready,            # ADR-094 — additif (HOLD tant que composants externes non livrés)
        "page_quality_components": page_quality_components,
        "remaining_blockers": blockers,
        "pending": pending,
        "unknown": unknown,
        "baseline_ref": baseline_ref,
        "evidence_provided": bool(evidence),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Orchestrateur boucle contenu — rapport de trajectoire (report-only).")
    ap.add_argument("--entity", required=True, help="type:slug, ex. gamme:filtre-a-air")
    ap.add_argument("--wiki-root", type=Path, default=SCRIPTS_DIR.parent)
    ap.add_argument("--raw-root", type=Path, default=Path("/opt/automecanik/automecanik-raw"))
    ap.add_argument("--monorepo-root", type=Path, default=Path("/opt/automecanik/app"))
    ap.add_argument("--baseline-ref", default="origin/main", help="ref git pour le score 'before' (effet contenu)")
    ap.add_argument("--threshold", type=float, default=0.80, help="seuil promotion simulé (dry-run)")
    ap.add_argument("--evidence", type=Path, default=None,
                    help="JSON de preuves runtime 3B (export_generated, projection_run_succeeded, "
                         "active_version_present, projection_rpc_readable, page_render_consumed_projection, "
                         "outcome_observed). Sans lui → UNKNOWN (jamais inventé).")
    ap.add_argument("--strict", action="store_true", help="exit 1 si business_loop_closed=false")
    args = ap.parse_args(argv)

    evidence = None
    if args.evidence is not None:
        if not args.evidence.is_file():
            print(f"--evidence introuvable: {args.evidence}", file=sys.stderr)
            return 2
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))

    report = run(args.entity, args.wiki_root, args.raw_root, args.monorepo_root,
                 args.baseline_ref, args.threshold, evidence)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.strict and not report["loop_closed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
