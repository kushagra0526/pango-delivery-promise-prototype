"""Business-day calendar for a Swedish warehouse (carriers deliver Mon-Fri, not on public holidays)."""
import datetime as dt


def easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return dt.date(y, month, day)


def holidays(years):
    out = set()
    for y in years:
        e = easter(y)
        mid = next(dt.date(y, 6, d) for d in range(19, 26) if dt.date(y, 6, d).weekday() == 4)   # midsummer eve
        out |= {dt.date(y, 1, 1), dt.date(y, 1, 6), e - dt.timedelta(2), e + dt.timedelta(1), dt.date(y, 5, 1),
                e + dt.timedelta(39), dt.date(y, 6, 6), mid, dt.date(y, 12, 24), dt.date(y, 12, 25), dt.date(y, 12, 26), dt.date(y, 12, 31)}
    return {d.toordinal() for d in out}


HOL = holidays(range(2024, 2028))


def is_bd(o):
    return dt.date.fromordinal(o).weekday() < 5 and o not in HOL


def next_bd(o):
    o += 1
    while not is_bd(o):
        o += 1
    return o


def add_bd(o, n):
    for _ in range(n):
        o = next_bd(o)
    return o


def bd_between(a, b):
    """Business days from a to b (b after a)."""
    n, o = 0, a
    while o < b:
        o = next_bd(o)
        n += 1
    return n


def ship_day(order_day, hour, cutoff=14):
    """The day the parcel would leave if handled on time: same business day before cutoff, else the next one."""
    if is_bd(order_day) and hour < cutoff:
        return order_day
    return next_bd(order_day)
