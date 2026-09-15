"""Refresh profile graphics from GitHub's public contribution calendar; no token needed."""

from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

USERNAME = "patelved3313"
FIRST_YEAR = 2026  # Public account created 2026-01-07; include every contribution year.
ASSETS = Path(__file__).resolve().parents[1] / "assets"
BG, FG, MUTED, LIME, BORDER = "#101210", "#F1F3E8", "#A8B09F", "#D5FF70", "#343B31"


class CalendarParser(HTMLParser):
    """Join calendar dates to their accessible contribution-count tooltips."""

    def __init__(self):
        super().__init__()
        self.cells = {}
        self.labels = {}
        self.target = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and "data-date" in attrs:
            key = attrs.get("id")
            if not key or key in self.cells:
                raise ValueError("Missing or duplicate calendar cell ID")
            self.cells[key] = date.fromisoformat(attrs["data-date"])
        if tag == "tool-tip":
            self.target = attrs.get("for")
            self.parts = []

    def handle_data(self, data):
        if self.target is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.target is not None:
            if self.target in self.labels:
                raise ValueError("Duplicate calendar tooltip")
            self.labels[self.target] = " ".join("".join(self.parts).split())
            self.target = None


def parse_calendar(html, start, end):
    parser = CalendarParser()
    parser.feed(html)
    days = {}
    for key, day in parser.cells.items():
        if not start <= day <= end:
            continue
        label = parser.labels.get(key, "")
        match = re.match(r"^(No|[\d,]+) contributions?\b", label)
        if not match:
            raise ValueError(f"Missing or invalid contribution count for {day}")
        count = 0 if match[1] == "No" else int(match[1].replace(",", ""))
        if day in days:
            raise ValueError(f"Duplicate calendar date: {day}")
        days[day] = count
    expected = {start + timedelta(days=i) for i in range((end - start).days + 1)}
    if set(days) != expected:
        raise ValueError("Incomplete GitHub calendar; retaining previous graphics")
    return days


def fetch_calendar(year, today):
    start, end = date(year, 1, 1), min(date(year, 12, 31), today)
    url = (f"https://github.com/users/{USERNAME}/contributions"
           f"?from={start.isoformat()}&to={end.isoformat()}")
    request = Request(url, headers={"User-Agent": f"{USERNAME}-profile-activity", "Accept": "text/html"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                if response.status != 200 or "text/html" not in response.headers.get("Content-Type", ""):
                    raise ValueError("GitHub did not return a contribution calendar")
                body = response.read(4_000_001)
                if len(body) > 4_000_000:
                    raise ValueError("Unexpected calendar response size")
                return parse_calendar(body.decode("utf-8"), start, end)
        except (OSError, ValueError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def summarize(days, today):
    """Today may still be empty: preserve a streak ending yesterday."""
    ordered = sorted((day, count) for day, count in days.items() if day <= today)
    longest = run = 0
    previous = None
    for day, count in ordered:
        if not isinstance(count, int) or count < 0:
            raise ValueError("Contribution counts must be nonnegative integers")
        run = (run + 1 if previous == day - timedelta(days=1) else 1) if count else 0
        longest = max(longest, run)
        previous = day
    cursor = today if days.get(today, 0) else today - timedelta(days=1)
    current = 0
    while days.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    recent = [(today - timedelta(days=i), days.get(today - timedelta(days=i), 0))
              for i in reversed(range(31))]
    return current, longest, recent


def render_activity(days, today, mobile=False):
    current, longest, recent = summarize(days, today)
    width, height = (420, 350) if mobile else (800, 350)
    pad = 24 if mobile else 32
    number_size = 42 if mobile else 52
    label_size = 16 if mobile else 18
    right = width - pad
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}" fill="none" role="img" aria-labelledby="title desc">',
             '<title id="title">Ved Patel — GitHub contribution activity</title>',
             f'<desc id="desc">Current daily streak: {current} days. Longest daily streak: {longest} days. '
             f'{sum(c for _, c in recent)} contributions in the last 31 days. '
             f'Updated {today.isoformat()} UTC. Based on GitHub’s public contribution calendar.</desc>',
             f'<rect width="{width}" height="{height}" rx="20" fill="{BG}" />',
             '<g font-family="Arial, Helvetica, sans-serif">']

    def text(x, y, value, size=16, color=MUTED, extra=""):
        parts.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" {extra}>{escape(str(value))}</text>')

    text(pad, 35, "GITHUB / ACTIVITY", 13, MUTED, 'letter-spacing="1.5"')
    for x, count, label, color in [(pad, current, "Current streak", LIME),
                                   (width / 2 + (12 if mobile else 16), longest, "Longest streak", FG)]:
        text(x, 96, count, number_size, color, 'font-weight="700" letter-spacing="-1"')
        text(x + len(str(count)) * number_size * .59 + 10, 96, "days", label_size)
        text(x, 126, label, label_size)
    parts.append(f'<path d="M{pad} 151H{right}" stroke="{BORDER}" />')
    text(pad, 183, f"{sum(c for _, c in recent)} contributions · Last 31 days", label_size, FG)
    bottom, top = 277, 211
    peak = max(1, max(c for _, c in recent))
    # A zero series remains a flat baseline, never a fabricated activity curve.
    points = [(pad + i * (width - 2 * pad) / 30, bottom - count / peak * (bottom - top))
              for i, (_, count) in enumerate(recent)]
    coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    parts.extend([
        f'<path d="M{pad} {top}H{right}M{pad} {bottom}H{right}" stroke="{BORDER}" />',
        f'<polygon points="{pad},{bottom} {coords} {right},{bottom}" fill="{LIME}" fill-opacity=".07" />',
        f'<polyline points="{coords}" stroke="{LIME}" stroke-width="2" stroke-linejoin="round" />',
    ])
    for (x, y), (day, count) in zip(points, recent):
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{FG if count else BORDER}">'
                     f'<title>{day.isoformat()}: {count} contributions</title></circle>')
    text(pad, 303, recent[0][0].strftime("%b %d"), 14)
    text(right, 303, today.strftime("%b %d"), 14, MUTED, 'text-anchor="end"')
    text(right, 208, str(peak), 12, MUTED, 'text-anchor="end"')
    text(pad, 332, f"Updated {today.strftime('%d %b %Y')} UTC · Public calendar", 12 if mobile else 14)
    parts.extend(['</g>', '</svg>', ''])
    return "\n".join(parts)


def refresh(today=None, assets=ASSETS, fetcher=fetch_calendar):
    today = today or datetime.now(timezone.utc).date()
    days = {}
    for year in range(FIRST_YEAR, today.year + 1):
        days.update(fetcher(year, today))
    # Validate all data before touching either last-known-good asset.
    expected = (today - date(FIRST_YEAR, 1, 1)).days + 1
    if len(days) != expected or any(date(FIRST_YEAR, 1, 1) + timedelta(days=i) not in days
                                    for i in range(expected)):
        raise ValueError("Incomplete contribution history")
    rendered = {"activity.svg": render_activity(days, today),
                "activity-mobile.svg": render_activity(days, today, mobile=True)}
    for svg in rendered.values():
        ET.fromstring(svg)
    for name, svg in rendered.items():
        temporary = assets / f".{name}.tmp"
        temporary.write_text(svg, encoding="utf-8")
        temporary.replace(assets / name)
    current, longest, recent = summarize(days, today)
    print(f"Updated {today}: current={current}, longest={longest}, last31={sum(c for _, c in recent)}")


if __name__ == "__main__":
    refresh()
