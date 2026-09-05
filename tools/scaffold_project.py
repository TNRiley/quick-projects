#!/usr/bin/env python3
"""Scaffold one Quick Project directory into a publishable GitHub repo.

Reads projects/<slug>/meta.json and writes README.md, LICENSE, .nojekyll and
.gitignore, then initialises git and makes the first commit if there isn't one.
Safe to re-run: it rewrites the generated files and commits only if something changed.

    python3 tools/scaffold_project.py still-cited
    python3 tools/scaffold_project.py --all
"""
import json, os, subprocess, sys, datetime, argparse

def _workspace_root(start):
    """Walk up until we find the directory holding projects/ — so these scripts work
    wherever they are moved to, rather than assuming a fixed depth."""
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "projects")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("could not find the workspace root (no projects/ directory above %s)" % start)

ROOT = _workspace_root(__file__)
PROJECTS = os.path.join(ROOT, "projects")
OWNER = "TNRiley"
AUTHOR_NAME = "Trevor Riley"
AUTHOR_EMAIL = "tnril@users.noreply.github.com"   # matches his existing public commits; keeps the real address out of public history

SOURCE_NOTE = {
    True: "The full build pipeline is in [`src/`](src/), with a README describing how to regenerate the page from scratch.",
    "html-is-source": "This project has no data pipeline — `index.html` *is* the source. Edit it directly.",
    "lost-reproducible": ("The original build pipeline was not preserved. `index.html` is complete and self-contained, "
                          "and the data route is documented well enough to regenerate it — see the sources below."),
}

MIT = """MIT License

Copyright (c) {year} {name}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

GITIGNORE = """.DS_Store
*.pyc
__pycache__/
# raw downloads and intermediates — regenerate them, don't commit them
*.csv
*.dly
!docs/*.csv
openalex_*.json
payload.json
retractionwatch.csv
node_modules/
"""

def readme(m):
    live = f"https://{OWNER.lower()}.github.io/{m['slug']}/"
    src = SOURCE_NOTE.get(m.get("hasSource"), "")
    lines = [
        f"# {m['favicon']} {m['title']}",
        "",
        f"**{m['tagline']}**",
        "",
        f"→ **[Open it]({live})**",
        "",
        m["blurb"],
        "",
        "## Running it",
        "",
        "One self-contained HTML file. No build step, no server, no network access at runtime — "
        "open `index.html` in a browser, or serve the directory with any static host.",
        "",
        "```bash",
        "python3 -m http.server 8000   # then visit http://localhost:8000",
        "```",
        "",
        "## Rebuilding it from scratch",
        "",
        "[REBUILD.md](REBUILD.md) is written for an LLM with a shell and nothing else: the data "
        "sources and their quirks, the processing decisions, the page's structure and interactions, "
        "and a table of expected values to check the result against.",
        "",
        "## Source",
        "",
        src,
        "",
    ]
    if m.get("sources"):
        lines += ["## Data", ""]
        for s in m["sources"]:
            lines.append(f"- **[{s['name']}]({s['url']})** — {s['licence']}")
        lines += ["", "Every figure on the page is computed from the data shipped with it. "
                      "Check the page's own methods panel for how each number is derived and where it should not be pushed.", ""]
    lines += [
        "## Built with",
        "",
        ", ".join(m.get("stack", [])) + ".",
        "",
        "## Licence",
        "",
        "Code is MIT (see [LICENSE](LICENSE)). Data keeps the licence of its source, listed above.",
        "",
        "---",
        "",
        f"Part of [Quick Projects](https://github.com/{OWNER}/quick-projects) — "
        f"one self-contained thing, built in one session. First published {m['built']}.",
        "",
    ]
    return "\n".join(lines)

def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

def scaffold(slug, do_git=True):
    d = os.path.join(PROJECTS, slug)
    m = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
    m["bytes"] = os.path.getsize(os.path.join(d, "index.html"))
    m.setdefault("published", False)
    json.dump(m, open(os.path.join(d, "meta.json"), "w", encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False)
    open(os.path.join(d, "README.md"), "w", encoding="utf-8", newline="\n").write(readme(m))
    open(os.path.join(d, "LICENSE"), "w", encoding="utf-8", newline="\n").write(MIT.format(year=m["built"][:4], name=AUTHOR_NAME))
    open(os.path.join(d, ".gitignore"), "w", encoding="utf-8", newline="\n").write(GITIGNORE)
    open(os.path.join(d, ".nojekyll"), "w", encoding="utf-8", newline="\n").write("")   # Pages: serve files as-is, no Jekyll pass
    if not do_git:
        return m
    if not os.path.isdir(os.path.join(d, ".git")):
        run(["git", "init", "-b", "main"], d)
    run(["git", "config", "user.name", AUTHOR_NAME], d)
    run(["git", "config", "user.email", AUTHOR_EMAIL], d)
    run(["git", "add", "-A"], d)
    if run(["git", "diff", "--cached", "--quiet"], d).returncode != 0:
        msg = (f"{m['title']}: {m['tagline']}\n\n{m['blurb']}\n\n"
               f"Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n")
        run(["git", "commit", "-m", msg], d)
    return m

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--no-git", action="store_true")
    a = ap.parse_args()
    slugs = sorted(os.listdir(PROJECTS)) if a.all else [a.slug]
    for s in slugs:
        if not os.path.isfile(os.path.join(PROJECTS, s, "meta.json")):
            continue
        m = scaffold(s, do_git=not a.no_git)
        head = run(["git", "log", "--oneline", "-1"], os.path.join(PROJECTS, s)).stdout.strip()
        print(f"  {s:16} {m['bytes']:>10,} B   {head or 'no commit'}")
