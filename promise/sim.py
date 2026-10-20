"""Simulated order stream for a Stockholm-based brand: lanes = carrier x destination zone, true
transit in business days, warehouse handling slips, and disruptions (temporary slowdowns, a lane that
gets permanently slower)."""
import datetime as dt
import numpy as np
from . import cal

CARRIERS = {"PostNord": dict(SE=1.2, NO=2.4, DK=2.0, FI=2.6, DE=3.4, NL=3.6, FR=4.2, PL=4.4),
            "DHL":      dict(SE=1.4, NO=2.2, DK=1.8, FI=2.2, DE=2.2, NL=2.4, FR=2.8, PL=3.0),
            "Bring":    dict(SE=1.6, NO=1.6, DK=2.2, FI=3.0, DE=3.8, NL=4.0, FR=4.6, PL=4.8),
            "UPS":      dict(SE=1.3, NO=1.9, DK=1.6, FI=2.0, DE=1.7, NL=1.8, FR=2.0, PL=2.4)}
SLA = {"PostNord": dict(near=(1, 3), far=(3, 5)), "DHL": dict(near=(1, 2), far=(2, 4)),
       "Bring": dict(near=(1, 3), far=(3, 5)), "UPS": dict(near=(1, 2), far=(1, 3))}
NEAR = {"SE", "NO", "DK", "FI"}
DEV = dict(start=dt.date(2025, 3, 3), days=182, orders_per_day=350, handling_slip=0.08, spread=0.35,
           zones=["SE", "NO", "DK", "FI", "DE", "NL", "FR"], zone_w=[40, 12, 10, 8, 14, 8, 8],
           disruptions=[dict(carrier="DHL", zone="DE", start=110, days=16, extra=2.0),
                        dict(carrier="PostNord", zone="*", start=60, days=10, extra=1.0)])


def make(seed, cfg=None):
    c = {**DEV, **(cfg or {})}
    r = np.random.default_rng(seed)
    start = (c["start"] if isinstance(c["start"], dt.date) else dt.date.fromisoformat(c["start"])).toordinal()
    w = np.array(c["zone_w"], float); w /= w.sum()
    orders = []
    for day in range(c["days"]):
        o = start + day
        n = r.poisson(c["orders_per_day"] * (1.25 if dt.date.fromordinal(o).weekday() >= 5 else 1.0))
        hours = r.uniform(0, 24, n)
        zones = r.choice(c["zones"], n, p=w)
        carr = r.choice(list(CARRIERS), n, p=[0.4, 0.3, 0.15, 0.15])
        for h, z, k in zip(hours, zones, carr):
            nominal = cal.ship_day(o, h)
            ship = cal.next_bd(nominal) if r.random() < c["handling_slip"] else nominal
            mu = CARRIERS[k].get(z, 3.0)
            for d in c["disruptions"]:
                if d["carrier"] == k and d["zone"] in (z, "*") and start + d["start"] <= ship < start + d["start"] + d["days"] * 1.4:
                    mu += d["extra"]
            transit = max(1, int(round(mu * np.exp(r.normal(0, c["spread"])))))
            delivered = cal.add_bd(ship, transit)
            orders.append(dict(t=o + h / 24, day=o, hour=h, zone=z, carrier=k, nominal=nominal, delivered=delivered,
                               D=cal.bd_between(nominal, delivered)))
    orders.sort(key=lambda x: x["t"])
    return dict(orders=orders, start=start, cfg=c)
