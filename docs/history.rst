======================
History and benchmarks
======================

History
-------

The |schwifty package|__ has been the standard IBAN and BIC library for Python since 2015.
It parses and validates account numbers against the `SWIFT IBAN Registry <https://www.swift.com/standards/data-standards/iban-international-bank-account-number>`__, and enriches them with data from many national bank registries.

.. |schwifty package| replace:: ``schwifty`` package
__ https://github.com/mdomke/schwifty

That data comes at a cost, though.
The ``schwifty`` package parses its registry JSON files and compiles a regular expression per country at import time, taking tens of milliseconds and tens of megabytes of memory before any account number has been validated.

swifter started in 2026 as a ground-up rewrite focused on speed: a Rust extension module, built with `PyO3 <https://pyo3.rs/>`__ and `maturin <https://www.maturin.rs/>`__, that compiles the IBAN registry data into its binary.

swifter keeps the ``schwifty`` package's registry data and validation behaviour, with a simplified API - see `Differences from the schwifty package`_.

How it works
------------

swifter compiles the IBAN specifications for all 127 registered countries into static tables in its Rust extension module:

* Per-country entries with the IBAN length, the BBAN structure as (length, character class) groups, and the positions of the bank code, branch code, account code, and national checksum digits.

* The ISO 3166-1 alpha-2 country codes, for validating BIC country codes.

Validation walks the value's bytes once against the country's structure groups, and computes the ISO 7064 mod-97-10 checksum arithmetically, without any big-integer conversion or regular expressions.
Nothing is parsed at import time: the tables live in the read-only data section of the extension module, so the operating system pages them in on demand.

Benchmarks
----------

From ``scripts/benchmark.py`` on Python 3.11 (Linux, x86-64), against ``schwifty`` 2026.7.3, working on a mix of account numbers from 17 countries:

.. list-table::
   :header-rows: 1

   * - Benchmark
     - schwifty
     - swifter
     - Speedup
   * - ``import``
     - 63.00 ms
     - 982.28 µs
     - 64.1x
   * - ``import`` + first ``IBAN()``
     - 66.23 ms
     - 1.00 ms
     - 66.1x
   * - ``IBAN()``
     - 273.52 µs
     - 11.08 µs
     - 24.7x
   * - ``IBAN()`` + components
     - 330.71 µs
     - 15.12 µs
     - 21.9x
   * - ``IBAN(allow_invalid=True).is_valid``
     - 283.22 µs
     - 13.08 µs
     - 21.7x
   * - ``IBAN.generate()``
     - 31.25 µs
     - 1.24 µs
     - 25.2x
   * - ``BIC()``
     - 10.99 µs
     - 1.05 µs
     - 10.5x

Run the benchmarks yourself with `uv <https://docs.astral.sh/uv/>`__, which installs the latest releases of both packages into a temporary environment:

.. code-block:: sh

    uv run scripts/benchmark.py

Or run the script with plain Python in a virtual environment with both ``schwifty`` and ``swifter`` installed.

Differences from the schwifty package
-------------------------------------

swifter keeps the ``schwifty`` package's IBAN registry data, class names, and validation behaviour, but simplifies the API:

* :class:`.IBAN` and :class:`.BIC` are not ``str`` subclasses.
  They still compare equal to strings, hash like their compact strings, support ``len()``, and convert with ``str()``, but string methods and slicing require going through :attr:`~swifter.IBAN.compact`.

* Options are keyword-only arguments.

* The bank registry data is gone, along with the APIs that need it: ``IBAN.bank``, ``IBAN.bic``, ``BIC.from_bank_code()``, ``BIC.candidates_from_bank_code()``, ``BIC.exists``, and friends.
  swifter validates and parses account numbers; it does not identify banks.

* National checksum algorithms are not implemented: there is no ``validate_bban`` parameter, and :meth:`.IBAN.generate` leaves national checksum digits as zeroes.
  The IBAN-level mod-97-10 checksum is always validated.

* ``IBAN.random()`` and ``BIC.random()`` are gone.

* ``iban.bban`` returns a plain string rather than a ``BBAN`` object, with the components available directly on the :class:`.IBAN`.

* The Pydantic integration is gone.

* The exceptions keep their names, minus ``InvalidBBANChecksum`` and ``GenerateRandomOverflowError``, with the base exception renamed from ``SchwiftyException`` to :exc:`.SwifterError`, still a ``ValueError`` subclass.
