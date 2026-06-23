#!/usr/bin/env python3
"""
promote — Promotion WIKI auto-tiered (ADR-083, amende ADR-033 ; réf. ADR-059).

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

import importlib.util
import json
import os
import re
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
# Cutover ADR-088 (gaté par flag, défaut OFF) : quel moteur de substance gate l'auto-promotion.
#   legacy      = confidence_score scalaire 0-1 >= seuil (comportement historique, défaut)
#   adr088_6dim = tier 6-dim shadow_score (planchers entity-aware) ∈ {A,S}
# Le FLIP (mettre PROMOTE_GATE_ENGINE=adr088_6dim) reste owner-gated : ADR-088 accepté au vault
# + 3 critères §F mesurés (new⊆old · known-bad→B/C · ≥1 fiche TIER A). Fail-closed dans les 2 modes.
PROMOTE_GATE_ENGINE_ENV = "PROMOTE_GATE_ENGINE"
ADR088_PROMOTE_TIERS = {"A", "S"}
MIN_DISTINCT_SOURCE_KINDS = 2
PROMOTER_ID = "skill:promoter"
PROMOTABLE_INPUT_STATUSES = {"proposed", "in_review"}
WIKI_ENTITY_DIRS = {"gamme", "vehicle", "constructeur", "diagnostic"}

# --- Invariant SÉCURITÉ : familles sécurité-critiques → JAMAIS auto-promues ----
# Classification déléguée au SINGLE SOURCE `safety_families.is_safety_proposal`
# (ADR fix #5) — partagé avec `quality-gates.gate_safety_unsourced`. Import paresseux
# (même pattern que `_load_gates` / `_compute_shadow` : modules chargés par chemin).
# Fail-closed : une fiche sécurité reste 100% revue humaine, même substance forte.
_safety_families_mod = None


def _is_safety_proposal(fm: dict) -> bool:
    """Délègue au classifieur sécurité unifié (single source, ADR fix #5). Fail-closed."""
    global _safety_families_mod
    try:
        if _safety_families_mod is None:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import safety_families as _sf
            _safety_families_mod = _sf
        return _safety_families_mod.is_safety_proposal(fm)
    except Exception:
        return True  # fail-closed : doute → sécurité → revue humaine


# --- Invariant ANTI-NUMBER-SWAPPING : valeurs numériques critiques → revue humaine -
# Axiome n°0 : le contenu ne FABRIQUE jamais une valeur. La provenance PAR-VALEUR
# n'existe pas dans le modèle (`source_refs` = niveau document) → la corroboration
# automatique par-nombre est IMPOSSIBLE. On route donc vers la revue humaine les
# valeurs HIGH-HARM (couple, pression) où un number-swapping est dangereux ; les
# cotes mm/µm et températures sont FLAGGÉES (observabilité) sans bloquer (mesuré :
# block ≈ 2 fiches véhicule à couple/pression ; les fiches sécurité sont déjà bloquées).
# Enforcement par-valeur complet = futur (provenance par-claim au schéma, ADR-gated).
_NUM_PREFIX = r"(?<![\w.,])\d[\d.,   ]*\s?"
CRITICAL_NUMERIC_BLOCK = re.compile(
    _NUM_PREFIX + r"(Nm|N·m|N\.m|daNm|m\.kg|mkg|bar|kPa|MPa|psi)\b", re.IGNORECASE
)
CRITICAL_NUMERIC_OBSERVE = re.compile(
    _NUM_PREFIX + r"(mm|µm|μm|microns?|°\s?C)\b", re.IGNORECASE
)


def _numeric_review_flags(body: str) -> dict:
    """Inventaire des valeurs numériques critiques d'un corps de proposal.

    `block`   = couple/pression (HIGH-HARM) : number-swapping dangereux, non
                auto-vérifiable → revue humaine obligatoire avant auto-promotion.
    `observe` = cotes / températures : flaggées pour le relecteur, NE bloquent PAS.
    Fail-closed : toute erreur → `block` non vide (route vers revue humaine).
    """
    try:
        block = sorted({m.group(0).strip() for m in CRITICAL_NUMERIC_BLOCK.finditer(body or "")})
        observe = sorted({m.group(0).strip() for m in CRITICAL_NUMERIC_OBSERVE.finditer(body or "")})
        return {"block": block, "observe": observe}
    except Exception as exc:  # fail-closed : doute → revue humaine
        return {"block": [f"<erreur classif numérique: {exc}>"], "observe": []}


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


# --- Shadow scoring 6-dim (ADR-088 §F : observabilité AVANT cutover) ----------
# SHADOW pur : calcule le tier 6-dim À CÔTÉ de la décision legacy, l'attache à
# l'evidence pour mesurer les 3 critères de cutover sur le VRAI chemin de promotion,
# SANS jamais modifier la décision de porte. Fail-closed total : toute erreur →
# None (jamais de blocage, jamais d'exception remontée à evaluate_tier).
def _compute_shadow(fm: dict, body: str, target: Path, wiki_root: Path) -> dict | None:
    """Tier shadow 6-dim (report-only). Retourne un dict observabilité ou None si indéterminable.

    Réutilise `shadow_score.score` (ADR-088 Phase 3.3) + `reality_manifest` (lecture 0-DB).
    coverage-map : réutilise `shadow_score._load_coverage_map` (PR #53) si présent, sinon dégrade
    proprement à `coverage_map=None` (dim A → `A:no_coverage_map(dégradé)`, jamais de crash).
    """
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        import reality_manifest as _rm
        import shadow_score as _ss

        manifest = _rm.load_manifest(SCRIPTS_DIR.parent / "_meta" / "reality-manifest.json")
        cmap = None
        loader = getattr(_ss, "_load_coverage_map", None)  # fourni par PR #53
        if callable(loader):
            cmap = loader(fm.get("slug") or target.stem, wiki_root / "proposals")
        ctx = {"path": str(target), "manifest": manifest, "coverage_map": cmap,
               "wiki_root": wiki_root}
        r = _ss.score(fm, body, ctx)
        return {
            "shadow_tier": r.tier,
            "shadow_total": r.total,
            "shadow_dims": r.dims,
            "shadow_applicable": r.applicable,
            "shadow_floors_failed": r.floors_failed,
            "shadow_blocked": r.blocked,
            "manifest_status": _rm.status(manifest),
            "scorer": "shadow_score.score@6dim-v0",
        }
    except Exception as exc:  # noqa: BLE001 — fail-closed : observabilité best-effort, jamais bloquante
        return {"shadow_error": str(exc)}


# --- La porte tiered (cœur ADR-083) -------------------------------------------
def evaluate_tier(fm: dict, body: str, target: Path, wiki_root: Path,
                  threshold: float, gates, compute_score) -> dict:
    """
    Décision déterministe TIER A (auto) vs TIER B (humain). Fail-closed :
    toute exception est capturée par l'appelant → TIER B.
    """
    reasons: list[str] = []

    # INVARIANT SÉCURITÉ (fail-closed, prioritaire) : famille sécurité-critique →
    # JAMAIS auto-promue, quels que soient la substance et le moteur de gate. Force
    # TIER B (revue humaine ≠ auteur). Miroir de auto_review_wiki_proposal (monorepo).
    if _is_safety_proposal(fm):
        reasons.append(
            "safety: famille sécurité-critique → revue humaine obligatoire (jamais auto-promu)"
        )

    # INVARIANT ANTI-NUMBER-SWAPPING : valeurs HIGH-HARM (couple/pression) non
    # auto-vérifiables → revue humaine. Cotes/températures = observabilité (ne bloquent pas).
    numeric_flags = _numeric_review_flags(body)
    if numeric_flags["block"]:
        reasons.append(
            "numeric: valeurs critiques couple/pression non auto-vérifiables → "
            f"revue humaine (anti number-swapping): {numeric_flags['block'][:5]}"
        )

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

    # Le tier 6-dim est calculé dans les 2 modes : observabilité (toujours) + décisionnel (si flag on).
    shadow = _compute_shadow(fm, body, target, wiki_root)
    gate_engine = os.environ.get(PROMOTE_GATE_ENGINE_ENV, "legacy").strip().lower()
    if gate_engine == "adr088_6dim":
        # SUBSTANCE GATE = tier 6-dim (planchers entity-aware). Fail-closed : tier absent/erreur → blocage.
        st = (shadow or {}).get("shadow_tier")
        if st not in ADR088_PROMOTE_TIERS:
            why = st or (shadow or {}).get("shadow_error", "indéterminable")
            reasons.append(f"shadow_tier={why} (cutover ADR-088 : auto-promo exige A/S)")
    else:
        # SUBSTANCE GATE legacy (défaut) = confidence_score scalaire >= seuil.
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
        "gate_engine": gate_engine,
        "gate_status": {n: r.status for n, r in gate_results},
        "blocking_reasons": reasons,
        "shadow_score": shadow,
        "numeric_flags": numeric_flags,
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
    """Déplace la proposal vers le canon wiki approved (TIER A uniquement). 0 enrichissement.

    Move-semantics (invariant `check-slug-uniqueness`) : une gamme promue ne peut
    coexister comme proposal ET canon. On écrit le canon PUIS on supprime la proposal
    source. Traçabilité conservée : `promotion_evidence` + `provenance.promoted_from`
    + l'historique git. Fail-safe : la proposal n'est supprimée qu'APRÈS écriture d'un
    canon non-vide, et seulement si elle vit bien sous `proposals/`.
    """
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
    # SHADOW (ADR-088 §F) : trace le tier 6-dim si calculé, pour rendre les 3 critères
    # de cutover mesurables sur le chemin réel. .get → rétro-compat (decision sans shadow).
    shadow = decision.get("shadow_score")
    if shadow is not None:
        new_fm["promotion_evidence"]["shadow_score"] = shadow
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

    # Move-semantics : supprimer la proposal source APRÈS écriture du canon. Gardes :
    # (1) target est un vrai fichier, (2) sous proposals/ uniquement (jamais wiki/),
    # (3) distinct du canon, (4) canon bien écrit et non-vide. Une OSError éventuelle
    # remonte au handler de main() (pas de swallow silencieux — no-silent-fallback).
    proposals_root = (wiki_root / "proposals").resolve()
    if (
        target.is_file()
        and target.resolve() != out_path.resolve()
        and proposals_root in target.resolve().parents
        and out_path.is_file()
        and out_path.stat().st_size > 0
    ):
        target.unlink()

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
