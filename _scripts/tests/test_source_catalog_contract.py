"""Contrat source-catalog ↔ coverage (G1 Option A owner 2026-07-03, réparation #77).

Verrouille la réconciliation des DEUX schémas gouvernés distincts (le bug était de les confondre) :
  - catalog entry `status`         : enum ["active", "to_capture"]                       (source-catalog-entry.schema.json)
  - coverage entry `source_status` : enum ["pending_capture", "captured", "verified"]     (coverage-map.schema.json)

Bug réparé (G1) : le code lisait le `status` CATALOG (`active`/`to_capture`) et le testait contre l'enum
COVERAGE (`captured`/`verified`/`archived`) → intersection VIDE → AUCUNE page ne pouvait jamais être
« prouvée » (état impossible ; les anciens tests passaient sur des fixtures `status: captured` INVALIDES
au schéma catalog).

RÈGLE OWNER (G1 Option A) : page prouvée = catalog `status: active` **ET** `raw_ref` (manifest_id) présent —
l'intégrité FK/hash du raw_ref est DÉLÉGUÉE au gate existant `gate_source_catalog_raw_refs`, jamais
re-vérifiée ici. `to_capture` et `active` sans raw_ref = NON utilisable. Le source-catalog PROUVE ; la
vérité métier reste la DB Massdoc.

G2 (tecdoc_official autoritaire) = EN PAUSE (audit séparé du rôle de TecDoc) : ce contrat ne l'assert PAS.
"""
from __future__ import annotations

import gen_coverage_map as CM
import gap1_auto_review as AR


def _active_with_raw_ref(slug: str = "oem_disque", type_: str = "oem_manual") -> dict:
    return {"slug": slug, "type": type_, "status": "active",
            "raw_ref": {"repo": "automecanik-raw", "manifest_id": slug + "_x",
                        "expected_sha256": "sha256:" + "a" * 64}}


def test_source_catalog_contract_active_with_raw_ref_is_proven() -> None:
    """Cas nominal G1 : entrée catalog SCHÉMA-VALIDE `active` AVEC raw_ref = prouvée."""
    assert CM.is_page_proven(_active_with_raw_ref()) is True


def test_active_without_raw_ref_is_not_proven() -> None:
    """RÈGLE OWNER : `active` SANS raw_ref = PAS utilisable (le source-catalog exige un document/preuve)."""
    entry = {"slug": "x", "type": "oem_manual", "status": "active"}
    assert CM.is_page_proven(entry) is False


def test_to_capture_entry_is_not_proven() -> None:
    """Fail-closed : fichier pas encore archivé → non prouvée, même si manifest_id aspirationnel présent."""
    entry = {"slug": "bosch_fad", "type": "oem_manual", "status": "to_capture",
             "raw_ref": {"repo": "automecanik-raw", "manifest_id": "bosch_fad", "expected_sha256": None}}
    assert CM.is_page_proven(entry) is False


def test_phantom_captured_catalog_status_is_not_proven() -> None:
    """`captured` est une valeur COVERAGE (source_status), JAMAIS un status CATALOG valide.

    Anti-état-impossible : le code ne doit plus reconnaître le statut fantôme `captured` comme statut
    catalog prouvé (le schéma catalog n'autorise que active|to_capture). Attrape toute régression qui
    ré-introduirait la comparaison du status catalog contre l'enum coverage."""
    entry = {"slug": "x", "type": "oem_manual", "status": "captured",
             "raw_ref": {"repo": "automecanik-raw", "manifest_id": "x"}}
    assert CM.is_page_proven(entry) is False


def test_resolve_status_maps_active_authoritative_to_captured() -> None:
    """Intégration : un claim dont la source catalog est active+raw_ref+type autoritaire dans une section
    valide résout vers le token coverage `captured` (prouvé) → alimente le lock numérique sécurité.

    Type = oem_manual (manuel constructeur = preuve, `high` au SoT ⇒ dans `_authoritative_types()`
    dérivé). G2/tecdoc EN PAUSE : hors périmètre de ce test."""
    catalog = {"domain_to_slug": {"oem.example": "oem"},
               "slugs": {"oem": _active_with_raw_ref("oem")}}
    valid = {"## Critères de sélection"}
    c = {"domain": "oem.example", "section": "## Critères de sélection"}
    assert AR._resolve_status(c, catalog, valid) == "captured"
