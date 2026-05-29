# Good Vibes Map — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single Deneb (Vega) world map for the Miniviz Week-4 contest that fills every country by the vibe of its current local moment, computed live in the browser, with a clickable-legend spotlight.

**Architecture:** A small `Countries` table (ISO-numeric id, UTC offset) lives in the semantic model and is bound to a full-canvas Deneb visual. The world TopoJSON is embedded directly in the Vega spec (no external fetch — survives publish-to-web). Vega's `now()` computes each country's local hour from its offset, buckets it into one of six vibes, and colors the map. A hand-built interactive legend dims non-selected vibes.

**Tech Stack:** Power BI PBIP (TMDL semantic model + PBIR report), Deneb custom visual, Vega 5, Python 3 (pytz + pycountry) for one-time data generation, world-atlas TopoJSON.

**Reference spec:** `docs/superpowers/specs/2026-05-28-good-vibes-map-design.md`

---

## File Structure

| Path | Responsibility |
|---|---|
| `scripts/build_countries.py` | Generate country → ISO-numeric id + current UTC offset + region; emit `build/countries.json` |
| `scripts/build_geometry.py` | Download world-atlas `countries-110m`, drop Antarctica, minify → `build/world-110m.min.json` |
| `scripts/inline_topojson.py` | Inject the minified TopoJSON into the Vega spec → `build/vibe-map.built.json` |
| `deneb/vibe-map.vega.json` | Authored Vega spec (source of truth; references geometry by a placeholder dataset) |
| `build/` | Generated artifacts (git-ignored) |
| `minviz-week4.SemanticModel/definition/tables/Countries.tmdl` | The bound `Countries` table |
| `minviz-week4.Report/.../visuals/<id>/visual.json` | The Deneb visual on the page |

---

## Task 1: Project scaffolding

**Files:**
- Create: `.gitignore` (append), `scripts/`, `deneb/`, `build/`

- [ ] **Step 1: Initialize git (optional but recommended)**

The folder is not yet a git repo. If the user approved version control:

```bash
cd "C:/Users/jmanw/claude projects/miniviz-week4"
git init
```

- [ ] **Step 2: Create working folders**

```bash
mkdir -p scripts deneb build
```

- [ ] **Step 3: Ignore generated + companion artifacts**

Append to `.gitignore`:

```
build/
.superpowers/
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore && git commit -m "chore: scaffold folders for vibe-map build"
```

---

## Task 2: Generate the country offset dataset

**Files:**
- Create: `scripts/build_countries.py`
- Output: `build/countries.json`

Offsets are computed with `zoneinfo`/`pytz` **at generation time** (late May 2026), so DST-observing countries get their correct current offset automatically. This is exactly the "offsets as of May 2026" contract from the spec.

- [ ] **Step 1: Write the generator script**

```python
# scripts/build_countries.py
"""Emit build/countries.json: one row per country with ISO-numeric id,
name, current UTC offset (decimal hours), and region.
Offsets are DST-aware as of run time (contest window = May 2026)."""
import json, datetime
from zoneinfo import ZoneInfo
import pytz
import pycountry
import pycountry_convert as pcc

# Capital-zone overrides where pytz's first-listed zone is not the capital.
CAPITAL_TZ = {
    "US": "America/New_York",   # Washington DC
    "RU": "Europe/Moscow",
    "AU": "Australia/Sydney",   # Canberra
    "BR": "America/Sao_Paulo",  # Brasilia
    "CA": "America/Toronto",    # Ottawa
    "CD": "Africa/Kinshasa",
    "MX": "America/Mexico_City",
    "ID": "Asia/Jakarta",
    "KZ": "Asia/Almaty",
    "CL": "America/Santiago",
}

CONTINENT = {"AF": "Africa", "AS": "Asia", "EU": "Europe",
             "NA": "Americas", "SA": "Americas", "OC": "Oceania", "AN": "Antarctica"}

now = datetime.datetime.now(datetime.timezone.utc)
rows = []
for cc, tzs in pytz.country_timezones.items():
    tzname = CAPITAL_TZ.get(cc, tzs[0])
    offset = now.astimezone(ZoneInfo(tzname)).utcoffset().total_seconds() / 3600.0
    country = pycountry.countries.get(alpha_2=cc)
    if country is None or not getattr(country, "numeric", None):
        continue
    try:
        region = CONTINENT.get(pcc.country_alpha2_to_continent_code(cc), "Other")
    except KeyError:
        region = "Other"
    rows.append({
        "CountryId": int(country.numeric),
        "CountryName": country.name,
        "UtcOffset": round(offset, 2),
        "Region": region,
    })

rows.sort(key=lambda r: r["CountryId"])
with open("build/countries.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)
print(f"Wrote {len(rows)} countries")
```

