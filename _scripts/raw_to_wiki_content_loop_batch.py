#!/usr/bin/env python3
"""raw_to_wiki_content_loop_batch — TABLEAU DE BORD BACKLOG déterministe (REPORT-ONLY).

Thin wrapper batch au-dessus de `raw_to_wiki_content_loop_pilot` (Option A, cadrage owner
2026-07-15 : `audit/cadrage-batch-report-only-raw-to-wiki-loop-2026-07-15.md` au monorepo).

Périmètre STRICT (GO owner d'implémentation 2026-07-15) :
  • INPUT = UNIQUEMENT les entrées `subject_type: vehicle_gamme_fit` de la worklist RAW gouvernée
    (`manifests/ingestion-worklist.yaml`), VALIDÉES par `_schemas/ingestion-worklist.schema.json`.
    Aucun couple libre en CLI, aucune découverte, aucune invention (kw/URL/slug/page/entité).
  • Par couple : appelle le pilote SÉPARÉMENT pour la facette `gamme` et la facette `vehicle`,
    puis AGRÈGE UNIQUEMENT leur état. AUCUN modèle ni verdict `vehicle_gamme_fit` n'est créé
    (0 score couple-level).
  • Entrée non collectée (`capture.status` hors état capturé) OU facette non résoluble en
    `type:slug` explicite  ⇒  INPUT_NOT_READY, SANS invoquer le pilote, SANS tentative de collecte.
  • Fail-closed : worklist/schéma invalide ou absent  ⇒  exit != 0, AUCUN rapport partiel.
  • 0 écriture RAW/WIKI/DB/worklist ; 0 promotion auto ; 0 RAG. Autorité finale = HUMAINE.
  • Déterministe & traçable : tri stable, provenance (refs git) par run, aucun horodatage dans le
    corps. Reproductible : mêmes entrées ⇒ même rapport.

⚠️ Succès de ce batch = « rapport déterministe et traçable », JAMAIS « boucle fermée » ni
   « scraper opérationnel » (anti-overclaim, cf. audit smart-scraper 2026-07-15).

Usage :
  python3 raw_to_wiki_content_loop_batch.py \
      --worklist <ingestion-worklist.yaml> [--schema <schema.json>] \
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
# États `capture.status` où un artefact RAW EXISTE (le pilote a de quoi RAPPORTER).
# TODO / REJECTED ⇒ rien de collecté ⇒ INPUT_NOT_READY (sans tentative de collecte).
CAPTURED_STATES = {"CAPTURED", "CAPTURED_NEEDS_REVIEW", "GATED", "PROMOTED"}

# États de facette (batch-level ; ne RECRÉENT aucun verdict qualité — ils gouvernent l'INPUT).
INPUT_NOT_READY = "INPUT_NOT_READY"
RESOLVED_PILOT_RAN = "RESOLVED_PILOT_RAN"
FACET_INVALID = "INVALID"


class WorklistError(Exception):
    """Worklist ou schéma invalide/absent — fail-closed (jamais de skip silencieux)."""


class UnsafeOutputPath(Exception):
    """Chemin `--out` à l'intérieur d'un store RAW/WIKI — refusé (0 écriture pipeline)."""


# ── chargement + validation schéma (fail-closed) ─────────────────────────────

def load_worklist(worklist_path: Path, schema_path: Path) -> dict:
    worklist_path = Path(worklist_path)
    schema_path = Path(schema_path)
    if not worklist_path.is_file():
        raise WorklistError(f"worklist absente: {worklist_path}")
    if not schema_path.is_file():
        # Schéma absent ⇒ on NE valide pas ⇒ fail-closed (no silent fallback).
        raise WorklistError(f"schéma absent, validation impossible (fail-closed): {schema_path}")
    try:
        import yaml
        doc = yaml.safe_load(worklist_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise WorklistError(f"worklist illisible (YAML): {exc}") from exc
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise WorklistError(f"schéma illisible (JSON): {exc}") from exc
    try:
        import jsonschema
        jsonschema.validate(instance=doc, schema=schema)
    except Exception as exc:  # noqa: BLE001 — ValidationError ou SchemaError → fail-closed
        raise WorklistError(f"worklist non conforme au schéma (fail-closed): {exc}") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("worklist"), list):
        raise WorklistError("worklist: structure inattendue après validation")
    return doc


def select_couples(doc: dict) -> list[dict]:
    """Entrées vehicle_gamme_fit uniquement, triées par id (déterminisme). Rien d'autre."""
    couples = [e for e in doc["worklist"] if e.get("subject_type") == SUBJECT_TYPE]
    return sorted(couples, key=lambda e: str(e.get("id", "")))


# ── résolution de facette (0 invention) ──────────────────────────────────────

def _resolve_gamme_facet(entry: dict):
    """gamme facette → 'gamme:<slug>' si un slug gamme EXPLICITE existe dans l'entrée."""
    slug = entry.get("gamme")
    if isinstance(slug, str) and slug.strip():
        return f"gamme:{slug.strip()}", None
    return None, "aucun slug gamme explicite dans l'entrée worklist"


