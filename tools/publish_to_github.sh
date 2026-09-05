#!/usr/bin/env bash
# Create the GitHub repos, push, and turn on Pages. Idempotent — safe to re-run;
# repos that already exist are pushed to, not recreated.
#
# Needs the GitHub CLI, authenticated:
#     brew install gh && gh auth login
set -uo pipefail
OWNER="TNRiley"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while [ "$ROOT" != "/" ] && [ ! -d "$ROOT/projects" ]; do ROOT="$(dirname "$ROOT")"; done
OWNER_LC="$(printf %s "$OWNER" | tr "[:upper:]" "[:lower:]")"

command -v gh >/dev/null || { echo "gh not found. Run:  brew install gh && gh auth login"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh is installed but not authenticated. Run:  gh auth login"; exit 1; }

publish () {                       # $1 = local dir, $2 = repo name, $3 = description
  local dir="$1" repo="$2" desc="$3"
  echo "── $repo"
  ( cd "$dir" || exit 1
    if gh repo view "$OWNER/$repo" >/dev/null 2>&1; then
      echo "   repo exists"
      git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$OWNER/$repo.git"
    else
      gh repo create "$OWNER/$repo" --public --description "$desc" --disable-wiki >/dev/null || return 1
      git remote add origin "https://github.com/$OWNER/$repo.git" 2>/dev/null
      echo "   repo created"
    fi
    git push -u origin main || return 1
    if gh api "repos/$OWNER/$repo/pages" >/dev/null 2>&1; then
      echo "   pages already on"
    else
      gh api --method POST "repos/$OWNER/$repo/pages" \
        -f "source[branch]=main" -f "source[path]=/" >/dev/null 2>&1 \
        && echo "   pages enabled" || echo "   !! could not enable pages — turn it on in Settings → Pages"
    fi
    [ "$repo" = "quick-projects" ] || python3 "$ROOT/catalog/tools/mark_published.py" "$repo" >/dev/null 2>&1
    gh repo edit "$OWNER/$repo" --homepage "https://${OWNER_LC}.github.io/$repo/" >/dev/null 2>&1
    echo "   https://${OWNER_LC}.github.io/$repo/"
  )
}

for d in "$ROOT"/projects/*/; do
  slug="$(basename "$d")"
  desc="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['tagline'])" "$d/meta.json" 2>/dev/null)"
  publish "$d" "$slug" "$desc"
done
publish "$ROOT/catalog" "quick-projects" "A catalog of one-session, self-contained builds."

echo
echo "Done. Pages can take a minute or two to go live the first time."
echo "Catalog: https://${OWNER_LC}.github.io/quick-projects/"
