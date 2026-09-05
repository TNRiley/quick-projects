#!/usr/bin/env python3
"""Recover a template + payload from a built page whose pipeline was lost.

These pages are template + a large inlined JSON literal, spliced together at build time.
When the build scripts are gone (session scratchpads get wiped — it has happened three
times) the page itself still contains everything needed to reconstruct them.

Finds `const <NAME> = {...};`, writes the literal to payload.json and the rest to
template.html with a __PAYLOAD__ placeholder, then verifies the two splice back into a
file byte-identical to the input before writing anything.

    python3 catalog/tools/unsplice.py projects/daybook/index.html --var DATA --out projects/daybook/src
"""
import argparse, json, os, sys

def unsplice(path, var, out):
    src = open(path, encoding="utf-8").read()

    tools = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, tools)
    import wrap_for_pages
    wrapped = src.lstrip().lower().startswith("<!doctype")
    if wrapped:                                  # templates are stored fragment-shaped
        head = src.split(wrap_for_pages.OPEN, 1)[1].split("</head>", 1)[0].strip()
        body = src.split("<body>", 1)[1].rsplit("</body>", 1)[0].strip()
        frag = head + "\n" + body + "\n"
    else:
        frag = src

    needle = f"const {var} = "
    i = frag.find(needle)
    if i < 0:
        raise SystemExit(f"could not find `{needle}` in {path}")
    start = i + len(needle)
    j = frag.find(";\n", start)
    if j < 0:
        raise SystemExit("could not find the end of the payload literal")
    payload = frag[start:j]
    json.loads(payload)                           # must be valid JSON, not arbitrary JS

    template = frag[:start] + "__PAYLOAD__" + frag[j:]
    if template.replace("__PAYLOAD__", payload) != frag:
        raise SystemExit("round-trip check failed — refusing to write")

    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "payload.json"), "w", encoding="utf-8").write(payload)
    open(os.path.join(out, "template.html"), "w", encoding="utf-8").write(template)
    open(os.path.join(out, "inject.py"), "w", encoding="utf-8").write(INJECT % var)
    print(f"  template.html  {len(template):>10,} B")
    print(f"  payload.json   {len(payload):>10,} B")
    print(f"  round-trip verified against {os.path.basename(path)}"
          + (" (unwrapped first)" if wrapped else ""))

INJECT = '''#!/usr/bin/env python3
"""Splice payload.json into template.html -> ../index.html, then wrap it for Pages.

The payload never passes through the conversation that writes the page; the template
carries a __PAYLOAD__ placeholder and this puts the data in at the end. Variable: %s
"""
import os, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
payload = open(os.path.join(HERE, "payload.json"), encoding="utf-8").read()
template = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
out = os.path.join(HERE, "..", "index.html")
open(out, "w", encoding="utf-8").write(template.replace("__PAYLOAD__", payload))

root = HERE
while root != os.path.dirname(root) and not os.path.isdir(os.path.join(root, "projects")):
    root = os.path.dirname(root)
subprocess.run([sys.executable, os.path.join(root, "catalog", "tools", "wrap_for_pages.py"), out])
print("wrote", os.path.normpath(out), f"{os.path.getsize(out):,} bytes")
'''

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("--var", default="DATA")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    unsplice(a.page, a.var, a.out)
