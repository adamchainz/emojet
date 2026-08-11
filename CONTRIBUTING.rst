============
Contributing
============

Updating the data
-----------------

``scripts/generate_data.py`` builds the data tables (``src/data.rs``) from the checked-in seed files in ``scripts/seeds/``:

* ``iban_registry.json`` - the IBAN specification for each country: BBAN structure, IBAN length, SEPA membership, and the positions of the bank code, branch code, account code, and national checksum digits within the BBAN.
  Derived from the `SWIFT IBAN Registry <https://www.swift.com/standards/data-standards/iban-international-bank-account-number>`__, via the |schwifty package|__ (version 2026.7.3).

* ``country_codes.json`` - the ISO 3166-1 alpha-2 country codes, used to validate the country codes of BICs.

.. |schwifty package| replace:: ``schwifty`` package
__ https://github.com/mdomke/schwifty

The generated file is checked in, so a regular install or build downloads nothing.
To regenerate, for example after updating the seeds from a new registry release, run the script with uv:

.. code-block:: sh

    uv run scripts/generate_data.py
