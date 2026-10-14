#!/usr/bin/env python3
"""
Tests A3 — composition canonique de la décision de promotion (INNER LOOP control-plane).

Vérifie, par tranches indépendantes RED→GREEN :
  (i)   evaluate_tier expose les gate_outcomes STRUCTURÉS (status + violations)
        — 1 gate = 1 exécution = 1 résultat structuré conservé (contrat #2).
  (ii)  decide_promotion PUR & déterministe (même bundle ⇒ même décision).
  (iii) 3 évaluateurs manquants composés (coverage / regression / provenance),
        fail-closed préservant substance_tier (contrat P0-2).
  (iv)  snapshot + input_manifest + engine revisions (contrats #1/#3).
  (v)   surface CLI dry-run ≡ apply + anti-TOCTOU (contrat #2 CLI).

Discipline test_promote : 0 LLM / 0 DB, gates injectés factices.
"""
from __future__ import annotations

import datetime
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_promote():
    return _load("_promote", "promote.py")


FM_OK = {
    "entity_type": "gamme",
    "slug": "filtre-a-huile",
    "truth_level": "L1",
    "review_status": "in_review",
    "source_refs": [{"kind": "raw"}, {"kind": "web"}],
    "exportable": {"seo": False, "rag": False},
}


def _gate_result(status: str, violations=None):
    """Fake GateResult exposant status + violations structurées (miroir gates/_common.GateResult)."""
    vs = [SimpleNamespace(gate_id=g, message=m) for g, m in (violations or [])]
    return SimpleNamespace(status=status, violations=vs)


def _gate_fn(name: str, fail_name: str | None, msg: str):
    def fn(target):
        if name == fail_name:
            return _gate_result("fail", [(fail_name, msg)])
        return _gate_result("pass", [])
    return fn


def _gates(fail_name: str | None = None, msg: str = "claim non sourcé"):
    names = ["source", "claim", "contradiction", "risk", "confidence"]
    return [(n, _gate_fn(n, fail_name, msg)) for n in names]


# --- A3-i : evaluate_tier expose les gate_outcomes structurés ------------------
def test_evaluate_tier_exposes_structured_gate_outcomes(tmp_path):
    """Contrat #2 : evaluate_tier conserve le GateResult structuré (status + violations),
    pas seulement {name: status} — evidence non aplatie."""
    mod = _load_promote()
    d = mod.evaluate_tier(
        FM_OK, "body", tmp_path / "p.md", tmp_path,
        threshold=0.80, gates=_gates("risk", "claim non sourcé"),
        compute_score=lambda *a: 0.90,
    )
    assert "gate_outcomes" in d, "evaluate_tier doit exposer gate_outcomes structurés"
    outcomes = {o["name"]: o for o in d["gate_outcomes"]}
    assert set(outcomes) == {"source", "claim", "contradiction", "risk", "confidence"}
    assert outcomes["risk"]["status"] == "fail"
    # evidence structurée préservée (pas aplatie en 'gate:risk=fail')
    assert outcomes["risk"]["violations"] == [{"gate_id": "risk", "message": "claim non sourcé"}]
    assert outcomes["source"]["status"] == "pass"
    assert outcomes["source"]["violations"] == []
    # rétro-compat : gate_status (name->status) toujours présent
    assert d["gate_status"]["risk"] == "fail"


def test_evaluate_tier_gate_outcomes_single_execution(tmp_path):
    """1 gate = 1 exécution : chaque gate fn n'est appelée qu'une fois par evaluate_tier."""
    mod = _load_promote()
    calls: dict[str, int] = {}

    def counting_gate(name):
        def fn(target):
            calls[name] = calls.get(name, 0) + 1
            return _gate_result("pass", [])
        return fn

    names = ["source", "claim", "contradiction", "risk", "confidence"]
    gates = [(n, counting_gate(n)) for n in names]
    mod.evaluate_tier(
        FM_OK, "body", tmp_path / "p.md", tmp_path,
        threshold=0.80, gates=gates, compute_score=lambda *a: 0.90,
    )
    assert all(v == 1 for v in calls.values()), calls


def test_evaluate_tier_gate_outcomes_tolerates_status_only_gates(tmp_path):
    """Rétro-compat : un gate factice sans .violations (status-only) ne casse pas
    l'exposition structurée (violations dégradées à [])."""
    mod = _load_promote()
    names = ["source", "claim", "contradiction", "risk", "confidence"]
    gates = [(n, (lambda t: SimpleNamespace(status="pass"))) for n in names]
    d = mod.evaluate_tier(
        FM_OK, "body", tmp_path / "p.md", tmp_path,
        threshold=0.80, gates=gates, compute_score=lambda *a: 0.90,
    )
    outcomes = {o["name"]: o for o in d["gate_outcomes"]}
    assert outcomes["risk"]["violations"] == []


# --- A3-ii : evaluate_tier emits structured checks + pure decide_promotion -----
def _load_decision():
    return _load("_promotion_decision", "promotion_decision.py")


def _substance(mod, fm=None, gates=None, score=0.90, body="body", tmp_path=None):
    """Produit un composant `substance` (sortie evaluate_tier) pour construire un bundle."""
    return mod.evaluate_tier(
        fm or FM_OK, body, (tmp_path or Path("/tmp")) / "p.md", (tmp_path or Path("/tmp")),
        threshold=0.80, gates=gates or _gates(), compute_score=lambda *a: score,
    )


def test_evaluate_tier_emits_structured_checks(tmp_path):
    """decide_promotion doit consommer des CHECKS structurés, pas de la prose (C0).
    evaluate_tier expose une liste `checks` [{code, status, owner_stage, evidence}]."""
    mod = _load_promote()
    d = mod.evaluate_tier(
        FM_OK, "body", tmp_path / "p.md", tmp_path,
        threshold=0.80, gates=_gates("risk"), compute_score=lambda *a: 0.90,
    )
    assert "checks" in d
    by_code = {c["code"]: c for c in d["checks"]}
    # une check par dimension (safety, numeric, 5 gates, truth, substance, source-diversity)
    for code in ("SAFETY_HUMAN_REVIEW", "NUMERIC_HIGH_HARM", "GATE_RISK",
                 "TRUTH_LEVEL", "SUBSTANCE_SCORE", "SOURCE_DIVERSITY"):
        assert code in by_code, code
        assert by_code[code]["status"] in ("pass", "fail")
        assert by_code[code]["owner_stage"]
    assert by_code["GATE_RISK"]["status"] == "fail"
    assert by_code["SAFETY_HUMAN_REVIEW"]["status"] == "pass"  # FM_OK non-safety


def test_decide_promotion_is_pure_and_deterministic(tmp_path):
    """Même bundle ⇒ même PromotionDecision (fonction pure : 0 I/O, appelable 2×)."""
    pm = _load_promote()
    dec = _load_decision()
    substance = _substance(pm, tmp_path=tmp_path)
    bundle = {"substance": substance, "coverage": None, "regression": None, "provenance": None}
    d1 = dec.decide_promotion(bundle)
    d2 = dec.decide_promotion(bundle)
    assert d1 == d2
    assert d1["schema_version"]


def test_decide_promotion_eligible_when_substance_clean(tmp_path):
    pm = _load_promote()
    dec = _load_decision()
    substance = _substance(pm, gates=_gates(), score=0.90, tmp_path=tmp_path)  # all pass
    bundle = {"substance": substance}
    d = dec.decide_promotion(bundle)
    assert d["eligible"] is True
    assert d["promotion_status"] == "ELIGIBLE"
    assert d["blocking_reasons"] == []


def test_decide_promotion_blocks_with_typed_reasons_not_prose(tmp_path):
    """Blocking reasons = objets typés {code, owner_stage, detector_stage, evidence},
    jamais de prose (C0 : détection ≠ routage ; ordre canonique stable)."""
    pm = _load_promote()
    dec = _load_decision()
    substance = _substance(pm, gates=_gates("source"), score=0.90, tmp_path=tmp_path)
    d = dec.decide_promotion({"substance": substance})
    assert d["eligible"] is False
    assert d["promotion_status"] == "BLOCKED"
    codes = [r["code"] for r in d["blocking_reasons"]]
    assert "GATE_SOURCE" in codes
    for r in d["blocking_reasons"]:
        assert set(r) >= {"code", "owner_stage", "detector_stage", "evidence"}
        assert isinstance(r["code"], str)
    # ordre canonique déterministe (tri stable)
    assert codes == sorted(codes) or len(codes) == 1


def test_decide_promotion_preserves_substance_tier(tmp_path):
    """substance_tier reflète la dimension substance, exposée même quand bloqué."""
    pm = _load_promote()
    dec = _load_decision()
    substance = _substance(pm, gates=_gates("risk"), score=0.90, tmp_path=tmp_path)
    d = dec.decide_promotion({"substance": substance})
    assert "substance_tier" in d
    assert d["substance_tier"] is not None


# --- A1 + A3-iii : composer coverage / regression / provenance ----------------
def _clean_substance(tmp_path):
    """substance qui passe TOUS les checks (evaluate_tier ⇒ TIER A)."""
    pm = _load_promote()
    return _substance(pm, gates=_gates(), score=0.90, tmp_path=tmp_path)


def test_A1_divergence_composition_blocks_when_coverage_fails(tmp_path):
    """A1 (défaut central) : substance PASSE (eligible côté evaluate_tier), mais
    coverage-strict FAIL ⇒ la composition DOIT bloquer. Prouve que la décision
    n'est plus fragmentée (le gate manquant participe au verdict)."""
    dec = _load_decision()
    substance = _clean_substance(tmp_path)
    # divergence : substance seule = eligible ; coverage FAIL doit renverser le verdict
    assert dec.decide_promotion({"substance": substance})["eligible"] is True
    d = dec.decide_promotion({
        "substance": substance,
        "coverage": {"status": "FAIL", "evidence": {"fails": ["source_slug FK absent"]}},
    })
    assert d["eligible"] is False
    assert d["promotion_status"] == "BLOCKED"
    codes = [r["code"] for r in d["blocking_reasons"]]
    assert "COVERAGE_STRICT_FAIL" in codes
    # substance_tier préservé (le défaut coverage ne falsifie pas la substance)
    assert d["substance_tier"] == substance_tier_of(substance)


def substance_tier_of(substance):
    dec = _load_decision()
    return dec._substance_tier(substance)


def test_coverage_warn_is_observability_not_blocking(tmp_path):
    """coverage WARN = advisory (mirror CI : --strict bloque sur FAIL, pas WARN)."""
    dec = _load_decision()
    d = dec.decide_promotion({
        "substance": _clean_substance(tmp_path),
        "coverage": {"status": "WARN", "evidence": {"warns": ["coverage-map absente"]}},
    })
    assert d["eligible"] is True


def test_regression_regressed_blocks(tmp_path):
    dec = _load_decision()
    d = dec.decide_promotion({
        "substance": _clean_substance(tmp_path),
        "regression": {"verdict": "REGRESSED", "evidence": {"delta": -0.12}},
    })
    assert d["eligible"] is False
    assert "REGRESSION_DETECTED" in [r["code"] for r in d["blocking_reasons"]]


def test_regression_new_and_neutral_do_not_block(tmp_path):
    dec = _load_decision()
    for verdict in ("NEW", "NEUTRAL", "IMPROVED"):
        d = dec.decide_promotion({
            "substance": _clean_substance(tmp_path),
            "regression": {"verdict": verdict, "evidence": {}},
        })
        assert d["eligible"] is True, verdict


def test_A6_provenance_fail_blocks_nonsafety(tmp_path):
    """A6 : une fiche NON-safety avec raw_ref KO NE PEUT PAS être eligible
    (fermeture du fail-open non-safety au bon niveau : la composition)."""
    dec = _load_decision()
    d = dec.decide_promotion({
        "substance": _clean_substance(tmp_path),
        "provenance": {"status": "FAIL", "evidence": {"failures": ["raw_ref invalide"]}},
    })
    assert d["eligible"] is False
    assert d["promotion_status"] == "BLOCKED"
    assert "PROVENANCE_RAW_REF_FAIL" in [r["code"] for r in d["blocking_reasons"]]


def test_P0_2_provenance_unavailable_is_unknown_fail_closed_not_false_tier(tmp_path):
    """P0-2 : provenance INDISPONIBLE (RAW absent) ⇒ eligible=false +
    promotion_status=UNKNOWN_FAIL_CLOSED + reason PROVENANCE_GATE_UNAVAILABLE,
    substance_tier PRÉSERVÉ — JAMAIS un faux TIER B, JAMAIS route infra→specialist."""
    dec = _load_decision()
    substance = _clean_substance(tmp_path)
    d = dec.decide_promotion({
        "substance": substance,
        "provenance": {"status": "UNAVAILABLE", "evidence": {"reason": "cross_repo_env_missing"}},
    })
    assert d["eligible"] is False
    assert d["promotion_status"] == "UNKNOWN_FAIL_CLOSED"
    reasons = {r["code"]: r for r in d["blocking_reasons"]}
    assert "PROVENANCE_GATE_UNAVAILABLE" in reasons
    assert reasons["PROVENANCE_GATE_UNAVAILABLE"]["owner_stage"] == "PROVENANCE"
    # score métier NON falsifié : substance_tier reste celui de la substance
    assert d["substance_tier"] == substance_tier_of(substance)


def test_all_three_evaluators_clean_is_eligible(tmp_path):
    dec = _load_decision()
    d = dec.decide_promotion({
        "substance": _clean_substance(tmp_path),
        "coverage": {"status": "PASS", "evidence": {}},
        "regression": {"verdict": "IMPROVED", "evidence": {"delta": 0.05}},
        "provenance": {"status": "PASS", "evidence": {}},
    })
    assert d["eligible"] is True
    assert d["promotion_status"] == "ELIGIBLE"


# --- A3-iii : normalizers PURS (forme brute évaluateur → sous-résultat bundle) --
def test_normalize_coverage_maps_status():
    dec = _load_decision()
    assert dec.normalize_coverage({"status": "FAIL", "fails": ["x"]})["status"] == "FAIL"
    assert dec.normalize_coverage({"status": "warn", "warns": ["y"]})["status"] == "WARN"
    assert dec.normalize_coverage({"status": "PASS"})["status"] == "PASS"


def test_normalize_regression_maps_verdict():
    dec = _load_decision()
    r = dec.normalize_regression({"verdict": "REGRESSED", "delta_score": -0.1, "old_score": 0.9})
    assert r["verdict"] == "REGRESSED"
    assert r["evidence"]["delta_score"] == -0.1


def test_normalize_provenance_distinguishes_infra_from_content():
    """P0-2 au niveau normalizer : RAW absent / raw_inventory_unreachable = UNAVAILABLE,
    échec de contenu (raw_ref malformé) = FAIL, distincts."""
    dec = _load_decision()
    # RAW absent
    assert dec.normalize_provenance([], [], raw_available=False)["status"] == "UNAVAILABLE"
    # marqueur infra dans failures
    assert dec.normalize_provenance(
        ["raw_inventory_unreachable:slug: cross-repo"], [])["status"] == "UNAVAILABLE"
    # échec de contenu
    assert dec.normalize_provenance(
        ["raw_ref_malformed:slug"], [])["status"] == "FAIL"
    # propre
    assert dec.normalize_provenance([], ["advisory"])["status"] == "PASS"


def test_assemble_bundle_then_decide_end_to_end(tmp_path):
    """assemble_bundle (pur) + decide_promotion : chaîne complète depuis les sorties
    brutes des évaluateurs réels, provenance RAW indisponible → UNKNOWN_FAIL_CLOSED."""
    dec = _load_decision()
    substance = _clean_substance(tmp_path)
    bundle = dec.assemble_bundle(
        substance,
        coverage_raw={"status": "PASS"},
        regression_raw={"verdict": "NEW"},
        provenance_raw=([], []),
        raw_available=False,  # RAW non fourni
    )
    d = dec.decide_promotion(bundle)
    assert d["promotion_status"] == "UNKNOWN_FAIL_CLOSED"
    assert d["eligible"] is False
    assert "PROVENANCE_GATE_UNAVAILABLE" in [r["code"] for r in d["blocking_reasons"]]
    assert d["substance_tier"] == substance_tier_of(substance)


def test_assemble_bundle_omitted_evaluators_are_none(tmp_path):
    dec = _load_decision()
    bundle = dec.assemble_bundle(_clean_substance(tmp_path))
    assert bundle["coverage"] is None
    assert bundle["regression"] is None
    assert bundle["provenance"] is None
    assert dec.decide_promotion(bundle)["eligible"] is True  # substance seule = eligible


# --- A3-iv : snapshot manifest + engine revisions + stale detection -----------
def _write_candidate(tmp_path, content="---\nentity_type: gamme\nslug: filtre-a-huile\n---\nbody\n"):
    (tmp_path / "_meta").mkdir(exist_ok=True)
    (tmp_path / "_meta" / "source-catalog.yaml").write_text("sources: []\n", encoding="utf-8")
    cand = tmp_path / "proposals" / "filtre-a-huile.md"
    cand.parent.mkdir(exist_ok=True)
    cand.write_text(content, encoding="utf-8")
    return cand


def test_capture_input_manifest_is_deterministic_and_canonical(tmp_path):
    dec = _load_decision()
    cand = _write_candidate(tmp_path)
    m1 = dec.capture_input_manifest(cand, tmp_path, None, None)
    m2 = dec.capture_input_manifest(cand, tmp_path, None, None)
    assert m1 == m2
    entries = m1["input_manifest"]
    # trié canoniquement (role, path) — pas d'ordre implicite
    assert entries == sorted(entries, key=lambda e: (e["role"], e["path"]))
    roles = {e["role"] for e in entries}
    assert "candidate" in roles and "source_catalog" in roles
    # pas de path absolu machine-dépendant
    for e in entries:
        assert not str(e["path"]).startswith("/")
    # deux revisions d'engine distinctes conceptuellement (contrat #5)
    assert "evaluation_engine_revision" in m1 and "decision_engine_revision" in m1


def test_manifest_hash_reflects_actual_content(tmp_path):
    """Worktree dirty : le hash suit le CONTENU réellement lu, pas seulement la SHA git."""
    dec = _load_decision()
    cand = _write_candidate(tmp_path, "---\nentity_type: gamme\nslug: a\n---\nv1\n")
    h1 = dec.capture_input_manifest(cand, tmp_path, None, None)
    cand.write_text("---\nentity_type: gamme\nslug: a\n---\nv2 CHANGED\n", encoding="utf-8")
    h2 = dec.capture_input_manifest(cand, tmp_path, None, None)
    cand_sha1 = [e["sha256"] for e in h1["input_manifest"] if e["role"] == "candidate"][0]
    cand_sha2 = [e["sha256"] for e in h2["input_manifest"] if e["role"] == "candidate"][0]
    assert cand_sha1 != cand_sha2


def test_canonical_decision_attaches_inputs_manifest(tmp_path):
    dec = _load_decision()
    cand = _write_candidate(tmp_path)
    substance = _clean_substance(tmp_path)

    def fake_run(candidate_path, wiki_root, raw_root, baseline_path, threshold, gates, compute_score):
        return substance, {"status": "PASS"}, {"verdict": "NEW"}, ([], []), True

    d = dec.canonical_promotion_decision(cand, tmp_path, run_evaluators=fake_run)
    assert "inputs" in d
    assert d["inputs"]["input_manifest"]
    assert d["eligible"] is True


def test_stale_during_evaluation_is_fail_closed(tmp_path):
    """Contrat #1 : si un input change PENDANT l'évaluation (hash-before != after),
    la décision est UNKNOWN_FAIL_CLOSED / STALE_DURING_EVALUATION."""
    dec = _load_decision()
    cand = _write_candidate(tmp_path, "---\nentity_type: gamme\nslug: a\n---\nbefore\n")
    substance = _clean_substance(tmp_path)

    def mutating_run(candidate_path, wiki_root, raw_root, baseline_path, threshold, gates, compute_score):
        # simule une modif concurrente du candidat pendant l'évaluation
        Path(candidate_path).write_text("---\nentity_type: gamme\nslug: a\n---\nMUTATED\n", encoding="utf-8")
        return substance, {"status": "PASS"}, {"verdict": "NEW"}, ([], []), True

    d = dec.canonical_promotion_decision(cand, tmp_path, run_evaluators=mutating_run)
    assert d["eligible"] is False
    assert d["promotion_status"] == "UNKNOWN_FAIL_CLOSED"
    assert "STALE_DURING_EVALUATION" in [r["code"] for r in d["blocking_reasons"]]
    # substance_tier préservé même en stale
    assert d["substance_tier"] == substance_tier_of(substance)


# --- A3-v : CLI dry-run ≡ apply + anti-TOCTOU (dumb executor) ------------------
def _decide_with_inputs(dec, cand, tmp_path, substance):
    """Décision canonique avec un runner injecté (hermétique) — attache `inputs`."""
    def fake_run(*a):
        return substance, {"status": "PASS"}, {"verdict": "NEW"}, ([], []), True
    return dec.canonical_promotion_decision(cand, tmp_path, run_evaluators=fake_run)


def test_canonical_decision_carries_evaluation_passthrough(tmp_path):
    """A3-v : la décision embarque l'évidence `evaluation` (tier/score/gate_status/
    shadow) issue de LA MÊME exécution evaluate_tier — pour le stamp apply (DUMB
    EXECUTOR) et le report rétro-compat, sans réexécution (contrat #2)."""
    dec = _load_decision()
    cand = _write_candidate(tmp_path)
    substance = _clean_substance(tmp_path)  # tier A
    d = _decide_with_inputs(dec, cand, tmp_path, substance)
    assert "evaluation" in d
    assert d["evaluation"]["tier"] == substance["tier"]
    assert d["evaluation"]["confidence_score"] == substance["confidence_score"]
    assert d["evaluation"]["gate_status"] == substance["gate_status"]


def test_reverify_inputs_none_when_unchanged(tmp_path):
    dec = _load_decision()
    cand = _write_candidate(tmp_path)
    d = _decide_with_inputs(dec, cand, tmp_path, _clean_substance(tmp_path))
    assert dec.reverify_inputs(d, cand, tmp_path) is None


def test_reverify_inputs_flags_content_drift(tmp_path):
    """Anti-TOCTOU : un input change APRÈS la décision (hash du contenu) ⇒ STALE_DECISION."""
    dec = _load_decision()
    cand = _write_candidate(tmp_path, "---\nentity_type: gamme\nslug: a\n---\nv1\n")
    d = _decide_with_inputs(dec, cand, tmp_path, _clean_substance(tmp_path))
    cand.write_text("---\nentity_type: gamme\nslug: a\n---\nv2 CHANGED\n", encoding="utf-8")
    r = dec.reverify_inputs(d, cand, tmp_path)
    assert r is not None and r["code"] == "STALE_DECISION"
    assert "input_manifest" in r["evidence"]


def test_reverify_inputs_flags_engine_revision_drift(tmp_path):
    """Anti-TOCTOU couvre AUSSI les DEUX engine revisions — pas seulement
    candidate/baseline (le code des évaluateurs peut invalider la décision)."""
    dec = _load_decision()
    cand = _write_candidate(tmp_path)
    d = _decide_with_inputs(dec, cand, tmp_path, _clean_substance(tmp_path))
    d["inputs"]["evaluation_engine_revision"] = "TAMPERED"  # simule un engine différent
    r = dec.reverify_inputs(d, cand, tmp_path)
    assert r is not None and r["code"] == "STALE_DECISION"
    assert "evaluation_engine_revision" in r["evidence"]


def test_authorize_apply_refuses_when_not_eligible(tmp_path):
    """La porte du DUMB EXECUTOR refuse une décision non-eligible sans réévaluer."""
    dec = _load_decision()
    cand = _write_candidate(tmp_path)
    blocked = {"promotion_status": "BLOCKED", "eligible": False,
               "inputs": dec.capture_input_manifest(cand, tmp_path, None, None)}
    ok, refusal = dec.authorize_apply(blocked, cand, tmp_path)
    assert ok is False
    assert refusal["code"] == "APPLY_NOT_ELIGIBLE"


def test_authorize_apply_ok_when_eligible_and_fresh(tmp_path):
    dec = _load_decision()
    cand = _write_candidate(tmp_path)
    d = _decide_with_inputs(dec, cand, tmp_path, _clean_substance(tmp_path))
    assert d["eligible"] is True
    ok, refusal = dec.authorize_apply(d, cand, tmp_path)
    assert ok is True and refusal is None


def test_authorize_apply_refuses_on_stale(tmp_path):
    """Éligible à la décision, mais un input dérive avant apply ⇒ refus STALE_DECISION
    (le --apply n'est JAMAIS un 2ᵉ décideur ; il exige la fraîcheur du manifeste complet)."""
    dec = _load_decision()
    cand = _write_candidate(tmp_path, "---\nentity_type: gamme\nslug: a\n---\nv1\n")
    d = _decide_with_inputs(dec, cand, tmp_path, _clean_substance(tmp_path))
    cand.write_text("---\nentity_type: gamme\nslug: a\n---\nMUTATED\n", encoding="utf-8")
    ok, refusal = dec.authorize_apply(d, cand, tmp_path)
    assert ok is False and refusal["code"] == "STALE_DECISION"


# --- A3-v : CLI main() route dry-run ET apply par le MÊME décideur canonique ----
def _write_promotable(tmp_path):
    (tmp_path / "_meta").mkdir(exist_ok=True)
    (tmp_path / "_meta" / "source-catalog.yaml").write_text("sources: []\n", encoding="utf-8")
    prop = tmp_path / "proposals" / "filtre-a-huile.md"
    prop.parent.mkdir(exist_ok=True)
    prop.write_text(
        "---\n"
        "entity_type: gamme\n"
        "slug: filtre-a-huile\n"
        "truth_level: L1\n"
        "review_status: in_review\n"
        "source_refs:\n  - kind: raw\n  - kind: web\n"
        "exportable:\n  seo: false\n  rag: false\n"
        "---\nCorps de la fiche filtre à huile.\n",
        encoding="utf-8")
    return prop


def _extract_json_obj(text):
    """JSON du bloc principal — robuste à un éventuel bruit stdout/stderr autour."""
    import json as _json
    return _json.loads(text[text.index("{"):text.rindex("}") + 1])


def test_cli_dry_run_routes_through_canonical_decision(tmp_path, monkeypatch):
    """Preuve que main() dry-run passe par le décideur canonique (champs
    promotion_status/eligible/substance_tier/inputs que evaluate_tier SEUL n'a jamais
    produits) TOUT en préservant le contrat rétro-compat du pilote (report/tier_A/tier).
    """
    from click.testing import CliRunner
    pm = _load_promote()
    _write_promotable(tmp_path)
    # RAW absent ⇒ provenance UNAVAILABLE (fail-closed, jamais skip silencieux) —
    # pas de dépendance au repo raw réel.
    monkeypatch.setenv("AUTOMECANIK_RAW_PATH", str(tmp_path / "no-raw"))
    monkeypatch.delenv("PROMOTE_GATE_ENGINE", raising=False)
    result = CliRunner().invoke(pm.main, [
        "--wiki-root", str(tmp_path), "--target", "proposals/filtre-a-huile.md",
        "--dry-run", "--format", "json"])
    assert result.exit_code == 0, result.output
    data = _extract_json_obj(result.output)
    # rétro-compat pilote : clés top-level + entry.tier
    assert "report" in data and "tier_A" in data and "tier_B" in data
    entry = data["report"][0]
    assert "tier" in entry  # le pilote lit ceci (tier in {A,S})
    # routage canonique prouvé
    assert entry["promotion_status"] in ("ELIGIBLE", "BLOCKED", "UNKNOWN_FAIL_CLOSED")
    assert isinstance(entry["eligible"], bool)
    assert "substance_tier" in entry
    assert "inputs" in entry and entry["inputs"]["input_manifest"]