- [ ] **Step 2: Install dependencies and run**

```bash
python -m pip install pytz pycountry pycountry-convert
python scripts/build_countries.py
```

Expected: `Wrote ~245 countries` (pytz covers territories too; that's fine — extras simply won't match a TopoJSON feature and are ignored by the lookup).

- [ ] **Step 3: Validate the output**

Spot-check known offsets in `build/countries.json`:
- India (`356`) → `5.5`
- Nepal (`524`) → `5.75`
- USA (`840`) → `-4.0` (EDT in May; **note: summer offset, as designed**)
- Japan (`392`) → `9.0`

If USA shows `-5.0`, the run happened outside US DST — re-confirm the run date is within the contest window.

- [ ] **Step 4: Commit**

```bash
git add scripts/build_countries.py && git commit -m "feat: generate country UTC-offset dataset"
```

---

## Task 3: Create the `Countries` TMDL table

**Files:**
- Create: `minviz-week4.SemanticModel/definition/tables/Countries.tmdl`
- Modify: `minviz-week4.SemanticModel/definition/model.tmdl` (add `ref table Countries`)

**REQUIRED SUB-SKILL:** `pbip:tmdl` for exact TMDL syntax of a static (DATATABLE / inline-M) table.

**Contract:** four columns at country grain — `CountryId` (int64), `CountryName` (string), `UtcOffset` (double), `Region` (string) — sourced from the rows in `build/countries.json`. No relationships needed (single table).

- [ ] **Step 1: Author `Countries.tmdl`**

Invoke the `pbip:tmdl` skill. Feed it `build/countries.json` and the column contract above. Use a calculated `DATATABLE` partition (preferred for static literal data — no Power Query dependency) or an inline-M `#table` partition if the skill recommends it. Set `summarizeBy: none` on `CountryId` and `UtcOffset`, and mark `CountryId` as the table's key.

- [ ] **Step 2: Register the table in the model**

Add `ref table Countries` to `model.tmdl`.

- [ ] **Step 3: Validate the project structure**

**REQUIRED SUB-SKILL:** `pbip:pbip-validator` — confirm TMDL parses and the project still opens.

```
Validate: minviz-week4 PBIP project structure + Countries.tmdl syntax
```

- [ ] **Step 4: Verify the table loads in Desktop**

Reload the report in the open Power BI Desktop. Confirm the `Countries` table appears with ~180–245 rows and the spot-check offsets from Task 2.

- [ ] **Step 5: Commit**

```bash
git add minviz-week4.SemanticModel/ && git commit -m "feat: add Countries table with UTC offsets"
```

---

## Task 4: Acquire and process the world TopoJSON

**Files:**
- Create: `scripts/build_geometry.py`
- Output: `build/world-110m.min.json`

- [ ] **Step 1: Write the geometry script**

```python
# scripts/build_geometry.py
"""Download world-atlas countries-110m, drop Antarctica, write minified JSON."""
import json, urllib.request

URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"
with urllib.request.urlopen(URL) as r:
    topo = json.load(r)

geoms = topo["objects"]["countries"]["geometries"]
before = len(geoms)
# Antarctica = ISO numeric 010 (ids are strings in world-atlas).
geoms = [g for g in geoms if str(g.get("id")) != "10"]
topo["objects"]["countries"]["geometries"] = geoms

with open("build/world-110m.min.json", "w", encoding="utf-8") as f:
    json.dump(topo, f, separators=(",", ":"))
print(f"Geometries: {before} -> {len(geoms)} (Antarctica dropped)")
```

- [ ] **Step 2: Run and validate**

```bash
python scripts/build_geometry.py
```

Expected: `Geometries: 177 -> 176 (Antarctica dropped)`. Confirm `build/world-110m.min.json` exists and is ~90–110 KB.

- [ ] **Step 3: Commit**

```bash
git add scripts/build_geometry.py && git commit -m "feat: fetch and trim world TopoJSON"
```

---

## Task 5: Author the Deneb Vega spec

