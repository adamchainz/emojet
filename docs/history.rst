======================
History and benchmarks
======================

History
-------

|pycountry|__ has been the standard ISO databases library for Python since 2008.
It repackages the data maintained by Debian's |iso-codes|__ project: ISO 3166 countries and subdivisions, ISO 4217 currencies, ISO 639 languages, and ISO 15924 scripts.

.. |pycountry| replace:: ``pycountry``
__ https://github.com/pycountry/pycountry

.. |iso-codes| replace:: ``iso-codes``
__ https://salsa.debian.org/iso-codes-team/iso-codes

That data comes at a cost, though.
pycountry ships the databases as JSON files, parses each one on first use, and builds its search indices as dicts of Python objects.
That takes tens of milliseconds and tens of megabytes of memory before any record has been looked up.

countryry started in 2026 as a ground-up rewrite focused on speed: a Rust extension module, built with `PyO3 <https://pyo3.rs/>`__ and `maturin <https://www.maturin.rs/>`__, that compiles all the ISO data into its binary.

countryry keeps pycountry's data and lookup behaviour, with a simplified API - see `Differences from pycountry`_.

How it works
------------

countryry compiles all of the ISO data, for all seven databases, into static tables in its Rust extension module:

* One deduplicated string pool holding every value, sliced by spans, so each record is a row of integer pairs.

* Sorted arrays over the lowercased values of each indexed field, giving binary-search ``get()`` lookups without building an index at runtime.

* A sorted array of per-country subdivision ranges, so ``subdivisions.get(country_code=...)`` slices a contiguous run of records.

Record objects hold only an integer index into the tables, and their attributes are read straight from the pool on access.
Nothing is parsed at import time: the tables live in the read-only data section of the extension module, so the operating system pages them in on demand.

Benchmarks
----------

From ``scripts/benchmark.py`` on Python 3.11 (Linux, x86-64), against ``pycountry`` 26.2.16:

.. list-table::
   :header-rows: 1

   * - Benchmark
     - pycountry
     - countryry
     - Speedup
   * - ``import``
     - 39.86 ms
     - 866.02 µs
     - 46.0x
   * - ``import`` + first ``get()``
     - 42.34 ms
     - 866.37 µs
     - 48.9x
   * - ``countries.get()``
     - 0.46 µs
     - 0.26 µs
     - 1.8x
   * - ``subdivisions.get()``
     - 0.77 µs
     - 0.33 µs
     - 2.3x
   * - ``languages.get()``
     - 0.45 µs
     - 0.33 µs
     - 1.3x
   * - ``countries.lookup()``
     - 0.65 µs
     - 0.40 µs
     - 1.6x
   * - ``languages.lookup()``
     - 157.59 µs
     - 19.36 µs
     - 8.1x
   * - ``countries.search_fuzzy()``
     - 7.78 ms
     - 2.04 ms
     - 3.8x
   * - ``len(subdivisions)``
     - 0.16 µs
     - 0.03 µs
     - 6.1x

Memory use is also lower: importing and making one lookup in each of the country, subdivision, and language databases uses about 9.4 MB of memory with countryry versus 25.7 MB with pycountry.

One case is slower: ``subdivisions.get(country_code=...)`` builds a fresh list of records on each call, where pycountry returns its cached set, so call it once and keep the result if you need it repeatedly.

Run the benchmarks yourself with `uv <https://docs.astral.sh/uv/>`__, which installs the latest releases of both packages into a temporary environment:

.. code-block:: sh

    uv run scripts/benchmark.py

Or run the script with plain Python in a virtual environment with both ``pycountry`` and ``countryry`` installed.

Differences from pycountry
--------------------------

countryry keeps pycountry's data, database names, and lookup behaviour, but simplifies the API:

* The databases are static: ``add_entry()`` and ``remove_entry()`` are gone, since the data is compiled into the binary.
  Updates ship as new releases, mirroring new ``iso-codes`` data via pycountry releases.

* The gettext locales for translated names are gone, along with the package's data-directory attributes.

* ``subdivisions.get(country_code=...)`` and ``subdivisions.lookup(<country code>)`` return a list of subdivisions ordered by code, where pycountry returns an unordered set for the former, and its internal index set for the latter.

* ``search_fuzzy()`` exists on ``countries`` and ``subdivisions`` only, where pycountry also inherits it onto ``historic_countries``, with surprising results.

* Subdivisions are class ``Subdivision``, not ``SubdivisionHierarchy``.

* Records are immutable, with value-based equality and hashing: two lookups of the same record give equal objects, where pycountry caches and returns identical objects.

The record attributes, iteration orders, ``repr()`` formats, dict casting, error types, case- and accent-insensitivity, and fuzzy result rankings all match pycountry, verified exhaustively by the test suite.
