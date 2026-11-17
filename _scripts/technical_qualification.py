"""Corroboration par un second domaine d'autorité — qualification technique v2 (ADR-131, candidat).

Il calcule hors du modèle, depuis les métadonnées des captures (`_meta/source-catalog.yaml`), le
domaine d'autorité de chaque capture, puis applique et contrôle la règle de corroboration du skill qualification-technique 0.3.0 :

- en profondeur `complete`, `conserver` exige une capture de rôle `proof` et au moins deux domaines
  distincts parmi les sources de l'affirmation, concordantes ;
- une seule source (un seul domaine) : `preciser`, portée bornée à cette source ;
- discordance entre domaines : `retirer` si l'écart touche une valeur, une procédure ou la sécurité,
  sinon `preciser` ;
- profondeur `allegee` : règle inchangée (la corroboration est consignée, rien n'est déclassé).

Une capture absente du catalogue, ou sans la métadonnée que la définition demande, n'a pas de
domaine : elle ne compte pour aucun (fail-closed).

`qualification_status` lit les artefacts versionnés d'une fiche et recalcule la condition
`technical_qualification_pass` (ADR-131 D3 à D5, D7, D9). `promotion_decision.py` l'appelle et la
consigne ; elle ne bloque que si `TECHNICAL_QUALIFICATION_ADR` y est renseignée (D6).
"""
from __future__ import annotations

import functools
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

DEFINITIONS = ("publisher_class", "source_type", "host")
PUBLISHER_CLASSES = ("constructeur", "equipementier", "referentiel_technique", "formation")
BLOCKING_DISCORDANCE = ("value", "procedure", "safety")
CONCORDANCE = ("concordant", "discordant", "single_source", "no_source", "undetermined")


def _catalog_by_cid(catalog: dict) -> dict:
    out = {}
    for entry in catalog.get("sources") or []:
        cid = (entry.get("raw_ref") or {}).get("expected_sha256")
        if cid:
            out[cid] = entry
    return out


def capture_domains(captures: list[dict], catalog: dict, definition: str) -> list[dict]:
    """Domaine d'autorité de chaque capture, calculé hors du modèle.

    `captures` : [{"path", "cid", "source_url"?}]. Le domaine vaut, selon `definition` :
    `publisher_class` (champ `publisher_class` de l'entrée du catalogue, parmi PUBLISHER_CLASSES),
    `source_type` (champ `type` de l'entrée) ou `host` (hôte de `source_url`, sans `www.`).
    """
    if definition not in DEFINITIONS:
        raise ValueError(f"définition de domaine inconnue : {definition}")
    roles = catalog.get("source_type_editorial_role") or {}
    by_cid = _catalog_by_cid(catalog)
    out = []
    for cap in sorted(captures, key=lambda c: (c["path"], c["cid"])):
        entry = by_cid.get(cap["cid"])
        publisher = entry.get("publisher") if entry else None
        role = roles.get(entry.get("type"), "unknown") if entry else "unknown"
        if definition == "publisher_class":
            value = entry.get("publisher_class") if entry else None
            domain = value if value in PUBLISHER_CLASSES else None
        elif definition == "source_type":
            domain = entry.get("type") if entry else None
        else:
            host = urlparse(cap.get("source_url") or "").hostname
            domain = host[4:] if host and host.startswith("www.") else host
        out.append({"cid": cap["cid"], "publisher": publisher, "domain": domain or None,
                    "editorial_role": role if role in ("proof", "corroboration") else "unknown"})
    return out


def corroboration_of(sources: list[dict], domains: list[dict]) -> dict:
    """Domaines, captures et présence d'une preuve parmi les passages cités d'une affirmation."""
    by_cid = {d["cid"]: d for d in domains}
    cids = sorted({s.get("cid") for s in sources if s.get("cid") in by_cid})
    found = sorted({by_cid[c]["domain"] for c in cids if by_cid[c]["domain"]})
    proof = any(by_cid[c]["editorial_role"] == "proof" and by_cid[c]["domain"] for c in cids)
    return {"domains": found, "captures": cids, "proof": proof}


