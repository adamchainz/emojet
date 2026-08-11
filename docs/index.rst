swifter documentation
=====================

*Validate and parse IBANs and BICs in Python.*

----

**Get better at command line Git** with my book `Boost Your Git DX <https://adamchainz.gumroad.com/l/bygdx>`__.

----

Welcome to the documentation for swifter, a Rust-powered library covering the core API of the |schwifty package|__:

.. |schwifty package| replace:: ``schwifty`` package
__ https://github.com/mdomke/schwifty

.. code-block:: pycon

    >>> import swifter
    >>> iban = swifter.IBAN("DE89 3704 0044 0532 0130 00")
    >>> iban.bank_code
    '37040044'
    >>> swifter.BIC("GENODEM1GLS").country_code
    'DE'

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   installation
   api
   history
   changelog


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
