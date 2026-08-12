============
Contributing
============

Updating the data
-----------------

``scripts/generate_data.py`` builds the data tables (``src/data.rs``) from the ISO standards data maintained by Debian's |iso-codes|__ project, as shipped in the |pycountry|__ package:

* ISO 3166-1 countries and ISO 3166-3 formerly used country names.

* ISO 3166-2 country subdivisions.

* ISO 4217 currencies.

* ISO 639-3 languages and ISO 639-5 language families.

* ISO 15924 scripts.

.. |iso-codes| replace:: ``iso-codes``
__ https://salsa.debian.org/iso-codes-team/iso-codes

.. |pycountry| replace:: ``pycountry``
__ https://github.com/pycountry/pycountry

The script downloads the data files from the pycountry release pinned at its top, which pycountry ships unchanged from ``iso-codes``, except for adding each country's emoji flag.
Reading them from the pinned release keeps countryry's data identical to the pycountry version that the test suite compares against, so the exhaustive compatibility tests in ``tests/test_compat.py`` verify every record.

The generated file is checked in, so a regular install or build downloads nothing.
To regenerate, for example after a new pycountry release with new ``iso-codes`` data, update the pinned version at the top of the script and in the test dependencies in ``pyproject.toml``, and run it with uv:

.. code-block:: sh

    uv run scripts/generate_data.py
