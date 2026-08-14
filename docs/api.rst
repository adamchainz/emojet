=============
API reference
=============

.. module:: emojet

Everything lives in the ``emojet`` module, and all optional parameters are keyword-only.

Functions that take a ``language`` parameter accept any language code from :data:`LANGUAGES`, or ``"alias"`` for the English aliases used on GitHub and Slack, like ``:thumbsup:``.
Unsupported language codes raise :exc:`ValueError`.

Emoji names include their delimiters, ``":"`` by default, so a full name looks like ``:thumbs_up:``.
The names and data match those of the |emoji package|__ - see :doc:`history` for how the two libraries relate.

.. |emoji package| replace:: ``emoji`` package
__ https://github.com/carpedm20/emoji/

Strings must be well-formed Unicode: lone surrogates raise :exc:`UnicodeEncodeError`.

Conversion
----------

.. function:: emojize(string: str, *, language: str = "en", delimiters: tuple[str, str] = (":", ":"), variant: Literal["text_type", "emoji_type"] | None = None) -> str

   Return *string* with delimited emoji names replaced by the emoji themselves.
   Unknown names are left unchanged.

   .. code-block:: pycon

       >>> emojet.emojize("Python is fun :thumbs_up:")
       'Python is fun 👍'
       >>> emojet.emojize("Python is fun :thumbsup:", language="alias")
       'Python is fun 👍'
       >>> emojet.emojize("Python ist toll :daumen_hoch:", language="de")
       'Python ist toll 👍'
       >>> emojet.emojize("An :unknown_name: stays")
       'An :unknown_name: stays'

   ``delimiters`` is a tuple of two non-empty strings that surround each name:

   .. code-block:: pycon

       >>> emojet.emojize("Python is fun __thumbs_up__", delimiters=("__", "__"))
       'Python is fun 👍'

   ``variant`` may be ``"text_type"`` or ``"emoji_type"`` to force a text or emoji presentation, for emoji that support both.
   It appends the relevant Unicode variation selector, U+FE0E or U+FE0F:

   .. code-block:: pycon

       >>> emojet.emojize(":red_heart:", variant="text_type")
       '❤︎'
       >>> emojet.emojize(":red_heart:", variant="emoji_type")
       '❤️'

.. function:: demojize(string: str, *, language: str = "en", delimiters: tuple[str, str] = (":", ":")) -> str

   Return *string* with emoji replaced by their delimited names.
   The inverse of :func:`emojize`: emojizing the result returns the original string.

   .. code-block:: pycon

       >>> emojet.demojize("Python is fun 👍")
       'Python is fun :thumbs_up:'
       >>> emojet.demojize("Python is fun 👍", language="de")
       'Python is fun :daumen_hoch:'
       >>> emojet.demojize("Python is fun 👍", delimiters=("__", "__"))
       'Python is fun __thumbs_up__'

   Matching is greedy: at each position, the longest known emoji sequence wins.
   Multi-code-point sequences like family emoji or flags convert to a single name:

   .. code-block:: pycon

       >>> emojet.demojize("👨‍👩‍👧‍👦")
       ':family_man_woman_girl_boy:'
       >>> emojet.demojize("🇫🇷")
       ':France:'

.. function:: replace_emoji(string: str, replace: str | Callable[[str], str] | None = None) -> str

   Return *string* with emoji replaced.
   ``replace`` may be a string, or a callable that receives each emoji and returns its replacement.

   .. code-block:: pycon

       >>> emojet.replace_emoji("Python is fun 👍")
       'Python is fun '
       >>> emojet.replace_emoji("Python is fun 👍", replace="?")
       'Python is fun ?'
       >>> emojet.replace_emoji("Python is fun 👍", replace=lambda e: f"<{e}>")
       'Python is fun <👍>'

Searching
---------

.. function:: emoji_list(string: str) -> list[dict[str, Any]]

   Return a list of dicts describing each emoji in *string*, with its start and end indexes.

   .. code-block:: pycon

       >>> emojet.emoji_list("Unicode is tricky 😯, very tricky 🤯")
       [{'emoji': '😯', 'match_start': 18, 'match_end': 19}, {'emoji': '🤯', 'match_start': 33, 'match_end': 34}]

.. function:: distinct_emoji_list(string: str) -> list[str]

   Return the distinct emoji in *string*, in order of first appearance.

   .. code-block:: pycon

       >>> emojet.distinct_emoji_list("Some emoji repeat 😁😁👍😁")
       ['😁', '👍']

.. function:: emoji_count(string: str, *, unique: bool = False) -> int

   Return the number of emoji in *string*.
   Pass ``unique=True`` to count each distinct emoji once.

   .. code-block:: pycon

       >>> emojet.emoji_count("Some emoji repeat 😁😁👍😁")
       4
       >>> emojet.emoji_count("Some emoji repeat 😁😁👍😁", unique=True)
       2

.. function:: is_emoji(string: str) -> bool

   Return whether *string* is exactly one emoji.

   .. code-block:: pycon

       >>> emojet.is_emoji("👍")
       True
       >>> emojet.is_emoji("👍👍")
       False

.. function:: purely_emoji(string: str) -> bool

   Return whether *string* consists only of emoji.

   .. code-block:: pycon

       >>> emojet.purely_emoji("👍👍")
       True
       >>> emojet.purely_emoji("Python 👍")
       False

Lookup
------

.. function:: version(string: str) -> float

   Return the Unicode emoji version of the first emoji or delimited English name in *string*, as a float.
   Versions match those in Unicode's |emoji-test.txt|__, where 0.6 and 0.7 mark emoji that predate the versioned releases.
   Raises :exc:`ValueError` if *string* contains no emoji.

   .. |emoji-test.txt| replace:: ``emoji-test.txt``
   __ https://unicode.org/Public/emoji/latest/emoji-test.txt

   .. code-block:: pycon

       >>> emojet.version("👍")
       0.6
       >>> emojet.version("Python 🤯")
       5.0
       >>> emojet.version(":thumbs_up:")
       0.6

.. function:: get_emoji_by_name(name: str, *, language: str = "en") -> str | None

   Return the emoji for an exact delimited name, or :obj:`None` if the name is unknown.

   .. code-block:: pycon

       >>> emojet.get_emoji_by_name(":thumbs_up:")
       '👍'
       >>> emojet.get_emoji_by_name(":daumen_hoch:", language="de")
       '👍'
       >>> emojet.get_emoji_by_name(":not_a_real_name:") is None
       True

.. function:: emoji_status(string: str) -> str

   Return the Unicode qualification status of an emoji: ``"component"``, ``"fully_qualified"``, ``"minimally_qualified"``, or ``"unqualified"``.
   Raises :exc:`ValueError` if *string* is not exactly one emoji.

   .. code-block:: pycon

       >>> emojet.emoji_status("👍")
       'fully_qualified'
       >>> emojet.emoji_status("☺")
       'unqualified'
       >>> emojet.emoji_status("\N{EMOJI MODIFIER FITZPATRICK TYPE-1-2}")
       'component'

Data
----

.. data:: LANGUAGES

   The supported language codes, as a list of strings.

   .. code-block:: pycon

       >>> sorted(emojet.LANGUAGES)
       ['ar', 'de', 'en', 'es', 'fa', 'fr', 'id', 'it', 'ja', 'ko', 'pt', 'ru', 'tr', 'zh']

.. data:: UNICODE_VERSION

   The Unicode version that the emoji data was built from, as a string.

   .. code-block:: pycon

       >>> emojet.UNICODE_VERSION
       '17.0.0'
