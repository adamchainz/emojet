from __future__ import annotations

import operator

import pytest

import swifter

VALID_IBANS = [
    "AD1200012030200359100100",
    "AT611904300234573201",
    "BE68539007547034",
    "CH9300762011623852957",
    "DE89370400440532013000",
    "ES9121000418450200051332",
    "FR1420041010050500013M02606",
    "GB29NWBK60161331926819",
    "GR1601101250000000012300695",
    "IT60X0542811101000000123456",
    "NL91ABNA0417164300",
    "NO9386011117947",
    "PL61109010140000071219812874",
    "PT50000201231234567890154",
    "SA0380000000608010167519",
    "SE4550000000058398257466",
    "TR330006100519786457841326",
]


def test_country_codes_attribute():
    assert isinstance(swifter.COUNTRY_CODES, list)
    assert "DE" in swifter.COUNTRY_CODES
    assert sorted(swifter.COUNTRY_CODES) == swifter.COUNTRY_CODES


def test_exception_hierarchy():
    assert issubclass(swifter.SwifterError, ValueError)
    for exception in [
        swifter.InvalidLength,
        swifter.InvalidStructure,
        swifter.InvalidCountryCode,
        swifter.InvalidChecksumDigits,
        swifter.InvalidBankCode,
        swifter.InvalidBranchCode,
        swifter.InvalidAccountCode,
    ]:
        assert issubclass(exception, swifter.SwifterError)


@pytest.mark.parametrize("value", VALID_IBANS)
def test_iban_valid(value):
    iban = swifter.IBAN(value)
    assert iban.compact == value
    assert iban.is_valid
    assert iban.validate() is True


def test_iban_normalization():
    iban = swifter.IBAN(" de89 3704\t0044 0532 0130 00 ")
    assert iban.compact == "DE89370400440532013000"


def test_iban_attributes():
    iban = swifter.IBAN("DE89 3704 0044 0532 0130 00")
    assert iban.compact == "DE89370400440532013000"
    assert iban.formatted == "DE89 3704 0044 0532 0130 00"
    assert iban.country_code == "DE"
    assert iban.checksum_digits == "89"
    assert iban.bban == "370400440532013000"
    assert iban.bank_code == "37040044"
    assert iban.branch_code == ""
    assert iban.account_code == "0532013000"
    assert iban.national_checksum_digits == ""
    assert iban.in_sepa_zone is True


def test_iban_attributes_branch_code():
    iban = swifter.IBAN("GB29NWBK60161331926819")
    assert iban.bank_code == "NWBK"
    assert iban.branch_code == "601613"
    assert iban.account_code == "31926819"


def test_iban_attributes_national_checksum_digits():
    iban = swifter.IBAN("IT60X0542811101000000123456")
    assert iban.national_checksum_digits == "X"
    assert iban.bank_code == "05428"
    assert iban.branch_code == "11101"
    assert iban.account_code == "000000123456"


def test_iban_not_in_sepa_zone():
    assert swifter.IBAN("SA0380000000608010167519").in_sepa_zone is False


def test_iban_invalid_checksum():
    with pytest.raises(swifter.InvalidChecksumDigits):
        swifter.IBAN("DE99370400440532013000")


def test_iban_invalid_length():
    with pytest.raises(swifter.InvalidLength):
        swifter.IBAN("DE8937040044053201300")


def test_iban_invalid_structure():
    with pytest.raises(swifter.InvalidStructure):
        swifter.IBAN("DE8937040044053201300E")


def test_iban_invalid_structure_checksum_digits():
    with pytest.raises(swifter.InvalidStructure):
        swifter.IBAN("DEAB370400440532013000")


def test_iban_invalid_structure_non_ascii():
    with pytest.raises(swifter.InvalidStructure):
        swifter.IBAN("DÉ89370400440532013000")


def test_iban_invalid_country_code():
    with pytest.raises(swifter.InvalidCountryCode):
        swifter.IBAN("XX82WEST12345698765432")


def test_iban_invalid_country_code_numeric():
    # Structural error rather than a country code one, to match schwifty.
    with pytest.raises(swifter.InvalidStructure):
        swifter.IBAN("1282WEST12345698765432")


def test_iban_invalid_empty():
    with pytest.raises(swifter.InvalidCountryCode):
        swifter.IBAN("")


def test_iban_allow_invalid():
    iban = swifter.IBAN("DE99370400440532013000", allow_invalid=True)
    assert not iban.is_valid
    assert iban.bank_code == "37040044"
    with pytest.raises(swifter.InvalidChecksumDigits):
        iban.validate()


def test_iban_allow_invalid_unknown_country():
    iban = swifter.IBAN("XX82WEST12345698765432", allow_invalid=True)
    assert iban.country_code == "XX"
    assert iban.bban == "WEST12345698765432"
    with pytest.raises(swifter.InvalidCountryCode):
        _ = iban.bank_code


def test_iban_allow_invalid_keyword_only():
    with pytest.raises(TypeError):
        swifter.IBAN("DE99370400440532013000", True)


def test_iban_str():
    assert str(swifter.IBAN("DE89370400440532013000")) == "DE89370400440532013000"


def test_iban_repr():
    iban = swifter.IBAN("DE89370400440532013000")
    assert repr(iban) == "<IBAN=DE89370400440532013000>"


def test_iban_len():
    assert len(swifter.IBAN("DE89370400440532013000")) == 22


def test_iban_equality():
    iban = swifter.IBAN("DE89370400440532013000")
    assert iban == swifter.IBAN("de89 3704 0044 0532 0130 00")
    assert iban == "DE89370400440532013000"
    assert iban != swifter.IBAN("GB29NWBK60161331926819")
    assert iban != "GB29NWBK60161331926819"
    assert iban != 3.14


