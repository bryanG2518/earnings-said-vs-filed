import json, os, sys, unittest
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from ercheck import compute, insider, normalize, rules, validate, refuse, fetch
from ercheck.models import Finding, Source, FILED_REPORTED
from ercheck.cli import run


def load(name):
    with open(os.path.join(HERE, "fixtures", name)) as fh:
        return json.load(fh)

SRC = Source("10-Q", "2026-08-01", "0001045810-26-000075", "",
             "https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000075/nvda-20260726.htm")


class InsiderCodes(unittest.TestCase):
    """The Oracle trap: six executives 'disposed of' shares on the same day."""
    def test_oracle_tax_withholding_is_not_selling(self):
        s = insider.summarize(load("orcl_q1fy27.json")["insider_txns"])
        ins = s["insiders_by_class"]
        self.assertEqual(len(ins["administrative"]), 6)
        self.assertEqual(ins["planned_sale"], ["Michael Sicilia"])
        self.assertEqual(ins["discretionary_sale"], [])
        self.assertEqual(ins["purchase"], [])

    def test_admin_only_goes_to_context(self):
        f = rules.insider_findings(load("quiet_synthetic.json"))
        self.assertEqual(f[0].tier, "context")


class Guidance(unittest.TestCase):
    def test_broadcom_beat(self):
        f = rules.guidance_findings(load("avgo_q3fy26.json"))[0]
        self.assertEqual(f.values["direction"], "above")

    def test_lululemon_cut(self):
        fs = rules.guidance_findings(load("lulu_q2fy26.json"))
        self.assertEqual({f.values["direction"] for f in fs}, {"cut"})


class Computations(unittest.TestCase):
    def test_lulu_one_time_share(self):
        self.assertAlmostEqual(compute.one_time_share(2.92, 0.86), 0.2945, places=4)

    def test_nvda_divergence_fires(self):
        f = rules.divergence_findings(load("nvda_q2fy27.json"))
        self.assertEqual(len(f), 1)
        self.assertAlmostEqual(f[0].values["growth_a"], 0.1905, places=3)

    def test_adbe_flat_backlog_fires(self):
        self.assertEqual(len(rules.backlog_findings(load("adbe_q3fy26.json"))), 1)

    def test_materiality_none_when_unmeasurable(self):
        self.assertIsNone(compute.materiality())


class FiscalCalendar(unittest.TestCase):
    def test_labels(self):
        cases = [("2026-08-31", 5, "end", "Q1 FY27"),     # Oracle
                 ("2026-07-26", 1, "end", "Q2 FY27"),     # Nvidia
                 ("2026-08-28", 11, "end", "Q3 FY26"),    # Adobe
                 ("2026-08-02", 10, "end", "Q3 FY26"),    # Broadcom
                 ("2026-07-31", 1, "end", "Q2 FY27"),     # Salesforce
                 ("2026-08-02", 1, "start", "Q2 FY26")]   # Lululemon
        for end, m, naming, want in cases:
            self.assertEqual(normalize.fiscal_label(end, m, naming), want, end)

    def test_amendment_supersedes(self):
        best = normalize.latest_version([
            {"form": "10-Q", "filed": "2026-08-01", "accession": "A"},
            {"form": "10-Q/A", "filed": "2026-08-20", "accession": "B"}])
        self.assertEqual(best["accession"], "B")
        self.assertEqual(best["superseded"], ["A"])


class Validator(unittest.TestCase):
    def mk(self, template, values, not_mean="Routine disclosure.", sources=(SRC,)):
        return Finding("test", template, values, list(sources), FILED_REPORTED,
                       not_mean, formats={k: "usd" for k, v in values.items()
                                          if not isinstance(v, str)})

    def test_digit_in_template_blocked(self):
        self.assertTrue(validate.check_finding(self.mk("Revenue was $5 billion.", {})))

    def test_number_smuggled_in_text_value_blocked(self):
        f = self.mk("Driver: {d}.", {"d": "a $5 billion boost"})
        self.assertTrue(any("text value" in e for e in validate.check_finding(f)))

    def test_banned_language_blocked(self):
        f = self.mk("This suggests strength in {x}.", {"x": 1e9})
        self.assertTrue(any("suggests" in e for e in validate.check_finding(f)))

    def test_banned_in_not_mean_blocked(self):
        f = self.mk("Revenue was {x}.", {"x": 1e9}, not_mean="A bullish sign.")
        self.assertTrue(validate.check_finding(f))

    def test_missing_source_blocked(self):
        f = self.mk("Revenue was {x}.", {"x": 1e9}, sources=())
        self.assertTrue(any("citation" in e for e in validate.check_finding(f)))

    def test_form_names_allowed(self):
        self.assertEqual(validate.check_finding(
            self.mk("Disclosed in the 10-Q and a Form 4.", {})), [])

    def test_extraction_must_match_source_text(self):
        src = "outlook ... revenue guidance of approximately $29.4 billion;"
        self.assertTrue(validate.verify_extraction("$29.4 billion", src))
        self.assertFalse(validate.verify_extraction("$29.5 billion", src))


class EndToEnd(unittest.TestCase):
    FIXTURES = ["orcl_q1fy27.json", "avgo_q3fy26.json", "nvda_q2fy27.json",
                "adbe_q3fy26.json", "lulu_q2fy26.json", "quiet_synthetic.json"]

    def test_all_briefs_render_and_validate(self):
        for name in self.FIXTURES:
            for lang in ("en", "es"):
                brief, _ = run(load(name), lang)
                self.assertEqual(brief.count(validate.DISCLAIMER), 2, name)

    def test_quiet_quarter_has_no_core_findings(self):
        _, findings = run(load("quiet_synthetic.json"))
        self.assertEqual([f for f in findings if f.tier != "context"], [])

    def test_summary_ordered_by_materiality(self):
        _, fs = run(load("orcl_q1fy27.json"))
        m = [f.materiality for f in fs]
        self.assertEqual(m, sorted(m, reverse=True))


