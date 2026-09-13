"""Document input adapter for author_from_raw; candidate preparation only.

Exact source spans prove quotation identity, never entailment of the supplied
statement. The canonical promotion decision remains a separate operation.
"""
from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import os
import tempfile
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_reader(raw_root):
    # Explicit trusted checkout; never import a module chosen by document data.
    path = raw_root / "_scripts/document_contract.py"
    if path.is_symlink() or not path.is_file():
        raise ValueError("document_reader_unavailable")
    spec = importlib.util.spec_from_file_location("raw_document_contract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.read_document


def read_selection_documents(selection, raw_root):
    """Read every pinned receipt once. Aliases and repeated text are not evidence."""
    legacy = selection["version"] == "1.0.0"
    entries = ([{"id": "document", **{k: selection[k] for k in
                ("receipt_path", "receipt_sha256", "source_language")}}]
               if legacy else selection["documents"])
    reader = load_reader(raw_root)
    documents, identities, texts = {}, set(), set()
    for entry in entries:
        identity = (entry["receipt_path"], entry["receipt_sha256"])
        if entry["id"] in documents or identity in identities:
            raise ValueError("document_selection_duplicate_document")
        doc = reader(raw_root, entry["receipt_path"], expected_receipt_sha256=entry["receipt_sha256"])
        if doc["receipt_path"] != entry["receipt_path"] or doc["receipt_sha256"] != entry["receipt_sha256"]:
            raise ValueError("document_reader_identity_mismatch")
        if doc["extraction"]["sha256"] in texts:
            raise ValueError("document_selection_duplicate_text")
        documents[entry["id"]] = {**doc, "source_language": entry["source_language"]}
        identities.add(identity)
        texts.add(doc["extraction"]["sha256"])
    return documents


def document_proof(doc):
    return {"receipt_path": doc["receipt_path"], "receipt_sha256": doc["receipt_sha256"],
            "original": doc["original"], "extraction": doc["extraction"],
            "source_url": doc["source_url"], "source_language": doc["source_language"],
            "license_status": doc["license_status"], "qualification_state": doc["qualification_state"]}


def prepare_document(slug, raw_root, proposals_dir, selection_path):
    from author_from_raw import SECTION_SPEC, MIN_LEN, _split_fm, _section_prose

    raw_root, proposals_dir = Path(raw_root).resolve(), Path(proposals_dir).resolve()
    selection_bytes = Path(selection_path).read_bytes()
    selection = json.loads(selection_bytes)
    schema = json.loads((ROOT / "_meta/schema/document-selection.schema.json").read_text())
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(selection)
    if slug != selection["slug"]:
        raise ValueError("document_selection_entity_mismatch")
    template_path = proposals_dir / (slug + ".md")
    if template_path.is_symlink():
        raise ValueError("document_template_symlink")
    template = template_path.read_bytes()
    if digest(template) != selection["template_sha256"]:
        raise ValueError("document_template_changed")
    old, _ = _split_fm(template.decode("utf-8"))
    if old.get("entity_type") != "gamme" or old.get("id") != "gamme:" + slug or old.get("slug") != slug:
        raise ValueError("document_selection_entity_mismatch")
    if old.get("lineage_id") and old["lineage_id"] != selection["lineage_id"]:
        raise ValueError("document_lineage_changed")
    legacy = selection["version"] == "1.0.0"
    documents = read_selection_documents(selection, raw_root)
    sections, evidence, spans, used = {}, [], set(), set()
    section_sources = {}
    for claim in selection["claims"]:
        section = claim["section"]
        if section not in SECTION_SPEC:
            raise ValueError("document_claim_anchor_invalid")
        anchors = ([{"document_id": "document", **{k: claim[k] for k in ("start", "end", "quote")}}]
                   if legacy else claim["anchors"])
        verified = []
        for anchor in anchors:
            doc_id = anchor["document_id"]
            if doc_id not in documents:
                raise ValueError("document_claim_reference_unknown")
            doc = documents[doc_id]
            start, end = anchor["start"], anchor["end"]
            if end <= start or end > len(doc["text"]) or doc["text"][start:end] != anchor["quote"]:
                raise ValueError("document_claim_anchor_invalid")
            if (doc_id, start, end) in spans:
                raise ValueError("document_claim_duplicate")
            spans.add((doc_id, start, end))
            used.add(doc_id)
            source_id = "raw:" + doc["extraction"]["sha256"][7:]
            sources = section_sources.setdefault(section, [])
            if source_id not in sources:
                sources.append(source_id)
            verified.append({**anchor, "quote_sha256": digest(anchor["quote"].encode("utf-8"))})
        # Treat markup as source data. Never execute or render supplied HTML.
        statement = html.escape(claim["statement"], quote=False)
        sections.setdefault(section, []).append({"claim": statement})
        if legacy:
            evidence.append({**claim, "derivation": "supplied_statement_unverified",
                             "quote_sha256": verified[0]["quote_sha256"]})
        else:
            evidence.append({"section": section, "statement": claim["statement"],
                             "derivation": "supplied_statement_unverified", "anchors": verified})
    if used != set(documents):
        raise ValueError("document_selection_unused_document")
    editorial, parts = {}, ["# " + html.escape(old["title"], quote=False), ""]
    for section, (heading, key) in SECTION_SPEC.items():
        if section not in sections:
            continue
        prose = _section_prose(sections[section])
        if len(prose) < MIN_LEN:
            raise ValueError("document_section_too_short")
        editorial[key] = {"content_md": prose, "source_ids": section_sources[section], "truth_level": "inferred"}
        parts.extend([heading, "", prose, ""])
    # Only identity/catalog taxonomy is inherited. No old claims or approval flags.
    ed = old["entity_data"]
    fm = {"schema_version": "2.0.0", "id": old["id"], "entity_type": "gamme", "slug": slug,
          "title": old["title"], "lang": selection["lang"], "created_at": old.get("created_at", selection["prepared_at"]),
          "updated_at": selection["prepared_at"], "lineage_id": selection["lineage_id"],
          "truth_level": "L3", "review_status": "in_review", "reviewed_by": None, "reviewed_at": None,
          "exportable": {"rag": False, "seo": False, "support": False},
          "provenance": {"ingested_by": "script:author_from_raw:document", "promoted_from": None},
          "entity_data": {"pg_id": ed["pg_id"], "family": ed["family"], "editorial": editorial},
          "source_refs": [{"kind": "raw", "path": path, "cid": sha, "captured_at": doc["captured_at"][:10]}
                          for doc in documents.values()
                          for path, sha in ((doc["receipt_path"], doc["receipt_sha256"]),
                                            (doc["original"]["path"], doc["original"]["sha256"]),
                                            (doc["extraction"]["path"], doc["extraction"]["sha256"]))],
          "review_notes": ("Candidate statements are unverified. One document, not three independent sources. "
                           if legacy else "Candidate statements are unverified. Artifact, URL and document counts do not prove independent sources. ")
                          + "No automatic language detection, entailment, license or completeness validation."}
    proof = {"selection_sha256": digest(selection_bytes), "template_sha256": digest(template),
             **(document_proof(documents["document"]) if legacy else
                {"selection_version": "1.1.0", "documents": [{"id": key, **document_proof(value)}
                                                           for key, value in documents.items()],
                 "independent_sources_verified": False}),
             "anchor_unit": "unicode_code_points_zero_based_end_exclusive", "claims": evidence}
    # Bind evidence into the candidate body/hash, not only a detachable CLI report.
    parts += ["## Preuves de préparation — affirmations à vérifier", "",
              "Passages sources et reformulations proposées ; aucune validation sémantique acquise.", "",
              "```json", json.dumps(proof, ensure_ascii=True, sort_keys=True, indent=2).replace("`", "\\u0060"), "```", ""]
    body = "\n" + "\n".join(parts)
    fm["content_hash"] = digest(body.encode("utf-8"))
    for name, value in (("frontmatter.schema.json", fm), ("entity-data/gamme.schema.json", fm["entity_data"])):
        schema = json.loads((ROOT / "_meta/schema" / name).read_text())
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(value)
    output = "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body
    report = {"action": "CANDIDATE_PREPARED", "slug": slug, "claims_selected": len(evidence),
                    "editorial_sections": len(editorial), "candidate_sha256": digest(output.encode("utf-8")),
                    "promotion_evaluated": False, "retrievable": False, "evidence": proof}
    if not legacy:
        report["documents_selected"] = len(documents)
        report["anchors_selected"] = len(spans)
    return output, report


def write_candidate(path, text, protected_roots):
    """Publish a new isolated artifact, never overwrite a proposal or RAW file."""
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("document_output_symlink")
    if any(path.resolve().is_relative_to(Path(root).resolve()) for root in protected_roots):
        raise ValueError("document_output_protected")
    # Atomic, exclusive visibility; a competing writer wins without being replaced.
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".document-candidate-", delete=False) as tmp:
        temp = Path(tmp.name)
        try:
            tmp.write(text.encode("utf-8"))
            tmp.flush()
            os.fsync(tmp.fileno())
            os.link(temp, path)
        finally:
            temp.unlink(missing_ok=True)
