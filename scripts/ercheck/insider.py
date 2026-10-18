"""Form 4 transaction-code classification.

Codes follow the SEC Form 4 instructions. Only open-market purchases (P)
and sales (S) are market decisions; everything else is administrative.
"""
ADMINISTRATIVE = {
    "F": "tax withholding or exercise-price payment on vesting",
    "M": "option or RSU exercise/conversion",
    "A": "grant or award from the company",
    "G": "gift",
    "C": "conversion of a derivative security",
    "D": "disposition back to the issuer",
}
MARKET = {"P": "open-market purchase", "S": "open-market sale"}


def classify(txn: dict) -> str:
    """Return 'purchase', 'planned_sale', 'discretionary_sale', or 'administrative'."""
    code = txn.get("code", "").upper()
    if code == "P":
        return "purchase"
    if code == "S":
        return "planned_sale" if txn.get("plan_10b5_1") else "discretionary_sale"
    return "administrative"


def summarize(transactions: list) -> dict:
    """Group transactions by class. No thresholds; counts and values only."""
    out = {"purchase": [], "planned_sale": [], "discretionary_sale": [],
           "administrative": []}
    for t in transactions:
        out[classify(t)].append(t)
    def total(rows):
        return sum(r.get("shares", 0) * (r.get("price") or 0) for r in rows)
    return {
        "groups": out,
        "insiders_by_class": {k: sorted({r["insider"] for r in v})
                              for k, v in out.items()},
        "value_by_class": {k: total(v) for k, v in out.items()},
    }
