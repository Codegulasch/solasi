#!/usr/bin/env python3
"""Kopiert tools/flow_shared.js zwischen die Marker /*FLOW-BEGIN*/ und /*FLOW-END*/ in Oberfläche und Karte.
   `--check` ändert nichts und meldet mit Exit 1, wenn die Kopien abweichen (für CI und Tests)."""
import re, sys, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
src = (root / "tools" / "flow_shared.js").read_text(encoding="utf-8").rstrip("\n")
targets = [root / "solasi/app/static/index.html", root / "solasi/app/card/solasi-card.js"]
pat = re.compile(r"/\*FLOW-BEGIN\*/.*?/\*FLOW-END\*/", re.S)
bad = 0
for t in targets:
    txt = t.read_text(encoding="utf-8")
    if not pat.search(txt):
        print("Marker fehlen in", t); bad += 1; continue
    new = pat.sub(lambda m: "/*FLOW-BEGIN*/\n" + src + "\n/*FLOW-END*/", txt)
    if new != txt:
        if "--check" in sys.argv:
            print("weicht ab:", t); bad += 1
        else:
            t.write_text(new, encoding="utf-8"); print("aktualisiert:", t)
sys.exit(1 if bad else 0)
