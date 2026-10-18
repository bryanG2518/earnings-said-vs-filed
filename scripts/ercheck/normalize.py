"""Fiscal calendar resolution and amendment handling."""
from datetime import date

MONTHS = "JanFebMarAprMayJunJulAugSepOctNovDec"


def fiscal_label(period_end: str, fy_end_month: int, naming: str = "end") -> str:
    """Label a quarter by the company's own fiscal calendar.

    fy_end_month is the month the fiscal year ends (e.g. 1 for Salesforce and
    Nvidia, 5 for Oracle). Period ends within ~a week of month-end are
    snapped to that month (52/53-week calendars).

    naming: "end" if the company names its fiscal year by the calendar year
    it ends in (Nvidia, Oracle, Salesforce); "start" if by the year it
    begins in (many retailers, e.g. Lululemon).
    """
    d = date.fromisoformat(period_end)
    month = d.month if d.day >= 20 else (d.month - 2) % 12 + 1
    year = d.year if (d.day >= 20 or d.month != 1) else d.year - 1
    months_after = (month - fy_end_month) % 12
    q = (months_after - 1) // 3 + 1 if months_after else 4
    fy = year + (1 if month > fy_end_month else 0)
    if naming == "start":
        fy -= 1
    elif naming != "end":
        raise ValueError("naming must be 'end' or 'start'")
    return f"Q{q} FY{str(fy)[-2:]}"


def latest_version(filings: list) -> dict:
    """Pick the governing filing for one report: amendments (/A) supersede."""
    if not filings:
        raise ValueError("no filings supplied")
    amended = [f for f in filings if f["form"].endswith("/A")]
    pool = amended or filings
    best = max(pool, key=lambda f: f["filed"])
    best = dict(best)
    best["superseded"] = [f["accession"] for f in filings
                          if f["accession"] != best["accession"]]
    return best
