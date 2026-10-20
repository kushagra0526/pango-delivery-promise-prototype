"""docs/result.png: DHL->DE daily promise and late share (dev seed 1) + held-out summary."""
import json, sys, collections
sys.path.insert(0, ".")
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from promise import sim, engine

st = sim.make(1)
runs = {m: engine.run(st, m) for m in ("quantile", "adaptive")}
day = collections.defaultdict(lambda: collections.Counter())
for i, o in enumerate(st["orders"]):
    if o["carrier"] == "DHL" and o["zone"] == "DE":
        r = day[o["day"] - st["start"]]; r["n"] += 1
        for m, out in runs.items():
            r[m + "d"] += out[i]["promised"]; r[m + "l"] += out[i]["late"]
xs = [d for d in sorted(day) if 90 <= d <= 160]
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
for m, c, lab in (("quantile", "#999", "95th percentile of deliveries"), ("adaptive", "#1f6feb", "in-transit tracking (this)")):
    ax[0].plot(xs, [day[d][m + "d"] / day[d]["n"] for d in xs], color=c, lw=2, label=lab)
ax[0].axvspan(108, 130, color="#f85149", alpha=.08, label="DHL DE slowdown (+2 days)")
ax[0].set_title("Promised business days, DHL to Germany"); ax[0].set_xlabel("day"); ax[0].legend(fontsize=8)
h = json.load(open("out/heldout_first_run.json"))["results"]
names = {"sla_max": "carrier SLA max", "mean": "mean", "quantile": "95th pct", "adaptive": "this"}
late = [100 * h[m]["d_late"] / h[m]["dn"] for m in names]
ax[1].bar(list(names.values()), late, color=["#bbb", "#bbb", "#999", "#1f6feb"])
for i, m in enumerate(names):
    ax[1].text(i, late[i] + 1, f"{100 * h[m]['on_time'] / h[m]['n']:.1f}% on time\n{h[m]['days'] / h[m]['n']:.2f} d", ha="center", fontsize=8)
ax[1].set_title("Held-out (frozen first run): % late during disruptions"); ax[1].set_ylim(0, 75)
plt.tight_layout(); plt.savefig("docs/result.png", dpi=110)
