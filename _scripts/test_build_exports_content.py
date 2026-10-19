"""Content admission: synthetic fixtures, never real automotive evidence."""
import copy
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

def frontmatter():
    return json.loads((ROOT / "_meta/schema/frontmatter.schema.json").read_text())

def selector_valid(value):
    schema = frontmatter()
    # Exercise the complete frontmatter contract using an existing valid fiche.
    import yaml
    text = (ROOT / "wiki/gamme/filtre-a-huile.md").read_text()
    fm = yaml.safe_load(text.split("---", 2)[1])
    fm["exportable"]["content"] = True
    fm.pop("content_export", None)
    if value is not None:
        fm["content_export"] = value
    # Existing entity refs are orthogonal; their validation is covered by native suites.
    schema["properties"].pop("entity_data", None)
    schema["additionalProperties"] = True
    return list(Draft202012Validator(schema).iter_errors(fm))

@pytest.mark.parametrize("selector", [None, {"consumer":"seo","sections":["function"]},
    {"consumer":"fafa","sections":[]}, {"consumer":"fafa","sections":["function","function"]}])
def test_content_requires_explicit_fafa_sections(selector):
    assert selector_valid(selector)

def test_content_selector_accepted():
    assert not selector_valid({"consumer":"fafa","sections":["function"]})

def test_content_export_schema_is_strict():
    schema_path = ROOT / "_meta/schema/exports-content.schema.json"
    assert schema_path.is_file(), "Native export and admission contract missing"
    schema = json.loads(schema_path.read_text())
    assert list(Draft202012Validator(schema).iter_errors({"consumer":"fafa"}))

import hashlib
import importlib
import shutil
import subprocess
import sys
import yaml

TEXT = "Cette section est une preuve synthetique pour tester le raccordement et ne donne aucun conseil automobile."

def git(root, *args):
    return subprocess.check_output(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args], cwd=root, text=True).strip()

def make_fixture(tmp_path):
    root = tmp_path / "wiki-repo"
    root.mkdir()
    shutil.copytree(ROOT / "_scripts", root / "_scripts", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "_meta/schema", root / "_meta/schema")
    raw = tmp_path / "raw"
    (raw / "sources").mkdir(parents=True)
    (raw / "manifests").mkdir()
    (raw / "sources/proof.md").write_text(TEXT)
    digest = "sha256:" + hashlib.sha256(TEXT.encode()).hexdigest()
    (raw / "manifests/source-inventory.csv").write_text("manifest_id,path,sha256\nsrc-proof,sources/proof.md," + digest + "\n")
    (raw / "manifests/checksums.json").write_text(json.dumps({"sources/proof.md":digest}))
    (root / "_meta/source-catalog.yaml").write_text(yaml.safe_dump({"source_type_max_confidence":{"oem_manual":"high"},"source_type_editorial_role":{"oem_manual":"proof"},"sources":[{"slug":"source_test","type":"oem_manual","status":"active","raw_ref":{"repo":"automecanik-raw","manifest_id":"src-proof","expected_sha256":digest}}]}))
    (root / "_meta/entity-registry.json").write_text("{}")
    fm = dict(schema_version="2.0.0",id="gamme:fixture-content",entity_type="gamme",slug="fixture-content",title="Fixture content",lang="fr",created_at="2026-10-18",updated_at="2026-10-18",truth_level="L1",review_status="approved",reviewed_by="fixture",reviewed_at="2026-10-18",no_disputed_claims=True,
        exportable=dict(rag=False,seo=False,support=False,content=True), content_export=dict(consumer="fafa",sections=["function"]),
        source_refs=[dict(kind="raw",path="sources/proof.md",confidence="high"),dict(kind="external_url",url="https://example.invalid/fixture",captured_at="2026-10-18",confidence="high")],
        entity_data=dict(pg_id=1,family="filtration",editorial={"function":dict(content_md=TEXT,source_ids=["oem:source_test"],truth_level="sourced")}))
    heads = ["D\u00e9finition","Fonctionnement","Sympt\u00f4mes d'usure","Choix selon v\u00e9hicule","FAQ"]
    body = "\n".join("## " + h + "\n" + TEXT for h in heads) + "\n[[fixture-related]]\n"
    source=root / "wiki/gamme/fixture-content.md";source.parent.mkdir(parents=True)
    source.write_text("---\n"+yaml.safe_dump(fm,allow_unicode=True)+"---\n"+body)
    (source.parent / "fixture-related.md").write_text("---\nentity_type: gamme\nslug: fixture-related\n---\nFixture related")
    cov=root / "proposals/_coverage";cov.mkdir(parents=True)
    entries=[dict(claim_id="fixture-"+str(i),section="## "+h,text_anchor=TEXT,source_slug="source_test",evidence_type="oem_technical_page",confidence="high",source_policy="1_high",source_status="captured") for i,h in enumerate(heads)]
    (cov / "fixture-content.coverage.yaml").write_text(yaml.safe_dump(dict(fiche="fixture-content",schema_version="1.0.0",coverage_entries=entries),allow_unicode=True))
    git(root,"init","-q","-b","main");git(root,"add",".");git(root,"commit","-qm","Synthetic fixture only")
    origin=tmp_path / "origin.git";git(root,"clone","--bare","-q",str(root),str(origin));git(root,"remote","add","origin",str(origin))
    return root,raw,source

