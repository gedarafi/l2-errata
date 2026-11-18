"""Top causes and types, trend over time, repeated mistakes."""
from collections import Counter, defaultdict
from enum import Enum
from typing import Any

from .models import Entry


class Period(str, Enum):
    WEEK = "week"
    MONTH = "month"


class Group(str, Enum):
    """What the trend columns count."""
    CAUSE = "cause"  # learner-layer cause
    TYPE = "type"    # main ERRANT type, R:PREP → PREP
    FULL = "full"    # full ERRANT type


class Stats:
    def __init__(self, entries: list[Entry], by: Period = Period.WEEK, group: Group = Group.CAUSE, top: int = 5):
        self.entries = entries
        self.by = by
        self.group = group
        self.top = top

    def period_key(self, entry: Entry) -> str:
        if self.by is Period.MONTH:
            return entry.date.strftime("%Y-%m")
        year, week, _ = entry.date.isocalendar()
        return f"{year}-W{week:02d}"

    @staticmethod
    def group_key(entry: Entry, group: Group) -> str:
        if group is Group.CAUSE:
            return entry.cause.value
        if group is Group.FULL:
            return entry.errant_type
        return entry.main_type

    def compute(self) -> dict[str, Any]:
        entries = self.entries
        causes = Counter(e.cause.value for e in entries)
        types = Counter(e.main_type for e in entries)

        periods: dict[str, Counter] = defaultdict(Counter)
        for e in entries:
            periods[self.period_key(e)][self.group_key(e, self.group)] += 1
        overall = Counter(self.group_key(e, self.group) for e in entries)
        columns = [k for k, _ in overall.most_common(self.top)]

        trend = []
        for p in sorted(periods):
            c = periods[p]
            total = sum(c.values())
            row = {"period": p, "total": total, "counts": {k: c.get(k, 0) for k in columns}}
            row["counts"]["(rest)"] = total - sum(row["counts"].values())
            trend.append(row)

        # Same mistake logged more than once. Exact match: case matters (maybe → Maybe).
        pairs = Counter((e.original.strip(), e.corrected.strip()) for e in entries)
        repeats = [{"original": o, "corrected": c, "count": n} for (o, c), n in pairs.most_common() if n > 1]

        dates = [e.date for e in entries]
        return {
            "total": len(entries),
            "from": min(dates).isoformat() if dates else None,
            "to": max(dates).isoformat() if dates else None,
            "causes": causes.most_common(),
            "types": types.most_common(),
            "trend": {"by": self.by.value, "group": self.group.value, "columns": columns + ["(rest)"], "rows": trend},
            "repeats": repeats,
        }


class StatsReport:
    """Plain-text rendering of Stats.compute()."""

    def __init__(self, stats: dict[str, Any], lang: str, top: int):
        self.s = stats
        self.lang = lang
        self.top = top

    def bars(self, items: list[tuple[str, int]]) -> list[str]:
        total, top = self.s["total"], self.top
        width = max((len(k) for k, _ in items[:top]), default=0)
        lines = []
        for k, n in items[:top]:
            pct = 100 * n / total
            lines.append(f"  {k:<{width}}  {n:>3}  {pct:5.1f}%  {'█' * max(1, round(pct / 4))}")
        rest = sum(n for _, n in items[top:])
        if rest:
            lines.append(f"  {'(rest)':<{width}}  {rest:>3}")
        return lines

    def trend(self) -> list[str]:
        t = self.s["trend"]
        cols = t["columns"]
        widths = [max(len(c), 4) + 2 for c in cols]
        lines = [f"Trend by {t['by']} ({t['group']}, % of that period's mistakes)",
                 "  " + f"{'period':<9}" + f"{'n':>4}" + "".join(f"{c:>{w}}" for c, w in zip(cols, widths))]
        for r in t["rows"]:
            cells = "".join(f"{100 * r['counts'][c] / r['total']:>{w - 1}.0f}%" for c, w in zip(cols, widths))
            lines.append("  " + f"{r['period']:<9}" + f"{r['total']:>4}" + cells)
        return lines

    def repeats(self) -> list[str]:
        if not self.s["repeats"]:
            return ["  none yet: every mistake so far appears once"]
        return [f"  {r['count']}×  {r['original']!r} → {r['corrected']!r}" for r in self.s["repeats"]]

    def render(self) -> str:
        s = self.s
        return "\n".join([
            f"{s['total']} mistakes, {s['from']} → {s['to']}  (lang: {self.lang})\n",
            "Top causes — why", *self.bars(s["causes"]),
            "\nTop error types — what", *self.bars(s["types"]),
            "", *self.trend(),
            "\nRepeated mistakes", *self.repeats(),
        ])
