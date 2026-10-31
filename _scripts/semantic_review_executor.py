#!/usr/bin/env python3
"""
semantic_review_executor — exécuteur du protocole d'auto-review de sens (ADR-119 D2).

Il lance chaque passe de détection et chaque réfutateur dans un processus neuf, par une commande
fournie à l'appel, lancé dans un répertoire vide : le relecteur ne reçoit sur stdin que son
invite et le paquet de `semantic_review.py` (texte publié découpé, captures RAW citées), jamais
la proposition de travail ni la sortie d'un autre relecteur. Il assemble l'exécution, la valide
et la dépose sous `_audit/semantic-review/` (`semantic_review.record_run`), FAIL compris. Il ne
rend aucun verdict : `promotion_decision.py` le recalcule. Le commit de l'exécution reste à faire
par PR WIKI ; non versionnée, elle met la condition D3 en HISTORY_GAP.

Une passe ou un réfutateur en échec (code non nul, délai dépassé, réponse hors contrat) n'est pas
consigné et l'exécution porte `error` : la relecture se relance. Une erreur d'exécution ne
confirme ni n'écarte jamais un candidat.

La commande est une liste d'arguments où `{model}` est remplacé par l'identifiant du modèle ; elle
lit l'invite sur stdin et écrit la réponse sur stdout. Aucune commande ni aucun modèle par défaut.
Protocole et usage : `_meta/semantic-review.md`.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import semantic_review as sr  # noqa: E402

# Invites remises aux relecteurs. Les modifier = PR WIKI ; les exécutions déjà versionnées gardent
# leur verdict.
DETECTION_PROMPT = """Relecture de sens — passe de détection (ADR-119 D2)

Tu relis le texte publié d'une fiche technique automobile. Tu ne disposes que du paquet JSON
ci-dessous : les segments du texte publié et les captures RAW que la fiche cite. N'utilise aucune
autre source.

Pour chaque segment du paquet, sans en omettre aucun :
- relève toutes ses affirmations (kind "affirmation"), valeurs, unités, conditions et précautions
  comprises ;
- relève comme affirmation de kind "omission" toute condition, précaution ou cause qu'une capture
  citée rattache au même sujet et que le segment laisse de côté ;
- ou déclare qu'il n'en porte aucune ("no_claims": true).

Relève ensuite comme écart candidat toute affirmation qu'aucune capture citée ne porte, toute
affirmation contredite, déformée ou sur-généralisée par une capture, toute omission, et toute
divergence entre captures que le texte ne déclare pas. Classe chaque candidat :
- "valeur" : chiffre, unité, intervalle ou quantité ;
- "securite" : écart qui peut conduire à une action ou à une omission dangereuse ;
- "sens" : affirmation contredite, déformée, sur-généralisée ou non portée, divergence non
  déclarée ;
- "formulation" : écart sans effet sur le sens.
Dans le doute, relève le candidat : un candidat injustifié sera écarté par la réfutation, un écart
manqué ne le sera jamais.

Réponds uniquement par un objet JSON, sans autre texte :
{"segments": [{"id": "<id>", "claims": [{"text": "...", "kind": "affirmation"}]},
              {"id": "<id>", "no_claims": true}],
 "candidates": [{"class": "securite", "segment_id": "<id>", "claims": [0], "statement": "..."}]}
`claims` d'un candidat : indices, à partir de 0, des affirmations de son segment qu'il vise.

Paquet :
"""

REFUTATION_PROMPT = """Relecture de sens — réfutation (ADR-119 D2)

Un écart candidat a été relevé dans le texte publié d'une fiche technique automobile. Tu ne
disposes que du paquet JSON ci-dessous : l'écart, le segment qu'il vise et les captures RAW que
la fiche cite. N'utilise aucune autre source : ta connaissance propre ne peut pas écarter un
candidat.

- "refuted" : le candidat n'est pas un écart ; cite le passage d'une capture qui le montre ;
- "upheld" : une capture confirme l'écart ; cite le passage ;
- "undecidable" : aucune capture ne tranche ; "passage": null.
Le passage est recopié à l'identique depuis la capture, avec son "path" et son "cid".

Réponds uniquement par un objet JSON, sans autre texte :
{"verdict": "refuted", "passage": {"path": "...", "cid": "sha256:...", "quote": "..."}}

Paquet :
"""

VERDICTS = ("refuted", "upheld", "undecidable")
_FENCE = re.compile(r"\A```(?:json)?\n(.*)\n```\Z", re.S)


class ReviewerFailed(Exception):
    """Passe ou réfutateur sans réponse exploitable : code non nul, délai dépassé, réponse hors
    contrat. Son vote n'est pas consigné."""


def _require(condition, message: str) -> None:
    if not condition:
        raise ReviewerFailed(f"réponse hors contrat: {message}")


