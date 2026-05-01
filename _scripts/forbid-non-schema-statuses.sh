#!/usr/bin/env bash
# Anti-régression doc — bloque toute réintroduction des statuts legacy dans la
# documentation (CLAUDE.md, hot.md, _meta/, _templates/...).
#
# Plan humble-cuddling-scott P-pré §3 — verrou secondaire.
# Le verrou primaire pour les fiches est le hook wiki-frontmatter-schema-py qui
# valide chaque proposal/wiki contre _meta/schema/frontmatter.schema.json (enum
# review_status: draft|proposed|in_review|approved|deprecated).
#
# Ici on protège les docs qui FORMENT les agents : si CLAUDE.md ou hot.md
# enseigne à utiliser needs_human_review, chaque agent généré reproduira le bug.
#
# Regex assignment-style uniquement (^[\s]*key:[\s]+value) — ne matche PAS les
# mentions en prose entre backticks. Ainsi un avertissement comme :
#   "> termes \`needs_human_review\` désormais interdits"
# n'est pas flaggé, alors qu'une vraie assignment :
#   review_status: needs_human_review
# l'est.
set -euo pipefail

PATTERN='^[[:space:]]*(review_status|status):[[:space:]]+(needs_human_review|human_reviewed|validated)\b'
ALLOWED_STATUSES='draft|proposed|in_review|approved|deprecated'

found=0
for f in "$@"; do
  if grep -nE "$PATTERN" "$f" > /dev/null 2>&1; then
    grep -nE "$PATTERN" "$f" | while IFS= read -r line; do
      printf "ERROR: %s — legacy status assignment (use review_status enum: %s)\n  %s\n" \
        "$f" "$ALLOWED_STATUSES" "$line"
    done
    found=1
  fi
done

exit $found
