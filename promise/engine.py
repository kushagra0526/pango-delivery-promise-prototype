"""Checkout delivery promises: business days from the nominal ship day.

Every method sees only what a tracking feed would have shown by the time the order was placed.
  sla_max            the upper end of the carrier's published range
  mean               rounded mean of the lane's delivered history
  quantile           smallest day count that 95% of the lane's last 600 deliveries met (carrier pool when thin)
  adaptive (this)    promise from what tracking already shows about the lane's most recent parcels:
                     1. smallest d that the latest 150 parcels whose d-day outcome is known kept (<= 7 late).
                        A parcel shipped n business days ago and not delivered is already late for any d < n,
                        so this reads recent parcels without waiting for them to arrive;
                     2. plus a slowdown shift read from parcels not due yet: if far more of them are still
                        in transit after k ~ median days than history says, the lane has slowed by s days.
                     Falls back to the plain quantile until a lane has enough parcels.
"""
import heapq
from collections import defaultdict, deque
import numpy as np
from . import sim, cal

TARGET = 0.95
WINDOW, RECENT = 600, 600
COHORT, MAX_LATE = 150, 7                      # 7/150 late = 4.7%; tuned on dev seeds only
EARLY_N = 40


def q_days(data):
    """Smallest whole number of days d with share(D <= d) >= TARGET."""
    v = np.sort(np.asarray(data))
    return int(v[min(len(v) - 1, int(np.ceil(TARGET * len(v))) - 1)])


class Lane:
    def __init__(self):
        self.hist = deque(maxlen=WINDOW)
        self.shipped = deque(maxlen=RECENT)        # order indices, newest last
        self.n, self.cache = 0, {}


def base_days(method, L, pool, carrier, zone):
    if method == "sla_max" or (len(L.hist) < 30 and not pool):
        return sim.SLA[carrier]["near" if zone in sim.NEAR else "far"][1]
    if L.n not in L.cache:                          # L.n counts every update this lane reads
        data = list(L.hist) if len(L.hist) >= 30 else list(L.hist) + list(pool)[-300:]
        d = max(1, int(round(float(np.mean(data))))) if method == "mean" else q_days(data)
        L.cache = {L.n: max(1, d)}
    return L.cache[L.n]


def recent_days(L, orders, today, lo, hi):
    """Smallest d >= q that the lane's most recent parcels whose d-day outcome is already known kept.

    A parcel shipped n business days ago that has not arrived is already known to be late for any
    promise under n days, so for promise d we only need parcels shipped at least d+1 business days ago,
    not ones fully delivered. That shows a slowdown about (D - d) days sooner than delivered history."""
    for d in range(lo, hi):
        late = []
        for j in reversed(L.shipped):
            p = orders[j]
            if p["delivered"] < today:
                late.append(p["D"] > d)
            elif cal.bd_between(p["nominal"], today) > d:
                late.append(True)
            if len(late) == COHORT:
                break
        if len(late) < COHORT:
            return None
        if sum(late) <= MAX_LATE:
            return d
    return hi


def early_shift(L, orders, today, q):
    """Lane slowdown in days, read from parcels that are not due yet.

    Normally a share p_k of parcels is still in transit after k business days. If the most recent parcels
    shipped more than k days ago are still out far more often than that, the lane has slowed down; the
    shift s is the smallest one for which share(history > k - s) explains what we see. Using k near the
    median means a +2-day slowdown shows ~q-k days before any promise is actually missed."""
    h = np.asarray(L.hist)
    if len(h) < 100:
        return 0
    shift = 0
    for k in range(1, q):
        pk = float(np.mean(h > k))
        if not 0.2 <= pk <= 0.8:
            continue
        out = []
        for j in reversed(L.shipped):
            p = orders[j]
            if cal.bd_between(p["nominal"], today) > k:
                out.append(not (p["delivered"] < today and p["D"] <= k))
                if len(out) == EARLY_N:
                    break
        if len(out) < EARLY_N:
            continue
        for s in range(0, 5):
            ps = float(np.mean(h > k - s)) if k - s > 0 else 1.0
            if sum(out) <= EARLY_N * ps + 2.5 * np.sqrt(EARLY_N * ps * (1 - ps)) + 1:
                break
        shift = max(shift, s)
    return shift


def run(stream, method):
    lanes = defaultdict(Lane)
    pools = defaultdict(lambda: deque(maxlen=WINDOW))
    pending, out, floors = [], [], {}
    orders = stream["orders"]
    base = "quantile" if method == "adaptive" else method
    for i, o in enumerate(orders):
        while pending and pending[0][0] <= o["t"]:          # delivery known at the end of its day
            _, j = heapq.heappop(pending)
            p = orders[j]
            L = lanes[(p["carrier"], p["zone"])]
            L.hist.append(p["D"]); pools[p["carrier"]].append(p["D"]); L.n += 1
            for (c, _), M in lanes.items():
                if c == p["carrier"] and M is not L and len(M.hist) < 30:
                    M.n += 1                                 # thin lanes read the carrier pool
        lane = (o["carrier"], o["zone"])
        L = lanes[lane]
        q = base_days(base, L, pools[o["carrier"]], *lane)
        d, raised = q, False
        if method == "adaptive":
            if (lane, o["day"]) not in floors:              # tracking state changes once a day
                r = recent_days(L, orders, o["day"], 1, q + 5)
                floors[(lane, o["day"])] = q if r is None else r
            d = floors[(lane, o["day"])]
            if (lane, o["day"], "s") not in floors:
                floors[(lane, o["day"], "s")] = early_shift(L, orders, o["day"], q)
            d = d + floors[(lane, o["day"], "s")]
            raised = d > q
        out.append(dict(promised=d, late=o["D"] > d, raised=raised))
        L.shipped.append(i)
        heapq.heappush(pending, (o["delivered"] + 1, i))
    return out
