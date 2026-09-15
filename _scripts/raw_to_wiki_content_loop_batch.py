#!/usr/bin/env python3
"""raw_to_wiki_content_loop_batch — TABLEAU DE BORD BACKLOG déterministe (REPORT-ONLY).

Thin wrapper batch au-dessus de `raw_to_wiki_content_loop_pilot` (Option A, cadrage owner
2026-07-15 : `audit/cadrage-batch-report-only-raw-to-wiki-loop-2026-07-15.md` au monorepo).

Périmètre STRICT (GO owner d'implémentation 2026-07-15, corrections revue #82) :
  • INPUT = UNIQUEMENT les entrées `subject_type: vehicle_gamme_fit` de la worklist RAW
    CANONIQUE `<raw_root>/manifests/ingestion-worklist.yaml`, VALIDÉES par le schéma canonique
    `<raw_root>/_schemas/ingestion-worklist.schema.json`. Les deux chemins sont DÉRIVÉS de
    raw_root — aucun chemin worklist/schema arbitraire n'est accepté (anti-couple-inventé).
  • Par couple : appelle le pilote SÉPARÉMENT pour la facette `gamme` et la facette `vehicle`,
    puis AGRÈGE UNIQUEMENT leur état. AUCUN modèle ni verdict `vehicle_gamme_fit` (0 score
    couple-level). Le verdict du pilote est RELAYÉ intact (clé imbriquée `verdicts`), jamais aplati.
  • Une facette est prête SEULEMENT si (a) elle se résout en `type:slug` explicite SANS invention,
    ET (b) l'artefact RAW référencé existe RÉELLEMENT sur disque sous `<raw_root>/sources/`.
    Sinon ⇒ INPUT_NOT_READY, SANS invoquer le pilote, SANS tentative de collecte.
  • Fail-closed : worklist/schéma invalide ou absent ⇒ exit != 0, AUCUN rapport partiel.
  • 0 écriture RAW/WIKI/DB/worklist : `--out` REFUSE tout chemin sous raw_root OU wiki_root
    (dépôts pipeline entiers) — pas seulement quelques sous-dossiers.
  • 0 promotion auto ; 0 RAG ; 0 invention (kw/URL/slug/page/entité). Autorité finale = HUMAINE.
  • Déterministe & traçable : tri stable, provenance (refs git), aucun horodatage. Reproductible.

⚠️ Succès de ce batch = « rapport déterministe et traçable », JAMAIS « boucle fermée » ni
   « scraper opérationnel » (anti-overclaim, cf. audit smart-scraper 2026-07-15).

Usage :
  python3 raw_to_wiki_content_loop_batch.py \
      [--raw-root DIR] [--wiki-root DIR] [--monorepo-root DIR] \
      [--baseline-ref origin/main] [--threshold 0.80] [--out FILE.json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

SUBJECT_TYPE = "vehicle_gamme_fit"
# États `capture.status` où un artefact RAW peut EXISTER (condition nécessaire, jamais suffisante :
# l'existence disque est re-vérifiée). TODO / REJECTED ⇒ INPUT_NOT_READY (aucune tentative de collecte).
CAPTURED_STATES = {"CAPTURED", "CAPTURED_NEEDS_REVIEW", "GATED", "PROMOTED"}

INPUT_NOT_READY = "INPUT_NOT_READY"
RESOLVED_PILOT_RAN = "RESOLVED_PILOT_RAN"
FACET_INVALID = "INVALID"


class WorklistError(Exception):
    """Worklist ou schéma canonique invalide/absent — fail-closed (jamais de skip silencieux)."""


class UnsafeOutputPath(Exception):
    """Chemin `--out` sous un dépôt pipeline RAW/WIKI — refusé (0 écriture pipeline/worklist)."""


# ── chemins CANONIQUES dérivés de raw_root (anti chemin arbitraire) ──────────

def canonical_paths(raw_root) -> tuple[Path, Path]:
    raw_root = Path(raw_root)
    return (raw_root / "manifests" / "ingestion-worklist.yaml",
            raw_root / "_schemas" / "ingestion-worklist.schema.json")


# ── chargement + validation schéma (fail-closed) ─────────────────────────────

def load_worklist(worklist_path: Path, schema_path: Path) -> dict:
    worklist_path, schema_path = Path(worklist_path), Path(schema_path)
    if not worklist_path.is_file():
        raise WorklistError(f"worklist canonique absente: {worklist_path}")
    if not schema_path.is_file():
        raise WorklistError(f"schéma canonique absent, validation impossible (fail-closed): {schema_path}")
    try:
        import yaml
        doc = yaml.safe_load(worklist_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise WorklistError(f"worklist illisible (YAML): {exc}") from exc
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise WorklistError(f"schéma illisible (JSON): {exc}") from exc
    try:
        import jsonschema
        jsonschema.validate(instance=doc, schema=schema)
    except Exception as exc:  # ValidationError | SchemaError → fail-closed
        raise WorklistError(f"worklist non conforme au schéma canonique (fail-closed): {exc}") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("worklist"), list):
        raise WorklistError("worklist: structure inattendue après validation")
    return doc


def select_couples(doc: dict) -> list[dict]:
    """Entrées vehicle_gamme_fit uniquement, triées par id (déterminisme)."""
    couples = [e for e in doc["worklist"] if e.get("subject_type") == SUBJECT_TYPE]
    return sorted(couples, key=lambda e: str(e.get("id", "")))


# ── résolution de facette (0 invention) ──────────────────────────────────────

def _resolve_gamme_facet(entry: dict):
    slug = entry.get("gamme")
    if isinstance(slug, str) and slug.strip():
        return f"gamme:{slug.strip()}", None
    return None, "aucun slug gamme explicite dans l'entrée worklist"


def _resolve_vehicle_facet(entry: dict):
    """La worklist ne porte PAS de slug véhicule explicite (schéma = brand/model/motorisation).
    Sans slug explicite, résolution IMPOSSIBLE — aucune synthèse (fail-closed, 0 invention).
    Chemin d'extension futur : un champ `vehicle.slug` explicite (contrat = GO owner/vault distinct)."""
    veh = entry.get("vehicle") or {}
    if isinstance(veh, dict) and isinstance(veh.get("slug"), str) and veh["slug"].strip():
        return f"vehicle:{veh['slug'].strip()}", None
    return None, ("l'entrée worklist ne porte pas de slug véhicule explicite "
                  "(schéma = brand/model/motorisation) — fail-closed, aucune synthèse de slug")


