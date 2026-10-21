"""Offline verification of a native cross-repository qualification signed by an owner.

Trust is read from the Git base, never from the activating change. OpenSSH supplies
the signature primitive; no private RAW access or secret is needed by WIKI CI.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import yaml

CATALOG = '_meta/source-catalog.yaml'
TRUST = '_meta/source-activation-trust.json'
RECEIPTS = '_audit/source-activations'
PRINCIPAL = 'source-activation'
NAMESPACE = 'source-activation@automecanik.com'
GATE = ['quality-gates.py', '--cross-repo']
# Fields that give an active source its authority: the RAW proof (raw_ref), the role and
# confidence ceiling (type) and the identity counted for proof independence (publisher).
AUTHORITY_FIELDS = ('raw_ref', 'type', 'publisher')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError('Git verification failed: ' + ' '.join(args[:2]))
    return result.stdout.strip()


def entries(text):
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or not isinstance(data.get('sources'), list):
        raise ValueError('Invalid source catalog')
    result = {}
    for row in data['sources']:
        if not isinstance(row, dict) or not isinstance(row.get('slug'), str) or row['slug'] in result:
            raise ValueError('Invalid or duplicate source slug')
        result[row['slug']] = row
    return result


def requalified_fields(before, after):
    """Authority fields set or changed on a row; removing one creates no authority."""
    return [field for field in AUTHORITY_FIELDS
            if after.get(field) and after.get(field) != before.get(field)]


def transitions(before, after):
    return {slug: {'before': before.get(slug), 'after': row}
            for slug, row in after.items()
            if row.get('status', 'active') == 'active' and
            (slug not in before or before[slug].get('status', 'active') != 'active' or
             requalified_fields(before[slug], row))}


def input_files(root):
    names = git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0')
    result = {}
    for name in sorted(set(names)):
        if not name or name.startswith(RECEIPTS + '/'):
            continue
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Missing, external or symlink qualification input: ' + name)
        result[name] = path.read_bytes()
    return result


def digest(files):
    return hashlib.sha256(canonical({name: hashlib.sha256(content).hexdigest()
                                     for name, content in files.items()})).hexdigest()


def make_payload(root, base, raw_sha, gate_output):
    base = git(root, 'rev-parse', '--verify', base + '^{commit}')
    before = entries(git(root, 'show', f'{base}:{CATALOG}'))
    after = entries((root / CATALOG).read_text())
    return {'version': 1, 'wiki_base': base, 'raw_repo': 'ak125/automecanik-raw',
            'raw_sha': raw_sha, 'input_digest': digest(input_files(root)),
            'transitions': transitions(before, after), 'gate': GATE,
            'gate_output': gate_output, 'gate_returncode': 0}


def sign_payload(payload, key):
    result = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', NAMESPACE],
                            input=canonical(payload), capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError('Activation receipt signing failed')
    return {'payload': payload, 'signature': result.stdout.decode('ascii')}


def verify_signature(receipt, trust):
    if trust.get('principal') != PRINCIPAL or not trust.get('keys'):
        raise ValueError('Missing trusted activation signers in base')
    lines = []
    for key in trust['keys']:
        if not isinstance(key, str) or not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+(?: [^\r\n]*)?', key):
            raise ValueError('Invalid trusted activation key')
        lines.append(f'{PRINCIPAL} namespaces="{NAMESPACE}" {key}')
    with tempfile.TemporaryDirectory(prefix='wiki-receipt-') as folder:
        signers = Path(folder) / 'allowed'
        signature = Path(folder) / 'signature'
        signers.write_text('\n'.join(lines) + '\n')
        signature.write_text(receipt['signature'])
        result = subprocess.run(['ssh-keygen', '-Y', 'verify', '-f', str(signers),
                                 '-I', PRINCIPAL, '-n', NAMESPACE, '-s', str(signature)],
                                input=canonical(receipt['payload']), capture_output=True, timeout=30)
        if result.returncode:
            raise ValueError('Activation receipt signature not trusted')


def verify_activation(root, base):
    """Return precisely the transitions authorized by one intact, trusted receipt."""
    base = git(root, 'rev-parse', '--verify', base + '^{commit}')
    trust = json.loads(git(root, 'show', f'{base}:{TRUST}'))
    expected = make_payload(root, base, '', '')
    if not expected['transitions']:
        raise ValueError('No activation to qualify')
    for path in sorted((root / RECEIPTS).glob('*.json')):
        try:
            if path.is_symlink() or path.stat().st_size > 1024 * 1024:
                continue
            receipt = json.loads(path.read_text())
            payload = receipt['payload']
            for field in ('version', 'wiki_base', 'raw_repo', 'input_digest', 'transitions', 'gate', 'gate_returncode'):
                if payload[field] != expected[field]:
                    raise ValueError('Stale or mismatched activation receipt')
            if not re.fullmatch('[0-9a-f]{40}', payload['raw_sha']) or not payload['gate_output']:
                raise ValueError('Missing RAW or gate evidence')
            verify_signature(receipt, trust)
            return sorted(payload['transitions'])
        except (KeyError, ValueError, TypeError, OSError, subprocess.SubprocessError):
            continue
    raise ValueError('No valid signed receipt for the exact activation and inputs')


def activate_catalog(text, slugs):
    catalog = entries(text)
    if not slugs or len(set(slugs)) != len(slugs):
        raise ValueError('Expected distinct requested source slugs')
    for slug in slugs:
        if slug not in catalog or catalog[slug].get('status') != 'to_capture' or not catalog[slug].get('raw_ref'):
            raise ValueError('Source is not a captured inactive entry: ' + slug)
    document = yaml.compose(text)
    sources = next(value for key, value in document.value if key.value == 'sources')
    edits = []
    for row in sources.value:
        fields = {key.value: value for key, value in row.value}
        if fields['slug'].value in slugs:
            value = fields['status']
            edits.append((value.start_mark.index, value.end_mark.index))
    for start, end in sorted(edits, reverse=True):
        text = text[:start] + 'active' + text[end:]
    return text


def assert_clean(root):
    if root.is_symlink() or Path(git(root, 'rev-parse', '--show-toplevel')).resolve() != root.resolve():
        raise ValueError('Unexpected repository root')
    if git(root, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Pending repository changes must be preserved')


def run_cross_repo(wiki, raw):
    env = {key: value for key, value in os.environ.items()
           if key in {'HOME', 'PATH', 'LANG', 'LC_ALL'}}
    env.update({'AUTOMECANIK_RAW_PATH': str(raw.resolve()), 'PYTHONDONTWRITEBYTECODE': '1'})
    result = subprocess.run(['python3', '-B', str(wiki / '_scripts/quality-gates.py'), '--cross-repo'],
                            cwd=wiki, env=env, capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise ValueError('Native cross-repo gate failed: ' + (result.stdout + result.stderr)[-4000:])
    return result.stdout + result.stderr
