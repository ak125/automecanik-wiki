#!/usr/bin/env python3
"""
promote — Promotion WIKI auto-tiered (ADR-083, amende ADR-033 ; réf. ADR-059).

Décide la promotion d'une proposal validée vers le canon wiki
(`review_status: approved` + `exportable.seo: true`) via une PORTE DÉTERMINISTE
à deux tiers. Compose les 5 gates EXISTANTS (`_scripts/gates/`) + la formule
`compute-confidence-score.py`. **N'enrichit / ne génère JAMAIS** — il filtre,
décide, et recopie le canon proposé (mêmes invariants que `build_exports_seo.py`).

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

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
import yaml

# --- Constantes gouvernées (ADR-083) -----------------------------------------
# Seuil no-op par défaut. 1.01 = inatteignable → 0 auto-promotion (= aujourd'hui).
# Activation = abaisser à 0.80 (valeur canon ADR-083), owner-décidé.
AUTO_PROMOTE_THRESHOLD = 1.01
AUTO_PROMOTE_TRUTH_LEVELS = {"L1", "L2"}
MIN_DISTINCT_SOURCE_KINDS = 2
PROMOTER_ID = "skill:promoter"
PROMOTABLE_INPUT_STATUSES = {"proposed", "in_review"}
WIKI_ENTITY_DIRS = {"gamme", "vehicle", "constructeur", "diagnostic"}

SCRIPTS_DIR = Path(__file__).resolve().parent
FRONTMATTER_SEPARATOR = "---"


# --- Composition de l'existant (aucun nouveau gate, aucun nouvel index) -------
def _load_gates():
    """Importe les 5 wrappers de gates existants (package _scripts/gates/)."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    from gates.claim_gate import run_claim_gate
    from gates.confidence_gate import run_confidence_gate
    from gates.contradiction_gate import run_contradiction_gate
    from gates.risk_gate import run_risk_gate
    from gates.source_gate import run_source_gate

    return [
        ("source", run_source_gate),
        ("claim", run_claim_gate),
        ("contradiction", run_contradiction_gate),
        ("risk", run_risk_gate),
        ("confidence", run_confidence_gate),
    ]


