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

import importlib.util
from pathlib import Path
from types import SimpleNamespace

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
