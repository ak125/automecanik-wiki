"""ADR-112 / ADR-113 — amendements d'ADR-033 : contrat du schéma + ancres RAW.

  1. Schéma (`frontmatter.schema.json`, Draft 2020-12, même validateur que la CI) :
     cause_slug, evidence.strength, vehicle_scope, citations[], diagnostic.quick_checks[],
     safety_rules[] (chemin fixé), diagnostic_not_applicable (exclusif des relations).
  2. Parité du vocabulaire carburant avec entity-data/vehicle.schema.json (une seule liste).
  3. `gate_citation_anchors` (cross-repo, à la promotion) contre une archive RAW réelle :
     unité = points de code Unicode, base zéro, fin exclue, texte UTF-8 sans traduction des
     fins de ligne (même convention que document_authoring.py).

Exécution : cd _scripts/tests && python3 -m pytest test_diagnostic_claims_contract.py -v
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SCHEMA_DIR = SCRIPTS_DIR.parent / "_meta" / "schema"

_spec = importlib.util.spec_from_file_location("quality_gates", SCRIPTS_DIR / "quality-gates.py")
qg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qg)

SCHEMA = json.loads((SCHEMA_DIR / "frontmatter.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)

QUOTE_SHA = "sha256:" + "0" * 64
EVIDENCE = {"confidence": "medium", "source_policy": "manual_review", "reviewed": False, "diagnostic_safe": False}

BASE = {
    "schema_version": "2.0.0",
    "id": "gamme:filtre-contrat",
    "entity_type": "gamme",
    "slug": "filtre-contrat",
    "title": "Filtre contrat",
    "lang": "fr",
    "created_at": "2026-10-05",
    "updated_at": "2026-10-05",
    "truth_level": "L4",
    "review_status": "draft",
    "exportable": {"rag": False, "seo": False, "support": False},
}

RELATION = {
    "symptom_slug": "perte_puissance_filtration",
    "system_slug": "filtration",
    "cause_slug": "filtre_colmate",
    "relation_to_part": "possible_cause",
    "part_role": "Un filtre colmaté restreint le débit vers le moteur.",
    "vehicle_scope": {"fuel": "diesel"},
    "evidence": {**EVIDENCE, "strength": "parfois"},
    "sources": ["src_a"],
    "citations": [{"source": "src_a", "start": 0, "end": 10, "quote_sha256": QUOTE_SHA}],
}

QUICK_CHECK = {
    "cause_slug": "filtre_colmate",
    "check": "Contrôler l'état de l'élément filtrant.",
    "evidence": dict(EVIDENCE),
    "sources": ["src_a"],
}

RULE = {
    "rule_slug": "regle_test",
    "system_slug": "filtration",
    "condition": "Situation de test qui déclenche la règle.",
    "evidence": dict(EVIDENCE),
    "sources": ["src_a"],
}

SAFETY_FICHE = {**BASE, "id": "diagnostic:regles-securite", "entity_type": "diagnostic",
                "slug": "regles-securite", "title": "Règles de sécurité"}


def _gamme(**extra) -> dict:
    fm = copy.deepcopy(BASE)
    fm.update(copy.deepcopy(extra))
    return fm


def _errors(fm: dict) -> list[str]:
    return [e.message for e in VALIDATOR.iter_errors(fm)]


# ---------- 1. Schéma ----------

def test_schema_is_a_valid_draft_2020_12_schema():
    Draft202012Validator.check_schema(SCHEMA)


VALID = {
    "relation_with_new_fields": _gamme(diagnostic_relations=[RELATION]),
    "relation_without_new_fields": _gamme(diagnostic_relations=[
        {k: v for k, v in RELATION.items() if k not in {"cause_slug", "vehicle_scope", "citations"}}]),
    "quick_checks": _gamme(diagnostic_relations=[RELATION], diagnostic={"quick_checks": [QUICK_CHECK]}),
    "not_applicable_alone": _gamme(diagnostic_not_applicable={"reason": "Aucun lien avec le vocabulaire.", "reviewed": False}),
    "not_applicable_with_empty_relations": _gamme(
        diagnostic_relations=[], diagnostic_not_applicable={"reason": "Aucun lien avec le vocabulaire.", "reviewed": False}),
    "safety_rules_in_their_fiche": {**copy.deepcopy(SAFETY_FICHE), "safety_rules": [RULE]},
}


@pytest.mark.parametrize("name", sorted(VALID))
def test_schema_accepts(name):
    assert _errors(VALID[name]) == []


def _relation(**override) -> dict:
    r = copy.deepcopy(RELATION)
    r.update(override)
    return r


INVALID = {
    "not_applicable_with_relations": _gamme(
        diagnostic_relations=[RELATION], diagnostic_not_applicable={"reason": "Aucun lien avec le vocabulaire.", "reviewed": False}),
    "not_applicable_without_reviewed": _gamme(diagnostic_not_applicable={"reason": "Aucun lien avec le vocabulaire."}),
    "not_applicable_on_vehicle": {**_gamme(diagnostic_not_applicable={"reason": "Aucun lien avec le vocabulaire.", "reviewed": False}),
                                  "entity_type": "vehicle"},
    "quick_checks_on_diagnostic_fiche": {**copy.deepcopy(SAFETY_FICHE), "diagnostic": {"quick_checks": [QUICK_CHECK]}},
    "legacy_diagnostic_symptoms_block": _gamme(diagnostic={"symptoms": ["bruit"]}),
    "diagnostic_causes_block": _gamme(diagnostic={"quick_checks": [QUICK_CHECK], "causes": ["x"]}),
    "quick_check_without_cause": _gamme(diagnostic={"quick_checks": [{k: v for k, v in QUICK_CHECK.items() if k != "cause_slug"}]}),
    "strength_on_quick_check_evidence": _gamme(diagnostic={"quick_checks": [{**QUICK_CHECK, "evidence": {**EVIDENCE, "strength": "souvent"}}]}),
    "computed_score_on_rule_evidence": {**copy.deepcopy(SAFETY_FICHE),
                                        "safety_rules": [{**RULE, "evidence": {**EVIDENCE, "confidence_score_computed": 0.5}}]},
    "safety_rules_on_gamme": _gamme(safety_rules=[RULE]),
    "safety_rules_other_slug": {**copy.deepcopy(SAFETY_FICHE), "id": "diagnostic:autre", "slug": "autre", "safety_rules": [RULE]},
    "strength_numeric": _gamme(diagnostic_relations=[_relation(evidence={**EVIDENCE, "strength": 0.6})]),
    "strength_unknown_word": _gamme(diagnostic_relations=[_relation(evidence={**EVIDENCE, "strength": "toujours"})]),
    "vehicle_scope_empty": _gamme(diagnostic_relations=[_relation(vehicle_scope={})]),
    "vehicle_scope_engine_series_not_admitted": _gamme(diagnostic_relations=[_relation(vehicle_scope={"engine_series": "K9K"})]),
    "vehicle_scope_commercial_name": _gamme(diagnostic_relations=[_relation(vehicle_scope={"fuel": "TDI"})]),
    "citation_empty_list": _gamme(diagnostic_relations=[_relation(citations=[])]),
    "citation_bad_digest": _gamme(diagnostic_relations=[_relation(citations=[{**RELATION["citations"][0], "quote_sha256": "abc"}])]),
    "citation_extra_key": _gamme(diagnostic_relations=[_relation(citations=[{**RELATION["citations"][0], "excerpt": "texte"}])]),
    "citation_negative_start": _gamme(diagnostic_relations=[_relation(citations=[{**RELATION["citations"][0], "start": -1}])]),
    "cause_slug_uppercase": _gamme(diagnostic_relations=[_relation(cause_slug="Filtre")]),
}


@pytest.mark.parametrize("name", sorted(INVALID))
def test_schema_rejects(name):
    assert _errors(INVALID[name]), f"{name} must be rejected by the schema"


# ---------- 2. Parité carburant ----------

def test_vehicle_scope_fuel_vocabulary_is_the_vehicle_schema_vocabulary():
    vehicle = json.loads((SCHEMA_DIR / "entity-data" / "vehicle.schema.json").read_text(encoding="utf-8"))
    canon = vehicle["properties"]["motorizations"]["items"]["properties"]["fuel"]["enum"]
    scope = SCHEMA["properties"]["diagnostic_relations"]["items"]["properties"]["vehicle_scope"]
    assert scope["properties"]["fuel"]["enum"] == canon


# ---------- 3. Gates same-repo (appel direct) ----------

PROVEN = {"src_a": {"status": "active", "type": "oem_manual", "raw_ref": {"manifest_id": "m-a", "expected_sha256": QUOTE_SHA}}}


def test_relation_messages_keep_their_legacy_wording():
    """Extraction du contrôle evidence/sources : libellés des relations inchangés (consommés tels quels)."""
    fm = {"diagnostic_relations": [{**RELATION, "sources": ["inconnue"], "citations": None,
                                    "evidence": {"confidence": "high", "source_policy": "1_high"}}]}
    fm["diagnostic_relations"][0].pop("citations")
    issues = qg.gate_diagnostic_relations(fm, {})
    assert issues == [
        "schema_invalid: diagnostic_relations[0].evidence missing reviewed",
        "schema_invalid: diagnostic_relations[0].evidence missing diagnostic_safe",
        "source_policy_violated: diagnostic_relations[0] policy=1_high but no source with type allowing 'high' confidence",
        "confidence_overclaimed: diagnostic_relations[0] confidence=high but no source has eligible source_type",
        "source_slug_unknown: diagnostic_relations[0] cites 'inconnue' (base 'inconnue') absent from _meta/source-catalog.yaml",
    ]


def test_citation_span_must_be_non_empty():
    fm = {"diagnostic_relations": [_relation(citations=[{"source": "src_a", "start": 10, "end": 10, "quote_sha256": QUOTE_SHA}])]}
    assert any(i.startswith("citation_span_invalid: diagnostic_relations[0].citations[0]")
               for i in qg.gate_diagnostic_relations(fm, PROVEN))


def test_citation_on_page_suffixed_source_resolves_its_base_slug():
    fm = {"diagnostic_relations": [_relation(sources=["src_a_p12"])]}
    assert qg.gate_diagnostic_relations(fm, PROVEN) == []


def test_citation_source_is_the_base_slug_never_a_page():
    """L'ancre vise l'archive entière (points de code) : un suffixe de page n'y a pas de sens."""
    page = {**RELATION["citations"][0], "source": "src_a_p12"}
    fm = {"diagnostic_relations": [_relation(citations=[page], sources=["src_a_p12"])]}
    assert any(i.startswith("citation_source_not_in_sources: diagnostic_relations[0].citations[0] cites 'src_a_p12'")
               for i in qg.gate_diagnostic_relations(fm, PROVEN))


