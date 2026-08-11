=============
API reference
=============

.. module:: swifter

Everything lives in the ``swifter`` module, and all optional parameters are keyword-only.

Input values are normalized before use: whitespace is removed and letters are uppercased, so ``"de89 3704..."`` and ``"DE893704..."`` are equivalent.

The IBAN specifications - lengths, structures, and component positions - come from the SWIFT IBAN Registry, for the country codes in :data:`COUNTRY_CODES`.
The data matches that of the |schwifty package|__ - see :doc:`history` for how the two libraries relate.

.. |schwifty package| replace:: ``schwifty`` package
__ https://github.com/mdomke/schwifty

IBAN
----

.. class:: IBAN(iban, *, allow_invalid=False)

   An International Bank Account Number.

   Instantiating validates the value and raises a :exc:`SwifterError` subclass if it is invalid:

   .. code-block:: pycon

       >>> iban = swifter.IBAN("DE89 3704 0044 0532 0130 00")
       >>> iban
       <IBAN=DE89370400440532013000>
       >>> swifter.IBAN("DE99 3704 0044 0532 0130 00")
       Traceback (most recent call last):
       ...
       swifter.InvalidChecksumDigits: Invalid checksum digits in IBAN 'DE99370400440532013000'

   Pass ``allow_invalid=True`` to skip validation, for example to inspect the components of an invalid value:

   .. code-block:: pycon

       >>> iban = swifter.IBAN("DE99 3704 0044 0532 0130 00", allow_invalid=True)
       >>> iban.is_valid
       False
       >>> iban.bank_code
       '37040044'

   Instances compare equal to each other and to strings by their compact form, and are hashable and orderable:

   .. code-block:: pycon

       >>> swifter.IBAN("DE89370400440532013000") == swifter.IBAN("de89 3704 0044 0532 0130 00")
       True
       >>> swifter.IBAN("DE89370400440532013000") == "DE89370400440532013000"
       True

   .. classmethod:: from_bban(country_code, bban, *, allow_invalid=False)

      Create an IBAN from a country code and national Basic Bank Account Number, computing the checksum digits:

      .. code-block:: pycon

          >>> swifter.IBAN.from_bban("DE", "370400440532013000")
          <IBAN=DE89370400440532013000>

   .. classmethod:: generate(country_code, *, bank_code, account_code, branch_code="")

      Generate an IBAN from its components.
      Each component is right-aligned within its field in the country's BBAN structure and padded with zeroes, and the checksum digits are computed:

      .. code-block:: pycon

          >>> swifter.IBAN.generate("DE", bank_code="37040044", account_code="532013000")
          <IBAN=DE89370400440532013000>

      Raises :exc:`InvalidBankCode`, :exc:`InvalidBranchCode`, or :exc:`InvalidAccountCode` if a component exceeds its field, and :exc:`InvalidStructure` if the result does not match the country's BBAN structure.

   .. method:: validate()

      Return ``True``, or raise a :exc:`SwifterError` subclass if the IBAN is invalid.
      Useful with ``allow_invalid=True`` to surface the reason a value is invalid.

   .. attribute:: is_valid

      Whether the IBAN is valid, as a bool.

      .. code-block:: pycon

          >>> swifter.IBAN("DE99370400440532013000", allow_invalid=True).is_valid
          False

   .. attribute:: compact

      The IBAN without any spaces, as also returned by ``str()``:

      .. code-block:: pycon

          >>> swifter.IBAN("DE89 3704 0044 0532 0130 00").compact
          'DE89370400440532013000'

   .. attribute:: formatted

      The IBAN spaced into groups of four characters:

      .. code-block:: pycon

          >>> swifter.IBAN("DE89370400440532013000").formatted
          'DE89 3704 0044 0532 0130 00'

   .. attribute:: country_code

      The ISO 3166 alpha-2 country code:

      .. code-block:: pycon

          >>> swifter.IBAN("DE89370400440532013000").country_code
          'DE'

   .. attribute:: checksum_digits

      The two checksum digits after the country code:

      .. code-block:: pycon

          >>> swifter.IBAN("DE89370400440532013000").checksum_digits
          '89'

   .. attribute:: bban

      The country-specific Basic Bank Account Number: everything after the country code and checksum digits.

      .. code-block:: pycon

          >>> swifter.IBAN("DE89370400440532013000").bban
          '370400440532013000'

   .. attribute:: bank_code

      The country-specific bank code, or an empty string if the country does not define its position:

      .. code-block:: pycon

          >>> swifter.IBAN("DE89370400440532013000").bank_code
          '37040044'

   .. attribute:: branch_code

      The country-specific branch code, or an empty string if the country does not define one:

      .. code-block:: pycon

          >>> swifter.IBAN("GB29NWBK60161331926819").branch_code
          '601613'

   .. attribute:: account_code

      The country-specific account code, or an empty string if the country does not define its position:

      .. code-block:: pycon

          >>> swifter.IBAN("DE89370400440532013000").account_code
          '0532013000'

   .. attribute:: national_checksum_digits

      The country-specific checksum digits within the BBAN, or an empty string if the country does not have any:

      .. code-block:: pycon

          >>> swifter.IBAN("IT60X0542811101000000123456").national_checksum_digits
          'X'

   .. attribute:: in_sepa_zone

      Whether the country is in the Single Euro Payments Area, as a bool:

      .. code-block:: pycon

          >>> swifter.IBAN("DE89370400440532013000").in_sepa_zone
          True

