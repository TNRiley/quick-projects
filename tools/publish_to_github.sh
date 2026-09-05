#!/usr/bin/env bash
# Create the GitHub repos, push, and turn on Pages. Idempotent — safe to re-run;
# repos that already exist are pushed to, not recreated.
#
# Needs the GitHub CLI, authenticated as TNRiley:
#     macOS:    brew install gh
#     Windows:  winget install GitHub.cli
#     both:     gh auth login && gh auth switch --user TNRiley
set -uo pipefail
OWNER="TNRiley"
PY="python3"; "$PY" -c "" >/dev/null 2>&1 || PY="python"
"$PY" -c "" >/dev/null 2>&1 || { echo "no working python on PATH (tried python3, python)"; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Fixed-point walk-up: comparing against "/" never terminates on a Windows-style path
# (dirname "C:" is "C:"), so stop when dirname stops changing instead.
while [ ! -d "$ROOT/projects" ]; do
  parent="$(dirname "$ROOT")"; [ "$parent" = "$ROOT" ] && break; ROOT="$parent"
done
OWNER_LC="$(printf %s "$OWNER" | tr "[:upper:]" "[:lower:]")"

command -v gh >/dev/null || { echo "gh not found. Install it (macOS: brew install gh | Windows: winget install GitHub.cli), then: gh auth login"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh is installed but not authenticated. Run:  gh auth login"; exit 1; }

# These are personal projects: they belong to TNRiley, never the work account.
# Two accounts (TRileyNOAA for work, TNRiley for these) can both be authenticated at once,
# and gh acts as whichever is globally *active* — which is the work one by default.
# Rather than depend on that, pull TNRiley's token out of the credential store and scope it
# to this script via GH_TOKEN. The global active account is left exactly as it was, so this
# never disturbs work repos and there is nothing to remember or restore.
if [ -z "${GH_TOKEN:-}" ]; then
  GH_TOKEN="$(gh auth token --user "$OWNER" 2>/dev/null)"
  export GH_TOKEN
fi
if [ -z "${GH_TOKEN:-}" ]; then
  echo "No stored credential for $OWNER."
  echo "Run:  gh auth login    (authenticate as $OWNER, then re-run)"
  exit 1
fi

# Belt and braces: confirm the token really is TNRiley before creating anything.
active="$(gh api user --jq .login 2>/dev/null)"
if [ "$active" != "$OWNER" ]; then
  echo "gh is acting as ${active:-<unknown>}, not $OWNER — refusing to publish."
  exit 1
fi
echo "publishing as $active"

publish () {                       # $1 = local dir, $2 = repo name, $3 = description
  local dir="$1" repo="$2" desc="$3"
  echo "── $repo"
  ( cd "$dir" || exit 1
    if gh repo view "$OWNER/$repo" >/dev/null 2>&1; then
      echo "   repo exists"
      git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://$OWNER@github.com/$OWNER/$repo.git"
    else
      gh repo create "$OWNER/$repo" --public --description "$desc" --disable-wiki >/dev/null || return 1
      git remote add origin "https://$OWNER@github.com/$OWNER/$repo.git" 2>/dev/null
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
    [ "$repo" = "quick-projects" ] || "$PY" "$ROOT/catalog/tools/mark_published.py" "$repo" >/dev/null 2>&1
    gh repo edit "$OWNER/$repo" --homepage "https://${OWNER_LC}.github.io/$repo/" >/dev/null 2>&1
    echo "   https://${OWNER_LC}.github.io/$repo/"
  )
}

for d in "$ROOT"/projects/*/; do
  slug="$(basename "$d")"
  desc="$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1]))['tagline'])" "$d/meta.json" 2>/dev/null)"
  publish "$d" "$slug" "$desc"
done
publish "$ROOT/catalog" "quick-projects" "A catalog of one-session, self-contained builds."

echo
echo "Done. Pages can take a minute or two to go live the first time."
echo "Catalog: https://${OWNER_LC}.github.io/quick-projects/"
