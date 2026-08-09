from __future__ import annotations

import subprocess
import sys

import pytest

import emojet


def test_version_attribute():
    assert emojet.UNICODE_VERSION == "17.0.0"


def test_languages_attribute():
    assert emojet.LANGUAGES[0] == "en"
    assert "fr" in emojet.LANGUAGES


def test_demojize():
    assert emojet.demojize("Python is fun 👍") == "Python is fun :thumbs_up:"


def test_demojize_language():
    assert emojet.demojize("👍", language="de") == ":daumen_hoch:"
    assert emojet.demojize("👍", language="alias") == ":thumbsup:"


def test_demojize_delimiters():
    result = emojet.demojize("Unicode is tricky 😯", delimiters=("__", "__"))
    assert result == "Unicode is tricky __hushed_face__"


def test_demojize_strays_dropped():
    # Stray variation selectors are dropped, ZWJ between emoji is kept
    assert emojet.demojize("a️b") == "ab"
    assert (
        emojet.demojize("😁‍😁")
        == ":beaming_face_with_smiling_eyes:‍:beaming_face_with_smiling_eyes:"
    )


def test_demojize_unsupported_language():
    with pytest.raises(ValueError):
        emojet.demojize("👍", language="xx")


def test_demojize_keyword_only():
    with pytest.raises(TypeError):
        emojet.demojize("👍", "de")


def test_emojize():
    assert emojet.emojize("Python is fun :thumbs_up:") == "Python is fun 👍"


def test_emojize_language():
    assert emojet.emojize(":daumen_hoch:", language="de") == "👍"
    assert emojet.emojize(":thumbsup:", language="alias") == "👍"
    # Aliases fall back to English names
    assert emojet.emojize(":thumbs_up:", language="alias") == "👍"


def test_emojize_delimiters():
    assert emojet.emojize("{thumbs_up}", delimiters=("{", "}")) == "👍"
    assert emojet.emojize("__thumbs_up__", delimiters=("__", "__")) == "👍"
    assert emojet.emojize("<thumbs_up>", delimiters=("<", ">")) == "👍"


def test_emojize_empty_delimiter():
    with pytest.raises(ValueError):
        emojet.emojize(":thumbs_up:", delimiters=("", ""))


def test_emojize_unknown_name_kept():
    assert emojet.emojize(":not_a_real_emoji_name:") == ":not_a_real_emoji_name:"
    assert emojet.emojize("::") == "::"
    assert emojet.emojize(":") == ":"


def test_emojize_round_trips_zwj():
    text = "😁‍😁"
    assert emojet.emojize(emojet.demojize(text)) == text


def test_emojize_variants():
    assert emojet.emojize(":red_heart:", variant="text_type") == "❤︎"
    assert emojet.emojize(":red_heart:", variant="emoji_type") == "❤️"
    # An emoji without variation selector support is unaffected
    assert emojet.emojize(":1st_place_medal:", variant="text_type") == "🥇"
    # An emoji stored without a trailing selector gains one
    assert emojet.emojize(":Aquarius:", variant="emoji_type") == "♒️"


def test_emojize_invalid_variant():
    with pytest.raises(ValueError):
        emojet.emojize(":red_heart:", variant="wrong_type")


def test_emojize_unsupported_language():
    with pytest.raises(ValueError):
        emojet.emojize(":thumbs_up:", language="xx")


def test_replace_emoji():
    assert emojet.replace_emoji("Hi 😁!") == "Hi !"
    assert emojet.replace_emoji("Hi 😁!", "?") == "Hi ?!"


def test_replace_emoji_callable():
    result = emojet.replace_emoji("a😁b👍c", lambda e: f"<{e}>")
    assert result == "a<😁>b<👍>c"


def test_replace_emoji_callable_error():
    def boom(emoji):
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        emojet.replace_emoji("😁", boom)


def test_replace_emoji_callable_non_str():
    with pytest.raises(TypeError):
        emojet.replace_emoji("😁", lambda e: 123)


def test_emoji_list():
    assert emojet.emoji_list("Hi, I am fine. 😁") == [
        {"emoji": "😁", "match_start": 15, "match_end": 16}
    ]


def test_emoji_list_positions_are_code_points():
    (match,) = emojet.emoji_list("🇫🇷!")
    assert match == {"emoji": "🇫🇷", "match_start": 0, "match_end": 2}


def test_distinct_emoji_list():
    # First-appearance order
    assert emojet.distinct_emoji_list("🙂😁🙂😁") == ["🙂", "😁"]


def test_emoji_count():
    assert emojet.emoji_count("😁😁🙂") == 3
    assert emojet.emoji_count("😁😁🙂", unique=True) == 2


def test_is_emoji():
    assert emojet.is_emoji("👍")
    assert emojet.is_emoji("👨‍👩‍👧‍👦")
    assert not emojet.is_emoji("👍👍")
    assert not emojet.is_emoji("x")
    assert not emojet.is_emoji("")


def test_purely_emoji():
    assert emojet.purely_emoji("😁👍")
    assert emojet.purely_emoji("😁‍😁")
    assert emojet.purely_emoji("")
    assert not emojet.purely_emoji("😁x")
    assert not emojet.purely_emoji("‍😁")


def test_version():
    assert emojet.version("😁") == 0.6
    assert emojet.version(":butterfly:") == 3.0
    assert emojet.version(":thumbsup:") == 0.6  # alias
    assert emojet.version("text 🦋 text") == 3.0


def test_version_no_emoji():
    with pytest.raises(ValueError):
        emojet.version("no emoji at all")
    with pytest.raises(ValueError):
        emojet.version(":not_a_name:")


def test_get_emoji_by_name():
    assert emojet.get_emoji_by_name(":thumbs_up:") == "👍"
    assert emojet.get_emoji_by_name(":thumbsup:", language="alias") == "👍"
    assert emojet.get_emoji_by_name(":pouce_vers_le_haut:", language="fr") == "👍"
    assert emojet.get_emoji_by_name(":nope:") is None
    assert emojet.get_emoji_by_name(":nope:", language="fr") is None
    assert emojet.get_emoji_by_name("no_colons") is None
    with pytest.raises(ValueError):
        emojet.get_emoji_by_name(":thumbs_up:", language="xx")


def test_emoji_status():
    assert emojet.emoji_status("👍") == "fully_qualified"
    assert emojet.emoji_status("🏻") == "component"
    assert emojet.emoji_status("🅰") == "unqualified"
    with pytest.raises(ValueError):
        emojet.emoji_status("x")


def test_surrogates_raise():
    # Strings must be well-formed Unicode: lone surrogates cannot be passed
    # to the Rust extension
    with pytest.raises(UnicodeEncodeError):
        emojet.is_emoji("\ud800")


def test_import_runs_standalone():
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import emojet; assert emojet.demojize('😁') == "
            "':beaming_face_with_smiling_eyes:'",
        ],
        check=True,
        timeout=120,
    )