def test_safety_rules_path_is_fixed_under_wiki():
    fm = {"safety_rules": [RULE]}
    wrong = qg.REPO_ROOT / "wiki" / "diagnostic" / "safety-config.md"
    right = qg.REPO_ROOT / "wiki" / "diagnostic" / "regles-securite.md"
    proposal = qg.REPO_ROOT / "proposals" / "regles-securite.md"
    assert any(i.startswith("safety_rules_path_invalid") for i in qg.gate_safety_rules(fm, wrong, PROVEN))
    assert qg.gate_safety_rules(fm, right, PROVEN) == []
    assert qg.gate_safety_rules(fm, proposal, PROVEN) == []


def test_cited_source_slugs_cover_relations_quick_checks_and_rules():
    def cite(src):
        return [{"source": src, "start": 0, "end": 1, "quote_sha256": QUOTE_SHA}]
    fm = {"diagnostic_relations": [_relation(citations=cite("a"))],
          "diagnostic": {"quick_checks": [{**QUICK_CHECK, "citations": cite("b")}]},
          "safety_rules": [{**RULE, "citations": cite("c")}]}
    assert qg.cited_source_slugs(fm) == {"a", "b", "c"}
    assert qg.cited_source_slugs({}) == set()


# ---------- 4. gate_citation_anchors (cross-repo) ----------