# --- A8 : safety = non-régression (jamais éligible, même dimensions PASS) -------
def _safety_substance(pm, tmp_path, *, slug="colonne-de-direction"):
    """substance d'une fiche sécurité-critique (détectée par slug) — score parfait,
    tous gates PASS : seul l'invariant safety doit la bloquer."""
    fm = {**FM_OK, "slug": slug}
    return pm.evaluate_tier(fm, "body", tmp_path / "p.md", tmp_path,
                            threshold=0.80, gates=_gates(), compute_score=lambda *a: 0.99)


def test_A8_safety_fiche_never_eligible_at_composition(tmp_path):
    """A8 (non-régression ADR-091) : une fiche sécurité-critique n'est JAMAIS éligible,
    même quand coverage/regression/provenance PASSENT tous. Le check SAFETY_HUMAN_REVIEW
    (POLICY_SAFETY) bloque au niveau de LA COMPOSITION — jamais contourner par code."""
    pm = _load_promote()
    dec = _load_decision()
    substance = _safety_substance(pm, tmp_path)
    assert substance["tier"] == "B"  # invariant safety dès evaluate_tier
    # toutes les autres dimensions PASSENT : seule la safety doit renverser le verdict
    d = dec.decide_promotion({
        "substance": substance,
        "coverage": {"status": "PASS", "evidence": {}},
        "regression": {"verdict": "IMPROVED", "evidence": {}},
        "provenance": {"status": "PASS", "evidence": {}},
    })
    assert d["eligible"] is False
    assert d["promotion_status"] == "BLOCKED"
    assert "SAFETY_HUMAN_REVIEW" in [r["code"] for r in d["blocking_reasons"]]


def test_A8_safety_by_declared_family_also_blocks_composition(tmp_path):
    """La détection safety par `entity_data.family` (slug non-safety) bloque aussi
    la composition — parité avec la détection par slug (aucune porte dérobée)."""
    pm = _load_promote()
    dec = _load_decision()
    fm = {**FM_OK, "slug": "piece-generique", "entity_data": {"family": "freinage"}}
    substance = pm.evaluate_tier(fm, "body", tmp_path / "p.md", tmp_path,
                                 threshold=0.80, gates=_gates(), compute_score=lambda *a: 0.99)
    d = dec.decide_promotion({"substance": substance,
                              "coverage": {"status": "PASS"},
                              "provenance": {"status": "PASS", "evidence": {}}})
    assert d["eligible"] is False
    assert "SAFETY_HUMAN_REVIEW" in [r["code"] for r in d["blocking_reasons"]]


def test_A8_safety_authorize_apply_refuses(tmp_path):
    """Bout-en-bout A8×A3-v : une fiche safety ne franchit JAMAIS la porte du DUMB
    EXECUTOR (authorize_apply refuse — APPLY_NOT_ELIGIBLE)."""
    pm = _load_promote()
    dec = _load_decision()
    cand = _write_candidate(tmp_path)
    substance = _safety_substance(pm, tmp_path)

    def fake_run(*a):
        return substance, {"status": "PASS"}, {"verdict": "NEW"}, ([], []), True

    d = dec.canonical_promotion_decision(cand, tmp_path, run_evaluators=fake_run)
    assert d["eligible"] is False
    ok, refusal = dec.authorize_apply(d, cand, tmp_path)
    assert ok is False and refusal["code"] == "APPLY_NOT_ELIGIBLE"


# The canonical target is an input even when no caller supplies baseline_path.
# No corpus or consumer is mutated here; gates are injected to isolate freshness.
def _target_fixture(tmp_path):
    candidate = _write_candidate(tmp_path, "---\nentity_type: gamme\nslug: filtre-a-huile\n---\nproposal\n")
    target = tmp_path / "wiki/gamme/filtre-a-huile.md"
    target.parent.mkdir(parents=True)
    target.write_text("---\nreview_status: deprecated\n---\nold canon\n")
    return candidate, target


@pytest.mark.parametrize('change', ['edit', 'remove', 'create'])
def test_native_target_change_during_evaluation_blocks_decision(tmp_path, change):
    dec = _load_decision()
    candidate, target = _target_fixture(tmp_path)
    if change == 'create':
        target.unlink()
    substance = _clean_substance(tmp_path)
    def runner(*args):
        if change == 'remove':
            target.unlink()
        else:
            target.write_text("---\nreview_status: deprecated\n---\nchanged canon\n")
        return substance, {"status": "PASS"}, {"verdict": "NEW"}, ([], []), True
    decision = dec.canonical_promotion_decision(candidate, tmp_path, run_evaluators=runner)
    assert decision['eligible'] is False
    assert decision['blocking_reasons'][0]['code'] == 'STALE_DURING_EVALUATION'


@pytest.mark.parametrize('change', ['edit', 'remove', 'create'])
def test_native_target_change_before_apply_refuses_stale_decision(tmp_path, change):
    dec = _load_decision()
    candidate, target = _target_fixture(tmp_path)
    if change == 'create':
        target.unlink()
    decision = _decide_with_inputs(dec, candidate, tmp_path, _clean_substance(tmp_path))
    if change == 'remove':
        target.unlink()
    else:
        target.write_text("---\nreview_status: deprecated\n---\nchanged canon\n")
    allowed, refusal = dec.authorize_apply(decision, candidate, tmp_path)
    assert allowed is False
    assert refusal['code'] == 'STALE_DECISION'


def test_native_target_is_captured_even_with_an_explicit_other_baseline(tmp_path):
    import hashlib
    dec = _load_decision()
    candidate, target = _target_fixture(tmp_path)
    baseline = tmp_path / 'previous.md'
    baseline.write_text('historical comparison fixture')
    manifest = dec.capture_input_manifest(candidate, tmp_path, None, baseline)
    entries = {e['role']: e for e in manifest['input_manifest']}
    assert entries['canon_target']['path'] == 'wiki/gamme/filtre-a-huile.md'
    assert entries['canon_target']['sha256'] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert entries['baseline']['sha256'] == hashlib.sha256(baseline.read_bytes()).hexdigest()


@pytest.mark.parametrize('frontmatter', ['slug: filtre-a-huile', 'entity_type: inconnu\nslug: x',
                                         'entity_type: gamme'])
def test_untargetable_candidate_is_refused_not_captured_without_target(tmp_path, frontmatter):
    """Sans cible canon résoluble, pas de manifeste partiel : les adapters (CLI, gap1)
    traduisent l'erreur en refus fail-closed."""
    dec = _load_decision()
    candidate = tmp_path / 'candidate.md'
    candidate.write_text(f"---\n{frontmatter}\n---\n")
    with pytest.raises(dec.PromotionInputError, match='entity_type/slug invalides'):
        dec.capture_input_manifest(candidate, tmp_path, None, None)


@pytest.mark.parametrize('engine', ['evaluation_engine_revision', 'decision_engine_revision'])
def test_engine_change_during_evaluation_blocks_immediate_decision(tmp_path, monkeypatch, engine):
    dec = _load_decision()
    candidate, _ = _target_fixture(tmp_path)
    capture = dec.capture_input_manifest
    calls = []
    def changed(*args):
        result = capture(*args)
        if calls:
            result[engine] = 'changed engine fixture'
        calls.append(1)
        return result
    monkeypatch.setattr(dec, 'capture_input_manifest', changed)
    decision = _decide_with_inputs(dec, candidate, tmp_path, _clean_substance(tmp_path))
    assert decision['eligible'] is False
    assert decision['blocking_reasons'][0]['code'] == 'STALE_DURING_EVALUATION'


@pytest.mark.parametrize('change', ['missing', 'invalid'])
@pytest.mark.parametrize('phase', ['evaluation', 'apply'])
def test_unreadable_candidate_recapture_is_a_typed_refusal(tmp_path, change, phase):
    dec = _load_decision()
    candidate, _ = _target_fixture(tmp_path)
    substance = _clean_substance(tmp_path)
    def mutate():
        if change == 'missing':
            candidate.unlink()
        else:
            candidate.write_text('invalid frontmatter fixture')
    if phase == 'evaluation':
        def runner(*args):
            mutate()
            return substance, {"status": "PASS"}, {"verdict": "NEW"}, ([], []), True
        decision = dec.canonical_promotion_decision(candidate, tmp_path, run_evaluators=runner)
        assert decision['eligible'] is False
        refusal = decision['blocking_reasons'][0]
        assert refusal['code'] == 'STALE_DURING_EVALUATION'
    else:
        decision = _decide_with_inputs(dec, candidate, tmp_path, substance)
        mutate()
        allowed, refusal = dec.authorize_apply(decision, candidate, tmp_path)
        assert allowed is False
        assert refusal['code'] == 'STALE_DECISION'
    assert 'recapture_error' in refusal['evidence']


def test_unrelated_fiche_change_does_not_invalidate_target_decision(tmp_path):
    dec = _load_decision()
    candidate, target = _target_fixture(tmp_path)
    decision = _decide_with_inputs(dec, candidate, tmp_path, _clean_substance(tmp_path))
    target.with_name('unrelated.md').write_text('unrelated fixture')
    assert dec.authorize_apply(decision, candidate, tmp_path) == (True, None)



def test_native_regression_resolver_target_is_guarded_without_baseline_override(tmp_path, monkeypatch):
    dec = _load_decision()
    candidate, target = _target_fixture(tmp_path)
    target.write_text("---\nreview_status: approved\n---\naccepted predecessor\n")
    observed = []
    substance = _clean_substance(tmp_path)
    monkeypatch.setattr(dec, 'evaluate_tier', lambda *a: substance)
    def compare(cand, baseline, root):
        observed.append(baseline)
        target.write_text("---\nreview_status: approved\n---\nconcurrent predecessor\n")
        return {"verdict": "NEUTRAL"}
    real_load = dec._load_module
    def module(name, filename):
        if filename == 'compute-confidence-score.py':
            return real_load(name, filename)
        if filename == 'compare-proposal-versions.py':
            return SimpleNamespace(compare=compare)
        if filename == 'check-coverage-map.py':
            return SimpleNamespace(_load_catalog_slugs=lambda *a: set(),
                                   _load_schema=lambda *a: {},
                                   check_fiche=lambda *a: {"status": "PASS"})
        if filename == 'quality-gates.py':
            return SimpleNamespace(load_source_catalog=lambda: {},
                                   load_raw_inventory=lambda: ({'fixture'}, {}, {}, ''),
                                   gate_source_catalog_raw_refs=lambda *a: ([], []))
        raise AssertionError(filename)
    monkeypatch.setattr(dec, '_load_module', module)
    # Real runner and native automatic baseline resolution; evaluator transports
    # are injected. This is a decision test, not a CLI overwrite authorization.
    decision = dec.canonical_promotion_decision(candidate, tmp_path, gates=[], compute_score=lambda *a: 1)
    assert observed == [target]
    assert decision['eligible'] is False
    assert decision['blocking_reasons'][0]['code'] == 'STALE_DURING_EVALUATION'


@pytest.mark.parametrize('relative_path', [
    'proposals/_coverage/a.coverage.yaml', '_meta/reality-manifest.json', 'wiki/gammes/related.md'])
def test_score_input_added_after_decision_invalidates_apply(tmp_path, relative_path):
    dec = _load_decision()
    candidate = _write_candidate(tmp_path, '---\nentity_type: gamme\nslug: a\n---\n[[related]]\n')
    decision = _decide_with_inputs(dec, candidate, tmp_path, _clean_substance(tmp_path))
    assert decision['eligible'] is True
    changed = tmp_path / relative_path
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text('changed scoring input')
    assert dec.reverify_inputs(decision, candidate, tmp_path) is not None


@pytest.mark.parametrize("engine", ["legacy", "adr088_6dim"])
@pytest.mark.parametrize("state", ["pending", "false_captured", "false_verified", "no_hash", "no_anchor", "empty_map", "missing_map"])
def test_high_score_cannot_replace_archived_claim_proof(tmp_path, monkeypatch, state, engine):
    dec, cand, raw = _proof_candidate(tmp_path, monkeypatch, state)
    monkeypatch.setenv(dec.PROMOTE_GATE_ENGINE_ENV, engine)
    monkeypatch.setattr(dec, "_compute_shadow", lambda *a: {"shadow_tier": "S", "shadow_total": 99})
    decision = dec.canonical_promotion_decision(
        cand, tmp_path, raw_root=raw, gates=_gates(), compute_score=lambda *a: 0.99)
    assert decision["evaluation"]["confidence_score"] == 0.99
    assert decision["eligible"] is False, decision
    assert "COVERAGE_STRICT_FAIL" in [r["code"] for r in decision["blocking_reasons"]]
    assert any("proof_" in str(r["evidence"]) for r in decision["blocking_reasons"])
    ok, refusal = dec.authorize_apply(decision, cand, tmp_path, raw_root=raw)
    assert ok is False
    assert cand.exists() and not (tmp_path / "wiki" / "gamme" / "filtre-a-huile.md").exists()


def test_archived_anchored_claim_remains_eligible(tmp_path, monkeypatch):
    dec, cand, raw = _proof_candidate(tmp_path, monkeypatch, "captured")
    decision = dec.canonical_promotion_decision(
        cand, tmp_path, raw_root=raw, gates=_gates(), compute_score=lambda *a: 0.99)
    assert decision["eligible"] is True, decision


def _proof_candidate(tmp_path, monkeypatch, state, *, bind_provenance=True):
    """Real coverage/provenance evaluators; isolate unrelated score and domain gates."""
    import hashlib
    import json
    import shutil
    import yaml
    dec = _load_decision()
    cand = _write_candidate(tmp_path, "---\n" + yaml.safe_dump(FM_OK) +
                            "---\n## Fonctionnement\nUne explication sourcée.\n")
    raw = tmp_path / "raw"
    (raw / "manifests").mkdir(parents=True)
    (raw / "sources").mkdir()
    archive = raw / "sources" / "proof.md"
    archive.write_text("Une explication sourcée.\n")
    digest = "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest()
    (raw / "manifests" / "source-inventory.csv").write_text(
        "manifest_id,path,sha256\nsrc-proof,sources/proof.md," + digest + "\n")
    (raw / "manifests" / "checksums.json").write_text(json.dumps({"sources/proof.md": digest}))
    schema = tmp_path / "_meta" / "schema"
    schema.mkdir()
    shutil.copyfile(SCRIPTS.parent / "_meta" / "schema" / "coverage-map.schema.json", schema / "coverage-map.schema.json")
    source = {"slug": "source_test", "type": "oem_manual", "status": "active",
              "raw_ref": {"repo": "automecanik-raw", "manifest_id": "src-proof", "expected_sha256": digest}}
    if state in {"pending", "false_captured", "false_verified"}:
        source["status"] = "to_capture"
        source["raw_ref"]["expected_sha256"] = None
    if state == "no_hash":
        source["raw_ref"].pop("expected_sha256")
    (tmp_path / "_meta" / "source-catalog.yaml").write_text(yaml.safe_dump({"sources": [source]}))
    entry = {"claim_id": "filtre-huile-test", "section": "## Fonctionnement",
             "text_anchor": "Une explication sourcée.", "source_slug": "source_test",
             "evidence_type": "oem_technical_page", "confidence": "high", "source_policy": "1_high",
             "source_status": "pending_capture" if state == "pending" else "verified" if state == "false_verified" else "captured"}
    if state == "no_anchor":
        entry.pop("text_anchor")
    coverage = tmp_path / "proposals" / "_coverage"
    coverage.mkdir()
    if state != "missing_map":
        (coverage / "filtre-a-huile.coverage.yaml").write_text(yaml.safe_dump({
            "fiche": "filtre-a-huile", "schema_version": "1.0.0",
            "coverage_entries": [] if state == "empty_map" else [entry]}))
    # Bind the real existing provenance module to this isolated fixture even on
    # the pre-fix implementation, which otherwise reads its installation root.
    original_loader = dec._load_module
    def scoped_loader(name, filename):
        module = original_loader(name, filename)
        if filename == "quality-gates.py":
            module.SOURCE_CATALOG = tmp_path / "_meta" / "source-catalog.yaml"
            module.RAW_INVENTORY = raw / "manifests" / "source-inventory.csv"
        return module
    if bind_provenance:
        monkeypatch.setattr(dec, "_load_module", scoped_loader)
    return dec, cand, raw


@pytest.mark.parametrize("state", ["missing_file", "changed_file", "inventory_without_hash"])
def test_promotion_checks_archive_bytes_not_only_declared_status(tmp_path, monkeypatch, state):
    dec, cand, raw = _proof_candidate(tmp_path, monkeypatch, "captured", bind_provenance=False)
    archive = raw / "sources" / "proof.md"
    if state == "missing_file":
        archive.unlink()
    elif state == "changed_file":
        archive.write_text("Different document, old inventory unchanged.")
    else:
        (raw / "manifests" / "source-inventory.csv").write_text(
            "manifest_id,path,sha256\nsrc-proof,sources/proof.md,\n")
    decision = dec.canonical_promotion_decision(
        cand, tmp_path, raw_root=raw, gates=_gates(), compute_score=lambda *a: 0.99)
    assert decision["eligible"] is False, decision
    assert "PROVENANCE_RAW_REF_FAIL" in [r["code"] for r in decision["blocking_reasons"]]


def test_native_proof_roots_and_archive_change_before_apply(tmp_path, monkeypatch):
    dec, cand, raw = _proof_candidate(tmp_path, monkeypatch, "captured", bind_provenance=False)
    decision = dec.canonical_promotion_decision(
        cand, tmp_path, raw_root=raw, gates=_gates(), compute_score=lambda *a: 0.99)
    assert decision["eligible"] is True, decision
    (raw / "sources" / "proof.md").write_text("Changed after decision.")
    ok, refusal = dec.authorize_apply(decision, cand, tmp_path, raw_root=raw)
    assert ok is False
    assert refusal["code"] == "STALE_DECISION"


def test_unavailable_proof_schema_fails_closed(tmp_path, monkeypatch):
    dec, cand, raw = _proof_candidate(tmp_path, monkeypatch, "captured")
    (tmp_path / "_meta" / "schema" / "coverage-map.schema.json").unlink()
    decision = dec.canonical_promotion_decision(
        cand, tmp_path, raw_root=raw, gates=_gates(), compute_score=lambda *a: 0.99)
    assert decision["eligible"] is False
    assert decision["promotion_status"] == "UNKNOWN_FAIL_CLOSED"
    assert "COVERAGE_GATE_UNAVAILABLE" in [r["code"] for r in decision["blocking_reasons"]]



def test_environment_raw_root_archive_is_in_apply_snapshot(tmp_path, monkeypatch):
    dec, cand, raw = _proof_candidate(tmp_path, monkeypatch, "captured", bind_provenance=False)
    monkeypatch.setenv("AUTOMECANIK_RAW_PATH", str(raw))
    decision = dec.canonical_promotion_decision(
        cand, tmp_path, gates=_gates(), compute_score=lambda *a: 0.99)
    assert decision["eligible"] is True, decision
    assert any(e["role"] == "raw_archive" for e in decision["inputs"]["input_manifest"])
    (raw / "sources" / "proof.md").write_text("Changed, inventory still untouched.")
    ok, refusal = dec.authorize_apply(decision, cand, tmp_path)
    assert ok is False and refusal["code"] == "STALE_DECISION"


@pytest.mark.parametrize("escape", ["parent_path", "symlink"])
def test_archive_outside_raw_never_qualifies(tmp_path, monkeypatch, escape):
    dec, cand, raw = _proof_candidate(tmp_path, monkeypatch, "captured", bind_provenance=False)
    archive = raw / "sources" / "proof.md"
    outside = tmp_path / "outside.md"
    outside.write_bytes(archive.read_bytes())
    if escape == "symlink":
        archive.unlink()
        archive.symlink_to(outside)
    else:
        inv = raw / "manifests" / "source-inventory.csv"
        inv.write_text(inv.read_text().replace("sources/proof.md", "../outside.md"))
    decision = dec.canonical_promotion_decision(
        cand, tmp_path, raw_root=raw, gates=_gates(), compute_score=lambda *a: 0.99)
    assert decision["eligible"] is False
    assert any("raw_archive_path_invalid" in str(r["evidence"]) for r in decision["blocking_reasons"])
    assert not any(e["role"] == "raw_archive" for e in decision["inputs"]["input_manifest"])


# ADR-112 (§Amendements d'ADR-033) : citations[] ancrées dans RAW, vérifiées à la promotion.
ARCHIVE_TEXT = "Une explication sourcée.\n"


def _citation(text, quote, source="source_test"):
    import hashlib
    start = text.index(quote)
    return {"source": source, "start": start, "end": start + len(quote),
            "quote_sha256": "sha256:" + hashlib.sha256(quote.encode("utf-8")).hexdigest()}


def _cite(cand, citation):
    """Réécrit le candidat avec une relation diagnostic qui porte `citation`."""
    import yaml
    relation = {"symptom_slug": "voyant_huile", "system_slug": "filtration", "cause_slug": "filtre_colmate",
                "relation_to_part": "possible_cause", "part_role": "Un filtre colmaté réduit le débit d'huile.",
                "evidence": {"confidence": "medium", "source_policy": "1_high", "reviewed": False,
                             "diagnostic_safe": False, "strength": "parfois"},
                "sources": [citation["source"]], "citations": [citation]}
    cand.write_text("---\n" + yaml.safe_dump({**FM_OK, "diagnostic_relations": [relation]}, allow_unicode=True) +
                    "---\n## Fonctionnement\nUne explication sourcée.\n", encoding="utf-8")


@pytest.mark.parametrize("anchor, code", [
    ("exact", None),
    ("wrong_quote", "citation_quote_mismatch"),
    ("out_of_range", "citation_span_out_of_range"),
])
def test_promotion_verifies_citation_anchor_against_pinned_archive(tmp_path, monkeypatch, anchor, code):
    dec, cand, raw = _proof_candidate(tmp_path, monkeypatch, "captured", bind_provenance=False)
    citation = _citation(ARCHIVE_TEXT, "explication sourcée")
    if anchor == "wrong_quote":
        citation["quote_sha256"] = "sha256:" + "0" * 64
    elif anchor == "out_of_range":
        citation["end"] = len(ARCHIVE_TEXT) + 1
    _cite(cand, citation)
    decision = dec.canonical_promotion_decision(
        cand, tmp_path, raw_root=raw, gates=_gates(), compute_score=lambda *a: 0.99)
    if code is None:
        assert decision["eligible"] is True, decision
        return
    assert decision["eligible"] is False, decision
    reasons = [r for r in decision["blocking_reasons"] if r["code"] == "PROVENANCE_RAW_REF_FAIL"]
    assert reasons and code in str(reasons[0]["evidence"]), decision


def test_cited_only_archive_is_bound_to_the_decision(tmp_path, monkeypatch):
    """Une source citée mais absente de la carte de couverture est un input du verdict :
    ses octets sont dans le manifeste, et leur changement invalide l'application."""
    import hashlib
    import yaml
    dec, cand, raw = _proof_candidate(tmp_path, monkeypatch, "captured", bind_provenance=False)
    text = "Contrôle : un filtre colmaté allume le voyant.\n"
    cited = raw / "sources" / "cited.md"
    cited.write_bytes(text.encode("utf-8"))
    digest = "sha256:" + hashlib.sha256(cited.read_bytes()).hexdigest()
    inventory = raw / "manifests" / "source-inventory.csv"
    inventory.write_text(inventory.read_text() + "src-cited,sources/cited.md," + digest + "\n")
    catalog_path = tmp_path / "_meta" / "source-catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text())
    catalog["sources"].append({"slug": "source_cited", "type": "oem_manual", "status": "active",
                               "raw_ref": {"repo": "automecanik-raw", "manifest_id": "src-cited", "expected_sha256": digest}})
    catalog_path.write_text(yaml.safe_dump(catalog))
    _cite(cand, _citation(text, "filtre colmaté allume le voyant", source="source_cited"))
    decision = dec.canonical_promotion_decision(
        cand, tmp_path, raw_root=raw, gates=_gates(), compute_score=lambda *a: 0.99)
    assert decision["eligible"] is True, decision
    assert any(e["role"] == "raw_archive" and e["path"].endswith("sources/cited.md")
               for e in decision["inputs"]["input_manifest"]), decision["inputs"]["input_manifest"]
    cited.write_text("Changé après la décision, inventaire intact.\n", encoding="utf-8")
    ok, refusal = dec.authorize_apply(decision, cand, tmp_path, raw_root=raw)
    assert ok is False and refusal["code"] == "STALE_DECISION"


# --- Safety Auto-Gate (quality-gates.md §7) : conditions composées, politique en code -
SAFETY_FM = {**FM_OK, "slug": "colonne-de-direction", "no_disputed_claims": True}
SAFETY_BODY = "## Rôle technique\n\nLa colonne transmet la rotation du volant au boîtier.\n"
SAFETY_SHADOW = {"shadow_dims": {"A": 25.0, "C": 18.0}}
# Rôles éditoriaux du catalogue de test : seul `proof` compte pour `proof_sources_min`.
SAFETY_ROLES = {"oem_workshop": "proof", "oem_manual": "proof", "normative_standard": "proof",
                "tecdoc_official": "corroboration", "brochure": "corroboration"}
# Trois sources de preuve actives, trois éditeurs : la barre est atteinte, sans marge.
SAFETY_PROOF_SOURCES = (
    {"slug": "preuve_atelier", "type": "oem_workshop", "publisher": "Constructeur A"},
    {"slug": "preuve_manuel", "type": "oem_manual", "publisher": "Constructeur B"},
    {"slug": "preuve_norme", "type": "normative_standard", "publisher": "Organisme C"},
)


# Valeur d'une source de test qui retire la clé du catalogue (pas de défaut `active`).
_NO_KEY = object()


def _catalog_source(source: dict) -> dict:
    entry = {"status": "active", "title": source["slug"],
             "raw_ref": {"repo": "automecanik-raw", "manifest_id": source["slug"],
                         "expected_sha256": "sha256:" + "0" * 64}, **source}
    return {k: v for k, v in entry.items() if v is not _NO_KEY}


def _proof_entry(slug: str) -> dict:
    return {"claim_id": f"preuve-{slug}", "section": "## Rôle technique", "source_slug": slug,
            "evidence_type": "oem_workshop_excerpt", "confidence": "high",
            "source_policy": "1_high", "source_status": "captured"}


# Aucune plage déclarée : aucune valeur ne peut être `numeric_verified`.
SAFETY_RANGES = {"schema_version": "1.0.0", "families": {}}


def _safety_wiki(tmp_path, *, entries=(), body=SAFETY_BODY, sources=SAFETY_PROOF_SOURCES,
                 roles=SAFETY_ROLES, cited=None, ranges=SAFETY_RANGES):
    """Mini wiki : la fiche, le catalogue, les plages chiffrées (`ranges=None` : absentes) et
    la coverage-map (clé = nom de fichier). La coverage-map cite les sources `cited` (par
    défaut : toutes), puis les `entries` du test."""
    import yaml
    target = tmp_path / "proposals" / "colonne-de-direction.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    (tmp_path / "_meta").mkdir(parents=True, exist_ok=True)
    if ranges is not None:
        (tmp_path / "_meta" / "numeric-plausibility.yaml").write_text(
            yaml.safe_dump(ranges, allow_unicode=True), encoding="utf-8")
    (tmp_path / "_meta" / "source-catalog.yaml").write_text(yaml.safe_dump({
        "source_type_editorial_role": roles,
        "sources": [_catalog_source(s) for s in sources]}, allow_unicode=True), encoding="utf-8")
    cited = [s["slug"] for s in sources] if cited is None else list(cited)
    cov = tmp_path / "proposals" / "_coverage" / "colonne-de-direction.coverage.yaml"
    cov.parent.mkdir(parents=True, exist_ok=True)
    cov.write_text(yaml.safe_dump({"fiche": "colonne-de-direction",
                                   "coverage_entries": [_proof_entry(c) for c in cited] + list(entries)},
                                  allow_unicode=True), encoding="utf-8")
    return target