def _load_confidence_fn():
    """Charge compute_score depuis compute-confidence-score.py (filename à tirets)."""
    path = SCRIPTS_DIR / "compute-confidence-score.py"
    spec = importlib.util.spec_from_file_location("_confidence_score", path)
    if spec is None or spec.loader is None:
        raise click.ClickException(f"compute-confidence-score.py introuvable: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.compute_score


def _parse_markdown(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith(FRONTMATTER_SEPARATOR):
        raise click.ClickException(f"proposal sans frontmatter: {path}")
    parts = text.split(f"\n{FRONTMATTER_SEPARATOR}\n", 1)
    if len(parts) != 2:
        raise click.ClickException(f"frontmatter close-fence manquante: {path}")
    fm = yaml.safe_load(parts[0].lstrip(FRONTMATTER_SEPARATOR).lstrip("\n"))
    if not isinstance(fm, dict):
        raise click.ClickException(f"frontmatter non-dict: {path}")
    return fm, parts[1]


def _wiki_commit_sha(wiki_root: Path) -> str:
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=wiki_root, check=True, capture_output=True, text=True,
        )
        return out.stdout.strip()
    except Exception:
        return "0000000"


# --- La porte tiered (cœur ADR-083) -------------------------------------------
def evaluate_tier(fm: dict, body: str, target: Path, wiki_root: Path,
                  threshold: float, gates, compute_score) -> dict:
    """
    Décision déterministe TIER A (auto) vs TIER B (humain). Fail-closed :
    toute exception est capturée par l'appelant → TIER B.
    """
    reasons: list[str] = []

    gate_results = [(name, fn(target)) for name, fn in gates]
    failing = [(n, r.status) for n, r in gate_results if r.status != "pass"]
    if failing:
        reasons += [f"gate:{n}={s}" for n, s in failing]

    truth_level = fm.get("truth_level")
    if truth_level not in AUTO_PROMOTE_TRUTH_LEVELS:
        reasons.append(f"truth_level={truth_level} (auto exige L1/L2)")

    try:
        score = float(compute_score(fm, body, wiki_root))
    except Exception as exc:  # fail-closed
        reasons.append(f"confidence_score indéterminable: {exc}")
        score = 0.0
    if score < threshold:
        reasons.append(f"confidence_score={score:.2f} < seuil={threshold:.2f}")

    kinds = {
        s.get("kind")
        for s in (fm.get("source_refs") or [])
        if isinstance(s, dict) and s.get("kind")
    }
    if len(kinds) < MIN_DISTINCT_SOURCE_KINDS:
        reasons.append(f"source_refs kinds distincts={len(kinds)} (<{MIN_DISTINCT_SOURCE_KINDS})")

    tier = "A" if not reasons else "B"
    return {
        "tier": tier,
        "confidence_score": round(score, 4),
        "gate_status": {n: r.status for n, r in gate_results},
        "blocking_reasons": reasons,
    }


def _promotion_target_path(wiki_root: Path, fm: dict) -> Path:
    entity_type = fm.get("entity_type")
    slug = fm.get("slug")
    if entity_type not in WIKI_ENTITY_DIRS or not slug:
        raise click.ClickException(f"entity_type/slug invalides: {entity_type}/{slug}")
    out = (wiki_root / "wiki" / entity_type / f"{slug}.md").resolve()
    canon_root = (wiki_root / "wiki").resolve()
    # path enforcement strict — n'écrit JAMAIS hors wiki/<entity_type>/
    if canon_root not in out.parents:
        raise click.ClickException(f"refus écriture hors wiki/: {out}")
    return out


def _canon_already_approved(wiki_root: Path, fm: dict) -> bool:
    """
    True si wiki/<entity_type>/<slug>.md existe DÉJÀ en review_status: approved.

    Garde anti-écrasement (ADR-083 durcissement) : promote.py ne clobbe JAMAIS
    une fiche canon déjà validée (humain ou run antérieur). Fail-closed : fichier
    présent mais illisible → True (on ne touche pas).
    """
    entity_type = fm.get("entity_type")
    slug = fm.get("slug")
    if entity_type not in WIKI_ENTITY_DIRS or not slug:
        return False
    target = wiki_root / "wiki" / entity_type / f"{slug}.md"
    if not target.is_file():
        return False
    try:
        existing_fm, _ = _parse_markdown(target)
    except Exception:
        return True  # fail-closed : illisible → ne pas écraser
    return existing_fm.get("review_status") == "approved"


def apply_promotion(target: Path, fm: dict, body: str, wiki_root: Path,
                    decision: dict) -> Path:
    """Recopie la proposal en canon wiki approved (TIER A uniquement). 0 enrichissement."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sha = _wiki_commit_sha(wiki_root)
    out_path = _promotion_target_path(wiki_root, fm)
    # defense-in-depth : ne JAMAIS écraser une fiche canon déjà approved (idempotence / TOCTOU)
    if _canon_already_approved(wiki_root, fm):
        raise click.ClickException(f"refus écrasement canon déjà approved: {out_path}")

    new_fm = dict(fm)  # copie — aucune modification du contenu éditorial
    new_fm["review_status"] = "approved"
    new_fm["reviewed_by"] = f"{PROMOTER_ID}@{sha}"
    new_fm["reviewed_at"] = now
    new_fm["auto_promoted"] = True
    new_fm["promotion_tier"] = "A"
    new_fm["promotion_evidence"] = {
        "gate_status": decision["gate_status"],
        "confidence_score": decision["confidence_score"],
        "promoter": f"{PROMOTER_ID}@{sha}",
        "promoted_at": now,
    }
    exportable = dict(new_fm.get("exportable") or {})
    exportable["seo"] = True
    new_fm["exportable"] = exportable
    provenance = dict(new_fm.get("provenance") or {})
    provenance["promoted_from"] = str(target.relative_to(wiki_root))
    provenance["promoted_at"] = now
    new_fm["provenance"] = provenance

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = (
        f"{FRONTMATTER_SEPARATOR}\n"
        f"{yaml.safe_dump(new_fm, allow_unicode=True, sort_keys=False)}"
        f"{FRONTMATTER_SEPARATOR}\n{body}"
    )
    out_path.write_text(rendered, encoding="utf-8")
    return out_path


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
@click.option("--apply", "do_apply", is_flag=True, help="Écrit les promotions TIER A (sinon dry-run).")
@click.option("--dry-run", "dry_run", is_flag=True, help="Force le dry-run (défaut si --apply absent).")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def main(wiki_root: Path, target: str | None, entity_id: str | None, scan_all: bool,
         threshold: float, do_apply: bool, dry_run: bool, output_format: str) -> None:
    if not (target or scan_all or entity_id):
        raise click.UsageError("préciser --target, --entity-id ou --all")
    if dry_run:
        do_apply = False

    gates = _load_gates()
    compute_score = _load_confidence_fn()
    files = _candidate_files(wiki_root, target, entity_id)

    report: list[dict] = []
    for f in files:
        try:
            fm, body = _parse_markdown(f)
            if fm.get("review_status") not in PROMOTABLE_INPUT_STATUSES:
                report.append({"file": str(f), "tier": "skip",
                               "reason": f"review_status={fm.get('review_status')} non promouvable"})
                continue
            if _canon_already_approved(wiki_root, fm):
                report.append({"file": str(f), "tier": "skip",
                               "reason": "canon déjà approved — pas d'écrasement (idempotent)"})
                continue
            decision = evaluate_tier(fm, body, f, wiki_root, threshold, gates, compute_score)
        except Exception as exc:  # fail-closed → TIER B
            report.append({"file": str(f), "tier": "B", "blocking_reasons": [f"erreur: {exc}"]})
            continue

        entry = {"file": str(f), **decision}
        if decision["tier"] == "A" and do_apply:
            try:
                out = apply_promotion(f, fm, body, wiki_root, decision)
                entry["promoted_to"] = str(out)
            except Exception as exc:  # fail-closed
                entry["tier"] = "B"
                entry.setdefault("blocking_reasons", []).append(f"écriture échouée: {exc}")
        report.append(entry)

    auto = sum(1 for r in report if r.get("tier") == "A")
    human = sum(1 for r in report if r.get("tier") == "B")
    if output_format == "json":
        click.echo(json.dumps({"threshold": threshold, "apply": do_apply,
                               "tier_A": auto, "tier_B": human, "report": report},
                              ensure_ascii=False, indent=2))
    else:
        for r in report:
            click.echo(f"[{r.get('tier')}] {Path(r['file']).name} "
                       f"score={r.get('confidence_score','-')} {r.get('blocking_reasons', r.get('reason',''))}")
        click.echo(f"\nTIER A (auto)={auto}  TIER B (humain)={human}  "
                   f"seuil={threshold}  apply={do_apply}")
    sys.exit(0)


if __name__ == "__main__":
    main()
