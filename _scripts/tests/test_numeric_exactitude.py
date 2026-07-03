"""Tests du lock valeur numérique sécurité (numeric_exactitude, pure module).

Spec : _audit/numeric-value-verification-gate-spec-2026-07-03.md
Motif : ADR-093 documente le trou = aucune couche ne vérifie l'EXACTITUDE d'une valeur
numérique sécurité (couple/cote/tolérance). Ce module PUR (aucun LLM/DB/réseau, précédent
safety_families.py) classe chaque valeur en 6 verdicts, fail-closed.

Invariant d'honnêteté : sur disque-de-frein tel quel aujourd'hui (pages pending_capture),
AUCUNE valeur n'atteint numeric_verified → cohérent avec safety_auto_blocked.
"""
from __future__ import annotations

from pathlib import Path

import numeric_exactitude as NE

SCRIPTS = Path(__file__).resolve().parent.parent
# raw réel monté à côté du repo wiki (pattern gen_coverage_map)
RAW = Path("/opt/automecanik/automecanik-raw")


# --- fixtures de plages : la donnée gouvernée numeric-plausibility.yaml (statuts explicites) ---
# `validated` = autorité humaine 1× (Option A) ; `proposed` = machine, fail-closed (ne vaut pas validé).
RANGES = {
    "freinage": {
        "lateral_runout": {"unit": "mm", "min": 0.0, "max": 0.15,
                           "critical": True, "always_ref_specific": False, "status": "validated"},
        "min_thickness": {"unit": "mm", "min": 5.0, "max": 60.0,
                          "critical": True, "always_ref_specific": True, "status": "validated"},
        "temperature": {"unit": "°C", "min": 0.0, "max": 900.0,
                        "critical": False, "always_ref_specific": False, "status": "validated"},
        "disc_diameter": {"unit": "mm", "min": 200.0, "max": 420.0,
                          "critical": False, "always_ref_specific": True, "status": "validated"},
        "torque": {"unit": "Nm", "min": 5.0, "max": 400.0,
                   "critical": True, "always_ref_specific": False, "status": "validated"},
        "dtv": {"unit": "µm", "min": 0.0, "max": 50.0,
                "critical": True, "always_ref_specific": False, "status": "proposed"},
    }
}


# ── extraction ────────────────────────────────────────────────────────────────────────────────
def test_extract_value_and_unit_fr_decimal():
    vals = NE.extract_values("Le voile latéral doit rester < 0,05 mm sur véhicule moderne.")
    assert any(abs(v.value - 0.05) < 1e-9 and v.unit == "mm" for v in vals)


def test_extract_flags_tilde_as_approximate():
    vals = NE.extract_values("Tenue jusqu'à ~800 °C selon ATE.")
    assert vals and all(v.approximate for v in vals if v.unit == "°C")


def test_extract_flags_range_as_approximate():
    vals = NE.extract_values("La DTV ne doit pas dépasser ~12-15 µm sous peine de broutement.")
    assert vals and any(v.approximate and v.unit in ("µm", "μm") for v in vals)


def test_extract_handles_both_micro_signs():
    # µ (U+00B5) et μ (U+03BC) apparaissent tous deux dans le corpus disque
    a = NE.extract_values("écart 8 µm standard")
    b = NE.extract_values("écart 8 μm standard")
    assert a and b and a[0].unit in ("µm", "μm") and b[0].unit in ("µm", "μm")


# ── quantité déduite du contexte ────────────────────────────────────────────────────────────────
def test_detect_quantity_from_host_keywords():
    assert NE.detect_quantity("épaisseur minimale de 27 mm") == "min_thickness"
    assert NE.detect_quantity("le voile latéral toléré") == "lateral_runout"
    assert NE.detect_quantity("un couple de serrage") == "torque"
    assert NE.detect_quantity("une phrase sans grandeur connue") == "unknown"


# ── les 6 verdicts (fail-closed, premier bloquant gagne) ────────────────────────────────────────
def test_pending_capture_source_blocks_first():
    v = NE.extract_values("voile < 0,05 mm sur le disque avant")[0]
    verdict = NE.classify(v, "voile latéral < 0,05 mm sur le disque avant",
                          source_status="pending_capture", family="freinage",
                          ranges=RANGES, corroborating_sources=3)
    assert verdict == "numeric_source_not_captured"


def test_bare_number_missing_unit_is_unit_conflict():
    v = NE.extract_values("épaisseur mini 27")  # pas d'unité sur une grandeur dimensionnée
    verdict = NE.classify(v[0] if v else NE.NumVal("27", 27.0, "", False),
                          "épaisseur mini de 27 sur ce disque",
                          source_status="captured", family="freinage",
                          ranges=RANGES, corroborating_sources=3)
    assert verdict == "numeric_unit_conflict"


