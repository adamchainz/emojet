=============
API reference
=============

.. module:: countryry

Everything lives in the ``countryry`` module, as one database object per ISO standard:

.. list-table::
   :header-rows: 1

   * - Database
     - Standard
     - Contents
   * - :data:`countries`
     - ISO 3166-1
     - Countries
   * - :data:`subdivisions`
     - ISO 3166-2
     - Country subdivisions, like states and provinces
   * - :data:`historic_countries`
     - ISO 3166-3
     - Formerly used names of countries
   * - :data:`currencies`
     - ISO 4217
     - Currencies
   * - :data:`languages`
     - ISO 639-3
     - Languages
   * - :data:`language_families`
     - ISO 639-5
     - Language families and groups
   * - :data:`scripts`
     - ISO 15924
     - Scripts (writing systems)

The data and behaviour match those of |pycountry|__ - see :doc:`history` for how the two libraries relate.

.. |pycountry| replace:: ``pycountry``
__ https://github.com/pycountry/pycountry

Databases
---------

Each database is iterable, sized, and searchable:

.. code-block:: pycon

    >>> len(countryry.countries)
    249
    >>> next(iter(countryry.countries))
    Country(alpha_2='AW', alpha_3='ABW', flag='🇦🇼', name='Aruba', numeric='533')

.. method:: get(*, default=None, **criterion)
   :noindex:

   Return the record matching a single ``field=value`` criterion, compared case-insensitively, or *default* when there is no match.
   The field must be one the database indexes - for example countries can be fetched by ``alpha_2``, ``alpha_3``, ``numeric``, ``name``, ``official_name``, ``common_name``, or ``flag``:

   .. code-block:: pycon

       >>> countryry.countries.get(alpha_2="DE")
       Country(alpha_2='DE', alpha_3='DEU', flag='🇩🇪', name='Germany', numeric='276', official_name='Federal Republic of Germany')
       >>> countryry.countries.get(name="germany").alpha_2
       'DE'
       >>> countryry.countries.get(alpha_2="XX", default="unknown")
       'unknown'

   Passing zero or several criteria raises :exc:`TypeError`, a non-string value raises :exc:`LookupError`, and a non-indexed field raises :exc:`KeyError`.

   Subdivisions support one extra criterion, ``country_code``, returning the list of a country's subdivisions, empty for countries without any:

   .. code-block:: pycon

       >>> len(countryry.subdivisions.get(country_code="US"))
       57
       >>> countryry.subdivisions.get(country_code="AQ")
       []

.. method:: lookup(value)
   :noindex:

   Return the first record with *value* in any field, compared case-insensitively, searching indexed fields first.
   Raises :exc:`LookupError` when nothing matches:

   .. code-block:: pycon

       >>> countryry.currencies.lookup("euro")
       Currency(alpha_3='EUR', name='Euro', numeric='978')
       >>> countryry.languages.lookup("de")
       Language(alpha_2='de', alpha_3='deu', bibliographic='ger', name='German', scope='I', type='L')

   On subdivisions, a country code looks up the country's subdivisions, as a list.

.. method:: search_fuzzy(query)
   :noindex:

   On :data:`countries` and :data:`subdivisions` only: return a list of records matching *query* loosely, best matches first.
   Matching is case-insensitive and accent-insensitive, and considers exact matches, matches on a name's initials, and substring matches, in countries' own names and their subdivisions' names.
   Raises :exc:`LookupError` when nothing matches:

   .. code-block:: pycon

       >>> countryry.countries.search_fuzzy("Aland")[0].alpha_2
       'AX'
       >>> countryry.countries.search_fuzzy("berlin")[0].alpha_2
       'DE'
       >>> countryry.subdivisions.search_fuzzy("California")[0].code
       'US-CA'

Records
-------

Records are immutable objects with one attribute per field in the source data.
Fields that a record does not have raise :exc:`AttributeError`, so use :func:`getattr` with a default for optional fields like ``official_name``.
Records support equality, hashing, and casting to a :class:`dict`:

.. code-block:: pycon

    >>> aruba = countryry.countries.get(alpha_2="AW")
    >>> aruba.name
    'Aruba'
    >>> getattr(aruba, "official_name", None)
    >>> dict(aruba)
    {'alpha_2': 'AW', 'alpha_3': 'ABW', 'flag': '🇦🇼', 'name': 'Aruba', 'numeric': '533'}

.. class:: Country

   A country, from :data:`countries` (ISO 3166-1) or :data:`historic_countries` (ISO 3166-3).

   Countries always have ``alpha_2``, ``alpha_3``, ``numeric``, ``name``, and ``flag`` - the country's emoji flag - and may have ``official_name`` and ``common_name``.
   Historic countries have ``alpha_2``, ``alpha_3``, ``alpha_4``, ``name``, and ``withdrawal_date``, and may have ``numeric`` and ``comment``.

.. class:: Subdivision

   A country subdivision, from :data:`subdivisions` (ISO 3166-2).

   Subdivisions have ``code``, ``name``, ``type``, and ``country_code``, plus ``parent_code``, the full code of the parent subdivision, or None for top-level subdivisions.

   .. attribute:: country

      The subdivision's :class:`Country`.

   .. attribute:: parent

      The parent :class:`Subdivision`, or None for top-level subdivisions.

   .. code-block:: pycon

       >>> ain = countryry.subdivisions.get(code="FR-01")
       >>> ain.name, ain.type
       ('Ain', 'Metropolitan department')
       >>> ain.parent.name
       'Auvergne-Rhône-Alpes'
       >>> ain.country.name
       'France'

.. class:: Currency

   A currency, from :data:`currencies` (ISO 4217), with ``alpha_3``, ``name``, and ``numeric``.

.. class:: Language

   A language, from :data:`languages` (ISO 639-3), with ``alpha_3``, ``name``, ``scope``, and ``type``, and optionally ``alpha_2``, ``common_name``, ``inverted_name``, and ``bibliographic``.

.. class:: LanguageFamily

   A language family or group, from :data:`language_families` (ISO 639-5), with ``alpha_3`` and ``name``.

.. class:: Script

   A script (writing system), from :data:`scripts` (ISO 15924), with ``alpha_4``, ``name``, and ``numeric``.
