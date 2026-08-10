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

* A `perfect hash function <https://docs.rs/phf/>`__ over the 5,316 English names and aliases, giving guaranteed collision-free, single-probe lookups for :func:`.emojize`.

* A static `trie <https://en.wikipedia.org/wiki/Trie>`__ over the code points of all 5,225 emoji sequences, used by the scanner behind :func:`.demojize` and friends, and for exact emoji lookups.

* Per-language name tables, used directly by index without any loading step.

The scanners work on UTF-8 bytes end to end, building each result string in a single buffer, and skip runs of ASCII text with a byte-per-character test, since almost no emoji starts with an ASCII character.
Nothing is parsed at import time: the tables live in the read-only data section of the extension module, so the operating system pages them in on demand.

Benchmarks
----------

From ``scripts/benchmark.py`` on Python 3.14 (macOS, ARM), against ``emoji`` 2.15.0, converting a mixed text/emoji string:

.. list-table::
   :header-rows: 1

   * - Benchmark
     - emoji
     - emojet
     - Speedup
   * - ``import``
     - 20.57 ms
     - 869.94 µs
     - 23.7x
   * - ``import`` + first ``demojize()``
     - 24.45 ms
     - 911.13 µs
     - 26.8x
   * - ``demojize()``
     - 345.12 µs
     - 4.94 µs
     - 69.9x
   * - ``emojize()``
     - 29.23 µs
     - 8.33 µs
     - 3.5x
   * - ``emoji_list()``
     - 316.27 µs
     - 12.29 µs
     - 25.7x
   * - ``emoji_count()``
     - 317.48 µs
     - 2.23 µs
     - 142.4x
   * - ``replace_emoji()``
     - 337.75 µs
     - 4.33 µs
     - 77.9x
   * - ``is_emoji()``
     - 0.04 µs
     - 0.06 µs
     - 0.7x
   * - ``purely_emoji()``
     - 2.12 µs
     - 0.09 µs
     - 23.9x
   * - ``demojize(language='fr')``
     - 362.43 µs
     - 5.46 µs
     - 66.4x
   * - ``version()``
     - 365.57 µs
     - 0.08 µs
     - 4848.8x

Memory use is also lower: importing and calling ``demojize()`` once uses about 17.4 MB of memory with emojet versus 29.2 MB with the ``emoji`` package.

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
