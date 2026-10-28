"""Small formatting helpers.

Written by hand because Windows' strftime doesn't support %-I / %-d
(the "no leading zero" codes).
"""

from datetime import date, datetime, timedelta


def format_duration(d: timedelta) -> str:
    """e.g. 01:05:09"""
    total = int(d.total_seconds())
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_time(t: datetime) -> str:
    """e.g. 9:05 AM"""
    hour = t.hour % 12 or 12
    period = "AM" if t.hour < 12 else "PM"
    return f"{hour}:{t.minute:02d} {period}"


def format_date(d: date) -> str:
    """e.g. Thursday, October 22, 2026"""
    return f"{d:%A, %B} {d.day}, {d.year}"


def format_short_date(d: date) -> str:
    """e.g. Oct 22"""
    return f"{d:%b} {d.day}"


def format_hours(d: timedelta) -> str:
    """Human-friendly total, e.g. 7h 05m"""
    minutes = int(d.total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def format_range(start: date, end: date) -> str:
    """e.g. Oct 19 – 25, 2026 · Oct 26 – Nov 1, 2026 · Dec 28, 2026 – Jan 3, 2027"""
    if start.year != end.year:
        return f"{format_short_date(start)}, {start.year} – {format_short_date(end)}, {end.year}"
    if start.month != end.month:
        return f"{format_short_date(start)} – {format_short_date(end)}, {end.year}"
    return f"{format_short_date(start)} – {end.day}, {end.year}"