def _local(dec, tmp_path, *, fm=SAFETY_FM, body=SAFETY_BODY, shadow=SAFETY_SHADOW,
           gate_results=None, score=0.9, entries=(), **wiki):
    target = _safety_wiki(tmp_path, entries=entries, body=body, **wiki)
    if gate_results is None:
        gate_results = [(n, _gate_result("pass")) for n in dec.CANONICAL_GATE_NAMES]
    return dec._safety_local_conditions(fm, body, target, tmp_path, shadow, gate_results, score)


def test_safety_canonical_gate_names_are_the_loaded_gates():
    """`no_quality_gate_fail` exige exactement les 5 contrôles de `_load_gates` : la liste
    attendue ne peut pas dériver de celle réellement exécutée."""
    dec = _load_decision()
    assert tuple(n for n, _ in dec._load_gates()) == dec.CANONICAL_GATE_NAMES


def test_safety_local_conditions_all_proven_on_a_clean_fiche(tmp_path):
    dec = _load_decision()
    local = _local(dec, tmp_path)
    assert local["conditions"] and all(v is True for v in local["conditions"].values()), local


# Relation de la forme qu'exige l'export diagnostic : sa projection est contrôlée elle aussi.
_RELATION = {"symptom_slug": "volant_dur", "system_slug": "direction",
             "relation_to_part": "possible_cause",
             "part_role": "Une colonne grippée durcit la direction au braquage.",
             "evidence": {"confidence": "medium", "source_policy": "2_medium_concordant",
                          "reviewed": False, "diagnostic_safe": False},
             "sources": ["preuve_atelier"]}
_RELATION_SAFE = {**_RELATION, "evidence": {**_RELATION["evidence"], "diagnostic_safe": True}}
_RULE_MANUAL = {"rule": "contrôle visuel", "evidence": {
    "confidence": "low", "source_policy": "manual_review",
    "reviewed": False, "diagnostic_safe": False}}


@pytest.mark.parametrize("condition, overrides", [
    ("dim_A_floor", {"shadow": {"shadow_dims": {"A": 21.9, "C": 18.0}}}),
    ("dim_C_floor", {"shadow": {"shadow_dims": {"A": 25.0, "C": None}}}),
    ("dim_C_floor", {"shadow": {"shadow_dims": {"A": 25.0, "C": True}}}),
    ("no_quality_gate_fail", {"gate_results": "risk_fails"}),
    ("no_quality_gate_fail", {"gate_results": "contradiction_missing"}),
    ("numeric_exactitude_verified",
     {"body": "## Rôle technique\n\nSerrer la colonne à 25 Nm.\n"}),
    ("no_disputed_claims", {"fm": {**FM_OK, "slug": "colonne-de-direction"}}),
    ("no_disputed_claims", {"fm": {**SAFETY_FM, "no_disputed_claims": "yes"}}),
    ("diagnostic_live_authority_not_claimed",
     {"fm": {**SAFETY_FM, "diagnostic_relations": [_RELATION_SAFE]}}),
    ("no_manual_review_policy", {"fm": {**SAFETY_FM, "safety_rules": [_RULE_MANUAL]}}),
    ("no_manual_review_policy", {"entries": [{
        "claim_id": "c1", "section": "## Rôle technique",
        "text_anchor": "La colonne transmet la rotation", "source_slug": "src_x",
        "source_policy": "manual_review", "source_status": "captured"}]}),
    # Même éditeur à la casse et aux espaces près : deux éditeurs distincts seulement.
    ("proof_sources_min", {"sources": SAFETY_PROOF_SOURCES[:2] + (
        {"slug": "preuve_norme", "type": "normative_standard", "publisher": " constructeur  a "},)}),
    # Forme Unicode (NFC/NFD), ß/SS, espace insécable : un seul éditeur à chaque fois.
    ("proof_sources_min", {"sources": (
        {**SAFETY_PROOF_SOURCES[0], "publisher": "Société A"}, SAFETY_PROOF_SOURCES[1],
        {**SAFETY_PROOF_SOURCES[2], "publisher": "Société A"})}),
    ("proof_sources_min", {"sources": (
        {**SAFETY_PROOF_SOURCES[0], "publisher": "Straße A"}, SAFETY_PROOF_SOURCES[1],
        {**SAFETY_PROOF_SOURCES[2], "publisher": "STRASSE A"})}),
    # Forme canonique dont la décomposition réordonne les marques (ypogegrammeni) : un éditeur.
    ("proof_sources_min", {"sources": (
        {**SAFETY_PROOF_SOURCES[0], "publisher": "ᾄ A"}, SAFETY_PROOF_SOURCES[1],
        {**SAFETY_PROOF_SOURCES[2], "publisher": "ᾄ A"})}),
    ("proof_sources_min", {"sources": SAFETY_PROOF_SOURCES[:2] + (
        {**SAFETY_PROOF_SOURCES[2], "publisher": "Constructeur\N{NO-BREAK SPACE}A"},)}),
    # Lettre de compatibilité (ℂ) : majuscule seulement une fois décomposée, puis repliée.
    ("proof_sources_min", {"sources": SAFETY_PROOF_SOURCES[:2] + (
        {**SAFETY_PROOF_SOURCES[2], "publisher": "\u2102onstructeur A"},)}),
    # Éditeur sans aucun caractère alphanumérique : absent, il ne compte pas.
    ("proof_sources_min", {"sources": SAFETY_PROOF_SOURCES[:2] + (
        {**SAFETY_PROOF_SOURCES[2], "publisher": " — "},)}),
    # Corroboration (TecDoc) : jamais une preuve, même `high`.
    ("proof_sources_min", {"sources": SAFETY_PROOF_SOURCES[:2] + (
        {"slug": "preuve_norme", "type": "tecdoc_official", "publisher": "Organisme C"},)}),
    # Une source ne compte qu'`active`, exactement : ni autre casse, ni espace, ni défaut.
    *[("proof_sources_min", {"sources": SAFETY_PROOF_SOURCES[:2] + (
        {**SAFETY_PROOF_SOURCES[2], "status": status},)})
      for status in ("to_capture", "Active", " active", "active ", None, _NO_KEY)],
    # Un type ne prouve qu'au rôle `proof`, exactement : ni autre casse, ni espace.
    *[("proof_sources_min", {"roles": {**SAFETY_ROLES, "normative_standard": role}})
      for role in ("Proof", " proof", "proof ")],
    ("proof_sources_min", {"sources": SAFETY_PROOF_SOURCES[:2] + (
        {"slug": "preuve_norme", "type": "normative_standard"},)}),
    # Cataloguée mais non citée par la fiche : ne compte pas.
    ("proof_sources_min", {"cited": ["preuve_atelier", "preuve_manuel"]}),
])
def test_safety_each_local_condition_blocks_alone(tmp_path, condition, overrides):
    """Chaque condition est isolée : la casser ne fait tomber qu'elle."""
    dec = _load_decision()
    kwargs = dict(overrides)
    if kwargs.get("gate_results") == "risk_fails":
        kwargs["gate_results"] = [(n, _gate_result("fail" if n == "risk" else "pass"))
                                  for n in dec.CANONICAL_GATE_NAMES]
    elif kwargs.get("gate_results") == "contradiction_missing":
        kwargs["gate_results"] = [(n, _gate_result("pass"))
                                  for n in dec.CANONICAL_GATE_NAMES if n != "contradiction"]
    conditions = _local(dec, tmp_path, **kwargs)["conditions"]
    assert conditions[condition] is False
    assert [k for k, v in conditions.items() if v is not True] == [condition], conditions


def test_safety_indeterminable_shadow_fails_both_floors_and_says_why(tmp_path):
    dec = _load_decision()
    local = _local(dec, tmp_path, shadow={"shadow_error": "manifest absent"})
    assert [k for k, v in local["conditions"].items() if v is not True] == ["dim_A_floor",
                                                                            "dim_C_floor"]
    assert local["details"]["dim_A_floor"]["shadow_error"] == "manifest absent"


def test_safety_malformed_evidence_lists_fail_closed_with_reported_error(tmp_path):
    dec = _load_decision()
    local = _local(dec, tmp_path, fm={**SAFETY_FM, "diagnostic_relations": "pas une liste"})
    for name in ("diagnostic_live_authority_not_claimed", "no_manual_review_policy"):
        assert local["conditions"][name] is False
        assert "diagnostic_relations_malformed" in local["details"][name]["error"]


def test_safety_numeric_anchored_on_captured_source_still_blocks_on_proposed_range(tmp_path):
    """Valeur ancrée sur une source captée : la provenance est prouvée, mais aucune plage
    `validated` n'existe → jamais `numeric_verified` (pas de valeur dimensionnée auto)."""
    dec = _load_decision()
    body = "## Montage\n\nIl faut serrer à 25 Nm la vis de colonne.\n"
    target = _safety_wiki(tmp_path, body=body, entries=[{
        "claim_id": "c1", "section": "## Montage", "text_anchor": "serrer à 25 Nm",
        "source_slug": "src_x", "source_status": "captured"}])
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert result["anchored_claims"] == 1
    assert result["verified"] is False
    assert not any("numeric_source_not_captured" in v for v in result["sample"]), result


@pytest.mark.parametrize("where", [
    "## Montage\n\nIl faut serrer à 25 Nm la vis.\n",          # prose non ancrée
    "## Montage 25 Nm\n\nIl faut serrer la vis.\n",            # titre
    "## Montage\n\n```\n25 Nm\n```\n",                          # bloc de code
    "## Montage\n\nIl faut serrer ![25 Nm](x.png) la vis.\n",  # alt d'image
])
def test_safety_numeric_unanchored_rendered_value_is_unsourced(tmp_path, where):
    """Toute valeur du texte rendu hors ancre est non sourcée, où qu'elle se trouve."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path, body=where)
    result = dec._safety_numeric_exactitude(SAFETY_FM, where, target, tmp_path)
    assert result["verified"] is False
    assert any("numeric_source_not_captured" in v for v in result["sample"]), result


@pytest.mark.parametrize("where, raw", [
    ('Voir [la notice](https://ex.org/n "jeu de 22 mm").', "22 mm"),        # titre de lien
    ("Voir [la notice](https://ex.org/n 'jeu de 22 mm').", "22 mm"),
    ("Voir [la notice](https://ex.org/n (jeu de 22 mm)).", "22 mm"),
    ('![schéma](s.png "jeu de 22 mm")', "22 mm"),                            # titre d'image
    ('Voir [la notice][n].\n\n[n]: https://ex.org/n "jeu de 22 mm"', "22 mm"),  # définition de référence
    ('Texte.\n\n[n]: https://ex.org/n "jeu de 22 mm"', "22 mm"),             # … jamais utilisée
    ('> [n]: https://ex.org/n "jeu de 22 mm"\n\nVoir [n].', "22 mm"),        # … dans une citation
    ('- [n]: https://ex.org/n "jeu de 22 mm"\n\nVoir [n].', "22 mm"),        # … dans une liste
    ("Texte.\n\n[//]: # (Jeu relevé : 22 mm)", "22 mm"),                     # commentaire Markdown
    ("```22 mm\nx\n```", "22 mm"),                                           # info de bloc de code
    ("Voir [la notice](https://ex.org/jeu-22mm).", "22mm"),                   # URL de lien
    ("Voir [la notice](https://ex.org/n?c=jeu%20de%2022%20mm).", "22 mm"),    # … encodée
    ("Voir [la notice](https://ex.org/%32%32%20mm).", "22 mm"),
    ('Voir <a title="jeu de 22&#32;mm">ici</a>.', "22 mm"),                   # attribut HTML, entité
])
def test_safety_numeric_body_text_published_but_not_rendered_is_read_as_written(tmp_path, where, raw):
    """Titres, URL, définitions de référence, commentaires, info de bloc de code : absents du
    rendu, publiés dans le fichier canon. Lus tels qu'écrits, aucun n'échappe au contrôle."""
    dec = _load_decision()
    body = f"## Montage\n\n{where}\n"
    target = _safety_wiki(tmp_path, body=body)
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert result["verified"] is False
    assert f"corps (écrite) numeric_source_not_captured: {raw!r}" in _violations_of(result, "corps"), result
    assert _violations_of(result, "corps") == result["sample"], result


@pytest.mark.parametrize("where", [
    "Voir [la fiche](https://fr.wikipedia.org/wiki/Filtre_à_air).",   # destination non ASCII
    "Voir [la fiche](https://x.fr/1ère-monte).",
    "Voir [la fiche](https://x.fr/m%C3%A9thode).",                     # échappements écrits
    "Voir https://x.fr/m%C3%A9thode.",                                 # URL nue dans la prose
    "Voir [la fiche][n].\n\n[n]: https://x.fr/m%C3%A9thode",          # définition de référence
])
def test_safety_numeric_body_url_escapes_raise_no_false_positive(tmp_path, where):
    """Une destination est lue telle qu'écrite, échappements d'URL décodés : ni la forme que
    l'analyseur ré-encode (`é` → `%C3%A9`), ni un octet échappé ne passent pour une valeur."""
    dec = _load_decision()
    body = f"## Montage\n\n{where}\n"
    target = _safety_wiki(tmp_path, body=body)
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert result["verified"] is True, result


@pytest.mark.parametrize("text, raw", [
    ("Jeu de 25\u200bmm.", "25mm"),                                # espace sans chasse (Cf)
    ("Chauffer à 120 \u2103.", "120 °C"),                          # ℃ : compatibilité de °C
    ("Jeu de \uff12\uff15 \uff4d\uff4d.", "25 mm"),               # pleine chasse
    ("Jeu de 25\u034fmm.", "25mm"),                                # ignorable par défaut, hors Cf
    ("Jeu de 25\u3164mm.", "25mm"),                                # remplisseur hangûl (lettre)
    ("Section de 2,5 \u339f.", "2,5 mm²"),                         # ㎟ : l'exposant de l'unité reste un exposant
    ("Couple de 1,2\u00b710\u00b2 Nm.", "102 Nm"),                    # tout autre exposant : lu en chiffre (NFKC)
    ("Jeu de \u00b2\u2078 mm.", "28 mm"),
    ("Couple de \u2081\u2082\u2080 Nm.", "120 Nm"),                    # indices
    ("Couple de 120 \u1d3a\u1d50.", "120 Nm"),                         # unité en exposant
    ("Jeu de 25\ufffbmm.", "25mm"),                                # format (Cf), hors des espaces sans chasse
    ("Jeu de 25\U000e0100mm.", "25mm"),                            # sélecteur de variante (ignorable par défaut)
    ("Jeu de 25\u180bmm.", "25mm"),
])
def test_safety_numeric_body_value_is_read_in_compatibility_form(tmp_path, text, raw):
    """Caractère de format ou de compatibilité : la valeur est lue telle que le lecteur la voit."""
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    target = _safety_wiki(tmp_path, body=body)
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert _violations_of(result, "corps") == [
        f"corps ({form}) numeric_source_not_captured: {raw!r}" for form in ("rendue", "sans balisage")], result


@pytest.mark.parametrize("text, forms, unmodelled", [
    # Destination invalide : rendu tel qu'écrit, le balisage sépare la valeur de son unité
    ("Jeu de [25](x y) mm.", ["sans balisage"], []),
    # Alt d'image : lu à sa place dans le texte rendu ; l'image, que le contrôle ne modélise pas,
    # est relevée en plus
    ("Jeu de ![25](i.png) mm.", ["rendue", "sans balisage"], [("image", "i.png")]),
    # Nombre en code, unité dans un élément HTML : seul le rendu les réunit ; l'élément, que le
    # contrôle ne modélise pas, est relevé en plus
    ("Jeu de `25`<span> mm</span>.", ["rendue", "sans balisage"], [("raw_html", "<span"), ("raw_html", "</span")]),
])
def test_safety_numeric_body_value_split_by_markup_is_read(tmp_path, text, forms, unmodelled):
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    target = _safety_wiki(tmp_path, body=body)
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert _violations_of(result, "corps") == [
        f"corps ({form}) numeric_source_not_captured: '25 mm'" for form in forms] + [
        f"corps unmodelled_{kind}: {marker!r}" for kind, marker in unmodelled], result


@pytest.mark.parametrize("text, unmodelled", [
    # `$` : la formule n'est pas lue, elle est relevée ; la commande inconnue qui colle la valeur à
    # son unité reste lue sans balisage
    ("Serrer à $120\\Nm$.", [("formula", "$")]),
    # … sans formule : affichée telle qu'écrite, seule la lecture sans balisage relève
    ("Serrer à 120\\Nm.", []),
    # `$` monétaire : relevé aussi, sans que la valeur entre deux prix cesse d'être lue
    ("Kit à 30 $ ; serrage 120\\Nm ; main-d'œuvre 50 $.", [("formula", "$")]),
    ("```math\n120\\Nm\n```", [("rendered_fence", "math")]),
])
def test_safety_numeric_body_unmodelled_formula_never_hides_the_plain_reading(tmp_path, text, unmodelled):
    """Une formule n'est jamais lue en formule : elle est relevée, et la lecture sans balisage du
    même texte reste faite."""
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    target = _safety_wiki(tmp_path, body=body)
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert _violations_of(result, "corps") == [
        "corps (sans balisage) numeric_source_not_captured: '120Nm'"] + [
        f"corps unmodelled_{kind}: {marker!r}" for kind, marker in unmodelled], result


@pytest.mark.parametrize("separator, unmodelled", [
    ("\u2028", []),
    ("\u0085", [("control_character", "U+0085")]),
    ("\u000c", [("control_character", "U+000C")]),
])
def test_safety_numeric_body_line_separator_does_not_shift_the_lines_read(tmp_path, separator, unmodelled):
    """Une note de bas de page (GFM) affiche `25Nm` : la note est relevée et sa ligne lue, même
    après un caractère que `splitlines` compte comme une fin de ligne et l'analyseur non."""
    dec = _load_decision()
    body = f"## Montage\n\nVoir{separator}la note[^1].\n\n[^1]: 25**Nm**\nTexte suivant.\n"
    target = _safety_wiki(tmp_path, body=body)
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert _violations_of(result, "corps") == [
        "corps (sans balisage) numeric_source_not_captured: '25Nm'", "corps unmodelled_footnote: '[^1]'"] + [
        f"corps unmodelled_{kind}: {marker!r}" for kind, marker in unmodelled], result


@pytest.mark.parametrize("text, images", [
    ("Voir [la note](<https://e.x/tarage :%45 bar>).", []),
    # … l'image, relevée dans chaque décodage, sous sa destination normalisée par l'analyseur
    ("Voir ![schéma](<img/tarage :%45 bar.png>).", ["img/tarage%20:%45%20bar.png", "img/tarage%20:E%20bar.png"]),
])
def test_safety_numeric_body_link_destination_is_read_as_written(tmp_path, text, images):
    """Une destination de lien ou d'image est lue telle qu'écrite (`%45` affiché tel quel), pas
    seulement aux échappements décodés (`E`) : le décodage s'ajoute à la lecture écrite."""
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    target = _safety_wiki(tmp_path, body=body)
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert _violations_of(result, "corps") == ["corps (écrite) numeric_source_not_captured: '45 bar'"] + [
        f"corps unmodelled_image: {src!r}" for src in images], result


def _captured_anchor(section: str, anchor: str) -> dict:
    return {"claim_id": "c1", "section": section, "text_anchor": anchor,
            "source_slug": "preuve_atelier", "source_status": "captured"}


def test_safety_numeric_anchor_masks_only_its_own_block(tmp_path):
    """L'extrait ancré est classé sous sa source puis retiré dans son bloc et les formes qui en
    dérivent, pas dans un autre bloc qui affiche le même texte : là, la valeur reste non
    sourcée."""
    dec = _load_decision()
    body = "## Montage\n\nJeu de 25 mm à l'arrêt.\n\n## Contrôle\n\nJeu de 25&nbsp;mm à l'arrêt.\n"
    target = _safety_wiki(tmp_path, body=body, entries=[_captured_anchor("## Montage", "Jeu de 25 mm")])
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert (result["anchored_claims"], result["anchors_unmasked"]) == (1, [])
    assert _violations_of(result, "corps") == [
        "corps (rendue) numeric_context_missing: '25 mm'",
        "corps (rendue) numeric_source_not_captured: '25 mm'",
        "corps (sans balisage) numeric_context_missing: '25 mm'",
        "corps (sans balisage) numeric_source_not_captured: '25 mm'"], result


def test_safety_numeric_anchor_is_masked_in_its_markup_blind_form(tmp_path):
    """L'extrait ancré se lit dans le bloc sans balisage sous cette forme : un `_` de référence
    y disparaît comme dans le bloc. Il y est classé sous sa source, jamais non sourcé."""
    dec = _load_decision()
    body = "## Montage\n\nJeu de 25 mm (cote_A).\n"
    target = _safety_wiki(tmp_path, body=body,
                          entries=[_captured_anchor("## Montage", "Jeu de 25 mm (cote_A)")])
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert (result["anchored_claims"], result["anchors_unmasked"]) == (1, [])
    assert _violations_of(result, "corps") == [
        f"corps ({form}) numeric_context_missing: '25 mm'" for form in ("rendue", "sans balisage")], result


@pytest.mark.parametrize("text, status, anchor, expected", [
    # Espace sans chasse : le bloc ancrable lit « 50 Nm », le lecteur voit « 450 Nm ».
    ("Sur l'étrier avant, la vis de guide se bloque à 4\u200b50 Nm.", "captured",
     "Sur l'étrier avant, la vis de guide se bloque à 4\u200b50 Nm",
     ["corps (rendue) numeric_ambiguous: '50 Nm'", "corps (rendue) numeric_ambiguous: '450 Nm'",
      "corps (sans balisage) numeric_ambiguous: '450 Nm'"]),
    # Unité de compatibilité (pleine chasse, symbole carré), ancrée sans preuve.
    ("Sur l'étrier avant, la vis de guide se bloque à 450 \uff2e\uff4d.", "pending_capture",
     "la vis de guide se bloque à 450 \uff2e\uff4d",
     [f"corps ({form}) numeric_source_not_captured: '450 Nm'" for form in ("rendue", "sans balisage")]),
    ("Sur l'étrier avant, la garniture descend sous 2 \u339c.", "pending_capture",
     "la garniture descend sous 2 \u339c",
     [f"corps ({form}) numeric_source_not_captured: '2 mm'" for form in ("rendue", "sans balisage")]),
    # Marque, touche ou guillemet entre le nombre et l'unité : l'extrait est lu aussi en squelette,
    # sous le statut de sa source, la valeur telle que le lecteur la voit
    ("Vis de roue avant 400\N{COMBINING ACUTE ACCENT} Nm selon atelier.", "captured",
     "Vis de roue avant 400\N{COMBINING ACUTE ACCENT} Nm selon atelier",
     ["corps (rendue squelette) numeric_ambiguous: '400 Nm'"]),
    ("Vis de roue avant 4\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP} Nm selon atelier.",
     "captured",
     "Vis de roue avant 4\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP} Nm selon atelier",
     ["corps (rendue squelette) numeric_ambiguous: '4 Nm'"]),
    ('Vis de roue avant 25"Nm selon atelier.', "captured", 'Vis de roue avant 25"Nm selon atelier',
     ["corps (rendue squelette) numeric_ambiguous: '25Nm'"]),
    # `×` qui n'est pas entre deux nombres : retiré comme une marque
    ("Vis de roue avant 25×Nm selon atelier.", "captured", "Vis de roue avant 25×Nm selon atelier",
     ["corps (rendue squelette) numeric_ambiguous: '25Nm'"]),
    # Crochets échappés : lu sans balisage, l'extrait affiche `2"5 Nm`, que le squelette lit `25 Nm`
    ('Vis de roue avant 2"\\[5\\](x) Nm selon atelier.', "captured",
     'Vis de roue avant 2"[5](x) Nm selon atelier',
     ["corps (sans balisage) numeric_ambiguous: '5 Nm'",
      "corps (sans balisage squelette) numeric_ambiguous: '25 Nm'"]),
])
def test_safety_numeric_anchored_excerpt_is_read_in_each_form(tmp_path, text, status, anchor, expected):
    """L'extrait ancré est classé sous sa source dans chaque forme où il se lit, pas seulement
    dans son bloc ancrable : un caractère invisible ou de compatibilité ne cache pas la valeur
    que voit le lecteur."""
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    target = _safety_wiki(tmp_path, body=body,
                          entries=[{**_captured_anchor("## Montage", anchor), "source_status": status}])
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert (result["anchored_claims"], result["anchors_unmasked"]) == (1, []), result
    assert _violations_of(result, "corps") == expected, result


# Plages validées de la famille de la fiche de test : une valeur qui y entre, ancrée sur deux
# sources captées concordantes, est `numeric_verified`.
_RANGES_DIRECTION_VALIDATED = {"schema_version": "1.0.0", "families": {"direction": {
    "min_thickness": {"unit": "mm", "min": 5.0, "max": 60.0, "critical": True,
                      "always_ref_specific": True, "status": "validated"},
    "torque": {"unit": "Nm", "min": 5.0, "max": 400.0, "critical": True, "status": "validated"}}}}


@pytest.mark.parametrize("excerpts", [
    ("Disque 340×30 : épaisseur minimale 27 mm",
     "Disque 340×30 : épaisseur minimale 27 mm selon atelier"),
    ("Disque 340 × 30 : épaisseur minimale 27 mm",
     "Disque 340 × 30 : épaisseur minimale 27 mm selon atelier"),
    ("Vis de colonne M8×1,25 : couple 22 Nm", "Vis de colonne M8×1,25 : serrage 22 Nm"),
    ("Vis de colonne M8 × 1,25 : couple 22 Nm", "Vis de colonne M8 × 1,25 : serrage 22 Nm"),
])
def test_safety_numeric_anchored_dimension_keeps_its_times_sign_in_skeleton(tmp_path, excerpts):
    """Le `×` d'une cote ou d'un filetage, entre deux nombres, n'est pas du balisage : la lecture
    squelette d'un extrait ancré le garde, et y lit la référence précise et le contexte de la
    valeur comme les autres lectures. Deux sources captées concordantes, plage validée : la
    valeur est vérifiée dans chaque forme."""
    dec = _load_decision()
    body = "## Montage\n\n" + "\n\n".join(f"{e}." for e in excerpts) + "\n"
    entries = [{**_captured_anchor("## Montage", e), "claim_id": f"c{i}", "source_slug": slug}
               for i, (e, slug) in enumerate(zip(excerpts, ("preuve_atelier", "preuve_manuel")))]
    target = _safety_wiki(tmp_path, body=body, entries=entries, ranges=_RANGES_DIRECTION_VALIDATED)
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert (result["anchored_claims"], result["anchors_unmasked"]) == (2, []), result
    assert (result["verified"], result["violations_total"]) == (True, 0), result


def test_safety_numeric_anchor_that_splits_a_derived_value_leaves_it_unsourced(tmp_path):
    """Texte alternatif en place : l'ancre « 50 Nm » coupe « 450 Nm » dans les formes dérivées.
    Elle n'y est pas retirée, la valeur vue reste non sourcée, et l'ancre est rapportée."""
    dec = _load_decision()
    body = "## Montage\n\nLa vis se bloque à ![4](i.png)50 Nm sur l'étrier avant.\n"
    anchor = "50 Nm sur l'étrier avant"
    target = _safety_wiki(tmp_path, body=body, entries=[_captured_anchor("## Montage", anchor)])
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert result["anchored_claims"] == 1
    assert result["anchors_unmasked"] == [{"anchor": anchor, "form": form, "reason": "value_split"}
                                          for form in ("rendue", "sans balisage")], result
    assert _violations_of(result, "corps") == [
        "corps (rendue) numeric_ambiguous: '50 Nm'",
        "corps (rendue) numeric_source_not_captured: '450 Nm'",
        "corps (sans balisage) numeric_source_not_captured: '450 Nm'",
        "corps unmodelled_image: 'i.png'"], result