def test_min_thickness_general_statement_is_vehicle_specific():
    # cote réf-spécifique formulée en règle générale (aucun qualificatif restrictif)
    v = NE.extract_values("l'épaisseur minimale est de 27 mm")[0]
    verdict = NE.classify(v, "l'épaisseur minimale est de 27 mm",
                          source_status="captured", family="freinage",
                          ranges=RANGES, corroborating_sources=3)
    assert verdict == "numeric_vehicle_specific_do_not_generalize"


def test_min_thickness_with_ref_qualifier_not_flagged_specific():
    # même cote MAIS rattachée à une réf précise → PAS un faux positif
    host = "sur le disque Zimmermann 340×30 (5×112), l'épaisseur minimale est de 27 mm"
    v = NE.extract_values(host)
    # on cible la valeur 27 mm (épaisseur), pas 340/30/112
    nv = next(x for x in v if abs(x.value - 27.0) < 1e-9)
    verdict = NE.classify(nv, host, source_status="captured", family="freinage",
                          ranges=RANGES, corroborating_sources=3)
    assert verdict != "numeric_vehicle_specific_do_not_generalize"


def test_no_context_is_context_missing():
    v = NE.extract_values("Valeur retenue : 0,05 mm.")[0]
    verdict = NE.classify(v, "Valeur retenue : 0,05 mm.",
                          source_status="captured", family="freinage",
                          ranges=RANGES, corroborating_sources=3)
    assert verdict == "numeric_context_missing"


def test_approximate_value_is_ambiguous():
    v = next(x for x in NE.extract_values("tenue ~800 °C sur disque avant en fonte HC") if x.unit == "°C")
    verdict = NE.classify(v, "tenue ~800 °C sur disque avant en fonte HC",
                          source_status="captured", family="freinage",
                          ranges=RANGES, corroborating_sources=3)
    assert verdict == "numeric_ambiguous"


def test_out_of_range_is_ambiguous():
    v = NE.extract_values("voile latéral de 5 mm sur le disque avant")[0]
    verdict = NE.classify(v, "voile latéral de 5 mm sur le disque avant",
                          source_status="captured", family="freinage",
                          ranges=RANGES, corroborating_sources=3)
    assert verdict == "numeric_ambiguous"


def test_quantity_with_only_proposed_range_fails_closed():
    # dtv = plage `proposed` → jamais verified (Option A : proposé ≠ validé)
    v = next(x for x in NE.extract_values("la DTV de 10 µm sur le disque avant") if x.unit in ("µm", "μm"))
    verdict = NE.classify(v, "la DTV de 10 µm sur le disque avant",
                          source_status="captured", family="freinage",
                          ranges=RANGES, corroborating_sources=3)
    assert verdict == "numeric_ambiguous"


def test_isolated_critical_value_is_ambiguous():
    # grandeur critique + 1 seule source → isolée → ambiguë (exige corroboration ≥2)
    v = NE.extract_values("voile latéral de 0,05 mm sur le disque avant")[0]
    verdict = NE.classify(v, "voile latéral de 0,05 mm sur le disque avant",
                          source_status="captured", family="freinage",
                          ranges=RANGES, corroborating_sources=1)
    assert verdict == "numeric_ambiguous"


def test_verified_is_the_only_pass_and_needs_everything():
    # captured + contexte + plage validée + in-range + non-approx + non-réf-spécifique + corroboré ≥2
    host = "voile latéral de 0,05 mm mesuré sur le disque avant du véhicule"
    v = NE.extract_values(host)[0]
    verdict = NE.classify(v, host, source_status="verified", family="freinage",
                          ranges=RANGES, corroborating_sources=2)
    assert verdict == "numeric_verified"


# ── gate + invariant honnêteté disque ───────────────────────────────────────────────────────────
def test_gate_returns_violation_strings():
    claims = [{"text": "voile < 0,05 mm sur le disque avant", "source_status": "pending_capture"}]
    out = NE.gate_numeric_value_exactitude(claims, family="freinage", ranges=RANGES)
    assert out and all(isinstance(s, str) for s in out)
    assert any("numeric_source_not_captured" in s for s in out)


