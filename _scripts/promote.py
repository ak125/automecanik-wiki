#!/usr/bin/env python3
"""
promote — Promotion WIKI auto-tiered (ADR-083, amende ADR-033 ; réf. ADR-059).

**Adapter CLI** (click) au-dessus de la bibliothèque canonique `promotion_decision`.
Frontière stricte : CLI → bibliothèque, JAMAIS bibliothèque → CLI. Le cœur métier
(evaluate_tier, gates composition, apply_promotion, résolveurs baseline) vit dans
`promotion_decision.py` (click-free) ; ce module l'importe et l'expose au shell.

Décide la promotion d'une proposal validée vers le canon wiki
(`review_status: approved` + `exportable.seo: true`) via une PORTE DÉTERMINISTE
à deux tiers. Compose les 5 gates EXISTANTS (`_scripts/gates/`) + la formule
`compute-confidence-score.py`. **N'enrichit / ne génère JAMAIS** — il filtre,
décide, et DÉPLACE le canon proposé — écrit wiki/ puis supprime la proposal source,
move-semantics imposée par `check-slug-uniqueness` (mêmes invariants que `build_exports_seo.py`).

Pipeline :
    proposals/<slug>.md (review_status in {proposed, in_review})
        ↓ porte tiered déterministe (gates + confidence + truth_level + source diversity)
        ↓ TIER A  → wiki/<entity_type>/<slug>.md (review_status: approved, exportable.seo: true,
        ↓            reviewed_by: skill:promoter@<sha>, auto_promoted: true, promotion_tier: A)
        ↓ TIER B  → reste in_review (humain requis). JAMAIS approuvé automatiquement.

TIER A (auto) — promu SSI TOUT est vrai :
    - les 5 gate wrappers (source/claim/contradiction/risk/confidence) = PASS ;
    - confidence_score >= AUTO_PROMOTE_THRESHOLD ;
    - truth_level in {L1, L2} ;
    - >= 2 source_refs de `kind` distincts.
TIER B (humain) — tout le reste : un gate warn/fail, score insuffisant, L3/L4,
    diversité de sources insuffisante. Le jugement E-E-A-T / sécurité reste humain.

Fail-closed : toute exception / tout doute → TIER B (jamais d'auto-approve sur erreur).
No-op par défaut : AUTO_PROMOTE_THRESHOLD = 1.01 (inatteignable) → 0 promotion auto,
    comportement identique à aujourd'hui (100% humain). Owner abaisse à 0.80 pour activer.

Garde-fous (vérifiés par test_promote.py) : 0 LLM, 0 DB, 0 nouveau gate atomique,
    écriture uniquement sous wiki/<entity_type>/.

Usage :
    promote.py --wiki-root /opt/automecanik/automecanik-wiki --all --dry-run
    promote.py --wiki-root ... --target proposals/colonne-de-direction.md --apply
    promote.py --wiki-root ... --all --threshold 0.80 --apply

Exit : 0 — ok (promu/skipped) · 1 — source invalide · 2 — config/canon introuvable.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Frontière : le CLI IMPORTE la bibliothèque canonique (jamais l'inverse). Tout le
# cœur métier (constantes gouvernées ADR-083, evaluate_tier, apply_promotion,
# résolveurs baseline, décision canonique) vit dans promotion_decision (click-free).
from promotion_decision import (  # noqa: E402 — import après sys.path (adapter CLI → library)
    AUTO_PROMOTE_THRESHOLD,
    AUTO_PROMOTE_TRUTH_LEVELS,  # noqa: F401 — ré-exporté (contrat test_promote)
    PromotionInputError,
    _canon_already_approved,
    _compute_shadow,  # noqa: F401 — ré-exporté (contrat test_promote)
    _load_confidence_fn,
    _load_gates,
    _parse_markdown,
    _promotion_target_path,  # noqa: F401 — ré-exporté (contrat test_promote)
    apply_promotion,
    authorize_apply,
    canonical_promotion_decision,
    evaluate_tier,  # noqa: F401 — ré-exporté (contrat test_promote / test_promotion_decision)
)

# Statuts d'entrée promouvables — scope du scan CLI uniquement (pas de logique métier).
PROMOTABLE_INPUT_STATUSES = {"proposed", "in_review"}


# --- CLI ----------------------------------------------------------------------
def _candidate_files(wiki_root: Path, target: str | None, entity_id: str | None) -> list[Path]:
    proposals = wiki_root / "proposals"
    if target:
        p = (wiki_root / target).resolve() if not Path(target).is_absolute() else Path(target)
        return [p]
    files = sorted(proposals.glob("*.md")) if proposals.is_dir() else []
    if entity_id:
        slug = entity_id.split(":", 1)[-1]
        files = [f for f in files if slug in f.stem]
    return files


@click.command()
@click.option("--wiki-root", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True)
@click.option("--target", default=None, help="Une proposal précise (relatif au wiki-root).")
@click.option("--entity-id", default=None, help="Filtre par slug (ex: gamme:colonne-de-direction).")
@click.option("--all", "scan_all", is_flag=True, help="Scanner toutes les proposals/.")
@click.option("--threshold", type=float, default=AUTO_PROMOTE_THRESHOLD, show_default=True,
              help="Seuil confidence auto-promotion. 1.01 = no-op (aucune auto-promotion).")
@click.option("--raw-root", "raw_root", type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None, help="Checkout automecanik-raw (topology cross-repo). Absent ⇒ "
                                 "provenance UNAVAILABLE (fail-closed, jamais skip silencieux).")
@click.option("--apply", "do_apply", is_flag=True, help="Écrit les promotions éligibles (sinon dry-run).")
@click.option("--dry-run", "dry_run", is_flag=True, help="Force le dry-run (défaut si --apply absent).")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def main(wiki_root: Path, target: str | None, entity_id: str | None, scan_all: bool,
         threshold: float, raw_root: Path | None, do_apply: bool, dry_run: bool,
         output_format: str) -> None:
    if not (target or scan_all or entity_id):
        raise click.UsageError("préciser --target, --entity-id ou --all")
    if dry_run:
        do_apply = False

    # Frontière CLI : une erreur de cœur métier (PromotionInputError) est traduite ICI
    # en click.ClickException — la bibliothèque ne dépend jamais de click.
    try:
        gates = _load_gates()
        compute_score = _load_confidence_fn()
    except PromotionInputError as exc:
        raise click.ClickException(str(exc)) from exc
    # Topology (A3d) : --raw-root rend la provenance cross-repo enforçable. L'évaluateur
    # provenance lit AUTOMECANIK_RAW_PATH → le CLI (composition root) le renseigne depuis
    # --raw-root sans écraser un override explicite. Absent ⇒ provenance UNAVAILABLE.
    if raw_root and not os.environ.get("AUTOMECANIK_RAW_PATH"):
        os.environ["AUTOMECANIK_RAW_PATH"] = str(Path(raw_root).resolve())
    files = _candidate_files(wiki_root, target, entity_id)

    report: list[dict] = []
    for f in files:
        try:
            fm, body = _parse_markdown(f)
            if fm.get("review_status") not in PROMOTABLE_INPUT_STATUSES:
                report.append({"file": str(f), "tier": "skip", "promotion_status": "SKIP",
                               "eligible": False,
                               "reason": f"review_status={fm.get('review_status')} non promouvable"})
                continue
            if _canon_already_approved(wiki_root, fm):
                report.append({"file": str(f), "tier": "skip", "promotion_status": "SKIP",
                               "eligible": False,
                               "reason": "canon déjà approved — pas d'écrasement (idempotent)"})
                continue
            # UN SEUL décideur canonique : dry-run ET apply partagent ce chemin
            # (snapshot → collect → decide). --apply ne redécide jamais.
            decision = canonical_promotion_decision(
                f, wiki_root, raw_root=raw_root, threshold=threshold,
                gates=gates, compute_score=compute_score)
        except Exception as exc:  # fail-closed
            report.append({"file": str(f), "tier": "B", "promotion_status": "BLOCKED",
                           "eligible": False,
                           "blocking_reasons": [{"code": "EVALUATION_ERROR",
                                                 "evidence": {"detail": str(exc)}}]})
            continue

        evaluation = decision.get("evaluation") or {}
        # rétro-compat report : le pilote (SENSOR) lit `tier` (∈ {A,S}) et confidence_score.
        entry = {"file": str(f), **decision, "tier": evaluation.get("tier"),
                 "confidence_score": evaluation.get("confidence_score")}

        if do_apply:
            ok, refusal = authorize_apply(decision, f, wiki_root, raw_root=raw_root)
            if ok:
                try:
                    # apply_promotion = DUMB EXECUTOR : stampe l'évidence déjà décidée + déplace.
                    out = apply_promotion(f, fm, body, wiki_root, evaluation)
                    entry["promoted_to"] = str(out)
                except Exception as exc:  # fail-closed
                    entry["tier"] = "B"
                    entry["apply_error"] = str(exc)
            else:
                entry["apply_refused"] = refusal
        report.append(entry)

    auto = sum(1 for r in report if r.get("tier") == "A")
    human = sum(1 for r in report if r.get("tier") == "B")
    eligible = sum(1 for r in report if r.get("eligible") is True)
    blocked = sum(1 for r in report if r.get("promotion_status") == "BLOCKED")
    unknown = sum(1 for r in report if r.get("promotion_status") == "UNKNOWN_FAIL_CLOSED")
    if output_format == "json":
        click.echo(json.dumps({"threshold": threshold, "apply": do_apply,
                               "tier_A": auto, "tier_B": human,
                               "eligible": eligible, "blocked": blocked,
                               "unknown_fail_closed": unknown, "report": report},
                              ensure_ascii=False, indent=2))
    else:
        for r in report:
            codes = [x.get("code") for x in (r.get("blocking_reasons") or []) if isinstance(x, dict)]
            click.echo(f"[{r.get('promotion_status', r.get('tier'))}] {Path(r['file']).name} "
                       f"tier={r.get('substance_tier', '-')} eligible={r.get('eligible')} "
                       f"{codes or r.get('reason', '')}")
        click.echo(f"\néligibles={eligible}  bloqués={blocked}  unknown={unknown}  "
                   f"(TIER A legacy={auto})  seuil={threshold}  apply={do_apply}")
    sys.exit(0)


if __name__ == "__main__":
    main()