def test_safety_numeric_anchor_absent_from_a_derived_form_leaves_its_value_unsourced(tmp_path):
    """Texte alternatif en place : l'ancre, écrite sans l'image, ne se lit plus dans les formes
    dérivées (« Serrer repère à 25 Nm »). Elle n'y est pas retirée, la valeur vue reste non
    sourcée, et l'ancre est rapportée absente."""
    dec = _load_decision()
    body = "## Montage\n\nSerrer ![repère](i.png) à 25 Nm sur le pivot.\n"
    anchor = "Serrer à 25 Nm sur le pivot"
    target = _safety_wiki(tmp_path, body=body, entries=[_captured_anchor("## Montage", anchor)])
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert result["anchored_claims"] == 1
    assert result["anchors_unmasked"] == [{"anchor": anchor, "form": form, "reason": "absent"}
                                          for form in ("rendue", "sans balisage")], result
    assert _violations_of(result, "corps") == [
        "corps (rendue) numeric_context_missing: '25 Nm'"] + _unsourced("25 Nm") + [
        "corps unmodelled_image: 'i.png'"], result


def _unsourced(value, forms=("rendue", "sans balisage")):
    return [f"corps ({form}) numeric_source_not_captured: {value!r}" for form in forms]


@pytest.mark.parametrize("text, anchor, expected", [
    # Coupe à 80 caractères (`gen_coverage_map`) : le nombre séparé de son unité.
    ("Sur ce montage, remplacer les plaquettes avant dès que leur garniture atteint 2 mm "
     "d'épaisseur restante.",
     "Sur ce montage, remplacer les plaquettes avant dès que leur garniture atteint 2 ",
     _unsourced("2 mm")),
    ("Les vis de l'étrier se bloquent à 25 Nm sur le pivot.", "se bloquent à 2", _unsourced("25 Nm")),
    ("Les vis de l'étrier se bloquent à 25 Nm sur le pivot.", "Nm sur le pivot", _unsourced("25 Nm")),
    ("La section du câble est de 2,5 mm² sur ce faisceau.", "est de 2,5 mm", _unsourced("2,5 mm²")),
    # Marque d'approximation hors de l'ancre.
    ("Le couple est d'environ 25 Nm sur le pivot.", "25 Nm sur le pivot", _unsourced("25 Nm")),
    # Coupe visible seulement à la compatibilité près : « 4\u200b50 » se lit 450.
    ("La vis se bloque à 4\u200b50 Nm sur le pivot.", "50 Nm sur le pivot",
     _unsourced("50 Nm", ("rendue",)) + _unsourced("450 Nm")),
    # Coupe visible seulement en squelette : guillemet entre le nombre et son unité, ou entre
    # deux de ses chiffres ; la valeur vue y est rapportée une fois.
    ("Les vis de l'étrier se bloquent à 25\"Nm sur le pivot.", 'se bloquent à 25"',
     ["corps (rendue squelette) numeric_source_not_captured: '25Nm'"]),
    ("Les vis de l'étrier se bloquent à 2\"5 Nm sur le pivot.", 'se bloquent à 2"',
     _unsourced("5 Nm") + ["corps (rendue squelette) numeric_source_not_captured: '25 Nm'"]),
])
def test_safety_numeric_anchor_that_splits_a_value_is_not_masked(tmp_path, text, anchor, expected):
    """Une ancre dont la borne coupe une valeur (nombre, unité, exposant, marque
    d'approximation) ne porte pas sa source : son bloc n'est pas retiré, la valeur entière reste
    non sourcée, et l'ancre est rapportée."""
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    target = _safety_wiki(tmp_path, body=body, entries=[_captured_anchor("## Montage", anchor)])
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert result["anchored_claims"] == 0
    assert result["anchors_unmasked"] == [{"anchor": anchor, "form": "rendue", "reason": "value_split"}]
    assert _violations_of(result, "corps") == expected, result


_PIVOT = "Serrer à 25 Nm sur le pivot."


@pytest.mark.parametrize("paragraphs, anchor, anchored, unmasked, expected", [
    # Même texte dans un second bloc de la section : seul le premier porte la source.
    ([_PIVOT, _PIVOT], "Serrer à 25 Nm sur le pivot", 1, [],
     [f"corps ({form}) {code}: '25 Nm'" for form in ("rendue", "sans balisage")
      for code in ("numeric_context_missing", "numeric_source_not_captured")]),
    # Le premier bloc qui la contient coupe une valeur : l'ancre n'est pas cherchée plus loin.
    (["Serrer à 125 Nm sur le pivot.", _PIVOT], "25 Nm sur le pivot", 0, ["value_split"],
     [v for form in ("rendue", "sans balisage")
      for v in _unsourced("125 Nm", (form,)) + _unsourced("25 Nm", (form,))]),
])
def test_safety_numeric_anchor_is_located_in_one_block_only(tmp_path, paragraphs, anchor, anchored,
                                                            unmasked, expected):
    """L'extrait ancré est localisé dans le premier bloc ancrable de sa section qui le contient,
    et seulement là : un autre bloc qui affiche le même texte garde sa valeur non sourcée, que
    l'ancre ait été retirée de ce premier bloc ou non."""
    dec = _load_decision()
    body = "## Montage\n\n" + "\n\n".join(paragraphs) + "\n"
    target = _safety_wiki(tmp_path, body=body, entries=[_captured_anchor("## Montage", anchor)])
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert result["anchored_claims"] == anchored
    assert result["anchors_unmasked"] == [{"anchor": anchor, "form": "rendue", "reason": reason}
                                          for reason in unmasked]
    assert _violations_of(result, "corps") == expected, result


@pytest.mark.parametrize("anchor", [
    "serrer à 25 Nm sur le pivot",              # casse différente du bloc
    "Serrer à 25 Nm sur le pivot",        # « à » décomposé (NFD), le bloc est en NFC
])
def test_safety_numeric_anchor_is_located_like_the_coverage_map_locates_it(tmp_path, anchor):
    """L'ancre se localise comme `check-coverage-map` l'accepte (NFC, casse ignorée), dans son
    bloc comme dans chaque forme qui en dérive : un extrait que la coverage-map valide porte sa
    source."""
    dec = _load_decision()
    body = f"## Montage\n\n{_PIVOT}\n"
    target = _safety_wiki(tmp_path, body=body, entries=[_captured_anchor("## Montage", anchor)])
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert (result["anchored_claims"], result["anchors_unmasked"]) == (1, []), result
    assert _violations_of(result, "corps") == [
        f"corps ({form}) numeric_context_missing: '25 Nm'" for form in ("rendue", "sans balisage")], result


def test_safety_numeric_masked_anchor_bounds_the_clause(tmp_path):
    """L'extrait retiré borne la clause : le texte de part et d'autre ne s'y rejoint pas (la
    marque d'approximation ne passe pas à la valeur, que le bloc entier ne lit pas approchée),
    et l'ancre porte sa source."""
    dec = _load_decision()
    anchor = ", selon le manuel,"
    body = "## Montage\n\nLe couple vaut environ, selon le manuel, 25 Nm.\n"
    target = _safety_wiki(tmp_path, body=body, entries=[_captured_anchor("## Montage", anchor)])
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert (result["anchored_claims"], result["anchors_unmasked"]) == (1, [])
    assert _violations_of(result, "corps") == _unsourced("25 Nm"), result


def test_safety_numeric_body_blocks_are_separate_clauses(tmp_path):
    """Chaque bloc du corps est une clause : un nombre en fin de bloc et une unité en tête du
    suivant ne forment pas une valeur (résidu : nombre séparé de son unité par la structure)."""
    dec = _load_decision()
    body = "## Montage\n\nSerrer la vis à 25\n\nNm est l'unité du couple.\n"
    target = _safety_wiki(tmp_path, body=body)
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert _violations_of(result, "corps") == [], result


def test_string_readings_keep_rendered_blocks_apart():
    """Une chaîne publiée rendue garde ses blocs séparés (`;`) ; lue telle qu'écrite, elle forme
    la valeur, et ses blocs projetés joints sans séparateur, comme les joint `stripHtml`, aussi."""
    dec = _load_decision()
    ccm = dec._load_module("_coverage_string_readings", "check-coverage-map.py")
    assert dec._string_readings("Couple de 25\n\nNm", ccm) == [
        ("littérale", "Couple de 25 Nm"), ("rendue", "Couple de 25 ; Nm"),
        ("projection jointe", "Couple de 25Nm")]


def test_string_readings_read_the_string_as_the_projection_renders_it():
    """HTML affiché tel qu'écrit par `renderProjectionMarkdown`, sa grammaire inline appliquée
    jusque dans ce HTML : la lecture `projection` affiche la valeur, qu'aucune autre ne lit."""
    dec = _load_decision()
    ccm = dec._load_module("_coverage_string_readings", "check-coverage-map.py")
    assert dec._string_readings("<!-- 25 **mm** -->", ccm) == [
        ("littérale", "<!-- 25 **mm** -->"), ("projection", "<!-- 25 mm -->")]


# Texte de chaque bloc que `renderProjectionMarkdown` affiche (monorepo, `backend/src/modules/
# seo-projection/projection-markdown.renderer.ts` au commit d3b0060e6d), produit par le rendu
# TypeScript lui-même : HTML rendu, texte de chaque `<p>`, `<h3>`, `<h4>`, `<li>`, balises du rendu
# retirées et ses quatre entités décodées. Cas de ses propres tests, cas où CommonMark affiche
# autre chose, et classes JavaScript (`\s`, `trim`, `.`, `\d`) qui diffèrent de celles de Python.
@pytest.mark.parametrize("md, blocks", [
    ('5 < 10 && "x" > 3', ['5 < 10 && "x" > 3']),
    ('[clic](javascript:alert(1))', ['clic)']),
    ('[doc](https://ex.com/p)', ['doc']),
    ('[**a** <b>](/x)', ['a <b>']),
    ('Un.\n\nDeux\ntrois.', ['Un.', 'Deux trois.']),
    ('Un.\r\n\r\nDeux.\rTrois.', ['Un.', 'Deux. Trois.']),
    ('a **b** c', ['a b c']),
    ('a *b* c', ['a b c']),
    ('voir #LinkGamme_12# et ref_a_b', ['voir #LinkGamme_12# et ref_a_b']),
    ('a ** b * c', ['a ** b * c']),
    ('valeur `K9K` moteur', ['valeur K9K moteur']),
    ('`<b>x</b>`', ['<b>x</b>']),
    ('- un\n* deux', ['un', 'deux']),
    ('1. un\n2. deux', ['un', 'deux']),
    ('Intro :\n- a\n- b\nSuite.', ['Intro :', 'a', 'b', 'Suite.']),
    ('## Titre', ['Titre']),
    ('### Sous', ['Sous']),
    ('# Page', ['# Page']),
    ('- **a** et `b`\n- <x>', ['a et b', '<x>']),
    ('1.5 dCi : K9K.', ['1.5 dCi : K9K.']),
    ('', []),
    ('   \n  \n', []),
    ('Couple de serrage <!-- 25 **Nm** --> selon constructeur.',
     ['Couple de serrage <!-- 25 Nm --> selon constructeur.']),
    ('Couple de serrage <x a="25 **Nm**"> selon constructeur.',
     ['Couple de serrage <x a="25 Nm"> selon constructeur.']),
    ('Couple de serrage :\n\n<!--\n\n25 **Nm**\n\n-->\n\nselon constructeur.',
     ['Couple de serrage :', '<!--', '25 Nm', '-->', 'selon constructeur.']),
    ('Couple de serrage :\n\n<pre\n\n25 **Nm**\n\n>', ['Couple de serrage :', '<pre', '25 Nm', '>']),
    ('Couple de serrage [a[b](x y)c](<25 **Nm**>) selon constructeur.',
     ['Couple de serrage a[bc](<25 Nm>) selon constructeur.']),
    ('Couple de serrage `[``y](<25 **Nm**>) selon constructeur.',
     ['Couple de serrage [`y](<25 Nm>) selon constructeur.']),
    ('<!-- 25 **mm** -->', ['<!-- 25 mm -->']),
    ('<span title="25**mm**">x</span>', ['<span title="25mm">x</span>']),
    ('<!-- 25[mm](/x) -->', ['<!-- 25mm -->']),
    ('<!-- 25 `mm` -->', ['<!-- 25 mm -->']),
    ("Couple de serrage des vis d'étrier :\n\n    25\n**Nm** selon constructeur.",
     ["Couple de serrage des vis d'étrier :", '    25 Nm selon constructeur.']),
    ('<!-- c -->**25[](x)\nNm', ['<!-- c -->**25 Nm']),
    ('**[x](/a)**', ['x']),
    ('*a **b** c*', ['*a b c*']),
    ('``a``', ['a']),
    ('* * *', ['* *']),
    ('- \n- x', ['', 'x']),
    ('-', ['-']),
    ('##Titre', ['##Titre']),
    ('#### x', ['#### x']),
    ('##   Titre   ', ['Titre']),
    ('##\tTitre', ['Titre']),
    ('### ', ['### ']),
    ('[a](b)(c)', ['a(c)']),
    ('[a]((b))', ['a)']),
    ('**a*b**', ['*ab**']),
    ('***a***', ['*a*']),
    ('25&#32;Nm', ['25&#32;Nm']),
    ('&lt;25 Nm&gt;', ['&lt;25 Nm&gt;']),
    ('[x](//e.com)', ['x']),
    ('[25 **Nm**](https://e.x/a b)', ['25 Nm']),
    ('a\n## b\nc', ['a', 'b', 'c']),
    ('1) un', ['1) un']),
    ('10. dix\n11. onze', ['dix', 'onze']),
    ('## a\u2028b', ['## a\u2028b']),
    ('- a\u2028b', ['- a\u2028b']),
    ('x\n\x85\ny', ['x \x85 y']),
    ('x\n\ufeff\ny', ['x', 'y']),
    ('x\n\x1c\ny', ['x \x1c y']),
    ('١. un', ['١. un']),
    ('**25\xa0**', ['**25\xa0**']),
    ('*\ufeffx*', ['x*']),
    ('**x\x85**', ['x\x85']),
    ('*\x1fx*', ['\x1fx']),
    ('-\u3000item', ['item']),
    ('##\u2029t', ['t']),
    ('- a\u2029', ['- a\u2029']),
    ('**𝟐𝟓 Nm**', ['𝟐𝟓 Nm']),
    ('`😀`', ['😀']),
    ('a\u2028b\n\nc', ['a\u2028b', 'c']),
    ('##\x85t', ['##\x85t']),
])
def test_projection_blocks_match_the_typescript_renderer(md, blocks):
    assert _load_decision()._projection_blocks(md) == blocks


@pytest.mark.parametrize("body", [
    "## Montage\n\nIl faut serrer à 25 Nm la vis.\n",            # autre section que l'ancre
    "## Contrôle\n\n<p>Il faut serrer à 25 Nm la vis.</p>\n",    # HTML brut : bloc non ancrable
])
def test_safety_numeric_anchor_outside_an_anchorable_block_of_its_section_is_ignored(tmp_path, body):
    """Une ancre ne porte sa source que dans un bloc ancrable (texte Markdown) de sa section."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path, body=body, entries=[_captured_anchor("## Contrôle", "serrer à 25 Nm")])
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert result["anchored_claims"] == 0
    assert "corps (rendue) numeric_source_not_captured: '25 Nm'" in result["sample"], result


def test_safety_numeric_body_percent_escapes_are_read_in_compatibility_form(tmp_path):
    """Échappements lus affichés en IRI (`%32%35` tel qu'écrit, `%C2%AD` décodé), puis tous
    décodés, et lus comme le reste du texte : sans caractère de format."""
    dec = _load_decision()
    body = "## Montage\n\nJeu de %32%35%C2%ADmm.\n"
    target = _safety_wiki(tmp_path, body=body)
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert _violations_of(result, "corps") == [
        f"corps ({form}{suffix}) numeric_source_not_captured: {raw!r}" for form in ("rendue", "sans balisage")
        for suffix, raw in (("", "35mm"), (" décodée", "25mm"))], result


def test_safety_numeric_body_ascii_escapes_are_read_decoded_too(tmp_path):
    """Des échappements tous ASCII s'affichent en IRI tels qu'écrits (`N%6D`) : leur lecture
    décodée (`Nm`) reste lue à part, même quand l'affichage IRI ne diffère pas du texte brut."""
    dec = _load_decision()
    body = "## Montage\n\nJeu de 25 N%6D.\n"
    target = _safety_wiki(tmp_path, body=body)
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert _violations_of(result, "corps") == [
        f"corps ({form} décodée) numeric_source_not_captured: '25 Nm'" for form in ("rendue", "sans balisage")
    ], result


@pytest.mark.parametrize("text", [
    "Pression de tarage :%45 bar selon constructeur.",    # `%45` affiché tel qu'écrit, lu `E` décodé
    "Pression de tarage : %C3%A9%45 bar selon constructeur.",
])
def test_safety_numeric_percent_escape_does_not_hide_the_value_as_written(tmp_path, text):
    """Décoder un échappement ASCII (`%45` → `E`) efface les chiffres que la chaîne affiche telle
    qu'écrite : la lecture décodée s'ajoute à celle-ci, jamais ne la remplace."""
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    target = _safety_wiki(tmp_path, body=body)
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, target, tmp_path)
    assert result["verified"] is False
    assert _violations_of(result, "corps") == [
        f"corps ({form}) numeric_source_not_captured: '45 bar'" for form in ("rendue", "sans balisage")], result
    result = dec._safety_numeric_exactitude({**SAFETY_FM, "review_notes": text}, SAFETY_BODY, target, tmp_path)
    assert result["verified"] is False
    assert _violations_of(result, "fiche") == [
        "fiche $.review_notes (littérale) numeric_source_not_captured: '45 bar'"], result


def test_safety_proof_sources_cited_by_citations_count(tmp_path):
    """Citées = coverage-map ET `citations[]` : les slugs dont la provenance vérifie l'archive."""
    dec = _load_decision()
    rule = {"rule": "contrôle visuel", "citations": [{"source": "preuve_norme"}],
            "evidence": {"confidence": "high", "source_policy": "1_high",
                         "reviewed": False, "diagnostic_safe": False}}
    local = _local(dec, tmp_path, fm={**SAFETY_FM, "safety_rules": [rule]},
                   cited=["preuve_atelier", "preuve_manuel"])
    assert local["conditions"]["proof_sources_min"] is True, local["details"]["proof_sources_min"]
    assert local["details"]["proof_sources_min"]["publishers"]["organisme c"] == ["preuve_norme"]


def test_safety_proof_role_is_read_from_the_catalog_not_a_list(tmp_path):
    """Le rôle vient de `source_type_editorial_role` du catalogue : y passer un type en
    `proof` le fait compter, sans autre modification."""
    dec = _load_decision()
    sources = SAFETY_PROOF_SOURCES[:2] + (
        {"slug": "preuve_norme", "type": "brochure", "publisher": "Organisme C"},)
    blocked = _local(dec, tmp_path, sources=sources)["details"]["proof_sources_min"]
    assert blocked["not_counted"] == {"preuve_norme": "type=brochure role=corroboration"}
    local = _local(dec, tmp_path, sources=sources, roles={**SAFETY_ROLES, "brochure": "proof"})
    assert local["conditions"]["proof_sources_min"] is True


@pytest.mark.parametrize("roles", [{}, ["oem_workshop"]])
def test_safety_proof_sources_malformed_roles_fail_closed_with_error(tmp_path, roles):
    dec = _load_decision()
    local = _local(dec, tmp_path, roles=roles)
    assert local["conditions"]["proof_sources_min"] is False
    assert "source_type_editorial_role_malformed" in local["details"]["proof_sources_min"]["error"]


@pytest.mark.parametrize("publisher", [
    "", "   ", "\u200b", "\u3164", "\u115f\ufe0f", 2024, None,
    # caractère que la base Unicode ne définit pas : demi-codets isolés, même en paire, usage
    # privé, non attribué
    "Organisme \ud835\udc00", "Organisme \ud835", "\ue000", "Organisme \u0378",
])
def test_safety_proof_publisher_absent_is_not_counted(tmp_path, publisher):
    """Éditeur vide, invisible, non textuel, absent, ou qui porte un caractère que la base Unicode
    de l'interpréteur ne définit pas : aucun éditeur identifiable, la source ne compte pas, et
    ne forme jamais un éditeur."""
    dec = _load_decision()
    third = {k: v for k, v in SAFETY_PROOF_SOURCES[2].items() if k != "publisher"}
    if publisher is not None:
        third["publisher"] = publisher
    local = _local(dec, tmp_path, sources=SAFETY_PROOF_SOURCES[:2] + (third,))
    assert local["conditions"]["proof_sources_min"] is False
    assert local["details"]["proof_sources_min"]["not_counted"] == {"preuve_norme": "publisher_absent"}


@pytest.mark.parametrize("publisher", [
    "CONSTRUCTEUR\u00a0A", "Constructeur  a", "Constructeur A\u200b", "Constructeur\u034f A\ufe0f",
    "\uff23\uff4f\uff4e\uff53\uff54\uff52\uff55\uff43\uff54\uff45\uff55\uff52 \uff21",  # pleine chasse
])
def test_safety_proof_publisher_variants_are_one_publisher(tmp_path, publisher):
    """Casse, espaces, caractère invisible, pleine chasse : un même éditeur, jamais deux."""
    dec = _load_decision()
    sources = SAFETY_PROOF_SOURCES[:2] + ({**SAFETY_PROOF_SOURCES[2], "publisher": publisher},)
    local = _local(dec, tmp_path, sources=sources)
    assert local["conditions"]["proof_sources_min"] is False
    assert local["details"]["proof_sources_min"]["publishers"]["constructeur a"] == [
        "preuve_atelier", "preuve_norme"]


_EDITORIAL_SOURCED = {"source_ids": ["raw:sources/x.md"]}


def _editorial(content_md, **extra):
    """Frontmatter dont l'export SEO publie `content_md` en bloc éditorial sourcé."""
    return {"entity_data": {"editorial": {"function": {"content_md": content_md,
                                                       **_EDITORIAL_SOURCED, **extra}}}}


_SEO_BASE = _editorial("La colonne transmet la rotation.")
_QUOTE_SHA = "sha256:" + "0" * 64


def _violations_of(result, origin):
    """Violations publiées par `origin` (`fiche`, `seo`, `diagnostic`) ; l'échantillon doit
    les porter toutes."""
    assert result["violations_total"] == len(result["sample"]), result
    return [v for v in result["sample"] if v.startswith(f"{origin} ")]


@pytest.mark.parametrize("projected", [
    {"entity_data": {"editorial": {"function": {"content_md": "Serrer la colonne à 25 Nm.",
                                                **_EDITORIAL_SOURCED}}}},
    {"entity_data": {"maintenance": {"educational_advice": "Serrer à 25 Nm."}},
     "source_refs": [{"kind": "raw", "path": "sources/x.md"}, {"kind": "web", "url": "u"}]},
    {"entity_data": {"decision_brief": {"selection_criteria_top": ["serrage à 25 Nm"]}}},
    {"entity_data": {"decision_brief": {"function_oneliner": "Pièce serrée à 25 Nm."}}},
    {"entity_data": {"blocks": [{"role": "R3_CONSEILS", "content_md": "Serrer à **25 Nm**."}]}},
    {"entity_data": {"facts": [{"key": "couple", "value": "25 Nm"}]}},
    {"entity_type": "vehicle", "entity_data": {"maintenance_by_engine": {
        "k9k": {"content_md": "Serrer à 25 Nm.", **_EDITORIAL_SOURCED}}}},
])
def test_safety_numeric_value_projected_from_frontmatter_is_unsourced(tmp_path, projected):
    """Le texte que l'export SEO publie depuis le frontmatter est contrôlé comme le corps :
    aucune ancre ne le désigne, une valeur dimensionnée y est non sourcée."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude({**SAFETY_FM, **projected}, SAFETY_BODY, target, tmp_path)
    assert result["published"]["seo"] is True
    assert result["verified"] is False
    assert any(v.startswith("seo $.") and "numeric_source_not_captured" in v
               for v in result["sample"]), result


def test_safety_numeric_scope_is_the_fiche_and_the_seo_export(tmp_path, monkeypatch):
    """La fiche promue est publiée elle-même : un champ du frontmatter que `build_exports_seo`
    ne publie pas est lu dans la fiche ; dès que l'export le publie, il l'est aussi dans
    l'export, sans autre modification."""
    dec = _load_decision()
    fm = {**SAFETY_FM, "entity_data": {
        "editorial": {"function": {"content_md": "La colonne transmet la rotation.",
                                   **_EDITORIAL_SOURCED}},
        "decision_brief": {"selection_criteria_top": ["origine constructeur"],
                           "function_oneliner": "Relie le volant au boîtier."},
        "related_parts": ["cardan de direction"],
        "pg_id": 4242,
        "notes": "Serrer à 25 Nm."}}
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
    assert result["published"]["seo"] is True
    fiche = ["fiche $.entity_data.notes (littérale) numeric_source_not_captured: '25 Nm'"]
    assert result["sample"] == fiche, result
    load = dec._load_module

    def exporter_publishing_notes(name, filename):
        module = load(name, filename)
        if filename == "build_exports_seo.py":
            build = module.build_export

            def build_export(source_path, *args, **kwargs):
                doc = build(source_path, *args, **kwargs)
                notes = dec._parse_markdown(Path(source_path))[0]["entity_data"]["notes"]
                return None if doc is None else {**doc, "notes": notes}
            module.build_export = build_export
        return module

    monkeypatch.setattr(dec, "_load_module", exporter_publishing_notes)
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
    assert result["sample"] == fiche + [
        "seo $.notes (littérale) numeric_source_not_captured: '25 Nm'"], result


def test_safety_numeric_fiche_that_no_exporter_publishes_is_read(tmp_path):
    """Fiche `diagnostic` : aucun exporteur ne la publie, un lecteur du canon en sert le
    frontmatter tel quel (moteur diagnostic du monorepo, `wiki/diagnostic/`). Une valeur
    dimensionnée dans `entity_data` y est non sourcée."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    fm = {**SAFETY_FM, "entity_type": "diagnostic", "entity_data": {"faq": [
        {"question": "Quelle pression ?", "answer": "Gonfler à 2.4 bar."}]}}
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
    assert result["published"] == {"seo": False, "diagnostic": False}
    assert result["sample"] == [
        "fiche $.entity_data.faq[0].answer (littérale) numeric_source_not_captured: '2.4 bar'"], result


def test_safety_numeric_no_fiche_field_is_exempt(tmp_path):
    """Aucun champ n'est exempté, `review_notes` compris : la fiche est publiée telle
    qu'écrite. Faux positif conservateur, documenté (quality-gates.md) : la fiche retombe en
    relecture humaine."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude({**SAFETY_FM, "review_notes": "Couple relevé : 25 Nm."},
                                            SAFETY_BODY, target, tmp_path)
    assert result["sample"] == [
        "fiche $.review_notes (littérale) numeric_source_not_captured: '25 Nm'"], result


def test_safety_numeric_reads_the_frontmatter_promotion_writes(tmp_path, monkeypatch):
    """La fiche lue est celle que la promotion écrit : un champ que `_promoted_frontmatter`
    ajouterait est lu, sans autre modification."""
    dec = _load_decision()
    promoted = dec._promoted_frontmatter
    monkeypatch.setattr(dec, "_promoted_frontmatter",
                        lambda *a, **k: {**promoted(*a, **k), "promotion_note": "Serrer à 25 Nm."})
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude(SAFETY_FM, SAFETY_BODY, target, tmp_path)
    assert result["sample"] == [
        "fiche $.promotion_note (littérale) numeric_source_not_captured: '25 Nm'"], result


