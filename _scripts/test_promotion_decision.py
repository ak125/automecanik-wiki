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
    # une check par dimension (safety, numeric, review, 5 gates, truth, substance, source-diversity)
    for code in ("SAFETY_HUMAN_REVIEW", "NUMERIC_HIGH_HARM", "REVIEW_AUTHORITY_CLAIMED", "GATE_RISK",
                 "TRUTH_LEVEL", "SUBSTANCE_SCORE", "SOURCE_DIVERSITY"):
        assert code in by_code, code
        assert by_code[code]["status"] in ("pass", "fail")
        assert by_code[code]["owner_stage"]
    assert by_code["GATE_RISK"]["status"] == "fail"
    assert by_code["SAFETY_HUMAN_REVIEW"]["status"] == "pass"  # FM_OK non-safety
    assert by_code["REVIEW_AUTHORITY_CLAIMED"]["status"] == "pass"  # FM_OK ne déclare rien


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


def _safety_wiki(tmp_path, *, entries=(), body=SAFETY_BODY):
    """Mini wiki : la fiche et, si fournie, sa coverage-map (clé = nom de fichier)."""
    target = tmp_path / "proposals" / "colonne-de-direction.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    if entries:
        import yaml
        cov = tmp_path / "proposals" / "_coverage" / "colonne-de-direction.coverage.yaml"
        cov.parent.mkdir(parents=True, exist_ok=True)
        cov.write_text(yaml.safe_dump({"fiche": "colonne-de-direction",
                                       "coverage_entries": list(entries)}), encoding="utf-8")
    return target


def _local(dec, tmp_path, *, fm=SAFETY_FM, body=SAFETY_BODY, shadow=SAFETY_SHADOW,
           gate_results=None, entries=()):
    target = _safety_wiki(tmp_path, entries=entries, body=body)
    if gate_results is None:
        gate_results = [(n, _gate_result("pass")) for n in dec.CANONICAL_GATE_NAMES]
    return dec._safety_local_conditions(fm, body, target, tmp_path, shadow, gate_results)


def test_safety_canonical_gate_names_are_the_loaded_gates():
    """`no_quality_gate_fail` exige exactement les 5 contrôles de `_load_gates` : la liste
    attendue ne peut pas dériver de celle réellement exécutée."""
    dec = _load_decision()
    assert tuple(n for n, _ in dec._load_gates()) == dec.CANONICAL_GATE_NAMES


def test_safety_local_conditions_all_proven_on_a_clean_fiche(tmp_path):
    dec = _load_decision()
    local = _local(dec, tmp_path)
    assert local["conditions"] and all(v is True for v in local["conditions"].values()), local


_RELATION_SAFE = {"symptom": "volant_dur", "evidence": {
    "confidence": "medium", "source_policy": "2_medium_concordant",
    "reviewed": False, "diagnostic_safe": True}}
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


# --- Relecture et autorité diagnostic : jamais déclarées par la proposition elle-même ------
# ADR-033 D4 : `reviewed` / `diagnostic_safe` passent à true par un flip humain ou une règle
# d'ADR explicite, jamais automatiquement. Une proposition qui les déclare elle-même ne doit
# pas être promue sans regard humain, quelle que soit sa famille.
def _evidence(**flags):
    return {"confidence": "medium", "source_policy": "2_medium_concordant",
            "reviewed": False, "diagnostic_safe": False, **flags}


_NOT_APPLICABLE_REASON = "Aucun lien avec le vocabulaire des symptômes."


@pytest.mark.parametrize("fm_extra, claimed", [
    ({"diagnostic_relations": [{"symptom_slug": "voyant_huile",
                                "evidence": _evidence(reviewed=True)}]},
     {"reviewed_true": ["diagnostic_relations[0]"], "diagnostic_safe_true": []}),
    ({"diagnostic_relations": [{"symptom_slug": "voyant_huile", "evidence": _evidence()},
                               {"symptom_slug": "bruit_moteur",
                                "evidence": _evidence(diagnostic_safe=True)}]},
     {"reviewed_true": [], "diagnostic_safe_true": ["diagnostic_relations[1]"]}),
    ({"diagnostic": {"quick_checks": [{"cause_slug": "filtre_colmate",
                                       "evidence": _evidence(reviewed=True, diagnostic_safe=True)}]}},
     {"reviewed_true": ["diagnostic.quick_checks[0]"],
      "diagnostic_safe_true": ["diagnostic.quick_checks[0]"]}),
    ({"safety_rules": [{"rule_slug": "arret_immediat", "evidence": _evidence(reviewed=True)}]},
     {"reviewed_true": ["safety_rules[0]"], "diagnostic_safe_true": []}),
    ({"diagnostic_not_applicable": {"reason": _NOT_APPLICABLE_REASON, "reviewed": True}},
     {"reviewed_true": ["diagnostic_not_applicable"], "diagnostic_safe_true": []}),
])
def test_self_declared_review_blocks_a_non_safety_fiche(tmp_path, fm_extra, claimed):
    """Fiche non-sécurité, tout le reste PASS : la seule déclaration de relecture ou
    d'autorité diagnostic suffit à la bloquer, avec les entrées en cause."""
    pm = _load_promote()
    dec = _load_decision()
    substance = _substance(pm, fm={**FM_OK, **fm_extra}, tmp_path=tmp_path)
    assert substance["tier"] == "B", substance
    d = dec.decide_promotion({"substance": substance})
    assert d["promotion_status"] == "BLOCKED"
    assert [r["code"] for r in d["blocking_reasons"]] == ["REVIEW_AUTHORITY_CLAIMED"], d
    assert d["blocking_reasons"][0]["evidence"] == claimed


def test_unreviewed_claims_do_not_block(tmp_path):
    """Témoin : les mêmes listes avec reviewed/diagnostic_safe à false restent éligibles."""
    pm = _load_promote()
    dec = _load_decision()
    fm = {**FM_OK,
          "diagnostic_relations": [{"symptom_slug": "voyant_huile", "evidence": _evidence()}],
          "diagnostic": {"quick_checks": [{"cause_slug": "filtre_colmate", "evidence": _evidence()}]},
          "diagnostic_not_applicable": {"reason": _NOT_APPLICABLE_REASON, "reviewed": False}}
    substance = _substance(pm, fm=fm, tmp_path=tmp_path)
    assert substance["tier"] == "A", substance
    assert dec.decide_promotion({"substance": substance})["eligible"] is True


def test_unreadable_review_claims_fail_closed(tmp_path):
    """Liste mal formée : le contrôle ne peut pas conclure, il bloque et dit pourquoi."""
    pm = _load_promote()
    dec = _load_decision()
    substance = _substance(pm, fm={**FM_OK, "diagnostic_relations": "pas une liste"},
                           tmp_path=tmp_path)
    assert substance["tier"] == "B"
    d = dec.decide_promotion({"substance": substance})
    reason = next(r for r in d["blocking_reasons"] if r["code"] == "REVIEW_AUTHORITY_CLAIMED")
    assert "diagnostic_relations_malformed" in reason["evidence"]["error"]


def test_review_check_absent_input_is_never_a_pass():
    """Checks construits sans le résultat du contrôle : fail, jamais un succès par défaut."""
    dec = _load_decision()
    checks = dec._build_checks(False, [], [], "L1", 0.9, 0.8, "legacy", None, {"raw", "web"})
    check = next(c for c in checks if c["code"] == "REVIEW_AUTHORITY_CLAIMED")
    assert check["status"] == "fail" and check["evidence"] == {"evaluated": False}