def _resolve_vehicle_facet(entry: dict):
    """vehicle facette : la worklist ne porte PAS de slug véhicule explicite (schéma =
    brand/model/motorisation/engine_family_key). Sans slug explicite, résolution IMPOSSIBLE —
    on n'invente aucun slug (fail-closed). Retour: (None, raison)."""
    veh = entry.get("vehicle") or {}
    if isinstance(veh, dict) and isinstance(veh.get("slug"), str) and veh["slug"].strip():
        # Chemin d'extension futur (si le contrat worklist ajoute un slug véhicule explicite,
        # décision owner/vault) — non présent aujourd'hui.
        return f"vehicle:{veh['slug'].strip()}", None
    return None, ("l'entrée worklist ne porte pas de slug véhicule explicite "
                  "(schéma = brand/model/motorisation) — fail-closed, aucune synthèse de slug")


def _input_present(entry: dict) -> bool:
    """Un artefact RAW existe-t-il pour ce couple ? (status capturé + raw_path présent)."""
    cap = entry.get("capture") or {}
    return cap.get("status") in CAPTURED_STATES and bool(cap.get("raw_path"))


def _assess_facet(kind: str, entry: dict, roots: dict, baseline_ref: str,
                  threshold: float, pilot_runner) -> dict:
    entity_id, unresolved_reason = (
        _resolve_gamme_facet(entry) if kind == "gamme" else _resolve_vehicle_facet(entry)
    )
    if entity_id is None:
        return {"state": INPUT_NOT_READY, "reason": unresolved_reason,
                "entity_id": None, "pilot_verdict": None}
    if not _input_present(entry):
        status = (entry.get("capture") or {}).get("status")
        return {"state": INPUT_NOT_READY,
                "reason": f"capture.status={status} (aucune capture RAW) — pas de tentative de collecte",
                "entity_id": entity_id, "pilot_verdict": None}
    # Facette résolue + input présent : le pilote (report-only) RAPPORTE. Il n'écrit rien.
    try:
        raw = pilot_runner(entity_id, wiki_root=roots["wiki_root"], raw_root=roots["raw_root"],
                           monorepo_root=roots["monorepo_root"], baseline_ref=baseline_ref,
                           threshold=threshold)
    except Exception as exc:  # noqa: BLE001 — un pilote KO devient un état, jamais un crash batch
        return {"state": FACET_INVALID, "reason": f"pilote en erreur: {exc}",
                "entity_id": entity_id, "pilot_verdict": None}
    return {"state": RESOLVED_PILOT_RAN, "reason": "pilote report-only exécuté (dry-run)",
            "entity_id": entity_id, "pilot_verdict": _project_verdict(raw)}


def _project_verdict(raw) -> dict | None:
    """Projection COMPACTE du rapport pilote — on RELAIE, on ne recalcule aucun score."""
    if not isinstance(raw, dict):
        return None
    return {k: raw.get(k) for k in ("projection_operational", "business_loop_closed",
                                    "remaining_blockers") if k in raw}


# ── assemblage rapport ───────────────────────────────────────────────────────

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
    except Exception:  # noqa: BLE001 — inaccessible ⇒ UNKNOWN, jamais crash ni faux SHA
        return "UNKNOWN"


def run_batch(worklist_path, schema_path, raw_root, wiki_root, monorepo_root,
              baseline_ref: str = "origin/main", threshold: float = 0.80,
              pilot_runner=None) -> dict:
    roots = {"raw_root": Path(raw_root), "wiki_root": Path(wiki_root),
             "monorepo_root": Path(monorepo_root)}
    runner = pilot_runner or _default_pilot_runner
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


# ── écriture rapport (fail-closed hors stores) ───────────────────────────────

def write_report(report: dict, out_path, raw_root, wiki_root) -> None:
    out_path = Path(out_path).resolve()
    forbidden = [Path(raw_root, "sources").resolve(),
                 Path(wiki_root, "proposals").resolve(),
                 Path(wiki_root, "exports").resolve()]
    for store in forbidden:
        if out_path == store or store in out_path.parents:
            raise UnsafeOutputPath(f"--out interdit dans un store pipeline: {out_path} ⊂ {store}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Batch report-only worklist backlog (vehicle_gamme_fit).")
    ap.add_argument("--worklist", type=Path, required=True)
    ap.add_argument("--schema", type=Path, default=None,
                    help="défaut: <raw-root>/_schemas/ingestion-worklist.schema.json")
    ap.add_argument("--raw-root", type=Path, default=Path("/opt/automecanik/automecanik-raw"))
    ap.add_argument("--wiki-root", type=Path, default=SCRIPTS_DIR.parent)
    ap.add_argument("--monorepo-root", type=Path, default=Path("/opt/automecanik/app"))
    ap.add_argument("--baseline-ref", default="origin/main")
    ap.add_argument("--threshold", type=float, default=0.80)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    schema_path = args.schema or (args.raw_root / "_schemas" / "ingestion-worklist.schema.json")
    try:
        report = run_batch(args.worklist, schema_path, args.raw_root, args.wiki_root,
                           args.monorepo_root, args.baseline_ref, args.threshold)
    except WorklistError as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 2

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out is not None:
        try:
            write_report(report, args.out, args.raw_root, args.wiki_root)
        except UnsafeOutputPath as exc:
            print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
            return 2
        print(f"rapport écrit: {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