def test_safety_numeric_fiche_yaml_dates_and_numeric_keys_are_read_as_text(tmp_path):
    """Date YAML non citée, clé numérique : lues comme un lecteur JSON les reçoit, en texte."""
    import datetime
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    fm = {**SAFETY_FM, "created_at": datetime.date(2026, 10, 13),
          "entity_data": {"history": {2024: "Jeu de 2 mm relevé."}}}
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
    assert result["sample"] == [
        'fiche $.entity_data.history["2024"] (littérale) numeric_source_not_captured: \'2 mm\''], result


@pytest.mark.parametrize("notes, where", [
    # `"1"` et `1` : deux clés YAML, une seule après conversion JSON ; aucune valeur n'est perdue
    ({"1": "Jeu de 25 mm.", 1: "x"}, '$.notes["1"]'),
    ({1: "x", "1": "Jeu de 25 mm."}, '$.notes["1"]'),
    ({datetime.date(2024, 1, 1): "Jeu de 25 mm."}, '$.notes["2024-01-01"]'),
])
def test_safety_numeric_fiche_is_read_as_parsed_not_as_converted(tmp_path, notes, where):
    """Le frontmatter est lu tel qu'un lecteur YAML du canon l'analyse."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude({**SAFETY_FM, "notes": notes}, SAFETY_BODY, target, tmp_path)
    assert result["sample"] == [f"fiche {where} (littérale) numeric_source_not_captured: '25 mm'"], result


def test_published_strings_reads_non_string_scalars_by_their_text():
    """Date et `!!binary` YAML, en valeur comme en clé : lus par leur texte, octets décodés.
    Nombre, booléen et nul ne portent pas d'unité : seule leur clé est lue."""
    import yaml
    dec = _load_decision()
    doc = yaml.safe_load("d: 2026-10-13\n"
                         "b: !!binary SmV1IGRlIDI1IG1tLg==\n"
                         "2024-01-01: x\n"
                         "? !!binary MjUgbW0=\n"
                         ": y\n"
                         "n: 3\nt: true\nz: null\n")
    assert list(dec._published_strings(doc)) == [
        ("$.d (clé)", "d"), ("$.d", "2026-10-13"),
        ("$.b (clé)", "b"), ("$.b", "Jeu de 25 mm."),
        ('$["2024-01-01"] (clé)', "2024-01-01"), ('$["2024-01-01"]', "x"),
        ('$["25 mm"] (clé)', "25 mm"), ('$["25 mm"]', "y"),
        ("$.n (clé)", "n"), ("$.t (clé)", "t"), ("$.z (clé)", "z")]


def test_safety_numeric_fiche_yaml_binary_is_read_decoded(tmp_path):
    """Un `!!binary` YAML du frontmatter est publié tel que décodé : sa valeur est lue."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    fm = {**SAFETY_FM, "notes": "Jeu de 25 mm.".encode()}
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
    assert result["sample"] == ["fiche $.notes (littérale) numeric_source_not_captured: '25 mm'"], result


def test_published_strings_reads_a_yaml_set_in_a_stable_order():
    """Un `!!set` YAML n'a pas d'ordre : il est lu trié, la trace ne dépend pas du hachage."""
    import yaml
    dec = _load_decision()
    names = [f"v{i:02d}" for i in range(26)]
    doc = yaml.safe_load("s: !!set {" + ", ".join(reversed(names)) + "}\n")
    assert list(dec._published_strings(doc)) == [("$.s (clé)", "s")] + [
        (f"$.s[{i}]", name) for i, name in enumerate(names)]


def test_safety_numeric_reads_the_evaluation_the_decision_writes(tmp_path):
    """La fiche lue porte l'évaluation qu'écrira la décision (`promotion_evidence`), pas une
    évaluation neutre : une note du score shadow qui porte une valeur est lue."""
    dec = _load_decision()
    local = _local(dec, tmp_path, shadow={**SAFETY_SHADOW, "shadow_notes": ["A: 25 mm"]})
    assert local["conditions"]["numeric_exactitude_verified"] is False
    assert local["details"]["numeric_exactitude_verified"]["sample"] == [
        "fiche $.promotion_evidence.shadow_score.shadow_notes[0] (littérale) "
        "numeric_source_not_captured: '25 mm'"], local


def test_safety_numeric_database_projection_raises_no_false_positive(tmp_path):
    """Compatibilité, puissance, années, nombre de modèles : aucune valeur dimensionnée."""
    dec = _load_decision()
    fm = {**SAFETY_FM, "entity_data": {"pg_id": 4242, "dimensions": {"compatibility_factors": {
        "model_count_distinct": 412, "marques": ["renault", "dacia"], "fuels": ["Diesel", "Essence"],
        "power_ps_range": {"min": 60, "max": 140}, "year_range": {"min": 1998, "max": 2012}}}}}
    target = _safety_wiki(tmp_path)
    baseline = dec._safety_numeric_exactitude(SAFETY_FM, SAFETY_BODY, target, tmp_path)
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
    assert result["strings_read"]["seo"] > baseline["strings_read"]["seo"]
    assert result["strings_read"]["fiche"] > baseline["strings_read"]["fiche"]
    assert not any("aucun bloc structuré projetable" in w for w in result["projection_warnings"])
    assert result["verified"] is True, result
    with dec._promoted_fiche(fm, SAFETY_BODY, target, tmp_path) as (root, path):
        doc, _warnings = dec._seo_projection(path, root)
    assert any("puissance 60–140 ch" in b.get("content_md", "") for b in doc["blocks"]), doc["blocks"]


def test_safety_numeric_exporter_warning_is_reported_not_printed(tmp_path, capsys):
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude(SAFETY_FM, SAFETY_BODY, target, tmp_path)
    assert result["published"] == {"seo": True, "diagnostic": False}
    assert any("aucun bloc structuré projetable" in w for w in result["projection_warnings"])
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("projected, where, raw", [
    (_editorial("La colonne transmet la rotation.", usefulness_target="serrage 25 Nm"),
     "$.blocks[0].usefulness_target", "25 Nm"),
    ({"entity_data": {"blocks": [{"role": "R3_CONSEILS", "section": "Couple 25 Nm",
                                  "content_md": "Serrer correctement."}]}},
     "$.blocks[0].section", "25 Nm"),
    ({"entity_data": {"blocks": [{"role": "R3_CONSEILS", "content_md": "Serrer correctement.",
                                  "usefulness_target": "jeu 2 mm"}]}},
     "$.blocks[0].usefulness_target", "2 mm"),
    ({"entity_data": {"facts": [{"key": "couple 25 Nm", "value": "voir notice"}]}},
     "$.facts[0].key", "25 Nm"),
    ({"entity_data": {"facts": [{"key": "couple", "value": "voir notice",
                                 "source_id": "notice-25Nm"}]}},
     "$.facts[0].source_id", "25Nm"),
    ({**_SEO_BASE, "source_refs": [{"kind": "web", "url": "https://x.fr/serrage-25Nm"}]},
     "$.sources[0].url", "25Nm"),
    ({**_SEO_BASE, "source_refs": [{"kind": "raw", "id": "manuel-280mm", "path": "sources/x.md"}]},
     "$.sources[0].id", "280mm"),
    ({"entity_type": "vehicle", "entity_data": {"maintenance_by_engine": {
        "k9k turbo 1,2 bar": {"content_md": "Contrôler la colonne.", **_EDITORIAL_SOURCED}}}},
     "$.blocks[0].usefulness_target", "1,2 bar"),
])
def test_safety_numeric_every_published_seo_string_is_read(tmp_path, projected, where, raw):
    """Titre de section, cible d'usage, clé et identifiant de fait, URL et identifiant de
    source, clé moteur devenue cible d'usage : toute chaîne que l'export SEO publie est lue,
    quel que soit le champ."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude({**SAFETY_FM, **projected}, SAFETY_BODY, target, tmp_path)
    assert _violations_of(result, "seo") == [
        f"seo {where} (littérale) numeric_source_not_captured: {raw!r}"], result
    assert _violations_of(result, "fiche"), result  # la fiche publie la même chaîne


@pytest.mark.parametrize("case, error", [
    ("malformed_dimensions", "AttributeError: 'str' object has no attribute 'get'"),
    ("unserialisable", "TypeError: Object of type set is not JSON serializable"),
])
def test_safety_numeric_unexportable_seo_document_fails_closed_with_error(
        tmp_path, monkeypatch, case, error):
    """Fiche que l'export SEO ne sait pas projeter, ou document qu'il ne saurait écrire : le
    texte publié est indéterminable, la condition est fausse et l'erreur est rapportée."""
    dec = _load_decision()
    fm = SAFETY_FM
    if case == "malformed_dimensions":
        fm = {**SAFETY_FM, "entity_data": {"pg_id": 4242, "dimensions": "pas un mapping"}}
    else:
        load = dec._load_module

        def exporter_with_a_set(name, filename):
            module = load(name, filename)
            if filename == "build_exports_seo.py":
                build = module.build_export
                module.build_export = lambda *a, **k: {**build(*a, **k), "tags": {"a"}}
            return module

        monkeypatch.setattr(dec, "_load_module", exporter_with_a_set)
    local = _local(dec, tmp_path, fm=fm)
    assert local["conditions"]["numeric_exactitude_verified"] is False
    assert error in local["details"]["numeric_exactitude_verified"]["error"]


@pytest.mark.parametrize("document, error", [
    ({"updated": datetime.date(2026, 1, 1)}, "TypeError: Object of type date is not JSON serializable"),
    ({"tags": {"a"}}, "TypeError: Object of type set is not JSON serializable"),
    ({datetime.date(2026, 1, 1): "x"}, "TypeError: keys must be str, int, float, bool or None, not date"),
])
def test_safety_numeric_unexportable_diagnostic_document_fails_closed_with_error(
        tmp_path, monkeypatch, document, error):
    """Document diagnostic que l'export ne saurait écrire : ses chaînes ne sont pas lues dans un
    ordre ou une forme que l'export n'écrirait jamais ; la condition est fausse et l'erreur
    rapportée."""
    dec = _load_decision()
    monkeypatch.setattr(dec, "_diagnostic_projection", lambda *a, **k: document)
    local = _local(dec, tmp_path)
    assert local["conditions"]["numeric_exactitude_verified"] is False
    assert error in local["details"]["numeric_exactitude_verified"]["error"]


@pytest.mark.parametrize("content_md, forms, unmodelled", [
    ("**25** Nm", ["rendue"], []), ("25 *Nm*", ["rendue"], []), ("25&nbsp;Nm", ["rendue"], []),
    ("25&#8239;Nm", ["rendue"], []),
    # HTML en ligne : la valeur reste lue, rendue et sans balisage ; les balises, que le contrôle ne
    # modélise pas, sont relevées
    ("<b>25</b> Nm", ["rendue", "sans balisage"], [("raw_html", "<b"), ("raw_html", "</b")]),
])
def test_safety_numeric_published_string_is_read_as_rendered(tmp_path, content_md, forms, unmodelled):
    """Emphase, entités, balises : la valeur qu'affiche le rendu Markdown/HTML est lue, même
    absente du texte tel qu'écrit."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude({**SAFETY_FM, **_editorial(content_md)}, SAFETY_BODY,
                                            target, tmp_path)
    where = "seo $.blocks[0].content_md"
    assert _violations_of(result, "seo") == [
        f"{where} ({form}) numeric_source_not_captured: '25 Nm'" for form in forms] + [
        f"{where} unmodelled_{kind}: {marker!r}" for kind, marker in unmodelled], result


@pytest.mark.parametrize("content_md, raw, forms", [
    # URL de lien : absente du rendu, lue telle qu'écrite (la chaîne, puis la destination du lien)
    ("[voir](https://x.fr/serrage-25Nm)", "25Nm", ["littérale", "écrite"]),
    ("Serrer à 25 Nm.", "25 Nm", ["littérale"]),    # lectures identiques : une seule violation
    # U+0387 (ano teleia) : canoniquement équivalent au point médian de `N·m`, lu en NFC
    ("[voir](https://x.fr/serrage-25N·m)", "25N·m", ["littérale", "écrite"]),
])
def test_safety_numeric_published_string_is_read_as_written(tmp_path, content_md, raw, forms):
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude({**SAFETY_FM, **_editorial(content_md)}, SAFETY_BODY,
                                            target, tmp_path)
    assert _violations_of(result, "seo") == [
        f"seo $.blocks[0].content_md ({form}) numeric_source_not_captured: {raw!r}" for form in forms], result


@pytest.mark.parametrize("content_md, raw, forms, unmodelled", [
    # Échappement ASCII : affiché tel qu'écrit, la valeur reste visible
    ("Pression de tarage :%45 bar selon constructeur.", "45 bar", ["littérale"], []),
    # Structure de blocs ignorée : `renderProjectionMarkdown`, qui ne connaît pas le code indenté,
    # joint les lignes en un paragraphe, comme un lecteur en texte, là où CommonMark sépare le code
    # indenté du paragraphe suivant (lecture `sans structure`, ici identique à la projection jointe).
    ("Couple de serrage des vis d'étrier :\n\n    25\n**Nm** selon constructeur.", "25 Nm",
     ["projection", "projection jointe"], []),
    # Bloc HTML (commentaire) : CommonMark le rend tel quel, ligne par ligne ; joint, il affiche la
    # valeur ; le commentaire, que le contrôle ne modélise pas, est relevé
    ("<!-- c -->**25[](x)\nNm", "25 Nm", ["projection", "sans structure"], [("raw_html", "<!--")]),
    # … échappement décodé compris
    ("Couple :\n\n    25\n**N%6D** selon constructeur.", "25 Nm",
     ["projection décodée", "projection jointe décodée"], []),
    # Formule : jamais lue en formule, même d'un bloc à l'autre ; relevée, et la lecture sans
    # balisage reste faite
    ("Couple $120\\,\\mathrm{Nm}$ selon constructeur.", None, [], [("formula", "$")]),
    ("Kit à 30 $ ; serrage 120\\Nm ; main-d'œuvre 50 $.", "120Nm", ["sans balisage"], [("formula", "$")]),
    ("$$25\n\n\\text{Nm}$$", None, [], [("formula", "$")]),
])
def test_safety_numeric_published_string_is_read_for_any_renderer(tmp_path, content_md, raw, forms, unmodelled):
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude({**SAFETY_FM, **_editorial(content_md)}, SAFETY_BODY,
                                            target, tmp_path)
    assert result["verified"] is False
    for origin, where in (("seo", "$.blocks[0].content_md"),
                          ("fiche", "$.entity_data.editorial.function.content_md")):
        assert _violations_of(result, origin) == [
            f"{origin} {where} ({form}) numeric_source_not_captured: {raw!r}" for form in forms] + [
            f"{origin} {where} unmodelled_{kind}: {marker!r}" for kind, marker in unmodelled], result


# Chaque cas : affiché par `renderProjectionMarkdown`, caché par CommonMark (HTML, destination de
# lien) et par la lecture sans balisage (HTML et lien retirés avec leur contenu). Le HTML, que le
# contrôle ne modélise pas, est relevé en plus de la valeur.
_ONE_BLOCK = ["projection"]
_BLOCKS = ["projection", "projection jointe"]   # blocs lus séparés, puis joints comme `stripHtml`
_PROJECTION_ONLY = [
    # HTML affiché tel qu'écrit, emphase rendue jusque dans un commentaire ou un attribut
    ("Couple de serrage <!-- 25 **Nm** --> selon constructeur.", "25 Nm", _ONE_BLOCK, ["<!--"]),
    ('Couple de serrage <x a="25 **Nm**"> selon constructeur.', "25 Nm", _ONE_BLOCK, ["<x"]),
    ("<!-- 25 **mm** -->", "25 mm", _ONE_BLOCK, ["<!--"]),
    ('<span title="25**mm**">x</span>', "25mm", _ONE_BLOCK, ["<span", "</span"]),
    ("### Couple <!-- 25 **Nm** --> selon constructeur.", "25 Nm", _ONE_BLOCK, ["<!--"]),   # … dans un titre
    # … sur des lignes blanches : chaque ligne est un paragraphe, la valeur le sien
    ("Couple de serrage :\n\n<!--\n\n25 **Nm**\n\n-->\n\nselon constructeur.", "25 Nm", _BLOCKS, ["<!--"]),
    ("Couple de serrage :\n\n<pre\n\n25 **Nm**\n\n>", "25 Nm", _BLOCKS, ["<pre"]),
    # Lien lu de gauche à droite, au premier `]` : la destination de CommonMark reste du texte
    ("Couple de serrage [a[b](x y)c](<25 **Nm**>) selon constructeur.", "25 Nm", _ONE_BLOCK, []),
    # … lue aussi en forme de compatibilité (espace sans chasse retiré)
    ("Couple de serrage [a[b](x y)c](<25\u200b **Nm**>) selon constructeur.", "25 Nm", _ONE_BLOCK, []),
    # Code entre deux accents graves seulement : il prend le `[` du lien de CommonMark
    ("Couple de serrage `[``y](<25 **Nm**>) selon constructeur.", "25 Nm", _ONE_BLOCK, []),
]


@pytest.mark.parametrize("content_md, raw, forms, markers", _PROJECTION_ONLY)
def test_safety_numeric_content_md_is_read_as_the_projection_renders_it(tmp_path, content_md, raw, forms, markers):
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude({**SAFETY_FM, **_editorial(content_md)}, SAFETY_BODY,
                                            target, tmp_path)
    assert result["verified"] is False
    for origin, where in (("seo", "$.blocks[0].content_md"),
                          ("fiche", "$.entity_data.editorial.function.content_md")):
        assert _violations_of(result, origin) == [
            f"{origin} {where} ({form}) numeric_source_not_captured: {raw!r}" for form in forms] + [
            f"{origin} {where} unmodelled_raw_html: {m!r}" for m in markers], result


@pytest.mark.parametrize("notes, raw, forms, markers", _PROJECTION_ONLY)
def test_safety_numeric_frontmatter_string_is_read_as_the_projection_renders_it(tmp_path, notes, raw, forms, markers):
    """Toute chaîne publiée, pas seulement `content_md` : ni liste de champs, ni connaissance des
    lecteurs."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude({**SAFETY_FM, "review_notes": notes}, SAFETY_BODY,
                                            target, tmp_path)
    assert result["verified"] is False
    assert _violations_of(result, "fiche") == [
        f"fiche $.review_notes ({form}) numeric_source_not_captured: {raw!r}" for form in forms] + [
        f"fiche $.review_notes unmodelled_raw_html: {m!r}" for m in markers], result


@pytest.mark.parametrize("value", [
    "25\u2800Nm",                         # blanc braille, dessiné sans encre : affiché `25 Nm`
    "%EF%BC%92%EF%BC%95%E2%A0%80Nm",     # … le même, échappé (pleine chasse décodée)
])
def test_safety_numeric_blank_glyph_between_value_and_unit_is_read_as_a_space(tmp_path, value):
    """Un glyphe vide (ni espace, ni invisible pour Unicode) sépare la valeur de son unité comme un
    espace, dans le corps comme dans toute chaîne publiée."""
    dec = _load_decision()
    text = f"Serrer la colonne à {value}."
    caught = [f"({form}) numeric_source_not_captured: '25 Nm'" for form in ("rendue", "sans balisage")]
    body = f"## Montage\n\n{text}\n"
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body), tmp_path)
    assert _violations_of(result, "corps") == [f"corps {c}" for c in caught], result
    target = _safety_wiki(tmp_path)
    sourced = {**SAFETY_FM, **_SEO_BASE, "source_refs": [{"kind": "web", "url": f"https://x.fr/a?c={value}"}]}
    for fm, origin, where in (
            ({**SAFETY_FM, "review_notes": text}, "fiche", "$.review_notes"),
            ({**SAFETY_FM, **_editorial(text)}, "seo", "$.blocks[0].content_md"),
            ({**SAFETY_FM, **_editorial(text)}, "fiche", "$.entity_data.editorial.function.content_md"),
            (sourced, "seo", "$.sources[0].url"), (sourced, "fiche", "$.source_refs[0].url")):
        result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
        assert _violations_of(result, origin) == [f"{origin} {where} {c}" for c in caught], result


# Chaque cas : une forme qu'aucune lecture du contrôle ne modélise. Le contrôle lit chaque texte dans
# l'ordre écrit, sans HTML, sans formule, sans moteur de rendu ni note de bas de page : plutôt qu'une
# lecture de plus par moteur, la forme est relevée, dans le corps comme dans toute chaîne publiée, et
# la fiche ne passe pas.
_UNMODELLED = [
    # Contrôle bidirectionnel (forçage, isolat, marque), écrit, échappé ou en entité HTML
    ("Serrer la colonne à \u202emN 52\u202c.", [("display_order", "U+202E"), ("display_order", "U+202C")]),
    ("Serrer la colonne à %E2%80%AEmN 52", [("display_order", "U+202E")]),
    ("Serrer la colonne à &#x202E;mN 52&#x202C;.", [("display_order", "U+202E"), ("display_order", "U+202C")]),
    # … ou que seuls les deux décodages successifs révèlent, dans un ordre ou dans l'autre
    ("Serrer la colonne à &#37;E2&#37;80&#37;AEmN 52.", [("display_order", "U+202E")]),
    ("Serrer la colonne à %26%23x202E%3BmN 52.", [("display_order", "U+202E")]),
    ("Couple : \u2067mN 52\u2069 selon constructeur.", [("display_order", "U+2067"), ("display_order", "U+2069")]),
    # Caractère de classe R, AL ou AN : l'ordre affiché peut différer de l'ordre écrit (marque en
    # tête : `test_safety_numeric_leading_mark_is_a_violation`)
    ("\u0627 Nm \u0662\u0665 selon constructeur",
     [("display_order", "U+0627"), ("display_order", "U+0662"), ("display_order", "U+0665")]),
    ("Couple : \u05d0 Nm 25 selon constructeur.", [("display_order", "U+05D0")]),
    # HTML brut, quel que soit l'élément ou l'attribut : direction, feuille de style, SVG
    ('Serrer la colonne à <bdo dir="rtl">mN 52</bdo>.', [("raw_html", "<bdo"), ("raw_html", "</bdo")]),
    ('Serrer à <span dir="rtl"><span dir="ltr">Nm</span> <span dir="ltr">25</span></span>.',
     [("raw_html", "<span"), ("raw_html", "</span")]),
    ("Serrer la colonne à <style>p { direction: rtl }</style> mN 52.",
     [("raw_html", "<style"), ("raw_html", "</style")]),
    ('Serrer à <svg><text direction="rtl" unicode-bidi="bidi-override">mN 52</text></svg>.',
     [("raw_html", "<svg"), ("raw_html", "<text"), ("raw_html", "</text"), ("raw_html", "</svg")]),
    # Bloc HTML (élément de bloc, commentaire), que CommonMark ne lit pas en ligne
    ('<div dir="rtl">\n\nmN 52\n\n</div>', [("raw_html", "<div"), ("raw_html", "</div")]),
    ("<!-- direction inversée -->", [("raw_html", "<!--")]),
    # Instruction de traitement : CommonMark la lit jusqu'au premier `?>`, le navigateur jusqu'au
    # premier `>` (`25Nm?>` affiché)
    ("Serrer à 25<?x>Nm?>.", [("raw_html", "<?x")]),
    # … dans une cellule de tableau (GFM) qu'un code en ligne semble traverser : la cellule l'emporte
    ("| a | b | c |\n|---|---|---|\n| `x | 25<?x>Nm?> | y` |", [("raw_html", "<?x")]),
    # Formule : tout `$`, monétaire compris, écrit, en entité ou échappé ; aucune commande n'est lue
    ("Jeu de $25\\,\\mathrm{mm}$.", [("formula", "$")]),
    ("Kit à 30 $ ; serrer la colonne à $25\\text{ Nm}$.", [("formula", "$")]),
    ("Serrer la colonne à $25\\ \\mathrm{N m}$.", [("formula", "$")]),
    ("$`25\\,\\mathrm{N\\!m}`$", [("formula", "$")]),
    ("Serrer à &#36;25&#36;.", [("formula", "$")]),
    ("Kit à 30 \\$ ; jeu contrôlé.", [("formula", "$")]),
    ("Jeu en %24x %5Cmu y%24.", [("formula", "$")]),
    # Bloc confié à un moteur de rendu (formule, diagramme, carte, modèle 3D, recherche et vue
    # « Bases » d'Obsidian), quelle que soit la casse
    ("```math\n25\\,\\mathrm{N\\!m}\n```", [("rendered_fence", "math")]),
    ("```math\n\\qquad\\mathrm{Nm}" + "\\negthickspace" * 12 + "\\negmedspace25\\qquad\\enspace\n```",
     [("rendered_fence", "math")]),
    ('```mermaid\ngraph LR\nA["Serrer à 25#32;Nm"]\n```', [("rendered_fence", "mermaid")]),
    ("~~~ GeoJSON x\n{}\n~~~", [("rendered_fence", "geojson")]),
    ("~~~topojson\n{}\n~~~", [("rendered_fence", "topojson")]),
    ("```stl\nsolid x\n```", [("rendered_fence", "stl")]),
    ('```query\n"couple de serrage"\n```', [("rendered_fence", "query")]),   # recherche d'Obsidian
    ("```base\nfilters: x\n```", [("rendered_fence", "base")]),               # vue « Bases »
    ("~~~Base\nviews: []\n~~~", [("rendered_fence", "base")]),
    # … que seul un décodage (échappement, entité) produit
    ("Couple\n\n%60%60%60math\n\\qquad\\mathrm{Nm}" + "\\negthickspace" * 12
     + "\\negmedspace25\\qquad\\enspace\n%60%60%60", [("rendered_fence", "math")]),
    ("&#96;&#96;&#96;mermaid\ngraph LR\nA-->B\n&#96;&#96;&#96;", [("rendered_fence", "mermaid")]),
    # Note de bas de page (GFM) : GitHub y joint sa définition, que CommonMark ne connaît pas ;
    # fermée ou non, lue en un seul passage
    ("Voir la note[^n] du constructeur.", [("footnote", "[^n]")]),
    ("Voir la note[^n du constructeur.", [("footnote", "[^n du constructeur.")]),
    # … ou note en ligne d'Obsidian, lecteur que déclare le dépôt, fermée ou non
    ("Serrer la colonne^[voir notice] à la main.", [("footnote", "^[voir notice]")]),
    ("Serrer la colonne^[voir notice à la main.", [("footnote", "^[voir notice à la main.")]),
    # Renvoi d'Obsidian qui n'affiche pas son texte : insertion (fermée ou non), lien à libellé,
    # à titre ou à bloc, commentaire masqué ; le lien simple (`[[colonne]]`) reste lu
    ("Couple de serrage : ![[couple-roue]]", [("obsidian", "![[couple-roue]]")]),
    ("Voir ![[schéma de montage", [("obsidian", "![[schéma de montage")]),
    # (dernier mot de la ligne, `[[note^b]].` est relevé aussi en identifiant de bloc)
    ("Voir [[note#Couple]] et [[note^b]].",
     [("obsidian", "[[note#Couple]]"), ("obsidian", "[[note^b]]"), ("obsidian", "[[note^b]].")]),
    ("Voir [[colonne]] et [[colonne|la colonne]].", [("obsidian", "[[colonne|la colonne]]")]),
    # … lien écrit avec l'extension de sa note, qu'Obsidian peut afficher sans elle
    ("Voir [[25.md]] pour le couple.", [("obsidian", "[[25.md]]")]),
    ("Voir [[Note.MD ]] et [[note]].", [("obsidian", "[[Note.MD ]]")]),
    # … blancs ECMAScript de fin compris
    ("Voir [[25.md\ufeff]] pour le couple.", [("obsidian", "[[25.md\ufeff]]")]),
    ("Serrer la colonne %%masqué%% à la main.", [("obsidian", "%%")]),
    # Relevés dans l'ordre du texte, quel que soit le motif qui les trouve
    ("Voir %%x%% puis [[a|b]] et ![[c]].",
     [("obsidian", "%%"), ("obsidian", "[[a|b]]"), ("obsidian", "![[c]]")]),
    # … identifiant de bloc en fin de ligne, masqué : relevé dans tout dernier mot de ligne qui
    # porte un `^` suivi d'un caractère, où qu'il soit dans le mot, blancs de fin compris, quelle
    # que soit la fin de ligne ; le `^` d'une note n'en est pas un
    ("Serrer la colonne à la main. ^montage", [("obsidian", "^montage")]),
    ("Voir la note x^montage  \r\nsuite", [("obsidian", "x^montage")]),
    ("Serrer la colonne à la main ^montage\rsuite", [("obsidian", "^montage")]),
    ("Serrer la colonne à la main ^montage\u2028suite", [("obsidian", "^montage")]),
    # … suivi de blancs ECMAScript, U+FEFF compris
    ("Serrer la colonne à la main ^montage \ufeff\nsuite", [("obsidian", "^montage")]),
    ("Serrer la colonne à la main [^1]", [("footnote", "[^1]")]),
    ("Serrer la colonne à la main^[notice]", [("footnote", "^[notice]")]),
    ("Voir la note x[^a^montage", [("footnote", "[^a^montage"), ("obsidian", "x[^a^montage")]),
    ("Voir la note x[^1]^montage", [("footnote", "[^1]"), ("obsidian", "x[^1]^montage")]),
    # Masqué, il laisse le numéro de l'item se lire avec l'unité qui suit
    ("1. ^montage\n\n   Nm de couple", [("obsidian", "^montage")]),
    # Encadré en tête de citation, alerte de GitHub comprise : son marqueur s'affiche en icône et
    # en titre (le type, s'il n'en a pas)
    ("> [!note] Couple de serrage", [("callout", "[!note] Couple de serrage")]),
    ("> [!WARNING]\n> Serrer à la main.", [("callout", "[!WARNING]")]),
    ("25. > [!x] Nm", [("callout", "[!x] Nm")]),
    # … relevé sur la première ligne que lit l'analyseur (lignes blanches sautées, blancs
    # ECMAScript retirés), quel que soit le bloc qu'il en tire : titre, tableau, définition de lien
    ("> [!note] 25\n> ===", [("callout", "[!note] 25")]),
    ("> [!note] | 25\n> --- | ---", [("callout", "[!note] | 25")]),
    ("> [!25]: Nm", [("callout", "[!25]: Nm")]),
    ("25. > [!x] Nm\n    > ---", [("callout", "[!x] Nm")]),
    ("> \u00a0[!note] 25", [("callout", "[!note] 25")]),
    (">\n> [!note] 25", [("callout", "[!note] 25")]),
    ("> \ufeff[!note] 25", [("callout", "[!note] 25")]),
    # Code emoji, affiché en image (`:two:` en touche 2, `:100:` en pictogramme 100)
    ("Serrer la colonne à :two::five: Nm.", [("emoji_shortcode", ":two:"), ("emoji_shortcode", ":five:")]),
    ("Serrer la colonne à :100: Nm.", [("emoji_shortcode", ":100:")]),
    ("Serrer la colonne à :keycap_ten: Nm.", [("emoji_shortcode", ":keycap_ten:")]),   # affiché 🔟
    # Chiffre que la lecture ne lit pas : sans chiffre décimal dans sa décomposition de compatibilité
    ("Serrer la colonne à \u2777\u277a Nm.", [("numeral", "U+2777"), ("numeral", "U+277A")]),
    ("Serrer la colonne à \u4e8c\u5341\u4e94 Nm.",
     [("numeral", "U+4E8C"), ("numeral", "U+5341"), ("numeral", "U+4E94")]),
    ("Serrer la colonne à 2\u3007 Nm.", [("numeral", "U+3007")]),                    # valeur nulle
    # … ou que ses chiffres décimaux n'écrivent pas : `½`, décomposé `1⁄2`, lu `2`
    ("Serrer d'un ½ tour.", [("numeral", "U+00BD")]),
    # Image, du dépôt ou distante, en ligne ou par référence : ce qu'elle affiche n'est pas du texte
    ("Voir ![](https://x.fr/couple.png).", [("image", "https://x.fr/couple.png")]),
    ("Voir ![schéma][s].\n\n[s]: img/s.png", [("image", "img/s.png")]),
    # … ou que seul un décodage (entité, échappement) fait lire
    ("&#33;[x](a.png)", [("image", "a.png")]),
    ("x %21[x](a.png)", [("image", "a.png")]),
]


