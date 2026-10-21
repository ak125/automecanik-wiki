"""Real signatures and Git bases: no fabricated acceptance from mocks."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import activation_receipt as ar


def producer():
    spec = importlib.util.spec_from_file_location('activation_producer_test', Path(__file__).resolve().parents[1] / 'activate-sources.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cmd(root, *args):
    return subprocess.run(args, cwd=root, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / 'wiki'
    root.mkdir()
    cmd(root, 'git', 'init', '-q')
    cmd(root, 'git', 'config', 'user.email', 'test@example.invalid')
    cmd(root, 'git', 'config', 'user.name', 'Test')
    (root / '_meta').mkdir()
    (root / '_scripts').mkdir()
    (root / 'wiki').mkdir()
    (root / 'wiki/claim.md').write_text('Original anchored claim\n')
    (root / '_scripts/quality-gates.py').write_text('native gate baseline\n')
    key = tmp_path / 'key'
    cmd(root, 'ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key))
    (root / ar.TRUST).write_text(json.dumps({'principal': ar.PRINCIPAL, 'keys': [Path(str(key)+'.pub').read_text().strip()]}))
    sources = {'sources': [{'slug': 's', 'status': 'to_capture', 'raw_ref': {'repo': 'automecanik-raw', 'manifest_id': 'm', 'expected_sha256': 'sha256:'+'a'*64}}]}
    (root / ar.CATALOG).write_text(yaml.safe_dump(sources))
    cmd(root, 'git', 'add', '.')
    cmd(root, 'git', 'commit', '-qm', 'base')
    base = cmd(root, 'git', 'rev-parse', 'HEAD')
    sources['sources'][0]['status'] = 'active'
    (root / ar.CATALOG).write_text(yaml.safe_dump(sources))
    payload = ar.make_payload(root, base, 'b'*40, 'PASS cross-repo\n')
    receipt = ar.sign_payload(payload, key)
    path = root / ar.RECEIPTS / 'activation.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(receipt))
    return root, base, key, path


def test_real_signature_and_exact_tree_accepted(tree):
    root, base, _, _ = tree
    assert ar.verify_activation(root, base) == ['s']


def test_guard_accepts_only_signed_activation(tree, monkeypatch):
    root, base, _, path = tree
    spec = importlib.util.spec_from_file_location('guard_receipt_test', Path(__file__).resolve().parents[1] / 'check-activation-guard.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    monkeypatch.setattr(guard, 'REPO_ROOT', root)
    monkeypatch.setattr(guard, 'CATALOG', root / ar.CATALOG)
    monkeypatch.setattr(sys, 'argv', ['guard', '--base', base])
    assert guard.main() == 0
    path.unlink()
    assert guard.main() == 1


@pytest.mark.parametrize('mutation', ['signature', 'payload', 'catalog', 'anchor', 'code', 'untracked', 'missing'])
def test_tamper_or_missing_proof_is_rejected(tree, mutation):
    root, base, _, path = tree
    if mutation in ('signature', 'payload'):
        receipt = json.loads(path.read_text())
        if mutation == 'signature':
            receipt['signature'] = 'invalid'
        else:
            receipt['payload']['raw_sha'] = 'c'*40
        path.write_text(json.dumps(receipt))
    elif mutation == 'catalog':
        with (root / ar.CATALOG).open('a') as stream:
            stream.write('\n# changed after qualification\n')
    elif mutation == 'anchor':
        (root / 'wiki/claim.md').write_text('Changed anchored claim\n')
    elif mutation == 'code':
        (root / '_scripts/quality-gates.py').write_text('changed validator\n')
    elif mutation == 'untracked':
        (root / 'wiki/new.md').write_text('extra claim\n')
    else:
        path.unlink()
    with pytest.raises(ValueError):
        ar.verify_activation(root, base)


def test_new_key_in_current_tree_cannot_authorize_itself(tree, tmp_path):
    root, base, _, path = tree
    key = tmp_path / 'untrusted'
    cmd(root, 'ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key))
    (root / ar.TRUST).write_text(json.dumps({'principal': ar.PRINCIPAL, 'keys': [Path(str(key)+'.pub').read_text().strip()]}))
    path.write_text(json.dumps(ar.sign_payload(ar.make_payload(root, base, 'b'*40, 'PASS\n'), key)))
    with pytest.raises(ValueError):
        ar.verify_activation(root, base)


def test_other_source_not_covered_by_receipt_is_rejected(tree):
    root, base, _, _ = tree
    catalog = yaml.safe_load((root / ar.CATALOG).read_text())
    catalog['sources'].append({'slug': 'other', 'status': 'active'})
    (root / ar.CATALOG).write_text(yaml.safe_dump(catalog))
    with pytest.raises(ValueError):
        ar.verify_activation(root, base)


def test_receipt_must_cover_requalification_of_active_source(tree):
    # A signed activation of `s` does not carry a retype of the already-active `p`.
    root, _, key, path = tree
    path.unlink()
    catalog = yaml.safe_load(cmd(root, 'git', 'show', 'HEAD:' + ar.CATALOG))
    catalog['sources'].append({'slug': 'p', 'status': 'active', 'type': 'brochure', 'publisher': 'A',
                               'raw_ref': {'repo': 'automecanik-raw', 'manifest_id': 'p',
                                           'expected_sha256': 'sha256:' + 'c'*64}})
    (root / ar.CATALOG).write_text(yaml.safe_dump(catalog))
    cmd(root, 'git', 'commit', '-qam', 'active corroboration')
    base = cmd(root, 'git', 'rev-parse', 'HEAD')
    catalog['sources'][0]['status'] = 'active'
    catalog['sources'][1]['type'] = 'oem_workshop'
    (root / ar.CATALOG).write_text(yaml.safe_dump(catalog))
    payload = ar.make_payload(root, base, 'b'*40, 'PASS cross-repo\n')
    assert sorted(payload['transitions']) == ['p', 's']
    assert payload['transitions']['p']['before']['type'] == 'brochure'
    partial = {**payload, 'transitions': {'s': payload['transitions']['s']}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ar.sign_payload(partial, key)))
    with pytest.raises(ValueError):
        ar.verify_activation(root, base)
    path.write_text(json.dumps(ar.sign_payload(payload, key)))
    assert ar.verify_activation(root, base) == ['p', 's']


def test_nonexistent_and_later_bases_rejected(tree):
    root, base, _, _ = tree
    with pytest.raises(ValueError):
        ar.verify_activation(root, '0'*40)
    cmd(root, 'git', 'commit', '--allow-empty', '-qm', 'later base')
    later = cmd(root, 'git', 'rev-parse', 'HEAD')
    assert later != base
    with pytest.raises(ValueError):
        ar.verify_activation(root, later)


def test_failed_native_gate_does_not_change_catalog(tree, tmp_path):
    root, _, _, _ = tree
    before = (root / ar.CATALOG).read_bytes()
    (root / '_scripts/quality-gates.py').write_text('raise SystemExit(1)\n')
    with pytest.raises(ValueError, match='cross-repo'):
        ar.run_cross_repo(root, tmp_path)
    assert (root / ar.CATALOG).read_bytes() == before


def test_catalog_duplicate_slug_and_unrequested_status_rejected():
    with pytest.raises(ValueError):
        ar.activate_catalog('sources:\n- {slug: s, status: to_capture}\n- {slug: s, status: to_capture}\n', ['s'])
    with pytest.raises(ValueError):
        ar.activate_catalog('sources:\n- {slug: s, status: active}\n', ['s'])


def test_catalog_edit_preserves_every_other_byte():
    source = '# comment\nsources:\n  - slug: s\n    status: to_capture # pending\n    raw_ref: {repo: automecanik-raw}\n'
    assert ar.activate_catalog(source, ['s']) == source.replace('to_capture', 'active')


def test_untrusted_receipt_cannot_be_issued_from_changed_raw(tree, tmp_path):
    raw = tmp_path / 'raw'
    raw.mkdir()
    cmd(raw, 'git', 'init', '-q')
    (raw / 'data').write_text('uncommitted data')
    with pytest.raises(ValueError):
        ar.assert_clean(raw)


@pytest.mark.parametrize('case', ['success', 'gate_fail', 'raw_changes', 'untrusted_key'])
def test_producer_signs_only_after_success_and_preserves_failed_inputs(tree, tmp_path, monkeypatch, case):
    root, _, key, receipt = tree
    receipt.unlink()
    cmd(root, 'git', 'checkout', '--', ar.CATALOG)
    gate = 'print("PASS cross-repo")\n' if case != 'gate_fail' else 'raise SystemExit(1)\n'
    (root / '_scripts/quality-gates.py').write_text(gate)
    cmd(root, 'git', 'add', '.')
    cmd(root, 'git', 'commit', '-qm', 'gate fixture')
    raw = tmp_path / 'raw'
    raw.mkdir()
    cmd(raw, 'git', 'init', '-q')
    cmd(raw, 'git', 'config', 'user.email', 'test@example.invalid')
    cmd(raw, 'git', 'config', 'user.name', 'Test')
    (raw / 'data').write_text('captured archive')
    cmd(raw, 'git', 'add', '.')
    cmd(raw, 'git', 'commit', '-qm', 'capture')
    module = producer()
    def qualify(folder, repo):
        ar.assert_clean(folder)
        return ar.git(folder, 'rev-parse', 'HEAD')
    monkeypatch.setattr(module, 'qualified_main', qualify)
    if case == 'raw_changes':
        native = module.run_cross_repo
        def changed(wiki, raw_root):
            output = native(wiki, raw_root)
            (raw_root / 'data').write_text('concurrent change')
            return output
        monkeypatch.setattr(module, 'run_cross_repo', changed)
    if case == 'untrusted_key':
        key = tmp_path / 'wrong-key'
        cmd(root, 'ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key))
    before = ar.input_files(root)
    if case == 'success':
        result = module.issue(root, raw, key, ['s'])
        assert result['activated'] == ['s']
        assert ar.verify_activation(root, result['wiki_base']) == ['s']
        changed_paths = cmd(root, 'git', 'diff', '--name-only').splitlines()
        assert changed_paths == [ar.CATALOG]
    else:
        with pytest.raises(ValueError):
            module.issue(root, raw, key, ['s'])
        assert ar.input_files(root) == before
        assert list((root / ar.RECEIPTS).glob('*.json')) == []


@pytest.mark.parametrize('case', ['success', 'missing', 'failed', 'running', 'wrong_sha'])
def test_qualification_requires_fresh_sha_and_completed_ci(tree, monkeypatch, case):
    root, base, _, receipt = tree
    receipt.unlink()
    cmd(root, 'git', 'checkout', '--', ar.CATALOG)
    cmd(root, 'git', 'remote', 'add', 'origin', 'https://github.com/ak125/automecanik-raw.git')
    cmd(root, 'git', 'update-ref', 'refs/activation/main', base)
    module = producer()
    actual_git = module.git
    monkeypatch.setattr(module, 'git', lambda folder, *args: '' if args[0] == 'fetch' else actual_git(folder, *args))
    checks = [{'id': n, 'name': name, 'head_sha': base, 'status': 'completed', 'conclusion': 'success'}
              for n, name in enumerate(['pre-commit (Python 3.11)', 'pre-commit (Python 3.12)'])]
    if case == 'missing':
        checks.pop()
    elif case == 'failed':
        checks[0]['conclusion'] = 'failure'
    elif case == 'running':
        checks[0]['status'] = 'in_progress'
    elif case == 'wrong_sha':
        checks[0]['head_sha'] = '0'*40
    actual_run = subprocess.run
    def response(args, **kwargs):
        if args[0] == 'gh':
            return subprocess.CompletedProcess(args, 0, json.dumps({'check_runs': checks}), '')
        return actual_run(args, **kwargs)
    monkeypatch.setattr(subprocess, 'run', response)
    if case == 'success':
        assert module.qualified_main(root, 'ak125/automecanik-raw') == base
    else:
        with pytest.raises(ValueError):
            module.qualified_main(root, 'ak125/automecanik-raw')
