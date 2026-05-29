# scripts/build_countries.py
"""Emit build/countries.json: one row per country with ISO-numeric id,
name, current UTC offset (decimal hours), and region.
Offsets are DST-aware as of run time (contest window = May 2026)."""
import json, datetime, os
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
os.makedirs("build", exist_ok=True)
with open("build/countries.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)
print(f"Wrote {len(rows)} countries")
