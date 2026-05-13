"""
Helpers partagés entre les 5 wrappers de gates.

- Contrat Pydantic GateResult typé strict.
- Loader importlib pour le module legacy `_scripts/quality-gates.py` (filename
  avec tiret → pas importable directement).
- Parser frontmatter YAML d'un fichier .md.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
LEGACY_GATES_PATH = SCRIPTS_DIR / "quality-gates.py"


def load_legacy_gates_module() -> ModuleType:
    """
    Charge `_scripts/quality-gates.py` (filename non-importable directement)
    via importlib.util.spec_from_file_location.

    Le module legacy expose toutes les fonctions `gate_*` réutilisées par
    les wrappers.
    """
    spec = importlib.util.spec_from_file_location(
        "_quality_gates_legacy", LEGACY_GATES_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load legacy gates module: {LEGACY_GATES_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_quality_gates_legacy"] = module
    spec.loader.exec_module(module)
    return module


class GateViolation(BaseModel):
    """Un manquement détecté par un gate atomique."""

    model_config = ConfigDict(extra="forbid")

    gate_id: str = Field(min_length=1, description="Identifiant du gate atomique (ex: 'schema_invalid')")
    message: str = Field(min_length=1)


GateName = Literal["source", "claim", "contradiction", "risk", "confidence"]
GateStatus = Literal["pass", "fail", "warn"]


class GateResult(BaseModel):
    """
    Contrat de retour stable d'un wrapper.

    `exit_code` est dérivé de `status` (pass=0, fail=1, warn=2) pour usage CLI.
    """

    model_config = ConfigDict(extra="forbid")

    gate_name: GateName
    target_file: str
    status: GateStatus
    violations: list[GateViolation] = Field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return {"pass": 0, "fail": 1, "warn": 2}[self.status]


FRONTMATTER_SEPARATOR = "---"


def parse_markdown_file(path: Path) -> tuple[dict, str, str]:
    """
    Lit un fichier markdown avec frontmatter YAML.

    Retourne (frontmatter_dict, frontmatter_yaml_raw, body_md).
    Frontmatter vide → ({}, "", body_complet).
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith(FRONTMATTER_SEPARATOR):
        return {}, "", text
    parts = text.split(f"\n{FRONTMATTER_SEPARATOR}\n", 1)
    if len(parts) != 2:
        return {}, "", text
    fm_yaml = parts[0].lstrip(FRONTMATTER_SEPARATOR).lstrip("\n")
    body = parts[1]
    try:
        fm = yaml.safe_load(fm_yaml) or {}
    except yaml.YAMLError:
        fm = {}
    if not isinstance(fm, dict):
        fm = {}
    return fm, fm_yaml, body


def status_from_violations(violations: list[GateViolation]) -> GateStatus:
    """Pass si vide, fail si au moins une violation."""
    return "pass" if not violations else "fail"


def violations_from_legacy_strings(gate_id: str, msgs: list[str]) -> list[GateViolation]:
    """
    Convertit les messages str retournés par les `gate_*` legacy en
    GateViolation typées. Chaque str = 1 GateViolation avec gate_id partagé.
    """
    return [GateViolation(gate_id=gate_id, message=m) for m in msgs if m]
