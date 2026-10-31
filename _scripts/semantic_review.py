#!/usr/bin/env python3
"""
semantic_review — auto-review de sens d'une fiche WIKI (ADR-119 D2, D3, D8).

Module déterministe : il n'appelle aucun modèle. Les passes de détection et les réfutateurs
tournent hors du dépôt, sur le paquet que ce module produit ; ce module :

  - découpe le texte publié en segments (`segments`) : un par champ du frontmatter publié, un
    par bloc du corps ;
  - calcule la clé de relecture (`review_key`) : empreinte du texte publié, captures RAW citées,
    révision du protocole ;
  - valide et dépose une exécution sous `_audit/semantic-review/<slug>/<clé>/<sha256>.json`
    (`record_run`), sans verdict ;
  - recalcule le verdict de chaque exécution (`evaluate_run`) et l'état de la condition D3
    (`review_status`) pour `promotion_decision.py`, seul décideur.

Fail-closed : une exécution absente, périmée, incomplète, en erreur ou illisible ne donne jamais
`pass`. Un FAIL sur une clé n'est jamais remplacé par un PASS sur la même clé : les exécutions
sont adressées par leur contenu, et une exécution versionnée puis retirée de l'arbre est un trou
d'historique qui bloque. Protocole et usage : `_meta/semantic-review.md`.

CLI : `semantic_review.py packet|record|verdict FICHE ...` (voir `--help`).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path, PurePosixPath

import yaml
from jsonschema import Draft202012Validator
from markdown_it import MarkdownIt

SCRIPTS_DIR = Path(__file__).resolve().parent
SCHEMA_VERSION = "semantic-review/v1"
PACKET_SCHEMA_VERSION = "semantic-review-packet/v1"
REVIEW_DIR = Path("_audit") / "semantic-review"
RUN_SCHEMA_RELPATH = Path("_meta") / "schema" / "semantic-review-run.schema.json"

# Protocole D2. Le durcir (passes ou réfutateurs plus nombreux, classe bloquante ajoutée) = PR
# WIKI ; l'assouplir = ADR. Toute modification change `protocol_revision`, donc la clé : les
# exécutions déjà versionnées deviennent périmées.
PROTOCOL = {
    "detection_passes_min": 2,
    "refuters_min": 3,
    "refutation": "unanimous_with_capture_passage",
    "classes": ["valeur", "securite", "sens", "formulation"],
    "blocking_classes": ["valeur", "securite", "sens"],
    "segmenter": 1,
}

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_INCOMPLETE = "INCOMPLETE"
VERDICT_ERROR = "ERROR"

_CID = re.compile(r"\Asha256:[0-9a-f]{64}\Z")
_RUN_NAME = re.compile(r"\A[0-9a-f]{64}\.json\Z")
# Blocs feuilles du corps : chacun ouvre un segment. Une ligne de tableau est un bloc à part
# entière ; une ligne non blanche qu'aucun bloc ne porte (séparateur de tableau, marqueur de
# liste vide) prolonge le segment contigu.
_LEAF_BLOCKS = frozenset({"paragraph_open", "heading_open", "fence", "code_block",
                          "html_block", "hr", "tr_open"})
_MARKDOWN = MarkdownIt("commonmark").enable("table")


class ReviewInputUnavailable(Exception):
    """Entrée absente du contexte évalué (racine ou capture RAW, historique git, schéma) :
    défaut d'infrastructure, jamais un verdict sur le contenu."""


class RunInvalid(Exception):
    """Exécution illisible : schéma, références internes, nom ou clé incohérents."""


def _canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def protocol_revision() -> str:
    return _sha256_text(_canonical_json(PROTOCOL))


# --- Texte publié, segments et clé -------------------------------------------------------

def _yaml(value) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=True)


def published_text(fm: dict, body: str) -> str:
    """Texte publié relu : le frontmatter publié (sans cachets de promotion, voir
    `promotion_decision._published_frontmatter`), puis le corps."""
    return f"{_yaml(fm)}---\n{body}"


def _body_groups(body: str) -> list[str]:
    lines = body.split("\n")
    owner: dict[int, int] = {}
    for index, token in enumerate(_MARKDOWN.parse(body)):
        if token.type in _LEAF_BLOCKS and token.map:
            for line in range(*token.map):
                owner.setdefault(line, index)
    groups: list[list[str]] = []
    current, contiguous = None, False
    for number, line in enumerate(lines):
        block = owner.get(number)
        if block is not None:
            if contiguous and block == current:
                groups[-1].append(line)
            else:
                groups.append([line])
            current, contiguous = block, True
        elif line.strip():
            if contiguous:
                groups[-1].append(line)
            else:
                groups.append([line])
                current = None
            contiguous = True
        else:
            current, contiguous = None, False
    return ["\n".join(group) for group in groups]


