#!/usr/bin/env python3
"""check-activation-guard — guard d'activation SAME-REPO, RAW-INDÉPENDANT.

L'état dangereux n'est pas « un commit existe » — c'est précisément qu'une source de
`_meta/source-catalog.yaml` passe à `active`. Une transition `to_capture → active` (ou une
nouvelle entrée `active`) crée une PREUVE active dont la validité exige le gate cross-repo
(`quality-gates.py --cross-repo`, les 2 repos wiki+raw présents et frais) — ce que la CI wiki
seule NE PEUT PAS vérifier (aucun credential cross-repo secretless vers le repo RAW, privé).

Le seul chemin autorisé pour activer est le flux GOUVERNÉ d'activation qui exécute `--cross-repo`
AVANT la mutation. Ce guard fail-closed empêche le contournement de ce chemin par ÉDITION
DIRECTE sans reçu signé. Le reçu lie les octets contrôlés et les transitions exactes,
avec une clé de confiance déjà présente dans la base Git. Aucun accès RAW en CI.
Le garde compare l'état du catalog wiki
entre une base git et le head.

Ré-épingler une source déjà `active` (`raw_ref` changé) est une activation (ADR-116 D4 d) : la
nouvelle archive devient la preuve, et les ancres des fiches qui la citent doivent être
revérifiées par `--cross-repo` avant la mutation, sinon une ancre casserait en silence.

Requalifier une source déjà `active` (`type` ou `publisher` changé) est aussi une activation : le
`type` donne le rôle (`proof` ou `corroboration`) et le plafond de confiance, le `publisher`
l'éditeur compté pour l'indépendance des preuves (ADR-114 D3, ADR-116 D2). Le reçu signé portait
l'ancienne ligne ; sans ce contrôle, une brochure deviendrait une preuve, ou un éditeur scindé
compterait deux fois, sans signature. Chemin gouverné : repasser la source en `to_capture`
(libre), puis l'activer par le flux gouverné. Les champs d'autorité (`AUTHORITY_FIELDS`) et leur
comparaison (`requalified_fields`) sont ceux du reçu : une seule définition de l'activation.

Usage :
  check-activation-guard.py --base origin/main   # CI wiki, pull_request (fetch-depth: 0)
  check-activation-guard.py --base <before-sha>  # CI wiki, push main (github.event.before)
  check-activation-guard.py --base HEAD          # pre-commit (HEAD vs working tree)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from activation_receipt import requalified_fields, verify_activation  # noqa: E402

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
    base, était non-`active` (transition), absente (nouvelle active), ou `active` avec un champ
    d'autorité posé ou changé (`raw_ref` : ré-épingle, ADR-116 D4 d ; `type`, `publisher` :
    requalification). Désactivation, suppression, retrait d'un champ d'autorité, et
    to_capture inchangé/nouveau = autorisés (pas une création de preuve active)."""
    illicit: list[str] = []
    for slug, head in head_entries.items():
        if _status(head) != "active":
            continue
        base = base_entries.get(slug)
        if base is None:
            illicit.append(f"{slug}: nouvelle entrée `active` créée par édition directe")
        elif _status(base) != "active":
            illicit.append(f"{slug}: transition {_status(base)}→active par édition directe")
        elif changed := requalified_fields(base, head):
            illicit.append(f"{slug}: {', '.join(changed)} d'une entrée déjà `active` changé par "
                           "édition directe (ré-épingle ou requalification = activation, "
                           "ADR-116 D4 d, ADR-114 D3)")
    return illicit


def _git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True)


def _load_base_entries(base: str) -> dict[str, dict]:
    # Ref invalide = CI/hook mal configuré → fail-loud (jamais un skip silencieux).
    # `^{commit}` : sans lui, `rev-parse --verify` accepte tout SHA complet bien formé
    # (y compris le SHA nul d'un push) sans vérifier que l'objet existe.
    if _git(["rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"]).returncode != 0:
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
        # A receipt is trusted only with a key already present in the Git base.
        # No RAW credential or caller-supplied PASS is accepted in this guard.
        try:
            slugs = verify_activation(REPO_ROOT, args.base)
            print(f"PASS activation-guard: reçu signé vérifié pour {len(slugs)} activation(s), base={args.base}")
            return 0
        except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
            print(f"Activation receipt rejected: {error}")
        print("FAIL activation-guard: activation d'une source interdite par édition directe :")
        for msg in illicit:
            print(f"  - {msg}")
        print(
            "\nUne transition to_capture→active (ou une nouvelle entrée active, ou un raw_ref,\n"
            "un type ou un publisher changé sur une entrée active) crée une PREUVE\n"
            "active dont la validité exige le gate cross-repo (`quality-gates.py --cross-repo`,\n"
            "les 2 repos wiki+raw présents et frais) — non vérifiable par la CI wiki seule.\n"
            "Active UNIQUEMENT via le flux gouverné d'activation (qui exécute --cross-repo AVANT\n"
            "la mutation) ; pour requalifier, repasser d'abord la source en to_capture.\n"
            "Ce guard same-repo ne nécessite aucun accès au repo RAW."
        )
        return 1

    print(f"PASS activation-guard: aucune activation par édition directe (base={args.base}, {len(head)} entrées)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
