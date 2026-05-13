#!/usr/bin/env python3
"""
risk_gate — Wrapper "safety + commercial + pollution" : combine
  gate_pollution + gate_catalog_leak + gate_commercial_promise +
  gate_safety_unsourced + gate_maintenance_advice.
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


def run_risk_gate(target: Path) -> GateResult:
    legacy = load_legacy_gates_module()
    fm, _, body = parse_markdown_file(target)

    violations: list[GateViolation] = []

    # Body-only gates
    violations.extend(violations_from_legacy_strings("pollution", legacy.gate_pollution(body)))
    violations.extend(
        violations_from_legacy_strings("catalog_leak", legacy.gate_catalog_leak(body))
    )
    violations.extend(
        violations_from_legacy_strings(
            "commercial_promise", legacy.gate_commercial_promise(body)
        )
    )

    # Frontmatter + body
    violations.extend(
        violations_from_legacy_strings(
            "safety_unsourced", legacy.gate_safety_unsourced(fm, body)
        )
    )

    # Frontmatter only
    violations.extend(
        violations_from_legacy_strings(
            "maintenance_advice", legacy.gate_maintenance_advice(fm)
        )
    )

    return GateResult(
        gate_name="risk",
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
    result = run_risk_gate(target)
    if output_format == "json":
        click.echo(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        click.echo(f"gate=risk status={result.status} target={result.target_file}")
        for v in result.violations:
            click.echo(f"  - [{v.gate_id}] {v.message}")
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
