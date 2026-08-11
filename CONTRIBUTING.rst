============
Contributing
============

Updating the data
-----------------

``scripts/generate_data.py`` builds the data tables (``src/data.rs``) by downloading the data from its original sources:

* The `SWIFT IBAN Registry <https://www.swift.com/standards/data-standards/iban>`__, as the TXT release linked from that page: the IBAN specification for each country - BBAN structure, IBAN length, SEPA membership, and the positions of the bank and branch codes within the BBAN.

* The ISO 3166-1 alpha-2 country codes, used to validate the country codes of BICs, from the `Debian iso-codes project <https://salsa.debian.org/iso-codes-team/iso-codes>`__, the canonical open dataset of the ISO 3166 standard.

The downloads are combined with the checked-in seed file ``scripts/seeds/registry_overrides.json``: curated corrections and additions that the registry itself does not carry - the positions of account codes and national checksum digits that the registry leaves unspecified, and the countries with partial-IBAN formats that it does not list.
This data is derived from the |schwifty package|__ (version 2026.7.3), which accumulated it over years of releases.
This mirrors the ``schwifty`` package's own pipeline, which combines the registry download with a hand-maintained overrides file.

.. |schwifty package| replace:: ``schwifty`` package
__ https://github.com/mdomke/schwifty

The generated file is checked in, so a regular install or build downloads nothing.
To regenerate, for example after a new registry release, run the script with uv:

.. code-block:: sh

    uv run scripts/generate_data.py
