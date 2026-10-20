"""On-time rate vs promised days, overall and inside disruptions.  python evaluate.py [dev|heldout] [out.json]"""
import json, sys, time
import numpy as np
from promise import sim, engine

METHODS = {"sla_max": "carrier SLA, upper end", "mean": "historical mean", "quantile": "lane 95th percentile",
           "adaptive": "in-transit tracking promise (this)"}


def in_disruption(o, s):
    for d in s["cfg"]["disruptions"]:
        if d["carrier"] == o["carrier"] and d["zone"] in (o["zone"], "*") and s["start"] + d["start"] <= o["nominal"] < s["start"] + d["start"] + d["days"]:
            return True
    return False


def run(which):
    if which == "heldout":
        h = json.load(open("heldout/config.json"))
        seeds, cfg = h["seeds"], h["cfg"]
    else:
        seeds, cfg = [1, 2, 3], None
    res = {m: dict(n=0, on_time=0, days=0.0, dn=0, d_late=0) for m in METHODS}
    for s in seeds:
        st = sim.make(s, cfg)
        warm = st["start"] + 28                                  # first 4 weeks: history builds up
        for m in METHODS:
            out = engine.run(st, m)
            for o, p in zip(st["orders"], out):
                if o["day"] < warm:
                    continue
                r = res[m]
                r["n"] += 1; r["on_time"] += not p["late"]; r["days"] += p["promised"]
                if in_disruption(o, st):
                    r["dn"] += 1; r["d_late"] += p["late"]
    return dict(set=which, results=res)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "dev"
    t0 = time.time()
    r = run(which)
    print(f"{which}: ({time.time() - t0:.0f}s)")
    for m, x in r["results"].items():
        print(f"  {METHODS[m]:44s} on time {100 * x['on_time'] / x['n']:5.1f}%   avg promise {x['days'] / x['n']:.2f} business days   "
              f"late during disruptions {x['d_late']:5d}/{x['dn']} ({100 * x['d_late'] / max(1, x['dn']):.0f}%)")
    if len(sys.argv) > 2:
        json.dump(r, open(sys.argv[2], "w"), indent=1)