def segments(fm: dict, body: str) -> list[dict]:
    """Découpage déterministe du texte publié (ADR-119 D2, complétude) : `fm:<champ>` pour chaque
    champ du frontmatter publié, puis `body:<n>` pour chaque bloc du corps. Toute ligne non blanche
    du corps appartient à un et un seul segment."""
    parts = [(f"fm:{key}", _yaml({key: fm[key]})) for key in sorted(fm, key=str)]
    parts += [(f"body:{n}", text) for n, text in enumerate(_body_groups(body), start=1)]
    return [{"id": sid, "sha256": _sha256_text(text), "text": text} for sid, text in parts]


def cited_captures(fm: dict) -> list[dict]:
    """Captures RAW citées (`source_refs` de kind `raw`), triées et dédoublonnées. Une capture
    sans `cid` ou à chemin non relatif ne peut pas lier la relecture à ses octets : ValueError."""
    refs = fm.get("source_refs")
    if refs is None:
        return []
    if not isinstance(refs, list):
        raise ValueError("source_refs_malformed: liste attendue")
    found = set()
    for i, ref in enumerate(refs):
        if not isinstance(ref, dict) or ref.get("kind") != "raw":
            continue
        path, cid = ref.get("path"), ref.get("cid")
        if not isinstance(path, str) or not path or "\\" in path:
            raise ValueError(f"capture_ref_malformed: source_refs[{i}].path")
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts:
            raise ValueError(f"capture_ref_malformed: source_refs[{i}].path")
        if cid is None:
            raise ValueError(f"capture_ref_unpinned: source_refs[{i}] sans cid")
        if not isinstance(cid, str) or not _CID.match(cid):
            raise ValueError(f"capture_ref_malformed: source_refs[{i}].cid")
        found.add((path, cid))
    return [{"path": path, "cid": cid} for path, cid in sorted(found)]


def review_key(fm: dict, body: str) -> tuple[str, dict]:
    """Clé D2 : sha256 du JSON canonique de {empreinte du texte publié, captures citées,
    révision du protocole}."""
    key_inputs = {"text_sha256": _sha256_text(published_text(fm, body)),
                  "captures": cited_captures(fm),
                  "protocol_revision": protocol_revision()}
    return _sha256_text(_canonical_json(key_inputs)), key_inputs


def load_captures(captures: list[dict], raw_root) -> dict:
    """Texte de chaque capture citée, ses octets vérifiés contre son `cid`."""
    root = Path(raw_root)
    if not root.is_dir():
        raise ReviewInputUnavailable("racine RAW")
    texts = {}
    for capture in captures:
        try:
            data = (root / capture["path"]).read_bytes()
        except OSError as exc:
            raise ReviewInputUnavailable(f"capture RAW {capture['path']}") from exc
        if f"sha256:{hashlib.sha256(data).hexdigest()}" != capture["cid"]:
            raise ValueError(f"capture_cid_mismatch: {capture['path']}")
        try:
            texts[(capture["path"], capture["cid"])] = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"capture_not_text: {capture['path']}") from exc
    return texts


def build_packet(fm: dict, body: str, raw_root) -> dict:
    """Paquet remis aux passes et aux réfutateurs : le texte publié découpé et les captures
    citées, rien d'autre (ADR-119 D2, entrées)."""
    key, key_inputs = review_key(fm, body)
    texts = load_captures(key_inputs["captures"], raw_root)
    return {
        "schema_version": PACKET_SCHEMA_VERSION,
        "key": key,
        "key_inputs": key_inputs,
        "protocol": PROTOCOL,
        "segments": segments(fm, body),
        "captures": [{**capture, "text": texts[(capture["path"], capture["cid"])]}
                     for capture in key_inputs["captures"]],
    }


# --- Exécutions -----------------------------------------------------------------------------

def load_run_schema(wiki_root) -> dict:
    path = Path(wiki_root) / RUN_SCHEMA_RELPATH
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReviewInputUnavailable(RUN_SCHEMA_RELPATH.as_posix()) from exc


def _duplicates(values) -> list:
    seen, dup = set(), []
    for value in values:
        if value in seen and value not in dup:
            dup.append(value)
        seen.add(value)
    return dup


