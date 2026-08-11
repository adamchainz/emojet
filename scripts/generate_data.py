# /// script
# requires-python = ">=3.12"
# ///
"""
Generate the static Rust data tables (src/data.rs) for swifter, by
downloading the data from its original sources:

* The SWIFT IBAN Registry, as the TXT release linked from |the SWIFT
  data standards page|: the IBAN specification per country - BBAN
  structure, IBAN length, SEPA membership, and the positions of the bank
  and branch codes within the BBAN.

* The ISO 3166-1 alpha-2 country codes, used to validate the country
  code of BICs, from the Debian iso-codes project, the canonical open
  dataset of the ISO 3166 standard.

The downloads are combined with the checked-in seed file
scripts/seeds/registry_overrides.json - see CONTRIBUTING.rst.

Run with uv:

    uv run scripts/generate_data.py

.. |the SWIFT data standards page| replace::
   https://www.swift.com/standards/data-standards/iban
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

REGISTRY_PAGE_URL = "https://www.swift.com/standards/data-standards/iban"
ISO3166_URL = (
    "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_3166-1.json"
)

HERE = Path(__file__).parent.resolve()
SEEDS = HERE / "seeds"
DATA_RS = HERE / ".." / "src" / "data.rs"

Record = dict[str, Any]

COUNTRY_CODE_RE = re.compile(r"[A-Z]{2}")
EMPTY_RANGE = (0, 0)

CHAR_CLASSES = {
    "n": 0,  # digits
    "a": 1,  # uppercase letters
    "c": 2,  # uppercase letters and digits
}

GROUP_RE = re.compile(r"(\d+)!([nac])")


def http_get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "swifter-data-build"})
    with urllib.request.urlopen(request) as response:
        data: bytes = response.read()
    return data


def fetch_registry() -> str:
    """Download the IBAN Registry TXT release linked from the SWIFT page."""
    page = http_get(REGISTRY_PAGE_URL).decode("utf-8", errors="replace")
    for pattern in (
        r'<a\b[^>]*?href="([^"]+)"[^>]*?data-tracking-title="IBAN Registry \(TXT\)"',
        r'<a\b[^>]*?data-tracking-title="IBAN Registry \(TXT\)"[^>]*?href="([^"]+)"',
    ):
        match = re.search(pattern, page)
        if match:
            return http_get(urljoin(REGISTRY_PAGE_URL, match[1])).decode("latin1")
    raise ValueError("Cannot find the IBAN Registry (TXT) link")


def parse_int(raw: str) -> int:
    match = re.search(r"\d+", raw)
    return int(match[0]) if match else 0


def parse_range(raw: str) -> tuple[int, int]:
    """Parse a position like "1-4" into a zero-based (start, end) range."""
    match = re.search(r".*?(?P<from>\d+)\s*-\s*(?P<to>\d+)", raw)
    if not match:
        return EMPTY_RANGE
    return (int(match["from"]) - 1, int(match["to"]))


def parse_registry(raw: str) -> dict[str, Record]:
    """Parse the registry TXT, a transposed table of tab-separated lines,
    into a record per country code, expanding the territories that share
    another country's IBAN format."""
    columns: dict[str, list[Any]] = {}
    for line in raw.split("\r\n"):
        header, *rows = line.split("\t")
        if header == "IBAN prefix country code (ISO 3166)":
            columns["country"] = [
                match[0] if (match := COUNTRY_CODE_RE.search(item)) else ""
                for item in rows
            ]
        elif header == "Country code includes other countries/territories":
            columns["other_countries"] = [
                COUNTRY_CODE_RE.findall(item) for item in rows
            ]
        elif header == "BBAN structure":
            columns["bban_spec"] = rows
        elif header == "BBAN length":
            columns["bban_length"] = [parse_int(item) for item in rows]
        elif header == "Bank identifier position within the BBAN":
            columns["bank_code"] = [parse_range(item) for item in rows]
        elif header == "Branch identifier position within the BBAN":
            columns["branch_code"] = [parse_range(item) for item in rows]
        elif header == "IBAN length":
            columns["iban_length"] = [parse_int(item) for item in rows]
        elif header == "SEPA country":
            columns["in_sepa_zone"] = [item.lower() == "yes" for item in rows]

    registry = {}
    for row in zip(*columns.values(), strict=True):
        record = dict(zip(columns.keys(), row, strict=True))
        bank_code = record.pop("bank_code")
        branch_code = record.pop("branch_code")
        record["positions"] = {
            "account_code": (
                max(bank_code[1], branch_code[1]),
                record["bban_length"],
            ),
            "bank_code": bank_code,
        }
        if branch_code != EMPTY_RANGE:
            record["positions"]["branch_code"] = branch_code
        for code in [record.pop("country"), *record.pop("other_countries")]:
            registry[code] = {"country": code, **record}
    return registry