def builder():
    assert (ROOT / "_scripts/build_exports_content.py").is_file(), "Native builder missing"
    return importlib.import_module("build_exports_content")

def native(root,raw,*args,input=None):
    return subprocess.run([sys.executable,"-B",str(root / "_scripts/build_exports_content.py"),"--wiki-root",str(root),"--raw-root",str(raw),*args],input=input,text=True,capture_output=True)

def test_native_decision_and_real_export(tmp_path):
    builder()
    root,raw,source=make_fixture(tmp_path)
    out=native(root,raw)
    assert out.returncode == 0, out.stderr
    exported=root / "exports/content/gamme/fixture-content.json"
    payload=json.loads(exported.read_text())
    assert payload["sections"][0]["content_md"] == TEXT
    assert payload["decision"]["promotion_status"] == "ELIGIBLE"
    before=exported.read_bytes()
    assert native(root,raw,"--check").returncode == 0
    assert native(root,raw).returncode == 0
    assert exported.read_bytes() == before

@pytest.mark.parametrize("change,code", [
    ("audience","AUDIENCE_NOT_ALLOWED"),("unapproved","SOURCE_NOT_APPROVED"),
    ("unknown-section","SECTION_NOT_FOUND"),("unsourced","CANONICAL_DECISION_BLOCKED"),
    ("uncovered-editorial","CANONICAL_DECISION_BLOCKED"),("dirty","REFERENCE_MISMATCH"),
    ("native-block","CANONICAL_DECISION_BLOCKED")])
def test_content_cannot_bypass_native_controls(tmp_path,change,code):
    mod=builder();root,raw,source=make_fixture(tmp_path)
    fm,body=mod.promotion._parse_markdown(source)
    if change=="audience":fm["content_export"]["consumer"]="seo"
    elif change=="unapproved":fm["review_status"]="in_review"
    elif change=="unknown-section":fm["content_export"]["sections"]=["unknown"]
    elif change=="unsourced":fm["entity_data"]["editorial"]["function"]["source_ids"]=[]
    elif change=="uncovered-editorial":fm["entity_data"]["editorial"]["function"]["content_md"]=TEXT+" Extra claim."
    elif change=="native-block":fm["truth_level"]="L4"
    elif change=="dirty":body+="\nChanged"
    source.write_text("---\n"+yaml.safe_dump(fm,allow_unicode=True)+"---\n"+body)
    if change!="dirty":git(root,"add",".");git(root,"commit","-qm","Fixture mutation")
    with pytest.raises(mod.AdmissionError) as error: mod.build_content_export(source,root,raw_root=raw)
    assert error.value.code == code

def request_for(root):
    file=root / "exports/content/gamme/fixture-content.json";b=file.read_bytes();e=json.loads(b);s=e["sections"][0]
    return dict(schema_version="1.0.0",request_id="fixture-request",consumer="fafa",references=[dict(doc_id="synthetic-wiki",export_path="exports/content/gamme/fixture-content.json",export_sha256=hashlib.sha256(b).hexdigest(),wiki_path=e["wiki_path"],source_wiki_commit=e["source_wiki_commit"],section=s["section"],section_sha256=s["sha256"],excerpt=s["content_md"])])

@pytest.mark.parametrize("mutation,want",[("none","ADMITTED"),("excerpt","REFERENCE_MISMATCH"),("hash","REFERENCE_MISMATCH"),("section","SECTION_NOT_FOUND"),("source","STALE_EXPORT"),("retract","AUDIENCE_NOT_ALLOWED"),("remote","AUTHORITY_NOT_CURRENT"),("outage","AUTHORITY_UNAVAILABLE"),("escape","REFERENCE_MISMATCH")])
def test_resolver_binds_exact_current_export(tmp_path,mutation,want):
    builder();root,raw,source=make_fixture(tmp_path)
    out=native(root,raw);assert out.returncode==0,out.stderr
    req=request_for(root);ref=req["references"][0]
    if mutation=="excerpt":ref["excerpt"]+=" forged"
    if mutation=="hash":ref["export_sha256"]="0"*64
    if mutation=="section":ref["section"]="faq"
    if mutation in {"source","retract"}:
        text=source.read_text();source.write_text(text.replace("content: true","content: false") if mutation=="retract" else text+"\nChanged fixture")
        git(root,"add",".");git(root,"commit","-qm","Fixture change");git(root,"push","-q","origin","main")
    if mutation=="remote":git(root,"commit","--allow-empty","-qm","Local divergence")
    if mutation=="outage":git(root,"remote","set-url","origin",str(tmp_path / "absent.git"))
    if mutation=="escape":
        f=root / ref["export_path"];other=tmp_path / "export.json";shutil.copyfile(f,other);f.unlink();f.symlink_to(other)
    out=native(root,raw,"--resolve-stdin",input=json.dumps(req))
    assert out.returncode == (0 if want=="ADMITTED" else 2),out.stderr
    answer=json.loads(out.stdout);assert answer["results"][0]["code"]==want,answer
    assert answer["request_id"]==req["request_id"]

