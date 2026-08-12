"""
Tests comparing countryry's behaviour against pycountry, exhaustively over
all records, for the shared core behaviour.
"""

from __future__ import annotations

import pycountry
import pytest

import countryry

DATABASES = [
    "countries",
    "historic_countries",
    "subdivisions",
    "currencies",
    "languages",
    "language_families",
    "scripts",
]


def pairs(name):
    return getattr(countryry, name), getattr(pycountry, name)


def norm(record):
    """A record as a comparable dict, replacing any linked subdivision with
    its code, since countryry and pycountry records have different types.
    Collections of records, from country code queries, compare as sorted
    lists."""
    if isinstance(record, (list, set)):
        return sorted((norm(r) for r in record), key=lambda fields: fields["code"])
    fields = dict(record)
    if "parent" in fields:
        fields["parent"] = fields["parent"].code
    return fields


def norm_repr(record):
    """A record's repr with pycountry's SubdivisionHierarchy class renamed,
    the one intended repr difference."""
    return repr(record).replace("SubdivisionHierarchy(", "Subdivision(")


@pytest.mark.parametrize("name", DATABASES)
def test_len_matches(name):
    ours, theirs = pairs(name)
    assert len(ours) == len(theirs)


@pytest.mark.parametrize("name", DATABASES)
def test_every_record_matches(name):
    ours, theirs = pairs(name)
    for actual, expected in zip(ours, theirs):
        assert norm(actual) == norm(expected)
        assert norm_repr(actual) == norm_repr(expected)


@pytest.mark.parametrize("name", DATABASES)
def test_get_every_indexed_value(name):
    ours, theirs = pairs(name)
    for expected in theirs:
        for field in theirs.indices:
            value = dict(expected).get(field)
            if not isinstance(value, str):
                continue
            actual = ours.get(**{field: value})
            assert norm(actual) == norm(theirs.get(**{field: value}))


@pytest.mark.parametrize("name", DATABASES)
def test_lookup_every_indexed_value(name):
    ours, theirs = pairs(name)
    for record in theirs:
        for field, value in dict(record).items():
            if field not in theirs.indices or not isinstance(value, str):
                continue
            assert norm(ours.lookup(value)) == norm(theirs.lookup(value))


def test_lookup_non_indexed_values():
    for value in ["I", "C", "Azerbaijani, North", "Swiss German"]:
        actual = countryry.languages.lookup(value)
        expected = pycountry.languages.lookup(value)
        assert norm(actual) == norm(expected)
    for value in ["California", "Metropolitan department", "FR-ARA"]:
        actual_sub = countryry.subdivisions.lookup(value)
        expected_sub = pycountry.subdivisions.lookup(value)
        assert norm(actual_sub) == norm(expected_sub)


def test_subdivisions_hierarchy_every_record():
    for actual, expected in zip(countryry.subdivisions, pycountry.subdivisions):
        assert actual.country_code == expected.country_code
        assert actual.parent_code == expected.parent_code
        assert norm(actual.country) == norm(expected.country)
        if expected.parent_code is None:
            assert actual.parent is None and expected.parent is None
        else:
            assert norm(actual.parent) == norm(expected.parent)


def test_subdivisions_get_country_code_every_country():
    for country in pycountry.countries:
        actual = countryry.subdivisions.get(country_code=country.alpha_2)
        expected = pycountry.subdivisions.get(country_code=country.alpha_2)
        # pycountry gives a set here where countryry gives a sorted list
        assert {s.code for s in actual} == {s.code for s in expected}


@pytest.mark.parametrize(
    "query",
    [
        "Germany",
        "germany",
        "DE",
        "de",
        "🇩🇪",
        "United",
        "United States",
        "USA",
        "UAE",
        "England",
        "berlin",
        "Bayern",
        "California",
        "york",
        "saint",
        "Korea",
        "Aland",
        "Åland",
        "Türkiye",
        "İstanbul",
        "Côte d'Ivoire",
        "congo",
        "new",
        "island",
    ],
)
def test_search_fuzzy_matches(query):
    actual = countryry.countries.search_fuzzy(query)
    expected = pycountry.countries.search_fuzzy(query)
    assert [c.alpha_2 for c in actual] == [c.alpha_2 for c in expected]


@pytest.mark.parametrize(
    "query",
    ["California", "Bayern", "saint", "İstanbul", "Auvergne", "york"],
)
def test_search_fuzzy_subdivisions_matches(query):
    actual = countryry.subdivisions.search_fuzzy(query)
    expected = pycountry.subdivisions.search_fuzzy(query)
    assert [s.code for s in actual] == [s.code for s in expected]


def test_search_fuzzy_missing_matches():
    with pytest.raises(LookupError):
        countryry.countries.search_fuzzy("zzzz")
    with pytest.raises(LookupError):
        pycountry.countries.search_fuzzy("zzzz")


@pytest.mark.parametrize("name", DATABASES)
def test_get_errors_match(name):
    ours, theirs = pairs(name)
    for db in [ours, theirs]:
        with pytest.raises(TypeError):
            db.get()
        with pytest.raises(TypeError):
            db.get(a="x", b="y")
        with pytest.raises(LookupError):
            db.get(name=123)
        with pytest.raises(KeyError):
            db.get(nope="x")


@pytest.mark.parametrize("name", DATABASES)
def test_lookup_errors_match(name):
    ours, theirs = pairs(name)
    messages = set()
    for db in [ours, theirs]:
        with pytest.raises(LookupError):
            db.lookup(123)
        with pytest.raises(LookupError) as excinfo:
            db.lookup("zzzzzz")
        messages.add(str(excinfo.value))
    assert len(messages) == 1
