"""EDGAR fetch layer, built on edgartools (MIT). Live use only.

Guards: a declared identity is required (SEC fair-access policy), the rate
is capped below the SEC's ceiling, and each run has a hard request budget.
The core pipeline never imports this module, so it runs and tests offline.
"""
import os

RATE_LIMIT_PER_SEC = 5          # conservative; SEC ceiling is 10
REQUEST_BUDGET = 25             # per run
OUT_OF_SCOPE_SIC = {            # v1 excludes banks, insurers, REITs
    "6020", "6021", "6022", "6029", "6035", "6036",   # banks, thrifts
    "6311", "6321", "6331", "6351", "6361", "6399",   # insurance
    "6798",                                           # REITs
}
OUT_OF_SCOPE_FORMS = {"20-F", "40-F", "6-K"}          # foreign private issuers

# XBRL concept fallbacks: companies tag the same line differently.
CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues", "SalesRevenueNet"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "eps_diluted": ["EarningsPerShareDiluted"],
    "ocf": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment",
              "PaymentsToAcquireProductiveAssets"],
    "rpo": ["RevenueRemainingPerformanceObligation"],
    "shares_diluted": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
}


def index_url(cik, accession):
    """Standard EDGAR filing-index link. Use the issuer's CIK (not the
    filing agent's, which is often the accession prefix)."""
    return ("https://www.sec.gov/Archives/edgar/data/"
            f"{int(cik)}/{accession.replace('-', '')}/{accession}-index.htm")


class BudgetExceeded(RuntimeError):
    pass


class ScopeError(RuntimeError):
    pass


def resolve_concept(facts: dict, field: str, period_end: str):
    """Return (value, concept) from a companyfacts-style dict, or
    (None, None) if no mapped concept has a value for that period.
    Missing values are reported as 'not computed', never estimated."""
    usgaap = facts.get("facts", {}).get("us-gaap", {})
    for concept in CONCEPTS[field]:
        units = usgaap.get(concept, {}).get("units", {})
        for rows in units.values():
            for r in rows:
                if r.get("end") == period_end and r.get("form") in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
                    return r["val"], concept
    return None, None


class EdgarSource:
    def __init__(self, identity=None, budget=REQUEST_BUDGET):
        self.identity = identity or os.environ.get("EDGAR_IDENTITY")
        if not self.identity or "@" not in self.identity:
            raise RuntimeError(
                "Set EDGAR_IDENTITY to 'Your Name your@email.com'. The SEC "
                "requires automated clients to declare who they are.")
        self.budget = budget
        self.used = 0
        self._edgar = None

    def _spend(self, n=1):
        if self.used + n > self.budget:
            raise BudgetExceeded(f"request budget of {self.budget} reached")
        self.used += n

    def _lib(self):
        if self._edgar is None:
            import edgar                                   # pip install edgartools
            from edgar import httpclient
            edgar.set_identity(self.identity)
            httpclient.update_rate_limiter(requests_per_second=RATE_LIMIT_PER_SEC)
            self._edgar = edgar
        return self._edgar

    def company(self, ticker):
        self._spend()
        c = self._lib().Company(ticker)
        sic = str(getattr(c, "sic", "") or "")
        if sic in OUT_OF_SCOPE_SIC:
            raise ScopeError(f"{ticker}: SIC {sic} is out of scope for v1")
        return c

    def facts(self, company):
        self._spend()
        return company.get_facts()

    def filings(self, company, form, limit=4):
        self._spend()
        if form in OUT_OF_SCOPE_FORMS:
            raise ScopeError(f"{form} filers are out of scope for v1")
        return company.get_filings(form=form).head(limit)

    def form4_window(self, company, start, end, max_filings=12):
        self._spend()
        fl = company.get_filings(form="4").filter(date=f"{start}:{end}")
        out = []
        for f in fl.head(max_filings):
            self._spend()
            out.append(f.obj())
        return out
