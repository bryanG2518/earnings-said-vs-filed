# Quarter input schema

All money in US dollars (not millions). All dates ISO `YYYY-MM-DD`.
Every `source` is `{form, filed, accession, section, url}`.
- `accession`: the SEC accession number (`0001234567-26-000123`); leave empty for non-SEC sources.
- `url`: **required.** Direct link to the exact document used, e.g.
  `https://www.sec.gov/Archives/edgar/data/730263/000073026326000028/thoq4fy26-earningsrelease.htm`.
  Note the folder uses the *issuer's* CIK; the accession prefix is sometimes a
  filing agent's (Oracle's plan-termination 8-K was filed by agent 0001193125).

A *Filed* confidence tag requires a sec.gov URL containing the accession
digits. Non-SEC sources are allowed but are tagged **Secondary-Unverified**
and cited as "NOT AN SEC FILING" with their link.

| Key | Shape | Feeds finding |
|---|---|---|
| company, ticker, fiscal_label | strings | header |
| period_end, fy_end_month, fy_naming | date, 1-12, "end"/"start" | fiscal label |
| revenue | `{value}` | materiality denominator |
| eps_gaap | `{value}` | one-time share of EPS |
| guidance[] | `{metric, fmt, prior_low, prior_high?, new_low, new_high?, prior_source, source}` | guidance_delta |
| one_time_items[] | `{desc, per_share, source}` | one_time_items |
| cash_flow | `{ocf, fcf, source}` | cash_vs_earnings |
| capital_actions[] | `{type: equity_sale|buyback, dollars, source}` | capital_action |
| divergences[] | `{a_name, a_now, a_prev, b_name, b_now, b_prev, source}` | income_divergence (fires at a gap of 10 points or more) |
| backlog | `{rpo_series[], revenue_series[], sources[]}` | backlog_vs_revenue (RPO within ±2%, revenue up more than 2%) |
| footnotes[] | `{type: segment_recast|reclassification|impairment, source}` | footnote_comparability |
| insider_txns[] | `{insider, code, shares, price, plan_10b5_1?, source}` | insider_activity |
| plan_events[] | `{insider, event: adopted|terminated, source}` | plan_event |
| leadership[] | `{change, source}` | leadership_change |
| macro_mentions[] | `{driver, source}` | macro_driver (context only) |

Text fields (`desc`, `metric`, `change`, `driver`, names) may not contain
digits; the validator blocks them so numbers can't bypass computation.