def confirmed(claim: dict, depth: str) -> bool:
    """Une affirmation `complete` est confirmée par deux domaines : conserver, preuve, concordance."""
    corr = claim.get("corroboration") or {}
    return (depth == "complete" and claim.get("verdict") == "conserver" and corr.get("proof") is True
            and len(corr.get("domains") or []) >= 2 and corr.get("concordance") == "concordant")


def enforce(claim: dict, depth: str, domains: list[dict]) -> dict:
    """Recalcule la corroboration d'une affirmation et applique la règle du skill 0.3.0.

    Le modèle fournit `concordance` et `discordance_on` (il lit les passages) ; les domaines, les
    captures et la preuve sont recalculés ici et remplacent ce que le modèle a pu écrire. Une
    concordance absente ou hors contrat vaut `undetermined` (ou `single_source` sous deux domaines) :
    elle ne confirme rien. Un déclassement fait ici est consigné (`declassed_by: control`) avec le
    verdict d'origine.
    """
    out = dict(claim)
    given = dict(claim.get("corroboration") or {})
    corr = corroboration_of(claim.get("sources") or [], domains)
    concordance = given.get("concordance")
    if not corr["captures"]:
        concordance = "no_source"
    elif concordance not in CONCORDANCE or concordance in ("no_source", "undetermined"):
        concordance = "single_source" if len(corr["domains"]) < 2 else "undetermined"
    elif concordance == "concordant" and len(corr["domains"]) < 2:
        concordance = "single_source"
    corr["concordance"] = concordance
    corr["discordance_on"] = given.get("discordance_on") if concordance == "discordant" and \
        given.get("discordance_on") in BLOCKING_DISCORDANCE + ("other",) else None
    corr["declassed_from"] = given.get("declassed_from") if given.get("declassed_from") in \
        ("conserver", "preciser", "reformuler") else None
    corr["declassed_by"] = "model" if corr["declassed_from"] else None
    if depth == "complete":
        verdict = out.get("verdict")
        target = None
        if concordance == "discordant" and corr["discordance_on"] in BLOCKING_DISCORDANCE:
            target = "retirer" if verdict != "retirer" else None
        elif verdict == "conserver" and not confirmed({**out, "corroboration": corr}, depth):
            target = "preciser"
        if target:
            corr["declassed_from"], corr["declassed_by"] = verdict, "control"
            out["verdict"] = target
    out["corroboration"] = corr
    return out


def corroboration_violations(run: dict) -> list[str]:
    """Contrôle déterministe d'un artefact v2 : refuse un `conserver` complete sans second domaine.

    Recalcule domaines, captures et preuve depuis `key_inputs.capture_domains` et les passages ;
    signale tout écart avec la corroboration consignée, et toute règle du skill 0.3.0 violée.
    """
    if run.get("schema_version") != "technical-qualification/v2" or run.get("role") != "qualification":
        return []
    domains = (run.get("key_inputs") or {}).get("capture_domains") or []
    out = []
    for seg in run.get("segments") or []:
        for claim in seg.get("claims") or []:
            where = f"{seg['id']} {claim.get('id')}"
            corr = claim.get("corroboration")
            if not isinstance(corr, dict):
                out.append(f"{where}: corroboration absente")
                continue
            fresh = corroboration_of(claim.get("sources") or [], domains)
            for field in ("domains", "captures", "proof"):
                if corr.get(field) != fresh[field]:
                    out.append(f"{where}: {field} consigné {corr.get(field)!r}, recalculé {fresh[field]!r}")
            if seg.get("depth") != "complete":
                continue
            if claim.get("verdict") == "conserver" and not confirmed({**claim, "corroboration": fresh | {
                    "concordance": corr.get("concordance")}}, "complete"):
                out.append(f"{where}: conserver complete sans preuve ni second domaine concordant")
            if corr.get("concordance") == "discordant" and corr.get("discordance_on") in BLOCKING_DISCORDANCE \
                    and claim.get("verdict") != "retirer":
                out.append(f"{where}: discordance sur {corr['discordance_on']} sans retirer")
    return out