**Files:**
- Create: `deneb/vibe-map.vega.json`

This is the core deliverable. The `world` dataset's `values` is left as an empty object placeholder `{}` here — Task 6 injects the real TopoJSON. The Power BI data arrives under the dataset name Deneb exposes (confirm exact name with the deneb-visuals skill in Task 7; this spec assumes `dataset`).

- [ ] **Step 1: Write the spec**

```json
{
  "$schema": "https://vega.github.io/schema/vega/v5.json",
  "background": "#0B1026",
  "padding": 16,
  "autosize": {"type": "fit", "contains": "padding"},
  "signals": [
    {
      "name": "now",
      "update": "now()",
      "on": [{"events": {"type": "timer", "throttle": 60000}, "update": "now()"}]
    },
    {
      "name": "selectedVibe",
      "value": null,
      "on": [
        {"events": "@swatch:click, @swatchLabel:click",
         "update": "datum.vibe === selectedVibe ? null : datum.vibe"},
        {"events": "dblclick", "update": "null"}
      ]
    }
  ],
  "data": [
    {
      "name": "world",
      "values": {},
      "format": {"type": "topojson", "feature": "countries"},
      "transform": [
        {
          "type": "lookup", "from": "dataset", "key": "CountryId",
          "fields": ["id"], "as": ["pbi"],
          "values": ["UtcOffset", "CountryName"]
        },
        {"type": "filter", "expr": "datum.pbi != null"},
        {
          "type": "formula", "as": "localHour",
          "expr": "((utchours(now) + utcminutes(now)/60) + datum.pbi.UtcOffset + 24) % 24"
        },
        {
          "type": "formula", "as": "vibe",
          "expr": "datum.localHour < 5 ? 'Asleep' : datum.localHour < 9 ? 'Sunrise' : datum.localHour < 12 ? 'Deep focus' : datum.localHour < 15 ? 'Lunch' : datum.localHour < 19 ? 'Golden hour' : 'Nightlife'"
        }
      ]
    },
    {
      "name": "vibeMeta",
      "values": [
        {"vibe": "Asleep",      "emoji": "🌙", "label": "Asleep",            "order": 0},
        {"vibe": "Sunrise",     "emoji": "☕", "label": "Sunrise & coffee",  "order": 1},
        {"vibe": "Deep focus",  "emoji": "💻", "label": "Deep-focus morning","order": 2},
        {"vibe": "Lunch",       "emoji": "🍽️", "label": "Lunch / midday",    "order": 3},
        {"vibe": "Golden hour", "emoji": "🌇", "label": "Golden hour",       "order": 4},
        {"vibe": "Nightlife",   "emoji": "🎉", "label": "Nightlife",         "order": 5}
      ]
    },
    {
      "name": "selectedCount",
      "source": "world",
      "transform": [
        {"type": "filter", "expr": "selectedVibe != null && datum.vibe === selectedVibe"},
        {"type": "aggregate", "ops": ["count"], "as": ["n"]}
      ]
    }
  ],
  "scales": [
    {
      "name": "vibeColor", "type": "ordinal",
      "domain": ["Asleep","Sunrise","Deep focus","Lunch","Golden hour","Nightlife"],
      "range": ["#2E3A59","#FF7E6B","#2DD4BF","#FBBF24","#FB7185","#A78BFA"]
    }
  ],
  "projections": [
    {"name": "proj", "type": "naturalEarth1", "fit": {"signal": "data('world')"},
     "size": {"signal": "[width, height-90]"}}
  ],
  "title": {
    "text": "Where are the good vibes — right now?",
    "subtitle": "Every country coloured by what its people are likely doing this very minute. Click a vibe to spotlight it.",
    "color": "#E8ECFB", "subtitleColor": "#8A93B8",
    "fontSize": 22, "subtitleFontSize": 12, "anchor": "start", "offset": 6
  },
  "marks": [
    {
      "type": "shape", "from": {"data": "world"},
      "encode": {
        "update": {
          "fill": {"signal": "selectedVibe == null || datum.vibe === selectedVibe ? scale('vibeColor', datum.vibe) : '#1B2236'"},
          "stroke": {"value": "#0B1026"}, "strokeWidth": {"value": 0.4},
          "tooltip": {"signal": "{'Country': datum.pbi.CountryName, 'Local time': format(floor(datum.localHour),'02d') + ':00', 'Vibe': datum.vibe}"}
        }
      },
      "transform": [{"type": "geoshape", "projection": "proj"}]
    },
    {
      "type": "group",
      "encode": {"update": {"y": {"signal": "height-44"}, "x": {"value": 0}}},
      "marks": [
        {
          "type": "symbol", "name": "swatch", "from": {"data": "vibeMeta"},
          "encode": {
            "update": {
              "x": {"signal": "datum.order * (width/6) + 10"}, "y": {"value": 8},
              "size": {"value": 160}, "shape": {"value": "circle"},
              "fill": {"signal": "scale('vibeColor', datum.vibe)"},
              "opacity": {"signal": "selectedVibe == null || datum.vibe === selectedVibe ? 1 : 0.3"},
              "cursor": {"value": "pointer"}
            }
          }
        },
        {
          "type": "text", "name": "swatchLabel", "from": {"data": "vibeMeta"},
          "encode": {
            "update": {
              "x": {"signal": "datum.order * (width/6) + 24"}, "y": {"value": 12},
              "text": {"signal": "datum.emoji + ' ' + datum.label"},
              "fill": {"value": "#C7CEEC"}, "fontSize": {"value": 11}, "baseline": {"value": "middle"},
              "opacity": {"signal": "selectedVibe == null || datum.vibe === selectedVibe ? 1 : 0.4"},
              "cursor": {"value": "pointer"}
            }
          }
        }
      ]
    },
    {
      "type": "text", "from": {"data": "selectedCount"},
      "encode": {
        "update": {
          "x": {"signal": "width"}, "y": {"value": 0}, "align": {"value": "right"},
          "text": {"signal": "selectedVibe == null ? '' : selectedVibe + ' right now in ' + datum.n + ' countries'"},
          "fill": {"value": "#8A93B8"}, "fontSize": {"value": 12}
        }
      }
    },
    {
      "type": "text",
      "encode": {
        "update": {
          "x": {"value": 0}, "y": {"signal": "height-4"},
          "text": {"value": "Local time computed live in your browser · UTC offsets as of May 2026"},
          "fill": {"value": "#5A618A"}, "fontSize": {"value": 9}
        }
      }
    }
  ]
}
```