# Accents avant l'extrait (octets ≠ points de code) + CRLF (read_text() traduirait les fins de ligne).
ARCHIVE_TEXT = "Préambule éèà\r\nLe filtre colmaté réduit le débit d'air.\r\nFin.\r\n"
QUOTE = "filtre colmaté réduit le débit"


def _raw(tmp_path: Path, monkeypatch, content: bytes, *, slug="src_a", status="active") -> dict:
    raw = tmp_path / "raw"
    (raw / "sources").mkdir(parents=True)
    (raw / "manifests").mkdir()
    (raw / "sources" / "doc.md").write_bytes(content)
    digest = "sha256:" + hashlib.sha256(content).hexdigest()
    (raw / "manifests" / "source-inventory.csv").write_text(
        "path,manifest_id,layer,unstable_id,sha256,size_bytes,added_at\n"
        f"sources/doc.md,m-doc,sources,,{digest},{len(content)},2026-10-05\n", encoding="utf-8")
    monkeypatch.setattr(qg, "RAW_INVENTORY", raw / "manifests" / "source-inventory.csv")
    return {slug: {"status": status, "type": "oem_manual",
                   "raw_ref": {"repo": "automecanik-raw", "manifest_id": "m-doc", "expected_sha256": digest}}}


def _citation(text: str, quote: str, source="src_a") -> dict:
    start = text.index(quote)
    return {"source": source, "start": start, "end": start + len(quote),
            "quote_sha256": "sha256:" + hashlib.sha256(quote.encode("utf-8")).hexdigest()}


