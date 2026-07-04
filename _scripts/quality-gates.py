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


def gate_source_catalog_raw_refs(source_catalog: dict[str, dict]) -> tuple[list[str], list[str]]:
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
        # Evidence sub-fields
        ev = r.get("evidence") or {}
        if isinstance(ev, dict):
            for k in ("confidence", "source_policy", "reviewed", "diagnostic_safe"):
                if k not in ev:
                    issues.append(f"schema_invalid: diagnostic_relations[{i}].evidence missing {k}")
            conf = ev.get("confidence")
            policy = ev.get("source_policy")
            sources = r.get("sources") or []
            # Policy violation
            if policy == "1_high":
                # Need ≥ 1 source whose source_type allows high
                has_high = any(
                    source_catalog.get(s, {}).get("type") in {"oem_manual", "oem_workshop", "tecdoc_official", "normative_standard", "parts_feed_certified"}
                    for s in sources
                )
                if not has_high:
                    issues.append(
                        f"source_policy_violated: diagnostic_relations[{i}] policy=1_high but no source with type allowing 'high' confidence"
                    )
            elif policy == "2_medium_concordant":
                medium_sources = [s for s in sources if source_catalog.get(s, {}).get("type") in SOURCE_TYPE_TO_MAX_CONFIDENCE]
                # Distinct references (>= 2 distinct slugs)
                if len(set(medium_sources)) < 2:
                    issues.append(
                        f"source_policy_violated: diagnostic_relations[{i}] policy=2_medium_concordant but < 2 distinct sources"
                    )
            elif policy == "manual_review":
                # OK — fiche bloquée jusqu'à revue humaine, pas FAIL ici
                pass
            elif policy is not None:
                issues.append(
                    f"schema_invalid: diagnostic_relations[{i}].evidence.source_policy invalid: {policy}"
                )
            # Confidence overclaim : high requires source_type allowing high
            if conf == "high":
                has_eligible = any(
                    SOURCE_TYPE_TO_MAX_CONFIDENCE.get(source_catalog.get(s, {}).get("type"), "low") == "high"
                    for s in sources
                )
                if not has_eligible:
                    issues.append(
                        f"confidence_overclaimed: diagnostic_relations[{i}] confidence=high but no source has eligible source_type"
                    )
        # Sources slugs must exist in catalog
        for s in r.get("sources") or []:
            # Tolerate page suffix like bosch_fad_2020_p27 → strip _pNN
            base = re.sub(r"_p\d+$", "", s)
            if base not in source_catalog:
                issues.append(
                    f"source_slug_unknown: diagnostic_relations[{i}] cites '{s}' (base '{base}') absent from _meta/source-catalog.yaml"
                )
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
