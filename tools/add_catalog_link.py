#!/usr/bin/env python3
"""Put a breadcrumb back to the catalog at the top of a project page.

Inserted just inside <body> as a slim inline bar rather than a floating pill, so it can
never overlap page content on a narrow screen. It inherits the page's own text colour and
uses translucent greys for its rules, so it works on any of these pages in either theme
without knowing anything about their palettes.

The bar also carries the visit counter (see visit_counter.py), which is why it lives
here rather than in a step of its own: every project's injector already finishes by
running this script, so a counter change reaches all of them on the next rebuild with
no per-project edit and no new step for an injector to drop.

Idempotent — re-running replaces the existing bar rather than stacking another one.

    python3 catalog/tools/add_catalog_link.py --all
    python3 catalog/tools/add_catalog_link.py projects/daybook/index.html
"""
import argparse, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import visit_counter

OWNER = "TNRiley"
CATALOG = f"https://{OWNER.lower()}.github.io/quick-projects/"
START, END = "<!-- catalog-link -->", "<!-- /catalog-link -->"

BAR = f"""{START}
<style>
.qp-crumb{{display:flex;align-items:center;gap:8px;padding:9px 18px;
  border-bottom:1px solid rgba(128,128,128,.26);background:rgba(128,128,128,.06);
  font:500 12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.06em}}
.qp-crumb a{{color:inherit;text-decoration:none;opacity:.68;display:inline-flex;gap:7px;align-items:center}}
.qp-crumb a:hover,.qp-crumb a:focus-visible{{opacity:1;text-decoration:underline;text-underline-offset:3px}}
.qp-crumb .qp-sep{{opacity:.34}}
.qp-crumb .qp-here{{opacity:.44;text-transform:uppercase}}
.qp-crumb .qp-visits{{margin-left:auto;opacity:.44;font-variant-numeric:tabular-nums}}
@media(max-width:600px){{.qp-crumb{{padding:8px 14px;font-size:11px}}}}
@media print{{.qp-crumb{{display:none}}}}
</style>
<nav class="qp-crumb" aria-label="Breadcrumb">
  <a href="{CATALOG}">&larr;&nbsp;Quick Projects</a>
  <span class="qp-sep">/</span>
  <span class="qp-here">__TITLE__</span>
</nav>
__COUNTER__
{END}"""

def apply(path, title, slug):
    s = open(path, encoding="utf-8").read()
    s = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", s, flags=re.S)
    bar = BAR.replace("__TITLE__", title).replace("__COUNTER__", visit_counter.project_snippet(slug))
    m = re.search(r"<body[^>]*>", s, re.I)
    if m:
        s = s[:m.end()] + "\n" + bar + s[m.end():]
    else:                                   # unwrapped fragment: goes at the very top
        s = bar + "\n" + s
    open(path, "w", encoding="utf-8", newline="\n").write(s)
    return "linked"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    while root != os.path.dirname(root) and not os.path.isdir(os.path.join(root, "projects")):
        root = os.path.dirname(root)
    paths = a.paths or (sorted(glob.glob(os.path.join(root, "projects", "*", "index.html"))) if a.all else [])
    import json
    for p in paths:
        meta = os.path.join(os.path.dirname(p), "meta.json")
        title = json.load(open(meta, encoding="utf-8"))["title"] if os.path.isfile(meta) else "Project"
        slug = os.path.basename(os.path.dirname(p))
        print(f"  {os.path.relpath(p, root):40} {apply(p, title, slug)}")