def retake_questions(run: dict) -> list[dict]:
    """Questions de reprise : chaque affirmation complete non confirmée par deux domaines.

    Le motif vaut `no_capture` (aucun passage), `discordant` ou `single_domain`. La question est
    celle du modèle (`retake_question`) si elle existe, sinon un gabarit consigné comme tel.
    """
    out = []
    for seg in run.get("segments") or []:
        if seg.get("depth") != "complete":
            continue
        for claim in seg.get("claims") or []:
            if confirmed(claim, "complete"):
                continue
            corr = claim.get("corroboration") or {}
            reason = {"no_source": "no_capture", "discordant": "discordant"}.get(
                corr.get("concordance"), "single_domain")
            question = claim.get("retake_question")
            source = "model" if isinstance(question, str) and question.strip() else "template"
            if source == "template":
                have = ", ".join(corr.get("domains") or []) or "aucun"
                question = (f"Trouver une capture d'un domaine d'autorité autre que : {have}, qui porte "
                            f"ou contredit : « {claim.get('text')} »")
            out.append({"segment_id": seg["id"], "claim_id": claim["id"], "reason": reason,
                        "domains_present": list(corr.get("domains") or []), "question": question,
                        "question_source": source})
    return out


def loop_score(run: dict) -> dict:
    """Score de la boucle : part des affirmations complete confirmées par deux domaines."""
    total = hit = 0
    for seg in run.get("segments") or []:
        if seg.get("depth") != "complete":
            continue
        for claim in seg.get("claims") or []:
            total += 1
            hit += confirmed(claim, "complete")
    return {"complete_claims": total, "confirmed": hit, "score": (hit / total) if total else None}


def loop_stop(scores: list[float], target: float, max_retakes: int) -> str | None:
    """Arrêt de la boucle de reprise (seo-content-loop §5), sur l'historique des scores.

    `scores[0]` est la qualification initiale, `scores[i]` celle de la reprise i. Renvoie
    `target_reached`, `no_progress`, `max_retakes`, ou None pour une reprise de plus.
    """
    if not scores:
        return None
    if scores[-1] is not None and scores[-1] >= target:
        return "target_reached"
    if len(scores) >= 2 and (scores[-1] or 0) <= (scores[-2] or 0):
        return "no_progress"
    if len(scores) - 1 >= max_retakes:
        return "max_retakes"
    return None


# --- Condition technical_qualification_pass (ADR-131 D3) ------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent
QUALIFICATION_DIR = Path("_audit") / "technical-qualification"
RUN_SCHEMA_RELPATH = Path("_meta") / "schema" / "technical-qualification-run.schema.json"
SKILL_RELPATH = Path("_meta") / "skills" / "qualification-technique" / "SKILL.md"
CATALOG_RELPATH = Path("_meta") / "source-catalog.yaml"
# Définition du domaine retenue par ADR-131 D9 ; la base est le catalogue, source unique (D9).
DOMAIN_DEFINITION = "publisher_class"
DOMAIN_BASIS = CATALOG_RELPATH.as_posix()
VERDICT_ORDER = ("conserver", "preciser", "reformuler", "retirer")
# Plancher de profondeur (ADR-131 D4) : sections et champs qui le portent.
PROCEDURE_HEADINGS = ("## Montage", "## Entretien")
DIAGNOSTIC_HEADINGS = ("## Symptômes",)
PROCEDURE_KEYS = ("replacement_guidance", "maintenance_interval", "maintenance")
DIAGNOSTIC_KEYS = ("failure_symptoms",)
# Statuts, du plus fort au plus faible ; seul PASS rend la condition vraie.
STATUS_ORDER = ("FAIL", "HISTORY_GAP", "UNREADABLE", "CONTESTED", "PASS", "PRODUCER_UNKNOWN",
                "NOT_INDEPENDENT", "NO_FRESHNESS", "INCOMPLETE", "NO_CONTESTATION", "ERROR")


