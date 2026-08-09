======================
History and benchmarks
======================

History
-------

The |emoji package|__ has been the standard emoji library for Python since 2014.
It assembles names for every emoji, in many languages, from the upstream sources: Unicode's emoji data files, `Unicode CLDR <https://cldr.unicode.org/>`__ annotations, and GitHub's `gemoji <https://github.com/github/gemoji>`__ alias database.

.. |emoji package| replace:: ``emoji`` package
__ https://github.com/carpedm20/emoji/

That data comes at a cost, though.
The ``emoji`` package parses a 520 KB JSON file at import time, builds a search tree of dicts on first use, and loads more JSON files for emoji names in other languages on demand.
That takes tens of milliseconds of import time and tens of megabytes of memory before any emoji has been processed.

emojet started in 2026 as a ground-up rewrite focused on speed: a Rust extension module, built with `PyO3 <https://pyo3.rs/>`__ and `maturin <https://www.maturin.rs/>`__, that compiles all the emoji data into its binary.

emojet keeps the ``emoji`` package's data and conversion behaviour, with a simplified API - see `Differences from the emoji package`_.

How it works
------------

emojet compiles all of the emoji data, for all languages, into static tables in its Rust extension module:

* A `perfect hash function <https://docs.rs/phf/>`__ over the 5,316 English names and aliases, giving guaranteed collision-free, single-probe lookups for ``emojize()``.

* A static trie over the code points of all 5,225 emoji sequences, used by the scanner behind ``demojize()`` and friends, and for exact emoji lookups.

* Per-language name tables, used directly by index without any loading step.

The scanners work on UTF-8 bytes end to end, building each result string in a single buffer, and skip runs of ASCII text with a byte-per-character test, since almost no emoji starts with an ASCII character.
Nothing is parsed at import time: the tables live in the read-only data section of the extension module, so the operating system pages them in on demand.

Benchmarks
----------

From ``scripts/benchmark.py`` on Python 3.13 (Linux, x86-64), against ``emoji`` 2.15.0, converting a mixed text/emoji string:

=================================  =========  =========  =======
Benchmark                          emoji      emojet     Speedup
=================================  =========  =========  =======
``import``                         40.03 ms   828.40 µs  48.3x
``import`` + first ``demojize()``  49.08 ms   779.75 µs  62.9x
``demojize()``                     517.65 µs  4.17 µs    124.2x
``emojize()``                      42.38 µs   6.97 µs    6.1x
``emoji_list()``                   420.78 µs  16.73 µs   25.2x
``emoji_count()``                  431.43 µs  2.55 µs    169.3x
``replace_emoji()``                460.44 µs  3.84 µs    120.0x
``purely_emoji()``                 3.41 µs    0.10 µs    32.7x
``demojize(language='fr')``        479.29 µs  4.64 µs    103.3x
``version()``                      493.96 µs  0.08 µs    6425.9x
=================================  =========  =========  =======

Memory use is also lower: importing and calling ``demojize()`` once uses about 9.7 MB of memory with emojet versus 18.5 MB with the ``emoji`` package.

Run the benchmarks yourself with `uv <https://docs.astral.sh/uv/>`__, which installs the latest releases of both packages into a temporary environment:

.. code-block:: sh

    uv run scripts/benchmark.py

Or run the script with plain Python in a virtual environment with both ``emoji`` and ``emojet`` installed.

Differences from the emoji package
----------------------------------

emojet keeps the ``emoji`` package's data, function names, and conversion behaviour, but simplifies the API:

* Options are keyword-only arguments, and the option-like parameters are gone: the ``config`` class, ``version=`` and ``handle_version=`` filtering, and language loading (all languages are always available).

* The data-structure API is gone: ``EMOJI_DATA``, ``STATUS``, ``analyze()``, and the ``Token``/``EmojiMatch`` classes.
  ``emoji_status()`` covers the common use of looking up qualification statuses.

* ``replace_emoji()`` callables receive just the emoji string.

* ``version()`` always returns a float, and looks up emoji and English names only.

* Unsupported language codes raise ``ValueError``.

* Emoji matching is greedy longest-match, with stray variation selectors dropped and zero-width joiners between emoji kept, so ``emojize()`` reverses ``demojize()``.
  This matches the ``emoji`` package on well-formed text, but in truncated or invalid sequences the ``emoji`` package can fail to match emoji, or split a joined sequence into its components, where emojet still finds the longest valid emoji.
  The test suite verifies that emojet never matches less.

* Similarly, ``emojize()`` converts every well-formed known name, while the ``emoji`` package skips a name when its opening delimiter also closes a preceding non-name run, like the second ``:`` in ``:9:thumbs_up:``.

* Strings must be well-formed Unicode: lone surrogates raise ``UnicodeEncodeError``.

Updating the data
-----------------

``scripts/generate_data.py`` builds the data tables (``src/data.rs``) from their original sources, following the ``emoji`` package's own data pipeline:

* Emoji, their English names, statuses, and versions, from Unicode's |emoji-test.txt|__.

* Variation selector support from Unicode's ``emoji-variation-sequences.txt``.

* Translated names from `Unicode CLDR <https://cldr.unicode.org/>`__ annotations.

* Aliases from GitHub's `gemoji <https://github.com/github/gemoji>`__ database.

.. |emoji-test.txt| replace:: ``emoji-test.txt``
__ https://unicode.org/Public/emoji/latest/emoji-test.txt

Alias names from older sources and their ordering, plus translations for emoji that CLDR does not cover, accumulated over the years by the ``emoji`` package, come from the checked-in seed files in ``scripts/seeds/``, derived from ``emoji`` 2.15.0.
This mirrors the ``emoji`` package's own scripts, which combine the downloads with the data of the previous release.

The generated file is checked in, so a regular install or build downloads nothing.
To regenerate, for example after a new Unicode or CLDR release, update the pinned versions at the top of the script, and run it with uv:

.. code-block:: sh

    uv run scripts/generate_data.py