BIC
---

.. class:: BIC(bic, *, allow_invalid=False)

   A Business Identifier Code, as defined in ISO 9362:2022.

   Instantiating validates the value - its length, structure, and country code - and raises a :exc:`SwifterError` subclass if it is invalid:

   .. code-block:: pycon

       >>> bic = swifter.BIC("GENODEM1GLS")
       >>> bic
       <BIC=GENODEM1GLS>
       >>> swifter.BIC("GENOXXM1GLS")
       Traceback (most recent call last):
       ...
       swifter.InvalidCountryCode: Unknown country code 'XX'

   Pass ``allow_invalid=True`` to skip validation.
   Instances compare equal to each other and to strings by their compact form, and are hashable and orderable.

   .. method:: validate()

      Return ``True``, or raise a :exc:`SwifterError` subclass if the BIC is invalid.

   .. attribute:: is_valid

      Whether the BIC is valid, as a bool.

   .. attribute:: compact

      The BIC without any spaces, as also returned by ``str()``.

   .. attribute:: formatted

      The BIC spaced into its components:

      .. code-block:: pycon

          >>> swifter.BIC("GENODEM1GLS").formatted
          'GENO DE M1 GLS'

   .. attribute:: bank_code

      The bank code: the first four characters:

      .. code-block:: pycon

          >>> swifter.BIC("GENODEM1GLS").bank_code
          'GENO'

   .. attribute:: country_code

      The ISO 3166 alpha-2 country code:

      .. code-block:: pycon

          >>> swifter.BIC("GENODEM1GLS").country_code
          'DE'

   .. attribute:: location_code

      The two-character location code:

      .. code-block:: pycon

          >>> swifter.BIC("GENODEM1GLS").location_code
          'M1'

   .. attribute:: branch_code

      The three-character branch code, or an empty string for eight character BICs:

      .. code-block:: pycon

          >>> swifter.BIC("GENODEM1GLS").branch_code
          'GLS'
          >>> swifter.BIC("GENODEM1").branch_code
          ''

   .. attribute:: type

      The connection type indicated by the second character of the location code: ``"testing"`` for ``0``, ``"passive"`` for ``1``, ``"reverse billing"`` for ``2``, or ``"default"`` otherwise:

      .. code-block:: pycon

          >>> swifter.BIC("GENODEFF").type
          'default'
          >>> swifter.BIC("GENODEM1GLS").type
          'passive'
          >>> swifter.BIC("GENODEM0GLS").type
          'testing'

Exceptions
----------

All exceptions inherit from :exc:`SwifterError`, which inherits from :exc:`ValueError`.

.. exception:: SwifterError

   Base exception for all swifter errors.

.. exception:: InvalidLength

   The length of the value does not match the specification.

.. exception:: InvalidStructure

   The value contains unexpected characters.

.. exception:: InvalidCountryCode

   The country code of the value is unknown.

.. exception:: InvalidChecksumDigits

   The IBAN's checksum digits are incorrect.

.. exception:: InvalidBankCode

   The bank code passed to :meth:`IBAN.generate` does not fit the country's IBAN structure.

.. exception:: InvalidBranchCode

   The branch code passed to :meth:`IBAN.generate` does not fit the country's IBAN structure.

.. exception:: InvalidAccountCode

   The account code passed to :meth:`IBAN.generate` does not fit the country's IBAN structure.

Data
----

.. data:: COUNTRY_CODES

   The country codes in the IBAN registry data, as a sorted list of strings.

   .. code-block:: pycon

       >>> len(swifter.COUNTRY_CODES)
       127
       >>> swifter.COUNTRY_CODES[:5]
       ['AD', 'AE', 'AL', 'AO', 'AT']