def validate_run(run, schema: dict) -> None:
    """Schéma, puis références internes et clé. RunInvalid à la première incohérence."""
    errors = sorted(Draft202012Validator(schema).iter_errors(run), key=lambda e: list(e.absolute_path))
    if errors:
        raise RunInvalid("schema: " + "; ".join(
            f"{'/'.join(map(str, e.absolute_path)) or '$'}: {e.message}" for e in errors[:5]))
    problems = []
    segment_claims = {}
    for segment in run["segments"]:
        claim_ids = [c["id"] for c in segment.get("claims", [])]
        if _duplicates(claim_ids):
            problems.append(f"claims dupliquées dans {segment['id']}: {_duplicates(claim_ids)}")
        segment_claims[segment["id"]] = set(claim_ids)
    if _duplicates(s["id"] for s in run["segments"]):
        problems.append(f"segments dupliqués: {_duplicates(s['id'] for s in run['segments'])}")
    pass_ids = [p["pass_id"] for p in run["passes"]]
    if _duplicates(pass_ids):
        problems.append(f"passes dupliquées: {_duplicates(pass_ids)}")
    models = set(run["models"])
    for p in run["passes"]:
        if p["model"] not in models:
            problems.append(f"passe {p['pass_id']}: modèle non consigné")
        unknown = sorted(set(p["covered_segments"]) - set(segment_claims))
        if unknown:
            problems.append(f"passe {p['pass_id']}: segments inconnus {unknown}")
    if _duplicates(c["id"] for c in run["candidates"]):
        problems.append(f"candidats dupliqués: {_duplicates(c['id'] for c in run['candidates'])}")
    for c in run["candidates"]:
        if not set(c["raised_by"]) <= set(pass_ids):
            problems.append(f"candidat {c['id']}: passe inconnue dans raised_by")
        if c["segment_id"] not in segment_claims:
            problems.append(f"candidat {c['id']}: segment inconnu")
        elif not set(c.get("claim_ids", [])) <= segment_claims[c["segment_id"]]:
            problems.append(f"candidat {c['id']}: affirmation inconnue dans son segment")
        if _duplicates(r["refuter_id"] for r in c["refutations"]):
            problems.append(f"candidat {c['id']}: réfutateur dupliqué")
        if any(r["model"] not in models for r in c["refutations"]):
            problems.append(f"candidat {c['id']}: modèle de réfutateur non consigné")
    if _sha256_text(_canonical_json(run["key_inputs"])) != run["key"]:
        problems.append("clé différente de l'empreinte de key_inputs")
    if problems:
        raise RunInvalid("; ".join(problems))


