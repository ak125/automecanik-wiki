#!/usr/bin/env python3
"""Banc d'étalonnage du skill qualification-technique (ADR-131, candidat ; mandat AC, point 5).

Rend reproductible le banc du 2026-11-15 (mandat S, script hors dépôt `tq_run.py`) :

- `packet`   : paquet d'un cas (segments, plancher de profondeur, lots, domaines, clé), sans appel ;
- `qualify`  : relecture de qualification, N passages, artefacts technical-qualification/v2 ;
- `contest`  : relecture de contestation d'un artefact de qualification ;
- `variance` : verdicts retrouvés et dispersion, contre les verdicts attendus d'un jeu de référence.

Le banc ne décide rien et n'est branché nulle part : il assemble le paquet avec
`semantic_review.build_packet`, appelle le relecteur avec `semantic_review_executor.ask`
(processus neuf, répertoire vide), applique `technical_qualification.enforce`, valide l'artefact
contre `_meta/schema/technical-qualification-run.schema.json` et l'écrit sous
`OUT/<slug>/run-NN/<clé>/<sha256>.json`. Aucun seuil (ADR-131 D6).

Domaines (ADR-131 D9) : `--domains TABLE.yaml` fusionne en mémoire une table
`captures: [{cid, publisher, type, publisher_class}]` sur `_meta/source-catalog.yaml`, tant que
la classe d'éditeur n'est pas dans le catalogue. La fusion et les empreintes des deux fichiers
sont consignées dans `key_inputs.domain_basis`.

Cas (YAML ou JSON) : {"slug", "fm", "body", "subject", "freshness", "producer"} ; `--raw-root` est un
extrait RAW au commit `freshness.raw_commit` (les octets sont vérifiés contre chaque `cid`).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shlex
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numeric_exactitude as ne  # noqa: E402
import safety_families as sf  # noqa: E402
import semantic_review as sr  # noqa: E402
import semantic_review_executor as ex  # noqa: E402
import technical_qualification as tq  # noqa: E402

WIKI = Path(__file__).resolve().parent.parent
SKILL = WIKI / "_meta/skills/qualification-technique/SKILL.md"
SCHEMA = WIKI / "_meta/schema/technical-qualification-run.schema.json"
CATALOG = WIKI / "_meta/source-catalog.yaml"

VERDICTS = ("conserver", "preciser", "reformuler", "retirer")
SEVERITY = {v: i for i, v in enumerate(VERDICTS)}
DEPTH_REASONS = ("safety_family", "numeric_value", "procedure", "diagnostic_relation", "escalated", "doubt")
PROCEDURE_HEADINGS = ("## Montage", "## Entretien")
DIAGNOSTIC_HEADINGS = ("## Symptômes",)
PROCEDURE_KEYS = ("replacement_guidance", "maintenance_interval", "maintenance")
DIAGNOSTIC_KEYS = ("failure_symptoms",)
_ZERO_CID = "sha256:" + "0" * 64


# --- Paquet ---------------------------------------------------------------------------------

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _contains_key(value, keys) -> bool:
    if isinstance(value, dict):
        return any(k in keys or _contains_key(v, keys) for k, v in value.items())
    if isinstance(value, list):
        return any(_contains_key(v, keys) for v in value)
    return False


def floors(fm: dict, segments: list[dict]) -> dict:
    """Plancher de profondeur de chaque segment (SKILL §5) et ses motifs."""
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
                field is not None and (field in PROCEDURE_KEYS or _contains_key(fm.get(field), PROCEDURE_KEYS))):
            reasons.append("procedure")
        if (field is None and heading and heading.startswith(DIAGNOSTIC_HEADINGS)) or \
                field == "diagnostic_relations" or \
                (field is not None and _contains_key(fm.get(field), DIAGNOSTIC_KEYS)):
            reasons.append("diagnostic_relation")
        out[sid] = ("complete" if reasons else "allegee", reasons)
    return out


def shard(segments: list[dict], limit: int) -> list[list[dict]]:
    """Lots de segments consécutifs dont le texte cumulé reste sous `limit` caractères (un segment
    plus long forme son propre lot). Déterministe : même entrée, mêmes lots."""
    groups, current, size = [], [], 0
    for seg in segments:
        n = len(seg["text"])
        if current and size + n > limit:
            groups.append(current)
            current, size = [], 0
        current.append(seg)
        size += n
    if current:
        groups.append(current)
    return groups


def invite(skill_text: str, name: str) -> str:
    match = re.search(rf"<!-- invite:{name} -->\n(.*?)<!-- /invite -->", skill_text, re.S)
    if not match:
        raise ValueError(f"invite {name} absente du skill")
    return match.group(1)


def anchored(passage, captures: dict) -> bool:
    """La citation est-elle dans le texte normalisé de la capture citée (chemin et cid) ?"""
    if not isinstance(passage, dict):
        return False
    text = captures.get((passage.get("path"), passage.get("cid")))
    quote = passage.get("quote")
    return bool(text and isinstance(quote, str) and quote.strip()
                and sr._normalize(quote) in sr._normalize(text))


def merge_domains(catalog: dict, table: dict | None) -> dict:
    """Catalogue + table de domaines, en mémoire. Une entrée existante reçoit `publisher_class` ;
    une capture absente du catalogue reçoit une entrée minimale (publisher, type, classe)."""
    merged = copy.deepcopy(catalog)
    if not table:
        return merged
    sources = merged.setdefault("sources", [])
    by_cid = {(e.get("raw_ref") or {}).get("expected_sha256"): e for e in sources}
    for row in table.get("captures") or []:
        entry = by_cid.get(row["cid"])
        if entry is None:
            entry = {"slug": "domain-table-" + row["cid"][7:19], "type": row.get("type"),
                     "publisher": row.get("publisher"), "raw_ref": {"expected_sha256": row["cid"]}}
            sources.append(entry)
            by_cid[row["cid"]] = entry
        entry["publisher_class"] = row.get("publisher_class")
    return merged


def load_case(path: Path) -> dict:
    case = yaml.safe_load(path.read_text(encoding="utf-8"))
    for field in ("slug", "fm", "body", "subject", "freshness", "producer"):
        if field not in case:
            raise ValueError(f"{path}: champ {field} absent")
    return case


def prepare(case: dict, raw_root: Path, catalog_path: Path, table_path: Path | None,
            definition: str, shard_chars: int) -> dict:
    """Tout ce qui précède l'appel au relecteur, sans réseau ni modèle."""
    packet = sr.build_packet(case["fm"], case["body"], raw_root)
    catalog_bytes = catalog_path.read_bytes()
    catalog = yaml.safe_load(catalog_bytes)
    table, basis = None, f"{catalog_path.name} sha256 {_sha256_bytes(catalog_bytes)}"
    if table_path is not None:
        table_bytes = table_path.read_bytes()
        table = yaml.safe_load(table_bytes)
        basis += f" + table {table_path.name} sha256 {_sha256_bytes(table_bytes)} fusionnée en mémoire"
    catalog = merge_domains(catalog, table)
    urls = {}
    for cap in packet["captures"]:
        found = re.search(r"^source_url: *(.+)$", cap["text"], re.M)
        urls[cap["cid"]] = found.group(1).strip().strip("'\"") if found else None
    domains = tq.capture_domains([{"path": c["path"], "cid": c["cid"], "source_url": urls.get(c["cid"])}
                                  for c in packet["key_inputs"]["captures"]], catalog, definition)
    skill_bytes = SKILL.read_bytes()
    key_inputs = {"text_sha256": packet["key_inputs"]["text_sha256"],
                  "captures": packet["key_inputs"]["captures"],
                  "skill_sha256": _sha256_bytes(skill_bytes),
                  "domain_definition": definition, "domain_basis": basis,
                  "capture_domains": domains}
    floor = floors(case["fm"], packet["segments"])
    segs = [{"id": s["id"], "text": s["text"], "depth_floor": floor[s["id"]][0],
             "depth_floor_reasons": floor[s["id"]][1]} for s in packet["segments"]]
    by_cid = {d["cid"]: d for d in domains}
    captures = [{"path": c["path"], "cid": c["cid"], "publisher": by_cid[c["cid"]]["publisher"],
                 "domain": by_cid[c["cid"]]["domain"], "editorial_role": by_cid[c["cid"]]["editorial_role"],
                 "text": c["text"]} for c in packet["captures"]]
    groups = shard(segs, shard_chars)
    return {"key": sr._sha256_text(sr._canonical_json(key_inputs)), "key_inputs": key_inputs,
            "segments": segs, "seg_sha": {s["id"]: s["sha256"] for s in packet["segments"]},
            "captures": captures, "texts": {(c["path"], c["cid"]): c["text"] for c in captures},
            "groups": groups, "skill_text": skill_bytes.decode("utf-8")}


