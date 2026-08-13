======================
History and benchmarks
======================

History
-------

The `Public Suffix List <https://publicsuffix.org/>`__ is the volunteer-maintained registry, started by Mozilla in 2007, of the domain suffixes under which anyone can register names: ``com``, ``co.uk``, ``github.io``, and thousands more.
Knowing where the public part of a domain ends is what lets browsers scope cookies, and lets other software group hosts by their registrable domain.

The |publicsuffixlist package|__ has been a standard way to query the list in Python since 2014.
It bundles a snapshot of the list as a data file, and each ``PublicSuffixList`` instance parses those ~250 KB into a large set of rules, in both Unicode and punycode forms, before the first lookup.
That takes tens of milliseconds and several megabytes of memory, in every process.

.. |publicsuffixlist package| replace:: ``publicsuffixlist`` package
__ https://github.com/ko-zu/psl

pslr started in 2026 as a ground-up rewrite focused on speed: a Rust extension module, built with `PyO3 <https://pyo3.rs/>`__ and `maturin <https://www.maturin.rs/>`__, with the whole list compiled into its binary.

pslr keeps the ``publicsuffixlist`` package's data source and lookup behaviour, with a simplified API.
See `Differences from the publicsuffixlist package`_.

How it works
------------

``scripts/generate_data.py`` downloads the list direct from its source at publicsuffix.org and compiles it into a static table (``src/data.rs``): a `trie <https://en.wikipedia.org/wiki/Trie>`__ over rule labels, walked right to left from the TLD, with exact, wildcard, and exception rules as node flags.
Every internationalized rule is stored in both its Unicode and punycode forms, generated like the ``publicsuffixlist`` package does, so both kinds of domain match.
The generated file is checked in, so a regular install or build downloads nothing.
Updating the data is rerunning the script.

Around that trie, pslr implements the ``publicsuffixlist`` package's handling of domains: lowercasing, ignoring one trailing dot, rejecting empty labels, and treating the parent domain of a wildcard rule as itself public, the interpretation required by the list's own linter.
The deepest matching rule wins in a single walk, and the results come back as slices of the prepared domain, built in Rust without constructing any intermediate Python objects.

Nothing is parsed at import time: the tables live in the read-only data section of the extension module, so the operating system pages them in on demand, and every process shares them.

Benchmarks
----------

From ``scripts/benchmark.py`` on Python 3.11 (Linux, x86-64), against ``publicsuffixlist`` 1.0.2.20260726:

.. list-table::
   :header-rows: 1

   * - Benchmark
     - publicsuffixlist
     - pslr
     - Speedup
   * - ``import`` + first ``publicsuffix()``
     - 51.37 ms
     - 991.37 µs
     - 51.8x
   * - ``publicsuffix()``
     - 2.06 µs
     - 0.48 µs
     - 4.3x
   * - ``publicsuffix()``, unknown TLD
     - 1.90 µs
     - 0.37 µs
     - 5.2x
   * - ``privatesuffix()``
     - 2.03 µs
     - 0.46 µs
     - 4.4x
   * - ``privatesuffix()``, wildcard rule
     - 2.23 µs
     - 0.34 µs
     - 6.6x
   * - ``is_private()``
     - 1.80 µs
     - 0.39 µs
     - 4.6x
   * - ``privateparts()``
     - 2.49 µs
     - 0.60 µs
     - 4.2x
   * - ``subdomain()``
     - 2.28 µs
     - 0.47 µs
     - 4.8x

Memory use is also lower: importing and making one lookup peaks at about 8.0 MB of memory with pslr versus 12.3 MB with the ``publicsuffixlist`` package, against a 7.5 MB baseline interpreter.

Run the benchmarks yourself with `uv <https://docs.astral.sh/uv/>`__, which installs the latest releases of both packages into a temporary environment:

.. code-block:: sh

    uv run scripts/benchmark.py

Or run the script with plain Python in a virtual environment with both ``publicsuffixlist`` and ``pslr`` installed.

Differences from the publicsuffixlist package
---------------------------------------------

pslr keeps the ``publicsuffixlist`` package's method names, data source, and lookup behaviour, but simplifies the API:

* Everything is a module-level function: there is no ``PublicSuffixList`` class to construct, since the compiled-in list is the only data source.
  The ``source=`` option is gone, and ``accept_encoded_idn=`` is effectively always true: Unicode and punycode rule forms are both always matched.

* Options are keyword-only arguments.
  ``accept_unknown`` and ``only_icann``, renamed ``icann_only``, move from constructor defaults to per-call options, honoured consistently: also by :func:`.is_public`, :func:`.is_private`, and :func:`.subdomain`, where the ``publicsuffixlist`` package uses its constructor defaults (and, for ``subdomain()``, ignores the ``accept_unknown`` argument it accepts).

* The ``suffix()`` alias is gone: use :func:`.privatesuffix`.

* Domains are strings: the tuple-of-bytes API is gone.

* Invalid domains consistently return :obj:`None` or :obj:`False`, where the ``publicsuffixlist`` package's ``subdomain()`` can raise :exc:`TypeError`.

* Strings must be well-formed Unicode: lone surrogates raise :exc:`UnicodeEncodeError`, rather than being carried through with ``surrogateescape``.
