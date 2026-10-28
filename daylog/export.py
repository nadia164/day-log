"""Turn a Report into CSV (for Excel/Sheets) or Markdown (for notes,
status updates, GitHub, Notion...)."""

from __future__ import annotations

import csv
import io

from .formatting import format_date, format_duration, format_hours, format_range, format_time
from .reports import Report


def to_csv(report: Report) -> str:
    """One row per day (future days left out)."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "Date", "Weekday", "Hours", "Time worked", "Sessions",
        "First in", "Last out", "Accomplishments",
    ])
    for d in report.days:
        if d.is_future:
            continue
        last_out = d.last_out
        writer.writerow([
            d.day.isoformat(),
            f"{d.day:%A}",
            f"{d.worked.total_seconds() / 3600:.2f}",  # decimal hours, easy to SUM in Excel
            format_duration(d.worked),
            len(d.sessions),
            format_time(d.first_in) if d.first_in else "",
            format_time(last_out) if last_out else ("running" if d.sessions else ""),
            " | ".join(a.text for a in d.accomplishments),
        ])
    return out.getvalue()


def to_markdown(report: Report) -> str:
    lines = [
        f"# Daylog report: {format_range(report.start, report.end)}",
        "",
        f"**Total:** {format_hours(report.total)} · "
        f"**Days worked:** {report.days_worked} · "
        f"**Daily average:** {format_hours(report.daily_average)} · "
        f"**Accomplishments:** {report.accomplishment_count}",
    ]
    for d in report.days:
        if not d.has_activity:
            continue  # skip empty days
        lines += ["", f"## {format_date(d.day)}"]
        if d.sessions:
            end = format_time(d.last_out) if d.last_out else "now"
            lines.append(f"_{format_hours(d.worked)} · {format_time(d.first_in)} – {end}_")
        if d.accomplishments:
            lines.append("")
            lines += [f"- {a.text}" for a in d.accomplishments]
    return "\n".join(lines) + "\n"