def prompts(prep: dict, role: str, qualification: dict | None = None) -> list[str]:
    """Invites de chaque lot, dans l'ordre des lots."""
    head = invite(prep["skill_text"], role)
    out = []
    for group in prep["groups"]:
        packet = {"segments": group, "captures": prep["captures"]}
        if role == "contestation":
            qsegs = {s["id"]: s for s in qualification["segments"]}
            packet["qualification"] = [qsegs[s["id"]] for s in group if s["id"] in qsegs]
        out.append(head + json.dumps(packet, ensure_ascii=False))
    return out


# --- Artefacts ------------------------------------------------------------------------------

def write_artifact(out: Path, slug: str, art: dict) -> tuple[Path, str]:
    """Valide puis écrit l'artefact sous `OUT/<slug>/run-NN/<clé>/<sha256>.json`. Chaque passage a son
    répertoire : deux passages aux réponses identiques donnent deux artefacts, comptés deux fois. Le
    parent immédiat reste la clé, comme le dépôt l'exige (`test_deposited_artifacts_conform`)."""
    import jsonschema
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(art)
    data = (json.dumps(art, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    digest = _sha256_bytes(data)
    runs = 0
    while (out / slug / f"run-{runs:02d}" / art["key"]).exists():
        runs += 1
    target = out / slug / f"run-{runs:02d}" / art["key"] / f"{digest}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target, digest


def _call_all(command, model, texts, timeout, jobs):
    with ThreadPoolExecutor(max(1, jobs)) as pool:
        futures = [pool.submit(ex.ask, command, model, text, timeout) for text in texts]
    results = []
    for future in futures:
        try:
            results.append((future.result(), None))
        except Exception as exc:  # noqa: BLE001 — l'erreur est consignée dans l'artefact
            results.append((None, f"{type(exc).__name__}: {exc}"))
    return results


def _sources(raw: list) -> list[dict]:
    return [{"path": x.get("path") or "?", "cid": x.get("cid") or _ZERO_CID, "quote": x.get("quote") or "?"}
            for x in raw if isinstance(x, dict)]


def qualify(prep: dict, answers: list, errors: list, notes: list) -> list[dict]:
    """Segments de l'artefact de qualification depuis les réponses des lots."""
    by_id = {}
    for (answer, error), group in zip(answers, prep["groups"]):
        if error:
            errors.append(f"lot {group[0]['id']}..{group[-1]['id']}: {error}")
            continue
        for seg in answer.get("segments") or []:
            if isinstance(seg, dict):
                by_id[seg.get("id")] = seg
    out, n = [], 0
    domains = prep["key_inputs"]["capture_domains"]
    for seg in prep["segments"]:
        answer = by_id.get(seg["id"])
        if answer is None:
            errors.append(f"segment absent de la réponse: {seg['id']}")
            continue
        floor, reasons = seg["depth_floor"], seg["depth_floor_reasons"]
        depth = answer.get("depth") if answer.get("depth") in ("complete", "allegee") else floor
        if floor == "complete" and depth == "allegee":
            notes.append(f"profondeur relevée au plancher: {seg['id']}")
            depth = "complete"
        given = [r for r in answer.get("depth_reasons") or [] if r in DEPTH_REASONS]
        row = {"id": seg["id"], "sha256": prep["seg_sha"][seg["id"]], "depth_floor": floor, "depth": depth,
               "depth_reasons": list(dict.fromkeys(reasons + given))}
        claims = answer.get("claims") or []
        if answer.get("no_claims") or not claims:
            row["no_claims"] = True
            out.append(row)
            continue
        row["claims"] = []
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            sources = _sources(claim.get("sources") or [])
            for src in sources:
                if not anchored(src, prep["texts"]):
                    notes.append(f"passage non ancré: {seg['id']} c{n}: {src['quote'][:80]}")
            corroboration = claim.get("corroboration")
            if not isinstance(corroboration, dict):
                notes.append(f"corroboration absente de la réponse: {seg['id']} c{n}")
                corroboration = {}
            verdict = claim.get("verdict")
            if verdict not in VERDICTS:
                notes.append(f"verdict hors contrat ({verdict!r}) lu comme retirer: {seg['id']} c{n}")
                verdict = "retirer"
            item = {"id": f"c{n}", "text": claim.get("text") or "?", "verdict": verdict, "sources": sources,
                    "portee": claim.get("portee") or "?", "limite": claim.get("limite") or "?",
                    "proposed_wording": claim.get("proposed_wording"), "corroboration": corroboration,
                    "retake_question": claim.get("retake_question")
                    if isinstance(claim.get("retake_question"), str) else None}
            row["claims"].append(tq.enforce(item, depth, domains))
            n += 1
        out.append(row)
    return out


def contest(prep: dict, qualification: dict, answers: list, errors: list, notes: list) -> tuple[list, list]:
    qsegs = {s["id"]: s for s in qualification["segments"]}
    out, missed = [], []
    for (answer, error), group in zip(answers, prep["groups"]):
        if error:
            errors.append(f"lot {group[0]['id']}..{group[-1]['id']}: {error}")
            continue
        for seg in answer.get("segments") or []:
            sid = seg.get("id") if isinstance(seg, dict) else None
            if sid not in qsegs or not seg.get("positions"):
                continue
            positions = []
            for x in seg["positions"]:
                if not isinstance(x, dict) or x.get("position") not in ("agree", "contest", "undecidable"):
                    continue
                item = {"claim_id": x.get("claim_id") or "c0", "position": x["position"],
                        "statement": x.get("statement") or "?", "passage": None}
                if x.get("verdict") in VERDICTS:
                    item["verdict"] = x["verdict"]
                checks = x.get("checks")
                if isinstance(checks, dict) and checks.get("concordance") in ("holds", "fails", "undecidable") \
                        and checks.get("independence") in ("holds", "fails", "undecidable"):
                    item["checks"] = {"concordance": checks["concordance"], "independence": checks["independence"]}
                if isinstance(x.get("passage"), dict):
                    if not anchored(x["passage"], prep["texts"]):
                        notes.append(f"passage non ancré: {sid} {item['claim_id']}")
                    item["passage"] = {k: x["passage"].get(k) or "?" for k in ("path", "cid", "quote")}
                positions.append(item)
            if positions:
                q = qsegs[sid]
                out.append({"id": sid, "sha256": prep["seg_sha"][sid], "depth_floor": q["depth_floor"],
                            "depth": q["depth"], "depth_reasons": q.get("depth_reasons", []),
                            "positions": positions})
        for m in answer.get("missed") or []:
            if isinstance(m, dict) and m.get("segment_id") in prep["seg_sha"]:
                item = {"segment_id": m["segment_id"], "text": m.get("text") or "?",
                        "verdict": m.get("verdict") if m.get("verdict") in VERDICTS else "retirer",
                        "statement": m.get("statement") or "?", "passage": None}
                if isinstance(m.get("passage"), dict):
                    item["passage"] = {k: m["passage"].get(k) or "?" for k in ("path", "cid", "quote")}
                missed.append(item)
    return out, missed


def run_once(case: dict, prep: dict, role: str, reviewer: dict, command: list[str], timeout: float,
             jobs: int, qualification_path: Path | None = None) -> tuple[dict, list]:
    art = {"schema_version": "technical-qualification/v2", "key": prep["key"], "key_inputs": prep["key_inputs"],
           "subject": case["subject"], "freshness": case["freshness"], "reviewer": reviewer,
           "producer": case["producer"], "role": role}
    errors, notes = [], []
    if role == "qualification":
        answers = _call_all(command, reviewer["model"], prompts(prep, role), timeout, jobs)
        art["segments"] = qualify(prep, answers, errors, notes)
        art["retake_questions"] = tq.retake_questions(art)
        violations = tq.corroboration_violations(art)
        if violations:
            raise RuntimeError("contrôle de corroboration: " + "; ".join(violations))
    else:
        qbytes = qualification_path.read_bytes()
        q = json.loads(qbytes)
        art["contests"] = {"artifact_sha256": _sha256_bytes(qbytes), "reviewer_model": q["reviewer"]["model"],
                           "reviewer_provider": q["reviewer"]["provider"]}
        answers = _call_all(command, reviewer["model"], prompts(prep, role, q), timeout, jobs)
        art["segments"], art["missed"] = contest(prep, q, answers, errors, notes)
    if errors:
        art["error"] = "; ".join(errors)
    return art, notes


# --- Variance -------------------------------------------------------------------------------

def observe(artifact: dict, target: dict) -> dict:
    """Verdict observé d'une cible dans un artefact : le plus sévère des verdicts des affirmations
    de son segment qui correspondent à `match` sans correspondre à `exclude`."""
    seg = next((s for s in artifact.get("segments") or [] if s["id"] == target["segment"]), None)
    if seg is None:
        return {"verdict": "segment_absent", "claims": []}
    match = re.compile(target["match"], re.I)
    exclude = re.compile(target["exclude"], re.I) if target.get("exclude") else None
    hits = [c for c in seg.get("claims") or []
            if match.search(c["text"]) and not (exclude and exclude.search(c["text"]))]
    if not hits:
        return {"verdict": "absent", "depth": seg.get("depth"), "claims": []}
    worst = max(hits, key=lambda c: SEVERITY[c["verdict"]])
    return {"verdict": worst["verdict"], "depth": seg.get("depth"),
            "claims": [{"id": c["id"], "verdict": c["verdict"], "text": c["text"],
                        "concordance": c["corroboration"].get("concordance"),
                        "discordance_on": c["corroboration"].get("discordance_on"),
                        "domains": c["corroboration"].get("domains"),
                        "proof": c["corroboration"].get("proof"),
                        "declassed_by": c["corroboration"].get("declassed_by"),
                        "declassed_from": c["corroboration"].get("declassed_from")} for c in hits]}


LIMIT_SIGNAL = re.compile(r"contradi|discord|contredi|omet|omission|n.est pas port|ne porte pas|non port", re.I)


def variance(expected: dict, artifacts: list[tuple[str, dict]], raw_root: Path | None = None) -> dict:
    """Part retrouvée, part défendable et dispersion par cible ; aucun seuil (ADR-131 D6).

    Signale aussi, sans rien conclure : passages non ancrés (si `raw_root`), et `conserver` dont la
    limite ou la portée décrit une contradiction ou une omission (SKILL §4, hors méthode).
    """
    by_case: dict[str, list] = {}
    for name, art in artifacts:
        if art.get("role") == "qualification":
            by_case.setdefault(art["subject"]["slug"], []).append((name, art))
    rows = []
    for target in expected["targets"]:
        runs = [(name, observe(art, target)) for name, art in sorted(by_case.get(target["case"], []))]
        verdicts = [o["verdict"] for _, o in runs]
        n = len(verdicts)
        modal = max((verdicts.count(v) for v in set(verdicts)), default=0)
        accepted = {target["expected"], *target.get("defensible", [])}
        rows.append({"id": target["id"], "case": target["case"], "segment": target["segment"],
                     "expected": target["expected"], "defensible": target.get("defensible", []),
                     "runs": n, "verdicts": verdicts,
                     "recovered": (verdicts.count(target["expected"]) / n) if n else None,
                     "defensible_share": (sum(v in accepted for v in verdicts) / n) if n else None,
                     "distinct": len(set(verdicts)), "modal_share": (modal / n) if n else None,
                     "observations": [{"artifact": name, **o} for name, o in runs]})
    signals, anchoring = [], {"quotes": 0, "anchored": 0, "unanchored": []}
    reviewers = set()
    for name, art in artifacts:
        reviewers.add((art["reviewer"]["model"], art["reviewer"]["provider"], art["reviewer"].get("cli_version")))
        texts = None
        if raw_root is not None:
            texts = sr.load_captures(art["key_inputs"]["captures"], raw_root)
        for seg in art.get("segments") or []:
            for claim in seg.get("claims") or []:
                if claim["verdict"] == "conserver" and LIMIT_SIGNAL.search(
                        f"{claim.get('limite', '')} {claim.get('portee', '')}"):
                    signals.append({"artifact": name, "segment": seg["id"], "claim": claim["id"],
                                    "limite": claim.get("limite")})
                if texts is not None:
                    for src in claim.get("sources") or []:
                        anchoring["quotes"] += 1
                        if anchored(src, texts):
                            anchoring["anchored"] += 1
                        else:
                            anchoring["unanchored"].append(f"{name} {seg['id']} {claim['id']}")
    scored = [r for r in rows if r["runs"]]
    total = sum(r["runs"] for r in scored)
    hits = sum(r["verdicts"].count(r["expected"]) for r in scored)
    accepted = sum(r["defensible_share"] * r["runs"] for r in scored)
    keys = ("model", "provider", "cli_version")
    return {"targets": rows,
            "summary": {"targets": len(rows), "observations": total,
                        "recovered": hits / total if total else None,
                        "defensible_share": accepted / total if total else None,
                        "stable_targets": sum(1 for r in scored if r["distinct"] == 1),
                        "reviewers": [dict(zip(keys, r)) for r in sorted(reviewers, key=str)],
                        "artifacts_with_error": [name for name, art in artifacts if art.get("error")]},
            "conserver_limit_signals": signals,
            "anchoring": anchoring if raw_root is not None else None}


def _pct(x) -> str:
    return "—" if x is None else f"{round(100 * x)} %"


def markdown(report: dict) -> str:
    lines = ["| Cible | Attendu | Défendable | Verdicts observés | Retrouvé | Défendable (part) | Distincts |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in report["targets"]:
        lines.append(f"| `{r['id']}` | {r['expected']} | {', '.join(r['defensible']) or '—'} | "
                     f"{', '.join(r['verdicts']) or '—'} | {_pct(r['recovered'])} | {_pct(r['defensible_share'])} | "
                     f"{r['distinct']} |")
    return "\n".join(lines) + "\n"


# --- Interface ------------------------------------------------------------------------------

def _reviewer(args) -> dict:
    reviewer = {"model": args.model, "provider": args.provider}
    if args.cli_version:
        reviewer["cli_version"] = args.cli_version
    return reviewer


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("packet", "qualify", "contest"):
        p = sub.add_parser(mode)
        p.add_argument("case", type=Path)
        if mode == "contest":
            p.add_argument("qualification", type=Path)
        p.add_argument("--raw-root", type=Path, required=True)
        p.add_argument("--catalog", type=Path, default=CATALOG)
        p.add_argument("--domains", type=Path)
        p.add_argument("--domain-definition", default="publisher_class", choices=tq.DEFINITIONS)
        p.add_argument("--shard-chars", type=int, default=5000)
        if mode != "packet":
            p.add_argument("--model", required=True)
            p.add_argument("--provider", required=True, choices=("anthropic", "openai"))
            p.add_argument("--command", required=True, help="commande du relecteur ; {model} est substitué")
            p.add_argument("--cli-version")
            p.add_argument("--out", type=Path, required=True)
            p.add_argument("--runs", type=int, default=1)
            p.add_argument("--timeout", type=float, default=1500)
            p.add_argument("--jobs", type=int, default=3)
    v = sub.add_parser("variance")
    v.add_argument("expected", type=Path, help="verdicts attendus du jeu de référence (YAML ou JSON)")
    v.add_argument("artifacts", type=Path, nargs="+", help="artefacts ou répertoires (récursif)")
    v.add_argument("--raw-root", type=Path)
    v.add_argument("--markdown", action="store_true")
    args = parser.parse_args(argv)

    if args.mode == "variance":
        files = []
        for path in args.artifacts:
            files += sorted(path.rglob("*.json")) if path.is_dir() else [path]
        arts = [(str(f), json.loads(f.read_text(encoding="utf-8"))) for f in files]
        report = variance(yaml.safe_load(args.expected.read_text(encoding="utf-8")), arts, args.raw_root)
        print(markdown(report) if args.markdown else json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    case = load_case(args.case)
    prep = prepare(case, args.raw_root, args.catalog, args.domains, args.domain_definition, args.shard_chars)
    if args.mode == "packet":
        texts = prompts(prep, "qualification")
        print(json.dumps({"key": prep["key"], "key_inputs": prep["key_inputs"],
                          "lots": [[s["id"] for s in g] for g in prep["groups"]],
                          "prompt_sha256": [sr._sha256_text(t) for t in texts],
                          "segments": prep["segments"]}, ensure_ascii=False, indent=2))
        return 0
    role = "qualification" if args.mode == "qualify" else "contestation"
    command = shlex.split(args.command)
    results = []
    for _ in range(args.runs):
        art, notes = run_once(case, prep, role, _reviewer(args), command, args.timeout, args.jobs,
                              getattr(args, "qualification", None))
        target, digest = write_artifact(args.out, case["slug"], art)
        results.append({"artifact": str(target), "sha256": digest, "error": art.get("error"), "notes": notes})
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
