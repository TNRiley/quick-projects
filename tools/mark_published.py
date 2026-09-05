#!/usr/bin/env python3
"""Flip a project's meta.json to published:true, then regenerate the catalog.
Called by publish_to_github.sh after a successful push; safe to run by hand.

    python3 catalog/tools/mark_published.py still-cited
"""
import json, os, sys, subprocess

TOOLS = os.path.dirname(os.path.abspath(__file__))
root = TOOLS
while root != os.path.dirname(root) and not os.path.isdir(os.path.join(root, "projects")):
    root = os.path.dirname(root)

for slug in sys.argv[1:]:
    f = os.path.join(root, "projects", slug, "meta.json")
    if not os.path.isfile(f):
        print(f"  {slug}: no meta.json — skipped"); continue
    m = json.load(open(f))
    if m.get("published"):
        print(f"  {slug}: already marked published"); continue
    m["published"] = True
    json.dump(m, open(f, "w"), indent=2, ensure_ascii=False)
    print(f"  {slug}: marked published")
subprocess.run([sys.executable, os.path.join(TOOLS, "build_catalog.py")])
