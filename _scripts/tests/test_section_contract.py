"""Structural evidence: exact aliases, real Markdown blocks and no double count."""
import importlib.util
from pathlib import Path

import pytest

import author_from_raw
import editorial_sections as contract
import promotion_decision

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("section_scorer", ROOT / "_scripts/compute-confidence-score.py")
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)
PROSE = "Le thermostat participe à la régulation du circuit de refroidissement."


def score(body, entity_type="gamme"):
    return SCORER.explain_score({"entity_type": entity_type}, body, ROOT / "wiki")["components"]["sections"]


@pytest.mark.parametrize("heading, criterion", [
    ("Rôle technique", "Fonctionnement"),
    ("Fonction", "Fonctionnement"),
    ("Symptômes & diagnostic", "Symptômes d'usure"),
    ("Symptômes système auxquels cette pièce peut contribuer", "Symptômes d'usure"),
    ("Critères de choix selon le véhicule", "Choix selon véhicule"),
    ("FAQ", "FAQ"),
])
def test_controlled_heading_has_one_owner(heading, criterion):
    result = score(f"## {heading}\n\n{PROSE}")
    assert result["filled"] == [criterion]
    assert result["matched_headings"][criterion] == [heading]
    assert result["contribution"] == 0.06


def test_no_definition_credit_or_optional_role_bonus():
    body = "\n".join(f"{h}\n\n{PROSE}\n" for h, _ in contract.SECTION_SPEC.values())
    result = score(body)
    assert set(result["filled"]) == {"Fonctionnement", "Symptômes d'usure", "Choix selon véhicule", "FAQ"}
    assert result["missing_or_insufficient"] == ["Définition"]
    assert result["contribution"] == 0.24


def test_alias_and_old_title_cannot_double_count():
    body = f"## Rôle technique\n{PROSE}\n## Fonctionnement\n{PROSE}"
    result = score(body)
    assert result["filled"] == ["Fonctionnement"]
    assert result["contribution"] == 0.06


@pytest.mark.parametrize("body", [
    "<!--\n## Fonctionnement\n" + PROSE + "\n-->",
    "```markdown\n## Fonctionnement\n" + PROSE + "\n```",
    "~~~\n## Fonctionnement\n" + PROSE + "\n~~~",
    "    ## Fonctionnement\n    " + PROSE,
    "> ## Fonctionnement\n> " + PROSE,
    "## Fonctionnement\n\n<!-- " + PROSE + " -->",
    "## Fonctionnement\n\n```\n" + PROSE + "\n```",
    "## Fonctionnement\n\n    " + PROSE,
    "## Fonctionnement\n\n### " + PROSE,
    "## Fonctionnement\n\n![image alternative assez longue pour gonfler le score](image.png)",
    "## Fonctionnement\n\n<div hidden>" + PROSE + "</div>",
    "## Fonctionnement\n\nTexte <span hidden>" + PROSE + "</span>",
    "## Fonctionnement\n\n# Autre document\n\n" + PROSE,
    "## Fonctionnement détaillé qui ne figure pas au contrat\n\n" + PROSE,
    "## <span hidden>Fonctionnement</span>\n\n" + PROSE,
    "## Fonctionnement\nCourt.",
])
def test_markup_or_unsupported_heading_does_not_fill_section(body):
    assert "Fonctionnement" not in score(body)["filled"]


@pytest.mark.parametrize("body", [
    "## FONCTIONNEMENT ##\n\n" + PROSE,
    "## **Fonctionnement**\n\n" + PROSE,
    "Fonctionnement\n--------------\n\n" + PROSE,
    "## Fonctionnement\n\n### Principe\n\n" + PROSE,
    "## Fonctionnement\n\n- " + PROSE,
    "## Fonctionnement\n\n> " + PROSE,
])
def test_supported_markdown_prose_is_counted(body):
    assert score(body)["filled"] == ["Fonctionnement"]


def test_unicode_apostrophe_and_normalization():
    assert score("## Symptômes d’usure\n\n" + PROSE)["filled"] == ["Symptômes d'usure"]
    assert score("## Ro\u0302le technique\n\n" + PROSE)["filled"] == ["Fonctionnement"]


def test_unknown_alias_does_not_match_by_substring():
    assert score("## Rôle technique supplémentaire\n\n" + PROSE)["filled"] == []


def test_aliases_are_gamme_only():
    assert score("## Rôle technique\n\n" + PROSE, "vehicle")["filled"] == []


def test_contract_is_shared_with_author():
    assert author_from_raw.SECTION_SPEC is contract.SECTION_SPEC


def test_alias_collision_is_refused():
    with pytest.raises(ValueError, match="score_section_alias_collision"):
        SCORER.section_evidence("", ["Définition", "Fonctionnement"],
                                {"Définition": ("Rôle technique",),
                                 "Fonctionnement": ("Rôle technique",)})


def test_parser_version_drift_is_refused(monkeypatch):
    monkeypatch.setattr(SCORER, "version", lambda _: "unsupported")
    with pytest.raises(ValueError, match="score_parser_version_unsupported"):
        score("## Fonctionnement\n" + PROSE)


@pytest.mark.parametrize("filename", ["editorial_sections.py", "requirements-scoring.txt"])
def test_contract_or_dependency_change_invalidates_decision(tmp_path, monkeypatch, filename):
    scripts = tmp_path / "_scripts"
    scripts.mkdir()
    for name in promotion_decision._EVALUATION_ENGINE_FILES:
        (scripts / name).write_bytes((ROOT / "_scripts" / name).read_bytes())
    candidate = tmp_path / "candidate.md"
    candidate.write_text("---\nslug: sample\n---\n")
    monkeypatch.setattr(promotion_decision, "SCRIPTS_DIR", scripts)
    inputs = promotion_decision.capture_input_manifest(candidate, tmp_path, None, None)
    assert promotion_decision.reverify_inputs({"inputs": inputs}, candidate, tmp_path) is None
    with (scripts / filename).open("a") as output:
        output.write("\n# Changed after evaluation\n")
    result = promotion_decision.reverify_inputs({"inputs": inputs}, candidate, tmp_path)
    assert result["code"] == "STALE_DECISION"
    assert "evaluation_engine_revision" in result["evidence"]