def test_unreconciled_export_preserved_and_rejected(tmp_path):
    builder();root,raw,source=make_fixture(tmp_path)
    out=native(root,raw);assert out.returncode==0,out.stderr
    exported=root / "exports/content/gamme/fixture-content.json";before=exported.read_bytes()
    source.write_text(source.read_text().replace("content: true","content: false"));git(root,"add",".");git(root,"commit","-qm","Retire fixture")
    out=native(root,raw,"--check")
    assert out.returncode!=0 and "UNRECONCILED_EXPORT" in out.stderr
    assert exported.read_bytes()==before

def test_duplicate_protocol_rejected(tmp_path):
    builder();root,raw,_=make_fixture(tmp_path)
    out=native(root,raw,"--resolve-stdin",input='{"request_id":"a","request_id":"b"}')
    assert out.returncode==1

@pytest.mark.parametrize("target",["source","schema","export","catalog"])
def test_change_during_resolution_blocks(tmp_path,monkeypatch,target):
    mod=builder();root,raw,source=make_fixture(tmp_path)
    out=native(root,raw);assert out.returncode==0,out.stderr
    req=request_for(root)
    original=mod._build
    def change(*args):
        result=original(*args)
        file={"source":source,"schema":root/mod.SCHEMA,"export":root/req["references"][0]["export_path"],"catalog":root/mod.CATALOG_REL}[target]
        file.write_bytes(file.read_bytes()+b"\n")
        return result
    monkeypatch.setattr(mod,"_build",change)
    response=mod.resolve(req,root,raw)
    assert response["results"][0]["code"]=="AUTHORITY_INPUT_CHANGED",response

@pytest.mark.parametrize("change",["duplicate","extra","missing"])
def test_request_protocol_is_strict(tmp_path,change):
    builder();root,raw,_=make_fixture(tmp_path)
    assert native(root,raw).returncode==0
    req=request_for(root)
    if change=="duplicate":req["references"]*=2
    elif change=="extra":req["command"]="forbidden"
    else:del req["request_id"]
    out=native(root,raw,"--resolve-stdin",input=json.dumps(req))
    assert out.returncode==1

def test_dirty_catalog_and_wrong_source_commit_rejected(tmp_path):
    mod=builder();root,raw,source=make_fixture(tmp_path)
    assert native(root,raw).returncode==0
    req=request_for(root);req["references"][0]["source_wiki_commit"]="0"*40
    out=native(root,raw,"--resolve-stdin",input=json.dumps(req))
    assert json.loads(out.stdout)["results"][0]["code"]=="REFERENCE_MISMATCH"
    catalog=root/mod.CATALOG_REL;catalog.write_bytes(catalog.read_bytes()+b"\n")
    with pytest.raises(mod.AdmissionError,match="REFERENCE_MISMATCH"):
        mod.build_content_export(source,root,raw_root=raw)

def test_source_change_before_native_snapshot_cannot_mix_versions(tmp_path,monkeypatch):
    mod=builder();root,raw,source=make_fixture(tmp_path)
    original=mod.promotion.canonical_promotion_decision
    def change(*args,**kwargs):
        source.write_bytes(source.read_bytes()+b"\n")
        return original(*args,**kwargs)
    monkeypatch.setattr(mod.promotion,"canonical_promotion_decision",change)
    with pytest.raises(mod.AdmissionError,match="AUTHORITY_INPUT_CHANGED"):
        mod.build_content_export(source,root,raw_root=raw)

def test_cli_refuses_other_checkout_as_authority(tmp_path):
    builder();root,raw,_=make_fixture(tmp_path)
    out=subprocess.run([sys.executable,"-B",str(ROOT/"_scripts/build_exports_content.py"),"--wiki-root",str(root),"--raw-root",str(raw)],capture_output=True,text=True)
    assert out.returncode==1 and "AUTHORITY_ROOT_MISMATCH" in out.stderr
    assert not (root/"exports/content").exists()
