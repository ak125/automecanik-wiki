#!/usr/bin/env python3
"""
contradiction_gate — Wrapper "logical consistency" : combine
  gate_diagnostic_relations + gate_legacy_symptoms_block.

Détecte les incohérences logiques entre diagnostic_relations[] (canon ADR-033)
et les anti-patterns legacy (diagnostic.symptoms[] interdit).
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


def run_contradiction_gate(target: Path) -> GateResult:
    legacy = load_legacy_gates_module()
    fm, fm_yaml, _ = parse_markdown_file(target)

    violations: list[GateViolation] = []

    # gate_legacy_symptoms_block operates on raw fm_yaml (textual)
    violations.extend(
        violations_from_legacy_strings(
            "legacy_symptoms_block", legacy.gate_legacy_symptoms_block(fm_yaml)
        )
    )

    # gate_diagnostic_relations requires source_catalog
    try:
        source_catalog = legacy.load_source_catalog()
        violations.extend(
            violations_from_legacy_strings(
                "diagnostic_relations",
                legacy.gate_diagnostic_relations(fm, source_catalog),
            )
        )
    except Exception as exc:
        violations.append(
            GateViolation(
                gate_id="source_catalog_load_failed",
                message=f"could not load source-catalog.yaml: {exc}",
            )
        )

    return GateResult(
        gate_name="contradiction",
        target_file=str(target),
        status=status_from_violations(violations),
        violations=violations,
    )


@click.command()
@click.option(
    "--target",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def main(target: Path, output_format: str) -> None:
    result = run_contradiction_gate(target)
    if output_format == "json":
        click.echo(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        click.echo(f"gate=contradiction status={result.status} target={result.target_file}")
        for v in result.violations:
            click.echo(f"  - [{v.gate_id}] {v.message}")
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
