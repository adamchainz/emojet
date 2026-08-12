===========
🌍 countryry
===========

.. image:: https://img.shields.io/readthedocs/countryry?style=for-the-badge
   :target: https://countryry.readthedocs.io/en/latest/

.. image:: https://img.shields.io/github/actions/workflow/status/adamchainz/countryry/main.yml.svg?branch=main&style=for-the-badge
   :target: https://github.com/adamchainz/countryry/actions?workflow=CI

.. image:: https://img.shields.io/badge/Coverage-100%25-success?style=for-the-badge
   :target: https://github.com/adamchainz/countryry/actions?workflow=CI

.. image:: https://img.shields.io/pypi/v/countryry.svg?style=for-the-badge
   :target: https://pypi.org/project/countryry/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
   :target: https://github.com/psf/black

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=for-the-badge
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit

----

ISO country, subdivision, language, currency, and script databases in Python.

.. code-block:: pycon

    >>> import countryry
    >>> countryry.countries.get(alpha_2="DE")
    Country(alpha_2='DE', alpha_3='DEU', flag='🇩🇪', name='Germany', numeric='276', official_name='Federal Republic of Germany')
    >>> countryry.currencies.lookup("euro")
    Currency(alpha_3='EUR', name='Euro', numeric='978')

----

**Get better at command line Git** with my book `Boost Your Git DX <https://adamchainz.gumroad.com/l/bygdx>`__.

----

Documentation
-------------

Please see https://countryry.readthedocs.io/.