def _fm_citing(citation: dict) -> dict:
    return {"diagnostic_relations": [_relation(citations=[citation], sources=[citation["source"]])]}


def test_anchor_matches_code_point_span_on_untranslated_utf8(tmp_path, monkeypatch):
    catalog = _raw(tmp_path, monkeypatch, ARCHIVE_TEXT.encode("utf-8"))
    citation = _citation(ARCHIVE_TEXT, QUOTE)
    # Garde du test : un décalage en octets ou un texte aux fins de ligne traduites ne coïnciderait pas.
    assert len(ARCHIVE_TEXT[:citation["start"]].encode("utf-8")) != citation["start"]
    assert ARCHIVE_TEXT.replace("\r\n", "\n").find(QUOTE) != citation["start"]
    assert qg.gate_citation_anchors(_fm_citing(citation), catalog) == []


def test_anchor_on_quick_check_and_safety_rule_is_verified(tmp_path, monkeypatch):
    catalog = _raw(tmp_path, monkeypatch, ARCHIVE_TEXT.encode("utf-8"))
    bad = {**_citation(ARCHIVE_TEXT, QUOTE), "quote_sha256": QUOTE_SHA}
    fm = {"diagnostic": {"quick_checks": [{**QUICK_CHECK, "citations": [bad]}]},
          "safety_rules": [{**RULE, "citations": [bad]}]}
    issues = qg.gate_citation_anchors(fm, catalog)
    assert [i.split(":")[0] for i in issues] == ["citation_quote_mismatch", "citation_quote_mismatch"]
    assert "diagnostic.quick_checks[0].citations[0]" in issues[0]
    assert "safety_rules[0].citations[0]" in issues[1]


