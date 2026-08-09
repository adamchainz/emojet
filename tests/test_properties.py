"""
Property-based tests, generating strings from emoji-aware fragments.

The first group checks invariants between emojet functions, the second
compares behaviour against the emoji package.

Run with more examples by selecting the "thorough" profile:

    pytest tests/test_properties.py --hypothesis-profile=thorough
"""

from __future__ import annotations

import emoji
import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st

import emojet

THUMBS_UP = "\U0001f44d"
ZWJ = "\u200d"
VS15 = "\ufe0e"
VS16 = "\ufe0f"
STATUSES = {"component", "fully_qualified", "minimally_qualified", "unqualified"}


@pytest.fixture(autouse=True, scope="module")
def load_all_languages():
    emoji.config.load_language()


ALL_EMOJI = sorted(emoji.EMOJI_DATA)

# Sequences cut mid-way, to exercise longest-match backtracking.
PARTIAL_EMOJI = sorted({e[: len(e) // 2] for e in ALL_EMOJI if len(e) > 1})

# Zero-width joiner, variation selectors, skin tones, regional indicators,
# keycap combiner, and keycap bases: the characters that combine into
# sequences, including the only ASCII characters that can start an emoji.
COMPONENTS = [
    ZWJ,
    VS15,
    VS16,
    "\U0001f3fb",
    "\U0001f3ff",
    "\U0001f1e6",
    "\U0001f1fa",
    "\u20e3",
    "#",
    "*",
    "9",
]

NAMES = [
    emojet.demojize(THUMBS_UP),
    emojet.demojize(THUMBS_UP, language="alias"),
    emojet.demojize(THUMBS_UP, language="de"),
    emojet.demojize(f"#{VS16}\u20e3"),  # keycap: name contains "#"
    emojet.demojize("\U0001f1eb\U0001f1f7"),  # flag: name is capitalized
    emojet.demojize(f"\U0001f468{ZWJ}\U0001f469{ZWJ}\U0001f467{ZWJ}\U0001f466"),
    emojet.demojize("\u2764" + f"{VS16}{ZWJ}\U0001f525"),  # ZWJ pair with selector
    ":not_a_real_name:",
    "::",
    ":",
]

fragments = (
    st.sampled_from(ALL_EMOJI)
    | st.sampled_from(PARTIAL_EMOJI)
    | st.sampled_from(COMPONENTS)
    | st.sampled_from(NAMES)
    | st.text(alphabet="ab :_-Z9\u0301\n", max_size=3)
    | st.text(max_size=3)
)
texts = st.lists(fragments, max_size=10).map("".join)

surrogates = st.text(alphabet=st.characters(categories=["Cs"]), min_size=1, max_size=2)


def _matches(module, string):
    return [
        (m["emoji"], m["match_start"], m["match_end"])
        for m in module.emoji_list(string)
    ]


def _same_matches(string):
    """
    Whether emojet and the emoji package find the same emoji in string.

    emojet matches the longest valid emoji at each position, while the emoji
    package can fail to match anything in truncated or invalid sequences, or
    split a joined sequence into its components, so the exact-equality
    differential tests only apply when the two agree.
    test_matching_never_misses covers the disagreements.
    """
    return _matches(emojet, string) == _matches(emoji, string)


def _covered(module, string):
    covered = set()
    for m in module.emoji_list(string):
        covered.update(range(m["match_start"], m["match_end"]))
    return covered


# Invariants between emojet functions


@given(texts, st.sampled_from(["en", "alias", "de", "ja"]))
@example("", "en")
@example(":thumbs_up:", "alias")  # an English name canonicalizes to :thumbsup:
@example(f":{THUMBS_UP}:thumbs", "en")
def test_demojize_emojize_round_trip_is_stable(string, language):
    # One demojize/emojize cycle can canonicalize names - for example an
    # English name emojizes in alias mode, then demojizes to its alias -
    # after which the cycle repeats exactly.
    def cycle(s):
        return emojet.demojize(emojet.emojize(s, language=language), language=language)

    stable = cycle(emojet.demojize(string, language=language))
    assert cycle(stable) == stable


@given(texts)
@example("")
@example(THUMBS_UP * 2 + "a" + THUMBS_UP)
def test_counts_agree_with_lists(string):
    listed = [m["emoji"] for m in emojet.emoji_list(string)]
    distinct = emojet.distinct_emoji_list(string)
    assert emojet.emoji_count(string) == len(listed)
    assert emojet.emoji_count(string, unique=True) == len(distinct)
    assert distinct == list(dict.fromkeys(listed))


@given(texts)
@example("")
@example("a\U0001f1eb\U0001f1f7\U0001f1eb")  # astral characters, partial flag
def test_emoji_list_spans_slice_out(string):
    prev_end = 0
    for match in emojet.emoji_list(string):
        assert prev_end <= match["match_start"] < match["match_end"] <= len(string)
        assert string[match["match_start"] : match["match_end"]] == match["emoji"]
        assert emojet.is_emoji(match["emoji"])
        assert emojet.emoji_status(match["emoji"]) in STATUSES
        assert isinstance(emojet.version(match["emoji"]), float)
        prev_end = match["match_end"]


@given(texts)
@example("")
@example(THUMBS_UP)
def test_replace_emoji_callable_sees_emoji_list(string):
    seen = []

    def replace(emj):
        seen.append(emj)
        return ""

    replaced = emojet.replace_emoji(string, replace=replace)
    assert seen == [m["emoji"] for m in emojet.emoji_list(string)]
    assert replaced == emojet.replace_emoji(string, replace="")


@given(texts)
@example("")
@example(THUMBS_UP)
@example("a" + THUMBS_UP)
@example(THUMBS_UP + ZWJ)  # trailing joiner still counts as purely emoji
@example(ZWJ + THUMBS_UP)  # leading joiner does not
def test_purely_and_is_emoji_agree_with_emoji_list(string):
    matches = emojet.emoji_list(string)
    joined = "".join(m["emoji"] for m in matches)

    # A string is purely emoji when, ignoring variation selectors, it is
    # emoji matches with only zero-width joiners after them.
    gaps = []
    pos = 0
    for m in matches:
        gaps.append(string[pos : m["match_start"]])
        pos = m["match_end"]
    gaps.append(string[pos:])
    gaps = [g.replace(VS15, "").replace(VS16, "") for g in gaps]
    purely = gaps[0] == "" and all(set(g) <= {ZWJ} for g in gaps[1:])

    assert emojet.purely_emoji(string) == purely
    assert emojet.is_emoji(string) == (len(matches) == 1 and joined == string)


@given(texts, surrogates, texts)
def test_lone_surrogates_raise(prefix, surrogate, suffix):
    string = prefix + surrogate + suffix
    with pytest.raises(UnicodeEncodeError):
        emojet.demojize(string)
    with pytest.raises(UnicodeEncodeError):
        emojet.emoji_list(string)
    with pytest.raises(UnicodeEncodeError):
        emojet.emojize(string)


# Differential properties against the emoji package


@given(texts)
@example("\U0001f3f4\U000e0067")  # black flag + stray tag character
@example("\u2764" + VS16 + ZWJ + "X")  # red heart + joiner + text
@example("\U0001f3c3\U0001f3fc" + ZWJ + "\u2642" + VS16 + ZWJ)  # trailing joiner
def test_matching_never_misses(string):
    # emojet matches the longest valid emoji at each position. In truncated
    # or invalid sequences the emoji package can fail to match anything, or
    # split a joined sequence into its components, but every character it
    # matches, emojet must match too.
    assert _covered(emoji, string) <= _covered(emojet, string)


@given(texts, st.sampled_from(["en", "alias", "de", "ja", "ar"]))
@example(VS16 + THUMBS_UP + ZWJ, "en")
def test_demojize_matches(string, language):
    assume(_same_matches(string))
    expected = emoji.demojize(string, language=language)
    assert emojet.demojize(string, language=language) == expected


@given(texts, st.sampled_from([(":", ":"), ("__", "__"), ("{", "}"), ("<", ">")]))
@example(":9:thumbs_up:", (":", ":"))
@example("__x__thumbs_up__", ("__", "__"))
@example(":thumbs::thumbs_up:", (":", ":"))
def test_emojize_matches(string, delimiters):
    expected = emoji.emojize(string, delimiters=delimiters)
    actual = emojet.emojize(string, delimiters=delimiters)
    if actual != expected:
        # emojet converts names that the emoji package skips: when a
        # delimited run of name characters is not a known name, the emoji
        # package consumes it whole, including a closing delimiter that
        # could open a known name, like the second ":" in ":9:thumbs_up:".
        # Beyond those extra conversions the outputs must agree, so
        # converting the skipped names must reach emojet's output.
        assert emojet.emojize(expected, delimiters=delimiters) == actual


@given(texts)
@example(THUMBS_UP * 2)
def test_counts_match(string):
    assume(_same_matches(string))
    assert emojet.emoji_count(string) == emoji.emoji_count(string)
    expected_unique = emoji.emoji_count(string, unique=True)
    assert emojet.emoji_count(string, unique=True) == expected_unique
    expected_distinct = sorted(emoji.distinct_emoji_list(string))
    assert sorted(emojet.distinct_emoji_list(string)) == expected_distinct


@given(texts)
@example("")
@example(THUMBS_UP)
def test_purely_and_is_emoji_match(string):
    assume(_same_matches(string))
    assert emojet.purely_emoji(string) == emoji.purely_emoji(string)
    assert emojet.is_emoji(string) == emoji.is_emoji(string)


@given(texts)
@example("")
@example(THUMBS_UP)
def test_version_matches(string):
    assume(_same_matches(string))
    # emojet.version() looks up emoji and English names only, so it may
    # raise where the emoji package would find a name in another language.
    try:
        actual = emojet.version(string)
    except ValueError:
        pass
    else:
        assert actual == float(emoji.version(string))
