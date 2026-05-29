# Design: "Where Are the Good Vibes — Right Now?"

**Date:** 2026-05-28
**Project:** miniviz-week4 (Power BI PBIP)
**Challenge:** Miniviz May — Week 4, "Where are the good vibes" (Fabric QuickViz Gallery)

## Goal

A single Deneb (Vega) world map that fills every country by the **vibe of its
current local moment**, computed live in the viewer's browser. Clicking a vibe
in the legend dims the rest of the world, spotlighting "where it's golden hour
right now." The map does 100% of the storytelling.

## Why this fits the brief

The Week-4 brief asks for a map that shows a **pattern or difference across
locations, not just where things are**, kept simple (one category), uncluttered,
with the map doing the storytelling. The vibe map encodes a single category (the
current vibe bucket) and reveals humanity's daily rhythm wrapped around the
planet at this instant — a pattern, not just placement. Six buckets keeps it
uncluttered.

The moderator flagged that **Shape Map legend colors break on publish-to-web**.
Deneb (Vega + embedded TopoJSON) gives full control over fill, legend, and
projection and renders reliably in the gallery.

## Decisions locked during brainstorming

- **Mood:** "Aurora" — dark navy ocean (`#0B1026`), glowing neon vibe colors.
- **Buckets:** six (see palette below). Confirmed not too many/few.
- **Computation:** **live in Vega** (browser `now()`), not DAX `NOW()`. Shows the
  viewer's real current moment and works in publish-to-web with no refresh.
- **Interaction:** **in-Deneb** clickable-legend spotlight. A native Power BI
  slicer cannot filter a value that only exists in the browser, and an in-viz
  spotlight is cleaner anyway.
- **Granularity:** **country-level, one UTC offset per country** (capital /
  principal zone). Matches the contest sample and the "one category" read.
  Multi-zone giants (US, Russia) render as a single color — accepted.

## The six vibe buckets

Local-hour ranges, Aurora palette, and the gray used when a country is *not* the
spotlighted vibe:

| Vibe | Emoji | Local hours | Color |
|---|---|---|---|
| Asleep | 🌙 | 00:00–05:00 | `#2E3A59` |
| Sunrise & coffee | ☕ | 05:00–09:00 | `#FF7E6B` |
| Deep-focus morning | 💻 | 09:00–12:00 | `#2DD4BF` |
| Lunch / midday | 🍽️ | 12:00–15:00 | `#FBBF24` |
| Golden hour | 🌇 | 15:00–19:00 | `#FB7185` |
| Nightlife / evening | 🎉 | 19:00–24:00 | `#A78BFA` |

- Dimmed (non-selected) fill: `~#1B2236` (slightly above the ocean, low contrast).
- Ocean background: `#0B1026`. Subtle graticule in a low-alpha slate.

## Architecture

### Data flow

```
Countries table (model)  ──bound dataset──┐
  CountryId, UtcOffset                     │
                                           ▼
World TopoJSON (inlined in spec) ──► Vega lookup (join offset by id)
                                           │
                              now() + UtcOffset ► localHour ► vibe bucket
                                           │
                              geoshape mark, fill = vibe color scale
                                           │
                              clickable legend ► selectedVibe signal ► dim others
```

### 1. Semantic model — `Countries` table

One table, ~180 rows, one row per country.

| Column | Type | Notes |
|---|---|---|
| `CountryId` | whole number | ISO 3166-1 **numeric**; matches world-atlas feature `id` (the join key) |
| `CountryName` | text | display / tooltip |
| `UtcOffset` | decimal | hours, e.g. `5.5`, `5.75`, `-5`; **current May-2026 values** (DST-observing countries use their summer offset) |
| `Region` | text | continent grouping; reserved for future use / tooltip |

Authored as a TMDL table with a `calculated`/inline M source or a literal
`DATATABLE`-style partition. The exact source mechanism is an implementation
detail for the plan; the contract is the four columns above at country grain.

### 2. Geometry — embedded TopoJSON

- Source: **world-atlas `countries-110m.json`** (numeric ISO ids).
- **Inlined into the Deneb spec** as a named dataset — no external `url` (publish-to-web
  blocks external fetches). ~100 KB minified; acceptable in a Deneb spec.
- Antarctica (id `010`) filtered out.

### 3. Deneb spec (Vega, not Vega-Lite)

Vega proper is required for: the `now()` / timer signals, the topojson + lookup
join, the custom interactive-legend dim behavior, and the dynamic caption.

Key elements:
- `signals`:
  - `now` — a timer signal updating every 60 s (`{update: "now()"}` driven by a
    timer), with render-time evaluation as the guaranteed baseline.
  - `selectedVibe` — set by legend clicks; `null` = show all.
- `data`:
  - `world` — inline topojson, `format: {type:"topojson", feature:"countries"}`,
    Antarctica filtered.
  - `offsets` — the bound Power BI dataset.
  - `lookup` transform on `world` pulling `UtcOffset` (and `CountryName`) from
    `offsets` by `id`.
  - `formula`: `localHour = ((utchours(now)+utcminutes(now)/60) + datum.UtcOffset + 24) % 24`,
    then `vibe` via a threshold expression over the six ranges.
- `projection`: `naturalEarth1`, fit to canvas.
- `marks`:
  - ocean rect (`#0B1026`), optional graticule.
  - `geoshape` countries, fill = `vibeColor(datum.vibe)`, dimmed when
    `selectedVibe != null && datum.vibe != selectedVibe`.
  - text marks: title, subtitle, dynamic caption (count of countries in the
    current/selected vibe).
  - interactive legend (symbol + label per vibe) wired to `selectedVibe`.

### 4. Layout — full-canvas Deneb

Deneb owns the entire report page for pixel control and a single clean artifact:
- **Title** (top): "Where are the good vibes — right now?"
- **Subtitle** (one line): what the colors mean.
- **Map** (center, dominant).
- **Interactive legend** (bottom or right): six swatches, clickable.
- **Footnote** (tiny): "Local time computed live in your browser · UTC offsets as of May 2026."

## Live behavior & limitations

- **Render-time correctness (guaranteed):** the map opens at the viewer's real
  current moment.
- **60 s timer (progressive enhancement):** the vibe band visibly creeps west;
  if the Deneb sandbox throttles timers, it degrades gracefully to render-time.
- **DST caveat:** offsets are baked at May-2026 values. Correct for the contest
  window; a country viewed across a DST boundary later in the year could be off
  by an hour. A full timezone engine is out of scope.

## Validation

1. Author the spec; validate Vega syntax via the Deneb skill / reviewer.
2. Place the visual in the PBIR page (full-canvas), bind the `Countries` dataset.
3. Render in the open Power BI Desktop to confirm fill, legend click-to-spotlight,
   and that the current vibe band looks right for "now."

## Out of scope (noted for later)

- **Variant B** — clock-vs-sun deviation map (revisit after A ships, for A/B
  feedback from others).
- Splitting multi-zone giants (US / Canada / Russia / Australia / Brazil) into
  sub-regions.
- Full DST / IANA timezone engine.
