# scripts/build_geometry.py
"""Download world-atlas countries-110m, drop Antarctica, write minified JSON."""
import json, urllib.request, os

URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"
with urllib.request.urlopen(URL) as r:
    topo = json.load(r)

geoms = topo["objects"]["countries"]["geometries"]
before = len(geoms)
# Antarctica = ISO numeric 010; world-atlas stores ids as zero-padded 3-digit strings.
geoms = [g for g in geoms if str(g.get("id")) != "010"]
topo["objects"]["countries"]["geometries"] = geoms

os.makedirs("build", exist_ok=True)
with open("build/world-110m.min.json", "w", encoding="utf-8") as f:
    json.dump(topo, f, separators=(",", ":"))
print(f"Geometries: {before} -> {len(geoms)} (Antarctica dropped)")