def test_disque_real_claims_zero_verified():
    """Invariant : sur les claims réels disque (pages non capturées), 0 valeur ne PASS."""
    if not RAW.is_dir():
        return  # raw non monté (CI hermétique) → skip silencieux borné
    bdir = RAW / "sources" / "web-research" / "disque-de-frein"
    if not bdir.is_dir():
        return
    texts = []
    for md in bdir.glob("*.md"):
        for line in md.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("- ") and NE.extract_values(line):
                texts.append({"text": line.strip(), "source_status": "pending_capture"})
    assert texts, "attendu : des claims numériques réels dans disque-de-frein"
    verdicts = NE.classify_all(texts, family="freinage", ranges=RANGES)
    assert all(v != "numeric_verified" for _, v in verdicts)
    # les pages pending → tout est source_not_captured (raison technique, pas humaine)
    assert all(v == "numeric_source_not_captured" for _, v in verdicts)


# ── DURCISSEMENT auto-review 2026-07-03 (findings BLOQUANT/HAUTE) ────────────────────────────────
def test_unit_must_match_range_unit():
    # BLOQUANT 1 : l'unité de la valeur DOIT concorder avec l'unité de la plage (sinon °C certifié en mm).
    host = "le diamètre extérieur du disque réf 340×30 vaut 300 °C"  # absurde exprès : °C sur grandeur mm
    v = next(x for x in NE.extract_values(host) if x.unit == "°C")
    assert NE.classify(v, host, source_status="verified", family="freinage",
                       ranges=RANGES, corroborating_sources=3) == "numeric_unit_conflict"


def test_multi_quantity_binds_local_quantity_per_value():
    # BLOQUANT 2 : chaque valeur classée sur SA grandeur LOCALE, pas la 1re de toute la phrase.
    # discriminant : sous le bug (voile pour tout), 340 mm → lateral_runout [0,0.15] → ambiguous ;
    # avec la correction, 340 mm → disc_diameter (réf-spécifique).
    host = "voile latéral 0,05 mm sur le disque avant ; diamètre extérieur 340 mm"
    res = dict(NE.classify_all([{"text": host, "source_status": "verified", "corroborating_sources": 3}],
                               family="freinage", ranges=RANGES))
    assert res["340 mm"] == "numeric_vehicle_specific_do_not_generalize"  # disc_diameter, pas lateral_runout
    assert res["0,05 mm"] == "numeric_verified"                          # lateral_runout in-range corroboré


def test_general_statement_with_unrelated_dimcode_stays_vehicle_specific():
    # HAUTE 1 : un N×M sans rapport (entraxe) + « en général » ne doit PAS lever le verdict réf-spécifique.
    host = "en général, l'épaisseur minimale est de 27 mm (entraxe 5×112)"
    v = next(x for x in NE.extract_values(host) if abs(x.value - 27.0) < 1e-9)
    assert NE.classify(v, host, source_status="verified", family="freinage",
                       ranges=RANGES, corroborating_sources=3) == "numeric_vehicle_specific_do_not_generalize"


def test_discourse_reference_word_stays_vehicle_specific():
    # HAUTE 1 : « par référence au constructeur » (discours) n'est PAS un qualificatif de réf précise.
    host = "par référence au constructeur, l'épaisseur minimale est 27 mm"
    v = NE.extract_values(host)[0]
    assert NE.classify(v, host, source_status="verified", family="freinage",
                       ranges=RANGES, corroborating_sources=3) == "numeric_vehicle_specific_do_not_generalize"


def test_missing_unit_dimensioned_quantity_blocks_at_gate():
    # HAUTE 3 : grandeur dimensionnée + chiffre nu SANS unité extraite → BLOQUE (pas d'évasion silencieuse).
    out = NE.gate_numeric_value_exactitude(
        [{"text": "l'épaisseur minimale est de 27 sur ce disque", "source_status": "verified"}],
        family="freinage", ranges=RANGES)
    assert any("numeric_unit_conflict" in s for s in out), out


def test_unrecognized_unit_blocks_at_gate():
    # HAUTE 3 : unité épelée non reconnue (« newton-mètres ») ne doit PAS passer inaperçue → BLOQUE.
    out = NE.gate_numeric_value_exactitude(
        [{"text": "le couple de serrage est de 120 newton-mètres", "source_status": "verified"}],
        family="freinage", ranges=RANGES)
    assert out, "un couple exprimé en unité épelée doit bloquer, pas s'évader"


def test_non_critical_validated_still_needs_corroboration():
    # HAUTE 4 : toute plage validée exige corroboration ≥2 (le garde ne doit pas être mort pour non-critique).
    host = "tenue 800 °C sur le disque avant du véhicule"
    v = next(x for x in NE.extract_values(host) if x.unit == "°C")
    assert NE.classify(v, host, source_status="verified", family="freinage",
                       ranges=RANGES, corroborating_sources=1) == "numeric_ambiguous"
    assert NE.classify(v, host, source_status="verified", family="freinage",
                       ranges=RANGES, corroborating_sources=2) == "numeric_verified"
