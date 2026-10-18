"""Finding catalog. Each detector turns normalized data into Findings.

Templates contain no digits: every number is a {placeholder} filled by code.
"""
from . import compute, insider
from .models import (Finding, Source, FILED_REPORTED, FILED_COMPUTED,
                     FILED_TAGS, SECONDARY, is_verified_sec_source)

CATALOG = [
    "guidance_delta", "one_time_items", "cash_vs_earnings",
    "capital_action", "income_divergence", "backlog_vs_revenue",
    "footnote_comparability", "insider_activity", "plan_event",
    "leadership_change", "macro_driver",
]


def _src(d):
    return Source(**d)


def guidance_findings(q):
    out = []
    for g in q.get("guidance", []):
        delta = compute.guidance_delta(g["prior_low"], g.get("prior_high"),
                                       g["new_low"], g.get("new_high"))
        vals = {"metric": g["metric"], "direction": delta["direction"],
                "prior_low": g["prior_low"], "new_low": g["new_low"]}
        fmts = {"prior_low": g["fmt"], "new_low": g["fmt"]}
        if g.get("prior_high") is not None:
            prior = "a prior range of {prior_low} to {prior_high}"
            vals["prior_high"] = g["prior_high"]; fmts["prior_high"] = g["fmt"]
        else:
            prior = "prior guidance of approximately {prior_low}"
        if g.get("new_high") is not None:
            new = "The new range is {new_low} to {new_high}"
            vals["new_high"] = g["new_high"]; fmts["new_high"] = g["fmt"]
            tmpl = f"{{metric}} guidance was {{direction}}. {new}, versus {prior}."
        else:
            tmpl = f"Reported {{metric}} of {{new_low}} came in {{direction}} {prior}."
        out.append(Finding(
            kind="guidance_delta", template=tmpl, values=vals, formats=fmts,
            sources=[_src(g["prior_source"]), _src(g["source"])],
            confidence=FILED_COMPUTED,
            not_mean="Guidance is the company's own estimate; a change in "
                     "guidance describes management's expectations, not an "
                     "outcome.",
            materiality=compute.materiality(
                guidance_distance=delta["distance"]) or 0.0))
    return out


def one_time_findings(q):
    out = []
    eps = q.get("eps_gaap", {}).get("value")
    for item in q.get("one_time_items", []):
        share = compute.one_time_share(eps, item["per_share"]) if eps else None
        vals = {"desc": item["desc"], "per_share": item["per_share"],
                "eps": eps}
        tmpl = ("Reported GAAP EPS of {eps} includes {per_share} per share "
                "from {desc}, an item the company identifies as non-recurring.")
        if share is not None:
            vals["share"] = share
            tmpl += " That is {share} of reported EPS."
        out.append(Finding(
            kind="one_time_items", template=tmpl, values=vals,
            formats={"eps": "eps", "per_share": "eps", "share": "pct"},
            sources=[_src(item["source"])], confidence=FILED_COMPUTED,
            not_mean="A one-time item can be legitimate and fully disclosed; "
                     "excluding it shows the underlying trend, not an error.",
            materiality=compute.materiality(eps_impact=item["per_share"],
                                            eps=eps) or 0.0))
    return out


def cash_findings(q):
    cf = q.get("cash_flow")
    if not cf or cf.get("ocf") is None or cf.get("fcf") is None:
        return []
    if not (cf["ocf"] > 0 and cf["fcf"] < 0):
        return []
    return [Finding(
        kind="cash_vs_earnings",
        template=("Operating cash flow was {ocf} while free cash flow was "
                  "{fcf}, meaning capital spending exceeded operating cash "
                  "generation this quarter."),
        values={"ocf": cf["ocf"], "fcf": cf["fcf"]},
        formats={"ocf": "usd", "fcf": "usd"},
        sources=[_src(cf["source"])], confidence=FILED_REPORTED,
        not_mean="Negative free cash flow during a planned investment "
                 "period is common and is not by itself a sign of distress.",
        materiality=compute.materiality(dollar_impact=cf["fcf"],
                                        revenue=q["revenue"]["value"]) or 0.0)]


