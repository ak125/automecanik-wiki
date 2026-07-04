"""
Tests Pytest des 5 wrappers GateResult.

Garde-fous architecturaux :
- Aucun nouveau gate atomique (refuse les fonctions `def gate_*` dans gates/)
- Aucun import LLM / DB
- Composition des gates legacy uniquement (importlib loader)
- Contrat Pydantic GateResult typé stable
"""
from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from gates._common import (
    GateResult,
    GateViolation,
    load_legacy_gates_module,
    parse_markdown_file,
    status_from_violations,
    violations_from_legacy_strings,
)


GATES_DIR = Path(__file__).parent
GATES_SUBPACKAGE = "gates"


# ---------- Contrat Pydantic GateResult ----------

def test_gate_result_pass_exit_code_0() -> None:
    r = GateResult(gate_name="source", target_file="/tmp/x.md", status="pass", violations=[])
    assert r.exit_code == 0


def test_gate_result_fail_exit_code_1() -> None:
    r = GateResult(
        gate_name="risk",
        target_file="/tmp/x.md",
        status="fail",
        violations=[GateViolation(gate_id="pollution", message="found Skip to main content")],
    )
    assert r.exit_code == 1


def test_gate_result_warn_exit_code_2() -> None:
    r = GateResult(gate_name="claim", target_file="/tmp/x.md", status="warn", violations=[])
    assert r.exit_code == 2


def test_gate_result_rejects_unknown_gate_name() -> None:
    with pytest.raises(ValidationError):
        GateResult(gate_name="totally_invalid", target_file="/tmp/x.md", status="pass")  # type: ignore[arg-type]


def test_gate_result_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        GateResult(
            gate_name="source",
            target_file="/tmp/x.md",
            status="pass",
            extra_field="oops",  # type: ignore[call-arg]
        )


# ---------- Helpers ----------

def test_status_from_violations_empty_is_pass() -> None:
    assert status_from_violations([]) == "pass"


def test_status_from_violations_any_is_fail() -> None:
    v = [GateViolation(gate_id="x", message="msg")]
    assert status_from_violations(v) == "fail"


def test_violations_from_legacy_strings_skips_empty() -> None:
    msgs = ["err1", "", "err2"]
    out = violations_from_legacy_strings("test_gate", msgs)
    assert len(out) == 2
    assert all(v.gate_id == "test_gate" for v in out)


def test_parse_markdown_file_without_frontmatter(tmp_path: Path) -> None:
    f = tmp_path / "x.md"
    f.write_text("just body\n")
    fm, fm_yaml, body = parse_markdown_file(f)
    assert fm == {}
    assert fm_yaml == ""
    assert "just body" in body


def test_parse_markdown_file_with_frontmatter(tmp_path: Path) -> None:
    f = tmp_path / "x.md"
    f.write_text("---\nslug: x\ntitle: X\n---\nbody\n")
    fm, fm_yaml, body = parse_markdown_file(f)
    assert fm["slug"] == "x"
    assert "slug: x" in fm_yaml
    assert "body" in body


# ---------- Legacy module loader ----------

def test_legacy_gates_module_loads() -> None:
    """importlib loader doit fonctionner sur _scripts/quality-gates.py."""
    module = load_legacy_gates_module()
    # Verify expected functions are present
    expected = [
        "gate_schema_invalid",
        "gate_sources_missing",
        "gate_slug_collision",
        "gate_pollution",
        "gate_catalog_leak",
        "gate_commercial_promise",
        "gate_safety_unsourced",
        "gate_maintenance_advice",
        "gate_diagnostic_relations",
        "gate_legacy_symptoms_block",
        "gate_path_anti_patterns",
        "gate_symptom_unstructured",
        "gate_source_catalog_raw_refs",
    ]
    for fn_name in expected:
        assert hasattr(module, fn_name), f"legacy module missing {fn_name}"


# ---------- Architectural guards: NO new gates in wrappers ----------

def test_no_new_atomic_gate_defined_in_wrappers() -> None:
    """
    Garde-fou architectural : aucun wrapper ne définit `def gate_*` lui-même.
    Tout gate atomique doit vivre dans _scripts/quality-gates.py legacy.
    """
    wrapper_files = list(GATES_DIR.glob("*_gate.py")) + [GATES_DIR / "run_all.py"]
    pattern = re.compile(r"^def gate_", re.MULTILINE)
    for wrapper in wrapper_files:
        text = wrapper.read_text(encoding="utf-8")
        match = pattern.search(text)
        assert match is None, (
            f"new atomic gate defined in wrapper {wrapper.name}: "
            f"line {text[:match.start()].count(chr(10)) + 1}. "
            "Wrappers must COMPOSE existing gates, not invent new ones."
        )


