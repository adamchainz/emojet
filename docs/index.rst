pslr documentation
==================

*Extract public suffixes and registrable domains in Python.*

----

**Get better at command line Git** with my book `Boost Your Git DX <https://adamchainz.gumroad.com/l/bygdx>`__.

----

Welcome to the documentation for pslr, a Rust-powered library covering the core API of the |publicsuffixlist package|__, running many times faster:

.. |publicsuffixlist package| replace:: ``publicsuffixlist`` package
__ https://github.com/ko-zu/psl

.. code-block:: pycon

    >>> import pslr
    >>> pslr.publicsuffix("www.tfl.gov.uk")
    'gov.uk'
    >>> pslr.privatesuffix("www.tfl.gov.uk")
    'tfl.gov.uk'

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
