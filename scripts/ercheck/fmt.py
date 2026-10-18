"""Number formatting. Deterministic, used by render and validate."""

def usd(v):
    a, s = abs(v), "-" if v < 0 else ""
    if a >= 1e9:
        return f"{s}${a/1e9:,.2f} billion"
    if a >= 1e6:
        return f"{s}${a/1e6:,.1f} million"
    return f"{s}${a:,.0f}"

FORMATTERS = {
    "usd": usd,
    "eps": lambda v: f"${v:,.2f}",
    "pct": lambda v: f"{v*100:.1f}%",
    "pct_signed": lambda v: f"{v*100:+.1f}%",
    "int": lambda v: f"{int(v):,}",
    "text": str,
}


def fill(template, values, formats):
    rendered = {}
    for k, v in values.items():
        f = formats.get(k, "text")
        rendered[k] = FORMATTERS[f](v) if not isinstance(v, str) else v
    return template.format(**rendered), rendered
