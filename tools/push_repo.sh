#!/usr/bin/env bash
# Push one already-created GitHub repo. The Mac path: no gh CLI needed there — no Homebrew,
# but osxkeychain is the system credential helper and already holds a GitHub credential,
# so plain git push authenticates on its own.
#
# The empty repo must exist first (create it at github.com/new, no README/licence/gitignore):
#     bash catalog/tools/push_repo.sh still-cited
#     bash catalog/tools/push_repo.sh quick-projects        # the catalog lives in catalog/
set -uo pipefail
OWNER="TNRiley"
PY="python3"; "$PY" -c "" >/dev/null 2>&1 || PY="python"
"$PY" -c "" >/dev/null 2>&1 || { echo "no working python on PATH (tried python3, python)"; exit 1; }
SLUG="${1:?usage: push_repo.sh <slug>}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Fixed-point walk-up: comparing against "/" never terminates on a Windows-style path
# (dirname "C:" is "C:"), so stop when dirname stops changing instead.
while [ ! -d "$ROOT/projects" ]; do
  parent="$(dirname "$ROOT")"; [ "$parent" = "$ROOT" ] && break; ROOT="$parent"
done

if [ "$SLUG" = "quick-projects" ]; then DIR="$ROOT/catalog"; else DIR="$ROOT/projects/$SLUG"; fi
[ -d "$DIR/.git" ] || { echo "no git repo at $DIR"; exit 1; }

code=$(curl -s -o /dev/null -w '%{http_code}' -L "https://github.com/$OWNER/$SLUG")
if [ "$code" = "404" ]; then
  echo "github.com/$OWNER/$SLUG does not exist yet."
  echo "Create it empty at https://github.com/new  (no README, no .gitignore, no licence), then re-run."
  exit 1
fi

cd "$DIR" || exit 1
# username embedded: this machine also holds a TRileyNOAA credential, and without it
# git offers that one and GitHub returns 403.
git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://$OWNER@github.com/$OWNER/$SLUG.git"
git push -u origin main || exit 1

if [ "$SLUG" != "quick-projects" ]; then
  "$PY" "$ROOT/catalog/tools/mark_published.py" "$SLUG"
fi
echo
echo "Pushed. Now turn on Pages:"
echo "  https://github.com/$OWNER/$SLUG/settings/pages"
echo "  Source: Deploy from a branch → main → / (root) → Save"
echo "  Site:   https://$(printf %s "$OWNER" | tr '[:upper:]' '[:lower:]').github.io/$SLUG/"
