import datetime as dt
from promise import cal, engine, sim


def o(y, m, d):
    return dt.date(y, m, d).toordinal()


def test_calendar_skips_weekend_and_swedish_holidays():
    assert not cal.is_bd(o(2025, 6, 6))              # national day
    assert not cal.is_bd(o(2025, 6, 20))             # midsummer eve
    assert cal.easter(2025) == dt.date(2025, 4, 20)
    assert cal.add_bd(o(2025, 4, 17), 1) == o(2025, 4, 22)   # Good Friday + Easter Monday
    assert cal.bd_between(o(2025, 3, 7), o(2025, 3, 10)) == 1


def test_cutoff():
    assert cal.ship_day(o(2025, 3, 4), 13.9) == o(2025, 3, 4)
    assert cal.ship_day(o(2025, 3, 4), 14.1) == o(2025, 3, 5)
    assert cal.ship_day(o(2025, 3, 8), 9) == o(2025, 3, 10)  # Saturday


def test_quantile_is_discrete_95th():
    assert engine.q_days([1] * 95 + [9] * 5) == 1
    assert engine.q_days([1] * 94 + [9] * 6) == 9


def test_methods_only_use_known_deliveries():
    st = sim.make(7, dict(days=40, orders_per_day=80))
    a = engine.run(st, "adaptive")
    st2 = sim.make(7, dict(days=40, orders_per_day=80))
    for p in st2["orders"][-200:]:                     # change the future: promises before it must not move
        p["delivered"] += 30; p["D"] += 20
    b = engine.run(st2, "adaptive")
    cut = len(a) - 200
    assert [x["promised"] for x in a[:cut]] == [x["promised"] for x in b[:cut]]


def test_in_transit_parcels_count_as_late_before_they_arrive():
    st = sim.make(3, dict(days=1, orders_per_day=1))
    L = engine.Lane()
    today = o(2025, 3, 20)
    orders = [dict(nominal=o(2025, 3, 10), delivered=today + 30, D=99) for _ in range(engine.COHORT)]
    L.shipped.extend(range(len(orders)))
    assert engine.recent_days(L, orders, today, 1, 6) == 6    # all still out after 8 bd: every d <= 5 already missed


def test_adaptive_reacts_to_slowdown():
    cfg = dict(days=120, disruptions=[dict(carrier="DHL", zone="DE", start=60, days=40, extra=2.0)])
    st = sim.make(5, cfg)
    q, a = engine.run(st, "quantile"), engine.run(st, "adaptive")
    lane = [i for i, x in enumerate(st["orders"]) if x["carrier"] == "DHL" and x["zone"] == "DE"
            and 60 <= x["day"] - st["start"] < 100]
    assert sum(a[i]["late"] for i in lane) < 0.6 * sum(q[i]["late"] for i in lane)
