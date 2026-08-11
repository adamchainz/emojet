from __future__ import annotations

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

import swifter


@given(st.text())
@example("DE89 3704 0044 0532 0130 00")
def test_iban_fuzz(value):
    iban = swifter.IBAN(value, allow_invalid=True)
    assert isinstance(iban.compact, str)
    assert isinstance(iban.is_valid, bool)
    if iban.is_valid:
        assert iban.validate() is True
    else:
        with pytest.raises(swifter.SwifterError):
            iban.validate()


@given(st.text())
@example("GENODEM1GLS")
def test_bic_fuzz(value):
    bic = swifter.BIC(value, allow_invalid=True)
    assert isinstance(bic.compact, str)
    assert isinstance(bic.is_valid, bool)
    if bic.is_valid:
        assert bic.validate() is True
    else:
        with pytest.raises(swifter.SwifterError):
            bic.validate()


@given(
    bank_code=st.integers(0, 10**8 - 1),
    account_code=st.integers(0, 10**10 - 1),
)
def test_iban_generate_valid(bank_code, account_code):
    iban = swifter.IBAN.generate(
        "DE", bank_code=str(bank_code), account_code=str(account_code)
    )
    assert iban.is_valid
    assert iban.bank_code == str(bank_code).zfill(8)
    assert iban.account_code == str(account_code).zfill(10)


@given(
    bank_code=st.integers(0, 10**8 - 1),
    account_code=st.integers(0, 10**10 - 1),
)
def test_iban_formatted_round_trips(bank_code, account_code):
    iban = swifter.IBAN.generate(
        "DE", bank_code=str(bank_code), account_code=str(account_code)
    )
    assert swifter.IBAN(iban.formatted) == iban


@given(
    account_code=st.integers(0, 10**10 - 1),
    position=st.integers(4, 21),
    offset=st.integers(1, 9),
)
def test_iban_single_digit_change_detected(account_code, position, offset):
    # The mod-97-10 checksum catches every single-digit substitution.
    iban = swifter.IBAN.generate(
        "DE", bank_code="37040044", account_code=str(account_code)
    )
    compact = iban.compact
    changed = str((int(compact[position]) + offset) % 10)
    corrupted = compact[:position] + changed + compact[position + 1 :]
    assert not swifter.IBAN(corrupted, allow_invalid=True).is_valid
