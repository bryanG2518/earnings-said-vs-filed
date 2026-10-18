# Earnings Said vs. Filed

A Claude skill that compares what a company said in its earnings release with
what it filed with the SEC, then writes a one-page brief. Code computes every
number. Every finding links to the filing it came from.

> Informational only. Not investment advice. Never recommends buying, selling,
> or holding anything.

![Terminal demo: the tool prints a cited brief for Oracle's quarter, ending on an insider-activity finding that explains six "disposals" were tax withholding](docs/demo.gif)

## Try it without installing anything

Six real quarters ship with the repo as fixtures, so you can read the output
before deciding whether you want the skill. No API key and no network needed:

```bash
git clone https://github.com/bryanG2518/earnings-said-vs-filed.git
cd earnings-said-vs-filed/scripts
python -m ercheck.cli --input ../tests/fixtures/orcl_q1fy27.json
```

That prints the Oracle brief from the demo above. Spanish works too:

```bash
python -m ercheck.cli --input ../tests/fixtures/lulu_q2fy26.json --lang es
```

The brief generator uses only the Python standard library. `edgartools` is
needed when you want to pull a quarter from EDGAR yourself, not to run the
fixtures.

## What it catches (from real September 2026 filings)

- **Oracle:** six executives "disposed of" shares on the same day. All six
  were tax withholding on vesting awards (Form 4 code F), not sales. The one
  actual sale was under a pre-arranged plan. A separate 8-K disclosed a
  trading-plan termination that never appears on a Form 4.
- **NVIDIA:** operating income and net income grew at very different rates
  quarter over quarter, and the 10-Q notes a segment recast.
- **Adobe:** backlog stayed level across three quarters of rising revenue.
- **Broadcom:** actual revenue versus the prior quarter's guidance, from two
  8-Ks alone.
- **Lululemon:** a one-time item's share of reported EPS, and a guidance cut.

## How to use it

### Install the skill

The skill is the whole folder. `SKILL.md` tells Claude when to run and how to
drive the pipeline in `scripts/`.

For Claude Code, put the folder where Claude looks for skills, so that
`SKILL.md` lands at `~/.claude/skills/earnings-said-vs-filed/SKILL.md`:

```bash
git clone https://github.com/bryanG2518/earnings-said-vs-filed.git
mkdir -p ~/.claude/skills
cp -r earnings-said-vs-filed ~/.claude/skills/
```

For the Claude app, zip the folder with `SKILL.md` at the top level inside it,
then upload the zip as a custom skill in settings.

### Tell the SEC who you are

The SEC throttles automated clients that don't identify themselves, so set
this before the first live fetch. Use your own name and a working email:

```bash
pip install edgartools
export EDGAR_IDENTITY="Your Name you@email.com"
```

Add that line to your shell profile and you won't have to think about it again.

### Ask in plain English

Naming the skill is optional. Each of these starts it:

- "What really happened in Oracle's latest earnings?"
- "Did NVIDIA's insiders sell after the quarter, or was it tax withholding?"
- "Compare what Adobe said about guidance with what it filed."
- "Were there any one-time items in Lululemon's EPS?"

Ask for Spanish and you get a Spanish brief.

### What comes back

A one-page brief in four parts. A "what changed" summary. Then the findings,
each one written as a plain sentence with a link to the exact SEC document
behind it and a line explaining what the finding does *not* prove. Then a
source log, and a glossary for terms like 10b5-1 and Form 4 code F.

Follow-up questions work. Ask why a finding fired and it explains from the
filing, not from memory.

### What it refuses to do

It won't say whether to buy, sell, or hold, won't set price targets, and won't
tell you whether a stock is cheap. Ask anyway and it declines, then offers to
walk through a finding instead. When a number can't be traced to a filing, the
brief prints "not computed" rather than guessing at it.

## How it stays honest

- **Numbers never come from the model.** The prose is written with
  placeholders and code fills them in. The validator blocks any digit a model
  typed directly.
- **Every source is a link.** Each citation points at the exact document used.
  A "Filed" tag requires a sec.gov link matching the accession number, and
  anything else gets labeled Secondary-Unverified and marked as not a filing.
- **Fail closed:** banned language, a missing citation, or a number that cannot
  be traced will block the brief instead of degrading it.
- **Insider codes rather than "buy" and "sell":** Form 4 transactions are
  classified by their actual code, with no arbitrary cluster threshold.

## Evaluation status

Thresholds were set before any results existed (`eval/thresholds.json`):
100% numeric accuracy, per-finding precision at or above 90% and recall at or
above 80% on a held-out set, and a false-alarm rate under 10% on quiet
quarters.

Where it stands: 5 real development quarters plus 1 synthetic control, labeled
by the author of the rules. They pass, which makes it a smoke test rather than
evidence. The held-out test set of 15 quarters and the 20 quiet controls
aren't built yet. Results will be published here whether they pass or fail.

Run the suite yourself:

```bash
cd tests && python -m unittest test_core -v
python eval/run_eval.py --split dev
```

## Scope (v1)

US domestic 10-Q and 10-K filers. Not banks, insurers, REITs, or foreign
private issuers. The fetch layer respects SEC fair-access rules with a
declared identity, 5 requests per second, and a hard budget of 25 requests
per run.

## Known limitations

- Guidance and one-time items live in press-release exhibits rather than XBRL,
  so they depend on exact-text extraction. Two of the five fixtures still
  carry press-sourced numbers, labeled Secondary-Unverified until they're
  checked against EDGAR.
- Spanish output translates the labels and glossary, not the finding
  sentences.
- The live EDGAR path has not been exercised from the build environment, which
  has no network access.

## Contributing

Bug reports and new quarters are both useful. A quarter the tool gets wrong is
more useful than one it gets right: open an issue with the ticker, the period,
and the filing link, and say what it should have caught.

## License

MIT, with an explicit no-advice notice. See `LICENSE`.
