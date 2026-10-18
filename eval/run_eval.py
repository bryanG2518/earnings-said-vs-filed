"""Evaluation harness: per-kind precision/recall, false alarms, thresholds.

  python eval/run_eval.py --split dev
  python eval/run_eval.py --split test     # run ONCE, after rules are frozen
"""
import argparse, collections, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from ercheck.cli import run
from ercheck import insider

FIX = os.path.join(HERE, "..", "tests", "fixtures")


def core_counts(findings):
    return collections.Counter(f.kind for f in findings if f.tier != "context")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    a = ap.parse_args()
    labels = json.load(open(os.path.join(HERE, "labels.json")))
    th = json.load(open(os.path.join(HERE, "thresholds.json")))
    cases = labels[a.split]
    if not cases:
        print(f"No labeled cases in '{a.split}' yet."); return 1
    tp, fp, fn = collections.Counter(), collections.Counter(), collections.Counter()
    blocked, violations = 0, []
    for name, lab in cases.items():
        q = json.load(open(os.path.join(FIX, name)))
        try:
            _, fs = run(q)
        except Exception as e:                 # validation block counts as miss
            blocked += 1; fn.update(lab["expect"]); continue
        got, want = core_counts(fs), collections.Counter(lab["expect"])
        for k in set(got) | set(want):
            tp[k] += min(got[k], want[k])
            fp[k] += max(0, got[k] - want[k])
            fn[k] += max(0, want[k] - got[k])
        if "discretionary_sale" in lab.get("must_not", []):
            s = insider.summarize(q.get("insider_txns", []))
            if s["groups"]["discretionary_sale"]:
                violations.append(f"{name}: discretionary sale reported")
    quiet_alarms = 0
    for name in labels["quiet"]:
        _, fs = run(json.load(open(os.path.join(FIX, name))))
        quiet_alarms += 1 if core_counts(fs) else 0
    far = quiet_alarms / max(1, len(labels["quiet"]))

    print(f"Split: {a.split}  cases: {len(cases)}  quiet controls: {len(labels['quiet'])}")
    print(f"{'kind':26}{'TP':>4}{'FP':>4}{'FN':>4}{'prec':>8}{'recall':>8}  status")
    ok = True
    for k in sorted(set(tp) | set(fp) | set(fn)):
        p = tp[k] / (tp[k] + fp[k]) if tp[k] + fp[k] else 0.0
        r = tp[k] / (tp[k] + fn[k]) if tp[k] + fn[k] else 0.0
        good = p >= th["precision_per_kind_min"] and r >= th["recall_per_kind_min"]
        ok &= good
        print(f"{k:26}{tp[k]:4}{fp[k]:4}{fn[k]:4}{p:8.2f}{r:8.2f}  {'PASS' if good else 'FAIL'}")
    print(f"false-alarm rate on quiet controls: {far:.2f} "
          f"({'PASS' if far <= th['false_alarm_rate_max'] else 'FAIL'})")
    print(f"briefs blocked by validation: {blocked}; must-not violations: {violations or 'none'}")
    ok &= far <= th["false_alarm_rate_max"] and not violations
    n = len(cases)
    need = th["target_set_size"][a.split]
    print(f"\nSet size {n}/{need} target. " + ("Thresholds met." if ok else "Thresholds NOT met.")
          + (" Too small to count as evidence." if n < need else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