def capital_findings(q):
    out = []
    for c in q.get("capital_actions", []):
        verb = {"equity_sale": "sold common stock totaling",
                "buyback": "repurchased shares totaling"}[c["type"]]
        out.append(Finding(
            kind="capital_action",
            template=f"During the quarter the company {verb} {{dollars}}.",
            values={"dollars": c["dollars"]}, formats={"dollars": "usd"},
            sources=[_src(c["source"])], confidence=FILED_REPORTED,
            not_mean=("Issuing stock increases share count; whether that is "
                      "offset by what the capital funds is outside the scope "
                      "of this brief." if c["type"] == "equity_sale" else
                      "Repurchases reduce share count; they are a capital "
                      "allocation choice, not a statement about value."),
            materiality=compute.materiality(dollar_impact=c["dollars"],
                                            revenue=q["revenue"]["value"]) or 0.0))
    return out


def divergence_findings(q, min_gap=0.10):
    out = []
    for d in q.get("divergences", []):
        r = compute.divergence(d["a_now"], d["a_prev"], d["b_now"], d["b_prev"])
        if r is None or abs(r["gap"]) < min_gap:
            continue
        out.append(Finding(
            kind="income_divergence",
            template=("{a_name} changed {growth_a} compared with {basis}, "
                      "while {b_name} changed {growth_b}."),
            values={"a_name": d["a_name"], "b_name": d["b_name"],
                    "basis": d.get("basis", "the prior quarter"),
                    "growth_a": r["growth_a"], "growth_b": r["growth_b"]},
            formats={"growth_a": "pct_signed", "growth_b": "pct_signed"},
            sources=[_src(d["source"])], confidence=FILED_COMPUTED,
            not_mean="A gap between these lines often comes from items "
                     "outside operations in either period; check both "
                     "periods before drawing conclusions.",
            materiality=min(1.0, abs(r["gap"]))))
    return out


def backlog_findings(q, flat_band=0.02):
    b = q.get("backlog")
    if not b:
        return []
    rpo, rev = b["rpo_series"], b["revenue_series"]
    rpo_chg = compute.pct_change(rpo[-1], rpo[0])
    rev_chg = compute.pct_change(rev[-1], rev[0])
    if rpo_chg is None or rev_chg is None:
        return []
    if not (abs(rpo_chg) <= flat_band and rev_chg > flat_band):
        return []
    return [Finding(
        kind="backlog_vs_revenue",
        template=("Across the last {n} quarters, revenue changed {rev_chg} "
                  "while remaining performance obligations changed {rpo_chg}, "
                  "from {rpo_first} to {rpo_last}."),
        values={"n": len(rpo), "rev_chg": rev_chg, "rpo_chg": rpo_chg,
                "rpo_first": rpo[0], "rpo_last": rpo[-1]},
        formats={"n": "int", "rev_chg": "pct_signed", "rpo_chg": "pct_signed",
                 "rpo_first": "usd", "rpo_last": "usd"},
        sources=[_src(s) for s in b["sources"]], confidence=FILED_COMPUTED,
        not_mean="Backlog can stay level for timing reasons such as contract "
                 "renewal cycles; it is one input, not a forecast.",
        materiality=min(1.0, abs(rev_chg - rpo_chg)))]


def footnote_findings(q):
    labels = {"segment_recast": "changed how it presents segment revenue "
                                "and restated prior periods",
              "reclassification": "moved a customer or item between segments",
              "impairment": "recorded an impairment charge"}
    return [Finding(
        kind="footnote_comparability",
        template=f"The filing states the company {labels[f['type']]}. "
                 "Segment comparisons across periods should use the "
                 "restated figures.",
        values={}, sources=[_src(f["source"])], confidence=FILED_REPORTED,
        not_mean="Presentation changes are routine disclosures and do not "
                 "change total reported results.",
        materiality=compute.FIXED_MIDDLE, tier="fixed-middle")
        for f in q.get("footnotes", [])]


