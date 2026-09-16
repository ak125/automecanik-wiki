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
