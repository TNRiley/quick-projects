#!/usr/bin/env python3
"""Generate the Quick Projects catalog site from every projects/*/meta.json.

    python3 tools/build_catalog.py

Writes catalog/index.html and catalog/catalog.json. Adding a project to the catalog
means dropping a meta.json next to its index.html and re-running this.
"""
import json, os, glob, datetime, html, sys

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
TOOLS = os.path.dirname(os.path.abspath(__file__))
OWNER = "TNRiley"
CATALOG_REPO = "quick-projects"
OUT = os.path.join(ROOT, "catalog")
esc = lambda s: html.escape(str(s), quote=True)

def load():
    ms = []
    for f in sorted(glob.glob(os.path.join(ROOT, "projects", "*", "meta.json"))):
        m = json.load(open(f))
        d = os.path.dirname(f)
        m["bytes"] = os.path.getsize(os.path.join(d, "index.html"))
        m["published"] = bool(m.get("published"))
        m["repo"] = f"https://github.com/{OWNER}/{m['slug']}" if m["published"] else None
        m["live"] = f"https://{OWNER.lower()}.github.io/{m['slug']}/" if m["published"] else None
        ms.append(m)
    ms.sort(key=lambda m: (m["built"], m["slug"]), reverse=True)
    return ms

def human(b):
    return f"{b/1e6:.1f} MB" if b >= 1e6 else f"{b/1e3:.0f} KB"

SRC_LABEL = {True: ("full pipeline", "ok"), "html-is-source": ("HTML is the source", "ok"),
             "lost-reproducible": ("page only", "warn")}

def card(m):
    tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in m.get("tags", []))
    lab, cls = SRC_LABEL.get(m.get("hasSource"), ("—", ""))
    srcs = "".join(
        f'<li><a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["name"])}</a>'
        f'<span class="lic">{esc(s["licence"])}</span></li>' for s in m.get("sources", []))
    srcblock = f'<div class="k">Data</div><ul class="srcs">{srcs}</ul>' if srcs else \
               '<div class="k">Data</div><p class="none">No external data — the page is the whole thing.</p>'
    if m["published"]:
        hit = f'<a class="hit" href="{esc(m["live"])}" aria-label="Open {esc(m["title"])}"></a>'
        acts = (f'<a class="btn primary" href="{esc(m["live"])}">Open&nbsp;&rarr;</a>'
                f'<a class="btn" href="{esc(m["repo"])}">Repository</a>')
    else:
        hit = ""
        acts = ('<span class="btn pending">Not published yet</span>')
    return f"""<article class="card{'' if m['published'] else ' unpublished'}">
  {hit}
  <div class="plate"><canvas data-plate="{esc(m['slug'])}" aria-hidden="true"></canvas>
    <span class="glyph" aria-hidden="true">{esc(m['favicon'])}</span></div>
  <div class="cbody">
    <h2>{esc(m['title'])}</h2>
    <p class="tag-line">{esc(m['tagline'])}</p>
    <p class="blurb">{esc(m['blurb'])}</p>
    <div class="tags">{tags}</div>
    <div class="meta">
      <div class="k">Card</div>
      <dl>
        <div><dt>First published</dt><dd>{esc(m['built'])}</dd></div>
        <div><dt>Page weight</dt><dd>{human(m['bytes'])}</dd></div>
        <div><dt>Built with</dt><dd>{esc(", ".join(m.get("stack", [])))}</dd></div>
        <div><dt>Source</dt><dd class="{cls}">{esc(lab)}</dd></div>
      </dl>
      {srcblock}
    </div>
    <div class="acts">{acts}</div>
  </div>
</article>"""

def sources_table(ms):
    idx = {}
    for m in ms:
        for s in m.get("sources", []):
            idx.setdefault((s["name"], s["url"], s["licence"]), []).append(m)
    if not idx:
        return ""
    rows = ""
    for (name, url, lic), users in sorted(idx.items()):
        used = " ".join(
            (f'<a class="pill" href="{esc(u["live"])}">{esc(u["title"])}</a>' if u["published"]
             else f'<span class="pill muted">{esc(u["title"])}</span>') for u in users)
        rows += (f'<tr><td><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(name)}</a></td>'
                 f'<td class="lic-cell">{esc(lic)}</td><td>{used}</td></tr>')
    return f"""<section class="blk">
  <h2 class="sec">Where the data came from</h2>
  <p class="sublede">Every external dataset used across the collection, with the licence it carries and the projects that draw on it. Each page repeats this in its own methods panel, in more detail and with the limitations attached.</p>
  <div class="scroller"><table>
    <thead><tr><th>Dataset</th><th>Licence</th><th>Used by</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
</section>"""

def build():
    ms = load()
    total = sum(m["bytes"] for m in ms)
    dates = [m["built"] for m in ms]
    live = sum(1 for m in ms if m["published"])
    stats = [(f"{live} / {len(ms)}", "projects published so far, each built end to end in a single session"),
             (human(total), "of self-contained HTML — no build step, no server, no runtime network"),
             (f"{len({s['name'] for m in ms for s in m.get('sources', [])})}", "public datasets pulled at build time and baked in"),
             (f"{dates[-1][:7]} – {dates[0][:7]}", "first and latest")]
    tpl = open(os.path.join(TOOLS, "catalog_template.html"), encoding="utf-8").read()
    out = (tpl.replace("__CARDS__", "\n".join(card(m) for m in ms))
              .replace("__SOURCES__", sources_table(ms))
              .replace("__STATS__", "".join(
                  f'<div><div class="v">{esc(v)}</div><div class="k">{esc(k)}</div></div>' for v, k in stats))
              .replace("__SLUGS__", json.dumps([m["slug"] for m in ms]))
              .replace("__OWNER__", OWNER)
              .replace("__CATALOG_REPO__", CATALOG_REPO)
              .replace("__GENERATED__", datetime.date.today().isoformat()))
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(out)
    open(os.path.join(OUT, ".nojekyll"), "w").write("")
    json.dump({"generated": datetime.date.today().isoformat(), "owner": OWNER, "projects": ms},
              open(os.path.join(OUT, "catalog.json"), "w"), indent=2, ensure_ascii=False)
    # the catalog is authored as an Artifact-shaped fragment; Pages needs a real document
    sys.path.insert(0, TOOLS)
    import wrap_for_pages
    wrap_for_pages.wrap(os.path.join(OUT, "index.html"))
    print(f"catalog/index.html  {os.path.getsize(os.path.join(OUT,'index.html')):,} bytes  ({len(ms)} projects)")

if __name__ == "__main__":
    build()
