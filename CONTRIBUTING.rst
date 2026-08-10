============
Contributing
============

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