def _input_present(entry: dict, raw_root: Path):
    """Vrai SEULEMENT si un artefact RAW existe RÉELLEMENT sur disque, sous <raw_root>/sources/,
    et que le statut est un état capturé. Retourne (bool, raison_si_non)."""
    cap = entry.get("capture") or {}
    status = cap.get("status")
    if status not in CAPTURED_STATES:
        return False, f"capture.status={status} (aucune capture RAW)"
    raw_path = cap.get("raw_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return False, "capture.raw_path absent"
    sources_root = (Path(raw_root) / "sources").resolve()
    resolved = (Path(raw_root) / raw_path).resolve()
    if resolved != sources_root and sources_root not in resolved.parents:
        return False, f"raw_path hors de raw_root/sources (fail-closed): {raw_path}"
    if not resolved.exists():
        return False, f"artefact RAW absent sur disque: {raw_path}"
    return True, None


def _project_verdict(raw):
    """Projection COMPACTE : on RELAIE le verdict pilote intact (dont la clé imbriquée `verdicts`
    = projection_operational / outcome_status / business_loop_closed). On ne recalcule aucun score."""
    if not isinstance(raw, dict):
        return None
    out: dict = {}
    if isinstance(raw.get("verdicts"), dict):
        out["verdicts"] = raw["verdicts"]
    for k in ("remaining_blockers", "tier_after", "citation_ready", "page_quality_ready", "loop_closed"):
        if k in raw:
            out[k] = raw[k]
    return out or None


def _assess_facet(kind: str, entry: dict, roots: dict, baseline_ref: str,
                  threshold: float, pilot_runner) -> dict:
    entity_id, unresolved = (
        _resolve_gamme_facet(entry) if kind == "gamme" else _resolve_vehicle_facet(entry)
    )
    if entity_id is None:
        return {"state": INPUT_NOT_READY, "reason": unresolved,
                "entity_id": None, "pilot_verdict": None}
    present, not_ready = _input_present(entry, roots["raw_root"])
    if not present:
        return {"state": INPUT_NOT_READY, "reason": f"{not_ready} — pas de tentative de collecte",
                "entity_id": entity_id, "pilot_verdict": None}
    try:
        raw = pilot_runner(entity_id, wiki_root=roots["wiki_root"], raw_root=roots["raw_root"],
                           monorepo_root=roots["monorepo_root"], baseline_ref=baseline_ref,
                           threshold=threshold)
    except Exception as exc:  # un pilote KO devient un état, jamais un crash batch
        return {"state": FACET_INVALID, "reason": f"pilote en erreur: {exc}",
                "entity_id": entity_id, "pilot_verdict": None}
    return {"state": RESOLVED_PILOT_RAN, "reason": "pilote report-only exécuté (dry-run)",
            "entity_id": entity_id, "pilot_verdict": _project_verdict(raw)}


def _assess_couple(entry: dict, roots: dict, baseline_ref: str, threshold: float,
                   pilot_runner) -> dict:
    gamme = _assess_facet("gamme", entry, roots, baseline_ref, threshold, pilot_runner)
    vehicle = _assess_facet("vehicle", entry, roots, baseline_ref, threshold, pilot_runner)
    veh = entry.get("vehicle") or {}
    # ⚠️ Aucune clé de verdict/score couple-level : on présente les 2 états de facette, point.
    return {
        "worklist_id": entry.get("id"),
        "priority": entry.get("priority"),
        "target_consumer": entry.get("target_consumer"),
        "gamme_slug": entry.get("gamme"),
        "vehicle_descriptor": {k: veh.get(k) for k in ("brand", "model", "motorisation")},
        "facets": {"gamme": gamme, "vehicle": vehicle},
    }


def _git_head(root: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "UNKNOWN"
    except Exception:  # inaccessible ⇒ UNKNOWN, jamais crash ni faux SHA
        return "UNKNOWN"


def run_batch(raw_root, wiki_root, monorepo_root, baseline_ref: str = "origin/main",
              threshold: float = 0.80, pilot_runner=None) -> dict:
    roots = {"raw_root": Path(raw_root), "wiki_root": Path(wiki_root),
             "monorepo_root": Path(monorepo_root)}
    runner = pilot_runner or _default_pilot_runner
    worklist_path, schema_path = canonical_paths(roots["raw_root"])
    doc = load_worklist(worklist_path, schema_path)
    couples = select_couples(doc)
    rows = [_assess_couple(e, roots, baseline_ref, threshold, runner) for e in couples]

    def _count(state):
        return sum(1 for r in rows for f in r["facets"].values() if f["state"] == state)

    return {
        "kind": "raw_to_wiki_content_loop_batch",
        "scope": "vehicle_gamme_fit worklist backlog dashboard — report-only, no collection",
        "disclaimer": ("Succès = rapport déterministe et traçable. PAS une preuve de boucle "
                       "fermée ni de scraper opérationnel. Autorité finale = humaine."),
        "provenance": {
            "worklist_path": str(worklist_path),
            "worklist_schema_version": doc.get("schema_version"),
            "schema_path": str(schema_path),
            "raw_root": str(roots["raw_root"]), "raw_head": _git_head(roots["raw_root"]),
            "wiki_root": str(roots["wiki_root"]), "wiki_head": _git_head(roots["wiki_root"]),
            "monorepo_root": str(roots["monorepo_root"]),
            "baseline_ref": baseline_ref, "threshold": threshold,
        },
        "counts": {
            "couples": len(rows),
            "facets_input_not_ready": _count(INPUT_NOT_READY),
            "facets_pilot_ran": _count(RESOLVED_PILOT_RAN),
            "facets_invalid": _count(FACET_INVALID),
        },
        "rows": rows,
    }


def _default_pilot_runner(entity_id, *, wiki_root, raw_root, monorepo_root,
                          baseline_ref, threshold):
    """Runner réel : importe le pilote co-localisé et appelle son `run()` INCHANGÉ (report-only,
    promotion/export en dry-run côté pilote). Import différé : jamais chargé si aucune facette
    n'est prête (cas backlog TODO actuel)."""
    import raw_to_wiki_content_loop_pilot as pilot  # co-localisé dans _scripts/
    return pilot.run(entity_id, Path(wiki_root), Path(raw_root), Path(monorepo_root),
                     baseline_ref, threshold)


# ── écriture rapport (fail-closed sous TOUT dépôt pipeline) ───────────────────

def write_report(report: dict, out_path, raw_root, wiki_root) -> None:
    out_path = Path(out_path).resolve()
    for store in (Path(raw_root).resolve(), Path(wiki_root).resolve()):
        if out_path == store or store in out_path.parents:
            raise UnsafeOutputPath(
                f"--out interdit sous un dépôt pipeline (RAW/WIKI): {out_path} ⊂ {store}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Batch report-only worklist backlog (vehicle_gamme_fit). "
                    "Worklist+schéma CANONIQUES dérivés de --raw-root (aucun chemin arbitraire).")
    ap.add_argument("--raw-root", type=Path, default=Path("/opt/automecanik/automecanik-raw"))
    ap.add_argument("--wiki-root", type=Path, default=SCRIPTS_DIR.parent)
    ap.add_argument("--monorepo-root", type=Path, default=Path("/opt/automecanik/app"))
    ap.add_argument("--baseline-ref", default="origin/main")
    ap.add_argument("--threshold", type=float, default=0.80)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    try:
        report = run_batch(args.raw_root, args.wiki_root, args.monorepo_root,
                           args.baseline_ref, args.threshold)
    except WorklistError as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 2

    if args.out is not None:
        try:
            write_report(report, args.out, args.raw_root, args.wiki_root)
        except UnsafeOutputPath as exc:
            print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
            return 2
        print(f"rapport écrit: {args.out}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
