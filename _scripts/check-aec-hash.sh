#!/usr/bin/env bash
# check-aec-hash.sh — verify _meta/agent-exit-contract.md matches the distribution_sha256
# published by ak125/governance-vault in 99-meta/canon-hashes.json (key `aec`).
#
# Used by .github/workflows/agent-exit-contract-hash.yml. Can run locally — needs `gh` auth
# OR a public raw URL fetch (default).
#
# Source of truth: rules-agent-exit-contract.md §"Distribution canonique".

set -euo pipefail

LOCAL_COPY="_meta/agent-exit-contract.md"
CANON_HASHES_URL="https://raw.githubusercontent.com/ak125/governance-vault/main/99-meta/canon-hashes.json"

if [[ ! -f "${LOCAL_COPY}" ]]; then
  echo "ERROR: ${LOCAL_COPY} missing in this repo" >&2
  exit 1
fi

local_sha=$(sha256sum "${LOCAL_COPY}" | awk '{print $1}')

# Vault is private — `gh api` is the reliable fetch path. Fall back to curl raw if `gh` absent.
if command -v gh >/dev/null 2>&1; then
  canon_json=$(gh api repos/ak125/governance-vault/contents/99-meta/canon-hashes.json --jq '.content' | base64 -d)
else
  canon_json=$(curl -fsSL "${CANON_HASHES_URL}")
fi

vault_sha=$(printf '%s' "${canon_json}" | python3 -c "import json,sys; print(json.load(sys.stdin)['canons']['aec']['distribution_sha256'])")

if [[ "${local_sha}" != "${vault_sha}" ]]; then
  echo "::error::AEC distribution drift" >&2
  echo "  local  ${LOCAL_COPY}: ${local_sha}" >&2
  echo "  vault  aec.distribution_sha256:    ${vault_sha}" >&2
  echo "Resync: copy ledger/rules/rules-agent-exit-contract.md from the vault, strip frontmatter, write to ${LOCAL_COPY}." >&2
  exit 1
fi

echo "OK — ${LOCAL_COPY} matches vault canon-hashes.json aec.distribution_sha256 (${vault_sha})"