@pytest.mark.parametrize("text, found", _UNMODELLED)
def test_safety_numeric_unmodelled_construct_is_a_violation(tmp_path, text, found):
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body), tmp_path)
    assert result["verified"] is False
    assert _violations_of(result, "corps") == [
        f"corps unmodelled_{kind}: {marker!r}" for kind, marker in found], result
    target = _safety_wiki(tmp_path)
    for fm, origin, where in (
            ({**SAFETY_FM, "review_notes": text}, "fiche", "$.review_notes"),
            ({**SAFETY_FM, **_editorial(text)}, "seo", "$.blocks[0].content_md"),
            ({**SAFETY_FM, **_editorial(text)}, "fiche", "$.entity_data.editorial.function.content_md")):
        result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
        assert result["verified"] is False
        assert _violations_of(result, origin) == [
            f"{origin} {where} unmodelled_{kind}: {marker!r}" for kind, marker in found], result



def test_safety_numeric_obsidian_syntax_that_shows_its_text_is_read_not_refused(tmp_path):
    """Syntaxe d'Obsidian qui affiche son texte : lien simple, affiché sans ses crochets comme le
    lit la lecture sans balisage, lien non fermé, `^` en milieu de ligne, titre en tête de
    citation, surlignage, dont la lecture squelette retire les signes. Elle n'est pas refusée, et
    la valeur qu'Obsidian affiche est lue."""
    dec = _load_decision()
    for text, shown, published in (
            ("Voir [[filtre-a-huile]] pour le montage.", [], []),
            # `couple 25 Nm` affiché par Obsidian, `couple 2]]5 Nm` par GitHub
            ("Serrer selon [[couple 2]]5 Nm.",
             ["(rendue) numeric_source_not_captured: '5 Nm'",
              "(sans balisage) numeric_source_not_captured: '25 Nm'"],
             ["(littérale) numeric_source_not_captured: '5 Nm'",
              "(sans balisage) numeric_source_not_captured: '25 Nm'"]),
            ("Serrer ^montage puis visser.", [], []),
            # lien non fermé, affiché tel qu'écrit ; titre en tête de citation (sa ligne commence
            # par `#`) et `[!` hors citation, qui ne sont pas des encadrés
            ("Voir [[note|montage sans fermeture.", [], []),
            ("> # [!note] Couple de serrage", [], []),
            ("[!note] Couple de serrage", [], []),
            # `25 Nm` surligné par Obsidian
            ("Serrer à 2==5== Nm.", ["(rendue squelette) numeric_source_not_captured: '25 Nm'"],
             ["(littérale squelette) numeric_source_not_captured: '25 Nm'"])):
        body = f"## Montage\n\n{text}\n"
        result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body),
                                                tmp_path)
        assert _violations_of(result, "corps") == [f"corps {v}" for v in shown], result
        result = dec._safety_numeric_exactitude({**SAFETY_FM, "review_notes": text}, SAFETY_BODY,
                                                _safety_wiki(tmp_path), tmp_path)
        assert _violations_of(result, "fiche") == [
            f"fiche $.review_notes {v}" for v in published], result


def test_obsidian_is_declared_without_community_plugins():
    """Le contrôle ne modélise que les modules de base d'Obsidian : le dépôt n'active aucun module
    tiers, qui peut afficher toute syntaxe autrement que le texte lu."""
    import json
    path = Path(__file__).resolve().parent.parent / ".obsidian" / "community-plugins.json"
    assert json.loads(path.read_text(encoding="utf-8")) == []


def _nested(text, quote, depth):
    """`text` imbriqué dans `depth` citations, ou dans `depth` listes à puces."""
    if quote:
        return "\n".join("> " * depth + line for line in text.split("\n"))
    first, *rest = text.split("\n")
    return "\n".join(["  " * level + "- a" for level in range(depth - 1)]
                     + ["  " * (depth - 1) + "- " + first] + ["  " * depth + line for line in rest])


@pytest.mark.parametrize("quote, depth, container", [
    (True, 19, "blockquote_open"),
    (False, 9, "list_item_open"),      # liste et élément : deux niveaux par liste
])
@pytest.mark.parametrize("text, found", [
    ("Voir ![](i.png) ici.", [("image", "i.png")]),
    ("Jeu de $x$ ici.", [("formula", "$")]),
    ("```math\nx\n```", [("rendered_fence", "math")]),
    ("Voir :two: ici.", [("emoji_shortcode", ":two:")]),
    ("Voir <b>x</b> ici.", [("raw_html", "<b"), ("raw_html", "</b")]),
])
def test_safety_numeric_construct_nested_beyond_the_parser_limit_is_a_violation(
        tmp_path, quote, depth, container, text, found):
    """markdown-it n'analyse pas le contenu d'un conteneur ouvert au niveau `maxNesting - 1` : la
    forme qu'il porte lui échappe, un navigateur l'affiche. Jusqu'à la limite, la forme est
    relevée ; un niveau de plus, l'imbrication l'est, dans le corps comme dans une chaîne publiée
    (dont la lecture du texte relève encore ce qu'elle voit sans l'analyse)."""
    dec = _load_decision()
    nesting = f"unmodelled_nesting: {container!r}"
    for level, expected in ((depth, [f"unmodelled_{kind}: {marker!r}" for kind, marker in found]),
                            (depth + 1, [nesting])):
        nested = _nested(text, quote, level)
        body = f"## Montage\n\n{nested}\n"
        result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body), tmp_path)
        assert result["verified"] is False
        assert _violations_of(result, "corps") == [f"corps {v}" for v in expected], result
        target = _safety_wiki(tmp_path)
        for fm, origin, where in (
                ({**SAFETY_FM, "review_notes": nested}, "fiche", "$.review_notes"),
                ({**SAFETY_FM, **_editorial(nested)}, "seo", "$.blocks[0].content_md"),
                ({**SAFETY_FM, **_editorial(nested)}, "fiche", "$.entity_data.editorial.function.content_md")):
            result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
            assert result["verified"] is False
            published = _violations_of(result, origin)
            if level == depth:
                assert published == [f"{origin} {where} {v}" for v in expected], result
            else:
                assert f"{origin} {where} {nesting}" in published, result


def test_safety_numeric_reference_defined_beyond_the_parser_limit_is_a_violation(tmp_path):
    """Définition de référence au-delà de la limite : markdown-it ne la lit pas, `![s][s]` n'est
    plus une image pour lui ; l'imbrication est relevée."""
    dec = _load_decision()
    text = "Voir ![s][s].\n\n" + "> " * 20 + "[s]: img/s.png"
    body = f"## Montage\n\n{text}\n"
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body), tmp_path)
    assert _violations_of(result, "corps") == ["corps unmodelled_nesting: 'blockquote_open'"], result
    target = _safety_wiki(tmp_path)
    for fm, origin, where in (
            ({**SAFETY_FM, "review_notes": text}, "fiche", "$.review_notes"),
            ({**SAFETY_FM, **_editorial(text)}, "seo", "$.blocks[0].content_md"),
            ({**SAFETY_FM, **_editorial(text)}, "fiche", "$.entity_data.editorial.function.content_md")):
        result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
        assert _violations_of(result, origin) == [
            f"{origin} {where} unmodelled_nesting: 'blockquote_open'"], result


@pytest.mark.parametrize("text, found", [
    # U+070F entre les chiffres : `52` écrit, `25` affiché
    ("Serrage de la vis de roue avant à \u070f5\u070f2 Nm selon atelier.", "unmodelled_display_order: 'U+070F'"),
    # Caractère de contrôle (DEL), invisible entre la valeur et son unité, écrit ou échappé
    ("Serrer la colonne à 25\x7fNm sur le véhicule.", "unmodelled_control_character: 'U+007F'"),
    ("Serrer la colonne à 25 N%7Fm sur le véhicule.", "unmodelled_control_character: 'U+007F'"),
    ("Serrer à %2425%24.", "unmodelled_formula: '$'"),
    # Barre de fraction : `1⁄2` affiché en fraction, lu `2`
    ("Serrer à 1\u20442 Nm.", "unmodelled_numeral: 'U+2044'"),
    # Numérateur de fraction : `⅟2` affiché en fraction, lu `2`, quoique son chiffre (`1`) épelle
    # sa valeur
    ("Serrer à \N{FRACTION NUMERATOR ONE}2 Nm.", "unmodelled_numeral: 'U+215F'"),
    # Caractère d'usage privé entre les chiffres : `5` lu, son affichage inconnu
    ("Serrer la colonne à \ue0002\ue0005 Nm.", "unmodelled_unknown_character: 'U+E000'"),
    # Lien Obsidian à libellé : `[[a|5]]` n'affiche que `5`, `2[[a|5]] Nm` s'affiche `25 Nm`
    ("Serrer la colonne à 2[[a|5]] Nm.", "unmodelled_obsidian: '[[a|5]]'"),
    # Identifiant de bloc masqué : `à 2 ^b5` puis `Nm` s'affiche `à 2` puis `Nm`, `5 Nm` lu
    ("Serrer la colonne à 2 ^b5\nNm.", "unmodelled_obsidian: '^b5'"),
])
def test_safety_numeric_unmodelled_construct_is_reported_with_the_values_read(tmp_path, text, found):
    """La forme non modélisée s'ajoute aux valeurs lues, jamais ne les remplace."""
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body), tmp_path)
    corps = _violations_of(result, "corps")
    assert f"corps {found}" in corps and any("numeric_source_not_captured" in v for v in corps), result
    result = dec._safety_numeric_exactitude({**SAFETY_FM, "review_notes": text}, SAFETY_BODY,
                                            _safety_wiki(tmp_path), tmp_path)
    notes = _violations_of(result, "fiche")
    assert f"fiche $.review_notes {found}" in notes and any(
        "numeric_source_not_captured" in v for v in notes), result


@pytest.mark.parametrize("text, found", [
    # Code inerte en tête : le HTML d'un bloc suivant reste relevé
    ('Le gabarit contient `<!--` en tête.\n\nVis de colonne serrée à <span dir="rtl"><span dir="ltr">Nm</span>'
     ' <span dir="ltr">25</span></span> en atelier.', [("raw_html", "<span"), ("raw_html", "</span")]),
    # Définition de note : GitHub y joint la ligne suivante, paresseuse ou indentée
    ("Serrer la vis[^n].\n\n[^n]: 25\nNm", [("footnote", "[^n]")]),
    ("Serrer la vis[^n].\n\n[^n]: 25\n    Nm", [("footnote", "[^n]")]),
    # Lien HTML : relevé, même sans valeur à lire
    ('Voir <a href="https://x.fr/m%C3%A9thode">la fiche</a>.', [("raw_html", "<a"), ("raw_html", "</a")]),
    # Code du corps tel qu'écrit : affiché tel quel, inerte ; lien automatique : pas du HTML
    ("Voir `<b>` et la fiche.", []),
    ("Voir <https://x.fr/m%C3%A9thode> et la fiche.", []),
    # Dès qu'un décodage change le corps, son code n'est plus inerte : un accent grave décodé
    # (échappement, entité) peut fabriquer le délimiteur qui le rendrait inerte
    ("Lire %60%3Cspan dir=rtl%3E%60 ici.", [("raw_html", "<span")]),
    ("Lire &#96;<span dir=rtl>&#96; ici.", [("raw_html", "<span")]),
    ("Voir `<b>` et https://x.fr/a%20b.", [("raw_html", "<b")]),
    ("Voir <https://x.fr/m%C3%A9thode> et `<b>` puis `$`.", [("raw_html", "<b"), ("formula", "$")]),
    ("```\n<span dir=rtl>\n```\n\nVoir https://x.fr/a%20b.", [("raw_html", "<span")]),
    ("    <span dir=rtl>\n\nVoir https://x.fr/a%20b.", [("raw_html", "<span")]),
    # Image : relevée, et son texte alternatif lu comme le texte, caractère échappé joint à ce qui
    # le suit, son code inerte seulement dans le corps tel qu'écrit
    ("Voir ![jeu $x$](i.png).", [("image", "i.png"), ("formula", "$")]),
    ("Voir ![jeu \\<span dir=rtl>](i.png).", [("image", "i.png"), ("raw_html", "<span")]),
    ("Voir ![%60%3Cbdo%3E%60](i.png).", [("image", "i.png"), ("raw_html", "<bdo")]),
])
def test_safety_numeric_body_construct_is_found_in_every_block_and_decoding(tmp_path, text, found):
    """Corps : chaque bloc et chaque décodage est relu en entier ; le code n'est inerte que dans le
    corps tel qu'écrit."""
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body), tmp_path)
    assert result["verified"] is (not found), result
    assert _violations_of(result, "corps") == [
        f"corps unmodelled_{kind}: {marker!r}" for kind, marker in found], result


def test_safety_numeric_published_string_code_is_never_inert(tmp_path):
    """Chaîne publiée : un lecteur peut la servir sous toute forme, son code n'est jamais inerte."""
    dec = _load_decision()
    text = "Voir `<b>` et la fiche."
    target = _safety_wiki(tmp_path)
    for fm, origin, where in (
            ({**SAFETY_FM, "review_notes": text}, "fiche", "$.review_notes"),
            ({**SAFETY_FM, **_editorial(text)}, "seo", "$.blocks[0].content_md")):
        result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
        assert _violations_of(result, origin) == [f"{origin} {where} unmodelled_raw_html: '<b'"], result


@pytest.mark.parametrize("url, found", [
    ("https://x.fr/a?c=\u202emN%2052", "unmodelled_display_order: 'U+202E'"),
    ("https://x.fr/a?c=%E2%80%AEmN%2052", "unmodelled_display_order: 'U+202E'"),
    ("https://x.fr/a?c=%7F", "unmodelled_control_character: 'U+007F'"),
])
def test_safety_numeric_unmodelled_character_in_a_source_url_is_a_violation(tmp_path, url, found):
    dec = _load_decision()
    fm = {**SAFETY_FM, **_SEO_BASE, "source_refs": [{"kind": "web", "url": url}]}
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, _safety_wiki(tmp_path), tmp_path)
    for origin, where in (("seo", "$.sources[0].url"), ("fiche", "$.source_refs[0].url")):
        assert _violations_of(result, origin) == [f"{origin} {where} {found}"], result


@pytest.mark.parametrize("text", [
    "Crémaillère de direction : vue ; la direction (rtl, unicode-bidi) : crémaillère.",
    "Kit à 30 € ; jeu contrôlé.",
    "Serrer à 25\\circ C.",                       # commande TeX hors formule : affichée telle qu'écrite
    "Serrer\tla vis à la main.",                 # tabulation : un blanc, pas un caractère de contrôle
    "Contrôle à 10:00:00, puis à 10:30:45.",      # heure : pas un code emoji
    "Surface en m² ; étape ① : serrer à la main.",  # exposant, chiffre cerclé : décomposés en eux-mêmes
])
def test_safety_numeric_words_of_an_unmodelled_construct_raise_no_false_positive(tmp_path, text):
    """Seule la forme est relevée, jamais le vocabulaire : ni « direction », ni un prix sans `$`, ni
    une commande TeX hors formule."""
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    target = _safety_wiki(tmp_path, body=body)
    for fm in ({**SAFETY_FM, "review_notes": text}, {**SAFETY_FM, **_editorial(text)}):
        result = dec._safety_numeric_exactitude(fm, body, target, tmp_path)
        assert result["verified"] is True, result


def test_bidi_controls_are_the_unicode_bidi_control_property():
    """`_BIDI_CONTROLS` est la propriété Bidi_Control : chaque caractère de formatage
    bidirectionnel explicite (plongement, forçage, isolat et leur fin) et les trois marques."""
    import unicodedata

    dec = _load_decision()
    explicit = {cp for cp in range(0x110000) if unicodedata.bidirectional(chr(cp)) in
                ("LRE", "RLE", "PDF", "LRO", "RLO", "LRI", "RLI", "FSI", "PDI")}
    marks = {ord(unicodedata.lookup(name))
             for name in ("ARABIC LETTER MARK", "LEFT-TO-RIGHT MARK", "RIGHT-TO-LEFT MARK")}
    assert dec._BIDI_CONTROLS == explicit | marks


@pytest.mark.parametrize("content_md, raw", [
    # Les surfaces R3 passent le rendu de la projection par `stripHtml`, qui supprime `"` (rendu
    # `&quot;`) et toute séquence `&mot;`, entité ou non, puis joint les blocs sans séparateur
    ('Serrer la colonne à 25"Nm.', "25Nm"),
    ("Serrer la colonne à 25&quot;Nm.", "25Nm"),
    ("Serrer la colonne à 25&amp;quot;Nm.", "25Nm"),                # entité échappée, décodée à l'affichage
    ("Serrer la colonne à 25&#34;Nm.", "25Nm"),                     # entité numérique, supprimée aussi
    ('Serrer la colonne à 25"N"m.', "25Nm"),
    ("Serrer la colonne à 25&nbsp_;Nm.", "25Nm"),
    ("Serrer la colonne à 25 &x; Nm.", "25 Nm"),
    ('Chauffer à 25"°C.', "25°C"),                                    # signe d'unité gardé
    ("Serrer à 25&Amp;quot;Nm.", "25Nm"),                              # `&amp;` sans casse (`/gi`)
])
def test_safety_numeric_published_string_is_read_as_its_skeleton(tmp_path, content_md, raw):
    """La lecture squelette ne garde que chiffres, lettres, espaces et signes d'unité, sans `"` ni
    séquence `&mot;` : ce qu'affichent ces surfaces."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude({**SAFETY_FM, **_editorial(content_md)}, SAFETY_BODY,
                                            target, tmp_path)
    for origin, where in (("seo", "$.blocks[0].content_md"),
                          ("fiche", "$.entity_data.editorial.function.content_md")):
        assert _violations_of(result, origin) == [
            f"{origin} {where} (littérale squelette) numeric_source_not_captured: {raw!r}"], result


@pytest.mark.parametrize("content_md, numbered", [
    ("Serrer la colonne à 25\n- Nm", []),
    # Liste numérotée : son numéro n'est pas du texte, et il précède l'unité
    ("Serrer la colonne à 25\n1. Nm", ["unmodelled_ordered_list_number: '1. Nm'"]),
])
def test_safety_numeric_published_string_blocks_are_read_joined(tmp_path, content_md, numbered):
    """`stripHtml` joint sans séparateur les blocs du rendu de la projection (`<p>…25</p><ul><li>Nm`
    affiché `25Nm`) : la lecture `projection jointe` les lit ainsi."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    result = dec._safety_numeric_exactitude({**SAFETY_FM, **_editorial(content_md)}, SAFETY_BODY,
                                            target, tmp_path)
    for origin, where in (("seo", "$.blocks[0].content_md"),
                          ("fiche", "$.entity_data.editorial.function.content_md")):
        assert _violations_of(result, origin) == [
            f"{origin} {where} (projection jointe) numeric_source_not_captured: '25Nm'"] + [
            f"{origin} {where} {v}" for v in numbered], result


