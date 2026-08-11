from __future__ import annotations

import random
from importlib.metadata import version

import pytest
import schwifty
import schwifty.exceptions

import swifter

# swifter's registry data is derived from this schwifty version.
pytestmark = pytest.mark.skipif(
    version("schwifty") != "2026.7.3",
    reason="Compatibility tests target the seed data's schwifty version.",
)


def random_ibans() -> list[schwifty.IBAN]:
    """A reproducible random valid IBAN for every registered country."""
    rng = random.Random(20260811)
    ibans = []
    for country_code in swifter.COUNTRY_CODES:
        for _ in range(10):
            try:
                ibans.append(
                    schwifty.IBAN.random(country_code, random=rng, use_registry=False)
                )
            except schwifty.exceptions.SchwiftyException:
                continue
            break
    return ibans


@pytest.mark.parametrize("theirs", random_ibans(), ids=str)
def test_iban_components_match(theirs):
    ours = swifter.IBAN(str(theirs))
    assert ours.compact == theirs.compact
    assert ours.formatted == theirs.formatted
    assert ours.country_code == theirs.country_code
    assert ours.checksum_digits == theirs.checksum_digits
    assert ours.bban == str(theirs.bban)
    assert ours.bank_code == theirs.bank_code
    assert ours.branch_code == theirs.branch_code
    assert ours.account_code == theirs.account_code
    assert ours.national_checksum_digits == theirs.bban.national_checksum_digits
    assert ours.in_sepa_zone == theirs.in_sepa_zone


def test_country_codes_match_registry():
    theirs = {
        schwifty.registry.get_iban_spec(country_code).country
        for country_code in swifter.COUNTRY_CODES
    }
    assert set(swifter.COUNTRY_CODES) == theirs


@pytest.mark.parametrize(
    "value",
    [
        "DE99370400440532013000",
        "DE8937040044053201300",
        "DE8937040044053201300E",
        "XX82WEST12345698765432",
        "1282WEST12345698765432",
    ],
)
def test_iban_errors_match(value):
    with pytest.raises(schwifty.exceptions.SchwiftyException) as their_error:
        schwifty.IBAN(value)
    with pytest.raises(swifter.SwifterError) as our_error:
        swifter.IBAN(value)
    assert type(our_error.value).__name__ == type(their_error.value).__name__


@pytest.mark.parametrize(
    "value",
    [
        "GENODEM1GLS",
        "GENODEFF",
        "GENODEM0GLS",
        "BNPAFRPPXXX",
    ],
)
def test_bic_components_match(value):
    theirs = schwifty.BIC(value)
    ours = swifter.BIC(value)
    assert ours.compact == theirs.compact
    assert ours.formatted == theirs.formatted
    assert ours.bank_code == theirs.bank_code
    assert ours.country_code == theirs.country_code
    assert ours.location_code == theirs.location_code
    assert ours.branch_code == theirs.branch_code
    assert ours.type == theirs.type


@pytest.mark.parametrize(
    "value",
    [
        "GENODEM1G",
        "GENO12M1",
        "GENOXXM1GLS",
    ],
)
def test_bic_errors_match(value):
    with pytest.raises(schwifty.exceptions.SchwiftyException) as their_error:
        schwifty.BIC(value)
    with pytest.raises(swifter.SwifterError) as our_error:
        swifter.BIC(value)
    assert type(our_error.value).__name__ == type(their_error.value).__name__


def test_generate_matches():
    theirs = schwifty.IBAN.generate(
        "DE", bank_code="37040044", account_code="532013000"
    )
    ours = swifter.IBAN.generate("DE", bank_code="37040044", account_code="532013000")
    assert ours.compact == theirs.compact


def test_from_bban_matches():
    theirs = schwifty.IBAN.from_bban("DE", "370400440532013000")
    ours = swifter.IBAN.from_bban("DE", "370400440532013000")
    assert ours.compact == theirs.compact