def read_run(path: Path, schema: dict, key: str) -> dict:
    """Une exécution versionnée : nom = sha256 de ses octets, répertoire = sa clé."""
    data = path.read_bytes()
    if path.name != f"{hashlib.sha256(data).hexdigest()}.json":
        raise RunInvalid("nom différent de l'empreinte du contenu")
    try:
        run = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunInvalid(f"JSON illisible: {exc}") from exc
    validate_run(run, schema)
    if run["key"] != key or path.parent.name != key:
        raise RunInvalid("clé différente de celle de la fiche")
    return run


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def evaluate_run(run: dict, expected_segments: list[dict], capture_texts: dict) -> dict:
    """Verdict recalculé d'une exécution valide (ADR-119 D2). Un candidat est écarté seulement
    si au moins `refuters_min` réfutateurs distincts le réfutent tous avec un passage retrouvé
    dans une capture citée ; un seul réfutateur qui ne réfute pas, ou un passage introuvable, le
    confirme. Avec moins de réfutateurs, tous réfutant, il reste en attente : relecture
    incomplète. FAIL dès qu'un écart d'une classe bloquante est confirmé, même incomplète."""
    allowed = {(c["path"], c["cid"]) for c in run["key_inputs"]["captures"]}
    sources = {ref: _normalize(text) for ref, text in capture_texts.items() if ref in allowed}

    def anchored(passage) -> bool:
        if not isinstance(passage, dict):
            return False
        quote = _normalize(passage["quote"])
        source = sources.get((passage["path"], passage["cid"]))
        return bool(quote) and source is not None and quote in source

    confirmed = {name: 0 for name in PROTOCOL["classes"]}
    dismissed = pending = unsettled = 0
    for candidate in run["candidates"]:
        votes = [(r["verdict"], anchored(r["passage"])) for r in candidate["refutations"]]
        if any(verdict != "refuted" or not ok for verdict, ok in votes):
            confirmed[candidate["class"]] += 1
            if not any(verdict == "upheld" and ok for verdict, ok in votes):
                unsettled += 1
        elif len(votes) >= PROTOCOL["refuters_min"]:
            dismissed += 1
        else:
            pending += 1

    expected = {s["id"]: s["sha256"] for s in expected_segments}
    reviewed = {s["id"]: s["sha256"] for s in run["segments"]}
    incomplete = []
    missing = [sid for sid in expected if sid not in reviewed]
    extra = sorted(sid for sid in reviewed if sid not in expected)
    changed = [sid for sid in expected if sid in reviewed and reviewed[sid] != expected[sid]]
    if missing:
        incomplete.append(f"segments absents: {missing}")
    if extra:
        incomplete.append(f"segments inconnus: {extra}")
    if changed:
        incomplete.append(f"segments d'empreinte différente: {changed}")
    if len(run["passes"]) < PROTOCOL["detection_passes_min"]:
        incomplete.append(f"passes: {len(run['passes'])} < {PROTOCOL['detection_passes_min']}")
    for p in run["passes"]:
        uncovered = [sid for sid in expected if sid not in p["covered_segments"]]
        if uncovered:
            incomplete.append(f"passe {p['pass_id']}: segments non couverts {uncovered}")
    if pending:
        incomplete.append(f"candidats en attente de réfutateurs: {pending}")

    total_confirmed = sum(confirmed.values())
    if any(confirmed[name] for name in PROTOCOL["blocking_classes"]):
        verdict = VERDICT_FAIL
    elif run.get("error"):
        verdict = VERDICT_ERROR
    elif incomplete:
        verdict = VERDICT_INCOMPLETE
    else:
        verdict = VERDICT_PASS
    return {
        "verdict": verdict,
        "confirmed_by_class": confirmed,
        "dismissed": dismissed,
        "pending": pending,
        "unsettled_confirmed": unsettled,
        "unsettled_share": round(unsettled / total_confirmed, 4) if total_confirmed else None,
        "incomplete": incomplete,
        "error": run.get("error"),
        "models": run["models"],
    }


def _check_slug(slug) -> str:
    if not isinstance(slug, str) or not slug or "/" in slug or "\\" in slug or slug.startswith("."):
        raise ValueError(f"slug_malformed: {slug!r}")
    return slug