@pytest.mark.parametrize("text, shown, published", [
    # Le navigateur affiche le numéro de l'élément (`<ol start="25">`, `)` affiché `.`) ; la
    # projection numérote ses listes depuis 1 et ne lit pas `)`
    ("25. Nm de couple", ["ordered_list_number: '25. Nm'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '25. Nm'", "ordered_list_number: '1. Nm'"]),
    ("24. Serrer\n1. Nm de couple",                    # second élément : affiché 25, projeté 2
     ["ordered_list_number: '25. Nm'"],
     ["ordered_list_number: '25. Nm'", "ordered_list_number: '2. Nm'"]),
    ("2. 5 Nm de couple", ["ordered_list_number: '2. 5'"],
     ["ordered_list_number: '2. 5'", "ordered_list_number: '1. 5'"]),
    # Chiffre relevé à la première lecture qui en ouvre une, telle qu'écrite puis en squelette :
    # `"5` (squelette seul), `1"5` (affiché `1`, pas `15`), `<b>5</b>` (rendue seulement)
    ('2. "5 de couple', ["ordered_list_number: '2. 5'"],
     ["ordered_list_number: '2. 5'", "ordered_list_number: '1. 5'"]),
    ('3. 1"5 de couple', ["ordered_list_number: '3. 1'"],
     ["ordered_list_number: '3. 1'", "ordered_list_number: '1. 1'"]),
    ("2. <b>5</b> de couple", ["raw_html: '<b'", "raw_html: '</b'", "ordered_list_number: '2. 5'"],
     ["raw_html: '<b'", "raw_html: '</b'", "ordered_list_number: '2. 5'",
      "ordered_list_number: '1. 5'"]),
    ("0. Nm de couple", ["ordered_list_number: '0. Nm'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '0. Nm'", "ordered_list_number: '1. Nm'"]),
    ("25) Nm de couple", ["ordered_list_number: '25. Nm'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '25. Nm'"]),
    ("25.     Nm de couple", ["ordered_list_number: '25. Nm'"],     # contenu en code indenté
     ["leading_unit: 'Nm'", "ordered_list_number: '25. Nm'", "ordered_list_number: '1. Nm'"]),
    ("> 25. Nm de couple", ["ordered_list_number: '25. Nm'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '25. Nm'"]),
    ("25.\n    Nm de couple", ["ordered_list_number: '25. Nm'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '25. Nm'"]),
    ("1. mm d'épaisseur minimale", ["ordered_list_number: '1. mm'"],
     ["leading_unit: 'mm'", "ordered_list_number: '1. mm'"]),
    ("1. mm, jamais sous 2 mm", ["ordered_list_number: '1. mm'"],    # même unité plus loin
     ["leading_unit: 'mm'", "ordered_list_number: '1. mm'"]),
    ("3. millimètres d'épaisseur", ["ordered_list_number: '3. millimètre'"],
     ["leading_unit: 'millimètre'", "ordered_list_number: '3. millimètre'",
      "ordered_list_number: '1. millimètre'"]),
    # Premier contenu en bloc de code ou en bloc HTML : le numéro s'affiche devant lui
    ("1. ```\n   Nm de couple\n   ```", ["ordered_list_number: '1. Nm'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '1. Nm'"]),
    ("1. <div>\n   Nm de couple\n   </div>", ["raw_html: '<div'", "ordered_list_number: '1. Nm'"],
     ["leading_unit: 'Nm'", "raw_html: '<div'", "raw_html: '</div'", "ordered_list_number: '1. Nm'"]),
    # Sous-liste numérotée : numérotée par elle-même, pas par l'élément qui la contient
    ("1. Serrer\n   1. Nm de couple", ["ordered_list_number: '1. Nm'"],
     ["ordered_list_number: '1. Nm'"]),
    # Item qui suit une sous-liste numérotée : numéroté dans sa liste, pas dans la sous-liste
    ("1. Serrer\n   1. Contrôler\n2. Nm de couple", ["ordered_list_number: '2. Nm'"],
     ["ordered_list_number: '2. Nm'", "ordered_list_number: '1. Nm'"]),
    ("> 1. Serrer\n>    1. Contrôler\n> 2. Nm de couple", ["ordered_list_number: '2. Nm'"],
     ["ordered_list_number: '2. Nm'"]),
    ("1. Serrer\n   1. Contrôler\n\n   Puis vérifier.\n2. Nm de couple",
     ["ordered_list_number: '2. Nm'"],
     ["ordered_list_number: '2. Nm'", "ordered_list_number: '1. Nm'"]),
    # Case à cocher en tête de paragraphe (tout caractère entre crochets, suivi d'un blanc ou de
    # la fin de ligne), affichée en case par GitHub et Obsidian : le numéro se lit avec ce qui la
    # suit ; collée au texte, elle n'en est pas une ; le rendu projeté, qui n'en a pas, l'affiche
    # telle qu'écrite (`[ ]`, lue en squelette, y laisse le numéro devant l'unité)
    ("25. [x] Nm de couple", ["ordered_list_number: '25. Nm'"], ["ordered_list_number: '25. Nm'"]),
    ("25. [X] Nm de couple", ["ordered_list_number: '25. Nm'"], ["ordered_list_number: '25. Nm'"]),
    ("25. [b] Nm de couple", ["ordered_list_number: '25. Nm'"], ["ordered_list_number: '25. Nm'"]),
    ("25. [ ] Nm de couple", ["ordered_list_number: '25. Nm'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '25. Nm'", "ordered_list_number: '1. Nm'"]),
    ("25. [x]\nNm de couple", ["ordered_list_number: '25. Nm'"], ["ordered_list_number: '25. Nm'"]),
    ("25. [5] Nm de couple", ["ordered_list_number: '25. 5'"],
     ["ordered_list_number: '25. 5'", "ordered_list_number: '1. 5'"]),
    ("25. [x]Nm de couple", [], []),
    ("25. [x] Serrer la vis", [], []),
    # … en tête de paragraphe seulement : un bloc de code n'en a pas
    ("25.      [x] Nm de couple", [], []),
    ("25.     [x] Nm de couple", [], []),
    # Numéro suivi d'un mot : rien ne se lit avec lui
    ("1. Serrer la vis.\n2. Contrôler le jeu.", [], []),
    ("3. Contrôler le jeu à la main.", [], []),
    # Coût : un mot qui commence par une unité est relevé comme elle
    ("1. Inchangé : la vis se réutilise.", ["ordered_list_number: '1. Inch'"],
     ["leading_unit: 'Inch'", "ordered_list_number: '1. Inch'"]),
    ("3. bardage retiré", ["ordered_list_number: '3. bar'"],
     ["leading_unit: 'bar'", "ordered_list_number: '3. bar'", "ordered_list_number: '1. bar'"]),
    # Coût : sous-liste vide d'abord, le numéro est lu avec le bloc qui la suit
    ("1. -\n\n   Nm de couple\n2. Serrer", ["ordered_list_number: '1. Nm'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '1. Nm'"]),
    # Élément vide, sous-liste à puces, liste suivante : aucun numéro ne précède l'unité
    ("1. Serrer\n2.\n\n- Nm de couple", [], []),
    ("1. Serrer\n   - Nm de couple", [], []),
    ("1. Serrer\n\n- Nm de couple", [], []),
    # Bloc de code ou bloc HTML non vide d'abord : le numéro s'affiche devant lui,
    # pas devant l'unité
    ("1. ```\n   x\n   ```\n   Nm de couple", [], []),
    ("1. <div>x</div>\n\n   Nm de couple", ["raw_html: '<div'"], ["raw_html: '<div'", "raw_html: '</div'"]),
    # Premier bloc qui n'affiche rien (code, titre ou cellule vides, lien sans libellé, espace) :
    # sans ligne, il laisse le numéro au bloc suivant (GitHub affiche `25.` puis `Nm`)
    ("25. ```\n    ```\n    Nm de couple", ["ordered_list_number: '25. (bloc vide)'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '25. (bloc vide)'"]),
    ("24. Serrer\n25. ~~~\n    ~~~\n    Nm de couple", ["ordered_list_number: '25. (bloc vide)'"],
     ["ordered_list_number: '25. (bloc vide)'"]),
    ("25. #\n    Nm de couple", ["ordered_list_number: '25. (bloc vide)'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '25. (bloc vide)'"]),
    ("25. |  | Nm |\n    |--|--|", ["ordered_list_number: '25. (bloc vide)'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '25. (bloc vide)'",
      "ordered_list_number: '1. Nm'"]),
    ("25. [](https://x.y)\n\n    Nm de couple", ["ordered_list_number: '25. (bloc vide)'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '25. (bloc vide)'"]),
    ("25. &nbsp;\n\n    Nm de couple", ["ordered_list_number: '25. (bloc vide)'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '25. (bloc vide)'"]),
    ("25. &#32;\n\n    Nm de couple", ["ordered_list_number: '25. (bloc vide)'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '25. (bloc vide)'"]),
    # Coût : bloc de code d'une ligne blanche, que le navigateur affiche sur une ligne
    ("25. ```\n\n    ```\n    Nm de couple", ["ordered_list_number: '25. (bloc vide)'"],
     ["leading_unit: 'Nm'", "ordered_list_number: '25. (bloc vide)'"]),
    # Image (Markdown ou HTML) ou code en ligne : le numéro s'affiche à leur ligne, pas avec
    # l'unité qui suit
    ("25. ![](i.png)\n\n    Nm de couple", ["image: 'i.png'"],
     ["leading_unit: 'Nm'", "image: 'i.png'"]),
    ('25. <img src="i.png">\n\n    Nm de couple', ["raw_html: '<img'"],
     ["leading_unit: 'Nm'", "raw_html: '<img'"]),
    ('25. <img src="i.png"><img src="i.png">\n\n    Nm de couple',
     ["raw_html: '<img'"], ["leading_unit: 'Nm'", "raw_html: '<img'"]),
    ("25. `vis`\n\n    Nm de couple", [], []),
])
def test_safety_numeric_ordered_list_number_before_a_unit_or_digit_is_a_violation(
        tmp_path, text, shown, published):
    """Le numéro d'un élément de liste ordonnée n'est pas du texte : la lecture ne le voit pas, le
    lecteur le lit avec l'unité ou le chiffre qui ouvre l'élément (`25.` puis `Nm`). Il est relevé
    sous le numéro qu'affiche le rendu et, dans une chaîne publiée, sous celui de la projection."""
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body), tmp_path)
    assert result["verified"] is (not shown), result
    assert [v for v in _violations_of(result, "corps") if " unmodelled_" in v] == [
        f"corps unmodelled_{v}" for v in shown], result
    target = _safety_wiki(tmp_path)
    for fm, origin, where in (
            ({**SAFETY_FM, "review_notes": text}, "fiche", "$.review_notes"),
            ({**SAFETY_FM, **_editorial(text)}, "seo", "$.blocks[0].content_md"),
            ({**SAFETY_FM, **_editorial(text)}, "fiche", "$.entity_data.editorial.function.content_md")):
        result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
        assert result["verified"] is (not published), result
        assert [v for v in _violations_of(result, origin) if " unmodelled_" in v] == [
            f"{origin} {where} unmodelled_{v}" for v in published], result


@pytest.mark.parametrize("block, published", [
    ("25. {c}\n\n    Nm de couple", ["leading_unit: 'Nm'"]),
    ("25. # {c}\n    Nm de couple", ["leading_unit: 'Nm'"]),
    ("25. [{c}](https://x.y)\n\n    Nm de couple", ["leading_unit: 'Nm'"]),
    ("25. | {c} | Nm |\n    |--|--|", ["leading_unit: 'Nm'", "ordered_list_number: '1. Nm'"]),
    ("25. ```\n    {c}\n    ```\n    Nm de couple", ["leading_unit: 'Nm'"]),
])
@pytest.mark.parametrize("invisible", [
    "\u200b", "\u2060", "\ufeff", "\u00ad",      # invisibles
    "\u3164", "\u2800",                           # glyphes blancs
    "&#8203;",                                    # invisible en entité
])
def test_safety_numeric_ordered_item_whose_first_block_shows_no_character_is_a_violation(
        tmp_path, block, published, invisible):
    """Premier bloc fait de caractères invisibles ou de glyphes blancs : il n'affiche aucun
    caractère, le numéro de l'item se lit avec le bloc suivant (`25.` puis `Nm`)."""
    dec = _load_decision()
    text = block.format(c=invisible)
    body = f"## Montage\n\n{text}\n"
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body),
                                            tmp_path)
    assert [v for v in _violations_of(result, "corps") if " unmodelled_" in v] == [
        "corps unmodelled_ordered_list_number: '25. (bloc vide)'"], result
    shown = ["ordered_list_number: '25. (bloc vide)'"]
    expected = published[:1] + shown + published[1:]
    target = _safety_wiki(tmp_path)
    for fm, origin, where in (
            ({**SAFETY_FM, "review_notes": text}, "fiche", "$.review_notes"),
            ({**SAFETY_FM, **_editorial(text)}, "seo", "$.blocks[0].content_md"),
            ({**SAFETY_FM, **_editorial(text)}, "fiche",
             "$.entity_data.editorial.function.content_md")):
        result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
        assert [v for v in _violations_of(result, origin) if " unmodelled_" in v] == [
            f"{origin} {where} unmodelled_{v}" for v in expected], result


@pytest.mark.parametrize("text, unit", [
    ("mm d'épaisseur minimale", "mm"),
    ("\N{RIGHT-TO-LEFT MARK}mm d'épaisseur minimale", "mm"),     # lue aussi en squelette
    ("barre de torsion contrôlée", "bar"),       # coût : un mot qui commence par une unité
    # Rapportée telle qu'écrite : le squelette lit le signe micro en mu grec
    ("\N{MICRO SIGN}m de voile maximal", "\N{MICRO SIGN}m"),
    ("(mm d'épaisseur minimale)", "mm"),          # lue en squelette seulement
    ("&#109;m d'épaisseur minimale", "mm"),       # lue rendue seulement
    ("m%6D d'épaisseur minimale", "mm"),          # lue décodée seulement
    # Unité en lettres, rapportée sous la forme que lit `numeric_exactitude`
    ("newtons-mètres de couple", "newton"),
    ("millimètres d'épaisseur minimale", "millimètre"),
    ("degrés de chauffe", "degré"),
    ("Inchangé depuis la révision", "Inch"),      # coût : un mot qui commence par une unité en lettres
    ("daNm de couple", "daNm"),
    ("(daNm de couple)", "daNm"),
    # Le champ précédent finit par un nombre, ou par un nombre et un début d'entité que celui-ci
    # achève (`25&nbsp` puis `;mm`, `25&` puis `#32;mm`) : le squelette du texte joint lit la valeur
    (";mm d'épaisseur minimale", "mm"),
    ("nbsp;mm d'épaisseur minimale", "mm"),
    ("x;Nm de couple", "Nm"),
    ("#32;mm d'épaisseur minimale", "mm"),        # référence numérique : achevée après `&` seul
    ('"' * 44 + "mm d'épaisseur minimale", "mm"),
    ("- N\n- m d'épaisseur", "Nm"),               # blocs joints par la projection
    ("x [y](mm)", "mm"),                          # destination de lien, lue telle qu'écrite
    ("[](x y)mm d'épaisseur", "mm"),              # lien vide : lue sans balisage
    ("[\n\n](x)mm d'épaisseur", "mm"),             # coût : crochets en blocs, lue sans structure
])
def test_safety_numeric_published_string_leading_unit_is_a_violation(tmp_path, text, unit):
    """Une chaîne publiée qui commence par une unité : un nombre qui finit le texte affiché juste
    avant (champ voisin, joint sans séparateur par `stripHtml`) s'y lirait avec elle. Le corps,
    dont chaque bloc est une clause, n'est pas concerné."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    for fm, origin, where in (
            ({**SAFETY_FM, "review_notes": text}, "fiche", "$.review_notes"),
            ({**SAFETY_FM, **_editorial(text)}, "seo", "$.blocks[0].content_md")):
        result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
        assert result["verified"] is False
        assert f"{origin} {where} unmodelled_leading_unit: {unit!r}" in _violations_of(result, origin), result
    body = f"## Montage\n\n{text.lstrip(chr(0x200F))}\n"
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body), tmp_path)
    assert result["verified"] is True, result


def test_safety_numeric_published_key_leading_unit_is_a_violation(tmp_path):
    """Clé publiée qui commence par une unité : relevée comme toute chaîne publiée."""
    dec = _load_decision()
    fm = {**SAFETY_FM, "mm d'épaisseur minimale": "voir atelier"}
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, _safety_wiki(tmp_path), tmp_path)
    assert result["sample"] == [
        "fiche $[\"mm d'épaisseur minimale\"] (clé) unmodelled_leading_unit: 'mm'"], result


@pytest.mark.parametrize("text, mark", [
    # Marque en tête : relevée quel que soit l'ordre affiché (ici `Nm 25` : le paragraphe passe de
    # droite à gauche, mais `25`, qui suit une lettre latine, reste après `Nm`)
    ("\N{RIGHT-TO-LEFT MARK}Nm 25", "U+200F"),
    ("\N{ARABIC LETTER MARK}Nm 25", "U+061C"),
    # Caractère de classe AL en tête (U+070F fait afficher ce cas `25 Nm`)
    ("\u070fNm \u070f25", "U+070F"),
])
def test_safety_numeric_leading_mark_is_a_violation(tmp_path, text, mark):
    """Dans le corps, l'ordre d'affichage est relevé ; dans une chaîne publiée, l'unité qui suit
    la marque l'est aussi (`test_safety_numeric_published_string_leading_unit_is_a_violation`)."""
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body), tmp_path)
    assert _violations_of(result, "corps") == [f"corps unmodelled_display_order: {mark!r}"], result
    target = _safety_wiki(tmp_path)
    for fm, origin, where in (
            ({**SAFETY_FM, "review_notes": text}, "fiche", "$.review_notes"),
            ({**SAFETY_FM, **_editorial(text)}, "seo", "$.blocks[0].content_md")):
        result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
        assert _violations_of(result, origin) == [f"{origin} {where} unmodelled_leading_unit: 'Nm'",
                                                  f"{origin} {where} unmodelled_display_order: {mark!r}"], result


@pytest.mark.parametrize("text", [
    "Serrer la colonne à \u05ff5\u05ff2 Nm.",       # non attribué (Unicode 16 compris)
    "Serrer la colonne à \U0001ccf2\U0001ccf5 Nm.",  # chiffres détourés : attribués en Unicode 16
])
def test_safety_numeric_character_unknown_to_some_unicode_version_is_never_verified(tmp_path, text):
    """Caractère que la base Unicode de l'interpréteur ne définit pas : relevé (`unknown_character`) ;
    qu'elle le définisse (base plus récente), il est lu ou relevé selon ses propriétés. Jamais
    vérifié, quelle que soit la version."""
    dec = _load_decision()
    body = f"## Montage\n\n{text}\n"
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body), tmp_path)
    assert result["verified"] is False, result
    target = _safety_wiki(tmp_path)
    for fm in ({**SAFETY_FM, "review_notes": text}, {**SAFETY_FM, **_editorial(text)}):
        result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
        assert result["verified"] is False, result


def test_safety_numeric_lone_surrogate_in_a_published_string_is_a_violation(tmp_path):
    """Demi-codet isolé dans une chaîne du frontmatter (le corps, lu en UTF-8, n'en porte pas) :
    son affichage est inconnu, il est relevé."""
    dec = _load_decision()
    text = "Serrer la colonne à 25 Nm\ud800."
    target = _safety_wiki(tmp_path)
    for fm, origin, where in (
            ({**SAFETY_FM, "review_notes": text}, "fiche", "$.review_notes"),
            ({**SAFETY_FM, **_editorial(text)}, "seo", "$.blocks[0].content_md")):
        result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
        assert f"{origin} {where} unmodelled_unknown_character: 'U+D800'" in _violations_of(result, origin), result


def test_safety_numeric_lone_surrogate_in_a_published_key_is_a_violation(tmp_path):
    """Demi-codet isolé dans une clé du frontmatter : relevé, et le rapport, qui cite la clé,
    s'encode en UTF-8."""
    import json
    dec = _load_decision()
    fm = {**SAFETY_FM, "\ud835cle": "texte"}
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, _safety_wiki(tmp_path), tmp_path)
    assert result["sample"] == [
        "fiche $[\"\\ud835cle\"] (clé) unmodelled_unknown_character: 'U+D835'"], result
    json.dumps(result, ensure_ascii=False).encode("utf-8")


def test_safety_report_cites_a_lone_surrogate_of_a_slug_as_written_and_no_publisher(tmp_path):
    """Demi-codet isolé dans un slug cité : le détail des conditions le cite tel qu'écrit, et la
    sortie de `promote.py` l'échappe (`test_promote.py`). Dans un éditeur du catalogue, il
    n'identifie aucun éditeur, et l'éditeur qui écrit son échappement en texte en est un."""
    dec = _load_decision()
    rule = {"rule": "contrôle visuel", "citations": [{"source": "\ud835x"}],
            "evidence": {"confidence": "high", "source_policy": "1_high",
                         "reviewed": False, "diagnostic_safe": False}}
    local = _local(dec, tmp_path, fm={**SAFETY_FM, "safety_rules": [rule]})
    assert local["details"]["proof_sources_min"]["not_counted"] == {
        "\ud835x": "absent_du_catalogue"}, local["details"]["proof_sources_min"]
    sources = SAFETY_PROOF_SOURCES[:1] + (
        {"slug": "preuve_manuel", "type": "oem_manual", "publisher": "Organisme \ud835C"},
        {"slug": "preuve_norme", "type": "normative_standard", "publisher": "Organisme \\ud835C"})
    local = _local(dec, tmp_path, sources=sources)
    detail = local["details"]["proof_sources_min"]
    assert local["conditions"]["proof_sources_min"] is False, detail
    assert detail["publishers"] == {"constructeur a": ["preuve_atelier"],
                                    "organisme \\ud835c": ["preuve_norme"]}, detail
    assert detail["not_counted"] == {"preuve_manuel": "publisher_absent"}, detail
    sources = SAFETY_PROOF_SOURCES[:2] + (
        {"slug": "preuve_\ud835n", "type": "normative_standard", "publisher": "Organisme C"},)
    local = _local(dec, tmp_path, sources=sources)
    assert local["details"]["proof_sources_min"]["publishers"]["organisme c"] == ["preuve_\ud835n"]


@pytest.mark.parametrize("escape", ["&#37;", "&#x25;", "&percnt;"])
def test_safety_numeric_escape_revealed_by_an_entity_is_decoded_everywhere(tmp_path, escape):
    """Un échappement d'URL qui n'apparaît qu'une fois l'entité résolue est décodé dans une chaîne
    publiée comme dans le corps."""
    dec = _load_decision()
    text = f"Serrer la colonne à 25 N{escape}6D."
    body = f"## Montage\n\n{text}\n"
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body), tmp_path)
    assert _violations_of(result, "corps") == [
        f"corps ({form}) numeric_source_not_captured: '25 Nm'"
        for form in ("rendue décodée", "sans balisage décodée")], result
    result = dec._safety_numeric_exactitude({**SAFETY_FM, "review_notes": text}, SAFETY_BODY,
                                            _safety_wiki(tmp_path), tmp_path)
    assert _violations_of(result, "fiche") == [
        "fiche $.review_notes (rendue décodée) numeric_source_not_captured: '25 Nm'"], result


def test_safety_numeric_sample_is_capped_but_every_violation_is_counted(tmp_path):
    """L'échantillon rapporté est borné à 8 ; le total compte chaque violation."""
    dec = _load_decision()
    body = "## Montage\n\n" + "\n\n".join(f"Serrer la vis {i} à {20 + i} Nm." for i in range(12)) + "\n"
    result = dec._safety_numeric_exactitude(SAFETY_FM, body, _safety_wiki(tmp_path, body=body), tmp_path)
    assert result["violations_total"] == 24
    assert result["sample"] == [f"corps (rendue) numeric_source_not_captured: '{20 + i} Nm'" for i in range(8)]


@pytest.mark.parametrize("url", [
    "https://fr.wikipedia.org/wiki/Frein_%C3%A0_disque",       # forme des URL réelles du corpus
    "https://x.fr/plaquettes-de-frein/m%C3%A9thode-%C3%A9tape-2",
])
def test_safety_numeric_accented_source_url_is_no_value(tmp_path, url):
    """Une URL de source aux caractères accentués échappés n'affiche aucune valeur : aucun faux
    positif (`%C3%A0` affiché `à`, jamais lu `3%`), dans le frontmatter comme dans le corps."""
    dec = _load_decision()
    body = f"## Montage\n\nVoir {url}.\n"
    target = _safety_wiki(tmp_path, body=body)
    fm = {**SAFETY_FM, "source_refs": [{"kind": "web", "url": url}]}
    result = dec._safety_numeric_exactitude(fm, body, target, tmp_path)
    assert result["verified"] is True, result


@pytest.mark.parametrize("text, decoded", [
    ("N%C2%B7m", "N·m"), ("N%6D", "Nm"), ("N%6d", "Nm"), ("%32%35%20%4E%6D", "25 Nm"),
    ("m%C3%A9thode", "méthode"), ("page%20123", "page 123"),
    # Après un nombre, espaces compris : le `%` peut être un signe pour cent, la suite reste écrite.
    ("50%C3%A9", "50%C3%A9"), ("50 %C3%A9", "50 %C3%A9"), ("50\xa0%C3%A9", "50\xa0%C3%A9"),
    ("remise-50%20ete", "remise-50%20ete"),
    # Octet qui ne forme pas un caractère UTF-8 : reste tel qu'écrit (`%XX`).
    # Deux octets gardés consécutifs : séparés, jamais lus `9%`.
    ("%E9%E9", "%E9·%E9"), ("%e9%e9", "%E9·%E9"), ("caf%C3%A9%20%E9", "café %E9"), ("%C3", "%C3"),
    ("100%", "100%"), ("%ZZ", "%ZZ"), ("%", "%"), ("a%2", "a%2"),
])
def test_percent_decoded(text, decoded):
    assert _load_decision()._percent_decoded(text) == decoded


@pytest.mark.parametrize("text, shown", [
    # Affichage de type IRI, plus strict que RFC 3987 §3.2 : tout échappement ASCII reste tel
    # qu'écrit, seuls les caractères non ASCII valides sont décodés ; deux échappements gardés
    # consécutifs sont séparés (`·`)
    ("m%C3%A9thode", "méthode"), ("N%C2%B7m", "N·m"), ("N%6D", "N%6D"),
    ("%32%35%20%4E%6D", "%32·%35·%20·%4E·%6D"), ("%C3%A9%45", "é%45"), ("caf%C3%A9%20%E9", "café%20·%E9"),
    # Octet invalide : reste tel qu'écrit, casse comprise
    ("%e9%e9", "%e9·%e9"), ("%E9%E9", "%E9·%E9"), ("%c3", "%c3"),
    ("50%C3%A9", "50%C3%A9"), ("100%", "100%"), ("%ZZ", "%ZZ"),
    # Caractère de contrôle : non ASCII (C1) décodé, puis relevé ; ASCII (DEL) tel qu'écrit
    ("x%C2%80", "x\x80"), ("%7F", "%7F"),
])
def test_percent_decoded_keeps_ascii_escapes_as_written(text, shown):
    assert _load_decision()._percent_decoded(text, keep_ascii=True) == shown


@pytest.mark.parametrize("url, found", [
    ("https://x.fr/m%C3%A9thode", []),                       # caractère non ASCII : affiché décodé
    ("https://x.fr/v2/page%20123", []),
    ("https://x.fr/25 N%6D", [("littérale décodée", "25 Nm")]),
    # Échappements ASCII : affichés tels qu'écrits, sans valeur lue entre deux échappements, puis décodés
    ("https://x.fr/%32%35%20%4E%6D", [("littérale décodée", "25 Nm")]),
    ("https://commons.wikimedia.org/wiki/Special:FilePath/ALFA%20ROMEO%20badge%20%28cropped%29.jpg", []),
    ("https://x.fr/docs/plaquettes%20de%20frein%20%28avant%29.pdf", []),
    ("https://x.fr/guide/l%27%20entretien-des-freins", []),
    # Faux positifs conservateurs, documentés : un `%` qui suit un nombre est lu comme un signe
    # pour cent, et les chiffres de la suite non décodée comme une valeur.
    ("https://x.fr/25%20N%C2%B7m", [("littérale", "25%"), ("littérale", "20N·m")]),
    ("https://x.fr/remise-50%20ete", [("littérale", "50%")]),
    ("https://x.fr/50%C3%A9", [("littérale", "50%"), ("littérale", "3%")]),
    ("https://x.fr/50 %C3%A9", [("littérale", "50 %"), ("littérale", "3%")]),
])
def test_safety_numeric_published_url_is_read_percent_decoded(tmp_path, url, found):
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    fm = {**SAFETY_FM, **_SEO_BASE, "source_refs": [{"kind": "web", "url": url}]}
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
    for origin, where in (("seo", "$.sources[0].url"), ("fiche", "$.source_refs[0].url")):
        assert _violations_of(result, origin) == [
            f"{origin} {where} ({form}) numeric_source_not_captured: {raw!r}" for form, raw in found], result


def _diagnostic_numeric(dec, tmp_path, *relations):
    target = _safety_wiki(tmp_path)
    fm = {**SAFETY_FM, "diagnostic_relations": list(relations)}
    return dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)


def test_safety_numeric_value_projected_by_diagnostic_export_is_unsourced(tmp_path):
    """`part_role` est publié tel quel par l'export diagnostic : une valeur dimensionnée y est
    non sourcée, comme dans le texte que projette l'export SEO."""
    dec = _load_decision()
    result = _diagnostic_numeric(dec, tmp_path, _RELATION, {
        **_RELATION, "part_role": "Une colonne usée de 2 mm au roulement durcit le braquage."})
    assert result["published"]["diagnostic"] is True
    assert _violations_of(result, "diagnostic") == [
        "diagnostic $.relations[1].part_role (littérale) numeric_source_not_captured: '2 mm'"], result


def test_safety_numeric_diagnostic_identifiers_raise_no_false_positive(tmp_path):
    """Vocabulaire fermé, empreinte, source à partie, portée véhicule : chaque chaîne publiée
    est lue, aucune ne porte de valeur dimensionnée."""
    import hashlib
    dec = _load_decision()
    relation = {**_RELATION, "vehicle_scope": {"fuel": "diesel"}, "sources": ["preuve_atelier_p12"],
                "citations": [{"source": "preuve_atelier", "start": 0, "end": 4,
                               "quote_sha256": "sha256:" + hashlib.sha256(b"x").hexdigest()}]}
    result = _diagnostic_numeric(dec, tmp_path, relation)
    assert result["published"]["diagnostic"] is True
    assert result["verified"] is True, result


@pytest.mark.parametrize("field, value, raw", [
    ("symptom_slug", "bruit-2mm", "2mm"),
    ("system_slug", "freinage-5bar", "5bar"),
    ("cause_slug", "usure-280mm", "280mm"),
])
def test_safety_numeric_diagnostic_slug_with_a_dimension_is_flagged(tmp_path, field, value, raw):
    """Aucun champ n'est exempté par son type : un slug porteur d'un motif chiffre + unité est
    lu comme tout texte publié. Faux positif conservateur, documenté (quality-gates.md)."""
    dec = _load_decision()
    result = _diagnostic_numeric(dec, tmp_path, {**_RELATION, field: value})
    assert _violations_of(result, "diagnostic") == [
        f"diagnostic $.relations[0].{field} (littérale) numeric_source_not_captured: {raw!r}"], result


def test_safety_numeric_diagnostic_schema_exempts_nothing(tmp_path):
    """Le schéma frontmatter n'est pas lu : y fermer `part_role` par un motif n'exempte ni le
    texte que l'export diagnostic publie, ni la fiche."""
    import json
    import shutil
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    path = tmp_path / "_meta" / "schema" / "frontmatter.schema.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SCRIPTS.parent / "_meta" / "schema" / "frontmatter.schema.json", path)
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema["properties"]["diagnostic_relations"]["items"]["properties"]["part_role"] = {
        "type": "string", "pattern": "^.+$"}
    path.write_text(json.dumps(schema), encoding="utf-8")
    fm = {**SAFETY_FM, "diagnostic_relations": [{**_RELATION, "part_role": "Jeu de 2 mm au braquage."}]}
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
    assert result["sample"] == [
        "fiche $.diagnostic_relations[0].part_role (littérale) numeric_source_not_captured: '2 mm'",
        "diagnostic $.relations[0].part_role (littérale) numeric_source_not_captured: '2 mm'"], result