@pytest.mark.parametrize("mutation, expected", [
    (lambda c: {**c, "quote_sha256": QUOTE_SHA}, "citation_quote_mismatch"),
    (lambda c: {**c, "start": c["start"] + 1, "end": c["end"] + 1}, "citation_quote_mismatch"),
    (lambda c: {**c, "end": len(ARCHIVE_TEXT) + 1}, "citation_span_out_of_range"),
])
def test_anchor_mismatch_fails(tmp_path, monkeypatch, mutation, expected):
    catalog = _raw(tmp_path, monkeypatch, ARCHIVE_TEXT.encode("utf-8"))
    issues = qg.gate_citation_anchors(_fm_citing(mutation(_citation(ARCHIVE_TEXT, QUOTE))), catalog)
    assert len(issues) == 1 and issues[0].startswith(expected), issues


def test_archive_changed_after_inventory_fails(tmp_path, monkeypatch):
    catalog = _raw(tmp_path, monkeypatch, ARCHIVE_TEXT.encode("utf-8"))
    (qg.RAW_INVENTORY.parent.parent / "sources" / "doc.md").write_bytes(b"autre contenu")
    issues = qg.gate_citation_anchors(_fm_citing(_citation(ARCHIVE_TEXT, QUOTE)), catalog)
    assert len(issues) == 1 and issues[0].startswith("citation_archive_sha_drift:src_a"), issues


def test_non_text_archive_cannot_carry_an_anchor(tmp_path, monkeypatch):
    catalog = _raw(tmp_path, monkeypatch, b"%PDF-1.7\n\xff\xfe\x00binary")
    citation = {"source": "src_a", "start": 0, "end": 4, "quote_sha256": QUOTE_SHA}
    issues = qg.gate_citation_anchors(_fm_citing(citation), catalog)
    assert len(issues) == 1 and issues[0].startswith("citation_source_not_text:src_a"), issues


def test_unproven_or_unknown_source_fails(tmp_path, monkeypatch):
    catalog = _raw(tmp_path, monkeypatch, ARCHIVE_TEXT.encode("utf-8"), status="to_capture")
    citation = _citation(ARCHIVE_TEXT, QUOTE)
    assert qg.gate_citation_anchors(_fm_citing(citation), catalog)[0].startswith("citation_source_not_raw_proven:src_a")
    unknown = _citation(ARCHIVE_TEXT, QUOTE, source="src_absente")
    assert qg.gate_citation_anchors(_fm_citing(unknown), catalog)[0].startswith("citation_source_not_raw_proven:src_absente")


def test_unresolved_archive_fails(tmp_path, monkeypatch):
    catalog = _raw(tmp_path, monkeypatch, ARCHIVE_TEXT.encode("utf-8"))
    catalog["src_a"]["raw_ref"]["expected_sha256"] = QUOTE_SHA  # aucune ligne d'inventaire à ce hash
    issues = qg.gate_citation_anchors(_fm_citing(_citation(ARCHIVE_TEXT, QUOTE)), catalog)
    assert len(issues) == 1 and issues[0].startswith("raw_archive_unresolved:src_a"), issues


def test_missing_raw_inventory_is_infra_unavailable_not_a_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(qg, "RAW_INVENTORY", tmp_path / "absent" / "source-inventory.csv")
    issues = qg.gate_citation_anchors(_fm_citing(_citation(ARCHIVE_TEXT, QUOTE)), PROVEN)
    # Marqueur reconnu par promotion_decision.normalize_provenance → UNAVAILABLE (fail-closed).
    assert len(issues) == 1 and issues[0].startswith("raw_inventory_unreachable:"), issues


def test_no_citation_needs_no_raw(tmp_path, monkeypatch):
    monkeypatch.setattr(qg, "RAW_INVENTORY", tmp_path / "absent" / "source-inventory.csv")
    assert qg.gate_citation_anchors({"diagnostic_relations": [_relation(citations=None)]}, PROVEN) == []
