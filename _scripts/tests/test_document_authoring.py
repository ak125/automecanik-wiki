"""Candidate behavior uses native WIKI schemas; RAW reader mocked here.

The retained MAHLE integration evidence separately exercises the real RAW reader.
"""
import copy
import json
import sys
from pathlib import Path

import pytest
import yaml

import author_from_raw as author
import document_authoring as document


@pytest.fixture
def lane(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    proposals = tmp_path / "proposals"
    raw.mkdir()
    proposals.mkdir()
    fm = {"id": "gamme:thermostat", "slug": "thermostat", "title": "Thermostat", "entity_type": "gamme",
          "review_status": "approved", "exportable": {"seo": True},
          "lineage_id": "01900000-0000-7000-8000-000000000001",
          "entity_data": {"pg_id": 316, "family": "refroidissement", "dimensions": {"stale": "old claim"}}}
    template = "---\n" + yaml.safe_dump(fm) + "---\nOLD CONTENT\n"
    (proposals / "thermostat.md").write_text(template)
    text = "Début 📖. " + "Various systems and engine components must be supplied with coolant as required. " * 2
    receipt = "sources/auto-captures/documents/" + "a" * 64 + ".md"
    doc = {"receipt_path": receipt, "receipt_sha256": "sha256:" + "b" * 64,
           "text": text, "captured_at": "2026-09-13T22:36:59Z", "source_url": "https://manufacturer.example/cooling",
           "original": {"path": "sources/document-originals/" + "c" * 64 + ".html", "sha256": "sha256:" + "c" * 64},
           "extraction": {"path": "normalized/document-text/" + "d" * 64 + ".txt", "sha256": "sha256:" + "d" * 64},
           "license_status": "unknown", "qualification_state": "pending"}
    def reader(root, relative, *, expected_receipt_sha256):
        assert root == raw and relative == receipt and expected_receipt_sha256 == doc["receipt_sha256"]
        return doc
    monkeypatch.setattr(document, "load_reader", lambda root: reader)
    quote = text[9:]
    selection = {"version": "1.0.0", "slug": "thermostat", "lang": "fr", "source_language": "en",
                 "prepared_at": "2026-09-14", "lineage_id": "01900000-0000-7000-8000-000000000001",
                 "template_sha256": document.digest(template.encode()), "receipt_path": receipt,
                 "receipt_sha256": doc["receipt_sha256"], "claims": [{"section": "function", "start": 9,
                 "end": len(text), "quote": quote,
                 "statement": "Selon cette présentation du fabricant, les composants du moteur reçoivent du liquide de refroidissement en fonction de leurs besoins de régulation thermique."}]}
    selected = tmp_path / "selection.json"
    selected.write_text(json.dumps(selection))
    return raw, proposals, selected, selection, doc


def run(lane):
    raw, proposals, selected, _, _ = lane
    return document.prepare_document("thermostat", raw, proposals, selected)


def test_prepares_exact_provenance_and_drops_previous_claims_and_approval(lane):
    md, report = run(lane)
    fm, body = author._split_fm(md)
    assert fm["review_status"] == "in_review" and not any(fm["exportable"].values())
    assert fm["truth_level"] == "L3" and fm["reviewed_by"] is None
    assert fm["entity_data"]["editorial"]["function"]["truth_level"] == "inferred"
    assert "dimensions" not in fm["entity_data"] and "OLD CONTENT" not in md
    assert fm["content_hash"] == document.digest(body.encode())
    assert len(fm["source_refs"]) == 3 and all(r["kind"] == "raw" for r in fm["source_refs"])
    assert report["claims_selected"] == 1 and not report["promotion_evaluated"]
    assert report["evidence"]["claims"][0]["quote"] == lane[4]["text"][9:]
    assert run(lane) == (md, report)


@pytest.mark.parametrize("change", ["quote", "start", "end", "past_end", "section", "duplicate", "short", "empty", "unknown", "hash", "slug", "lineage", "lineage_changed", "date"])
def test_bad_selection_refused(lane, change):
    raw, proposals, path, selection, _ = lane
    selection = copy.deepcopy(selection)
    claim = selection["claims"][0]
    if change == "quote": claim["quote"] += "invented"
    elif change == "start": claim["start"] += 1
    elif change == "end": claim["end"] = claim["start"]
    elif change == "past_end": claim["end"] += 100
    elif change == "section": claim["section"] = "made_up_section"
    elif change == "duplicate": selection["claims"].append(copy.deepcopy(claim))
    elif change == "short": claim["statement"] = "Trop court."
    elif change == "empty": selection["claims"] = []
    elif change == "unknown": selection["approved"] = True
    elif change == "hash": selection["template_sha256"] = "sha256:" + "0" * 64
    elif change == "slug": selection["slug"] = "../escape"
    elif change == "lineage": selection["lineage_id"] = "not-a-uuid"
    elif change == "lineage_changed": selection["lineage_id"] = "01990000-0000-7000-8000-000000000001"
    elif change == "date": selection["prepared_at"] = "2026-02-31"
    path.write_text(json.dumps(selection))
    with pytest.raises(Exception): run(lane)


def test_reader_refusal_stops_authoring(lane, monkeypatch):
    def refuse(*args, **kwargs): raise ValueError("corrupt original")
    monkeypatch.setattr(document, "load_reader", lambda root: refuse)
    with pytest.raises(ValueError): run(lane)


def test_markup_cannot_close_proof_fence_or_render_html(lane):
    lane[3]["claims"][0]["statement"] += " <script>alert(1)</script>"
    lane[4]["text"] += "\n```\n<script>bad</script>"
    lane[3]["claims"][0].update(end=len(lane[4]["text"]), quote=lane[4]["text"][9:])
    lane[2].write_text(json.dumps(lane[3]))
    md, _ = run(lane)
    assert md.count("```") == 2
    assert "&lt;script&gt;alert" in md


def test_exclusive_output_and_protected_roots(lane, tmp_path):
    raw, proposals, _, _, _ = lane
    md, _ = run(lane)
    output = tmp_path / "candidate.md"
    document.write_candidate(output, md, (raw, proposals))
    assert output.read_text() == md
    with pytest.raises(FileExistsError): document.write_candidate(output, "overwrite", (raw, proposals))
    assert output.read_text() == md
    for dest in (raw / "source.md", proposals / "new.md"):
        with pytest.raises(ValueError): document.write_candidate(dest, md, (raw, proposals))
    alias = tmp_path / "alias"
    alias.symlink_to(raw, target_is_directory=True)
    with pytest.raises(ValueError): document.write_candidate(alias / "out.md", md, (raw, proposals))
    assert not list(tmp_path.glob(".document-candidate-*"))


def test_cli_failure_has_no_source_and_no_output(lane, tmp_path, capsys):
    lane[2].write_text('{"secret-sentinel": "bad input"}')
    output = tmp_path / "candidate.md"
    rc = author.main(["--slug", "thermostat", "--raw-root", str(lane[0]), "--proposals-dir", str(lane[1]),
                      "--document-selection", str(lane[2]), "--out", str(output)])
    captured = capsys.readouterr()
    assert rc == 1 and not output.exists() and not captured.out
    assert "secret-sentinel" not in captured.err
    assert json.loads(captured.err)["action"] == "REFUSED"


def test_cli_success_and_legacy_dispatch(lane, tmp_path, monkeypatch, capsys):
    output = tmp_path / "candidate.md"
    args = ["--slug", "thermostat", "--raw-root", str(lane[0]), "--proposals-dir", str(lane[1])]
    assert author.main([*args, "--document-selection", str(lane[2]), "--out", str(output)]) == 0
    assert json.loads(capsys.readouterr().out)["action"] == "CANDIDATE_PREPARED"
    calls = []
    monkeypatch.setattr(author, "author", lambda *a: (calls.append(a) or "legacy", {"hard_fail": None}))
    assert author.main(args) == 0 and len(calls) == 1


def test_missing_real_reader_is_closed(tmp_path):
    with pytest.raises(ValueError): document.load_reader(tmp_path)


@pytest.fixture
def multi_lane(lane, monkeypatch):
    raw, proposals, path, old, first = lane
    second = copy.deepcopy(first)
    # Same URL intentionally: multiple snapshots never establish independence.
    second.update(receipt_path='sources/auto-captures/documents/' + 'e' * 64 + '.md',
                  receipt_sha256='sha256:' + 'f' * 64)
    second['text'] = first['text'].replace('Various', 'Several')
    for key, letter, suffix in [('original', '1', '.html'), ('extraction', '2', '.txt')]:
        second[key]['sha256'] = 'sha256:' + letter * 64
        second[key]['path'] = second[key]['path'].rsplit('/', 1)[0] + '/' + letter * 64 + suffix
    docs = {'first': first, 'second': second}
    selection = {k: copy.deepcopy(v) for k, v in old.items()
                 if k not in ('receipt_path', 'receipt_sha256', 'source_language', 'claims')}
    selection['version'] = '1.1.0'
    selection['documents'] = [{'id': key, 'source_language': 'en',
                               'receipt_path': doc['receipt_path'], 'receipt_sha256': doc['receipt_sha256']}
                              for key, doc in docs.items()]
    selection['claims'] = [{'section': 'function', 'statement': old['claims'][0]['statement'],
                            'anchors': [{'document_id': key, 'start': 9, 'end': len(doc['text']), 'quote': doc['text'][9:]}
                                        for key, doc in docs.items()]}]
    calls = []
    def reader(root, relative, *, expected_receipt_sha256):
        doc = next(d for d in docs.values() if d['receipt_path'] == relative)
        if expected_receipt_sha256 != doc['receipt_sha256']:
            raise ValueError('document_receipt_changed')
        calls.append(relative)
        return doc
    monkeypatch.setattr(document, 'load_reader', lambda root: reader)
    path.write_text(json.dumps(selection))
    return (raw, proposals, path, selection, first), docs, calls


def test_multiple_anchors_render_one_claim_without_asserting_independence(multi_lane):
    lane, docs, calls = multi_lane
    md, report = run(lane)
    fm, _ = author._split_fm(md)
    assert calls == [d['receipt_path'] for d in docs.values()]
    assert report['documents_selected'] == 2 and report['anchors_selected'] == 2
    assert report['claims_selected'] == 1
    block = fm['entity_data']['editorial']['function']
    assert block['source_ids'] == ['raw:' + d['extraction']['sha256'][7:] for d in docs.values()]
    assert block['content_md'] == lane[3]['claims'][0]['statement']
    assert len(fm['source_refs']) == 6
    assert {r['kind'] for r in fm['source_refs']} == {'raw'}
    assert fm['truth_level'] == 'L3' and not any(fm['exportable'].values())
    assert report['evidence']['independent_sources_verified'] is False
    for anchor in report['evidence']['claims'][0]['anchors']:
        doc = docs[anchor['document_id']]
        assert anchor['quote'] == doc['text'][anchor['start']:anchor['end']]
        assert anchor['quote_sha256'] == document.digest(anchor['quote'].encode())


def test_sources_belong_only_to_the_sections_they_support(multi_lane):
    lane, docs, _ = multi_lane
    selection = lane[3]
    claim = selection['claims'][0]
    second = copy.deepcopy(claim)
    second['section'] = 'variants'
    second['anchors'] = [claim['anchors'].pop()]
    selection['claims'].append(second)
    lane[2].write_text(json.dumps(selection))
    md, _ = run(lane)
    fm, _ = author._split_fm(md)
    ed = fm['entity_data']['editorial']
    assert ed['function']['source_ids'] == ['raw:' + docs['first']['extraction']['sha256'][7:]]
    assert ed['variants']['source_ids'] == ['raw:' + docs['second']['extraction']['sha256'][7:]]


@pytest.mark.parametrize('change,code', [
    ('unknown_reference', 'document_claim_reference_unknown'),
    ('duplicate_id', 'document_selection_duplicate_document'),
    ('receipt_alias', 'document_selection_duplicate_document'),
    ('duplicate_text', 'document_selection_duplicate_text'),
    ('unused', 'document_selection_unused_document'),
    ('duplicate_anchor', 'document_claim_duplicate'),
    ('wrong_quote', 'document_claim_anchor_invalid'),
    ('past_end', 'document_claim_anchor_invalid'),
    ('changed_receipt', 'document_receipt_changed'),
])
def test_multidocument_refusal_is_atomic(multi_lane, tmp_path, capsys, change, code):
    lane, docs, _ = multi_lane
    selection = lane[3]
    anchors = selection['claims'][0]['anchors']
    if change == 'unknown_reference': anchors[1]['document_id'] = 'absent'
    elif change == 'duplicate_id': selection['documents'][1]['id'] = 'first'
    elif change == 'receipt_alias': selection['documents'][1].update(selection['documents'][0], id='alias')
    elif change == 'duplicate_text': docs['second']['extraction'] = copy.deepcopy(docs['first']['extraction'])
    elif change == 'unused': anchors.pop()
    elif change == 'duplicate_anchor': anchors.append(copy.deepcopy(anchors[0]))
    elif change == 'wrong_quote': anchors[1]['quote'] += 'invented'
    elif change == 'past_end': anchors[1]['end'] += 1
    elif change == 'changed_receipt': selection['documents'][1]['receipt_sha256'] = 'sha256:' + '0' * 64
    lane[2].write_text(json.dumps(selection))
    output = tmp_path / 'refused.md'
    rc = author.main(['--slug', 'thermostat', '--raw-root', str(lane[0]), '--proposals-dir', str(lane[1]),
                      '--document-selection', str(lane[2]), '--out', str(output)])
    captured = capsys.readouterr()
    assert rc == 1 and not output.exists() and not captured.out
    assert json.loads(captured.err)['error_code'] == code


@pytest.mark.parametrize('change', ['version', 'mixed_v1', 'no_anchor', 'eleven_documents', 'confidence', 'independent'])
def test_multidocument_schema_refuses_ambiguous_or_self_approved_input(multi_lane, change):
    lane, _, _ = multi_lane
    selection = lane[3]
    if change == 'version': selection['version'] = '1.2.0'
    elif change == 'mixed_v1': selection['receipt_path'] = selection['documents'][0]['receipt_path']
    elif change == 'no_anchor': selection['claims'][0]['anchors'] = []
    elif change == 'eleven_documents': selection['documents'] *= 6
    elif change == 'confidence': selection['documents'][0]['confidence'] = 'high'
    elif change == 'independent': selection['documents'][0]['independent'] = True
    lane[2].write_text(json.dumps(selection))
    with pytest.raises(Exception): run(lane)


def test_reader_cannot_substitute_receipt_identity(lane, monkeypatch):
    original = copy.deepcopy(lane[4])
    original['receipt_sha256'] = 'sha256:' + '0' * 64
    monkeypatch.setattr(document, 'load_reader', lambda root: lambda *a, **kw: original)
    with pytest.raises(ValueError, match='document_reader_identity_mismatch'): run(lane)
