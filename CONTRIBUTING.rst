============
Contributing
============

Updating the data
-----------------

``scripts/generate_data.py`` builds the data table (``src/data.rs``) by downloading the `Public Suffix List <https://publicsuffix.org/>`__ direct from its source, and vendors the list's own test data (``tests/data/test_psl.txt``) from its |source repository|__.

.. |source repository| replace:: source repository
__ https://github.com/publicsuffix/list

The generated files are checked in, so a regular install or build downloads nothing.
To regenerate with the latest list, run the script with uv:

.. code-block:: sh

    uv run scripts/generate_data.py
