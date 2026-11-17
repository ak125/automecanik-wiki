#!/usr/bin/env bash
# check-aec-hash.sh — verify _meta/agent-exit-contract.md matches the distribution_sha256
# published by ak125/nestjs-remix-monorepo in
# .spec/00-canon/canon-distribution/canon-hashes.json (key `aec`), read on `main`.
#
# Used by .github/workflows/agent-exit-contract-hash.yml. Can run locally.
#
# The monorepo is public: no dedicated token is needed. `gh api` is preferred because it
# reads `main` without the CDN cache of the raw URL; curl on the raw URL is the fallback
# when `gh` is absent.
#
# Source of truth: AEC §"Distribution canonique". Until 2026-11-17 the manifest was read
# from ak125/governance-vault, now a read-only archive (owner decisions 72 and 73).

set -euo pipefail

LOCAL_COPY="_meta/agent-exit-contract.md"
CANON_REPO="ak125/nestjs-remix-monorepo"
CANON_MANIFEST=".spec/00-canon/canon-distribution/canon-hashes.json"
CANON_HASHES_URL="https://raw.githubusercontent.com/${CANON_REPO}/main/${CANON_MANIFEST}"

if [[ ! -f "${LOCAL_COPY}" ]]; then
  echo "ERROR: ${LOCAL_COPY} missing in this repo" >&2
  exit 1
fi

local_sha=$(sha256sum "${LOCAL_COPY}" | awk '{print $1}')

if command -v gh >/dev/null 2>&1; then
  manifest_origin="gh api repos/${CANON_REPO}/contents/${CANON_MANIFEST}"
  canon_json=$(gh api "repos/${CANON_REPO}/contents/${CANON_MANIFEST}" --jq '.content' | base64 -d)
else
  manifest_origin="${CANON_HASHES_URL}"
  canon_json=$(curl -fsSL "${CANON_HASHES_URL}")
fi
echo "Manifest read from: ${manifest_origin}"

canon_sha=$(printf '%s' "${canon_json}" | python3 -c "import json,sys; print(json.load(sys.stdin)['canons']['aec']['distribution_sha256'])")

if [[ ! "${canon_sha}" =~ ^[0-9a-f]{64}$ ]]; then
  echo "::error::aec.distribution_sha256 read from ${CANON_REPO} is not a SHA-256: '${canon_sha}'" >&2
  exit 1
fi

if [[ "${local_sha}" != "${canon_sha}" ]]; then
  echo "::error::AEC distribution drift" >&2
  echo "  local     ${LOCAL_COPY}: ${local_sha}" >&2
  echo "  monorepo  aec.distribution_sha256: ${canon_sha}" >&2
  echo "Resync: copy .claude/canon-mirrors/agent-exit-contract.md from ${CANON_REPO} (main) to ${LOCAL_COPY}, byte for byte, in a PR." >&2
  exit 1
fi

echo "OK — ${LOCAL_COPY} matches ${CANON_REPO} canon-hashes.json aec.distribution_sha256 (${canon_sha})"
