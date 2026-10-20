"""One lane, one slowdown: DHL to Germany gets ~2 business days slower for about three weeks (dev seed 1)."""
import collections
from promise import sim, engine

st = sim.make(1)
runs = {m: engine.run(st, m) for m in ("mean", "quantile", "adaptive")}
rows = collections.defaultdict(lambda: collections.Counter())
for i, o in enumerate(st["orders"]):
    if o["carrier"] == "DHL" and o["zone"] == "DE":
        wk = (o["day"] - st["start"]) // 7
        if 14 <= wk <= 21:
            r = rows[wk]; r["n"] += 1
            for m, out in runs.items():
                r[m + "_late"] += out[i]["late"]; r[m + "_days"] += out[i]["promised"]
print("DHL -> DE, orders placed per week. Promise in business days (avg), share of those orders delivered late.\n")
print(f"{'week':>4} {'orders':>6} | {'mean':>12} | {'95th pct':>12} | {'in-transit (this)':>18}")
for wk, r in sorted(rows.items()):
    cell = lambda m: f"{r[m + '_days'] / r['n']:.1f}d {100 * r[m + '_late'] / r['n']:3.0f}% late"
    print(f"{wk:>4} {r['n']:>6} | {cell('mean'):>12} | {cell('quantile'):>12} | {cell('adaptive'):>18}")
print("\nThe slowdown starts in week 15 and ends in week 18. The 95th percentile only moves once late parcels are")
print("delivered, then keeps the longer promise for weeks. The in-transit promise reads parcels that are still out:")
print("it moves up sooner and comes back down once recent parcels arrive on time again.")