def insider_findings(q):
    txns = q.get("insider_txns", [])
    if not txns:
        return []
    s = insider.summarize(txns)
    ins = s["insiders_by_class"]
    vals = {"n_admin": len(ins["administrative"]),
            "n_planned": len(ins["planned_sale"]),
            "n_disc": len(ins["discretionary_sale"]),
            "n_buy": len(ins["purchase"]),
            "v_planned": s["value_by_class"]["planned_sale"],
            "v_disc": s["value_by_class"]["discretionary_sale"],
            "v_buy": s["value_by_class"]["purchase"]}
    tmpl = ("Insiders in the review window, by transaction type: "
            "administrative only, such as tax withholding on vesting awards: "
            "{n_admin}; sales under a pre-arranged trading plan: {n_planned} "
            "(total {v_planned}); sales outside a plan: {n_disc} (total "
            "{v_disc}); open-market purchases: {n_buy} (total {v_buy}).")
    fm = {k: "int" for k in ("n_admin", "n_planned", "n_disc", "n_buy")}
    fm.update({k: "usd" for k in ("v_planned", "v_disc", "v_buy")})
    srcs = []
    for t in txns:
        src = _src(t["source"])
        if src not in srcs:
            srcs.append(src)
    market = vals["n_planned"] + vals["n_disc"] + vals["n_buy"]
    return [Finding(
        kind="insider_activity", template=tmpl, values=vals, formats=fm,
        sources=srcs, confidence=FILED_REPORTED,
        not_mean="Tax-withholding transactions happen automatically when "
                 "awards vest, and plan sales are scheduled in advance; "
                 "neither reflects a new decision about the stock.",
        materiality=compute.FIXED_MIDDLE if market else 0.0,
        tier="fixed-middle" if market else "context")]


def plan_event_findings(q):
    return [Finding(
        kind="plan_event",
        template="{insider} {event} a pre-arranged trading plan "
                 "for company stock.",
        values={"insider": e["insider"], "event": e["event"]},
        sources=[_src(e["source"])], confidence=FILED_REPORTED,
        not_mean="Plan adoptions and terminations have many personal "
                 "reasons, including tax and estate planning.",
        materiality=compute.FIXED_MIDDLE, tier="fixed-middle")
        for e in q.get("plan_events", [])]


def leadership_findings(q):
    return [Finding(
        kind="leadership_change",
        template="Leadership change disclosed: {change}.",
        values={"change": e["change"]}, sources=[_src(e["source"])],
        confidence=FILED_REPORTED,
        not_mean="Leadership transitions are often planned well in advance.",
        materiality=compute.FIXED_MIDDLE, tier="fixed-middle")
        for e in q.get("leadership", [])]


def macro_findings(q):
    return [Finding(
        kind="macro_driver",
        template="The filing names {driver} as a factor in results.",
        values={"driver": m["driver"]}, sources=[_src(m["source"])],
        confidence=FILED_REPORTED,
        not_mean="This notes the company's own attribution; it does not "
                 "measure how much of the result the factor explains.",
        materiality=0.0, tier="context")
        for m in q.get("macro_mentions", [])]


DETECTORS = [guidance_findings, one_time_findings, cash_findings,
             capital_findings, divergence_findings, backlog_findings,
             footnote_findings, insider_findings, plan_event_findings,
             leadership_findings, macro_findings]


def apply_provenance(findings):
    """A Filed-* tag requires every source to be an SEC accession number.
    Anything else is downgraded, never silently passed as filed data."""
    for f in findings:
        if f.confidence in FILED_TAGS and not all(
                is_verified_sec_source(s) for s in f.sources):
            f.confidence = SECONDARY
    return findings


def detect(q):
    findings = []
    for fn in DETECTORS:
        findings.extend(fn(q))
    apply_provenance(findings)
    return sorted(findings, key=lambda f: f.materiality, reverse=True)
