#!/usr/bin/env python3
"""gap1_auto_review — DRIVER pipeline auto GAP-1 : authoring → coverage-map candidate → auto-review.

Chaîne (owner 2026-07-02, production auto contrôlée) :
  author_from_raw → gen_coverage_map → [gates EXISTANTS] shadow_score + check-coverage-map + quality-gates
  → VERDICT auto-review + garde sécurité ADR-091.

Report-only, 0 mutation (fiche/coverage écrites dans un dossier SHADOW temporaire, JAMAIS proposals/ réel),
0 LLM, 0 DB, 0 promotion réelle. Réutilise les scorers/validateurs existants (verify-before-invent) — ne
réimplémente rien.

VERDICT — Safety Auto-Gate (quality-gates.md §7). Un seul décideur : la décision canonique
(`promotion_decision`) ; gap1 la REPORTE et y ajoute ses conditions sur les claims RAW extraits.
  • `auto_promote_eligible`           — non-sécurité, décision canonique ELIGIBLE.
  • `auto_blocked`                    — non-sécurité, décision canonique non éligible (codes exacts).
  • `safety_auto_blocked`             — sécurité, ≥1 condition non prouvée : condition RAW de gap1, condition
                                        de la Safety Auto-Gate canonique ou autre motif canonique. Raison
                                        TECHNIQUE (capturer, sourcer, corriger), jamais une tâche humaine.
  • `blocked_by_current_safety_policy`— sécurité, toutes les conditions prouvées ; seule la politique bloque
                                        (`promotion_decision.SAFETY_AUTO_APPROVAL_ADR` vide). Se lève par une
                                        PR WIKI citant l'ADR vault acceptée, jamais par option ni variable.
  • `safety_auto_approved`            — sécurité, décision canonique ELIGIBLE et 0 condition RAW bloquante.
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
import promotion_decision as promo_decision  # noqa: E402  (A4 : décideur canonique unique, pydantic-free)

NUMERIC_RANGES_PATH = REPO_ROOT / "_meta" / "numeric-plausibility.yaml"


def _load_numeric_ranges() -> dict:
    """Plages chiffrées via le chargeur unique `promotion_decision.load_numeric_ranges`.

    Absent → {} (fail-closed : toute valeur → numeric_ambiguous, rien ne se vérifie).
    Illisible ou mal formé → {} + message OBSERVABLE sur stderr (fail-closed, pas de repli silencieux)."""
    try:
        return promo_decision.load_numeric_ranges(NUMERIC_RANGES_PATH)
    except ValueError as exc:
        print(f"[numeric-lock] {exc} → 0 plage chargée, toute valeur numérique BLOQUÉE (fail-closed).",
              file=sys.stderr)
        return {}


def _resolve_status(c: dict, catalog: dict, valid_sections: set) -> str:
    """source_status d'un claim via la MÊME logique que gen_coverage_map.generate (page-level, Option A).

    Gate IDENTIQUE à generate() : cataloged **ET** `section ∈ valid_sections` **ET** type autoritaire
    **ET** `is_page_proven` (catalog status: active) → token coverage `captured` ; sinon pending_capture.
    Ne PAS relâcher ce prédicat (auto-review 2026-07-03 : une copie laxiste sans le gate section = dérive fail-open)."""
    cat_slug = catalog["domain_to_slug"].get(c["domain"])
    if not cat_slug or c.get("section") not in valid_sections:
        return "pending_capture"
    entry = catalog["slugs"][cat_slug]
    authoritative = str(entry.get("type", "")) in cov_mod._authoritative_types()
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


def _raw_ref_gate(catalog_slugs: dict) -> tuple[bool, list[str], list[str]]:
    """Exécute le gate EXISTANT `gate_source_catalog_raw_refs` (Plan P2 : FK `manifest_id` + hash drift du
    raw_ref cross-repo) sur les entrées du source-catalog — rend VRAI, dans le flux GAP-1, le contrat G1
    « une entrée `active` n'est utilisable que si son raw_ref est vérifié par les gates existants ».

    0 logique FK/hash réimplémentée : réutilise la FONCTION du gate existant. Charge le module hyphené
    `quality-gates.py` DIRECTEMENT via importlib (même technique que `gates/_common.load_legacy_gates_module`
    mais SANS passer par `gates/_common`, qui importe pydantic au niveau module et n'est PAS disponible dans
    le job CI pydantic-free « Python quality gates ») → le pipeline GAP-1 reste pydantic-free. Rend
    `(ok, failures, warnings)` : `ok=False` ⇔ ≥1 failure (source_unreferenceable / raw_ref_missing_manifest_id
    / raw_ref_malformed / source_unresolved / source_sha_drift). Les warnings (`raw_inventory_unreachable` =
    fail-open GOUVERNÉ quand le raw n'est pas checkouté ; `legacy_archived_at_deprecated`) NE bloquent PAS."""
    import importlib.util
    legacy_path = SCRIPTS_DIR / "quality-gates.py"
    spec = importlib.util.spec_from_file_location("_quality_gates_legacy", legacy_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load legacy gates module: {legacy_path}")
    legacy = importlib.util.module_from_spec(spec)
    sys.modules["_quality_gates_legacy"] = legacy
    spec.loader.exec_module(legacy)
    failures, warnings = legacy.gate_source_catalog_raw_refs(catalog_slugs)
    return (not failures), list(failures), list(warnings)


def _is_safety(slug: str, fm: dict) -> bool:
    try:
        import safety_families as sf
        return sf.is_safety_proposal({**fm, "slug": slug})
    except Exception:
        return True  # fail-closed


# Safety Auto-Gate — conditions propres à gap1, sur les claims RAW extraits (la fiche publiée, elle, est
# jugée par la décision canonique : planchers A/C, 5 contrôles qualité, exactitude chiffrée du texte rendu,
# no_disputed_claims, diagnostic_safe, manual_review, couverture stricte, régression, provenance, politique).
def _raw_claim_conditions(cov_report: dict, numeric_exactitude_verified: bool | None = None,
                          source_catalog_raw_refs_ok: bool | None = None) -> dict:
    """None = non évalué (absent du résultat) ; bool = condition évaluée."""
    conditions = {
        "page_level_all_captured": (cov_report.get("valid_entries", 0) > 0
                                    and cov_report.get("entries_page_pending_capped", 0) == 0),
        "no_pending_source_validation": cov_report.get("candidate_sources", 0) == 0,
    }
    # Lock valeur numérique sur TOUS les claims RAW authored (ADR-093 numeric-exactitude hole).
    if numeric_exactitude_verified is not None:
        conditions["numeric_exactitude_verified"] = bool(numeric_exactitude_verified)
    # Gate raw_ref cross-repo EXISTANT (gate_source_catalog_raw_refs, Plan P2) : échec FK/hash → bloque.
    if source_catalog_raw_refs_ok is not None:
        conditions["source_catalog_raw_refs_ok"] = bool(source_catalog_raw_refs_ok)
    return conditions


def _safety_auto_gate(cov_report: dict, numeric_exactitude_verified: bool | None = None,
                      source_catalog_raw_refs_ok: bool | None = None,
                      promotion_decision: dict | None = None) -> dict:
    """Union des conditions RAW de gap1 et de la décision canonique (jamais re-décidée ici).

    `blocking` liste tout ce qui n'est pas prouvé ; `policy_only` ⇔ rien d'autre que la politique
    (`SAFETY_HUMAN_REVIEW` sans condition bloquante). Fail-closed : décision absente ou non éligible
    sans motif = bloquant."""
    raw_claims = _raw_claim_conditions(cov_report, numeric_exactitude_verified, source_catalog_raw_refs_ok)
    pdz = promotion_decision or {}
    reasons = [r for r in (pdz.get("blocking_reasons") or []) if isinstance(r, dict)]
    safety = next((r for r in reasons if r.get("code") == "SAFETY_HUMAN_REVIEW"), None)
    safety_evidence = (safety or {}).get("evidence") or {}
    eligible = pdz.get("eligible") is True and pdz.get("promotion_status") == "ELIGIBLE"
    canonical = {
        "promotion_status": pdz.get("promotion_status") or "NO_CANONICAL_DECISION",
        "eligible": eligible,
        "safety_blocking_conditions": list(safety_evidence.get("blocking_conditions") or []),
        "other_blocking_codes": [r.get("code") for r in reasons if r.get("code") != "SAFETY_HUMAN_REVIEW"],
        "policy": safety_evidence.get("policy"),
    }
    blocking = [k for k, ok in raw_claims.items() if not ok]
    if not pdz:
        blocking.append("canonical_decision_available")
    if safety is not None and "blocking_conditions" not in safety_evidence:
        blocking.append("canonical_safety_conditions_reported")
    blocking += canonical["safety_blocking_conditions"] + canonical["other_blocking_codes"]
    if pdz and not blocking and not eligible and safety is None:
        blocking.append("canonical_decision_eligible")
    return {"raw_claims": raw_claims, "canonical": canonical, "blocking": blocking,
            "policy_only": not blocking and safety is not None}


def compute_verdict(safety: bool, cov_report: dict, *,
                    numeric_exactitude_verified: bool | None = None,
                    source_catalog_raw_refs_ok: bool | None = None,
                    promotion_decision: dict | None = None) -> dict:
    """Verdict auto-review PUR (testable). Aucun `human_review`.

    La promotion vient de la DÉCISION CANONIQUE EMBARQUÉE (promote.py : substance + coverage +
    regression + provenance, et Safety Auto-Gate pour la sécurité), JAMAIS d'un tier/floor local.
    `promotion_decision is None` ⇒ bloqué (fail-closed). Sécurité : union avec les conditions RAW."""
    if not safety:
        pdz = promotion_decision or {}
        if pdz.get("eligible") is True and pdz.get("promotion_status") == "ELIGIBLE":
            return {"verdict": "auto_promote_eligible",
                    "reason": "non-sécurité, décision canonique ELIGIBLE "
                              "(promote.py composition : substance+coverage+regression+provenance)"}
        codes = [r.get("code") for r in (pdz.get("blocking_reasons") or []) if isinstance(r, dict)]
        status = pdz.get("promotion_status") or "NO_CANONICAL_DECISION"
        return {"verdict": "auto_blocked",
                "reason": f"non-sécurité, décision canonique {status} : {codes or 'aucune décision fournie'}"}
    gate = _safety_auto_gate(cov_report, numeric_exactitude_verified, source_catalog_raw_refs_ok,
                             promotion_decision)
    if gate["blocking"]:
        return {"verdict": "safety_auto_blocked", "gate": gate,
                "reason": "Safety Auto-Gate KO (raisons techniques, PAS besoin humain) : "
                          + ", ".join(gate["blocking"])}
    if gate["policy_only"]:
        return {"verdict": "blocked_by_current_safety_policy", "gate": gate,
                "reason": "Safety Auto-Gate : toutes les conditions prouvées ; auto-validation sécurité non "
                          "ratifiée (promotion_decision.SAFETY_AUTO_APPROVAL_ADR vide) → se lève par PR WIKI "
                          "citant l'ADR vault acceptée, jamais par contournement code"}
    return {"verdict": "safety_auto_approved", "gate": gate,
            "reason": "Safety Auto-Gate PASS, décision canonique ELIGIBLE "
                      f"(politique {promo_decision.SAFETY_AUTO_APPROVAL_ADR})"}


def _canonical_promotion(fiche_path: Path, wiki_root: Path, raw_root: Path) -> dict:
    """A4 : décision de promotion CANONIQUE (A3) sur le shadow fiche — gap1 EMBARQUE
    l'objet, ne re-décide/re-score/route pas. `wiki_root = workdir` (contexte shadow :
    fiche pas encore dans le wiki ⇒ coverage/provenance UNAVAILABLE = honnête, route capture).
    Fail-closed : toute erreur → décision UNKNOWN_FAIL_CLOSED typée (jamais skip silencieux)."""
    try:
        return promo_decision.canonical_promotion_decision(fiche_path, wiki_root, raw_root=raw_root)
    except Exception as exc:  # noqa: BLE001
        return {"schema_version": promo_decision.SCHEMA_VERSION, "substance_tier": None,
                "promotion_status": "UNKNOWN_FAIL_CLOSED", "eligible": False,
                "blocking_reasons": [{"code": "PROMOTION_DECISION_ERROR", "owner_stage": "PROMOTION",
                                      "detector_stage": "GAP1_REPORTER",
                                      "evidence": {"detail": str(exc)}}]}


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

    # 3-ter) GATE raw_ref cross-repo EXISTANT (gate_source_catalog_raw_refs, Plan P2) exécuté DANS le flux
    #        GAP-1 → rend vrai le contrat G1 (active+raw_ref réellement vérifié par le gate, pas juste supposé).
    #        Report-only ; alimente une condition RAW DÉDIÉE de la Safety Auto-Gate (les 5 contrôles qualité
    #        de la fiche sont, eux, jugés par la décision canonique : `no_quality_gate_fail`).
    raw_refs_ok, raw_ref_failures, raw_ref_warnings = _raw_ref_gate(cov_mod._load_catalog()["slugs"])
    # A6 : plus de `if safety else None` local. Le raw_ref/provenance NON-safety n'est PLUS ignoré
    # ici : il est ENFORCÉ par la décision canonique embarquée (provenance, A3/A4). Cette valeur ne
    # sert plus qu'à la classification de la Safety Auto-Gate (branche sécurité) — fournie telle quelle.
    raw_refs_gate_input = raw_refs_ok

    # 4-bis) DÉCISION DE PROMOTION CANONIQUE (A3) — UN SEUL décideur : gap1 embarque l'objet,
    #        ne calcule plus l'éligibilité (fin du décideur parallèle `auto_promote_eligible`).
    promotion = _canonical_promotion(fiche_path, workdir, raw_root)

    # 4) VERDICT auto-review — Safety Auto-Gate (0 `human_review` ; goulot humain remplacé par gate auto)
    tier = (score or {}).get("tier")
    floors_ko = (score or {}).get("floors_failed") or []
    v = compute_verdict(safety, cov_report, numeric_exactitude_verified=numeric_gate_input,
                        source_catalog_raw_refs_ok=raw_refs_gate_input, promotion_decision=promotion)

    return {
        "slug": slug,
        "safety_family": safety,
        "safety_auto_approval_adr": promo_decision.SAFETY_AUTO_APPROVAL_ADR,
        "authoring": {"editorial_sections": author_report.get("editorial_sections"),
                      "facts_total": author_report.get("facts_total"),
                      "related_gammes": author_report.get("related_gammes"),
                      "commerce_intent": author_report.get("commerce_intent"),
                      # A7 : comptabilité de perte RAW visible (authored / hard_fail / conservation)
                      "authored": author_report.get("authored"),
                      "authoring_hard_fail": author_report.get("hard_fail"),
                      "extraction_accounting": author_report.get("extraction_accounting")},
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
        "source_catalog_raw_refs": {"ok": raw_refs_ok,
                                    "failures": raw_ref_failures[:8], "failures_total": len(raw_ref_failures),
                                    "warnings": raw_ref_warnings[:8], "warnings_total": len(raw_ref_warnings)},
        "promotion_decision": promotion,  # A4 : objet PromotionDecision canonique EMBARQUÉ (0 reconstruction)
        "verdict": v["verdict"],
        "verdict_reason": v["reason"],
        "safety_auto_gate": v.get("gate"),
        "invariants": ["shadow-only (0 mutation proposals/catalog réel)", "0 LLM/0 DB/0 promotion",
                       "sources inconnues = pending_source_validation (ne comptent pas dim A)",
                       "sécurité : blocage = gate AUTO (technique) ou politique (gouvernance) — "
                       "jamais un goulot humain ; lever la politique = PR WIKI citant l'ADR vault acceptée"],
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
