"""
build_tmdl.py
Reads build/countries.json and writes the Countries TMDL table file.

Partition style: inline M partition using #table(...) literal.
This is preferred for static data with no external source dependency.
In M/Power Query, strings are delimited with " and interior " must be
escaped as "". The generator handles this plus preserves UTF-8.
"""

import json
import pathlib
import uuid

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

INPUT_JSON = REPO_ROOT / "build" / "countries.json"
OUTPUT_DIR = REPO_ROOT / "minviz-week4.SemanticModel" / "definition" / "tables"
OUTPUT_FILE = OUTPUT_DIR / "Countries.tmdl"

# Fixed lineage tags so the file is deterministic across re-runs.
# Generated once here; do NOT change after first commit.
TABLE_LINEAGE_TAG   = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
COL_COUNTRY_ID_TAG  = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
COL_COUNTRY_NAME_TAG = "c3d4e5f6-a7b8-9012-cdef-123456789012"
COL_UTC_OFFSET_TAG  = "d4e5f6a7-b8c9-0123-defa-234567890123"
COL_REGION_TAG      = "e5f6a7b8-c9d0-1234-efab-345678901234"
PARTITION_LINEAGE_TAG = "f6a7b8c9-d0e1-2345-fabc-456789012345"


def m_escape_string(s: str) -> str:
    """Escape a string value for use inside an M double-quoted string literal.
    In M, the only escape needed is doubling internal double-quote characters.
    The function returns the value WITHOUT surrounding quotes so the caller
    can wrap as needed.
    """
    return s.replace('"', '""')


def format_number(v) -> str:
    """Format a float for M: no trailing .0 for integers, preserve decimals."""
    if isinstance(v, int):
        return str(v)
    # For floats that are whole numbers, emit as integer literal (cleaner).
    if v == int(v):
        return str(int(v))
    return str(v)


def main():
    with open(INPUT_JSON, encoding="utf-8") as f:
        countries = json.load(f)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build the #table row list.
    # Each row: { CountryId, CountryName, UtcOffset, Region }
    # M row syntax: { <int>, "<escaped string>", <number>, "<escaped string>" }
    row_lines = []
    for c in countries:
        country_id   = c["CountryId"]
        country_name = m_escape_string(c["CountryName"])
        utc_offset   = format_number(c["UtcOffset"])
        region       = m_escape_string(c["Region"])
        row_lines.append(
            f'\t\t\t\t\t{{ {country_id}, "{country_name}", {utc_offset}, "{region}" }}'
        )

    rows_block = ",\n".join(row_lines)

    # TMDL uses tabs for indentation.
    # Depths:
    #   0: table declaration
    #   1: table properties, column/partition declarations
    #   2: column/partition properties
    #   3: DAX/M body (2 levels deeper than the declaration at depth 1)
    #
    # For a partition declared at depth 1, the M source body is at depth 3.
    # The #table literal spans many lines; each continuation line is at depth 3+
    # (we use 5 tabs for the data rows to keep them cleanly nested inside the
    # type list and row list brackets).

    tmdl = (
        f"table Countries\n"
        f"\tlineageTag: {TABLE_LINEAGE_TAG}\n"
        f"\n"
        f"\tcolumn CountryId\n"
        f"\t\tdataType: int64\n"
        f"\t\tisKey\n"
        f"\t\tlineageTag: {COL_COUNTRY_ID_TAG}\n"
        f"\t\tsummarizeBy: none\n"
        f"\t\tsourceColumn: CountryId\n"
        f"\n"
        f"\t\tannotation SummarizationSetBy = Automatic\n"
        f"\n"
        f"\tcolumn CountryName\n"
        f"\t\tdataType: string\n"
        f"\t\tlineageTag: {COL_COUNTRY_NAME_TAG}\n"
        f"\t\tsummarizeBy: none\n"
        f"\t\tsourceColumn: CountryName\n"
        f"\n"
        f"\t\tannotation SummarizationSetBy = Automatic\n"
        f"\n"
        f"\tcolumn UtcOffset\n"
        f"\t\tdataType: double\n"
        f"\t\tlineageTag: {COL_UTC_OFFSET_TAG}\n"
        f"\t\tsummarizeBy: none\n"
        f"\t\tsourceColumn: UtcOffset\n"
        f"\n"
        f"\t\tannotation SummarizationSetBy = Automatic\n"
        f"\n"
        f"\tcolumn Region\n"
        f"\t\tdataType: string\n"
        f"\t\tlineageTag: {COL_REGION_TAG}\n"
        f"\t\tsummarizeBy: none\n"
        f"\t\tsourceColumn: Region\n"
        f"\n"
        f"\t\tannotation SummarizationSetBy = Automatic\n"
        f"\n"
        f"\tpartition Countries = m\n"
        f"\t\tmode: import\n"
        f"\t\tsource =\n"
        f"\t\t\t\tlet\n"
        f"\t\t\t\t    Source = #table(\n"
        f"\t\t\t\t        type table [\n"
        f"\t\t\t\t            CountryId = Int64.Type,\n"
        f"\t\t\t\t            CountryName = text,\n"
        f"\t\t\t\t            UtcOffset = number,\n"
        f"\t\t\t\t            Region = text\n"
        f"\t\t\t\t        ],\n"
        f"\t\t\t\t        {{\n"
        f"{rows_block}\n"
        f"\t\t\t\t        }}\n"
        f"\t\t\t\t    )\n"
        f"\t\t\t\tin\n"
        f"\t\t\t\t    Source\n"
        f"\n"
        f"\tannotation PBI_ResultType = Table\n"
        f"\n"
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(tmdl)

    print(f"Written: {OUTPUT_FILE}")
    print(f"Rows: {len(countries)}")

    # Spot-check key entries
    spot_checks = {356: None, 524: None, 840: None, 384: None}
    for c in countries:
        if c["CountryId"] in spot_checks:
            spot_checks[c["CountryId"]] = c

    print("\nSpot checks:")
    for cid, c in spot_checks.items():
        print(f"  [{cid}] {c['CountryName']} / UTC {c['UtcOffset']} / {c['Region']}")


if __name__ == "__main__":
    main()
