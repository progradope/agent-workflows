#!/usr/bin/env bash
# Attach visual evidence (screenshots, GIFs, short videos) to a GitHub PR so it
# shows inline in the PR description, the same way the "Attach files" button
# does. Uses GitHub CLI's --attach flag (gh v2.99.0 or later), which uploads
# each file to GitHub's attachment storage and rewrites local references in
# the Markdown to the uploaded URLs. Nothing is pushed to any branch.
#
# The evidence lives in a marked section of the PR description, replaced on
# re-runs; the rest of the description is kept. --in comment posts one PR
# comment instead (an older evidence comment is deleted).
#
# Usage:
#   attach-pr-evidence.sh --pr 2422 --body summary.md [--in description|comment] [--dry-run] FILE...
# FILE: .png .jpg .jpeg .gif .webp .svg .mp4 .mov .webm (images max 10 MB).
set -euo pipefail

PR="" BODY="" DRY=0 WHERE="description" FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --pr) PR="$2"; shift 2 ;;
    --body) BODY="$2"; shift 2 ;;
    --in) WHERE="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) FILES+=("$1"); shift ;;
  esac
done
[ -n "$PR" ] && [ -n "$BODY" ] && [ ${#FILES[@]} -gt 0 ] || { echo "usage: --pr N --body FILE FILE..." >&2; exit 2; }
[ -f "$BODY" ] || { echo "body file not found: $BODY" >&2; exit 2; }
case "$WHERE" in description|comment) ;; *) echo "--in must be description or comment" >&2; exit 2 ;; esac
command -v gh >/dev/null && command -v jq >/dev/null || { echo "needs gh and jq" >&2; exit 2; }

GH_VER=$(gh --version | head -1 | sed -E 's/^gh version ([0-9]+\.[0-9]+\.[0-9]+).*/\1/')
if [ "$(printf '%s\n2.99.0\n' "$GH_VER" | sort -V | head -1)" != "2.99.0" ]; then
  echo "gh $GH_VER is too old: --attach needs gh v2.99.0 or later" >&2; exit 2
fi

MAX_BYTES=$((10 * 1024 * 1024))
for f in "${FILES[@]}"; do
  [ -s "$f" ] || { echo "missing or empty: $f" >&2; exit 2; }
  lower=$(printf "%s" "$f" | tr "[:upper:]" "[:lower:]")
  case "$lower" in
    *.png|*.jpg|*.jpeg|*.gif|*.webp|*.svg)
      [ "$(wc -c < "$f")" -le "$MAX_BYTES" ] || { echo "image over 10 MB: $f" >&2; exit 2; } ;;
    *.mp4|*.mov|*.webm) ;;
    *) echo "unsupported file type: $f" >&2; exit 2 ;;
  esac
done

REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
HEAD_SHA=$(gh pr view "$PR" --json headRefOid --jq .headRefOid)
START="<!-- pr-visual-evidence:start -->"
END="<!-- pr-visual-evidence:end -->"
MARKER="<!-- pr-visual-evidence:pr-${PR} -->"

if [ "$DRY" = 1 ]; then
  echo "repo=$REPO pr=$PR head=$HEAD_SHA in=$WHERE gh=$GH_VER"
  printf '  %s\n' "${FILES[@]}"
  exit 0
fi

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
ATTACH=()
{
  if [ "$WHERE" = "description" ]; then echo "$START"; else echo "$MARKER"; fi
  echo "## Visual evidence"
  echo
  echo "Head: \`${HEAD_SHA}\`"
  echo
  cat "$BODY"
  echo
  for f in "${FILES[@]}"; do
    name=$(basename "$f")
    # gh rewrites these local references to the uploaded URLs.
    echo "**${name}**"
    echo
    echo "![${name}](${f})"
    echo
    ATTACH+=(--attach "$f")
  done
  if [ "$WHERE" = "description" ]; then echo "$END"; fi
} > "$TMP/section.md"

if [ "$WHERE" = "description" ]; then
  gh pr view "$PR" --json body --jq .body > "$TMP/old.md"
  # Drop any previous evidence section, keep everything else, append the new one.
  awk -v s="$START" -v e="$END" '
    index($0, s) { skip = 1; next }
    skip && index($0, e) { skip = 0; next }
    !skip { print }
  ' "$TMP/old.md" | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}' > "$TMP/kept.md"
  { cat "$TMP/kept.md"; printf '\n\n'; cat "$TMP/section.md"; } > "$TMP/new.md"
  gh pr edit "$PR" --body-file "$TMP/new.md" "${ATTACH[@]}" >/dev/null
  gh pr view "$PR" --json url --jq .url
else
  OLD=$(gh api "repos/$REPO/issues/$PR/comments" --paginate \
    --jq ".[] | select(.body | contains(\"$MARKER\")) | .id")
  gh pr comment "$PR" --body-file "$TMP/section.md" "${ATTACH[@]}"
  for id in $OLD; do gh api -X DELETE "repos/$REPO/issues/comments/$id" >/dev/null; done
fi
