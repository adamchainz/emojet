from __future__ import annotations

import re

import pytest

import pslr


def test_list_checksum():
    assert re.fullmatch(r"[0-9a-f]{64}", pslr.LIST_CHECKSUM)


def test_publicsuffix():
    assert pslr.publicsuffix("www.example.com") == "com"
    assert pslr.publicsuffix("example.com") == "com"
    assert pslr.publicsuffix("com") == "com"


def test_publicsuffix_multi_label():
    assert pslr.publicsuffix("www.example.co.uk") == "co.uk"


def test_publicsuffix_private_section():
    assert pslr.publicsuffix("adamchainz.github.io") == "github.io"


def test_publicsuffix_icann_only():
    assert pslr.publicsuffix("adamchainz.github.io", icann_only=True) == "io"
    assert pslr.publicsuffix("www.tfl.gov.uk", icann_only=True) == "gov.uk"


def test_publicsuffix_unknown():
    assert pslr.publicsuffix("example.unknowntld") == "unknowntld"
    assert pslr.publicsuffix("unknowntld") == "unknowntld"


def test_publicsuffix_accept_unknown_false():
    result = pslr.publicsuffix("example.unknowntld", accept_unknown=False)
    assert result is None
    assert pslr.publicsuffix("example.com", accept_unknown=False) == "com"


def test_publicsuffix_wildcard():
    assert pslr.publicsuffix("b.test.ck") == "test.ck"
    assert pslr.publicsuffix("ck", accept_unknown=False) == "ck"


def test_publicsuffix_wildcard_root():
    # kobe.jp is not listed itself, but *.kobe.jp makes it public
    assert pslr.publicsuffix("kobe.jp") == "kobe.jp"


def test_publicsuffix_exception():
    # !www.ck overrides *.ck
    assert pslr.publicsuffix("www.ck") == "ck"


def test_publicsuffix_case():
    assert pslr.publicsuffix("WwW.Example.COM") == "com"


def test_publicsuffix_keep_case():
    assert pslr.publicsuffix("Example.COM", keep_case=True) == "COM"


def test_publicsuffix_trailing_dot():
    assert pslr.publicsuffix("example.com.") == "com"


def test_publicsuffix_idn():
    assert pslr.publicsuffix("食狮.中国") == "中国"
    assert pslr.publicsuffix("shishi.xn--fiqs8s") == "xn--fiqs8s"


@pytest.mark.parametrize("domain", ["", ".", "..", ".com", "example..com"])
def test_publicsuffix_invalid(domain):
    assert pslr.publicsuffix(domain) is None


def test_publicsuffix_keyword_only():
    with pytest.raises(TypeError):
        pslr.publicsuffix("example.com", False)


def test_publicsuffix_non_string():
    with pytest.raises(TypeError):
        pslr.publicsuffix(None)


def test_publicsuffix_surrogates():
    with pytest.raises(UnicodeEncodeError):
        pslr.publicsuffix("\ud83d.com")


def test_privatesuffix():
    assert pslr.privatesuffix("www.example.com") == "example.com"
    assert pslr.privatesuffix("a.www.example.co.uk") == "example.co.uk"


def test_privatesuffix_entirely_public():
    assert pslr.privatesuffix("com") is None
    assert pslr.privatesuffix("test.ck") is None
    assert pslr.privatesuffix("kobe.jp") is None


def test_privatesuffix_unknown():
    assert pslr.privatesuffix("example.unknowntld") == "example.unknowntld"
    result = pslr.privatesuffix("example.unknowntld", accept_unknown=False)
    assert result is None


def test_privatesuffix_icann_only():
    result = pslr.privatesuffix("adamchainz.github.io", icann_only=True)
    assert result == "github.io"


def test_privatesuffix_keep_case():
    result = pslr.privatesuffix("WwW.Example.COM", keep_case=True)
    assert result == "Example.COM"


