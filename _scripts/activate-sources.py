#!/usr/bin/env python3
"""Qualify then sign exact source activations. No push, promotion or policy override."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile

from activation_receipt import (CATALOG, RECEIPTS, activate_catalog, assert_clean, digest,
                                git, input_files, make_payload, run_cross_repo,
                                sign_payload, verify_activation)


def qualified_main(root, repo):
    assert_clean(root)
    if git(root, 'remote', 'get-url', 'origin') not in {
        f'https://github.com/{repo}.git', f'git@github.com:{repo}.git'
    }:
        raise ValueError('Unexpected qualification origin')
    ref = 'refs/activation/main'
    git(root, 'fetch', '--no-write-fetch-head', 'origin', f'refs/heads/main:{ref}')
    sha = git(root, 'rev-parse', ref)
    if git(root, 'rev-parse', 'HEAD') != sha:
        raise ValueError('Qualification must start on the clean, current main SHA')
    response = subprocess.run(['gh', 'api', f'repos/{repo}/commits/{sha}/check-runs?per_page=100'],
                              check=True, capture_output=True, text=True, timeout=60)
    checks = json.loads(response.stdout)['check_runs']
    latest = {}
    for check in sorted(checks, key=lambda item: item['id'], reverse=True):
        if check['head_sha'] == sha:
            latest.setdefault(check['name'], check)
    required = {'pre-commit (Python 3.11)', 'pre-commit (Python 3.12)'}
    if repo.endswith('-wiki'):
        required.add('Python quality gates (validate-frontmatter, quality-gates, compute-confidence-score)')
    if not required.issubset(latest) or any(latest[name]['conclusion'] != 'success' for name in required):
        raise ValueError('Required main CI is not successful')
    if any(c['status'] != 'completed' or c['conclusion'] not in {'success', 'neutral', 'skipped'} for c in latest.values()):
        raise ValueError('Main CI is incomplete or unsuccessful')
    return sha


def issue(root, raw, key, slugs):
    base = qualified_main(root, 'ak125/automecanik-wiki')
    raw_sha = qualified_main(raw, 'ak125/automecanik-raw')
    if key.is_symlink() or not key.is_file() or key.stat().st_uid != os.getuid() or key.stat().st_mode & 0o077:
        raise ValueError('Expected owner-only signing key')
    if key.resolve().is_relative_to(root.resolve()) or key.resolve().is_relative_to(raw.resolve()):
        raise ValueError('Signing key must remain outside repositories')
    files = input_files(root)
    original = files[CATALOG]
    candidate = activate_catalog(original.decode(), slugs).encode()
    with tempfile.TemporaryDirectory(prefix='wiki-activation-') as directory:
        snapshot = Path(directory)
        for name, content in files.items():
            dest = snapshot / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(candidate if name == CATALOG else content)
        output = run_cross_repo(snapshot, raw)
    # Recheck both exact bases and the RAW worktree after the gate, before signing.
    if qualified_main(root, 'ak125/automecanik-wiki') != base or qualified_main(raw, 'ak125/automecanik-raw') != raw_sha:
        raise ValueError('Main advanced during qualification; rerun on fresh bases')
    if input_files(root) != files:
        raise ValueError('WIKI inputs changed during qualification')
    payload = make_payload(root, base, raw_sha, output)
    planned = {**files, CATALOG: candidate}
    # Construct the payload from the verified temporary tree without touching the catalog.
    from activation_receipt import entries, transitions
    payload['input_digest'] = digest(planned)
    payload['transitions'] = transitions(entries(original.decode()), entries(candidate.decode()))
    receipt = sign_payload(payload, key)
    from activation_receipt import TRUST, verify_signature
    verify_signature(receipt, json.loads(git(root, 'show', f'{base}:{TRUST}')))
    path = root / RECEIPTS / (payload['input_digest'] + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError('Receipt already exists; preserve it')
    try:
        with path.open('x') as handle:
            json.dump(receipt, handle, ensure_ascii=True, indent=2)
            handle.write('\n')
        (root / CATALOG).write_bytes(candidate)
        verified = verify_activation(root, base)
        if verified != sorted(slugs):
            raise ValueError('Receipt covers unexpected transitions')
    except Exception:
        if (root / CATALOG).read_bytes() == candidate:
            (root / CATALOG).write_bytes(original)
        path.unlink(missing_ok=True)
        raise
    return {'wiki_base': base, 'raw_sha': raw_sha, 'activated': verified, 'receipt': str(path), 'gate_output': output}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-root', required=True, type=Path)
    parser.add_argument('--key', required=True, type=Path)
    parser.add_argument('--slugs', required=True, nargs='+')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    lock_path = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir')) / 'source-activation.lock'
    with lock_path.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(json.dumps(issue(root, args.raw_root, args.key, args.slugs), ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
