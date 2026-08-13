LIST_CHECKSUM: str

def publicsuffix(
    domain: str,
    *,
    accept_unknown: bool = True,
    icann_only: bool = False,
    keep_case: bool = False,
) -> str | None: ...
def privatesuffix(
    domain: str,
    *,
    accept_unknown: bool = True,
    icann_only: bool = False,
    keep_case: bool = False,
) -> str | None: ...
def is_public(
    domain: str,
    *,
    accept_unknown: bool = True,
    icann_only: bool = False,
) -> bool: ...
def is_private(
    domain: str,
    *,
    accept_unknown: bool = True,
    icann_only: bool = False,
) -> bool: ...
def privateparts(
    domain: str,
    *,
    accept_unknown: bool = True,
    icann_only: bool = False,
    keep_case: bool = False,
) -> tuple[str, ...] | None: ...
def subdomain(
    domain: str,
    depth: int,
    *,
    accept_unknown: bool = True,
    icann_only: bool = False,
    keep_case: bool = False,
) -> str | None: ...
