"""
Tests comparing emojet's behaviour against the emoji package, exhaustively
over all emoji, for the shared core behaviour.
"""

from __future__ import annotations

import unicodedata

import emoji
import pytest

import emojet

LANGUAGES = ["en", "alias", *[lang for lang in emoji.LANGUAGES if lang != "en"]]


@pytest.fixture(autouse=True, scope="module")
def load_all_languages():
    emoji.config.load_language()


def test_languages_match():
    assert emojet.LANGUAGES == emoji.LANGUAGES


@pytest.mark.parametrize("language", LANGUAGES)
def test_demojize_every_emoji(language):
    for emj in emoji.EMOJI_DATA:
        string = f"a{emj}Z"
        expected = emoji.demojize(string, language=language)
        actual = emojet.demojize(string, language=language)
        assert actual == expected, emj


@pytest.mark.parametrize("language", LANGUAGES)
def test_demojize_alternate_delimiters_every_emoji(language):
    for emj in emoji.EMOJI_DATA:
        expected = emoji.demojize(emj, delimiters=("__", "__"), language=language)
        actual = emojet.demojize(emj, delimiters=("__", "__"), language=language)
        assert actual == expected, emj


@pytest.mark.parametrize("language", LANGUAGES)
def test_emojize_round_trip_every_emoji(language):
    for emj in emoji.EMOJI_DATA:
        named = emoji.demojize(emj, language=language)
        expected = emoji.emojize(named, language=language)
        actual = emojet.emojize(named, language=language)
        assert actual == expected, emj


@pytest.mark.parametrize("delimiters", [("{", "}"), ("__", "__"), ("<", ">")])
def test_emojize_alternate_delimiters_every_emoji(delimiters):
    for emj in emoji.EMOJI_DATA:
        named = emoji.demojize(emj, delimiters=delimiters)
        expected = emoji.emojize(named, delimiters=delimiters)
        actual = emojet.emojize(named, delimiters=delimiters)
        assert actual == expected, emj


def test_emojize_decomposed_names():
    for language in ["en", "fr", "de"]:
        for emj in list(emoji.EMOJI_DATA)[::10]:
            named = unicodedata.normalize("NFD", emoji.demojize(emj, language=language))
            expected = emoji.emojize(named, language=language)
            actual = emojet.emojize(named, language=language)
            assert actual == expected, emj


@pytest.mark.parametrize("variant", [None, "text_type", "emoji_type"])
def test_emojize_variants_every_name(variant):
    for data in emoji.EMOJI_DATA.values():
        string = f"Hello {data['en']}!"
        expected = emoji.emojize(string, variant=variant)
        actual = emojet.emojize(string, variant=variant)
        assert actual == expected, data["en"]


def test_emojize_every_alias():
    for data in emoji.EMOJI_DATA.values():
        for alias in data.get("alias", []):
            string = f"Hello {alias}!"
            expected = emoji.emojize(string, language="alias")
            actual = emojet.emojize(string, language="alias")
            assert actual == expected, alias


def test_emoji_list_every_emoji():
    for emj in emoji.EMOJI_DATA:
        string = f"a{emj}Z{emj}"
        expected = emoji.emoji_list(string)
        actual = emojet.emoji_list(string)
        assert [dict(sorted(e.items())) for e in actual] == [
            dict(sorted(e.items())) for e in expected
        ], emj


def test_replace_emoji_every_emoji():
    for emj in emoji.EMOJI_DATA:
        string = f"a{emj}Z"
        assert emojet.replace_emoji(string, "<E>") == emoji.replace_emoji(
            string, "<E>"
        ), emj


def test_is_emoji_every_emoji():
    for emj in emoji.EMOJI_DATA:
        assert emojet.is_emoji(emj)
        assert emojet.is_emoji(emj) == emoji.is_emoji(emj)


def test_version_every_emoji():
    for emj in emoji.EMOJI_DATA:
        assert emojet.version(emj) == float(emoji.version(emj)), emj


def test_get_emoji_by_name_every_name():
    for language in LANGUAGES:
        seen = set()
        for data in emoji.EMOJI_DATA.values():
            name = data["en"] if language == "alias" else data.get(language)
            if name is None or name in seen:
                continue
            seen.add(name)
            expected = emoji.unicode_codes.get_emoji_by_name(name, language)
            actual = emojet.get_emoji_by_name(name, language=language)
            assert actual == expected, (name, language)
