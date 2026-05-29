# scripts/embed_spec.py
"""Embed build/vibe-map.built.json into the Deneb visual's jsonSpec property.

The Vega spec is stored in visual.json as a PBIR string literal at
  visual.objects.vega[0].properties.jsonSpec.expr.Literal.Value
i.e. the entire spec JSON wrapped in single quotes, with every internal
single quote doubled ('' ) per PBIR literal escaping. This script updates
ONLY that value so the visual always carries the current built spec.
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILT = ROOT / "build" / "vibe-map.built.json"
VISUAL = (ROOT / "minviz-week4.Report" / "definition" / "pages"
          / "d8c00e4d3c82002ad857" / "visuals" / "986024f7d0671910" / "visual.json")

# Read the built spec as raw text (preserves emoji + exact JSON).
spec_text = BUILT.read_text(encoding="utf-8")

# PBIR literal: wrap in single quotes, double any internal single quotes.
pbir_literal = "'" + spec_text.replace("'", "''") + "'"

visual = json.loads(VISUAL.read_text(encoding="utf-8"))
props = visual["visual"]["objects"]["vega"][0]["properties"]
props["jsonSpec"]["expr"]["Literal"]["Value"] = pbir_literal

VISUAL.write_text(
    json.dumps(visual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(f"Embedded {len(spec_text)} chars of spec into {VISUAL.name}")
print(f"Internal single quotes escaped: {spec_text.count(chr(39))}")
