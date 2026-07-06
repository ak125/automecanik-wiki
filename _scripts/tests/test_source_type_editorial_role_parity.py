"""Loader guard — the source_type → editorial_role policy has ONE machine SoT.

`_meta/source-catalog.yaml › source_type_editorial_role` is the machine source of truth for
whether a source_type may PROVE an editorial claim (`proof`) or only CORROBORATE it
(`corroboration`), mirrored in prose at source-policy.md §9.1. `quality-gates.py` reads it via
`_load_source_type_editorial_role()` (fail-closed); `SOURCE_TYPE_EDITORIAL_ROLE` is the loaded
value, so equality with the catalog is by construction — this test guards the loader.

It also locks the two invariants the loader enforces at import (a broken loader would fail at
import, this makes the intent explicit and regression-visible):
  1. KEY PARITY with `source_type_max_confidence` — every source_type declares BOTH axes
     (max_confidence AND editorial_role); a type present on one map and absent on the other is a
     silent modelling drift, forbidden fail-closed.
  2. ROLE SEMANTICS — `tecdoc_official` is `high` but `corroboration` (TecDoc corroborates, never
     proves; catalogue truth = Massdoc DB). This is the doctrine that replaced the hardcoded
     `_G2_PAUSED_AUTHORITATIVE_TYPES` blocklist with a role-derived authoritative set.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parent
SOURCE_CATALOG = REPO_ROOT / "_meta" / "source-catalog.yaml"
VALID_ROLES = {"proof", "corroboration"}


def _load_quality_gates():
    # filename has a hyphen → load via importlib (same pattern as test_quality_gates.py)
    spec = importlib.util.spec_from_file_location("quality_gates", SCRIPTS_DIR / "quality-gates.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _catalog() -> dict:
    return yaml.safe_load(SOURCE_CATALOG.read_text(encoding="utf-8")) or {}


def _role_map() -> dict:
    return _catalog().get("source_type_editorial_role")


def test_catalog_declares_source_type_editorial_role():
    m = _role_map()
    assert isinstance(m, dict) and m, (
        "_meta/source-catalog.yaml must declare `source_type_editorial_role` (machine SoT, §9.1)"
    )
    assert set(m.values()) <= VALID_ROLES, (
        f"editorial_role values must be a subset of {VALID_ROLES}, got {set(m.values())}"
    )


def test_editorial_role_in_parity_with_quality_gates():
    gate = _load_quality_gates().SOURCE_TYPE_EDITORIAL_ROLE
    assert _role_map() == gate, (
        "DRIFT: _meta/source-catalog.yaml `source_type_editorial_role` (SoT-of-record) != "
        "_scripts/quality-gates.py SOURCE_TYPE_EDITORIAL_ROLE. Keep them identical — edit the "
        "catalog (SoT); the gate reads it directly."
    )


def test_editorial_role_key_parity_with_max_confidence():
    """Every source_type MUST declare BOTH max_confidence AND editorial_role (loader enforces
    this fail-closed at import; asserting it here makes the modelling invariant regression-visible)."""
    cat = _catalog()
    conf = set(cat.get("source_type_max_confidence") or {})
    role = set(cat.get("source_type_editorial_role") or {})
    assert conf == role, (
        "KEY DRIFT between source_type_max_confidence and source_type_editorial_role — "
        f"missing role={sorted(conf - role)}, missing confidence={sorted(role - conf)}. "
        "Every source_type must declare BOTH axes."
    )


def test_editorial_roles_match_owner_doctrine():
    """Doctrine lock (owner 2026-07-06): ONLY primary OE/normative sources may PROVE editorial
    content; every other type corroborates. This is what replaced the hardcoded
    `_G2_PAUSED_AUTHORITATIVE_TYPES` blocklist with role-derived admissibility.

    - `proof`         = {oem_manual, oem_workshop, normative_standard}.
    - `tecdoc_official` = corroboration (reliable in its domain, but catalogue truth = Massdoc DB).
    - `parts_feed_certified` = corroboration (owner decision 2026-07-06): a certified supplier
      feed is CATALOGUE data (ref/attribute/compat = Massdoc DB domain), reliable (`high`, can
      corroborate to `1_high` confidence) but NOT primary editorial proof. Evidence: 0 catalog
      instances + `source-policy.md` semantics + already SECONDARY in compute-symptom-confidence.
    Guards the exact `source fiable` ≠ `source autorisée à prouver éditorial` distinction #81 adds."""
    role = _role_map()
    assert {t for t, r in role.items() if r == "proof"} == {
        "oem_manual", "oem_workshop", "normative_standard"}
    assert role.get("tecdoc_official") == "corroboration"
    assert role.get("parts_feed_certified") == "corroboration"


# ---- fail-closed enforcement (exit 2) — lock the loader against future loosening -----------------
# The tests above assert the *catalog* is well-formed; these assert the *loader ENFORCES* it. Without
# them, a future edit weakening `quality-gates.py:181` from sys.exit(2) to warn-and-continue would
# still pass the suite (the parity tests only ever run against the valid committed catalog). We point
# the module's SOURCE_CATALOG at a malformed tmp variant and assert the loader exits 2 (no-silent-
# fallback). Parity is checked against the module-global confidence map (loaded from the real catalog),
# which is exactly the drift the guard must catch.
def _assert_loader_exits_2(catalog: dict, tmp_path: Path) -> str:
    qg = _load_quality_gates()  # loads clean against the real catalog first
    cat = tmp_path / "source-catalog.yaml"
    cat.write_text(yaml.safe_dump(catalog), encoding="utf-8")
    qg.SOURCE_CATALOG = cat
    with pytest.raises(SystemExit) as exc:
        qg._load_source_type_editorial_role()
    assert exc.value.code == 2, f"loader must exit 2 (fail-closed), got {exc.value.code!r}"
    return qg  # noqa: RET504 — returned only so callers can reuse the fresh module if needed


def test_loader_exits_closed_on_missing_role_map(tmp_path, capsys):
    c = _catalog()
    c.pop("source_type_editorial_role")
    _assert_loader_exits_2(c, tmp_path)
    assert "source_type_editorial_role manquant/vide" in capsys.readouterr().err


def test_loader_exits_closed_on_invalid_role_value(tmp_path, capsys):
    c = _catalog()
    c["source_type_editorial_role"]["oem_manual"] = "gospel"
    _assert_loader_exits_2(c, tmp_path)
    assert "rôles invalides" in capsys.readouterr().err


def test_loader_exits_closed_on_key_parity_break_missing_role(tmp_path, capsys):
    c = _catalog()
    c["source_type_editorial_role"].pop("forum")  # declared in confidence map, not in role map
    _assert_loader_exits_2(c, tmp_path)
    assert "parité de clés rompue" in capsys.readouterr().err


def test_loader_exits_closed_on_key_parity_break_extra_role(tmp_path, capsys):
    c = _catalog()
    c["source_type_editorial_role"]["ghost_type"] = "proof"  # role for a type with no confidence
    _assert_loader_exits_2(c, tmp_path)
    assert "parité de clés rompue" in capsys.readouterr().err
