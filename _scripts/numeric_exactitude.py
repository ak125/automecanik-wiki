#!/usr/bin/env python3
"""Lock valeur numérique sécurité — classification PURE (aucun LLM/DB/réseau).

Ferme le trou documenté par ADR-093 : la barre de preuve existante prouve
provenance + structure (dim A, coverage-map, safety_families), JAMAIS l'exactitude
d'un CHIFFRE (couple Nm, cote mm, tolérance µm). Sur une pièce freinage, un chiffre
faux auto-approuvé = danger physique.

Module pur sur le précédent `safety_families.py` : fonctions déterministes, plages
gouvernées INJECTÉES (jamais lues ici — chargées par l'appelant depuis
`_meta/numeric-plausibility.yaml`). Fail-closed : en cas de doute → BLOCK.

Durci après auto-review adversariale 2026-07-03 (2 BLOQUANT + 4 HAUTE) :
- l'unité de la valeur DOIT concorder avec l'unité canonique de la plage (°C ≠ mm) ;
- la grandeur est déduite PAR VALEUR (clause locale), pas une fois pour toute la phrase ;
- une cote réf-spécifique énoncée en règle générale (« en général ») reste réf-spécifique ;
- un chiffre non extrait sur une grandeur dimensionnée (unité manquante/épelée) BLOQUE
  au lieu de s'évader silencieusement ;
- toute plage `validated` exige corroboration ≥2, comptée depuis les sources CAPTÉES
  DISTINCTES concordantes (`classify_all`, plus de stub à 1 ; auto-corroboration exclue).

Spec : `_audit/numeric-value-verification-gate-spec-2026-07-03.md`.
Report-only : ce module classe et remonte ; il n'auto-approuve rien.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

VERDICTS = frozenset({
    "numeric_verified",
    "numeric_ambiguous",
    "numeric_context_missing",
    "numeric_unit_conflict",
    "numeric_source_not_captured",
    "numeric_vehicle_specific_do_not_generalize",
})

# valeurs COVERAGE prouvées (enum `source_status` de coverage-map.schema.json). Le status CATALOG
# `active` est mappé vers ces valeurs par gen_coverage_map.is_page_proven / _resolve_status (SoT du
# prédicat) ; "archived" n'appartient à AUCUN des deux schémas (fantôme) → retiré.
PROVEN_STATUSES = frozenset({"captured", "verified"})

# unités reconnues (longues d'abord pour l'alternation ; µ = U+00B5, μ = U+03BC)
_UNIT = r"(?:mm²|daNm|N·m|N\.m|Nm|mm|µm|μm|cm|kPa|MPa|bar|psi|°C|%|kg)"
_NUM = r"\d+(?:[.,]\d+)?"
_VALUE_RE = re.compile(rf"({_NUM})\s*({_UNIT})")
_BARE_NUM_RE = re.compile(_NUM)

# marqueurs d'approximation dans le contexte gauche immédiat (~, ≈, environ, plage `12-15` / `12 à 15`)
_APPROX_LEFT = re.compile(r"(?:[~≈]|environ\s+|\d\s*(?:[-–]|à)\s*)$")

# unité épelée en toutes lettres (non reconnue par _UNIT) accolée à un nombre → évasion à bloquer
_SPELLED_UNIT_RE = re.compile(
    r"\d[\d.,]*\s*(?:newton|mètre|metre|millimètre|millimetre|micron|micromètre|micrometre|"
    r"degré|degre|pascal|pouce|inch|kilogramme|décanewton|decanewton)", re.IGNORECASE)

# grandeur déduite du contexte (français) — premier match gagne
_QUANTITY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("min_thickness", [r"épaisseur\s+min", r"épaisseur\s+mini", r"\bmin\s*th\b", r"cote\s+mini"]),
    ("dtv", [r"\bdtv\b", r"variation\s+d.{0,3}épaisseur"]),
    ("lateral_runout", [r"voile", r"faux[-\s]?rond", r"lateral\s+runout", r"\brunout\b"]),
    ("bolt_pattern", [r"entraxe", r"\bpcd\b"]),
    ("disc_diameter", [r"diamètre", r"\bØ\b"]),
    ("torque", [r"couple", r"serrage"]),
    ("temperature", [r"°c", r"température"]),
]

# tokens de contexte d'application (pièce / véhicule / condition / référence)
_CONTEXT_RE = re.compile(
    r"(disque|plaquette|frein|étrier|etrier|tambour|mâchoire|machoire|moyeu|"
    r"véhicule|vehicule|essieu|avant|arrière|arriere|roue|moderne|ancien|"
    r"réf\b|reference|référence|\d+\s*[×xX]\s*\d+)", re.IGNORECASE)

# qualificatif de RÉFÉRENCE PRÉCISE (code dimensionnel `N×M`, ou « réf <code-avec-chiffre> »).
# DURCI : ne matche plus le mot discours « référence » (« par référence au constructeur » = général).
_REF_QUALIFIER_RE = re.compile(r"(\d+\s*[×xX]\s*\d+|réf\.?\s+[\wÀ-ÿ./-]*\d)", re.IGNORECASE)

# formulation généralisante → une cote réf-spécifique énoncée ainsi RESTE réf-spécifique (jamais généralisée)
_GENERALIZING_RE = re.compile(
    r"en général|généralement|en règle générale|habituellement|systématiquement|"
    r"toujours|dans tous les cas|pour tout(?:e|s)?\s+(?:les?\s+)?disque", re.IGNORECASE)

# séparateurs de clause (pour lier grandeur ↔ valeur localement, pas sur toute la phrase)
_CLAUSE_DELIM = re.compile(r"[,;:]|\s+et\s+")


def _norm_unit(u: str) -> str:
    """Normalise les 2 signes micro (µ U+00B5 / μ U+03BC) ; sinon inchangé."""
    return "µm" if u in ("µm", "μm") else u


@dataclass
class NumVal:
    raw: str
    value: float
    unit: str
    approximate: bool
    start: int = -1


def extract_values(text: str) -> list[NumVal]:
    """Valeurs DIMENSIONNÉES (nombre + unité reconnue) — pas les nombres nus (dates, comptes).

    `approximate=True` si la valeur est précédée de ~ / ≈ / « environ » ou d'une plage `12-15` / `12 à`.
    `start` = position du match (pour lier la grandeur à la valeur, cf. `classify_all`).
    """
    out: list[NumVal] = []
    for m in _VALUE_RE.finditer(text):
        raw_num, unit = m.group(1), m.group(2)
        left = text[max(0, m.start() - 14):m.start()]
        approximate = bool(_APPROX_LEFT.search(left))
        out.append(NumVal(raw=m.group(0), value=float(raw_num.replace(",", ".")),
                          unit=unit, approximate=approximate, start=m.start()))
    return out


def detect_quantity(host: str) -> str:
    """Grandeur physique déduite des mots-clés de la phrase-hôte, sinon 'unknown'."""
    low = host.lower()
    for quantity, patterns in _QUANTITY_KEYWORDS:
        if any(re.search(p, low) for p in patterns):
            return quantity
    return "unknown"


def _clause_of(text: str, pos: int) -> str:
    """Sous-chaîne (clause) contenant la position `pos`, bornée par `,` `;` `:` ` et `."""
    left, right = 0, len(text)
    for m in _CLAUSE_DELIM.finditer(text):
        if m.end() <= pos:
            left = m.end()
        elif m.start() >= pos:
            right = m.start()
            break
    return text[left:right]


def _has_context(host: str) -> bool:
    return bool(_CONTEXT_RE.search(host))


def _has_ref_qualifier(host: str) -> bool:
    return bool(_REF_QUALIFIER_RE.search(host))


def classify(
    nv: NumVal,
    host: str,
    *,
    source_status: str,
    family: str,
    ranges: dict,
    corroborating_sources: int,
    quantity: str | None = None,
) -> str:
    """Classe UNE valeur numérique. Fail-closed, premier verdict bloquant gagne.

    Ordre : source_not_captured → unit(absente|incompatible) → vehicle_specific
    → context_missing → (statut/plage/approx/corroboration ⇒ ambiguous) → verified.
    `quantity` explicite = grandeur locale (cf. `classify_all`) ; None → déduite de `host`.
    """
    # 1. provenance : page non prouvée → invérifiable à la source
    if source_status not in PROVEN_STATUSES:
        return "numeric_source_not_captured"

    if quantity is None:
        quantity = detect_quantity(host)
    qdef = (ranges.get(family) or {}).get(quantity)
    dimensioned = bool(qdef and qdef.get("unit"))

    # 2a. unité absente sur une grandeur qui en exige une
    if nv.unit == "" and dimensioned:
        return "numeric_unit_conflict"
    # 2b. unité INCOMPATIBLE avec l'unité canonique de la plage (ex. °C certifié en mm) — BLOQUANT auto-review
    if qdef and nv.unit and _norm_unit(nv.unit) != _norm_unit(str(qdef.get("unit", ""))):
        return "numeric_unit_conflict"

    # 3. cote réf-spécifique énoncée en règle générale OU sans qualificatif de réf précise
    if qdef and qdef.get("always_ref_specific") and (
            _GENERALIZING_RE.search(host) or not _has_ref_qualifier(host)):
        return "numeric_vehicle_specific_do_not_generalize"

    # 4. aucun contexte d'application (quel disque / véhicule / condition / réf)
    if not _has_context(host):
        return "numeric_context_missing"

    # 5. statut gouverné + approximation + plage + corroboration → ambiguous (fail-closed)
    if qdef is None or qdef.get("status") != "validated":
        return "numeric_ambiguous"          # grandeur inconnue OU plage seulement proposée (Option A)
    if nv.approximate:
        return "numeric_ambiguous"
    lo, hi = qdef.get("min"), qdef.get("max")
    if lo is not None and hi is not None and not (lo <= nv.value <= hi):
        return "numeric_ambiguous"          # hors plage plausible famille
    if corroborating_sources < 2:
        return "numeric_ambiguous"          # toute valeur validée exige corroboration ≥2 sources captées

    # 6. seul chemin PASS
    return "numeric_verified"


def _unverifiable_tokens(text: str, family: str, ranges: dict, extracted: list[NumVal]) -> list[str]:
    """Chiffres NON extraits comme valeur dimensionnée mais sur une grandeur qui exige une unité.

    Ferme l'évasion silencieuse (unité manquante ou épelée non reconnue) : un couple « 120
    newton-mètres » ou une épaisseur « 27 » sans `mm` ne doit PAS produire 0 violation.
    """
    fam = ranges.get(family) or {}
    out: list[str] = []
    # (a) unité épelée en toutes lettres accolée à un nombre
    out.extend(m.group(0).strip() for m in _SPELLED_UNIT_RE.finditer(text))
    # (b) chiffre nu dans une clause à grandeur dimensionnée SANS valeur dimensionnée déjà extraite
    extracted_spans = [(nv.start, nv.start + len(nv.raw)) for nv in extracted if nv.start >= 0]
    clauses_with_value = {_clause_of(text, nv.start) for nv in extracted if nv.start >= 0}
    for cm in _BARE_NUM_RE.finditer(text):
        pos = cm.start()
        if any(s <= pos < e for s, e in extracted_spans):
            continue                                   # fait partie d'une valeur dimensionnée extraite
        clause = _clause_of(text, pos)
        if clause in clauses_with_value:
            continue                                   # la clause porte déjà une valeur (ce chiffre = annexe/compte)
        qdef = fam.get(detect_quantity(clause))
        if qdef and qdef.get("unit"):                  # grandeur dimensionnée mais ce chiffre n'a pas d'unité
            out.append(cm.group(0))
    return list(dict.fromkeys(out))                    # dedup, ordre préservé


def _local_quantity(text: str, nv: NumVal) -> str:
    """Grandeur liée LOCALEMENT à la valeur (clause de `nv.start`), pas à toute la phrase."""
    return detect_quantity(_clause_of(text, nv.start)) if nv.start >= 0 else detect_quantity(text)


def _corro_key(quantity: str, nv: NumVal) -> tuple[str, str, float]:
    """Clé de concordance : même grandeur + même unité normalisée + même valeur (à l'arrondi).

    Deux sources CAPTÉES qui asservissent la même valeur de la même grandeur tombent dans le
    même bucket (corroboration) ; des valeurs divergentes (Brembo 0,10 / ZF 0,05) tombent dans
    des buckets disjoints → chacune isolée → jamais corroborée. Concordance stricte (fail-closed) :
    accord à la tolérance déclarée près = V2 ultérieur (`no_disputed_claims`).
    """
    return (quantity, _norm_unit(nv.unit), round(nv.value, 4))


def classify_all(claims: list[dict], *, family: str, ranges: dict) -> list[tuple[str, str]]:
    """[(valeur_brute, verdict)] pour chaque valeur (grandeur liée LOCALEMENT) + chiffres inextractibles.

    Corroboration RÉELLE : comptée depuis les sources CAPTÉES DISTINCTES qui concordent sur la même
    valeur (pré-passe `buckets`), plus de stub à 1. Un `corroborating_sources` explicite sur un claim
    reste un override (contrôle direct/tests) ; sinon le compte est dérivé des buckets. Fail-closed :
    aucune source captée → corroboration 0 → toute plage validée reste `numeric_ambiguous`.
    """
    # pré-passe : (grandeur, unité, valeur) → set des source_id PROUVÉS distincts (auto-corroboration exclue)
    buckets: dict[tuple[str, str, float], set[str]] = {}
    parsed: list[tuple[dict, str, str, list[NumVal]]] = []
    for c in claims:
        text = c["text"]
        status = c.get("source_status", "pending_capture")
        sid = c.get("source_id")
        vals = extract_values(text)
        parsed.append((c, text, status, vals))
        if status in PROVEN_STATUSES and sid:
            for nv in vals:
                buckets.setdefault(_corro_key(_local_quantity(text, nv), nv), set()).add(sid)

    res: list[tuple[str, str]] = []
    for c, text, status, vals in parsed:
        override = c.get("corroborating_sources")
        for nv in vals:
            q = _local_quantity(text, nv)
            corr = int(override) if override is not None else len(buckets.get(_corro_key(q, nv), ()))
            res.append((nv.raw, classify(nv, text, source_status=status, family=family,
                                          ranges=ranges, corroborating_sources=corr, quantity=q)))
        # évasion silencieuse : uniquement pertinent quand la source est prouvée (sinon déjà source_not_captured)
        if status in PROVEN_STATUSES:
            for tok in _unverifiable_tokens(text, family, ranges, vals):
                res.append((tok, "numeric_unit_conflict"))
    return res


def gate_numeric_value_exactitude(claims: list[dict], *, family: str, ranges: dict) -> list[str]:
    """Violations (str) = toute valeur non `numeric_verified`. Vide → toutes vérifiées."""
    out: list[str] = []
    for raw, verdict in classify_all(claims, family=family, ranges=ranges):
        if verdict != "numeric_verified":
            out.append(f"{verdict}: {raw!r}")
    return out