def test_privatesuffix_idn():
    assert pslr.privatesuffix("www.食狮.中国") == "食狮.中国"


def test_privatesuffix_invalid():
    assert pslr.privatesuffix("example..com") is None


def test_is_public():
    assert pslr.is_public("com")
    assert pslr.is_public("co.uk")
    assert pslr.is_public("kobe.jp")
    assert not pslr.is_public("example.com")
    assert not pslr.is_public("www.ck")


def test_is_public_accept_unknown():
    assert pslr.is_public("unknowntld")
    assert not pslr.is_public("unknowntld", accept_unknown=False)


def test_is_public_icann_only():
    assert pslr.is_public("github.io")
    assert not pslr.is_public("github.io", icann_only=True)


def test_is_public_invalid():
    assert not pslr.is_public("")
    assert not pslr.is_public("example..com")


def test_is_private():
    assert pslr.is_private("example.com")
    assert pslr.is_private("www.example.com")
    assert pslr.is_private("www.ck")
    assert not pslr.is_private("com")
    assert not pslr.is_private("kobe.jp")


def test_is_private_accept_unknown():
    assert pslr.is_private("example.unknowntld")
    assert not pslr.is_private("example.unknowntld", accept_unknown=False)


def test_is_private_icann_only():
    assert not pslr.is_private("github.io")
    assert pslr.is_private("github.io", icann_only=True)


def test_is_private_invalid():
    assert not pslr.is_private("")
    assert not pslr.is_private("example..com")


def test_privateparts():
    result = pslr.privateparts("aaa.www.example.com")
    assert result == ("aaa", "www", "example.com")
    assert isinstance(result, tuple)


def test_privateparts_no_subdomains():
    assert pslr.privateparts("example.com") == ("example.com",)


def test_privateparts_entirely_public():
    assert pslr.privateparts("com") is None


def test_privateparts_accept_unknown():
    assert pslr.privateparts("a.b.unknowntld") == ("a", "b.unknowntld")
    result = pslr.privateparts("a.b.unknowntld", accept_unknown=False)
    assert result is None


def test_privateparts_icann_only():
    result = pslr.privateparts("www.adamchainz.github.io", icann_only=True)
    assert result == ("www", "adamchainz", "github.io")


def test_privateparts_keep_case():
    result = pslr.privateparts("aAa.WWW.Example.COM", keep_case=True)
    assert result == ("aAa", "WWW", "Example.COM")


def test_privateparts_invalid():
    assert pslr.privateparts("example..com") is None


def test_subdomain():
    assert pslr.subdomain("aaa.www.example.com", 0) == "example.com"
    assert pslr.subdomain("aaa.www.example.com", 1) == "www.example.com"
    assert pslr.subdomain("aaa.www.example.com", 2) == "aaa.www.example.com"


def test_subdomain_too_deep():
    assert pslr.subdomain("aaa.www.example.com", 3) is None


def test_subdomain_entirely_public():
    assert pslr.subdomain("com", 0) is None


def test_subdomain_accept_unknown():
    assert pslr.subdomain("a.b.unknowntld", 0) == "b.unknowntld"
    assert pslr.subdomain("a.b.unknowntld", 0, accept_unknown=False) is None


def test_subdomain_icann_only():
    result = pslr.subdomain("www.adamchainz.github.io", 0, icann_only=True)
    assert result == "github.io"


def test_subdomain_keep_case():
    result = pslr.subdomain("aAa.WWW.Example.COM", 1, keep_case=True)
    assert result == "WWW.Example.COM"


def test_subdomain_negative_depth():
    with pytest.raises(OverflowError):
        pslr.subdomain("www.example.com", -1)


def test_subdomain_huge_depth():
    assert pslr.subdomain("www.example.com", 2**64 - 1) is None
    assert pslr.subdomain("www.example.com", 2**64 - 2) is None


def test_subdomain_invalid():
    assert pslr.subdomain("example..com", 0) is None
