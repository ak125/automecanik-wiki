#!/usr/bin/env python3
"""
source_gate — Wrapper "source provenance" per-proposal (SAME-REPO) : gate_sources_missing.

Le gate cross-repo `gate_source_catalog_raw_refs` (catalog-wide, exige un checkout
automecanik-raw) N'EST PAS composé ici : c'est un contrôle catalog-wide qui n'a pas sa
place dans un wrapper per-proposal, et l'invoquer dans la job promotion-gates (sans RAW)
enforcerait un gate dans un environnement incapable. Il est enforcé EXCLUSIVEMENT par
`quality-gates.py --cross-repo` (caller-split, must-fix owner 2026-07-04).

Sortie : GateResult Pydantic typé. CLI exit code = exit_code Pydantic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from ._common import (
    GateResult,
    GateViolation,
    load_legacy_gates_module,
    parse_markdown_file,
    status_from_violations,
    violations_from_legacy_strings,
)


def run_source_gate(target: Path) -> GateResult:
    """Compose les gates source pour un fichier target."""
    legacy = load_legacy_gates_module()
    fm, _, _ = parse_markdown_file(target)

    violations: list[GateViolation] = []

    # gate_sources_missing (per-proposal, same-repo — no external resource needed)
    violations.extend(
        violations_from_legacy_strings("sources_missing", legacy.gate_sources_missing(fm))
    )

    # NB : le gate cross-repo `gate_source_catalog_raw_refs` (catalog-wide, exige automecanik-raw)
    # n'est PAS invoqué ici — il est enforcé exclusivement par `quality-gates.py --cross-repo`
    # (caller-split : ne jamais lancer un gate RAW-dépendant dans la job promotion-gates sans RAW).

    return GateResult(
        gate_name="source",
        target_file=str(target),
        status=status_from_violations(violations),
        violations=violations,
    )


@click.command()
@click.option(
    "--target",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Fichier proposal/wiki .md à valider",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def main(target: Path, output_format: str) -> None:
    """Exécute source_gate sur target et exit avec exit_code typé."""
    result = run_source_gate(target)
    if output_format == "json":
        click.echo(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        click.echo(f"gate=source status={result.status} target={result.target_file}")
        for v in result.violations:
            click.echo(f"  - [{v.gate_id}] {v.message}")
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
