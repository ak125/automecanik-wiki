#!/usr/bin/env python3
"""
claim_gate — Wrapper "schema + structure" : combine
  gate_schema_invalid + gate_slug_collision + gate_path_anti_patterns.
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


def run_claim_gate(target: Path) -> GateResult:
    legacy = load_legacy_gates_module()
    fm, _, _ = parse_markdown_file(target)

    violations: list[GateViolation] = []

    violations.extend(
        violations_from_legacy_strings("schema_invalid", legacy.gate_schema_invalid(fm))
    )

    # gate_path_anti_patterns operates on Path
    violations.extend(
        violations_from_legacy_strings("path_anti_patterns", legacy.gate_path_anti_patterns(target))
    )

    # gate_slug_collision requires entity-registry.json
    try:
        registry = legacy.load_registry()
        violations.extend(
            violations_from_legacy_strings(
                "slug_collision", legacy.gate_slug_collision(fm, registry, target)
            )
        )
    except Exception as exc:
        violations.append(
            GateViolation(
                gate_id="entity_registry_load_failed",
                message=f"could not load entity-registry.json: {exc}",
            )
        )

    return GateResult(
        gate_name="claim",
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
    result = run_claim_gate(target)
    if output_format == "json":
        click.echo(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        click.echo(f"gate=claim status={result.status} target={result.target_file}")
        for v in result.violations:
            click.echo(f"  - [{v.gate_id}] {v.message}")
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
