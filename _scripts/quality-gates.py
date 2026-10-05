#!/usr/bin/env python3
"""Run quality gates §2 + §5.bis of _meta/quality-gates.md on wiki/proposals files.

Gates §2 (legacy v1.0) — read-only, aucune écriture DB :
    schema_invalid           — frontmatter required keys missing
    sources_missing          — source_refs vide (sauf truth_level=L4)
    slug_collision           — slug déjà présent dans entity-registry
    pollution_detected       — fragments scrape (Textar, Brembo, "Skip to main content"…)
    catalog_leak             — prix/stock/SKU/compatibilité exacte
    commercial_promise       — promesses commerciales
    safety_unsourced         — affirmation safety sans source confidence: high

Gates §5.bis (canon ADR-033 §D1-§D3) :
    relation_to_part_missing     — entrée diagnostic_relations[] sans relation_to_part
    symptom_unstructured         — lexique symptôme dans corps non miroité dans diagnostic_relations[]
    confidence_overclaimed       — evidence.confidence: high mais source_type ne le permet pas
    source_policy_violated       — source_policy non respecté
    legacy_symptoms_block        — diagnostic.symptoms: présent (anti-pattern ADR-033 §D2)
    forbidden_systemes_dir       — fichier sous wiki/systemes/ (anti-pattern §D3)
    forbidden_per_symptom_file   — fichier wiki/diagnostic/<symptom>-*.md (anti-pattern §D3)
    source_slug_unknown          — slug absent de _meta/source-catalog.yaml
    maintenance_advice_missing   — kg_nodes.MaintenanceInterval mais pas entity_data.maintenance.educational_advice (ADR-032)

Gates ADR-112 / ADR-113 (amendements d'ADR-033) :
    citation_span_invalid                    — citations[].end <= start
    citation_source_not_in_sources           — source citée absente des sources[] de l'entrée
    citation_source_not_raw_proven           — source citée non active ou sans raw_ref (gen_coverage_map.is_page_proven)
    diagnostic_not_applicable_with_relations — constat « sans relation » + diagnostic_relations[] non vide
    quick_check_cause_unlinked               — diagnostic.quick_checks[].cause_slug absent des cause_slug de la fiche
    safety_rules_path_invalid                — safety_rules hors wiki/diagnostic/regles-securite.md
    safety_rule_slug_duplicate               — rule_slug déclaré deux fois
    (cross-repo, à la promotion : gate_citation_anchors — span + empreinte contre l'archive RAW épinglée)

Usage:
    quality-gates.py <file>...
    quality-gates.py --all

Exit:
    0 — all PASS
    1 — at least one FAIL
    2 — script error

Reference: plan rev 6 + ADR-033 + ADR-032 + _meta/quality-gates.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("FATAL: PyYAML required\n")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTITY_REGISTRY = REPO_ROOT / "_meta" / "entity-registry.json"
SOURCE_CATALOG = REPO_ROOT / "_meta" / "source-catalog.yaml"

# Plan humble-cuddling-scott P2 — sibling automecanik-raw repo pour cross-repo
# content-addressing. Local : assumé en sibling de wiki repo. CI : clone explicite.
# Override via env AUTOMECANIK_RAW_PATH si layout différent.
import os
RAW_REPO_PATH = Path(os.environ.get("AUTOMECANIK_RAW_PATH", REPO_ROOT.parent / "automecanik-raw")).resolve()
RAW_INVENTORY = RAW_REPO_PATH / "manifests" / "source-inventory.csv"
RAW_CHECKSUMS = RAW_REPO_PATH / "manifests" / "checksums.json"

# Pollution markers — common scrape artefacts
POLLUTION_PATTERNS = [
    r"\bSkip to main content\b",
    r"\bAccept (all )?cookies?\b",
    r"\bSubscribe to our newsletter\b",
    r"\bTextar\b",
    r"\bBrembo\b",
    r"<script[\s>]",
    r"<iframe[\s>]",
    r"\b(?:Loading|Chargement)…\b",
    r"\bCookie [Pp]olicy\b",
]

CATALOG_LEAK_PATTERNS = [
    r"\b\d+[,.]?\d*\s*€\b",
    r"\b€\s*\d+[,.]?\d*\b",
    # SKU/EAN format : alphanumeric with at least one digit and hyphen/digits
    r"\b(?:SKU|EAN)\s*:?\s*[A-Z0-9][A-Z0-9-]{4,}\b",
    # Réf./Référence followed by code-like token (must contain digit)
    r"\b(?:Réf\.?|Référence)\s*:?\s*(?=[A-Z0-9-]*\d)[A-Z][A-Z0-9-]{3,}\b",
    r"\bstock\s*:?\s*\d+\b",
    r"\b(?:en|hors)\s+stock\b",
    r"\bcompatible avec (?:la |le |les |l')?\w+\s+\w+\s+\d{2,4}\b",
]

COMMERCIAL_PROMISE_PATTERNS = [
    r"\b(?:le|la|les) meilleur(?:e|s|es)?\b",
    r"\bgaranti(?:e|es|s)?\s+(?:à|a)\s+(?:100|cent)\s*%\b",
    r"\ble moins cher\b",
    r"\boffre exclusive\b",
    r"\bprix imbattable\b",
    r"\bsatisfait ou remboursé\b",
]

# Lexique symptômes implicites (français)
IMPLICIT_SYMPTOM_LEXICON = [
    r"\bbruit(?:s)?\b",
    r"\bgrincement(?:s)?\b",
    r"\bclaquement(?:s)?\b",
    r"\bsifflement(?:s)?\b",
    r"\busure\s+(?:anormale|irr[eé]guli[eè]re|pr[eé]matur[eé]e)\b",
    r"\bvibration(?:s)?\b",
    r"\bvoyant(?:s)?\b",
    r"\bfum[eé]e\b",
    r"\bsurchauffe\b",
    r"\bfuite(?:s)?\b",
    r"\bjeu(?:x)?\s+(?:anormal|excessif)\b",
    r"\bbroute\b",
    r"\bcale\b",
    r"\bperte\s+de\s+puissance\b",
]

# Pattern fichier-par-symptôme interdit (anti-pattern ADR-033 §D3)
FORBIDDEN_PER_SYMPTOM_RE = re.compile(
    r"/(bruit|grincement|vibration|voyant|fumee|fumée|surchauffe|fuite|usure|symptome|symptôme|claquement|sifflement)[a-z0-9_-]*\.md$",
    re.IGNORECASE,
)

# Chemin unique des règles de sécurité (ADR-112 D1 : fixé par la PR de schéma, phase 0)
SAFETY_RULES_PATH = "wiki/diagnostic/regles-securite.md"

# Source types → max confidence autorisée. SoT machine UNIQUE = _meta/source-catalog.yaml
# › source_type_max_confidence (doc prose miroir : source-policy.md §9.1). Cutover S1d :
# lecture directe du catalogue, plus de dict hardcodé. Fail-CLOSED : SoT absente/corrompue
# → exit 2 bruyant, jamais une politique vide silencieuse (no-silent-fallback : une map
# vide ferait passer/bloquer les overclaims selon le site, donc on refuse de tourner).
def _load_source_type_max_confidence() -> dict[str, str]:
    valid = {"low", "medium", "high"}
    if not SOURCE_CATALOG.exists():
        sys.stderr.write(f"FATAL: source-catalog.yaml introuvable: {SOURCE_CATALOG}\n")
        sys.exit(2)
    try:
        data = yaml.safe_load(SOURCE_CATALOG.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        sys.stderr.write(f"FATAL: source-catalog.yaml illisible: {e}\n")
        sys.exit(2)
    m = data.get("source_type_max_confidence")
    if not isinstance(m, dict) or not m:
        sys.stderr.write(
            "FATAL: source-catalog.yaml › source_type_max_confidence manquant/vide "
            "(SoT machine, cf. source-policy.md §9.1)\n"
        )
        sys.exit(2)
    bad = {k: v for k, v in m.items() if v not in valid}
    if bad:
        sys.stderr.write(f"FATAL: source_type_max_confidence: confidences invalides {bad} (attendu ⊆ {valid})\n")
        sys.exit(2)
    return m


SOURCE_TYPE_TO_MAX_CONFIDENCE = _load_source_type_max_confidence()
CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}


# Source types → rôle éditorial (proof | corroboration). SoT machine UNIQUE = _meta/source-catalog.yaml
# › source_type_editorial_role (doc prose miroir : source-policy.md §9.1). Modélise la frontière
# métier « qui peut PROUVER un claim éditorial » orthogonalement à max_confidence : `tecdoc_official`
# est `high` mais `corroboration` (TecDoc corrobore, ne prouve pas — vérité catalogue = DB Massdoc).
# L'admissibilité éditoriale (gen_coverage_map._authoritative_types) se DÉRIVE de proof ∧ high,
# remplaçant l'ancienne blocklist hardcodée. Fail-CLOSED comme la map confidence : SoT absente,
# rôle invalide, OU parité de clés rompue avec source_type_max_confidence (dérive silencieuse d'un
# type déclaré d'un côté et pas de l'autre) → exit 2 bruyant (no-silent-fallback).
def _load_source_type_editorial_role() -> dict[str, str]:
    valid = {"proof", "corroboration"}
    if not SOURCE_CATALOG.exists():
        sys.stderr.write(f"FATAL: source-catalog.yaml introuvable: {SOURCE_CATALOG}\n")
        sys.exit(2)
    try:
        data = yaml.safe_load(SOURCE_CATALOG.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        sys.stderr.write(f"FATAL: source-catalog.yaml illisible: {e}\n")
        sys.exit(2)
    m = data.get("source_type_editorial_role")
    if not isinstance(m, dict) or not m:
        sys.stderr.write(
            "FATAL: source-catalog.yaml › source_type_editorial_role manquant/vide "
            "(SoT machine, cf. source-policy.md §9.1)\n"
        )
        sys.exit(2)
    bad = {k: v for k, v in m.items() if v not in valid}
    if bad:
        sys.stderr.write(f"FATAL: source_type_editorial_role: rôles invalides {bad} (attendu ⊆ {valid})\n")
        sys.exit(2)
    if set(m) != set(SOURCE_TYPE_TO_MAX_CONFIDENCE):
        missing = sorted(set(SOURCE_TYPE_TO_MAX_CONFIDENCE) - set(m))
        extra = sorted(set(m) - set(SOURCE_TYPE_TO_MAX_CONFIDENCE))
        sys.stderr.write(
            "FATAL: source_type_editorial_role: parité de clés rompue avec source_type_max_confidence "
            f"(sans rôle={missing}, sans confidence={extra}) — chaque source_type DOIT déclarer "
            "max_confidence ET editorial_role\n"
        )
        sys.exit(2)
    return m


SOURCE_TYPE_EDITORIAL_ROLE = _load_source_type_editorial_role()

# Slugs maintenance hardcoded (en attendant Phase 3 export)
KG_MAINTENANCE_INTERVAL_SLUGS = {
    "filtre-a-huile",
    "filtre-a-air",
    "filtre-habitacle",
    "liquide-de-frein",
    "plaquette-de-frein",
    "disque-de-frein",
    "kit-de-distribution",
    "liquide-de-refroidissement",
    "batterie",
    "amortisseur",
    "pneu",
    "bougies-d-allumage",
    "huile-moteur",
}


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 5 :]


def parse_fm(text: str) -> tuple[dict, str]:
    fm_yaml, body = split_frontmatter(text)
    if not fm_yaml:
        return {}, text
    try:
        fm = yaml.safe_load(fm_yaml) or {}
    except yaml.YAMLError:
        fm = {}
    return fm if isinstance(fm, dict) else {}, body


def load_registry() -> dict:
    if not ENTITY_REGISTRY.exists():
        return {"gammes": {}, "vehicles": {}, "constructeurs": {}, "support": {}, "diagnostic": {}}
    try:
        return json.loads(ENTITY_REGISTRY.read_text())
    except json.JSONDecodeError:
        return {}


def load_source_catalog() -> dict[str, dict]:
    """Returns dict of slug → source entry."""
    if not SOURCE_CATALOG.exists():
        return {}
    try:
        data = yaml.safe_load(SOURCE_CATALOG.read_text())
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    sources = data.get("sources", []) or []
    result = {}
    for s in sources:
        if isinstance(s, dict) and "slug" in s:
            result[s["slug"]] = s
    return result


# --- Plan P2 — cross-repo content-addressing (raw_ref) ---


def load_raw_inventory() -> tuple[set[str], dict[str, str], set[str], str]:
    """Returns (manifest_ids set, manifest_id→sha256 dict, duplicate_ids set, msg).

    Lit automecanik-raw/manifests/source-inventory.csv. msg explique l'état
    pour le rapport de gate (présent ou absent + raison).

    duplicate_ids = manifest_id apparaissant >1 fois dans l'inventaire consommé.
    Défense wiki INDÉPENDANTE du gate natif RAW (recompute depuis le CSV réellement
    consommé, aucun tri / premier / dernier gagnant silencieux). Contrat IDENTIQUE au
    SoT RAW : exception gouvernée `rec-<doc_id>` (recyclé, PARTAGÉ à dessein entre les
    chunks s001..sNNN d'un document) exclue — miroir de l'invariant H2
    automecanik-raw/_scripts/regen-manifests.py (`if not mid.startswith("rec-")`).
    Un fork plus strict côté wiki rougirait à tort une donnée RAW gouvernée-légale."""
    if not RAW_INVENTORY.exists():
        return set(), {}, set(), f"raw inventory absent at {RAW_INVENTORY}"
    import csv
    manifest_ids: set[str] = set()
    sha_by_id: dict[str, str] = {}
    seen: set[str] = set()
    duplicate_ids: set[str] = set()
    try:
        with RAW_INVENTORY.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mid = row.get("manifest_id", "").strip()
                sha = row.get("sha256", "").strip()
                if mid:
                    if mid in seen and not mid.startswith("rec-"):
                        duplicate_ids.add(mid)  # doublon-preuve → gate FAIL (jamais un last-wins)
                    seen.add(mid)
                    manifest_ids.add(mid)
                    if sha:
                        sha_by_id[mid] = sha
        return manifest_ids, sha_by_id, duplicate_ids, f"loaded {len(manifest_ids)} manifest_ids from {RAW_INVENTORY}"
    except (OSError, csv.Error) as e:
        return set(), {}, set(), f"failed to read {RAW_INVENTORY}: {e}"


def source_archive_paths(source_catalog: dict[str, dict]) -> tuple[dict[str, Path], list[str]]:
    """Resolve only requested active source pages inside the selected RAW checkout.

    Shared by the promotion snapshot and integrity gate. A recycled document can
    have multiple chunks: the expected hash must identify one concrete archive.
    No reading of a target outside RAW, including escaped symlinks.
    """
    import csv
    requested = {slug: entry for slug, entry in source_catalog.items()
                 if entry.get("status") == "active"}
    if not requested:
        return {}, []
    with RAW_INVENTORY.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    root = RAW_INVENTORY.parent.parent.resolve()
    paths, failures = {}, []
    for slug, entry in requested.items():
        ref = entry.get("raw_ref") or {}
        mid, digest = ref.get("manifest_id"), ref.get("expected_sha256")
        matches = [row for row in rows if mid and row.get("manifest_id", "").strip() == mid
                   and digest and row.get("sha256", "").strip() == digest]
        if len(matches) != 1:
            failures.append(f"raw_archive_unresolved:{slug}: expected one archive with matching id/hash")
            continue
        raw_path = matches[0].get("path", "")
        path = (root / raw_path).resolve()
        if not raw_path or root not in path.parents:
            failures.append(f"raw_archive_path_invalid:{slug}: outside RAW or empty")
            continue
        paths[slug] = path
    return paths, failures


# Statuts worklist RAW (ingestion-worklist.schema.json) qui portent une archive capturée.
# TODO / GATED / REJECTED n'en portent pas : rapportés, jamais comptés comme capture.
RAW_CAPTURED_STATUSES = frozenset({"CAPTURED", "CAPTURED_NEEDS_REVIEW", "PROMOTED"})


def _is_positive_id(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def raw_worklist_captures(slug: str, pg_id: int | None) -> dict:
    """Captures RAW d'UNE gamme, liées par son identité canonique `entity_ref.pg_id`.

    Lit `manifests/ingestion-worklist.yaml` du checkout RAW sélectionné (même point
    d'override que RAW_INVENTORY). Contrat RAW (`_schemas/ingestion-worklist.schema.json`) :
    l'identité est `entity_ref` ; le libellé `gamme` est DESCRIPTIF. Donc :
      • aucun rattachement par libellé seul : un item sans `entity_ref.pg_id` n'est jamais
        compté, seulement rapporté dans `unbound_same_label` ;
      • même pg_id mais libellé ≠ slug ⇒ `mismatch` (liaison ambiguë, fail-closed côté appelant) ;
      • une capture ne compte que si son `capture.raw_path` désigne UNE ligne de l'inventaire,
        dans le checkout RAW, dont les octets ont le sha256 inventorié (même contrat que
        `source_archive_paths` + vérification d'archive de `gate_source_catalog_raw_refs`).
    Lecture seule : une capture reste `CAPTURED_NEEDS_REVIEW` et ne devient jamais ici une
    source catalog `active` (acte owner, `check-activation-guard.py`).
    `readable=False` ⇔ worklist ou inventaire illisible : l'appelant rend UNKNOWN, jamais un faux 0."""
    import csv
    import hashlib
    manifests = RAW_INVENTORY.parent
    worklist_path = manifests / "ingestion-worklist.yaml"
    out = {"worklist": str(worklist_path), "pg_id": pg_id, "readable": True, "detail": None,
           "resolved": [], "not_captured": [], "mismatch": [], "failures": [],
           "unbound_same_label": []}
    if not _is_positive_id(pg_id):
        return {**out, "pg_id": None, "detail": "pg_id_absent"}
    if not worklist_path.is_file():
        return {**out, "detail": "worklist_absent"}
    try:
        data = yaml.safe_load(worklist_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        return {**out, "readable": False, "detail": f"worklist_unreadable: {e}"}
    items = data.get("worklist") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return {**out, "readable": False, "detail": "worklist_malformed: clé `worklist` (liste) absente"}

    captured = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            out["failures"].append(f"worklist_item_malformed:#{index}")
            continue
        wid, label = item.get("id"), item.get("gamme")
        ref = item.get("entity_ref")
        bound = (item.get("subject_type") == "gamme" and isinstance(ref, dict)
                 and _is_positive_id(ref.get("pg_id")) and ref.get("pg_id") == pg_id)
        if not bound:
            if label == slug:
                out["unbound_same_label"].append(wid)
            continue
        if label != slug:
            out["mismatch"].append({"worklist_id": wid, "gamme": label})
            continue
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        capture = item.get("capture") if isinstance(item.get("capture"), dict) else {}
        record = {"worklist_id": wid, "status": capture.get("status"),
                  "authoritative_domain": source.get("authoritative_domain"),
                  "url": source.get("url"), "source_type": source.get("source_type")}
        if capture.get("status") not in RAW_CAPTURED_STATUSES:
            out["not_captured"].append(record)
        elif not isinstance(capture.get("raw_path"), str) or not capture["raw_path"]:
            out["failures"].append(f"capture_raw_path_absent:{wid}")
        else:
            captured.append({**record, "raw_path": capture["raw_path"]})
    if not captured:
        return out

    if not RAW_INVENTORY.is_file():
        return {**out, "readable": False, "detail": f"raw inventory absent at {RAW_INVENTORY}"}
    try:
        with RAW_INVENTORY.open(encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
    except (OSError, csv.Error) as e:
        return {**out, "readable": False, "detail": f"raw inventory unreadable: {e}"}
    root = manifests.parent.resolve()
    for record in captured:
        wid, raw_path = record["worklist_id"], record["raw_path"]
        path = (root / raw_path).resolve()
        if root not in path.parents:
            out["failures"].append(f"raw_archive_path_invalid:{wid}: outside RAW")
            continue
        matches = [row for row in rows if (row.get("path") or "").strip() == raw_path]
        if len(matches) != 1:
            out["failures"].append(f"raw_archive_unresolved:{wid}: expected one inventory row for {raw_path}")
            continue
        manifest_id = (matches[0].get("manifest_id") or "").strip()
        expected = (matches[0].get("sha256") or "").strip()
        if not manifest_id:
            out["failures"].append(f"raw_archive_unresolved:{wid}: inventory row without manifest_id")
            continue
        if not path.is_file():
            out["failures"].append(f"raw_archive_missing:{wid}")
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        actual = "sha256:" + digest.hexdigest()
        if actual != expected:
            out["failures"].append(f"raw_archive_sha_drift:{wid}: expected={expected} actual={actual}")
            continue
        out["resolved"].append({**record, "manifest_id": manifest_id, "sha256": expected})
    out["resolved"].sort(key=lambda r: str(r["worklist_id"]))
    return out


def gate_source_catalog_raw_refs(source_catalog: dict[str, dict], *,
                                 verify_archive_slugs: set[str] | None = None) -> tuple[list[str], list[str]]:
    """Plan P2 — valide raw_ref cross-repo + arbitrage transition raw_ref vs archived_at.

    Returns (failures, warnings). Tableau d'arbitrage 4 cas :

      | raw_ref | archived_at | status     | comportement |
      | ✓       | -           | active     | check raw inventory — FAIL-CLOSED si unresolved / duplicate / raw injoignable (H1-B) |
      | ✓       | -           | to_capture | OK (pas de check, pas encore capturé) |
      | -       | ✓           | active     | WARN legacy_archived_at_deprecated (jusqu'à J+30) |
      | -       | ✓           | to_capture | OK (mode legacy, transition) |
      | ✓       | ✓           | -          | priority raw_ref ; archived_at ignoré silencieusement |
      | -       | -           | -          | FAIL source_unreferenceable |
    """
    failures: list[str] = []
    warnings: list[str] = []
    manifest_ids, sha_by_id, duplicate_ids, raw_msg = load_raw_inventory()
    raw_available = bool(manifest_ids)

    for slug, entry in source_catalog.items():
        raw_ref = entry.get("raw_ref")
        archived_at = entry.get("archived_at")
        status = entry.get("status", "active")

        if not raw_ref and not archived_at:
            failures.append(f"source_unreferenceable:{slug}: ni raw_ref ni archived_at")
            continue

        if raw_ref:
            if not isinstance(raw_ref, dict):
                failures.append(f"raw_ref_malformed:{slug}: raw_ref must be a dict")
                continue
            mid = raw_ref.get("manifest_id")
            expected_sha = raw_ref.get("expected_sha256")
            if not mid:
                failures.append(f"raw_ref_missing_manifest_id:{slug}")
                continue

            # Cross-repo check (only if raw inventory is reachable AND status: active)
            if status == "active" and raw_available:
                if mid in duplicate_ids:
                    failures.append(
                        f"duplicate_manifest_id:{slug}: manifest_id={mid} apparaît >1 fois dans le raw inventory (preuve ambiguë)"
                    )
                elif mid not in manifest_ids:
                    failures.append(f"source_unresolved:{slug}: manifest_id={mid} absent du raw inventory")
                elif expected_sha and mid in sha_by_id and sha_by_id[mid] != expected_sha:
                    failures.append(f"source_sha_drift:{slug}: expected={expected_sha} actual={sha_by_id[mid]}")
            elif status == "active" and not raw_available:
                # Preuve DÉCLARÉE (active + raw_ref) mais raw inventory injoignable =
                # preuve invérifiable cross-repo → FAIL-CLOSED (no silent fallback).
                # Garde catégorie : cette branche n'est atteinte QUE par une entrée active
                # (0 active → jamais ici, même RAW absent → PASS).
                failures.append(
                    f"raw_inventory_unreachable:{slug}: preuve déclarée invérifiable cross-repo ({raw_msg})"
                )
            # status: to_capture → OK (pas de check, c'est l'état attendu)

        # archived_at sans raw_ref → legacy mode, deprecate-before-rename
        if archived_at and not raw_ref:
            if status == "active":
                warnings.append(
                    f"legacy_archived_at_deprecated:{slug}: pas de raw_ref ; migrer avant deadline (Plan P2)"
                )
            # to_capture seul — OK, mode transition silencieux

    if verify_archive_slugs:
        # Promotion only: catalog declarations and CSV rows are not file proof.
        # Keep the preparatory catalog lint usable for unarchived candidates.
        import hashlib
        selected = {slug: source_catalog[slug] for slug in verify_archive_slugs
                    if slug in source_catalog}
        paths, path_failures = source_archive_paths(selected)
        failures.extend(path_failures)
        for slug, path in sorted(paths.items()):
            if not path.is_file():
                failures.append(f"raw_archive_missing:{slug}")
                continue
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            actual = "sha256:" + digest.hexdigest()
            expected = selected[slug]["raw_ref"]["expected_sha256"]
            if actual != expected:
                failures.append(f"raw_archive_sha_drift:{slug}: expected={expected} actual={actual}")

    return failures, warnings


# --- Gates legacy §2 ---

def gate_schema_invalid(fm: dict) -> list[str]:
    required = ["schema_version", "id", "entity_type", "slug", "title", "lang"]
    missing = [k for k in required if k not in fm]
    if missing:
        return [f"schema_invalid: missing keys {missing}"]
    return []


def gate_sources_missing(fm: dict) -> list[str]:
    refs = fm.get("source_refs") or []
    if fm.get("truth_level") == "L4":
        return []
    if not refs:
        return ["sources_missing: source_refs is empty"]
    return []


def gate_slug_collision(fm: dict, registry: dict, current_path: Path) -> list[str]:
    slug = fm.get("slug")
    et = fm.get("entity_type")
    if not slug or not et:
        return []
    bucket_key = f"{et}s" if not et.endswith("s") else et
    bucket = registry.get(bucket_key) or registry.get(et) or {}
    if slug in bucket:
        existing_path = (
            bucket[slug] if isinstance(bucket[slug], str) else bucket[slug].get("origin", "")
        )
        if existing_path:
            existing_full = REPO_ROOT / existing_path
            if existing_full.resolve() != current_path.resolve():
                return [f"slug_collision: slug '{slug}' already in registry as {existing_path}"]
    return []


def gate_pollution(body: str) -> list[str]:
    issues = []
    for pat in POLLUTION_PATTERNS:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            issues.append(f"pollution_detected: matched /{pat}/ → {m.group(0)!r}")
    return issues


def gate_catalog_leak(body: str) -> list[str]:
    issues = []
    for pat in CATALOG_LEAK_PATTERNS:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            issues.append(f"catalog_leak: matched /{pat}/ → {m.group(0)!r}")
    return issues


def gate_commercial_promise(body: str) -> list[str]:
    issues = []
    for pat in COMMERCIAL_PROMISE_PATTERNS:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            issues.append(f"commercial_promise: matched /{pat}/ → {m.group(0)!r}")
    return issues


# --- Gates ADR-033 / ADR-032 ---

def gate_diagnostic_relations(fm: dict, source_catalog: dict[str, dict]) -> list[str]:
    """Validate diagnostic_relations[] entries per ADR-033 §D1."""
    issues = []
    relations = fm.get("diagnostic_relations") or []
    if not isinstance(relations, list):
        return ["schema_invalid: diagnostic_relations must be an array"]
    for i, r in enumerate(relations):
        if not isinstance(r, dict):
            issues.append(f"schema_invalid: diagnostic_relations[{i}] not a mapping")
            continue
        # Required fields
        for field in ("symptom_slug", "system_slug", "relation_to_part", "part_role", "evidence", "sources"):
            if field not in r:
                if field == "relation_to_part":
                    issues.append(f"relation_to_part_missing: diagnostic_relations[{i}] symptom={r.get('symptom_slug', '?')}")
                else:
                    issues.append(f"schema_invalid: diagnostic_relations[{i}] missing {field}")
        rtp = r.get("relation_to_part")
        if rtp and rtp not in {"possible_cause", "symptom_amplifier", "secondary_effect"}:
            issues.append(f"schema_invalid: diagnostic_relations[{i}].relation_to_part invalid: {rtp}")
        issues += _evidence_and_sources_issues(f"diagnostic_relations[{i}]", r, source_catalog)
        issues += _citation_issues(f"diagnostic_relations[{i}]", r, source_catalog)
    return issues


def _evidence_and_sources_issues(label: str, entry: dict, source_catalog: dict[str, dict]) -> list[str]:
    """Evidence (ADR-033 §D1) + source slugs of one sourced entry.

    Shared by diagnostic_relations[], diagnostic.quick_checks[] and safety_rules[]
    (ADR-112 D1) : same evidence object, same source catalog, same messages."""
    issues = []
    # Evidence sub-fields
    ev = entry.get("evidence") or {}
    if isinstance(ev, dict):
        for k in ("confidence", "source_policy", "reviewed", "diagnostic_safe"):
            if k not in ev:
                issues.append(f"schema_invalid: {label}.evidence missing {k}")
        conf = ev.get("confidence")
        policy = ev.get("source_policy")
        sources = entry.get("sources") or []
        # Policy violation
        if policy == "1_high":
            # Need ≥ 1 source whose source_type allows high
            has_high = any(
                source_catalog.get(s, {}).get("type") in {"oem_manual", "oem_workshop", "tecdoc_official", "normative_standard", "parts_feed_certified"}
                for s in sources
            )
            if not has_high:
                issues.append(
                    f"source_policy_violated: {label} policy=1_high but no source with type allowing 'high' confidence"
                )
        elif policy == "2_medium_concordant":
            medium_sources = [s for s in sources if source_catalog.get(s, {}).get("type") in SOURCE_TYPE_TO_MAX_CONFIDENCE]
            # Distinct references (>= 2 distinct slugs)
            if len(set(medium_sources)) < 2:
                issues.append(
                    f"source_policy_violated: {label} policy=2_medium_concordant but < 2 distinct sources"
                )
        elif policy == "manual_review":
            # OK — fiche bloquée jusqu'à revue humaine, pas FAIL ici
            pass
        elif policy is not None:
            issues.append(
                f"schema_invalid: {label}.evidence.source_policy invalid: {policy}"
            )
        # Confidence overclaim : high requires source_type allowing high
        if conf == "high":
            has_eligible = any(
                SOURCE_TYPE_TO_MAX_CONFIDENCE.get(source_catalog.get(s, {}).get("type"), "low") == "high"
                for s in sources
            )
            if not has_eligible:
                issues.append(
                    f"confidence_overclaimed: {label} confidence=high but no source has eligible source_type"
                )
    # Sources slugs must exist in catalog
    for s in entry.get("sources") or []:
        # Tolerate page suffix like bosch_fad_2020_p27 → strip _pNN
        base = re.sub(r"_p\d+$", "", s)
        if base not in source_catalog:
            issues.append(
                f"source_slug_unknown: {label} cites '{s}' (base '{base}') absent from _meta/source-catalog.yaml"
            )
    return issues


def _is_page_proven(entry: dict) -> bool:
    """raw_proven (ADR-112 D2) = gen_coverage_map.is_page_proven, the single definition."""
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from gen_coverage_map import is_page_proven
    return is_page_proven(entry)


def _citation_issues(label: str, entry: dict, source_catalog: dict[str, dict]) -> list[str]:
    """Same-repo checks of citations[] (ADR-112 §Amendements d'ADR-033).

    The anchor itself (span + quote digest against the RAW archive bytes) needs RAW :
    `gate_citation_anchors`, run by the promotion provenance evaluator."""
    citations = entry.get("citations")
    if citations is None:
        return []
    if not isinstance(citations, list):
        return [f"schema_invalid: {label}.citations must be an array"]
    issues = []
    source_bases = {re.sub(r"_p\d+$", "", s) for s in entry.get("sources") or [] if isinstance(s, str)}
    for j, c in enumerate(citations):
        where = f"{label}.citations[{j}]"
        if not isinstance(c, dict):
            issues.append(f"schema_invalid: {where} not a mapping")
            continue
        start, end = c.get("start"), c.get("end")
        if type(start) is int and type(end) is int and end <= start:
            issues.append(f"citation_span_invalid: {where} end={end} <= start={start}")
        src = c.get("source")
        if not isinstance(src, str):
            issues.append(f"schema_invalid: {where} missing source")
        elif src not in source_bases:
            issues.append(f"citation_source_not_in_sources: {where} cites '{src}' absent from {label}.sources")
        elif not _is_page_proven(source_catalog.get(src) or {}):
            issues.append(
                f"citation_source_not_raw_proven: {where} cites '{src}' — not active with raw_ref.manifest_id in _meta/source-catalog.yaml"
            )
    return issues


def gate_diagnostic_not_applicable(fm: dict) -> list[str]:
    """ADR-113 §Amendements d'ADR-033 : a reviewed « no relation » statement excludes relations."""
    if "diagnostic_not_applicable" in fm and (fm.get("diagnostic_relations") or []):
        return [
            "diagnostic_not_applicable_with_relations: diagnostic_not_applicable and diagnostic_relations[] are mutually exclusive (ADR-113)"
        ]
    return []


def gate_quick_checks(fm: dict, source_catalog: dict[str, dict]) -> list[str]:
    """ADR-112 D1 : diagnostic.quick_checks[] = cause → check, tied to a cause of this fiche."""
    diagnostic = fm.get("diagnostic")
    if not isinstance(diagnostic, dict) or "quick_checks" not in diagnostic:
        return []  # legacy diagnostic.symptoms block: gate_legacy_symptoms_block
    checks = diagnostic.get("quick_checks")
    if not isinstance(checks, list):
        return ["schema_invalid: diagnostic.quick_checks must be an array"]
    relations = fm.get("diagnostic_relations") or []
    causes = {r.get("cause_slug") for r in relations if isinstance(r, dict)} if isinstance(relations, list) else set()
    issues = []
    for i, qc in enumerate(checks):
        label = f"diagnostic.quick_checks[{i}]"
        if not isinstance(qc, dict):
            issues.append(f"schema_invalid: {label} not a mapping")
            continue
        for field in ("cause_slug", "check", "evidence", "sources"):
            if field not in qc:
                issues.append(f"schema_invalid: {label} missing {field}")
        cause = qc.get("cause_slug")
        if cause and cause not in causes:
            issues.append(
                f"quick_check_cause_unlinked: {label} cause_slug '{cause}' is not a diagnostic_relations[].cause_slug of this fiche"
            )
        issues += _evidence_and_sources_issues(label, qc, source_catalog)
        issues += _citation_issues(label, qc, source_catalog)
    return issues


def gate_safety_rules(fm: dict, path: Path, source_catalog: dict[str, dict]) -> list[str]:
    """ADR-112 D1/D5 : safety rules live in ONE fiche, one entry per rule, stable rule_slug."""
    rules = fm.get("safety_rules")
    if rules is None:
        return []
    if not isinstance(rules, list):
        return ["schema_invalid: safety_rules must be an array"]
    issues = []
    try:
        rel = path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        rel = None
    # proposals/ stay free (promotion writes wiki/<entity_type>/<slug>.md, schema pins the slug)
    if rel is not None and rel.startswith("wiki/") and rel != SAFETY_RULES_PATH:
        issues.append(f"safety_rules_path_invalid: safety_rules allowed only in {SAFETY_RULES_PATH} (ADR-112 D1), found in {rel}")
    seen: set[str] = set()
    for i, rule in enumerate(rules):
        label = f"safety_rules[{i}]"
        if not isinstance(rule, dict):
            issues.append(f"schema_invalid: {label} not a mapping")
            continue
        for field in ("rule_slug", "system_slug", "condition", "evidence", "sources"):
            if field not in rule:
                issues.append(f"schema_invalid: {label} missing {field}")
        slug = rule.get("rule_slug")
        if isinstance(slug, str):
            if slug in seen:
                issues.append(f"safety_rule_slug_duplicate: {label} rule_slug '{slug}' already declared")
            seen.add(slug)
        issues += _evidence_and_sources_issues(label, rule, source_catalog)
        issues += _citation_issues(label, rule, source_catalog)
    return issues


def _sourced_entries(fm: dict) -> list[tuple[str, dict]]:
    """(label, entry) of every entry that may carry citations[] (ADR-112 D1)."""
    out = []
    relations = fm.get("diagnostic_relations")
    if isinstance(relations, list):
        out += [(f"diagnostic_relations[{i}]", r) for i, r in enumerate(relations) if isinstance(r, dict)]
    diagnostic = fm.get("diagnostic")
    checks = diagnostic.get("quick_checks") if isinstance(diagnostic, dict) else None
    if isinstance(checks, list):
        out += [(f"diagnostic.quick_checks[{i}]", c) for i, c in enumerate(checks) if isinstance(c, dict)]
    rules = fm.get("safety_rules")
    if isinstance(rules, list):
        out += [(f"safety_rules[{i}]", r) for i, r in enumerate(rules) if isinstance(r, dict)]
    return out


def cited_source_slugs(fm: dict) -> set[str]:
    """Catalog slugs named by citations[] — archives the promotion must bind and verify."""
    return {c["source"] for _, entry in _sourced_entries(fm)
            for c in (entry.get("citations") if isinstance(entry.get("citations"), list) else [])
            if isinstance(c, dict) and isinstance(c.get("source"), str)}


def gate_citation_anchors(fm: dict, source_catalog: dict[str, dict]) -> list[str]:
    """Cross-repo : each citation must match the bytes of the RAW archive pinned by
    raw_ref.expected_sha256 (ADR-112 §Amendements d'ADR-033, « ancrées dans RAW »).

    Needs RAW : run by the promotion provenance evaluator, the only path into wiki/.
    Same anchor unit and digest as document_authoring.py : Unicode code points,
    zero-based, end exclusive, on the UTF-8 text without newline translation."""
    import hashlib
    cited = cited_source_slugs(fm)
    if not cited:
        return []
    if not RAW_INVENTORY.is_file():
        return [f"raw_inventory_unreachable:citations: raw inventory absent at {RAW_INVENTORY}"]
    issues = []
    selected = {}
    for slug in sorted(cited):
        entry = source_catalog.get(slug) or {}
        if entry.get("status") == "active":
            selected[slug] = entry
        else:
            issues.append(f"citation_source_not_raw_proven:{slug}: not an active entry of _meta/source-catalog.yaml")
    paths, path_failures = source_archive_paths(selected)
    issues += path_failures
    texts: dict[str, str] = {}
    for slug, path in sorted(paths.items()):
        try:
            data = path.read_bytes()
        except OSError:
            issues.append(f"citation_archive_missing:{slug}")
            continue
        actual = "sha256:" + hashlib.sha256(data).hexdigest()
        expected = selected[slug]["raw_ref"]["expected_sha256"]
        if actual != expected:
            issues.append(f"citation_archive_sha_drift:{slug}: expected={expected} actual={actual}")
            continue
        try:
            texts[slug] = data.decode("utf-8")
        except UnicodeDecodeError:
            issues.append(f"citation_source_not_text:{slug}: archive is not UTF-8 text, no anchor possible")
    # A citation whose archive is not readable text is covered by the per-slug failure above.
    for label, entry in _sourced_entries(fm):
        citations = entry.get("citations")
        for j, c in enumerate(citations if isinstance(citations, list) else []):
            if not isinstance(c, dict) or c.get("source") not in texts:
                continue
            text, src = texts[c["source"]], c["source"]
            start, end = c.get("start"), c.get("end")
            where = f"{label}.citations[{j}]"
            if not (type(start) is int and type(end) is int and 0 <= start < end <= len(text)):
                issues.append(f"citation_span_out_of_range: {where} [{start}, {end}) outside '{src}' ({len(text)} code points)")
                continue
            digest = "sha256:" + hashlib.sha256(text[start:end].encode("utf-8")).hexdigest()
            if digest != c.get("quote_sha256"):
                issues.append(f"citation_quote_mismatch: {where} quote_sha256 does not match '{src}'[{start}:{end}]")
    return issues


def gate_legacy_symptoms_block(fm_yaml: str) -> list[str]:
    """Detect legacy `diagnostic.symptoms:` block (anti-pattern ADR-033 §D2)."""
    if re.search(r"^\s{2,}symptoms:\s*$", fm_yaml, re.MULTILINE):
        return ["legacy_symptoms_block: diagnostic.symptoms[] is forbidden (ADR-033 §D2). Use diagnostic_relations[] top-level."]
    return []


def gate_path_anti_patterns(path: Path) -> list[str]:
    """Detect forbidden filesystem paths (anti-pattern ADR-033 §D3)."""
    issues = []
    p = str(path.resolve())
    if "/wiki/systemes/" in p:
        issues.append(f"forbidden_systemes_dir: file under wiki/systemes/ is forbidden (ADR-033 §D3)")
    if "/wiki/diagnostic/" in p and FORBIDDEN_PER_SYMPTOM_RE.search(p):
        issues.append(
            f"forbidden_per_symptom_file: file matches forbidden pattern wiki/diagnostic/<symptom>-*.md (ADR-033 §D3)"
        )
    return issues


def gate_symptom_unstructured(fm: dict, body: str) -> list[str]:
    """Detect implicit symptoms in body not mirrored in diagnostic_relations[]."""
    if fm.get("entity_type") != "gamme":
        return []
    relations = fm.get("diagnostic_relations") or []
    structured_labels = " ".join(
        (r.get("symptom_slug", "") + " " + r.get("part_role", "")).lower()
        for r in relations
        if isinstance(r, dict)
    )
    detected = []
    for pat in IMPLICIT_SYMPTOM_LEXICON:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            term = m.group(0).lower()
            base = re.sub(r"s$", "", term)  # singular
            if base not in structured_labels and term not in structured_labels:
                detected.append(term)
    if detected:
        return [
            f"symptom_unstructured: implicit symptom(s) {sorted(set(detected))[:5]} in body not mirrored in diagnostic_relations[]"
        ]
    return []


def gate_safety_unsourced(fm: dict, body: str) -> list[str]:
    """For safety-critical families, each diagnostic_relations[] must satisfy source_policy."""
    if fm.get("entity_type") != "gamme":
        return []
    # Classification sécurité = SINGLE SOURCE partagé avec promote.py (ADR fix #5).
    # Import paresseux (module _scripts chargé par chemin) ; couvre les 6 familles
    # (+ airbag, suspension) et la détection par slug (entity_data.family souvent absent).
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from safety_families import is_safety_proposal
    if not is_safety_proposal(fm):
        return []
    family = (fm.get("entity_data") or {}).get("family", "") or "<slug-detected>"
    relations = fm.get("diagnostic_relations") or []
    if not relations:
        # No relations declared — OK if no implicit symptom; otherwise covered by symptom_unstructured
        return []
    issues = []
    for i, r in enumerate(relations):
        ev = (r.get("evidence") or {})
        sources = r.get("sources") or []
        if not sources:
            issues.append(f"safety_unsourced: diagnostic_relations[{i}] family={family} has no sources")
            continue
        # Already covered by gate_diagnostic_relations source_policy_violated, but keep explicit safety alert
        policy = ev.get("source_policy")
        if policy == "manual_review" and not ev.get("reviewed"):
            issues.append(
                f"safety_unsourced: diagnostic_relations[{i}] family={family} requires manual_review (status: human_review_required)"
            )
    return issues


def gate_maintenance_advice(fm: dict) -> list[str]:
    """ADR-032 §D1: gammes matching kg_nodes.MaintenanceInterval require entity_data.maintenance.educational_advice."""
    if fm.get("entity_type") != "gamme":
        return []
    slug = fm.get("slug", "")
    if slug not in KG_MAINTENANCE_INTERVAL_SLUGS:
        return []
    maintenance = (fm.get("entity_data") or {}).get("maintenance") or {}
    if not maintenance.get("educational_advice"):
        return [
            f"maintenance_advice_missing: slug '{slug}' matches kg_nodes.MaintenanceInterval but entity_data.maintenance.educational_advice is empty (ADR-032 §D1)"
        ]
    return []


# --- Runner ---

def run_gates(path: Path, registry: dict, source_catalog: dict[str, dict]) -> tuple[list[str], list[str]]:
    """Returns (failures, warnings)."""
    text = path.read_text()
    fm_yaml, body = split_frontmatter(text)
    fm, _ = parse_fm(text)

    failures: list[str] = []
    warnings: list[str] = []

    if not fm:
        return ["schema_invalid: no frontmatter"], []

    # §2 legacy gates
    failures += gate_schema_invalid(fm)
    failures += gate_sources_missing(fm)
    failures += gate_slug_collision(fm, registry, path)
    failures += gate_catalog_leak(body)
    failures += gate_commercial_promise(body)
    warnings += gate_pollution(body)

    # §5.bis ADR-033 + ADR-032 gates
    failures += gate_diagnostic_relations(fm, source_catalog)
    failures += gate_diagnostic_not_applicable(fm)
    failures += gate_quick_checks(fm, source_catalog)
    failures += gate_safety_rules(fm, path, source_catalog)
    failures += gate_legacy_symptoms_block(fm_yaml)
    failures += gate_path_anti_patterns(path)
    failures += gate_symptom_unstructured(fm, body)
    failures += gate_safety_unsourced(fm, body)
    failures += gate_maintenance_advice(fm)

    return failures, warnings


def _is_meta_path(p: Path) -> bool:
    """D19 convention: skip files whose name OR any parent component starts with `_`
    (meta containers like proposals/_quality/, proposals/_coverage/)."""
    try:
        rel = p.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        return False
    return any(part.startswith("_") for part in rel.parts)


def gather_files(args) -> list[Path]:
    if args.all or args.all_local:
        roots = [REPO_ROOT / "proposals", REPO_ROOT / "wiki"]
        files: list[Path] = []
        for root in roots:
            if root.exists():
                files.extend(p for p in root.rglob("*.md") if not _is_meta_path(p))
        return files
    return [p for p in (Path(f).resolve() for f in args.files) if not _is_meta_path(p)]


def _run_cross_repo_gate(source_catalog: dict[str, dict], *, warn_as_fail: bool) -> int:
    """`--cross-repo` — SEUL chemin autorisé à enforcer le gate cross-repo raw_ref.

    Le gate reste intrinsèquement fail-closed (preuve active + raw inventory injoignable →
    FAILURE). Ce mode ajoute, au niveau du CALLER, l'exigence que le job fournisse RÉELLEMENT
    son environnement RAW : raw inventory absent = env non fourni = FAILURE explicite
    (`cross_repo_env_missing`), jamais un pass silencieux sur 0 active. On ne conditionne PAS
    la sécurité à la présence de l'env — on EXIGE l'env pour ce mode dédié."""
    if not RAW_INVENTORY.exists():
        print(
            f"FAIL cross-repo: cross_repo_env_missing: raw inventory absent at {RAW_INVENTORY} — "
            "ce mode exige un checkout automecanik-raw (AUTOMECANIK_RAW_PATH)"
        )
        print("\ncross-repo source-catalog gate — 1 FAIL — 0 WARN (environnement RAW non fourni)")
        return 1
    failures, warnings = gate_source_catalog_raw_refs(source_catalog)
    for f in failures:
        print(f"FAIL source-catalog: {f}")
    for w in warnings:
        print(f"WARN source-catalog: {w}")
    n_active = sum(1 for e in source_catalog.values() if e.get("status", "active") == "active")
    print(
        f"\ncross-repo source-catalog gate — {len(failures)} FAIL — {len(warnings)} WARN "
        f"({n_active} entrées active vérifiées)"
    )
    if failures or (warn_as_fail and warnings):
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*")
    ap.add_argument(
        "--all", action="store_true",
        help="Toutes les fiches, gates SAME-REPO (alias de --all-local ; n'enforce PAS le cross-repo).",
    )
    ap.add_argument(
        "--all-local", action="store_true",
        help="Toutes les fiches, gates SAME-REPO uniquement — exclut le gate cross-repo raw_ref (exige automecanik-raw).",
    )
    ap.add_argument(
        "--cross-repo", action="store_true",
        help="UNIQUEMENT le gate cross-repo source-catalog raw_ref ; exige un checkout automecanik-raw. Seul chemin autorisé à l'enforcer.",
    )
    ap.add_argument("--warn-as-fail", action="store_true", help="Treat WARN as FAIL")
    args = ap.parse_args()

    # Chemin dédié cross-repo : SEUL invocateur du gate externe raw_ref (exige l'env RAW).
    if args.cross_repo:
        return _run_cross_repo_gate(load_source_catalog(), warn_as_fail=args.warn_as_fail)

    files = gather_files(args)
    if not files:
        sys.stderr.write("No files to process\n")
        return 0

    registry = load_registry()
    source_catalog = load_source_catalog()
    fail_count = 0
    warn_count = 0

    # Le gate cross-repo raw_ref n'est PAS lancé ici : il exige automecanik-raw et est exécuté
    # EXCLUSIVEMENT via `--cross-repo` par le flux GOUVERNÉ d'activation (2 repos présents+frais),
    # comme précondition de toute transition to_capture→active — PAS en CI (aucun credential
    # cross-repo secretless). Ce chemin (générique / pre-commit / --all / --all-local) ne lance
    # QUE les gates same-repo — jamais un gate RAW-dépendant dans un environnement incapable.
    for f in files:
        failures, warnings = run_gates(f, registry, source_catalog)
        if failures:
            fail_count += 1
            for issue in failures:
                print(f"FAIL {f}: {issue}")
        if warnings:
            warn_count += 1
            for issue in warnings:
                print(f"WARN {f}: {issue}")
        if not failures and not warnings:
            print(f"PASS {f}")

    total = len(files)
    print(f"\n{total - fail_count}/{total} PASS — {fail_count} FAIL — {warn_count} WARN")
    if fail_count or (args.warn_as_fail and warn_count):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
