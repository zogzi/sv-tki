"""Data-driven calendar; weekdays use Monday=0 through Sunday=6."""
import json
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"


def load_holidays():
    return json.loads((DATA / "holidays.json").read_text(encoding="utf-8"))


def easter(year):
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    n = h + l - 7 * m + 114
    return date(year, n // 31, n % 31 + 1)


def occurrence(holiday, year):
    rule = holiday["rule"]
    match rule["type"]:
        case "fixed":
            return date(year, rule["month"], rule["day"])
        case "easter":
            return easter(year) + timedelta(days=rule["offset"])
        case "nth_weekday":
            first = date(year, rule["month"], 1)
            result = first + timedelta(days=(rule["weekday"] - first.weekday()) % 7 + 7 * (rule["nth"] - 1))
            if result.month != first.month:
                raise ValueError("Weekday occurrence outside month")
            return result
        case _:
            raise ValueError("Unknown date rule")


def today(day, holidays):
    return [h for h in holidays if occurrence(h, day.year) == day]


def upcoming(day, holidays, count=5):
    events = [(occurrence(h, year), h) for year in range(day.year, day.year + 3) for h in holidays]
    return sorted((e for e in events if e[0] > day), key=lambda e: (e[0], e[1]["id"]))[:count]
