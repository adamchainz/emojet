"""
Property-based tests, generating domains from labels that exercise exact,
wildcard, exception, private-section, unknown, and IDN rules.

The first group checks invariants between pslr functions, the
second compares behaviour against the publicsuffixlist package.

Run with more examples by selecting the "thorough" profile:

    pytest tests/test_properties.py --hypothesis-profile=thorough
"""

from __future__ import annotations

import publicsuffixlist
from hypothesis import example, given
from hypothesis import strategies as st

import pslr

PSL = publicsuffixlist.PublicSuffixList()
PSL_ICANN = publicsuffixlist.PublicSuffixList(only_icann=True)

# Labels chosen to hit long-stable rules of every kind: exact (com, uk,
# co.uk, jp hierarchy), wildcard (*.ck, *.kobe.jp), exception (!www.ck,
# !city.kobe.jp), the private section (github.io, blogspot.com), unicode
# and punycode IDN rules (中国), unknown TLDs, and casing.
LABELS = [
    "com",
    "uk",
    "co",
    "jp",
    "kobe",
    "kyoto",
    "ide",
    "ck",
    "test",
    "www",
    "city",
    "example",
    "github",
    "io",
    "blogspot",
    "unknowntld",
    "中国",
    "食狮",
    "xn--fiqs8s",
    "xn--85x722f",
    "COM",
    "Example",
    "WWW",
    "0",
    "a",
    "xn--",
    "_tcp",
]

domains = st.lists(st.sampled_from(LABELS), min_size=1, max_size=5).map(".".join)
domains_maybe_invalid = st.one_of(
    domains,
    domains.map(lambda domain: domain + "."),
    domains.map(lambda domain: "." + domain),
    st.sampled_from(["", ".", "..", "...."]),
)


# Invariants


@given(domains)
@example("kobe.jp")
@example("www.ck")
def test_privatesuffix_extends_publicsuffix(domain):
    private = pslr.privatesuffix(domain)
    if private is not None:
        public = pslr.publicsuffix(domain)
        assert public is not None
        assert private.endswith("." + public)
        assert private.count(".") == public.count(".") + 1


@given(domains)
def test_publicsuffix_is_public(domain):
    public = pslr.publicsuffix(domain)
    # With accept_unknown, every valid domain has a public suffix
    assert public is not None
    assert pslr.is_public(public)


@given(domains)
def test_privatesuffix_is_private(domain):
    private = pslr.privatesuffix(domain)
    if private is not None:
        assert pslr.is_private(private)
        assert not pslr.is_public(private)


@given(domains)
def test_is_public_is_private_exclusive(domain):
    is_public = pslr.is_public(domain)
    is_private = pslr.is_private(domain)
    assert not (is_public and is_private)
    # With accept_unknown, every valid domain is one or the other
    assert is_public or is_private


@given(domains)
def test_subdomain_zero_is_privatesuffix(domain):
    expected = pslr.privatesuffix(domain)
    assert pslr.subdomain(domain, 0) == expected


@given(domains)
def test_privateparts_rejoin(domain):
    parts = pslr.privateparts(domain)
    if parts is not None:
        assert ".".join(parts) == domain.lower()
        assert parts[-1] == pslr.privatesuffix(domain)


@given(domains)
def test_case_insensitive(domain):
    expected = pslr.publicsuffix(domain)
    assert pslr.publicsuffix(domain.upper()) == expected


@given(domains)
def test_trailing_dot_ignored(domain):
    expected = pslr.publicsuffix(domain)
    assert pslr.publicsuffix(domain + ".") == expected


@given(domains)
def test_keep_case_lowercases_to_default(domain):
    kept = pslr.publicsuffix(domain, keep_case=True)
    # With accept_unknown, every valid domain has a public suffix
    assert kept is not None
    assert kept.lower() == pslr.publicsuffix(domain)


# Comparisons against publicsuffixlist


@given(domains_maybe_invalid)
@example("kobe.jp")
@example("0.bg")
def test_publicsuffix_matches(domain):
    assert pslr.publicsuffix(domain) == PSL.publicsuffix(domain)


@given(domains_maybe_invalid)
def test_publicsuffix_accept_unknown_matches(domain):
    expected = PSL.publicsuffix(domain, accept_unknown=False)
    assert pslr.publicsuffix(domain, accept_unknown=False) == expected


@given(domains_maybe_invalid)
@example("adamchainz.github.io")
def test_publicsuffix_icann_only_matches(domain):
    expected = PSL_ICANN.publicsuffix(domain)
    assert pslr.publicsuffix(domain, icann_only=True) == expected


@given(domains_maybe_invalid)
def test_privatesuffix_icann_only_matches(domain):
    expected = PSL_ICANN.privatesuffix(domain)
    assert pslr.privatesuffix(domain, icann_only=True) == expected


@given(domains_maybe_invalid)
def test_privatesuffix_matches(domain):
    assert pslr.privatesuffix(domain) == PSL.privatesuffix(domain)


@given(domains_maybe_invalid)
def test_privatesuffix_keep_case_matches(domain):
    expected = PSL.privatesuffix(domain, keep_case=True)
    assert pslr.privatesuffix(domain, keep_case=True) == expected


@given(domains_maybe_invalid)
def test_is_public_matches(domain):
    assert pslr.is_public(domain) == PSL.is_public(domain)


@given(domains_maybe_invalid)
def test_is_private_matches(domain):
    assert pslr.is_private(domain) == PSL.is_private(domain)


@given(domains_maybe_invalid)
def test_privateparts_matches(domain):
    assert pslr.privateparts(domain) == PSL.privateparts(domain)


@given(domains_maybe_invalid, st.integers(0, 3))
def test_subdomain_matches(domain, depth):
    try:
        expected = PSL.subdomain(domain, depth)
    except TypeError:
        # publicsuffixlist raises for invalid domains, pslr
        # returns None
        expected = None
    assert pslr.subdomain(domain, depth) == expected
