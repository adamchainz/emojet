"""
Property-based tests, generating queries from ISO-data-aware fragments.

The first group checks invariants between countryry's databases, the second
compares behaviour against pycountry.

Run with more examples by selecting the "thorough" profile:

    pytest tests/test_properties.py --hypothesis-profile=thorough
"""

from __future__ import annotations

import pycountry
from hypothesis import example, given
from hypothesis import strategies as st

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

SUBDIVISIONS = list(countryry.subdivisions)

# Every field value of every record, the raw material for queries.
ALL_VALUES = sorted(
    {
        value
        for name in DATABASES
        for record in getattr(countryry, name)
        for value in dict(record).values()
        if isinstance(value, str)
    }
)

FIELD_NAMES = sorted(
    {
        field
        for name in DATABASES
        for record in getattr(countryry, name)
        for field in dict(record)
    }
)

values = (
    st.sampled_from(ALL_VALUES)
    | st.sampled_from(ALL_VALUES).map(str.upper)
    | st.sampled_from(ALL_VALUES).map(str.swapcase)
    | st.sampled_from(ALL_VALUES).map(lambda v: v[: len(v) // 2])
    | st.text(max_size=8)
)
databases = st.sampled_from(DATABASES)
fields = st.sampled_from(FIELD_NAMES) | st.just("nope")


def norm(result):
    """A comparable form of a get() or lookup() result, replacing records
    with dicts and linked subdivisions with their codes, since countryry
    and pycountry records have different types."""
    if result is None or isinstance(result, str):
        return result
    if isinstance(result, (list, set)):
        return sorted((norm(r) for r in result), key=lambda fields: fields["code"])
    fields = dict(result)
    if "parent" in fields:
        fields["parent"] = fields["parent"].code
    return fields


def outcome(func):
    """The result of a call as comparable data: its normalized return value,
    or the name of the exception type it raised."""
    try:
        return norm(func())
    except Exception as exc:
        return type(exc).__name__


# Invariants between countryry databases


@given(databases, values)
@example("countries", "DE")
@example("subdivisions", "us")
@example("languages", "Swiss German")
def test_lookup_result_contains_value(name, value):
    # Any single record that lookup() finds must hold the value, in some
    # field, matched case-insensitively
    database = getattr(countryry, name)
    try:
        found = database.lookup(value)
    except LookupError:
        return
    if isinstance(found, list):
        # A country code looks up the country's subdivisions
        assert all(s.country_code.lower() == value.lower() for s in found)
    else:
        assert any(
            isinstance(v, str) and v.lower() == value.lower()
            for v in dict(found).values()
        )


@given(databases, values)
@example("countries", "DE")
def test_get_result_holds_value(name, value):
    # get() by an indexed field returns a record holding that value
    database = getattr(countryry, name)
    field = "code" if name == "subdivisions" else "name"
    found = database.get(**{field: value})
    if found is not None:
        assert dict(found)[field].lower() == value.lower()


@given(st.sampled_from(range(len(SUBDIVISIONS))))
def test_subdivision_hierarchy_consistent(index):
    subdivision = SUBDIVISIONS[index]
    assert subdivision.code.startswith(subdivision.country_code + "-")
    assert subdivision.country.alpha_2 == subdivision.country_code
    in_country = countryry.subdivisions.get(country_code=subdivision.country_code)
    assert subdivision in in_country
    if subdivision.parent_code is None:
        assert subdivision.parent is None
    else:
        assert subdivision.parent.code == subdivision.parent_code
        assert subdivision.parent.country_code == subdivision.country_code


# Differential properties against pycountry


@given(databases, fields, values)
@example("countries", "alpha_2", "de")
@example("subdivisions", "country_code", "US")
@example("subdivisions", "country_code", "AQ")
@example("subdivisions", "name", "California")
@example("languages", "scope", "I")
def test_get_matches(name, field, value):
    ours = getattr(countryry, name)
    theirs = getattr(pycountry, name)
    assert outcome(lambda: ours.get(**{field: value})) == outcome(
        lambda: theirs.get(**{field: value})
    )


@given(databases, values)
@example("countries", "🇩🇪")
@example("subdivisions", "us")
@example("languages", "Swiss German")
def test_lookup_matches(name, value):
    ours = getattr(countryry, name)
    theirs = getattr(pycountry, name)
    assert outcome(lambda: ours.lookup(value)) == outcome(lambda: theirs.lookup(value))


@given(values)
@example("USA")
@example("İstanbul")
@example(" berlin ")
@example("")
def test_search_fuzzy_matches(query):
    def fuzzy(database):
        try:
            return [country.alpha_2 for country in database.search_fuzzy(query)]
        except LookupError:
            return "LookupError"

    assert fuzzy(countryry.countries) == fuzzy(pycountry.countries)
