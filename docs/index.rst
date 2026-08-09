emojet documentation
====================

*Convert, find, and count emoji in Python.*

----

**Get better at command line Git** with my book `Boost Your Git DX <https://adamchainz.gumroad.com/l/bygdx>`__.

----

Welcome to the documentation for emojet, a Rust-powered library covering the core API of the |emoji package|__, running 10 to 100+ times faster:

.. |emoji package| replace:: ``emoji`` package
__ https://github.com/carpedm20/emoji/

.. code-block:: pycon

    >>> import emojet
    >>> emojet.emojize("Python is fun :thumbs_up:")
    'Python is fun 👍'
    >>> emojet.demojize("Python is fun 👍")
    'Python is fun :thumbs_up:'

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
