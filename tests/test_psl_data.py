"""
Tests running every checkPublicSuffix() case from the Public Suffix List's
own test data against privatesuffix().

The data file is vendored direct from the list's source repository -
update it with scripts/generate_data.py.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import pslr

TEST_DATA = Path(__file__).parent / "data" / "test_psl.txt"


def parse_value(value: str) -> str | None:
    if value == "null":
        return None
    assert value.startswith("'") and value.endswith("'")
    return value[1:-1]


def parse_cases() -> list[tuple[str | None, str | None]]:
    cases = []
    for line in TEST_DATA.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        match = re.fullmatch(r"checkPublicSuffix\((.+), (.+)\);", line)
        assert match is not None, line
        cases.append((parse_value(match[1]), parse_value(match[2])))
    return cases


def test_parse_cases():
    cases = parse_cases()
    assert len(cases) > 50
    assert ("example.COM", "example.com") in cases


@pytest.mark.parametrize(("domain", "expected"), parse_cases())
def test_check_public_suffix(domain, expected):
    if domain is None:
        with pytest.raises(TypeError):
            pslr.privatesuffix(domain)
    else:
        assert pslr.privatesuffix(domain) == expected
