from __future__ import annotations

import subprocess
import sys

import pytest

import countryry


def test_countries_len():
    assert len(countryry.countries) == 249


def test_countries_iter():
    first = next(iter(countryry.countries))
    assert first.alpha_2 == "AW"
    assert len(list(countryry.countries)) == 249


def test_countries_get():
    country = countryry.countries.get(alpha_2="DE")
    assert country.alpha_2 == "DE"
    assert country.alpha_3 == "DEU"
    assert country.numeric == "276"
    assert country.name == "Germany"
    assert country.official_name == "Federal Republic of Germany"
    assert country.flag == "🇩🇪"


def test_countries_get_case_insensitive():
    assert countryry.countries.get(alpha_2="de").name == "Germany"
    assert countryry.countries.get(name="germany").alpha_2 == "DE"


def test_countries_get_every_field():
    assert countryry.countries.get(alpha_3="FRA").alpha_2 == "FR"
    assert countryry.countries.get(numeric="250").alpha_2 == "FR"
    assert countryry.countries.get(flag="🇫🇷").alpha_2 == "FR"
    assert countryry.countries.get(common_name="Bolivia").alpha_2 == "BO"
    assert countryry.countries.get(official_name="French Republic").alpha_2 == "FR"


def test_countries_get_missing():
    assert countryry.countries.get(alpha_2="XX") is None
    assert countryry.countries.get(alpha_2="XX", default="nope") == "nope"


def test_countries_get_criteria_count():
    with pytest.raises(TypeError):
        countryry.countries.get()
    with pytest.raises(TypeError):
        countryry.countries.get(alpha_2="DE", alpha_3="DEU")


def test_countries_get_non_string():
    with pytest.raises(LookupError):
        countryry.countries.get(numeric=276)
    with pytest.raises(LookupError):
        countryry.countries.get(alpha_2=None)


def test_countries_get_unknown_field():
    with pytest.raises(KeyError):
        countryry.countries.get(nope="DE")


def test_countries_lookup():
    assert countryry.countries.lookup("de").alpha_2 == "DE"
    assert countryry.countries.lookup("DEU").alpha_2 == "DE"
    assert countryry.countries.lookup("germany").alpha_2 == "DE"
    assert countryry.countries.lookup("🇩🇪").alpha_2 == "DE"


def test_countries_lookup_missing():
    with pytest.raises(LookupError) as excinfo:
        countryry.countries.lookup("zzzz")
    assert str(excinfo.value) == "Could not find a record for 'zzzz'"


def test_countries_lookup_non_string():
    with pytest.raises(LookupError):
        countryry.countries.lookup(276)


def test_countries_search_fuzzy():
    results = countryry.countries.search_fuzzy("Germany")
    assert results[0].alpha_2 == "DE"


def test_countries_search_fuzzy_subdivision_match():
    results = countryry.countries.search_fuzzy("berlin")
    assert results[0].alpha_2 == "DE"


def test_countries_search_fuzzy_initials():
    results = countryry.countries.search_fuzzy("USA")
    assert results[0].alpha_2 == "US"


def test_countries_search_fuzzy_accents():
    results = countryry.countries.search_fuzzy("Aland")
    assert results[0].alpha_2 == "AX"


def test_countries_search_fuzzy_missing():
    with pytest.raises(LookupError):
        countryry.countries.search_fuzzy("zzzz")


def test_country_repr():
    country = countryry.countries.get(alpha_2="AW")
    assert repr(country) == (
        "Country(alpha_2='AW', alpha_3='ABW', flag='🇦🇼', name='Aruba', numeric='533')"
    )


def test_country_missing_attribute():
    country = countryry.countries.get(alpha_2="AW")
    with pytest.raises(AttributeError):
        _ = country.official_name
    with pytest.raises(AttributeError):
        _ = country.nope


def test_country_dict():
    country = countryry.countries.get(alpha_2="AW")
    assert dict(country) == {
        "alpha_2": "AW",
        "alpha_3": "ABW",
        "flag": "🇦🇼",
        "name": "Aruba",
        "numeric": "533",
    }


def test_country_equality():
    assert countryry.countries.get(alpha_2="DE") == countryry.countries.lookup("de")
    assert countryry.countries.get(alpha_2="DE") != countryry.countries.get(
        alpha_2="FR"
    )
    assert len({c.alpha_2 for c in countryry.countries}) == 249
    assert len(set(countryry.countries)) == 249


