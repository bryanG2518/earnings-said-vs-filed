"""Fail-closed validation. Any error blocks the brief."""
import re
from string import Formatter
from .models import CONFIDENCE_TAGS, FILED_TAGS, is_link, is_verified_sec_source
from . import fmt

BANNED = ["buy", "sell", "hold", "suggests", "suggest", "signals", "signal",
          "bullish", "bearish", "undervalued", "overvalued", "opportunity",
          "red flag", "should invest", "price target", "outperform",
          "underperform", "strong buy", "we recommend", "recommendation"]
# Form names and similar tokens that legitimately contain digits.
ALLOWED_DIGIT_TOKENS = ["10-Q/A", "10-K/A", "8-K/A", "10-Q", "10-K", "8-K",
                        "Form 4", "10b5-1", "Ex. 99.1", "99.1"]
DISCLAIMER = ("Informational summary of public SEC filings. Not investment "
              "advice. This brief does not recommend any action.")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def _placeholders(template):
    return {name for _, name, _, _ in Formatter().parse(template) if name}


def _strip_allowed(text):
    for tok in ALLOWED_DIGIT_TOKENS:
        text = text.replace(tok, "")
    return text


def check_template(template, values):
    """Templates (the only text a model may write) must contain no digits."""
    errs = []
    missing = _placeholders(template) - set(values)
    if missing:
        errs.append(f"placeholders without values: {sorted(missing)}")
    body = re.sub(r"\{[^}]*\}", "", template)
    if re.search(r"\d", _strip_allowed(body)):
        errs.append(f"digit typed into template: {template!r}")
    # Text values are model-writable too; they may not smuggle numbers.
    for k, v in values.items():
        if isinstance(v, str) and re.search(r"\d", _strip_allowed(v)):
            errs.append(f"digit inside text value {k!r}: {v!r}")
    return errs


def lint_language(text):
    errs = []
    low = text.lower()
    for w in BANNED:
        if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low):
            errs.append(f"banned term: {w!r}")
    return errs


def numbers_in(text):
    text = _strip_allowed(text)
    return re.findall(r"-?\$?\d[\d,]*\.?\d*%?(?: (?:billion|million))?", text)


def check_numbers(rendered_text, rendered_values):
    """Every number in the output must come from a formatted computed value."""
    allowed = set()
    for v in rendered_values.values():
        allowed.update(numbers_in(str(v)))
    return [f"number not traceable to computed values: {n}"
            for n in numbers_in(rendered_text) if n not in allowed]


def check_finding(f):
    errs = check_template(f.template, f.values)
    if errs:
        text = f.template            # can't fill safely; lint the raw text
    else:
        text, rv = fmt.fill(f.template, f.values, f.formats)
        errs += check_numbers(text, rv)
    errs += lint_language(text + " " + f.not_mean)
    if not f.sources:
        errs.append(f"{f.kind}: missing source citation")
    for s in f.sources:
        if not is_link(s.url):
            errs.append(f"{f.kind}: source has no link: {s.accession or s.section}")
    if f.confidence in FILED_TAGS and not all(
            is_verified_sec_source(s) for s in f.sources):
        errs.append(f"{f.kind}: '{f.confidence}' tag requires a sec.gov link "
                    "matching its SEC accession number")
    if f.confidence not in CONFIDENCE_TAGS:
        errs.append(f"{f.kind}: unknown confidence tag {f.confidence!r}")
    if not f.not_mean.strip():
        errs.append(f"{f.kind}: missing 'what this does not mean' line")
    return [f"{f.kind}: {e}" if not e.startswith(f.kind) else e for e in errs]


def verify_extraction(value_text, source_text):
    """A value a model extracted from filing text must appear verbatim in it.

    Used for press-release items (guidance, non-GAAP reconciliations) that
    are not in XBRL. Normalizes whitespace only; no fuzzy matching.
    """
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    return norm(value_text) in norm(source_text)


def validate_brief(findings, brief_text):
    errs = []
    for f in findings:
        errs += check_finding(f)
    if brief_text.count(DISCLAIMER) < 2:
        errs.append("disclaimer must appear at top and bottom")
    if errs:
        raise ValidationError(errs)
    return True