- [ ] **Step 2: Self-check the spec logic**

Read through and confirm: signal `now` updates on timer; `lookup` joins by `CountryId`→`id`; `localHour` wraps with `+24 % 24`; the six vibe thresholds match the spec table (00/05/09/12/15/19); color domain order matches `vibeColor` range order.

- [ ] **Step 3: Commit**

```bash
git add deneb/vibe-map.vega.json && git commit -m "feat: author vibe-map Vega spec"
```

---

## Task 6: Inline the TopoJSON into the spec

**Files:**
- Create: `scripts/inline_topojson.py`
- Output: `build/vibe-map.built.json`

- [ ] **Step 1: Write the inliner**

```python
# scripts/inline_topojson.py
"""Inject build/world-110m.min.json into the spec's `world` dataset values."""
import json

with open("deneb/vibe-map.vega.json", encoding="utf-8") as f:
    spec = json.load(f)
with open("build/world-110m.min.json", encoding="utf-8") as f:
    topo = json.load(f)

for d in spec["data"]:
    if d["name"] == "world":
        d["values"] = topo
        break
else:
    raise SystemExit("No 'world' dataset found in spec")

with open("build/vibe-map.built.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, ensure_ascii=False)
print("Wrote build/vibe-map.built.json")
```

- [ ] **Step 2: Run and validate**

```bash
python scripts/inline_topojson.py
```

Confirm `build/vibe-map.built.json` exists and is ~120 KB (spec + topojson).

- [ ] **Step 3: Validate the Vega before placing it**

**REQUIRED SUB-SKILL:** `reports:deneb-reviewer` — review `build/vibe-map.built.json` for Vega syntax / Deneb-convention issues. Fix any findings in `deneb/vibe-map.vega.json` (the source), then re-run the inliner.

- [ ] **Step 4: Commit**

```bash
git add scripts/inline_topojson.py && git commit -m "feat: inline TopoJSON into built spec"
```

---

## Task 7: Place the Deneb visual on the report page

**Files:**
- Create/modify: `minviz-week4.Report/definition/pages/d8c00e4d3c82002ad857/visuals/<id>/visual.json`

**REQUIRED SUB-SKILL:** `reports:deneb-visuals` (Deneb-in-PBIR mechanics) + `reports:pbir-cli` (adding/binding the visual).