def test_safety_numeric_scope_is_the_fiche_and_the_diagnostic_export(tmp_path, monkeypatch):
    """Un champ de relation que `build_exports_diagnostic` ne publie pas est lu dans la fiche ;
    dès que l'export le publie, il l'est aussi dans l'export, sans autre modification."""
    dec = _load_decision()
    relation = {**_RELATION, "note": "Remplacer sous 2 mm."}
    fiche = ["fiche $.diagnostic_relations[0].note (littérale) numeric_source_not_captured: '2 mm'"]
    assert _diagnostic_numeric(dec, tmp_path, relation)["sample"] == fiche
    load = dec._load_module

    def exporter_publishing_note(name, filename):
        module = load(name, filename)
        if filename == "build_exports_diagnostic.py":
            export = module._export_relation
            module._export_relation = lambda i, item, catalog: {**export(i, item, catalog),
                                                                "note": item["note"]}
        return module

    monkeypatch.setattr(dec, "_load_module", exporter_publishing_note)
    result = _diagnostic_numeric(dec, tmp_path, relation)
    assert result["sample"] == fiche + [
        "diagnostic $.relations[0].note (littérale) numeric_source_not_captured: '2 mm'"], result


@pytest.mark.parametrize("relations, error", [
    ([{**_RELATION, "sources": ["source_inconnue"]}], "source slug unknown to the catalog"),
    ([{k: v for k, v in _RELATION.items() if k != "part_role"}], "missing required key 'part_role'"),
    ("pas une liste", "diagnostic_relations must be a list"),
])
def test_safety_numeric_unexportable_relation_fails_closed_with_error(tmp_path, relations, error):
    """Relation que l'export refuserait : le texte publié est indéterminable, la condition est
    fausse et l'erreur de l'exporteur est rapportée."""
    dec = _load_decision()
    local = _local(dec, tmp_path, fm={**SAFETY_FM, "diagnostic_relations": relations})
    assert local["conditions"]["numeric_exactitude_verified"] is False
    assert error in local["details"]["numeric_exactitude_verified"]["error"]


@pytest.mark.parametrize("relation, where, raw", [
    ({**_RELATION, "vehicle_scope": {"fuel": "diesel", "disque de 280 mm minimum": True}},
     '$.relations[0].vehicle_scope["disque de 280 mm minimum"] (clé)', "280 mm"),
    ({**_RELATION, "part_role": {"Jeu de 2 mm au braquage": True}},
     '$.relations[0].part_role["Jeu de 2 mm au braquage"] (clé)', "2 mm"),
    ({**_RELATION, "symptom_slug": "volant dur au-dela de 2 mm de jeu"},
     "$.relations[0].symptom_slug", "2 mm"),
    ({**_RELATION, "evidence": {**_RELATION["evidence"], "strength": "si jeu > 2 mm"}},
     "$.relations[0].evidence.strength", "2 mm"),
    ({**_RELATION, "cause_slug": "jeu superieur a 2 mm"}, "$.relations[0].cause_slug", "2 mm"),
    ({**_RELATION, "evidence": {**_RELATION["evidence"], "confidence": "medium (jeu 2 mm)"}},
     "$.relations[0].evidence.confidence", "2 mm"),
    ({**_RELATION, "citations": [{"source": "preuve_atelier", "start": 0, "end": 4,
                                  "quote_sha256": _QUOTE_SHA, "note": "serrer a 25 Nm"}]},
     "$.relations[0].citations[0].note", "25 Nm"),
    ({**_RELATION, "vehicle_scope": {"fuel": "diesel", "note": "disque 280 mm"}},
     "$.relations[0].vehicle_scope.note", "280 mm"),
])
def test_safety_numeric_every_published_diagnostic_string_is_read(tmp_path, relation, where, raw):
    """Clé d'un mapping, slug en texte libre, champ d'`evidence` ou de citation, valeur de
    portée véhicule : toute chaîne que l'export diagnostic publie est lue, quel que soit le
    champ et le type que lui donne le schéma."""
    dec = _load_decision()
    result = _diagnostic_numeric(dec, tmp_path, relation)
    assert _violations_of(result, "diagnostic") == [
        f"diagnostic {where} (littérale) numeric_source_not_captured: {raw!r}"], result


def test_safety_numeric_string_derived_from_the_catalog_is_read(tmp_path):
    """L'export diagnostic publie aussi des chaînes du catalogue (`raw_ref` d'une source
    citée) : elles sont lues comme le reste du document."""
    dec = _load_decision()
    sources = ({**SAFETY_PROOF_SOURCES[0], "raw_ref": {
        "repo": "automecanik-raw", "manifest_id": "atelier-2mm", "expected_sha256": _QUOTE_SHA}},
    ) + SAFETY_PROOF_SOURCES[1:]
    target = _safety_wiki(tmp_path, sources=sources)
    fm = {**SAFETY_FM, "diagnostic_relations": [_RELATION]}
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
    assert result["sample"] == [
        "diagnostic $.relations[0].sources[0].raw_ref.manifest_id (littérale) "
        "numeric_source_not_captured: '2mm'"], result


@pytest.mark.parametrize("manifest_id, sample", [
    ("mm-atelier-p12", ["diagnostic $.relations[0].sources[0].raw_ref.manifest_id "
                        "unmodelled_leading_unit: 'mm'"]),
    ("atelier-p12", []),
])
def test_safety_numeric_catalog_string_leading_unit_is_a_violation(tmp_path, manifest_id, sample):
    """Chaîne du catalogue publiée par l'export diagnostic : son unité de tête est relevée comme
    celle de toute chaîne publiée."""
    dec = _load_decision()
    sources = ({**SAFETY_PROOF_SOURCES[0], "raw_ref": {
        "repo": "automecanik-raw", "manifest_id": manifest_id, "expected_sha256": _QUOTE_SHA}},
    ) + SAFETY_PROOF_SOURCES[1:]
    target = _safety_wiki(tmp_path, sources=sources)
    fm = {**SAFETY_FM, "diagnostic_relations": [_RELATION]}
    result = dec._safety_numeric_exactitude(fm, SAFETY_BODY, target, tmp_path)
    assert (result["verified"], result["sample"]) == (not sample, sample), result


def test_safety_numeric_renamed_exported_field_is_read(tmp_path, monkeypatch):
    """Un champ que l'exporteur renomme reste lu, sous son nouveau nom : aucune liste de champs."""
    dec = _load_decision()
    load = dec._load_module

    def exporter_renaming_part_role(name, filename):
        module = load(name, filename)
        if filename == "build_exports_diagnostic.py":
            export = module._export_relation

            def renamed(i, item, catalog):
                out = export(i, item, catalog)
                out["role_text"] = out.pop("part_role")
                return out
            module._export_relation = renamed
        return module

    monkeypatch.setattr(dec, "_load_module", exporter_renaming_part_role)
    result = _diagnostic_numeric(dec, tmp_path, {**_RELATION, "part_role": "Jeu de 2 mm au braquage."})
    assert _violations_of(result, "diagnostic") == [
        "diagnostic $.relations[0].role_text (littérale) numeric_source_not_captured: '2 mm'"], result


def test_safety_numeric_document_level_exported_field_is_read(tmp_path, monkeypatch):
    """Un champ que l'exporteur ajoute au document, hors relations, est lu lui aussi."""
    dec = _load_decision()
    load = dec._load_module

    def exporter_with_a_summary(name, filename):
        module = load(name, filename)
        if filename == "build_exports_diagnostic.py":
            build = module.build_gamme_export
            module.build_gamme_export = lambda *a, **k: {**build(*a, **k),
                                                         "summary": "Jeu de 2 mm au braquage."}
        return module

    monkeypatch.setattr(dec, "_load_module", exporter_with_a_summary)
    result = _diagnostic_numeric(dec, tmp_path, _RELATION)
    assert result["sample"] == [
        "diagnostic $.summary (littérale) numeric_source_not_captured: '2 mm'"], result


_CATALOG_ABSENT = "_meta/source-catalog.yaml absent de l'arbre évalué"
_RANGES_ABSENT = "_meta/numeric-plausibility.yaml absent de l'arbre évalué"
# Grandeur dimensionnée de la famille freinage : un nombre nu dans sa clause est une valeur.
_RANGES_FREINAGE = {"schema_version": "1.0.0", "families": {"freinage": {"min_thickness": {
    "unit": "mm", "min": 5.0, "max": 60.0, "critical": True, "status": "proposed"}}}}


def test_safety_numeric_absent_ranges_are_unavailable_never_verified(tmp_path):
    """Plages chiffrées absentes de l'arbre évalué : un nombre nu dans une clause à grandeur
    dimensionnée n'y serait plus reconnu. La condition est UNAVAILABLE (entrée absente), jamais
    vérifiée ni jugée sur le contenu ; les autres conditions restent évaluées."""
    dec = _load_decision()
    fm = {**SAFETY_FM, "slug": "disque-de-frein"}
    body = "## Rôle technique\n\nL'épaisseur minimale du disque avant est 27.\n"
    present = _local(dec, tmp_path / "present", fm=fm, body=body, ranges=_RANGES_FREINAGE)
    assert present["details"]["numeric_exactitude_verified"]["sample"] == [
        f"corps ({form}) numeric_source_not_captured: '27'" for form in ("rendue", "sans balisage")]
    absent = _local(dec, tmp_path / "absent", fm=fm, body=body, ranges=None)
    assert [k for k, v in absent["conditions"].items() if v is not True] == [
        "numeric_exactitude_verified"], absent
    assert absent["details"]["numeric_exactitude_verified"] == {
        "status": "UNAVAILABLE", "missing_input": _RANGES_ABSENT}


@pytest.mark.parametrize("text, anchor, expected", [
    ("L'épaisseur minimale du disque avant est 27.", "L'épaisseur minimale du disque avant est 2",
     _unsourced("27")),
    # Coupe visible seulement telle qu'écrite : « ⒈ » se lit « 1. » à la compatibilité près et y
    # rejoint le nombre coupé (« 1.2,7 » : 1.2 puis 7), là où le lecteur voit « 2,7 ».
    ("L'épaisseur minimale du disque avant est \u24882,7.",
     "L'épaisseur minimale du disque avant est \u24882",
     _unsourced("2,7", ("rendue",)) + _unsourced("1.2")),
])
def test_safety_numeric_anchor_that_splits_a_bare_number_is_not_masked(tmp_path, text, anchor, expected):
    """Nombre nu d'une clause à grandeur dimensionnée : une ancre qui le coupe (« 27 » lu « 2 »)
    ne porte pas sa source, même sans unité à séparer ; le nombre entier reste non sourcé, et
    l'ancre est rapportée."""
    dec = _load_decision()
    body = f"## Rôle technique\n\n{text}\n"
    target = _safety_wiki(tmp_path, body=body, ranges=_RANGES_FREINAGE,
                          entries=[_captured_anchor("## Rôle technique", anchor)])
    result = dec._safety_numeric_exactitude({**SAFETY_FM, "slug": "disque-de-frein"}, body, target, tmp_path)
    assert result["anchored_claims"] == 0
    assert result["anchors_unmasked"] == [{"anchor": anchor, "form": "rendue", "reason": "value_split"}]
    assert _violations_of(result, "corps") == expected, result


@pytest.mark.parametrize("projected, expected", [
    ({"diagnostic_relations": [_RELATION]},
     {"verified": False, "violations_total": 0, "status": "UNAVAILABLE",
      "missing_input": _CATALOG_ABSENT, "unavailable": [_CATALOG_ABSENT],
      "published": {"seo": True, "diagnostic": False}}),
    # Une violation prouvée ailleurs (fiche, export SEO) prime : la condition échoue pour le contenu.
    ({"diagnostic_relations": [_RELATION], **_editorial("Serrer à 25 Nm.")},
     {"verified": False, "violations_total": 2, "status": None, "unavailable": [_CATALOG_ABSENT]}),
    # Sans relation, l'export diagnostic ne publie rien : le catalogue n'est pas lu.
    (_SEO_BASE, {"verified": True, "status": None, "unavailable": []}),
])
def test_safety_numeric_absent_catalog_is_unavailable_never_verified(tmp_path, projected, expected):
    """Catalogue de sources absent de l'arbre évalué, fiche gamme à relations : le document
    diagnostic publié est indéterminable, la condition est UNAVAILABLE, jamais vérifiée."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    (tmp_path / "_meta" / "source-catalog.yaml").unlink()
    result = dec._safety_numeric_exactitude({**SAFETY_FM, **projected}, SAFETY_BODY, target, tmp_path)
    assert {k: result.get(k) for k in expected} == expected, result


def test_safety_local_conditions_absent_catalog_are_unavailable(tmp_path):
    """Les deux conditions qui lisent le catalogue sont fausses et typées UNAVAILABLE (entrée
    absente) ; les autres restent évaluées."""
    dec = _load_decision()
    target = _safety_wiki(tmp_path)
    (tmp_path / "_meta" / "source-catalog.yaml").unlink()
    fm = {**SAFETY_FM, "diagnostic_relations": [_RELATION]}
    local = dec._safety_local_conditions(fm, SAFETY_BODY, target, tmp_path, SAFETY_SHADOW,
                                         [(n, _gate_result("pass")) for n in dec.CANONICAL_GATE_NAMES], 0.9)
    assert [k for k, v in local["conditions"].items() if v is not True] == [
        "proof_sources_min", "numeric_exactitude_verified"], local
    assert local["details"]["proof_sources_min"] == {"status": "UNAVAILABLE",
                                                     "missing_input": _CATALOG_ABSENT}
    numeric = local["details"]["numeric_exactitude_verified"]
    assert numeric["status"] == "UNAVAILABLE" and numeric["missing_input"] == _CATALOG_ABSENT


@pytest.mark.parametrize("engine_file", [
    "build_exports_seo.py", "build_exports_diagnostic.py", "compute-symptom-confidence.py"])
def test_export_projections_are_evaluation_engine_files(engine_file):
    """Changer une projection change le texte contrôlé : une décision rendue devient STALE."""
    dec = _load_decision()
    assert engine_file in dec._EVALUATION_ENGINE_FILES


@pytest.mark.parametrize("entity_type", ["gamme", "vehicle", "constructeur", "diagnostic"])
def test_safety_projection_reads_the_fiche_apply_writes(tmp_path, entity_type):
    """La fiche que la gate projette est celle qu'`apply_promotion` écrit, aux valeurs de
    promotion près (SHA, horodatage, score) : les documents que les exporteurs publient
    depuis le canon écrit sont ceux que la gate a lus, et seulement eux (l'export
    diagnostic ne publie que les fiches de `wiki/gamme/`), dans chaque répertoire où la
    promotion écrit."""
    import json
    import subprocess
    import yaml
    dec = _load_decision()
    assert entity_type in dec.WIKI_ENTITY_DIRS
    _safety_wiki(tmp_path)
    fm = {**SAFETY_FM, **_SEO_BASE, "entity_type": entity_type, "diagnostic_relations": [_RELATION]}
    source = tmp_path / "proposals" / "colonne-de-direction.md"
    source.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True) + "---\n" + SAFETY_BODY,
                      encoding="utf-8")
    raw = tmp_path / "raw"
    pfm, pbody = dec._parse_markdown(source)
    with dec._promoted_fiche(pfm, pbody, source, tmp_path) as (root, path):
        gate_bytes = path.read_bytes()
        gate_seo, _warnings = dec._seo_projection(path, root)
        gate_diag = dec._diagnostic_projection(path, root, tmp_path)
    decision = {"eligible": True, "promotion_status": "ELIGIBLE",
                "evaluation": {"gate_status": "pass", "confidence_score": 0.9},
                "inputs": dec.capture_input_manifest(source, tmp_path, raw, None)}
    out = dec.apply_promotion(source, tmp_path, decision, raw_root=raw)
    assert out == tmp_path / "wiki" / entity_type / "colonne-de-direction.md" and not source.exists()
    written, _body = dec._parse_markdown(out)
    sha, now = written["reviewed_by"].split("@", 1)[1], written["reviewed_at"]

    def render(evaluation, sha, now):
        return dec._render_fiche(dec._promoted_frontmatter(
            pfm, evaluation, target_rel="proposals/colonne-de-direction.md", sha=sha, now=now), pbody)

    assert out.read_text(encoding="utf-8") == render(decision["evaluation"], sha, now)
    assert gate_bytes.decode("utf-8") == render({"gate_status": "pass", "confidence_score": 0.0},
                                                dec._COMMIT_SHA_FALLBACK, "1970-01-01T00:00:00+00:00")
    seo = dec._load_module("_test_seo_identity", "build_exports_seo.py")
    published_seo = seo.build_export(out, tmp_path, seo._COMMIT_SHA_PLACEHOLDER,
                                     seo._GENERATED_AT_PLACEHOLDER)
    # Type `diagnostic` sans bloc R3_CONSEILS/S2_DIAG : l'export SEO ne le publie pas (ADR-027).
    assert (published_seo is None) == (entity_type == "diagnostic")

    def unhashed(doc):  # `content_hash` : empreinte des octets de la fiche, qui portent SHA et horodatage
        return None if doc is None else {k: v for k, v in doc.items() if k != "content_hash"}

    assert unhashed(published_seo) == unhashed(gate_seo)
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(tmp_path)]
    subprocess.run(git + ["init", "-q"], check=True)
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "canon"], check=True)
    diag = dec._load_module("_test_diag_identity", "build_exports_diagnostic.py")
    expected, _unreconciled, _pins = diag._plan(tmp_path)
    exported = [rel for rel in expected if rel != "_index.json"]
    if entity_type != "gamme":
        assert exported == [] and gate_diag is None
        return
    assert exported == ["gamme/colonne-de-direction.json"]
    published_diag = json.loads(expected["gamme/colonne-de-direction.json"])
    published_diag.update(source_wiki_commit="0" * 40, source_catalog_commit="0" * 40)
    assert published_diag == gate_diag


def test_safety_seo_projection_scope_is_the_exporter_main_scope():
    """Les répertoires où la promotion écrit sont ceux que parcourt le `main` de l'export SEO."""
    dec = _load_decision()
    seo = dec._load_module("_test_seo_scope", "build_exports_seo.py")
    assert dec.WIKI_ENTITY_DIRS == seo.SEO_ENTITY_TYPES_BASE | {seo.DIAGNOSTIC_CONDITIONAL_TYPE}


def test_frontmatter_schema_is_not_a_decision_input(tmp_path, monkeypatch):
    """Aucun exporteur ne lit le schéma frontmatter : le changer après la décision ne la rend
    pas STALE ; changer le catalogue, que l'export diagnostic lit, la rend STALE."""
    import shutil
    dec, cand, raw = _proof_candidate(tmp_path, monkeypatch, "captured", bind_provenance=False)
    schema = tmp_path / "_meta" / "schema" / "frontmatter.schema.json"
    shutil.copyfile(SCRIPTS.parent / "_meta" / "schema" / "frontmatter.schema.json", schema)
    decision = dec.canonical_promotion_decision(
        cand, tmp_path, raw_root=raw, gates=_gates(), compute_score=lambda *a: 0.99)
    assert decision["eligible"] is True, decision
    roles = {e["role"] for e in decision["inputs"]["input_manifest"]}
    assert "frontmatter_schema" not in roles and "source_catalog" in roles
    schema.write_text("{}", encoding="utf-8")
    assert dec.authorize_apply(decision, cand, tmp_path, raw_root=raw) == (True, None)
    catalog = tmp_path / "_meta" / "source-catalog.yaml"
    catalog.write_text(catalog.read_text(encoding="utf-8") + "\n# changé après la décision\n",
                       encoding="utf-8")
    ok, refusal = dec.authorize_apply(decision, cand, tmp_path, raw_root=raw)
    assert ok is False and refusal["code"] == "STALE_DECISION"


def _safety_bundle(dec, tmp_path, monkeypatch, **bundle):
    """Substance réelle via evaluate_tier ; seul le tier shadow est fixé (planchers OK)."""
    monkeypatch.setattr(dec, "_compute_shadow", lambda *a: SAFETY_SHADOW)
    target = _safety_wiki(tmp_path)
    substance = dec.evaluate_tier(SAFETY_FM, SAFETY_BODY, target, tmp_path, threshold=0.80,
                                  gates=_gates(), compute_score=lambda *a: 0.99)
    return {"substance": substance, **bundle}


_ALL_PASS = {"coverage": {"status": "PASS", "evidence": {}},
             "regression": {"verdict": "IMPROVED", "evidence": {}},
             "provenance": {"status": "PASS", "evidence": {}}}


def test_safety_all_conditions_proven_but_policy_unratified_blocks_once(tmp_path, monkeypatch):
    dec = _load_decision()
    assert dec.SAFETY_AUTO_APPROVAL_ADR is None  # flip = PR dédiée après l'ADR vault
    d = dec.decide_promotion(_safety_bundle(dec, tmp_path, monkeypatch, **_ALL_PASS))
    assert d["eligible"] is False and d["promotion_status"] == "BLOCKED"
    assert [r["code"] for r in d["blocking_reasons"]] == ["SAFETY_HUMAN_REVIEW"]
    evidence = d["blocking_reasons"][0]["evidence"]
    assert evidence["blocking_conditions"] == []
    assert evidence["policy"] == {"auto_approval_adr": None, "status": "not_ratified"}


def test_safety_policy_ratified_and_all_conditions_proven_is_eligible(tmp_path, monkeypatch):
    dec = _load_decision()
    monkeypatch.setattr(dec, "SAFETY_AUTO_APPROVAL_ADR", "ADR-TEST")
    bundle = _safety_bundle(dec, tmp_path, monkeypatch, **_ALL_PASS)
    assert bundle["substance"]["tier"] == "A"
    d = dec.decide_promotion(bundle)
    assert d["eligible"] is True and d["promotion_status"] == "ELIGIBLE"


@pytest.mark.parametrize("missing, condition", [
    ("coverage", "coverage_strict_pass"),
    ("regression", "regression_gate_pass"),
    ("provenance", "provenance_pass"),
])
def test_safety_absent_evaluator_is_never_a_pass_even_when_ratified(
        tmp_path, monkeypatch, missing, condition):
    dec = _load_decision()
    monkeypatch.setattr(dec, "SAFETY_AUTO_APPROVAL_ADR", "ADR-TEST")
    rest = {k: v for k, v in _ALL_PASS.items() if k != missing}
    d = dec.decide_promotion(_safety_bundle(dec, tmp_path, monkeypatch, **rest))
    assert d["eligible"] is False
    safety = next(r for r in d["blocking_reasons"] if r["code"] == "SAFETY_HUMAN_REVIEW")
    assert safety["evidence"]["blocking_conditions"] == [condition]


def test_safety_regressed_or_warn_coverage_blocks_safety_even_when_ratified(tmp_path, monkeypatch):
    """WARN de couverture : advisory pour une fiche ordinaire, bloquant pour la sécurité."""
    dec = _load_decision()
    monkeypatch.setattr(dec, "SAFETY_AUTO_APPROVAL_ADR", "ADR-TEST")
    d = dec.decide_promotion(_safety_bundle(
        dec, tmp_path, monkeypatch, **{**_ALL_PASS, "coverage": {"status": "WARN"},
                                       "regression": {"verdict": "REGRESSED"}}))
    safety = next(r for r in d["blocking_reasons"] if r["code"] == "SAFETY_HUMAN_REVIEW")
    assert safety["evidence"]["blocking_conditions"] == ["coverage_strict_pass",
                                                         "regression_gate_pass"]


def test_safety_hand_built_check_without_conditions_never_passes(monkeypatch):
    """Un check sécurité sans conditions évaluées n'est jamais un succès, même ratifié."""
    dec = _load_decision()
    monkeypatch.setattr(dec, "SAFETY_AUTO_APPROVAL_ADR", "ADR-TEST")
    substance = {"checks": [{"code": "SAFETY_HUMAN_REVIEW", "status": "fail",
                             "owner_stage": "POLICY_SAFETY", "evidence": {"is_safety": True}}]}
    d = dec.decide_promotion({"substance": substance, **_ALL_PASS})
    safety = next(r for r in d["blocking_reasons"] if r["code"] == "SAFETY_HUMAN_REVIEW")
    assert "safety_local_conditions_evaluated" in safety["evidence"]["blocking_conditions"]


def test_safety_absent_catalog_is_reported_unavailable_by_the_decision(tmp_path, monkeypatch):
    """Les conditions non évaluables faute d'entrée sont nommées comme telles dans la raison
    bloquante : l'appelant distingue une entrée absente d'un contenu en échec."""
    dec = _load_decision()
    monkeypatch.setattr(dec, "_compute_shadow", lambda *a: SAFETY_SHADOW)
    target = _safety_wiki(tmp_path)
    (tmp_path / "_meta" / "source-catalog.yaml").unlink()
    fm = {**SAFETY_FM, "diagnostic_relations": [_RELATION]}
    substance = dec.evaluate_tier(fm, SAFETY_BODY, target, tmp_path, threshold=0.80,
                                  gates=_gates(), compute_score=lambda *a: 0.99)
    d = dec.decide_promotion({"substance": substance, **_ALL_PASS})
    assert [r["code"] for r in d["blocking_reasons"]] == ["SAFETY_HUMAN_REVIEW"], d
    evidence = d["blocking_reasons"][0]["evidence"]
    assert evidence["blocking_conditions"] == evidence["unavailable_conditions"] == [
        "proof_sources_min", "numeric_exactitude_verified"]


def test_safety_unavailable_conditions_exclude_conditions_failed_on_content(tmp_path, monkeypatch):
    """Une condition en échec sur le contenu reste un échec : seule une condition non évaluable
    faute d'entrée est nommée dans `unavailable_conditions`."""
    dec = _load_decision()
    monkeypatch.setattr(dec, "_compute_shadow", lambda *a: {"shadow_dims": {"A": 21.9, "C": 18.0}})
    target = _safety_wiki(tmp_path)
    (tmp_path / "_meta" / "source-catalog.yaml").unlink()
    substance = dec.evaluate_tier(SAFETY_FM, SAFETY_BODY, target, tmp_path, threshold=0.80,
                                  gates=_gates(), compute_score=lambda *a: 0.99)
    evidence = dec.decide_promotion({"substance": substance, **_ALL_PASS})["blocking_reasons"][0]["evidence"]
    assert "dim_A_floor" in evidence["blocking_conditions"], evidence
    assert evidence["unavailable_conditions"] == ["proof_sources_min"], evidence


def test_load_numeric_ranges_absent_is_empty_and_malformed_raises(tmp_path):
    dec = _load_decision()
    assert dec.load_numeric_ranges(tmp_path / "absent.yaml") == {}
    bad = tmp_path / "bad.yaml"
    bad.write_text("families: [1, 2]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="numeric_ranges_malformed"):
        dec.load_numeric_ranges(bad)
    broken = tmp_path / "broken.yaml"
    broken.write_text("families: {a: [\n", encoding="utf-8")
    with pytest.raises(ValueError, match="numeric_ranges_unreadable"):
        dec.load_numeric_ranges(broken)


def test_numeric_ranges_are_a_decision_input(tmp_path):
    """Valider une plage change la décision possible : le fichier est dans le manifest."""
    dec = _load_decision()
    cand = _write_candidate(tmp_path)
    manifest = dec.capture_input_manifest(cand, tmp_path, None, None)
    roles = {e["role"] for e in manifest["input_manifest"]}
    assert "numeric_ranges" in roles
