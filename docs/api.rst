=============
API reference
=============

.. module:: pslr

Everything lives in the ``pslr`` module, and all optional parameters are keyword-only.

Functions look domains up in the `Public Suffix List <https://publicsuffix.org/>`__, compiled into the extension module. See :doc:`history` for how the data is updated.
A **public suffix** is a domain under which anyone can register names, like ``com``, ``co.uk``, or ``github.io``.
The **private suffix**, also known as the registrable domain, eTLD+1, or apex domain, is the public suffix plus one more label, like ``example.co.uk``, the unit that domain registrations, cookie scoping, and rate limiting usually care about.

Domains are matched case-insensitively, one trailing dot is ignored, and internationalized domain names are matched in both Unicode (``食狮.中国``) and punycode (``xn--85x722f.xn--fiqs8s``) forms.
Results are lowercase, preserving the input's Unicode or punycode form.
Pass ``keep_case=True`` to preserve the input's case too.
A domain containing empty labels, like ``a..com`` or ``.com``, is invalid: lookups return :obj:`None` and checks return :obj:`False`.

By default, an unknown top-level domain counts as a public suffix, matching the list's implicit ``*`` rule for new or private TLDs.
Pass ``accept_unknown=False`` to treat unknown TLDs as no match instead.

The list has two sections: ICANN suffixes, delegated by domain registries, and private suffixes, registered by site operators offering subdomains to the public, like ``github.io``.
Both match by default.
Pass ``icann_only=True`` to match only registry-defined suffixes.

Strings must be well-formed Unicode: lone surrogates raise :exc:`UnicodeEncodeError`.

Lookup
------

.. function:: publicsuffix(domain: str, *, accept_unknown: bool = True, icann_only: bool = False, keep_case: bool = False) -> str | None

   Return the longest public suffix of *domain*, or :obj:`None` if it has none.

   .. code-block:: pycon

       >>> pslr.publicsuffix("www.tfl.gov.uk")
       'gov.uk'
       >>> pslr.publicsuffix("adamchainz.github.io")
       'github.io'
       >>> pslr.publicsuffix("adamchainz.github.io", icann_only=True)
       'io'
       >>> pslr.publicsuffix("example.unknowntld")
       'unknowntld'
       >>> pslr.publicsuffix("example.unknowntld", accept_unknown=False) is None
       True
       >>> pslr.publicsuffix("Example.COM", keep_case=True)
       'COM'

   Wildcard and exception rules apply, including treating a wildcard rule's parent domain as itself public:

   .. code-block:: pycon

       >>> pslr.publicsuffix("b.test.ck")  # *.ck
       'test.ck'
       >>> pslr.publicsuffix("www.ck")  # !www.ck
       'ck'
       >>> pslr.publicsuffix("kobe.jp")  # parent of *.kobe.jp
       'kobe.jp'

.. function:: privatesuffix(domain: str, *, accept_unknown: bool = True, icann_only: bool = False, keep_case: bool = False) -> str | None

   Return the private suffix of *domain*: the shortest suffix assigned to a registrant, one label beyond the public suffix.
   Returns :obj:`None` if *domain* is entirely public, or invalid.

   .. code-block:: pycon

       >>> pslr.privatesuffix("www.tfl.gov.uk")
       'tfl.gov.uk'
       >>> pslr.privatesuffix("gov.uk") is None
       True

Checking
--------

.. function:: is_public(domain: str, *, accept_unknown: bool = True, icann_only: bool = False) -> bool

   Return whether *domain* is entirely a public suffix.

   .. code-block:: pycon

       >>> pslr.is_public("gov.uk")
       True
       >>> pslr.is_public("tfl.gov.uk")
       False

.. function:: is_private(domain: str, *, accept_unknown: bool = True, icann_only: bool = False) -> bool

   Return whether *domain* has a private part: whether it is a private suffix or a subdomain of one.

   .. code-block:: pycon

       >>> pslr.is_private("tfl.gov.uk")
       True
       >>> pslr.is_private("gov.uk")
       False

Splitting
---------

.. function:: privateparts(domain: str, *, accept_unknown: bool = True, icann_only: bool = False, keep_case: bool = False) -> tuple[str, ...] | None

   Return a tuple of the subdomain labels of *domain* followed by its private suffix, or :obj:`None` if it has no private suffix.

   .. code-block:: pycon

       >>> pslr.privateparts("bank.dlr.tfl.gov.uk")
       ('bank', 'dlr', 'tfl.gov.uk')
       >>> pslr.privateparts("tfl.gov.uk")
       ('tfl.gov.uk',)

.. function:: subdomain(domain: str, depth: int, *, accept_unknown: bool = True, icann_only: bool = False, keep_case: bool = False) -> str | None

   Return the suffix of *domain* reaching *depth* labels beyond its private suffix, or :obj:`None` if *domain* has too few labels.
   Depth 0 is the private suffix itself.

   .. code-block:: pycon

       >>> pslr.subdomain("bank.dlr.tfl.gov.uk", 0)
       'tfl.gov.uk'
       >>> pslr.subdomain("bank.dlr.tfl.gov.uk", 1)
       'dlr.tfl.gov.uk'
       >>> pslr.subdomain("bank.dlr.tfl.gov.uk", 3) is None
       True

Data
----

.. data:: LIST_CHECKSUM

   The SHA-256 checksum of the Public Suffix List file that the data was built from, as a hex string, identifying the exact snapshot compiled in.

   .. code-block:: pycon

       >>> pslr.LIST_CHECKSUM
       'fe6adc7fb8014f57d28d69b18d0aa3e581efb432544922e12131a5d4a87bd954'