**Contract for the integration skill:**
- Visual type: Deneb custom visual, full-canvas on the existing page.
- Data binding: add `Countries` fields `CountryId`, `UtcOffset`, `CountryName` (and `Region` for tooltip) to the visual's data roles so they arrive as the Deneb dataset. Confirm the dataset name the spec references (`dataset` in the `lookup` transform) matches Deneb's exposed name; adjust the spec if Deneb uses a different default.
- Spec payload: the contents of `build/vibe-map.built.json`.
- Provider: set Deneb provider to **Vega** (not Vega-Lite).

- [ ] **Step 1: Confirm/import the Deneb custom visual**

Deneb must be available to the report. Use the `reports:deneb-visuals` skill to confirm Deneb is imported (in Desktop: Get more visuals → Deneb) and how it is referenced in PBIR.

- [ ] **Step 2: Add the visual and bind the dataset**

Use `reports:pbir-cli` / `reports:deneb-visuals` to add a full-canvas Deneb visual to page `d8c00e4d3c82002ad857`, bind the four `Countries` fields, and load the spec from `build/vibe-map.built.json`.

- [ ] **Step 3: Validate the report structure**

**REQUIRED SUB-SKILL:** `pbip:pbip-validator`.

```
Validate: minviz-week4 PBIP project + the new visual.json
```

- [ ] **Step 4: Commit**

```bash
git add minviz-week4.Report/ && git commit -m "feat: place vibe-map Deneb visual on page"
```

---

## Task 8: Render and verify in Power BI Desktop

- [ ] **Step 1: Reload the report in the open Desktop instance**

Reload `minviz-week4.pbip`. The map should render on a dark navy canvas, countries coloured by vibe.

- [ ] **Step 2: Verify the live vibe band**

Sanity-check against the real world clock right now:
- Countries where it is currently 15:00–19:00 local → 🌇 Golden hour (`#FB7185`).
- Countries in deep night → 🌙 Asleep (`#2E3A59`).
- The colours should trend in roughly vertical bands west→east.

- [ ] **Step 3: Verify the spotlight interaction**

Click a legend swatch → all other countries dim to `#1B2236`, the chosen vibe stays bright, and the top-right caption shows "<vibe> right now in N countries". Click again (or double-click) to reset.

- [ ] **Step 4: Verify the timer (best effort)**

Leave the visual open ~1–2 minutes; a country near a bucket boundary should shift colour as local time crosses the threshold. If it does not (sandbox throttling), confirm render-time correctness is still right — this is the documented graceful fallback.

- [ ] **Step 5: Tooltip + polish pass**

Hover a country → tooltip shows Country / Local time / Vibe. Check title and footnote are readable and not clipped at the report's canvas size.

- [ ] **Step 6: Final commit**

```bash
git add -A && git commit -m "feat: vibe-map renders and verified in Desktop"
```

---

## Self-Review (completed during planning)

- **Spec coverage:** Aurora palette + 6 buckets (Task 5 scales/vibeMeta), live Vega `now()` (Task 5 signals), country-level offsets (Tasks 2–3), embedded TopoJSON (Tasks 4, 6), in-Deneb spotlight (Task 5 marks + signal), full-canvas layout + caption + footnote (Task 5), validation/render (Tasks 7–8), DST/May-2026 caveat (Task 2 + footnote). All spec sections map to a task.
- **Placeholder scan:** the only literal placeholder is the `world.values: {}` in the authored spec, intentionally filled by Task 6's inliner (documented).
- **Name consistency:** `CountryId`/`UtcOffset`/`CountryName`/`Region` used identically across Tasks 2, 3, 5, 7; `vibe` bucket names match between the `formula`, the `vibeColor` scale domain, and `vibeMeta`.

## Known integration risks to watch during execution

1. **Deneb dataset name** — the spec's `lookup from: "dataset"` assumes Deneb's default exposed name; confirm and adjust in Task 7.
2. **Data point cap** — Deneb/PBI may cap rows; ~180 countries is well under the default, but raise the cap if any country renders uncoloured.
3. **Emoji rendering** in Vega text marks depends on the host font; if emojis fail, fall back to coloured dots only in the legend.
4. **`pycountry-convert`** may be awkward to install on Windows; if so, replace the `Region` derivation with a static alpha-2→continent dict (Region is non-critical, tooltip-only).
