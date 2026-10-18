from dataclasses import dataclass, field
from typing import Optional

# Confidence tags shown on every finding.
FILED_REPORTED = "Filed-Reported"   # number stated verbatim in a filing
FILED_COMPUTED = "Filed-Computed"   # our arithmetic on filed numbers
TRANSCRIPT = "Transcript"           # user-supplied transcript only
PRESS_HEADLINE = "Press-Headline"   # context only, never confirmation
SECONDARY = "Secondary-Unverified"  # number not yet traced to an SEC filing
CONFIDENCE_TAGS = {FILED_REPORTED, FILED_COMPUTED, TRANSCRIPT, PRESS_HEADLINE,
                   SECONDARY}
FILED_TAGS = {FILED_REPORTED, FILED_COMPUTED}

import re as _re
_ACCESSION = _re.compile(r"^\d{10}-\d{2}-\d{6}$")


def is_sec_accession(s: str) -> bool:
    return bool(_ACCESSION.match(s or ""))


def is_link(url: str) -> bool:
    return bool(_re.match(r"^https?://[^\s]+$", url or ""))


def is_verified_sec_source(src) -> bool:
    """SEC accession number AND a sec.gov link to that same accession."""
    if not (is_sec_accession(src.accession) and is_link(src.url)):
        return False
    host = _re.match(r"^https?://([^/]+)", src.url).group(1).lower()
    return (host in ("www.sec.gov", "sec.gov")
            and src.accession.replace("-", "") in src.url)


@dataclass(frozen=True)
class Source:
    form: str                 # e.g. "8-K", "10-Q", "4"
    filed: str                # ISO date
    accession: str            # SEC accession number or URL
    section: str = ""         # e.g. "Ex. 99.1", "Segment note"
    url: str = ""             # direct link to the exact document used


@dataclass
class Finding:
    kind: str                         # catalog key, see rules.CATALOG
    template: str                     # prose with {placeholders}, no digits
    values: dict                      # placeholder -> number or string
    sources: list                     # list[Source]
    confidence: str
    not_mean: str                     # "what this does not mean"
    materiality: float = 0.0          # 0..1, computed in code
    tier: Optional[str] = None        # "fixed-middle" for non-dollar findings
    formats: dict = field(default_factory=dict)  # placeholder -> fmt key
