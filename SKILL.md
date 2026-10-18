---
name: "earnings-said-vs-filed"
description: Compare what a public company said in its earnings release with what it actually filed with the SEC, and produce a cited one-page brief. Use this whenever the user asks about a company's latest earnings, guidance changes, one-time items, insider buying or selling, Form 4s, 10b5-1 plans, or "what really happened" in a quarter, even if they don't name this skill. Works from SEC EDGAR filings. Never gives buy, sell, or hold recommendations.
---

# Earnings Said vs. Filed

Produces a one-page brief on one company event (an earnings release or a
user-specified 8-K event), built from SEC EDGAR filings. Every number is
computed by code in `scripts/ercheck/`, and every finding cites its filing.

## Non-negotiable rules

1. **No recommendations, ever.** Before anything else, and on every
   follow-up, run `refuse.is_advice_request(user_text)`. If true, reply with
   `refuse.RESPONSE` and offer to explain a finding instead. This covers
   buy/sell/hold, price targets, "is it undervalued," and "what would you do."
2. **You never type a number.** Numbers come from XBRL via
   `fetch.resolve_concept`, or from filing text via
   `validate.verify_extraction` (the exact string must appear in the fetched
   filing). If a value can't be obtained either way, leave it out; the brief
   shows it as not computed. Never estimate.
3. **If validation blocks the brief, report the errors.** Do not edit numbers,
   tags, or wording to force it through.
4. **Neutral language in conversation too.** Don't use the banned terms in
   `validate.BANNED` when discussing a brief.

## Workflow

1. **Refusal check** (rule 1).
2. **Scope check.** v1 covers US domestic 10-Q/10-K filers. Out of scope:
   banks, insurers, REITs, foreign private issuers (20-F/6-K). Say so plainly
   if the ticker is out of scope.
3. **Fetch.** Requires network access and `pip install edgartools`. Set
   `EDGAR_IDENTITY="Name email@domain"` (SEC fair-access requirement).
   Use `fetch.EdgarSource`; it caps rate at 5 requests/second and 25 requests
   per run. If the environment has no network, tell the user to run the skill
   locally (see README) rather than substituting web search results.
4. **Build the quarter JSON** following `references/input-schema.md`.
   Resolve the fiscal label with `normalize.fiscal_label` (check whether the
   company names fiscal years by start or end year). Use
   `normalize.latest_version` so amendments win. For every source, record
   the SEC accession number **and the URL of the exact document you read**
   (the `.htm` or `.xml` file, not a search page). If you only have the
   issuer's CIK and the accession, use `fetch.index_url(cik, accession)`.
   A *Filed* tag requires a sec.gov link containing that accession; anything
   else is automatically tagged Secondary-Unverified. Never construct a link
   you did not open.
5. **Run:** `cd scripts && python -m ercheck.cli --input quarter.json
   [--lang es] --out brief.md`
6. **Present the brief** as produced, with its links intact. Don't
   paraphrase numbers from it, and don't strip or shorten the source links.

## Answering follow-up questions

Explain findings using only what the brief and its cited filings contain.
Point to the "What this does not mean" line when a user reads a finding as a
verdict. Transcripts are used only if the user supplies one; press coverage is
context only and never confirms a number.

## Known limits (tell the user when relevant)

- Spanish mode translates labels and glossary; finding sentences stay in English.
- Guidance and one-time items live in press-release exhibits, not XBRL, so
  they depend on exact-text extraction from the 8-K exhibit.
- Evaluation results so far are a small development set (see `eval/`).

## Files

- `scripts/ercheck/` — pipeline (compute, insider, normalize, rules, validate, render, refuse, fetch, cli)
- `references/input-schema.md` — quarter JSON format
- `references/stack.md` — dependencies and why each was chosen or rejected
- `eval/` — harness, labels, pre-registered thresholds
- `tests/` — unit tests and fixtures from real September 2026 filings
