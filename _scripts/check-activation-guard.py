#!/usr/bin/env python3
"""check-activation-guard — guard d'activation SAME-REPO, RAW-INDÉPENDANT.

L'état dangereux n'est pas « un commit existe » — c'est précisément qu'une source de
`_meta/source-catalog.yaml` passe à `active`. Une transition `to_capture → active` (ou une
nouvelle entrée `active`) crée une PREUVE active dont la validité exige le gate cross-repo
(`quality-gates.py --cross-repo`, les 2 repos wiki+raw présents et frais) — ce que la CI wiki
seule NE PEUT PAS vérifier (aucun credential cross-repo secretless entre 2 repos privés).

Le seul chemin autorisé pour activer est le flux GOUVERNÉ d'activation qui exécute `--cross-repo`
AVANT la mutation. Ce guard fail-closed empêche le contournement de ce chemin par ÉDITION
DIRECTE. Il ne nécessite AUCUN accès au repo RAW : il compare seulement l'état du catalog wiki
entre une base git et le head.

Usage :
  check-activation-guard.py --base origin/main   # CI wiki (fetch-depth: 0)
  check-activation-guard.py --base HEAD          # pre-commit (HEAD vs working tree)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_REL = "_meta/source-catalog.yaml"
CATALOG = REPO_ROOT / CATALOG_REL


def _status(entry: dict) -> str:
    # défaut `active` : identique au gate (quality-gates.py:gate_source_catalog_raw_refs),
    # pour qu'une entrée sans `status` explicite ne contourne pas le guard.
    return str(entry.get("status", "active"))


def _entries_by_slug(yaml_text: str) -> dict[str, dict]:
    data = yaml.safe_load(yaml_text) or {}
    sources = data.get("sources", []) if isinstance(data, dict) else []
    return {e["slug"]: e for e in sources if isinstance(e, dict) and "slug" in e}


def find_illicit_activations(base_entries: dict, head_entries: dict) -> list[str]:
    """Activations interdites par édition directe : une entrée `active` côté head qui, côté
    base, était non-`active` (transition) ou absente (nouvelle active). Désactivation,
    suppression, et to_capture inchangé/nouveau = autorisés (pas une création de preuve active)."""
    illicit: list[str] = []
    for slug, head in head_entries.items():
        if _status(head) != "active":
            continue
        base = base_entries.get(slug)
        if base is None:
            illicit.append(f"{slug}: nouvelle entrée `active` créée par édition directe")
        elif _status(base) != "active":
            illicit.append(f"{slug}: transition {_status(base)}→active par édition directe")
    return illicit


def _git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True)


def _load_base_entries(base: str) -> dict[str, dict]:
    # Ref invalide = CI/hook mal configuré → fail-loud (jamais un skip silencieux).
    if _git(["rev-parse", "--verify", "--quiet", base]).returncode != 0:
        print(
            f"FAIL activation-guard: base_ref_introuvable: '{base}' — CI/hook mal configuré "
            "(fetch-depth insuffisant ?). Fail-loud, pas de skip silencieux."
        )
        raise SystemExit(2)
    show = _git(["show", f"{base}:{CATALOG_REL}"])
    if show.returncode != 0:
        return {}  # catalog absent de la base (nouveau fichier) → base vide
    return _entries_by_slug(show.stdout)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--base", required=True,
        help="ref git de comparaison (origin/main en CI, HEAD en pre-commit)",
    )
    args = ap.parse_args()

    head = _entries_by_slug(CATALOG.read_text(encoding="utf-8"))
    base = _load_base_entries(args.base)
    illicit = find_illicit_activations(base, head)

    if illicit:
        print("FAIL activation-guard: activation d'une source interdite par édition directe :")
        for msg in illicit:
            print(f"  - {msg}")
        print(
            "\nUne transition to_capture→active (ou une nouvelle entrée active) crée une PREUVE\n"
            "active dont la validité exige le gate cross-repo (`quality-gates.py --cross-repo`,\n"
            "les 2 repos wiki+raw présents et frais) — non vérifiable par la CI wiki seule.\n"
            "Active UNIQUEMENT via le flux gouverné d'activation (qui exécute --cross-repo AVANT\n"
            "la mutation). Ce guard same-repo ne nécessite aucun accès au repo RAW."
        )
        return 1

    print(f"PASS activation-guard: aucune activation par édition directe (base={args.base}, {len(head)} entrées)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
