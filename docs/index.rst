countryry documentation
=======================

*ISO country, subdivision, language, currency, and script databases in Python.*

----

**Get better at command line Git** with my book `Boost Your Git DX <https://adamchainz.gumroad.com/l/bygdx>`__.

----

Welcome to the documentation for countryry, a Rust-powered library covering the core API of |pycountry|__, with the ISO databases compiled into its binary:

.. |pycountry| replace:: ``pycountry``
__ https://github.com/pycountry/pycountry

.. code-block:: pycon

    >>> import countryry
    >>> countryry.countries.get(alpha_2="DE")
    Country(alpha_2='DE', alpha_3='DEU', flag='🇩🇪', name='Germany', numeric='276', official_name='Federal Republic of Germany')
    >>> countryry.currencies.lookup("euro")
    Currency(alpha_3='EUR', name='Euro', numeric='978')

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
