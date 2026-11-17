"""Simulate detector-combination policies on raw_scores.json from benchmark_candidates.py (no re-inference).

Policies never average scores; they combine per-detector decisions. 'small/compressed' quality gate:
long side < 512 px or JPEG re-compression variant -> a 'real' outcome is downgraded to inconclusive.
Usage: python simulate_policies.py <benchmark_dir>
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

rows = json.loads((Path(sys.argv[1]) / "raw_scores.json").read_text(encoding="utf-8"))
POS, NEG = {"AI_GENERATED", "AI_EDITED", "MIXED"}, {"REAL", "MANUALLY_EDITED"}


def d(r, k):
    return r[k]["decision"]


def small(r):
    w, h = map(int, r["size"].split("x"))
    return max(w, h) < 512


def swin(r):
    return {"ai": "ai", "real": "real"}.get(d(r, "swinv2 (production)"), "unc")


POLICIES = {
    "P0 current: SwinV2 only": lambda r: swin(r),
    "P1 CF-lowq only": lambda r: d(r, "cf_lowq"),
    "P2 CF-frontier only": lambda r: d(r, "cf_frontier"),
    "P3 lowq AND frontier agree, else inconclusive":
        lambda r: d(r, "cf_lowq") if d(r, "cf_lowq") == d(r, "cf_frontier") else "unc",
    "P4 SwinV2 + CF-lowq: agree -> that; disagree -> inconclusive":
        lambda r: swin(r) if swin(r) == d(r, "cf_lowq") else "unc",
    "P5 majority of 3 (swin, frontier, lowq), no strong conflict":
        lambda r: ("ai" if [swin(r), d(r, "cf_frontier"), d(r, "cf_lowq")].count("ai") >= 2 and swin(r) != "real" else
                   "real" if [swin(r), d(r, "cf_frontier"), d(r, "cf_lowq")].count("real") >= 2 and
                   [swin(r), d(r, "cf_frontier"), d(r, "cf_lowq")].count("ai") == 0 else "unc"),
    "P6 CF-lowq AI & not contradicted by stable SwinV2-real; real only if both real":
        lambda r: ("ai" if d(r, "cf_lowq") == "ai" and swin(r) != "real" else
                   "real" if d(r, "cf_lowq") == "real" and swin(r) == "real" else "unc"),
}


def cf_vote(r, lowq_for_small):
    """One vote for the Community Forensics family (frontier and lowq share lineage -> not independent)."""
    if lowq_for_small and small(r):
        return d(r, "cf_lowq")  # the low-quality model was fine-tuned for downscaled inputs
    return d(r, "cf_lowq") if d(r, "cf_lowq") == d(r, "cf_frontier") else "unc"


def families(r, lowq_for_small=False):
    cf, sw = cf_vote(r, lowq_for_small), swin(r)
    if cf == "ai" and sw != "real":
        return "ai"
    if cf == "real" and sw != "ai":
        return "real"
    if cf == "unc" and sw in ("ai", "real"):
        return sw
    return "unc"


POLICIES["P7 two families (CF consensus vote, SwinV2 vote); conflict -> inconclusive"] = lambda r: families(r)
POLICIES["P8 as P7, CF vote = lowq alone for small images"] = lambda r: families(r, True)


def gate(fn):
    def g(r):
        out = fn(r)
        return "unc" if out == "real" and (small(r) or r["variant"] in ("jpeg70", "wa320")) else out
    return g


for name in list(POLICIES):
    POLICIES[name + "  +quality gate"] = gate(POLICIES[name])

cats = defaultdict(list)
for r in rows:
    if r["variant"] == "original":
        cats["all originals"].append(r)
        if r["src"] in ("batch", "regression"):
            cats["independent (batch+regr)"].append(r)
    else:
        cats[r["variant"]].append(r)

print(f"{'policy':78} | " + " | ".join(f"{c:>24}" for c in cats))
print(" " * 78 + " | " + " | ".join(f"{'TP/P FP/N unc  F1':>24}" for _ in cats))
for name, fn in POLICIES.items():
    cells = []
    for c, rs in cats.items():
        pos = [r for r in rs if r["label"] in POS]
        neg = [r for r in rs if r["label"] in NEG]
        tp = sum(fn(r) == "ai" for r in pos)
        fp = sum(fn(r) == "ai" for r in neg)
        unc = sum(fn(r) == "unc" for r in rs)
        prec = tp / (tp + fp) if tp + fp else 0
        rec = tp / len(pos) if pos else 0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
        cells.append(f"{tp:>2}/{len(pos):<2} {fp:>2}/{len(neg):<2} {unc:>3} {f1:5.2f}")
    print(f"{name:78} | " + " | ".join(f"{x:>24}" for x in cells))
reg = [r for r in rows if r["src"] == "regression" and r["variant"] == "original"][0]
print("\nregression image:", {n: fn(reg) for n, fn in POLICIES.items()})