def merge_dicts(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Merge nested dicts, with the right-hand side winning."""
    merged = dict(left)
    for key, right_value in right.items():
        left_value = merged.get(key)
        if isinstance(left_value, dict) and isinstance(right_value, dict):
            merged[key] = merge_dicts(left_value, right_value)
        else:
            merged[key] = right_value
    return merged


def fetch_country_codes() -> list[str]:
    data = json.loads(http_get(ISO3166_URL))
    return sorted(entry["alpha_2"] for entry in data["3166-1"])


def parse_bban_spec(spec: str) -> list[tuple[int, int]]:
    """Parse a BBAN structure like "8!n10!n" into (length, class) groups."""
    groups = []
    end = 0
    for match in GROUP_RE.finditer(spec):
        if match.start() != end:
            raise ValueError(f"Cannot parse BBAN spec: {spec!r}")
        end = match.end()
        groups.append((int(match[1]), CHAR_CLASSES[match[2]]))
    if end != len(spec):
        raise ValueError(f"Cannot parse BBAN spec: {spec!r}")
    return groups


def rust_range(positions: dict[str, Any], component: str) -> str:
    start, end = positions.get(component, EMPTY_RANGE)
    return f"({start}, {end})"


def write_data_rs(registry: dict[str, Record], country_codes: list[str]) -> None:
    lines = [
        "// Generated by scripts/generate_data.py - do not edit directly.",
        "",
        "pub struct IbanSpec {",
        "    pub country: &'static str,",
        "    pub iban_length: u8,",
        "    pub in_sepa_zone: bool,",
        "    // BBAN structure as (length, character class) groups, where the",
        "    // classes are 0 = digits, 1 = letters, 2 = letters and digits.",
        "    pub groups: &'static [(u8, u8)],",
        "    // Component positions within the BBAN, as (start, end) ranges.",
        "    pub bank_code: (u8, u8),",
        "    pub branch_code: (u8, u8),",
        "    pub account_code: (u8, u8),",
        "    pub national_checksum_digits: (u8, u8),",
        "}",
        "",
        "// Sorted by country code, for binary search.",
        "pub static IBAN_SPECS: &[IbanSpec] = &[",
    ]
    for country, record in sorted(registry.items()):
        groups = parse_bban_spec(record["bban_spec"])
        bban_length = sum(length for length, _ in groups)
        if bban_length + 4 != record["iban_length"]:
            raise ValueError(f"Length mismatch for {country}")
        positions = record.get("positions", {})
        for start, end in positions.values():
            if not (0 <= start <= end <= bban_length):
                raise ValueError(f"Position out of range for {country}")
        groups_rs = ", ".join(f"({length}, {cls})" for length, cls in groups)
        lines.append(
            "    IbanSpec { "
            f'country: "{country}", '
            f"iban_length: {record['iban_length']}, "
            f"in_sepa_zone: {str(record['in_sepa_zone']).lower()}, "
            f"groups: &[{groups_rs}], "
            f"bank_code: {rust_range(positions, 'bank_code')}, "
            f"branch_code: {rust_range(positions, 'branch_code')}, "
            f"account_code: {rust_range(positions, 'account_code')}, "
            "national_checksum_digits: "
            f"{rust_range(positions, 'national_checksum_digits')} "
            "},"
        )
    lines.extend(
        [
            "];",
            "",
            "// ISO 3166-1 alpha-2 country codes, sorted for binary search.",
            "pub static ISO3166_COUNTRIES: &[&str] = &[",
        ]
    )
    for start in range(0, len(country_codes), 12):
        row = ", ".join(f'"{code}"' for code in country_codes[start : start + 12])
        lines.append(f"    {row},")
    lines.extend(["];", ""])

    DATA_RS.write_text("\n".join(lines))
    print(f"Wrote {DATA_RS.resolve()}: {len(registry)} IBAN specs")


def main() -> None:
    overrides = json.loads((SEEDS / "registry_overrides.json").read_text())
    registry = merge_dicts(parse_registry(fetch_registry()), overrides)
    write_data_rs(registry, fetch_country_codes())


if __name__ == "__main__":
    main()