def _git(wiki_root: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=wiki_root, check=True,
                              capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReviewInputUnavailable(f"historique git du WIKI (git {args[0]})") from exc


def _history_gaps(wiki_root: Path, key_dir: Path) -> list[str]:
    """Exécutions de la clé versionnées un jour puis retirées de l'arbre, ou présentes sans être
    versionnées telles quelles. Historique superficiel ou absent : ReviewInputUnavailable."""
    if _git(wiki_root, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise ReviewInputUnavailable("historique git complet du WIKI (clone superficiel)")
    top = Path(_git(wiki_root, "rev-parse", "--show-toplevel").strip()).resolve()
    rel = key_dir.resolve().relative_to(top).as_posix()
    added = {line for line in _git(wiki_root, "log", "--format=", "--name-only", "--no-renames",
                                   "--diff-filter=A", "HEAD", "--", rel).splitlines() if line}
    gaps = [f"retirée de l'arbre: {path}" for path in sorted(added) if not (top / path).is_file()]
    status = _git(wiki_root, "status", "--porcelain", "--untracked-files=all", "--", rel)
    gaps += [f"non versionnée ou modifiée: {line[3:]}" for line in status.splitlines() if line]
    return gaps


def review_status(wiki_root, slug, fm: dict, body: str, raw_root) -> dict:
    """État de la condition D3 pour la fiche (`fm` = frontmatter publié). `pass` n'est vrai que
    si une exécution versionnée de la clé courante rend PASS et qu'aucune ne rend FAIL, sans
    exécution illisible ni trou d'historique sur cette clé. Statuts, du plus fort au plus faible :
    FAIL, HISTORY_GAP, UNREADABLE, PASS, INCOMPLETE, ERROR, STALE (exécutions d'une autre clé
    seulement), ABSENT ; NO_CAPTURE si la fiche ne cite aucune capture RAW."""
    wiki_root = Path(wiki_root)
    slug = _check_slug(slug)
    key, key_inputs = review_key(fm, body)
    result = {"key": key, "key_inputs": key_inputs, "status": None, "pass": False,
              "verdict_run": None, "runs": [], "unreadable": [], "history_gaps": []}
    if not key_inputs["captures"]:
        result["status"] = "NO_CAPTURE"
        return result
    capture_texts = load_captures(key_inputs["captures"], raw_root)
    schema = load_run_schema(wiki_root)
    slug_dir = wiki_root / REVIEW_DIR / slug
    key_dir = slug_dir / key
    result["history_gaps"] = _history_gaps(wiki_root, key_dir)
    expected = segments(fm, body)
    if key_dir.is_dir():
        for path in sorted(key_dir.iterdir()):
            try:
                if not path.is_file() or not _RUN_NAME.match(path.name):
                    raise RunInvalid("fichier hors convention <sha256>.json")
                run = read_run(path, schema, key)
            except (OSError, RunInvalid) as exc:
                result["unreadable"].append({"file": path.name, "error": str(exc)})
                continue
            result["runs"].append({"file": path.name, **evaluate_run(run, expected, capture_texts)})
    verdicts = [r["verdict"] for r in result["runs"]]
    if VERDICT_FAIL in verdicts:
        status = "FAIL"
    elif result["history_gaps"]:
        status = "HISTORY_GAP"
    elif result["unreadable"]:
        status = "UNREADABLE"
    elif VERDICT_PASS in verdicts:
        status = "PASS"
    elif VERDICT_INCOMPLETE in verdicts:
        status = "INCOMPLETE"
    elif VERDICT_ERROR in verdicts:
        status = "ERROR"
    elif slug_dir.is_dir() and any(p.name != key for p in slug_dir.iterdir()):
        status = "STALE"
    else:
        status = "ABSENT"
    result["status"] = status
    result["pass"] = status == "PASS"
    result["verdict_run"] = next((r["file"] for r in result["runs"] if r["verdict"] == status), None)
    return result


def record_run(wiki_root, slug, fm: dict, body: str, run: dict) -> Path:
    """Dépose une exécution valide de la fiche courante, adressée par son contenu. N'écrit jamais
    la fiche ; ne remplace jamais une exécution existante."""
    wiki_root = Path(wiki_root)
    slug = _check_slug(slug)
    validate_run(run, load_run_schema(wiki_root))
    key, key_inputs = review_key(fm, body)
    if run["key"] != key or run["key_inputs"] != key_inputs:
        raise RunInvalid("l'exécution ne porte pas sur le texte, les captures ou le protocole courants")
    data = (json.dumps(run, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    target = wiki_root / REVIEW_DIR / slug / key / f"{hashlib.sha256(data).hexdigest()}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(data)
    return target


# --- CLI ------------------------------------------------------------------------------------

def _decision_module():
    """`promotion_decision.py`, chargé par chemin pour la CLI seulement : lecture de la fiche,
    frontmatter publié et racine RAW identiques à ceux du décideur."""
    spec = importlib.util.spec_from_file_location("_promotion_decision_cli", SCRIPTS_DIR / "promotion_decision.py")
    decision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(decision)
    return decision


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Auto-review de sens d'une fiche WIKI (ADR-119 D2).")
    parser.add_argument("--wiki-root", type=Path, default=SCRIPTS_DIR.parent)
    parser.add_argument("--raw-root", type=Path, default=None,
                        help="racine RAW (défaut : AUTOMECANIK_RAW_PATH, puis ../automecanik-raw)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("packet", help="paquet JSON des segments et des captures, sur stdout").add_argument("fiche", type=Path)
    record = sub.add_parser("record", help="dépose une exécution sous _audit/semantic-review/")
    record.add_argument("fiche", type=Path)
    record.add_argument("run", type=Path)
    sub.add_parser("verdict", help="état de la condition D3 ; code 0 seulement si PASS").add_argument("fiche", type=Path)
    args = parser.parse_args(argv)

    decision = _decision_module()
    try:
        raw_fm, body = decision._parse_markdown(args.fiche)
        fm = decision._published_frontmatter(raw_fm)
        raw_root = decision._effective_raw_root(args.raw_root, args.wiki_root)
        if args.command == "packet":
            print(json.dumps(build_packet(fm, body, raw_root), ensure_ascii=False, indent=2))
            return 0
        if args.command == "record":
            run = json.loads(args.run.read_text(encoding="utf-8"))
            target = record_run(args.wiki_root, raw_fm.get("slug"), fm, body, run)
            print(target.resolve().relative_to(args.wiki_root.resolve()).as_posix())
            return 0
        status = review_status(args.wiki_root, raw_fm.get("slug"), fm, body, raw_root)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if status["pass"] else 1
    except (ReviewInputUnavailable, RunInvalid, decision.PromotionInputError, ValueError, OSError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
