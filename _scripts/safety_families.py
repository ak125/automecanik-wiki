#!/usr/bin/env python3
"""safety_families — classification sécurité-critique unifiée (SINGLE SOURCE, ADR fix #5).

Source UNIQUE consommée par :
  - ``promote.py::_is_safety_proposal`` — garde TIER B : une fiche sécurité n'est JAMAIS auto-promue ;
  - ``quality-gates.py::gate_safety_unsourced`` — relations diagnostiques non sourcées en famille sécurité.

Les deux modules l'importent en LAZY (les scripts ``_scripts/`` sont chargés par chemin de fichier —
pas d'import module-top sur un sibling). Patterns alignés sur
``auto_review_wiki_proposal.detect_safety_category`` (monorepo) → classification identique des 2 côtés.

Familles : freinage, direction, distribution, electricite-safety, airbag, suspension.
Classif robuste (``entity_data.family`` souvent ABSENT des proposals) : family + tokens slug/alias/title.
Fail-closed : doute / erreur → True (sécurité → revue humaine).
"""
from __future__ import annotations

import re

SAFETY_FAMILY_LABELS = {
    "freinage", "direction", "distribution", "electricite-safety", "airbag", "suspension",
}

SAFETY_SLUG_PATTERNS = {
    "freinage": re.compile(
        r"(?i)(\bfrein|plaquette|disque-de-frein|etrier|ma[iî]tre-cylindre|"
        r"\babs\b|liquide-de-frein|flexible-de-frein|capteur-d-usure)"
    ),
    "direction": re.compile(
        r"(?i)(\bdirection|cremaillere|rotule|biellette|colonne-de-direction|\btransmission\b)"
    ),
    "airbag": re.compile(r"(?i)\bairbag"),
    "suspension": re.compile(
        r"(?i)(amortisseur|ressort-de-suspension|\bressort\b|triangle-de-suspension|"
        r"\bbras-(?:oscillant|de-suspension)|silentbloc-de-triangle)"
    ),
    "distribution": re.compile(
        r"(?i)(distribution|courroie-de-distribution|cha[iî]ne-de-distribution|"
        r"galet-tendeur|tendeur-de-distribution|pompe-a-eau)"
    ),
}


def is_safety_proposal(fm: dict) -> bool:
    """True si la fiche relève d'une famille sécurité-critique. Fail-closed (doute → True).

    Deux signaux : ``entity_data.family`` explicite (souvent absent) + tokens sur
    slug / aliases / title (miroir monorepo ``detect_safety_category``).
    """
    try:
        family = ((fm.get("entity_data") or {}).get("family") or "").strip().lower()
        if family in SAFETY_FAMILY_LABELS:
            return True
        hay = " ".join([
            str(fm.get("slug") or ""),
            str(fm.get("title") or ""),
            " ".join(str(a) for a in (fm.get("aliases") or [])),
        ]).lower()
        return any(p.search(hay) for p in SAFETY_SLUG_PATTERNS.values())
    except Exception:
        return True
