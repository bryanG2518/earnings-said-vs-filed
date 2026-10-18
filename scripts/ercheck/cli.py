"""Command line entry point.

  python -m ercheck.cli --input quarter.json [--lang es] [--out brief.md]

The input is a normalized quarter (see references/input-schema.md). In the
skill workflow, Claude builds it from EDGAR via fetch.py; every value that
came from filing text must pass validate.verify_extraction first.
"""
import argparse, json, sys
from .rules import detect
from .render import render
from .validate import ValidationError


def run(q, lang="en"):
    findings = detect(q)
    return render(q, findings, lang=lang), findings


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--lang", default="en", choices=["en", "es"])
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    with open(a.input) as fh:
        q = json.load(fh)
    try:
        brief, _ = run(q, a.lang)
    except ValidationError as e:
        print("BRIEF BLOCKED by validation:", file=sys.stderr)
        for err in e.errors:
            print("  -", err, file=sys.stderr)
        return 2
    if a.out:
        open(a.out, "w").write(brief)
    else:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
