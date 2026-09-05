# Quick Projects

An index over a shelf of one-session builds. Each project lives in its own repository with its
own GitHub Pages site; this repo holds only the catalog page that links them together.

→ **[Browse the catalog](https://tnriley.github.io/quick-projects/)**

## Publishing a new project

See **[PUBLISHING.md](PUBLISHING.md)** — the full workflow, including two traps that are not
guessable (Artifact HTML is not standalone HTML; session scratchpads are wiped).

## This page is generated

`index.html` and `catalog.json` are produced by `tools/build_catalog.py` in this repo,
from each project's `meta.json` in the sibling `projects/` directory of the local workspace. Don't hand-edit them — the next regeneration
will overwrite your changes.

Adding a project:

1. Drop a `meta.json` beside its `index.html` (see any existing project for the shape).
2. `python3 tools/scaffold_project.py <slug>` — writes the README, licence, `.nojekyll` and first commit.
3. `python3 tools/build_catalog.py` — regenerates this catalog.

`catalog.json` is the machine-readable version of the same data, if anything else ever wants to
read the shelf.

## Licence

MIT. Each project carries its own licence and its own data attributions.