def test_iban_hash():
    iban = swifter.IBAN("DE89370400440532013000")
    assert hash(iban) == hash("DE89370400440532013000")
    assert len({iban, swifter.IBAN("DE89370400440532013000")}) == 1


def test_iban_ordering():
    at = swifter.IBAN("AT611904300234573201")
    de = swifter.IBAN("DE89370400440532013000")
    assert at < de
    assert at <= de
    assert de > at
    assert de >= at
    assert at < "DE89370400440532013000"
    with pytest.raises(TypeError):
        operator.lt(at, 1)


def test_iban_from_bban():
    iban = swifter.IBAN.from_bban("DE", "370400440532013000")
    assert iban.compact == "DE89370400440532013000"


def test_iban_from_bban_invalid_characters():
    with pytest.raises(swifter.InvalidStructure):
        swifter.IBAN.from_bban("DE", "3704004405320130_0")


def test_iban_generate():
    iban = swifter.IBAN.generate("DE", bank_code="37040044", account_code="532013000")
    assert iban.compact == "DE89370400440532013000"
    assert iban.account_code == "0532013000"


def test_iban_generate_branch_code():
    iban = swifter.IBAN.generate(
        "GB", bank_code="NWBK", branch_code="601613", account_code="31926819"
    )
    assert iban.compact == "GB29NWBK60161331926819"


def test_iban_generate_invalid_country_code():
    with pytest.raises(swifter.InvalidCountryCode):
        swifter.IBAN.generate("XX", bank_code="1", account_code="1")


def test_iban_generate_invalid_bank_code():
    with pytest.raises(swifter.InvalidBankCode):
        swifter.IBAN.generate("DE", bank_code="370400440", account_code="532013000")


def test_iban_generate_invalid_branch_code():
    with pytest.raises(swifter.InvalidBranchCode):
        swifter.IBAN.generate(
            "GB", bank_code="NWBK", branch_code="6016130", account_code="1"
        )


def test_iban_generate_invalid_account_code():
    with pytest.raises(swifter.InvalidAccountCode):
        swifter.IBAN.generate("DE", bank_code="37040044", account_code="53201300000")


def test_iban_generate_invalid_structure():
    with pytest.raises(swifter.InvalidStructure):
        swifter.IBAN.generate("DE", bank_code="NWBK", account_code="532013000")


def test_bic_valid():
    bic = swifter.BIC("GENODEM1GLS")
    assert bic.compact == "GENODEM1GLS"
    assert bic.is_valid
    assert bic.validate() is True


def test_bic_normalization():
    assert swifter.BIC(" genode m1 gls ").compact == "GENODEM1GLS"


def test_bic_attributes():
    bic = swifter.BIC("GENODEM1GLS")
    assert bic.formatted == "GENO DE M1 GLS"
    assert bic.bank_code == "GENO"
    assert bic.country_code == "DE"
    assert bic.location_code == "M1"
    assert bic.branch_code == "GLS"


def test_bic_attributes_eight_characters():
    bic = swifter.BIC("GENODEFF")
    assert bic.formatted == "GENO DE FF"
    assert bic.branch_code == ""


def test_bic_type():
    assert swifter.BIC("GENODEFF").type == "default"
    assert swifter.BIC("GENODEM0GLS").type == "testing"
    assert swifter.BIC("GENODEM1GLS").type == "passive"
    assert swifter.BIC("GENODEM2GLS").type == "reverse billing"


def test_bic_invalid_length():
    with pytest.raises(swifter.InvalidLength):
        swifter.BIC("GENODEM1G")


def test_bic_invalid_structure():
    with pytest.raises(swifter.InvalidStructure):
        swifter.BIC("GENO12M1")


def test_bic_invalid_structure_non_ascii():
    with pytest.raises(swifter.InvalidStructure):
        swifter.BIC("GÉNODEM1")


def test_bic_invalid_country_code():
    with pytest.raises(swifter.InvalidCountryCode):
        swifter.BIC("GENOXXM1GLS")


def test_bic_allow_invalid():
    bic = swifter.BIC("GENOXXM1GLS", allow_invalid=True)
    assert not bic.is_valid
    assert bic.country_code == "XX"
    with pytest.raises(swifter.InvalidCountryCode):
        bic.validate()


def test_bic_allow_invalid_keyword_only():
    with pytest.raises(TypeError):
        swifter.BIC("GENODEM1GLS", True)


def test_bic_str():
    assert str(swifter.BIC("GENODEM1GLS")) == "GENODEM1GLS"


def test_bic_repr():
    assert repr(swifter.BIC("GENODEM1GLS")) == "<BIC=GENODEM1GLS>"


def test_bic_len():
    assert len(swifter.BIC("GENODEM1GLS")) == 11
    assert len(swifter.BIC("GENODEFF")) == 8


def test_bic_equality():
    bic = swifter.BIC("GENODEM1GLS")
    assert bic == swifter.BIC("genodem1gls")
    assert bic == "GENODEM1GLS"
    assert bic != swifter.BIC("GENODEFF")
    assert bic != 3.14


def test_bic_hash():
    bic = swifter.BIC("GENODEM1GLS")
    assert hash(bic) == hash("GENODEM1GLS")
    assert len({bic, swifter.BIC("GENODEM1GLS")}) == 1


def test_bic_ordering():
    ff = swifter.BIC("GENODEFF")
    gls = swifter.BIC("GENODEM1GLS")
    assert ff < gls
    assert gls > ff
    assert ff < "GENODEM1GLS"
    with pytest.raises(TypeError):
        operator.lt(ff, 1)