def test_historic_countries():
    assert len(countryry.historic_countries) == 31
    country = countryry.historic_countries.get(alpha_4="DDDE")
    assert country.name == "German Democratic Republic"
    assert country.withdrawal_date == "1990-10-30"
    assert countryry.historic_countries.lookup("zaire, republic of").alpha_4 == "ZRCD"


def test_subdivisions_len():
    assert len(countryry.subdivisions) == 5046


def test_subdivisions_get():
    subdivision = countryry.subdivisions.get(code="US-CA")
    assert subdivision.code == "US-CA"
    assert subdivision.name == "California"
    assert subdivision.type == "State"
    assert subdivision.country_code == "US"


def test_subdivisions_hierarchy():
    subdivision = countryry.subdivisions.get(code="FR-01")
    assert subdivision.parent_code == "FR-ARA"
    assert subdivision.parent.name == "Auvergne-Rhône-Alpes"
    assert subdivision.parent.parent_code is None
    assert subdivision.parent.parent is None
    assert subdivision.country.alpha_2 == "FR"


def test_subdivisions_get_country_code():
    subdivisions = countryry.subdivisions.get(country_code="US")
    assert len(subdivisions) == 57
    assert all(s.country_code == "US" for s in subdivisions)
    # A known country with no subdivisions gives an empty list
    assert countryry.subdivisions.get(country_code="AQ") == []
    # An unknown country gives the default
    assert countryry.subdivisions.get(country_code="XX") is None
    assert countryry.subdivisions.get(country_code="XX", default=1) == 1


def test_subdivisions_get_non_indexed_field():
    with pytest.raises(KeyError):
        countryry.subdivisions.get(name="California")


def test_subdivisions_lookup():
    assert countryry.subdivisions.lookup("US-CA").name == "California"
    assert countryry.subdivisions.lookup("California").code == "US-CA"
    # A country code looks up the country's subdivisions
    assert len(countryry.subdivisions.lookup("us")) == 57


def test_subdivisions_search_fuzzy():
    results = countryry.subdivisions.search_fuzzy("California")
    assert results[0].code == "US-CA"
    with pytest.raises(LookupError):
        countryry.subdivisions.search_fuzzy("zzzz")


def test_subdivision_repr():
    subdivision = countryry.subdivisions.get(code="US-CA")
    assert repr(subdivision) == (
        "Subdivision(code='US-CA', country_code='US', name='California', "
        "parent_code=None, type='State')"
    )


def test_subdivision_dict():
    subdivision = countryry.subdivisions.get(code="FR-01")
    as_dict = dict(subdivision)
    assert as_dict["code"] == "FR-01"
    assert as_dict["parent_code"] == "FR-ARA"
    assert as_dict["parent"] == countryry.subdivisions.get(code="FR-ARA")


def test_currencies():
    assert len(countryry.currencies) == 178
    currency = countryry.currencies.get(alpha_3="EUR")
    assert currency.name == "Euro"
    assert currency.numeric == "978"
    assert countryry.currencies.lookup("euro").alpha_3 == "EUR"


def test_languages():
    assert len(countryry.languages) == 7923
    language = countryry.languages.get(alpha_2="de")
    assert language.alpha_3 == "deu"
    assert language.name == "German"
    assert language.bibliographic == "ger"
    assert countryry.languages.get(alpha_3="eng").name == "English"


def test_languages_get_non_indexed_field():
    with pytest.raises(KeyError):
        countryry.languages.get(scope="I")


def test_languages_lookup_non_indexed():
    # inverted_name is only searched by lookup()
    language = countryry.languages.lookup("german")
    assert language.alpha_3 == "deu"
    assert countryry.languages.lookup("Azerbaijani, North").alpha_3 == "azj"


def test_language_families():
    assert len(countryry.language_families) == 115
    family = countryry.language_families.get(alpha_3="gem")
    assert family.name == "Germanic languages"


def test_scripts():
    assert len(countryry.scripts) == 226
    script = countryry.scripts.get(alpha_4="Latn")
    assert script.name == "Latin"
    assert script.numeric == "215"
    assert countryry.scripts.lookup("latin").alpha_4 == "Latn"


def test_import_runs_standalone():
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import countryry; "
            "assert countryry.countries.get(alpha_2='DE').name == 'Germany'",
        ],
        check=True,
        timeout=120,
    )