class Refusal(unittest.TestCase):
    def test_advice_requests(self):
        for t in ["Should I buy ORCL?", "is it a good investment",
                  "what's your price target", "buy or sell?",
                  "Is Adobe undervalued?", "good time to sell lulu",
                  "Would you invest in Oracle?", "Is ORCL a buy?",
                  "Should I be worried about my Lululemon shares?",
                  "Would you add to my position?", "is nvda going to go up?",
                  "Rate this stock 1-10", "what is ORCL worth",
                  "should i dump adobe", "what's the fair value of AVGO"]:
            self.assertTrue(refuse.is_advice_request(t), t)

    def test_normal_questions_pass(self):
        for t in ["What did Oracle file this quarter?",
                  "Explain the Form 4 codes", "Why did free cash flow go negative?",
                  "Why did revenue go up?", "Why was guidance cut?",
                  "Explain the code F transactions", "Is the backlog finding important?",
                  "What does a 10b5-1 plan mean?"]:
            self.assertFalse(refuse.is_advice_request(t), t)


class FetchGuards(unittest.TestCase):
    def test_identity_required(self):
        os.environ.pop("EDGAR_IDENTITY", None)
        with self.assertRaises(RuntimeError):
            fetch.EdgarSource()

    def test_budget_enforced(self):
        src = fetch.EdgarSource(identity="Test User test@example.com", budget=2)
        src._spend(); src._spend()
        with self.assertRaises(fetch.BudgetExceeded):
            src._spend()

    def test_concept_fallback_and_missing(self):
        facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
            {"end": "2026-06-30", "val": 100, "form": "10-Q"}]}}}}}
        self.assertEqual(fetch.resolve_concept(facts, "revenue", "2026-06-30"),
                         (100, "Revenues"))
        self.assertEqual(fetch.resolve_concept(facts, "rpo", "2026-06-30"),
                         (None, None))


class Provenance(unittest.TestCase):
    """Found by reading real output: press-sourced numbers were tagged Filed."""
    def test_press_sourced_findings_downgraded(self):
        _, fs = run(load("lulu_q2fy26.json"))
        self.assertTrue(all(f.confidence == "Secondary-Unverified" for f in fs))

    def test_edgar_sourced_findings_keep_filed_tag(self):
        _, fs = run(load("avgo_q3fy26.json"))
        self.assertEqual(fs[0].confidence, "Filed-Computed")

    def test_validator_rejects_forged_filed_tag(self):
        f = Finding("t", "Revenue was {x}.", {"x": 1e9},
                    [Source("8-K", "2026-09-01", "", "", "https://example.com/pr")],
                    "Filed-Reported", "Routine.", formats={"x": "usd"})
        self.assertTrue(any("sec.gov link" in e for e in validate.check_finding(f)))

    def test_citation_is_honest(self):
        brief, _ = run(load("lulu_q2fy26.json"))
        self.assertIn("NOT AN SEC FILING", brief)
        self.assertNotIn("accession https://", brief)


class SourceLinks(unittest.TestCase):
    """Every citation must be a working link to the exact document used."""
    FIXTURES = ["orcl_q1fy27.json", "avgo_q3fy26.json", "nvda_q2fy27.json",
                "adbe_q3fy26.json", "lulu_q2fy26.json", "tho_q4fy26.json"]

    def test_every_citation_is_a_link(self):
        import re
        for name in self.FIXTURES:
            brief, fs = run(load(name))
            for f in fs:
                for s in f.sources:
                    self.assertIn(f"]({s.url})", brief, name)
            log = brief.split("## Source log")[1].split("## Glossary")[0]
            for line in [l for l in log.splitlines() if l.startswith("- ")]:
                self.assertRegex(line, r"\]\(https?://", name)

    def test_filed_links_point_to_sec(self):
        brief, _ = run(load("tho_q4fy26.json"))
        self.assertIn("(https://www.sec.gov/Archives/edgar/data/730263/"
                      "000073026326000028/thoq4fy26-earningsrelease.htm)", brief)

    def test_missing_link_blocked(self):
        f = Finding("t", "Revenue was {x}.", {"x": 1e9},
                    [Source("10-Q", "2026-08-01", "0001045810-26-000075")],
                    "Filed-Reported", "Routine.", formats={"x": "usd"})
        self.assertTrue(any("no link" in e for e in validate.check_finding(f)))

    def test_sec_link_to_wrong_filing_blocked(self):
        wrong = Source("10-Q", "2026-08-01", "0001045810-26-000075", "",
                       "https://www.sec.gov/Archives/edgar/data/730263/"
                       "000073026326000028/thoq4fy26-earningsrelease.htm")
        f = Finding("t", "Revenue was {x}.", {"x": 1e9}, [wrong],
                    "Filed-Reported", "Routine.", formats={"x": "usd"})
        self.assertTrue(any("matching" in e for e in validate.check_finding(f)))

    def test_lookalike_domain_blocked(self):
        fake = Source("8-K", "2026-09-22", "0000730263-26-000028", "",
                      "https://sec.gov.evil.example/000073026326000028/x.htm")
        from ercheck.models import is_verified_sec_source
        self.assertFalse(is_verified_sec_source(fake))

    def test_index_url_helper(self):
        self.assertEqual(
            fetch.index_url("0000730263", "0000730263-26-000028"),
            "https://www.sec.gov/Archives/edgar/data/730263/"
            "000073026326000028/0000730263-26-000028-index.htm")


if __name__ == "__main__":
    unittest.main(verbosity=2)
