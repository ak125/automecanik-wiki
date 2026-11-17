"""Corroboration par un second domaine d'autorité — qualification technique v2 (ADR-131, candidat).

Candidat non câblé : aucun code de promotion n'importe ce module. Il calcule hors du modèle, depuis
les métadonnées des captures (`_meta/source-catalog.yaml`), le domaine d'autorité de chaque capture,
puis applique et contrôle la règle de corroboration du skill qualification-technique 0.3.0 :

- en profondeur `complete`, `conserver` exige une capture de rôle `proof` et au moins deux domaines
  distincts parmi les sources de l'affirmation, concordantes ;
- une seule source (un seul domaine) : `preciser`, portée bornée à cette source ;
- discordance entre domaines : `retirer` si l'écart touche une valeur, une procédure ou la sécurité,
  sinon `preciser` ;
- profondeur `allegee` : règle inchangée (la corroboration est consignée, rien n'est déclassé).

Une capture absente du catalogue, ou sans la métadonnée que la définition demande, n'a pas de
domaine : elle ne compte pour aucun (fail-closed).
"""
from __future__ import annotations

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
