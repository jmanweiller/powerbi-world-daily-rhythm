# scripts/inline_topojson.py
"""Inject build/world-110m.min.json into the spec's `world` dataset values."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / "deneb" / "vibe-map.vega.json"
TOPO = ROOT / "build" / "world-110m.min.json"
OUT = ROOT / "build" / "vibe-map.built.json"

with open(SPEC, encoding="utf-8") as f:
    spec = json.load(f)
with open(TOPO, encoding="utf-8") as f:
    topo = json.load(f)

for d in spec["data"]:
    if d["name"] == "world":
        d["values"] = topo
        break
else:
    raise SystemExit("No 'world' dataset found in spec")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(spec, f, ensure_ascii=False)
print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