@functools.lru_cache(maxsize=None)
def _sibling(name: str):
    """Module voisin de `_scripts/`, chargé une fois par chemin (les scripts ne s'importent pas
    entre eux). `_sibling("semantic_review").ReviewInputUnavailable` signale une entrée absente."""
    spec = importlib.util.spec_from_file_location(f"_tq_{name}", SCRIPTS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # une dataclass du module se résout par sys.modules
    spec.loader.exec_module(module)
    return module


def _contains_key(value, keys) -> bool:
    if isinstance(value, dict):
        return any(k in keys or _contains_key(v, keys) for k, v in value.items())
    if isinstance(value, list):
        return any(_contains_key(v, keys) for v in value)
    return False


def depth_floors(fm: dict, segments: list[dict]) -> dict:
    """Plancher déterministe de chaque segment (ADR-131 D4) : {id: (profondeur, motifs)}.

    `complete` si l'un des motifs s'applique : `safety_family` (toute la fiche), `numeric_value`,
    `procedure`, `diagnostic_relation` ; sinon `allegee`. Mêmes règles que le banc d'étalonnage.
    """
    sf, ne = _sibling("safety_families"), _sibling("numeric_exactitude")
    safety = sf.is_safety_proposal(fm)
    heading, out = None, {}
    for seg in segments:
        sid, text = seg["id"], seg["text"]
        if sid.startswith("body:") and text.lstrip().startswith("## "):
            heading = text.strip().splitlines()[0]
        field = sid[3:] if sid.startswith("fm:") else None
        reasons = []
        if safety:
            reasons.append("safety_family")
        if ne.extract_values(text):
            reasons.append("numeric_value")
        if (field is None and heading and heading.startswith(PROCEDURE_HEADINGS)) or (
                field is not None and (field in PROCEDURE_KEYS
                                       or _contains_key(fm.get(field), PROCEDURE_KEYS))):
            reasons.append("procedure")
        if (field is None and heading and heading.startswith(DIAGNOSTIC_HEADINGS)) or \
                field == "diagnostic_relations" or \
                (field is not None and _contains_key(fm.get(field), DIAGNOSTIC_KEYS)):
            reasons.append("diagnostic_relation")
        out[sid] = ("complete" if reasons else "allegee", reasons)
    return out


def _stricter(*verdicts) -> str | None:
    """Verdict le plus strict ; None (verdict inconnu) l'emporte sur tout (fail-closed)."""
    if any(v not in VERDICT_ORDER for v in verdicts):
        return None
    return max(verdicts, key=VERDICT_ORDER.index)


def _blocks(verdict, depth: str, anchored: bool) -> bool:
    """Règle de blocage d'ADR-131 D4. Un verdict inconnu bloque (fail-closed)."""
    if verdict not in VERDICT_ORDER:
        return True
    if depth == "complete":
        return verdict != "conserver" or not anchored
    return verdict == "retirer"


def expected_key(fm: dict, body: str, wiki_root, catalog: dict) -> tuple[str, dict]:
    """Clé attendue de la fiche (ADR-131 D1) : texte publié, captures citées, empreinte du skill,
    et, en v2, domaines recalculés depuis le catalogue (D9). Une seule clé par fiche."""
    sr = _sibling("semantic_review")
    path = Path(wiki_root) / SKILL_RELPATH
    try:
        skill = path.read_bytes()
    except OSError as exc:
        raise sr.ReviewInputUnavailable(SKILL_RELPATH.as_posix()) from exc
    captures = sr.cited_captures(fm)
    key_inputs = {"text_sha256": sr._sha256_text(sr.published_text(fm, body)),
                  "captures": captures,
                  "skill_sha256": hashlib.sha256(skill).hexdigest(),
                  "domain_definition": DOMAIN_DEFINITION,
                  "domain_basis": DOMAIN_BASIS,
                  "capture_domains": capture_domains(captures, catalog, DOMAIN_DEFINITION)}
    return sr._sha256_text(sr._canonical_json(key_inputs)), key_inputs


def load_catalog(wiki_root) -> dict:
    sr = _sibling("semantic_review")
    import yaml
    try:
        return yaml.safe_load((Path(wiki_root) / CATALOG_RELPATH).read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise sr.ReviewInputUnavailable(CATALOG_RELPATH.as_posix()) from exc


def load_run_schema(wiki_root) -> dict:
    sr = _sibling("semantic_review")
    try:
        return json.loads((Path(wiki_root) / RUN_SCHEMA_RELPATH).read_text(encoding="utf-8"))
    except OSError as exc:
        raise sr.ReviewInputUnavailable(RUN_SCHEMA_RELPATH.as_posix()) from exc


class ArtifactInvalid(Exception):
    """Artefact illisible : nom, JSON, schéma, clé ou cohérence de la corroboration."""


def read_artifact(path: Path, schema: dict, key: str, key_inputs: dict) -> dict:
    """Artefact versionné : nom = sha256 de ses octets, conforme au schéma, de la clé de la fiche,
    `key_inputs` identiques à ceux recalculés, corroboration v2 cohérente (D9)."""
    from jsonschema import Draft202012Validator
    data = path.read_bytes()
    if path.name != f"{hashlib.sha256(data).hexdigest()}.json":
        raise ArtifactInvalid("nom différent de l'empreinte du fichier")
    try:
        run = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactInvalid(f"JSON illisible: {exc}") from exc
    errors = sorted(Draft202012Validator(schema).iter_errors(run), key=lambda e: list(e.absolute_path))
    if errors:
        raise ArtifactInvalid("schema: " + "; ".join(
            f"{'/'.join(map(str, e.absolute_path)) or '$'}: {e.message}" for e in errors[:5]))
    if run["key"] != key or path.parent.name != key:
        raise ArtifactInvalid("clé différente de celle de la fiche")
    if run["key_inputs"] != key_inputs:
        raise ArtifactInvalid("key_inputs différents de ceux recalculés (texte, captures, skill, domaines)")
    violations = corroboration_violations(run)
    if violations:
        raise ArtifactInvalid("corroboration incohérente: " + "; ".join(violations[:5]))
    return run


def fresh(run: dict) -> list[str]:
    """Preuve de fraîcheur (ADR-131 D7) : commit RAW consigné, garde passée si invoquée."""
    f = run.get("freshness") or {}
    out = []
    if not f.get("raw_commit"):
        out.append("freshness.raw_commit absent")
    if f.get("read_from") == "freshness_guard" and f.get("guard_exit") != 0:
        out.append(f"freshness.guard_exit={f.get('guard_exit')!r} (0 attendu)")
    return out


def independence(qualification: dict, contestation: dict) -> tuple[str | None, list[str]]:
    """Indépendance (ADR-131 D5) : (statut d'échec ou None, motifs)."""
    q_rev, q_prod = qualification["reviewer"], qualification["producer"]
    c_rev, contests = contestation["reviewer"], contestation["contests"]
    if q_prod["provider"] == "unknown":
        return "PRODUCER_UNKNOWN", [f"famille du producteur inconnue ({q_prod['basis']})"]
    out = []
    if c_rev["provider"] in (q_prod["provider"], q_rev["provider"]):
        out.append(f"contestataire {c_rev['provider']} de la famille du producteur "
                   f"({q_prod['provider']}) ou du 11 ({q_rev['provider']})")
    if (contests["reviewer_model"], contests["reviewer_provider"]) != (q_rev["model"], q_rev["provider"]):
        out.append("contests.reviewer_* ne désigne pas le relecteur de la qualification")
    return ("NOT_INDEPENDENT" if out else None), out


def evaluate_pair(qualification: dict, contestation: dict | None, expected_segments: list[dict],
                  floors: dict, domains: list[dict], capture_texts: dict) -> dict:
    """Statut d'une qualification, seule ou avec une contestation qui la désigne (ADR-131 D3, D4).

    Une affirmation bloque selon D4 avec le verdict le plus strict de la qualification (recalculé
    par `enforce`) et de la contestation. En profondeur `complete`, une position autre que `agree`
    bloque, comme `checks.independence` ou `checks.concordance` à `fails` sur un `conserver`
    (D9). Une affirmation n'est acquise que non bloquante et `agree`.
    """
    if qualification.get("error"):
        # Un artefact en erreur n'est ni PASS ni FAIL (D3) : la qualification se relance.
        return {"status": "ERROR", "blocking": [], "contested": [], "claims": 0,
                "notes": [f"qualification en erreur: {qualification['error']}"]}
    errored = []
    if contestation is not None and contestation.get("error"):
        errored = [f"contestation en erreur: {contestation['error']}"]
        contestation = None  # ses positions ne comptent pas ; la qualification seule peut échouer
    sr = _sibling("semantic_review")
    sources = {ref: sr._normalize(text) for ref, text in capture_texts.items()}

    def anchored(passage) -> bool:
        if not isinstance(passage, dict):
            return False
        quote = sr._normalize(passage["quote"])
        source = sources.get((passage["path"], passage["cid"]))
        return bool(quote) and source is not None and quote in source

    expected = {s["id"]: s["sha256"] for s in expected_segments}
    segs = {s["id"]: s for s in qualification["segments"]}
    incomplete, blocking, contested = [], [], []
    missing = [sid for sid in expected if sid not in segs]
    extra = sorted(sid for sid in segs if sid not in expected)
    changed = [sid for sid in expected if sid in segs and segs[sid].get("sha256") not in (None, expected[sid])]
    for label, ids in (("segments absents", missing), ("segments inconnus", extra),
                       ("segments d'empreinte différente", changed)):
        if ids:
            incomplete.append(f"{label}: {ids}")
    if any("positions" in s for s in qualification["segments"]):
        incomplete.append("qualification portant des positions")

    positions = {}
    if contestation is not None:
        for seg in contestation["segments"]:
            for pos in seg.get("positions") or []:
                positions.setdefault((seg["id"], pos["claim_id"]), []).append(pos)

    claims = []
    for sid, seg in segs.items():
        if sid not in expected:
            continue
        floor = floors.get(sid, ("complete", ["segment_inconnu"]))[0]
        depth = "complete" if "complete" in (floor, seg["depth"]) else "allegee"
        for claim in seg.get("claims") or []:
            cited = [p for p in claim.get("sources") or [] if anchored(p)]
            enforced = enforce({**claim, "sources": cited}, depth, domains)
            verdict, is_anchored = enforced["verdict"], bool(cited)
            # Un déclassement refait ici est du contrôle ; sinon l'attribution consignée reste vraie
            # (relancer enforce sur un claim déjà déclassé lirait `declassed_from` comme du modèle).
            declassed_by = enforced["corroboration"].get("declassed_by") if verdict != claim.get("verdict") \
                else (claim.get("corroboration") or {}).get("declassed_by")
            where = f"{sid} {claim['id']}"
            claims.append((sid, claim["id"]))
            if _blocks(verdict, depth, is_anchored):
                blocking.append({"where": where, "by": "qualification", "depth": depth,
                                 "verdict": verdict, "anchored": is_anchored, "declassed_by": declassed_by})
                continue
            if contestation is None:
                continue
            found = positions.get((sid, claim["id"]))
            if not found:
                incomplete.append(f"{where}: aucune position du contestataire")
                continue
            for pos in found:
                kind = pos["position"]
                checks = pos.get("checks") or {}
                if kind == "agree" and depth == "complete" and verdict == "conserver" and \
                        "fails" in (checks.get("independence"), checks.get("concordance")):
                    kind = "contest"
                if kind == "agree":
                    continue
                strict = _stricter(verdict, pos.get("verdict")) if kind == "contest" else verdict
                if depth == "complete" or _blocks(strict, depth, is_anchored):
                    blocking.append({"where": where, "by": "contestation", "depth": depth,
                                     "position": pos["position"], "verdict": strict})
                else:
                    contested.append({"where": where, "position": pos["position"], "verdict": strict})
    if contestation is not None:
        unknown = sorted(f"{s} {c}" for (s, c) in positions if (s, c) not in claims)
        if unknown:
            incomplete.append(f"positions sur des affirmations inconnues: {unknown}")
        for item in contestation.get("missed") or []:
            sid = item["segment_id"]
            depth = "complete" if sid not in segs else (
                "complete" if "complete" in (floors.get(sid, ("complete",))[0], segs[sid]["depth"])
                else "allegee")
            cited = [item["passage"]] if anchored(item["passage"]) else []
            enforced = enforce({"verdict": item["verdict"], "sources": cited}, depth, domains)
            if _blocks(enforced["verdict"], depth, bool(cited)):
                blocking.append({"where": f"{sid} missed", "by": "contestation", "depth": depth,
                                 "verdict": enforced["verdict"], "anchored": bool(cited)})
    if blocking:
        status = "FAIL"
    elif errored:
        status, incomplete = "ERROR", incomplete + errored
    elif contestation is None:
        status = "NO_CONTESTATION"
    else:
        status, why = independence(qualification, contestation)
        if status is None:
            stale = fresh(qualification) + fresh(contestation)
            if stale:
                status, why = "NO_FRESHNESS", stale
            elif incomplete:
                status = "INCOMPLETE"
            elif contested:
                status = "CONTESTED"
            else:
                status = "PASS"
        if why:
            incomplete = incomplete + why
    return {"status": status, "blocking": blocking, "contested": contested, "notes": incomplete,
            "claims": len(claims)}


def qualification_status(wiki_root, slug, fm: dict, body: str, raw_root) -> dict:
    """État de la condition `technical_qualification_pass` (ADR-131 D3) pour la fiche (`fm` =
    frontmatter publié). Statuts, du plus fort au plus faible : FAIL, HISTORY_GAP, UNREADABLE,
    CONTESTED, PASS, PRODUCER_UNKNOWN, NOT_INDEPENDENT, NO_FRESHNESS, INCOMPLETE, NO_CONTESTATION,
    ERROR, STALE (artefacts d'une autre clé seulement), ABSENT ; NO_CAPTURE si la fiche ne cite
    aucune capture RAW. `pass` n'est vrai que sur PASS. Lève `ReviewInputUnavailable` (infra) ou
    ValueError (référence ou slug invalide) : l'appelant en fait un statut."""
    sr = _sibling("semantic_review")
    wiki_root = Path(wiki_root)
    slug = sr._check_slug(slug)
    catalog = load_catalog(wiki_root)
    key, key_inputs = expected_key(fm, body, wiki_root, catalog)
    result = {"key": key, "status": None, "pass": False, "pairs": [], "unreadable": [],
              "history_gaps": [], "floors": {}, "skill_sha256": key_inputs["skill_sha256"]}
    expected = sr.segments(fm, body)
    floors = depth_floors(fm, expected)
    result["floors"] = {sid: {"depth": d, "reasons": r} for sid, (d, r) in floors.items() if d == "complete"}
    if not key_inputs["captures"]:
        result["status"] = "NO_CAPTURE"
        return result
    capture_texts = sr.load_captures(key_inputs["captures"], raw_root)
    schema = load_run_schema(wiki_root)
    slug_dir = wiki_root / QUALIFICATION_DIR / slug
    key_dir = slug_dir / key
    result["history_gaps"] = sr._history_gaps(wiki_root, key_dir)
    qualifications, contestations = {}, []
    if key_dir.is_dir():
        for path in sorted(key_dir.iterdir()):
            try:
                if not path.is_file():
                    raise ArtifactInvalid("fichier hors convention <sha256>.json")
                run = read_artifact(path, schema, key, key_inputs)
            except (OSError, ArtifactInvalid) as exc:
                result["unreadable"].append({"file": path.name, "error": str(exc)})
                continue
            if run["role"] == "qualification":
                qualifications[path.stem] = run
            else:
                contestations.append((path.stem, run))
    domains = key_inputs["capture_domains"]
    for sha, run in contestations:
        if run["contests"]["artifact_sha256"] not in qualifications:
            result["unreadable"].append({"file": f"{sha}.json",
                                         "error": "contestation d'une qualification absente de la clé"})
    for q_sha, q_run in qualifications.items():
        mine = [(c_sha, c) for c_sha, c in contestations if c["contests"]["artifact_sha256"] == q_sha]
        for c_sha, c_run in mine or [(None, None)]:
            pair = evaluate_pair(q_run, c_run, expected, floors, domains, capture_texts)
            result["pairs"].append({"qualification": f"{q_sha}.json",
                                    "contestation": f"{c_sha}.json" if c_sha else None, **pair})
    found = {p["status"] for p in result["pairs"]}
    if "FAIL" in found:
        status = "FAIL"
    elif result["history_gaps"]:
        status = "HISTORY_GAP"
    elif result["unreadable"]:
        status = "UNREADABLE"
    else:
        status = next((s for s in STATUS_ORDER[3:] if s in found), None)
        if status is None:
            status = "STALE" if slug_dir.is_dir() and any(p.name != key for p in slug_dir.iterdir()) \
                else "ABSENT"
    result["status"] = status
    result["pass"] = status == "PASS"
    return result
