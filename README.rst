==========
🏦 swifter
==========

.. image:: https://img.shields.io/readthedocs/swifter?style=for-the-badge
   :target: https://swifter.readthedocs.io/en/latest/

.. image:: https://img.shields.io/github/actions/workflow/status/adamchainz/swifter/main.yml.svg?branch=main&style=for-the-badge
   :target: https://github.com/adamchainz/swifter/actions?workflow=CI

.. image:: https://img.shields.io/badge/Coverage-100%25-success?style=for-the-badge
   :target: https://github.com/adamchainz/swifter/actions?workflow=CI

.. image:: https://img.shields.io/pypi/v/swifter.svg?style=for-the-badge
   :target: https://pypi.org/project/swifter/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
   :target: https://github.com/psf/black

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=for-the-badge
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit

----

Validate and parse IBANs and BICs in Python.

.. code-block:: pycon

    >>> import swifter
    >>> iban = swifter.IBAN("DE89 3704 0044 0532 0130 00")
    >>> iban.bank_code
    '37040044'
    >>> swifter.BIC("GENODEM1GLS").country_code
    'DE'

----

**Get better at command line Git** with my book `Boost Your Git DX <https://adamchainz.gumroad.com/l/bygdx>`__.

----

Documentation
-------------

Please see https://swifter.readthedocs.io/.
