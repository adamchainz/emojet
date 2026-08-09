==========
🚀 emojet
==========

.. image:: https://img.shields.io/readthedocs/emojet?style=for-the-badge
   :target: https://emojet.readthedocs.io/en/latest/

.. image:: https://img.shields.io/github/actions/workflow/status/adamchainz/emojet/main.yml.svg?branch=main&style=for-the-badge
   :target: https://github.com/adamchainz/emojet/actions?workflow=CI

.. image:: https://img.shields.io/badge/Coverage-100%25-success?style=for-the-badge
   :target: https://github.com/adamchainz/emojet/actions?workflow=CI

.. image:: https://img.shields.io/pypi/v/emojet.svg?style=for-the-badge
   :target: https://pypi.org/project/emojet/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
   :target: https://github.com/psf/black

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=for-the-badge
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit

----

Emoji for Python, but fast.
A Rust-powered library covering the core API of the |emoji package|__, running 10 to 100+ times faster:

.. |emoji package| replace:: ``emoji`` package
__ https://github.com/carpedm20/emoji/

.. code-block:: pycon

    >>> import emojet
    >>> emojet.emojize("Python is fun :thumbs_up:")
    'Python is fun 👍'
    >>> emojet.demojize("Python is fun 👍")
    'Python is fun :thumbs_up:'

----

**Get better at command line Git** with my book `Boost Your Git DX <https://adamchainz.gumroad.com/l/bygdx>`__.

----

Documentation
-------------

Please see https://emojet.readthedocs.io/.
