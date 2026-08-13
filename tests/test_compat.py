"""
Tests comparing pslr's behaviour against the publicsuffixlist
package, over the Public Suffix List's own test domains and variations of
them, for the shared core behaviour.
"""

from __future__ import annotations

import publicsuffixlist
import pytest

import pslr

from .test_psl_data import parse_cases

PSL = publicsuffixlist.PublicSuffixList()
PSL_ICANN = publicsuffixlist.PublicSuffixList(only_icann=True)

BASE_DOMAINS = [domain for domain, _ in parse_cases() if domain is not None]
DOMAINS = list(
    dict.fromkeys(
        [
            *BASE_DOMAINS,
            *[f"www.{domain}" for domain in BASE_DOMAINS],
            *[f"{domain}." for domain in BASE_DOMAINS],
            *[domain.upper() for domain in BASE_DOMAINS],
            "",
            ".",
            "..",
            "example..com",
            "adamchainz.github.io",
            "foo.blogspot.com",
        ]
    )
)


@pytest.mark.parametrize("domain", DOMAINS)
def test_publicsuffix(domain):
    assert pslr.publicsuffix(domain) == PSL.publicsuffix(domain)


@pytest.mark.parametrize("domain", DOMAINS)
def test_publicsuffix_accept_unknown_false(domain):
    expected = PSL.publicsuffix(domain, accept_unknown=False)
    assert pslr.publicsuffix(domain, accept_unknown=False) == expected


@pytest.mark.parametrize("domain", DOMAINS)
def test_publicsuffix_keep_case(domain):
    expected = PSL.publicsuffix(domain, keep_case=True)
    assert pslr.publicsuffix(domain, keep_case=True) == expected


@pytest.mark.parametrize("domain", DOMAINS)
def test_publicsuffix_icann_only(domain):
    expected = PSL_ICANN.publicsuffix(domain)
    assert pslr.publicsuffix(domain, icann_only=True) == expected


@pytest.mark.parametrize("domain", DOMAINS)
def test_privatesuffix(domain):
    assert pslr.privatesuffix(domain) == PSL.privatesuffix(domain)


@pytest.mark.parametrize("domain", DOMAINS)
def test_privatesuffix_keep_case(domain):
    expected = PSL.privatesuffix(domain, keep_case=True)
    assert pslr.privatesuffix(domain, keep_case=True) == expected


@pytest.mark.parametrize("domain", DOMAINS)
def test_privatesuffix_icann_only(domain):
    expected = PSL_ICANN.privatesuffix(domain)
    assert pslr.privatesuffix(domain, icann_only=True) == expected


@pytest.mark.parametrize("domain", DOMAINS)
def test_is_public(domain):
    assert pslr.is_public(domain) == PSL.is_public(domain)


@pytest.mark.parametrize("domain", DOMAINS)
def test_is_private(domain):
    assert pslr.is_private(domain) == PSL.is_private(domain)


@pytest.mark.parametrize("domain", DOMAINS)
def test_is_public_icann_only(domain):
    assert pslr.is_public(domain, icann_only=True) == PSL_ICANN.is_public(domain)


@pytest.mark.parametrize("domain", DOMAINS)
def test_is_private_icann_only(domain):
    assert pslr.is_private(domain, icann_only=True) == PSL_ICANN.is_private(domain)


@pytest.mark.parametrize("domain", DOMAINS)
def test_privateparts(domain):
    assert pslr.privateparts(domain) == PSL.privateparts(domain)


@pytest.mark.parametrize("domain", DOMAINS)
@pytest.mark.parametrize("depth", [0, 1, 2])
def test_subdomain(domain, depth):
    try:
        expected = PSL.subdomain(domain, depth)
    except TypeError:
        # publicsuffixlist raises for invalid domains, pslr
        # returns None
        expected = None
    assert pslr.subdomain(domain, depth) == expected