def ask(command: list[str], model: str, prompt: str, timeout) -> dict:
    """Une invite dans un processus neuf, lancé dans un répertoire vide. Réponse : un objet JSON,
    seul ou dans un unique bloc ```json."""
    argv = [arg.replace("{model}", model) for arg in command]
    with tempfile.TemporaryDirectory(prefix="semantic-review-") as cwd:
        try:
            done = subprocess.run(argv, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", cwd=cwd, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ReviewerFailed(f"{type(exc).__name__}: {exc}") from exc
    if done.returncode != 0:
        raise ReviewerFailed(f"code {done.returncode}: {done.stderr.strip()[-300:]}")
    text = done.stdout.strip()
    fenced = _FENCE.match(text)
    try:
        answer = json.loads(fenced.group(1) if fenced else text)
    except json.JSONDecodeError as exc:
        raise ReviewerFailed(f"réponse illisible: {exc}") from exc
    _require(isinstance(answer, dict), "objet JSON attendu")
    return answer


def parse_detection(answer: dict, segment_ids: set) -> tuple[dict, list]:
    """Segments couverts par la passe (avec leurs affirmations) et ses candidats. Une entrée hors
    contrat rejette toute la passe."""
    entries, candidates = answer.get("segments"), answer.get("candidates")
    _require(isinstance(entries, list) and isinstance(candidates, list), "segments et candidates attendus")
    covered: dict[str, list] = {}
    for entry in entries:
        _require(isinstance(entry, dict) and entry.get("id") in segment_ids, "segment inconnu")
        _require(entry["id"] not in covered, f"segment {entry['id']} répété")
        claims = entry.get("claims")
        if entry.get("no_claims") is True:
            _require(not claims, f"segment {entry['id']}: no_claims et affirmations à la fois")
            covered[entry["id"]] = []
            continue
        _require(isinstance(claims, list) and claims and all(
            isinstance(c, dict) and isinstance(c.get("text"), str) and c["text"].strip()
            and c.get("kind") in ("affirmation", "omission") for c in claims),
            f"segment {entry['id']}: affirmations ou no_claims attendus")
        covered[entry["id"]] = [{"text": c["text"], "kind": c["kind"]} for c in claims]
    found = []
    for c in candidates:
        _require(isinstance(c, dict) and c.get("class") in sr.PROTOCOL["classes"], "classe inconnue")
        _require(c.get("segment_id") in covered, "candidat hors des segments couverts")
        _require(isinstance(c.get("statement"), str) and c["statement"].strip(), "énoncé vide")
        indexes = c.get("claims", [])
        _require(isinstance(indexes, list) and all(
            type(i) is int and 0 <= i < len(covered[c["segment_id"]]) for i in indexes),
            "affirmation inconnue")
        found.append({"class": c["class"], "segment_id": c["segment_id"],
                      "claims": sorted(set(indexes)), "statement": c["statement"]})
    return covered, found


def parse_refutation(answer: dict) -> tuple[str, dict | None]:
    """Verdict et passage d'un réfutateur. Un passage bien formé est consigné tel quel : le
    décideur le cherche dans les captures de la clé."""
    _require(answer.get("verdict") in VERDICTS, "verdict inconnu")
    _require("passage" in answer, "passage attendu")
    passage = answer["passage"]
    if passage is not None:
        _require(isinstance(passage, dict) and set(passage) == {"path", "cid", "quote"}
                 and all(isinstance(v, str) and v.strip() for v in passage.values())
                 and sr._CID.match(passage["cid"]), "passage malformé")
    return answer["verdict"], passage


def _attempt(call):
    try:
        return call(), None
    except ReviewerFailed as exc:
        return None, str(exc)


def execute(fm: dict, body: str, raw_root, command: list[str], models: list[str], *,
            passes: int, refuters: int, timeout=None, jobs: int = 1) -> dict:
    """Une exécution complète du protocole sur le texte publié `fm` + `body`, prête à déposer."""
    packet = sr.build_packet(fm, body, raw_root)
    if not packet["key_inputs"]["captures"]:
        raise ValueError("no_capture: la fiche ne cite aucune capture RAW, la relecture est impossible")
    texts = {s["id"]: s["text"] for s in packet["segments"]}
    hashes = {s["id"]: s["sha256"] for s in packet["segments"]}
    captures = packet["captures"]
    detection_input = DETECTION_PROMPT + json.dumps(
        {"segments": [{"id": sid, "text": text} for sid, text in texts.items()], "captures": captures},
        ensure_ascii=False, indent=2)
    pass_specs = [(f"p{i}", models[i % len(models)]) for i in range(passes)]
    errors = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        detections = list(pool.map(lambda spec: _attempt(lambda: parse_detection(
            ask(command, spec[1], detection_input, timeout), set(texts))), pass_specs))

        claims: dict[str, list] = {}
        run_passes, candidates = [], []
        for (pass_id, model), (result, error) in zip(pass_specs, detections):
            if error:
                errors.append(f"passe {pass_id}: {error}")
                continue
            covered, found = result
            for sid, items in covered.items():
                claims.setdefault(sid, []).extend(
                    {"id": f"{pass_id}-{n}", **claim} for n, claim in enumerate(items, start=1))
            run_passes.append({"pass_id": pass_id, "model": model, "covered_segments": sorted(covered)})
            for c in found:
                candidates.append({
                    "id": f"c{len(candidates) + 1}", "class": c["class"], "segment_id": c["segment_id"],
                    "claim_ids": [f"{pass_id}-{i + 1}" for i in c["claims"]],
                    "statement": c["statement"], "raised_by": [pass_id], "refutations": []})

        def refute(job):
            candidate, _, model = job
            subject = {"candidate": {"class": candidate["class"], "statement": candidate["statement"],
                                     "segment": {"id": candidate["segment_id"],
                                                 "text": texts[candidate["segment_id"]]}},
                       "captures": captures}
            prompt = REFUTATION_PROMPT + json.dumps(subject, ensure_ascii=False, indent=2)
            return _attempt(lambda: parse_refutation(ask(command, model, prompt, timeout)))

        jobs_list = [(c, f"r{j}", models[j % len(models)]) for c in candidates for j in range(refuters)]
        for (candidate, refuter_id, model), (result, error) in zip(jobs_list, pool.map(refute, jobs_list)):
            if error:
                errors.append(f"candidat {candidate['id']} {refuter_id}: {error}")
                continue
            verdict, passage = result
            candidate["refutations"].append(
                {"refuter_id": refuter_id, "model": model, "verdict": verdict, "passage": passage})

    # Un segment qu'aucune passe n'a couvert reste absent : la relecture est incomplète.
    segments = [{"id": sid, "sha256": hashes[sid],
                 **({"claims": claims[sid]} if claims[sid] else {"no_claims": True})}
                for sid in texts if sid in claims]
    used = ({p["model"] for p in run_passes}
            | {r["model"] for c in candidates for r in c["refutations"]}
            or {model for _, model in pass_specs})
    run = {"schema_version": sr.SCHEMA_VERSION, "key": packet["key"], "key_inputs": packet["key_inputs"],
           "models": sorted(used), "segments": segments, "passes": run_passes, "candidates": candidates}
    if errors:
        run["error"] = "; ".join(errors)
    return run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exécute l'auto-review de sens d'une fiche WIKI (ADR-119 D2) "
                                                 "et dépose l'exécution sous _audit/semantic-review/.")
    parser.add_argument("fiche", type=Path)
    parser.add_argument("--command", required=True,
                        help="commande du relecteur ; {model} y est remplacé ; invite sur stdin, réponse sur stdout")
    parser.add_argument("--model", action="append", required=True, dest="models",
                        help="identifiant de modèle, répétable : passes et réfutateurs les prennent à tour de rôle")
    parser.add_argument("--passes", type=int, default=sr.PROTOCOL["detection_passes_min"])
    parser.add_argument("--refuters", type=int, default=sr.PROTOCOL["refuters_min"])
    parser.add_argument("--timeout", type=float, default=None, help="délai par appel, en secondes")
    parser.add_argument("--jobs", type=int, default=1, help="appels simultanés")
    parser.add_argument("--wiki-root", type=Path, default=SCRIPTS_DIR.parent)
    parser.add_argument("--raw-root", type=Path, default=None,
                        help="racine RAW (défaut : AUTOMECANIK_RAW_PATH, puis ../automecanik-raw)")
    args = parser.parse_args(argv)

    command = shlex.split(args.command)
    problems = []
    if not any("{model}" in arg for arg in command):
        problems.append("--command doit transmettre {model} : le modèle consigné est celui qui relit")
    if args.passes < sr.PROTOCOL["detection_passes_min"] or args.refuters < sr.PROTOCOL["refuters_min"]:
        problems.append("passes ou réfutateurs sous le protocole : l'assouplir exige un ADR")
    if args.jobs < 1:
        problems.append("--jobs doit valoir au moins 1")
    if problems:
        print("; ".join(problems), file=sys.stderr)
        return 2

    decision = sr._decision_module()
    try:
        raw_fm, body = decision._parse_markdown(args.fiche)
        fm = decision._published_frontmatter(raw_fm)
        raw_root = decision._effective_raw_root(args.raw_root, args.wiki_root)
        run = execute(fm, body, raw_root, command, args.models, passes=args.passes,
                      refuters=args.refuters, timeout=args.timeout, jobs=args.jobs)
        target = sr.record_run(args.wiki_root, raw_fm.get("slug"), fm, body, run)
        evaluation = sr.evaluate_run(run, sr.segments(fm, body),
                                     sr.load_captures(run["key_inputs"]["captures"], raw_root))
    except (sr.ReviewInputUnavailable, sr.RunInvalid, decision.PromotionInputError, ValueError, OSError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"recorded": target.resolve().relative_to(args.wiki_root.resolve()).as_posix(),
                      **evaluation}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
