#!/usr/bin/env python3
"""
confidence_gate — Wrapper "quality scoring" : compose
  gate_symptom_unstructured.

Garde la place pour gates de scoring additionnels futurs (confidence_overclaimed,
symptom_confidence_score) sans changer le contrat Pydantic.
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


def run_confidence_gate(target: Path) -> GateResult:
    legacy = load_legacy_gates_module()
    fm, _, body = parse_markdown_file(target)

    violations: list[GateViolation] = []

    violations.extend(
        violations_from_legacy_strings(
            "symptom_unstructured", legacy.gate_symptom_unstructured(fm, body)
        )
    )

    return GateResult(
        gate_name="confidence",
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
    result = run_confidence_gate(target)
    if output_format == "json":
        click.echo(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        click.echo(f"gate=confidence status={result.status} target={result.target_file}")
        for v in result.violations:
            click.echo(f"  - [{v.gate_id}] {v.message}")
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
