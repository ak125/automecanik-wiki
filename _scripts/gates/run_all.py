#!/usr/bin/env python3
"""
run_all — Exécute les 5 wrappers gates sur un target et aggrège les résultats.

Exit code :
  0 — tous les 5 gates PASS
  1 — au moins un gate FAIL

Sortie JSON : tableau de 5 GateResult.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .claim_gate import run_claim_gate
from .confidence_gate import run_confidence_gate
from .contradiction_gate import run_contradiction_gate
from .risk_gate import run_risk_gate
from .source_gate import run_source_gate


GATES = [
    ("source", run_source_gate),
    ("claim", run_claim_gate),
    ("contradiction", run_contradiction_gate),
    ("risk", run_risk_gate),
    ("confidence", run_confidence_gate),
]


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
    results = [fn(target) for _, fn in GATES]
    overall_status = "pass" if all(r.status == "pass" for r in results) else "fail"

    if output_format == "json":
        payload = {
            "target": str(target),
            "overall_status": overall_status,
            "results": [r.model_dump(mode="json") for r in results],
        }
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for r in results:
            click.echo(f"gate={r.gate_name} status={r.status}")
            for v in r.violations:
                click.echo(f"  - [{v.gate_id}] {v.message}")
        click.echo(f"\noverall: {overall_status}")

    sys.exit(0 if overall_status == "pass" else 1)


if __name__ == "__main__":
    main()
