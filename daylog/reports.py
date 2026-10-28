"""Report numbers for a week or month. Plain Python, no Qt or SQL,
so it's easy to test and the export code can reuse it."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .models import Accomplishment, WorkSession


@dataclass(frozen=True)
class DayReport:
    day: date
    worked: timedelta
    sessions: tuple[WorkSession, ...]
    accomplishments: tuple[Accomplishment, ...]
    is_future: bool = False

    @property
    def first_in(self) -> datetime | None:
        return self.sessions[0].start if self.sessions else None

    @property
    def last_out(self) -> datetime | None:
        """None if there are no sessions or the last one is still running."""
        return self.sessions[-1].end if self.sessions else None

    @property
    def has_activity(self) -> bool:
        return bool(self.sessions or self.accomplishments)


@dataclass(frozen=True)
class Report:
    start: date
    end: date
    days: tuple[DayReport, ...]

    @property
    def total(self) -> timedelta:
        return sum((d.worked for d in self.days), timedelta())

    @property
    def days_worked(self) -> int:
        return sum(1 for d in self.days if d.worked > timedelta())

    @property
    def daily_average(self) -> timedelta:
        """Average over days you actually worked (days off don't drag it down)."""
        if not self.days_worked:
            return timedelta()
        return self.total / self.days_worked

    @property
    def accomplishment_count(self) -> int:
        return sum(len(d.accomplishments) for d in self.days)

    @property
    def longest_day(self) -> DayReport | None:
        worked = [d for d in self.days if d.worked > timedelta()]
        return max(worked, key=lambda d: d.worked) if worked else None


def week_range(day: date) -> tuple[date, date]:
    """Monday to Sunday of the week containing `day`."""
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


def month_range(day: date) -> tuple[date, date]:
    last = calendar.monthrange(day.year, day.month)[1]
    return day.replace(day=1), day.replace(day=last)


def build_report(
    sessions: list[WorkSession],
    accomplishments: list[Accomplishment],
    start: date,
    end: date,
    now: datetime,
) -> Report:
    """Group sessions (by the day they started) and accomplishments into days.
    A running session counts up to `now`."""
    by_day_sessions: dict[date, list[WorkSession]] = {}
    for s in sessions:
        by_day_sessions.setdefault(s.day, []).append(s)
    by_day_items: dict[date, list[Accomplishment]] = {}
    for a in accomplishments:
        by_day_items.setdefault(a.day, []).append(a)

    days = []
    current = start
    while current <= end:
        day_sessions = tuple(by_day_sessions.get(current, []))
        days.append(
            DayReport(
                day=current,
                worked=sum((s.duration_at(now) for s in day_sessions), timedelta()),
                sessions=day_sessions,
                accomplishments=tuple(by_day_items.get(current, [])),
                is_future=current > now.date(),
            )
        )
        current += timedelta(days=1)
    return Report(start=start, end=end, days=tuple(days))