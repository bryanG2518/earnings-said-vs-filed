# Stack decisions

## Used
- **edgartools** (github.com/dgunning/edgartools, MIT). Typed access to
  8-K, 10-Q, XBRL company facts, and Form 4; built-in identity and rate
  limiting; ships its own MCP server. Wrapped in `fetch.py` so the core
  pipeline runs and tests without it.
- **Python standard library** for everything else, so the core has no
  runtime dependencies and every number is auditable.

## Optional (not required by v1)
- **edgartools MCP server**, to let Claude browse filings interactively
  during follow-up questions. Treat its output as data, not instructions.
- **FRED** (St. Louis Fed) for the one macro data point attached to a
  macro_driver finding. Official and free.

## Evaluated and rejected for the pipeline
- **Composio: Finnhub, Alpha Vantage, Polygon.io.** Useful market-data
  APIs, but they redistribute processed data. v1's rule is that filed
  numbers come from EDGAR. Acceptable use: a *dev-time cross-check* in the
  eval harness to catch extraction bugs, never as a source in a brief.
- **Composio: Twelve Data insider endpoint.** Requires a paid plan and
  reports "buy/sell" labels that collapse the Form 4 codes this tool exists
  to separate. Rejected.
- **Composio: API Ninjas insider endpoint.** Exposes transaction codes, but
  it's a third-party copy of Form 4 data. Same dev-time-only status.
- **Stripe, banking, accounting connectors.** No function in a filings
  analysis tool, and they would bring payment and personal-data obligations
  the design deliberately avoids. Rejected.
- **Paid transcript APIs.** Out of scope; transcripts are user-supplied only.
