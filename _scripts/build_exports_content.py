#!/usr/bin/env python3
"""Native content projection/admission for Fafa. No promotion or RAW writes."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import click
import yaml
from jsonschema import Draft202012Validator
import promotion_decision as promotion
from build_exports_diagnostic import (
    _canonical_json, _serialise, _committed_source_sha, _assert_commits_on,
    _load_catalog, CATALOG_REL,
)

SCHEMA = "_meta/schema/exports-content.schema.json"
VERSION = "1.0.0"
EXPORT_PATTERN = r"exports/content/gamme/[a-z0-9-]+\.json"

class AdmissionError(Exception):
    def __init__(self, code, status="DENIED"):
        super().__init__(code)
        self.code, self.status = code, status


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def bounded(root, relative):
    root = root.resolve()
    path = root / relative
    if not path.resolve().is_relative_to(root):
        raise AdmissionError("REFERENCE_MISMATCH")
    return path


def schema_at(root):
    return strict_json(bounded(root, SCHEMA).read_bytes())


def validate(root, value, definition=None):
    schema = schema_at(root)
    if definition:
        schema = {"$ref": "#/$defs/" + definition, "$defs": schema["$defs"]}
    Draft202012Validator(schema).validate(value)


def content_revision(root):
    # Bind all local schema dependencies and native code, including helpers loaded lazily.
    paths = list((root / "_meta/schema").rglob("*.json"))
    paths += list((root / "_scripts").rglob("*.py"))
    paths += [root / "_meta/entity-registry.json", root / "_scripts/requirements-scoring.txt"]
    manifest = [(p.relative_to(root).as_posix(), sha(bounded(root, p.relative_to(root)).read_bytes()) if p.is_file() else None)
                for p in sorted(paths) if not p.name.startswith("test_")]
    manifest.append((promotion.PROMOTE_GATE_ENGINE_ENV, os.environ.get(promotion.PROMOTE_GATE_ENGINE_ENV)))
    return sha(_canonical_json(manifest))


def _build(source_path, wiki_root, raw_root):
    root, raw = Path(wiki_root).resolve(), Path(raw_root).resolve()
    source = Path(source_path)
    relative = source.relative_to(root).as_posix()
    if not re.fullmatch(r"wiki/gamme/[a-z0-9-]+\.md", relative):
        raise AdmissionError("REFERENCE_MISMATCH")
    source = bounded(root, relative)
    revision = content_revision(root)
    before_inputs = promotion.capture_input_manifest(source, root, raw, None)
    source_bytes = source.read_bytes()
    fm, _ = promotion._parse_markdown(source, source_bytes=source_bytes)
    selector = fm.get("content_export") or {}
    if fm.get("exportable", {}).get("content") is not True or selector.get("consumer") != "fafa":
        raise AdmissionError("AUDIENCE_NOT_ALLOWED")
    if fm.get("review_status") != "approved" or fm.get("no_disputed_claims") is not True:
        raise AdmissionError("SOURCE_NOT_APPROVED")
    if fm.get("entity_type") != "gamme" or fm.get("slug") != source.stem:
        raise AdmissionError("REFERENCE_MISMATCH")
    gamme = strict_json(bounded(root, "_meta/schema/entity-data/gamme.schema.json").read_bytes())
    names = selector.get("sections")
    if not isinstance(names, list) or not names or any(not isinstance(n, str) or n not in gamme["properties"]["editorial"]["properties"] for n in names):
        raise AdmissionError("SECTION_NOT_FOUND")
    if len(set(names)) != len(names):
        raise AdmissionError("REFERENCE_MISMATCH")
    try:
        Draft202012Validator(strict_json(bounded(root, "_meta/schema/frontmatter.schema.json").read_bytes())).validate(fm)
        Draft202012Validator(gamme).validate(fm.get("entity_data"))
    except Exception as exc:
        raise AdmissionError("CANONICAL_DECISION_BLOCKED") from exc
    catalog_bytes = bounded(root, CATALOG_REL).read_bytes()
    try:
        catalog = _load_catalog(root, source_bytes=catalog_bytes)
        source_commit = _committed_source_sha(root, relative, source_bytes)
        catalog_commit = _committed_source_sha(root, CATALOG_REL, catalog_bytes)
    except click.ClickException as exc:
        raise AdmissionError("REFERENCE_MISMATCH") from exc
    # Existing coverage owns source proof. Require the selected whole text to be an
    # already covered anchor, not merely another block in the same approved fiche.
    coverage = yaml.safe_load(bounded(root, f"proposals/_coverage/{source.stem}.coverage.yaml").read_text())
    entries = coverage.get("coverage_entries", [])
    sections = []
    for name in sorted(names):
        block = (fm.get("entity_data", {}).get("editorial") or {}).get(name)
        if not block:
            raise AdmissionError("SECTION_NOT_FOUND")
        for source_id in block["source_ids"]:
            slug = source_id.split(":", 1)[1]
            if slug not in catalog or not any(e.get("source_slug") == slug and e.get("text_anchor") == block["content_md"] for e in entries):
                raise AdmissionError("CANONICAL_DECISION_BLOCKED")
        sections.append({"section": name, **{k:block[k] for k in ("content_md", "source_ids", "truth_level")},
                         "sha256": sha(block["content_md"].encode("utf-8"))})
    decision = promotion.canonical_promotion_decision(source, root, raw_root=raw)
    _reverify({"inputs": before_inputs}, source, root, raw, revision)
    if decision.get("eligible") is not True or decision.get("promotion_status") != "ELIGIBLE":
        unavailable = any(r["code"].endswith("_UNAVAILABLE") for r in decision.get("blocking_reasons", []))
        raise AdmissionError("AUTHORITY_UNAVAILABLE" if unavailable else "CANONICAL_DECISION_BLOCKED",
                             "UNAVAILABLE" if unavailable else "DENIED")
    inputs = decision["inputs"]
    payload = dict(schema_version=VERSION, export_kind="content_gamme", consumer="fafa",
                   wiki_path=relative, source_wiki_commit=source_commit, source_catalog_commit=catalog_commit,
                   source_file_sha256=sha(source_bytes), sections=sections, content_hash=sha(_canonical_json(sections)),
                   decision={"promotion_status":"ELIGIBLE", "content_engine_revision":revision,
                             **{k:inputs[k] for k in ("input_manifest", "evaluation_engine_revision", "decision_engine_revision")}})
    validate(root, payload)
    _reverify(decision, source, root, raw, revision)
    return payload, decision, revision


def _reverify(decision, source, root, raw, revision):
    if promotion.reverify_inputs(decision, source, root, raw_root=raw) or content_revision(root) != revision:
        raise AdmissionError("AUTHORITY_INPUT_CHANGED")


def build_content_export(source_path: Path, wiki_root: Path, *, raw_root: Path) -> dict:
    return _build(source_path, wiki_root, raw_root)[0]


def current_tip(root, remote, ref):
    # Remote and ref come only from operator arguments. No shell, no fetch/reset.
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", remote) or not ref.startswith("refs/heads/"):
        raise ValueError("INVALID_OPERATOR_CONFIG")
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=15, check=True).stdout.strip()
        out = subprocess.run(["git", "ls-remote", "--exit-code", remote, ref], cwd=root,
                             capture_output=True, text=True, timeout=15, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise AdmissionError("AUTHORITY_UNAVAILABLE", "UNAVAILABLE") from exc
    rows = [line.split() for line in out.stdout.splitlines()]
    if len(rows) != 1 or rows[0] != [head, ref]:
        raise AdmissionError("AUTHORITY_NOT_CURRENT", "UNAVAILABLE")
    return head


def resolve(request, root, raw, remote="origin", ref="refs/heads/main"):
    validate(root, request, "AdmissionRequest")
    refs = request["references"]
    if len({r["doc_id"] for r in refs}) != len(refs):
        raise ValueError("DUPLICATE_REFERENCE")
    results, final_checks, authority = [], [], None
    def failed_all(error):
        return [{"reference": r, "status": error.status, "code": error.code} for r in refs]
    try:
        authority = current_tip(root, remote, ref)
        for reference in refs:
            try:
                export_path = bounded(root, reference["export_path"])
                data = export_path.read_bytes()
                if sha(data) != reference["export_sha256"]:
                    raise AdmissionError("REFERENCE_MISMATCH")
                actual = strict_json(data)
                validate(root, actual)
                source = bounded(root, "wiki/gamme/" + export_path.stem + ".md")
                expected, decision, revision = _build(source, root, raw)
                _assert_commits_on(root, {expected["source_wiki_commit"]:["wiki"], expected["source_catalog_commit"]:["catalog"]}, ref)
                if data != _serialise(expected):
                    raise AdmissionError("STALE_EXPORT")
                if reference["wiki_path"] != expected["wiki_path"] or reference["source_wiki_commit"] != expected["source_wiki_commit"]:
                    raise AdmissionError("REFERENCE_MISMATCH")
                section = next((s for s in expected["sections"] if s["section"] == reference["section"]), None)
                if section is None:
                    raise AdmissionError("SECTION_NOT_FOUND")
                if reference["section_sha256"] != section["sha256"] or reference["excerpt"] != section["content_md"]:
                    raise AdmissionError("REFERENCE_MISMATCH")
                final_checks.append((decision, source, revision, export_path, data))
                result = {"status":"ADMITTED", "code":"ADMITTED"}
            except AdmissionError as error:
                result = {"status":error.status, "code":error.code}
            except PermissionError:
                result = {"status":"UNAVAILABLE", "code":"AUTHORITY_ACCESS_DENIED"}
            except (OSError, ValueError, click.ClickException):
                result = {"status":"UNAVAILABLE", "code":"AUTHORITY_UNAVAILABLE"}
            results.append({"reference":reference, **result})
        if current_tip(root, remote, ref) != authority:
            raise AdmissionError("AUTHORITY_NOT_CURRENT", "UNAVAILABLE")
        for decision, source, revision, export_path, data in final_checks:
            _reverify(decision, source, root, raw, revision)
            if bounded(root, export_path.relative_to(root)).read_bytes() != data:
                raise AdmissionError("AUTHORITY_INPUT_CHANGED")
    except AdmissionError as error:
        results = failed_all(error)
    except PermissionError:
        results = failed_all(AdmissionError("AUTHORITY_ACCESS_DENIED", "UNAVAILABLE"))
    except OSError:
        results = failed_all(AdmissionError("AUTHORITY_UNAVAILABLE", "UNAVAILABLE"))
    response = dict(schema_version=VERSION, request_id=request["request_id"], consumer="fafa",
                    authority_revision=authority, results=results)
    validate(root, response, "AdmissionResponse")
    return response


def generate(root, raw, check, ref):
    expected, checks = {}, []
    for source in sorted((root / "wiki/gamme").glob("*.md")):
        fm, _ = promotion._parse_markdown(source)
        if fm.get("exportable", {}).get("content") is not True:
            continue
        payload, decision, revision = _build(source, root, raw)
        _assert_commits_on(root, {payload["source_wiki_commit"]:["wiki"], payload["source_catalog_commit"]:["catalog"]}, ref)
        relative = "exports/content/gamme/" + source.stem + ".json"
        expected[relative] = _serialise(payload)
        checks.append((decision, source, revision))
    existing = {p.relative_to(root).as_posix() for p in (root / "exports/content/gamme").glob("*.json")}
    if existing - expected.keys():
        raise AdmissionError("UNRECONCILED_EXPORT")
    expected["exports/content/_index.json"] = _serialise({"schema_version":VERSION, "consumer":"fafa",
        "exports":[{"path":p,"sha256":sha(b)} for p,b in sorted(expected.items())]})
    for decision, source, revision in checks:
        _reverify(decision, source, root, raw, revision)
    for relative, data in expected.items():
        target = bounded(root, relative)
        if check:
            if not target.is_file() or target.read_bytes() != data:
                raise AdmissionError("STALE_EXPORT")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            # Atomic per file only. Resolution recomputes each export independently.
            fd, name = tempfile.mkstemp(dir=target.parent, prefix=".content-")
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data); stream.flush(); os.fsync(stream.fileno())
                os.replace(name, target)
            finally:
                if os.path.exists(name):
                    os.unlink(name)


@click.command()
@click.option("--wiki-root", type=click.Path(path_type=Path), required=True)
@click.option("--raw-root", type=click.Path(path_type=Path), required=True)
@click.option("--check", is_flag=True)
@click.option("--resolve-stdin", is_flag=True)
@click.option("--require-commits-on", default="refs/heads/main")
@click.option("--require-remote", default="origin")
def main(wiki_root, raw_root, check, resolve_stdin, require_commits_on, require_remote):
    root, raw = wiki_root.resolve(), raw_root.resolve()
    try:
        if root != Path(__file__).resolve().parents[1]:
            raise ValueError("AUTHORITY_ROOT_MISMATCH")
        if resolve_stdin:
            if check:
                raise ValueError("INCOMPATIBLE_MODES")
            data = sys.stdin.buffer.read(4 * 1024 * 1024 + 1)
            if len(data) > 4 * 1024 * 1024:
                raise ValueError("REQUEST_TOO_LARGE")
            answer = resolve(strict_json(data), root, raw, require_remote, require_commits_on)
            click.echo(json.dumps(answer, ensure_ascii=False))
            sys.exit(0 if all(r["status"] == "ADMITTED" for r in answer["results"]) else 2)
        generate(root, raw, check, require_commits_on)
    except Exception as error:
        click.echo(str(error), err=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