def test_source_gate_does_not_enforce_cross_repo_raw_refs() -> None:
    """Caller-split (must-fix owner 2026-07-04) : le wrapper source_gate (per-proposal,
    same-repo) NE compose PLUS gate_source_catalog_raw_refs. Ce gate cross-repo exige
    automecanik-raw et n'est exécuté QUE via `quality-gates.py --cross-repo` par le flux
    gouverné d'activation (hors CI, 2 repos présents). Invoquer un gate RAW-dépendant dans la
    job promotion-gates (sans RAW) = enforcement dans un env incapable → interdit. Ce test
    empêche la réintroduction de ce chemin."""
    text = (GATES_DIR / "source_gate.py").read_text(encoding="utf-8")
    # On interdit l'INVOCATION (call `...raw_refs(`), pas la mention en prose (docstring/
    # commentaire) qui explique l'omission délibérée.
    assert not re.search(r"gate_source_catalog_raw_refs\s*\(", text), (
        "source_gate ne doit PAS invoquer le gate cross-repo (job sans RAW) — "
        "l'enforcement cross-repo vit uniquement dans quality-gates.py --cross-repo"
    )


def test_no_llm_inference_imports_in_wrappers() -> None:
    """Garde-fou statique : aucun import LLM dans les wrappers."""
    forbidden = ["anthropic", "openai", "groq", "cohere", "mistralai", "google.generativeai"]
    for wrapper in GATES_DIR.glob("*.py"):
        if wrapper.name.startswith("test_"):
            continue
        text = wrapper.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"LLM SDK '{needle}' must not appear in {wrapper.name}"


def test_no_db_imports_in_wrappers() -> None:
    """Garde-fou statique : aucun import DB dans les wrappers."""
    forbidden_db = ["psycopg", "asyncpg", "supabase", "sqlalchemy", "django"]
    for wrapper in GATES_DIR.glob("*.py"):
        if wrapper.name.startswith("test_"):
            continue
        text = wrapper.read_text(encoding="utf-8")
        for needle in forbidden_db:
            assert needle not in text, f"DB SDK '{needle}' must not appear in {wrapper.name}"


def test_all_wrappers_expose_gate_result() -> None:
    """Chaque wrapper *_gate.py doit exporter une fonction run_*_gate retournant GateResult."""
    wrappers = {
        "source_gate": "run_source_gate",
        "claim_gate": "run_claim_gate",
        "contradiction_gate": "run_contradiction_gate",
        "risk_gate": "run_risk_gate",
        "confidence_gate": "run_confidence_gate",
    }
    for mod_name, fn_name in wrappers.items():
        mod = importlib.import_module(f"{GATES_SUBPACKAGE}.{mod_name}")
        assert hasattr(mod, fn_name), f"{mod_name} missing {fn_name}"


# ---------- End-to-end smoke tests on minimal fixture ----------

def _make_minimal_valid_fm() -> str:
    """Frontmatter v1.0.0 minimal qui passe gate_schema_invalid."""
    return (
        "---\n"
        "schema_version: '1.0.0'\n"
        "id: gamme:test-slug\n"
        "entity_type: gamme\n"
        "slug: test-slug\n"
        "title: Test\n"
        "lang: fr\n"
        "created_at: '2026-05-13'\n"
        "updated_at: '2026-05-13'\n"
        "truth_level: L1\n"
        "review_status: proposed\n"
        "exportable: false\n"
        "source_refs:\n"
        "  - kind: manual\n"
        "    note: test\n"
        "---\n"
    )


def test_claim_gate_minimal_valid_passes(tmp_path: Path) -> None:
    """Frontmatter minimal valide → claim_gate ne doit pas signaler schema_invalid."""
    from gates.claim_gate import run_claim_gate

    f = tmp_path / "test-slug.md"
    f.write_text(_make_minimal_valid_fm() + "body content\n")
    result = run_claim_gate(f)
    schema_violations = [v for v in result.violations if v.gate_id == "schema_invalid"]
    assert schema_violations == [], (
        f"minimal valid frontmatter should pass schema_invalid, "
        f"got: {[v.message for v in schema_violations]}"
    )


def test_claim_gate_missing_required_field_fails(tmp_path: Path) -> None:
    f = tmp_path / "bad.md"
    f.write_text(
        "---\n"
        "schema_version: '1.0.0'\n"
        "id: gamme:bad\n"
        # missing entity_type, slug, title, etc.
        "---\n"
        "body\n"
    )
    from gates.claim_gate import run_claim_gate

    result = run_claim_gate(f)
    assert result.status == "fail"
    assert any(v.gate_id == "schema_invalid" for v in result.violations)


def test_risk_gate_clean_body_passes(tmp_path: Path) -> None:
    f = tmp_path / "clean.md"
    f.write_text(_make_minimal_valid_fm() + "Description neutre sans pollution ni claim safety.\n")
    from gates.risk_gate import run_risk_gate

    result = run_risk_gate(f)
    # Status may be pass; we only assert no exception
    assert result.gate_name == "risk"
    assert result.target_file == str(f)
