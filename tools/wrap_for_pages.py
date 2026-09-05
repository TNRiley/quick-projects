#!/usr/bin/env python3
"""Turn an Artifact-shaped HTML fragment into a standalone document, and back.

Pages published as Claude Artifacts are authored as fragments: no <!doctype>, no <html>,
no <head> — the Artifact host wraps them at publish time and supplies the charset, the
viewport meta and a small reset. GitHub Pages supplies none of that, so the same file
served from a repo lands in quirks mode and, with no charset declared, renders UTF-8 as
Latin-1 (every emoji and en dash turns to mojibake).

This wraps the fragment into a real document, hoisting its leading <title>/<link>/<meta>/
<style>/<script> elements into a proper <head>. It is idempotent, and --unwrap reverses it
exactly, so a project can still be republished to the Artifact host from the same file.

    python3 tools/wrap_for_pages.py --all
    python3 tools/wrap_for_pages.py --unwrap projects/still-cited/index.html
"""
import re, sys, os, glob, argparse

OPEN = "<!-- wrapped-for-pages -->"
HEAD_TAGS = ("title", "link", "meta", "style", "script", "base")
SKELETON = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>:root{color-scheme:light dark}body{margin:0}img{max-width:100%%}[hidden]{display:none!important}</style>
%s
</head>
<body>
%s
</body>
</html>
"""

def split_head(frag):
    """Consume leading head-ish elements; return (head_html, body_html)."""
    i, n = 0, len(frag)
    while True:
        m = re.compile(r"\s*<(%s)\b" % "|".join(HEAD_TAGS), re.I).match(frag, i)
        if not m:
            break
        tag = m.group(1).lower()
        gt = frag.find(">", m.end())
        if gt < 0:
            break
        if tag in ("link", "meta", "base") or frag[gt-1] == "/":
            i = gt + 1
            continue
        close = frag.lower().find("</%s>" % tag, gt)
        if close < 0:
            break
        i = close + len(tag) + 3
    return frag[:i].strip(), frag[i:].lstrip("\n")

def wrap(path):
    s = open(path, encoding="utf-8").read()
    if s.lstrip().lower().startswith("<!doctype"):
        return "already standalone"
    head, body = split_head(s)
    open(path, "w", encoding="utf-8", newline="\n").write(SKELETON % (OPEN + "\n" + head, body))
    return "wrapped"

def unwrap(path):
    s = open(path, encoding="utf-8").read()
    if OPEN not in s:
        return "not wrapped by this tool — leaving alone"
    head = s.split(OPEN, 1)[1].split("</head>", 1)[0].strip()
    body = s.split("<body>", 1)[1].rsplit("</body>", 1)[0].strip()
    open(path, "w", encoding="utf-8", newline="\n").write(head + "\n" + body + "\n")
    return "unwrapped"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--unwrap", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(__file__)
    while root != os.path.dirname(root) and not os.path.isdir(os.path.join(root, "projects")):
        root = os.path.dirname(root)
    paths = a.paths or (sorted(glob.glob(os.path.join(root, "projects", "*", "index.html")))
                        + [os.path.join(root, "catalog", "index.html")] if a.all else [])
    for p in paths:
        print(f"  {os.path.relpath(p, root):38} {(unwrap if a.unwrap else wrap)(p)}")
