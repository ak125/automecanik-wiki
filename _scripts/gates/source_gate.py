#!/usr/bin/env python3
"""
source_gate — Wrapper "source provenance" : combine
  gate_source_catalog_raw_refs + gate_sources_missing.

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

    # gate_sources_missing (no external resource needed)
    violations.extend(
        violations_from_legacy_strings("sources_missing", legacy.gate_sources_missing(fm))
    )

    # gate_source_catalog_raw_refs requires loading source_catalog
    try:
        source_catalog = legacy.load_source_catalog()
        # gate_source_catalog_raw_refs returns tuple(errors, warnings) — both treated as violations
        errs, warns = legacy.gate_source_catalog_raw_refs(source_catalog)
        violations.extend(violations_from_legacy_strings("source_catalog_raw_refs", errs))
        violations.extend(violations_from_legacy_strings("source_catalog_raw_refs_warn", warns))
    except Exception as exc:
        violations.append(
            GateViolation(
                gate_id="source_catalog_load_failed",
                message=f"could not load source-catalog.yaml: {exc}",
            )
        )

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
