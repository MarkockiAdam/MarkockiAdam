#!/usr/bin/env python3
"""Render data/contributions.json as an animated contribution heatmap SVG.

Usage:
    python scripts/render_heatmap_svg.py
    STATIC=1 python scripts/render_heatmap_svg.py

Writes contrib-heatmap.svg at 860px wide so it lines up with the 370 + 490
portrait/info-card pair in the README.

The grid draws itself column by column, then a scanline sweeps across on a
loop. Streak and total figures are computed here from the raw day data.
"""

import json
import os
from datetime import date, datetime

from theme import (
    BRIGHT, DIM, GREEN, GREEN_SOFT, LEVELS, LEVEL_EMPTY_STROKE, MONO, MUTED,
    fmt, glow_filter, window_chrome,
)

SRC = os.path.join("data", "contributions.json")
OUT = "contrib-heatmap.svg"
STATIC = os.environ.get("STATIC") == "1"

CELL = 12.0
GAP = 3.0
PITCH = CELL + GAP
WEEKS = 53
DAY_COL = 26.0             # width of the Mon/Wed/Fri gutter

WIDTH = 860.0
PAD_X = (WIDTH - DAY_COL - (WEEKS * PITCH - GAP)) / 2

CHROME_H = 24.0
MONTH_H = 16.0
GRID_TOP = CHROME_H + 10 + MONTH_H
GRID_H = 7 * PITCH - GAP
LEGEND_Y = GRID_TOP + GRID_H + 24
STATS_Y = LEGEND_Y + 21
HEIGHT = STATS_Y + 16

CYCLE = 12.0

# The cycle starts on the *finished* graph and holds it, then wipes and
# redraws. Drawing from empty instead would mean anyone landing on the page
# at the top of a loop sees a blank year, which reads as broken rather than
# as animation. Fractions of the cycle:
HOLD_FRAC = 0.62           # finished graph sits still until here
WAVE_START = 0.65          # wipe, then the column wave begins
WAVE_SPAN = 0.22           # how long the wave takes to cross the year
SWEEP_SPAN = 0.13          # scanline pass once the wave lands

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load():
    if not os.path.exists(SRC):
        raise SystemExit(f"error: {SRC} missing -- run scripts/fetch_contributions.py first")
    with open(SRC, encoding="utf-8") as fh:
        return json.load(fh)


def streaks(days):
    """Longest and current run of consecutive days with at least one contribution.

    The final day is excluded from breaking the current streak: a day that is
    still in progress should not read as a broken streak.
    """
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)

    current = 0
    for d in reversed(days):
        if d["count"] > 0:
            current += 1
        elif current or d is not days[-1]:
            break
    return longest, current


def to_grid(days):
    """Lay days out as columns of weeks, Sunday first, matching GitHub."""
    grid = [[None] * 7 for _ in range(WEEKS)]
    first = datetime.strptime(days[0]["date"], "%Y-%m-%d").date()
    origin = first - date.resolution * ((first.weekday() + 1) % 7)

    for d in days:
        day = datetime.strptime(d["date"], "%Y-%m-%d").date()
        offset = (day - origin).days
        col, row = divmod(offset, 7)
        if 0 <= col < WEEKS:
            grid[col][row] = d
    return grid, origin


def month_labels(grid):
    """One label per month, placed at the first column that month occupies."""
    out, seen = [], set()
    for col, week in enumerate(grid):
        first = next((d for d in week if d), None)
        if not first:
            continue
        day = datetime.strptime(first["date"], "%Y-%m-%d").date()
        key = (day.year, day.month)
        if key in seen or day.day > 7:
            continue
        seen.add(key)
        out.append((col, MONTHS[day.month - 1]))
    return out


def main():
    data = load()
    days = data["days"]
    grid, _ = to_grid(days)
    longest, current = streaks(days)
    best = max(days, key=lambda d: d["count"])

    wave_end = WAVE_START + WAVE_SPAN

    o = []
    a = o.append
    a(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(WIDTH)}" '
        f'height="{fmt(HEIGHT)}" viewBox="0 0 {fmt(WIDTH)} {fmt(HEIGHT)}" '
        f'role="img" aria-label="{data["total"]} GitHub contributions in the last year">'
    )
    a(f'<title>{data["total"]} contributions from {data["range"]["from"]} '
      f'to {data["range"]["to"]}</title>')

    a("<defs>")
    a(
        f'<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{GREEN}" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="{GREEN_SOFT}" stop-opacity="0.22"/>'
        f'<stop offset="1" stop-color="{GREEN}" stop-opacity="0"/>'
        "</linearGradient>"
    )
    glow_filter(a, "cellglow", blur=1.5, strength=0.45)
    a(f'<clipPath id="gridclip"><rect x="{fmt(PAD_X + DAY_COL)}" '
      f'y="{fmt(GRID_TOP)}" width="{fmt(WEEKS * PITCH)}" height="{fmt(GRID_H)}"/></clipPath>')
    a("</defs>")

    window_chrome(a, WIDTH, HEIGHT, f'contributions.sh &#8212; {data["username"]}')

    # Month labels.
    a(f'<g font-family="{MONO}" font-size="9" fill="{MUTED}">')
    for col, label in month_labels(grid):
        x = PAD_X + DAY_COL + col * PITCH
        a(f'<text x="{fmt(x)}" y="{fmt(GRID_TOP - 6)}">{label}</text>')
    a("</g>")

    # Weekday gutter.
    a(f'<g font-family="{MONO}" font-size="9" fill="{DIM}">')
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = GRID_TOP + row * PITCH + CELL - 2
        a(f'<text x="{fmt(PAD_X)}" y="{fmt(y)}">{label}</text>')
    a("</g>")

    # The grid: one group per week column, revealed in a left-to-right wave.
    # The bloom sits on the whole grid so busy weeks glow rather than each
    # cell paying for its own filter pass.
    a('<g filter="url(#cellglow)">')
    eps = 0.002
    for col, week in enumerate(grid):
        x = PAD_X + DAY_COL + col * PITCH
        t0 = WAVE_START + (col / WEEKS) * WAVE_SPAN
        t1 = WAVE_START + ((col + 1.6) / WEEKS) * WAVE_SPAN
        # Opaque in markup so the graph is readable even where SMIL is ignored;
        # the animation overrides this from t=0 wherever it does run -- and its
        # own t=0 value is 1, so the graph is never blank on arrival.
        a('<g opacity="1">')
        if not STATIC:
            a(
                f'<animate attributeName="opacity" values="1;1;0;0;1;1" '
                f'keyTimes="0;{fmt(HOLD_FRAC)};{fmt(HOLD_FRAC + eps)};'
                f'{fmt(t0)};{fmt(min(t1, 1))};1" '
                f'dur="{fmt(CYCLE)}s" repeatCount="indefinite"/>'
            )
        for row in range(7):
            d = week[row]
            y = GRID_TOP + row * PITCH
            if d is None:
                continue
            fill = LEVELS[min(d["level"], 4)]
            stroke = f' stroke="{LEVEL_EMPTY_STROKE}"' if d["level"] == 0 else ""
            a(
                f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(CELL)}" '
                f'height="{fmt(CELL)}" rx="2.5" fill="{fill}"{stroke}>'
                f'<title>{d["count"]} on {d["date"]}</title></rect>'
            )
        a("</g>")
    a("</g>")

    # Scanline sweep across the finished grid.
    if not STATIC:
        span = WEEKS * PITCH
        a(f'<g clip-path="url(#gridclip)">')
        a(
            f'<rect y="{fmt(GRID_TOP)}" width="120" height="{fmt(GRID_H)}" '
            f'fill="url(#sweep)" x="{fmt(PAD_X + DAY_COL - 140)}">'
        )
        a(
            f'<animate attributeName="x" '
            f'values="{fmt(PAD_X + DAY_COL - 140)};{fmt(PAD_X + DAY_COL - 140)};'
            f'{fmt(PAD_X + DAY_COL + span + 20)};{fmt(PAD_X + DAY_COL + span + 20)}" '
            f'keyTimes="0;{fmt(wave_end)};{fmt(min(wave_end + SWEEP_SPAN, 1))};1" '
            f'dur="{fmt(CYCLE)}s" repeatCount="indefinite"/>'
        )
        a("</rect></g>")

    # Legend.
    legend_x = PAD_X + DAY_COL + WEEKS * PITCH - GAP - (5 * 15 + 74)
    a(f'<g font-family="{MONO}" font-size="9" fill="{DIM}">')
    a(f'<text x="{fmt(legend_x)}" y="{fmt(LEGEND_Y)}">Less</text>')
    for i, col in enumerate(LEVELS):
        stroke = f' stroke="{LEVEL_EMPTY_STROKE}"' if i == 0 else ""
        a(
            f'<rect x="{fmt(legend_x + 30 + i * 15)}" y="{fmt(LEGEND_Y - 9)}" '
            f'width="11" height="11" rx="2.5" fill="{col}"{stroke}/>'
        )
    a(f'<text x="{fmt(legend_x + 30 + 5 * 15 + 4)}" y="{fmt(LEGEND_Y)}">More</text>')
    a("</g>")

    # Stats strip.
    stats = [
        ("total", f'{data["total"]}'),
        ("longest streak", f"{longest}d"),
        ("current streak", f"{current}d"),
        ("best day", f'{best["count"]} on {best["date"]}'),
    ]
    a(f'<g font-family="{MONO}" font-size="10" xml:space="preserve">')
    a(
        f'<text x="{fmt(PAD_X)}" y="{fmt(STATS_Y)}" fill="{GREEN}">$ '
        f'<tspan fill="{MUTED}">git log --oneline | wc -l</tspan></text>'
    )
    x = PAD_X + DAY_COL + WEEKS * PITCH - GAP
    sep = f'<tspan fill="#30363d">  &#183;  </tspan>'
    parts = sep.join(
        f'<tspan fill="{DIM}">{k} </tspan><tspan fill="{BRIGHT}">{v}</tspan>'
        for k, v in stats
    )
    a(f'<text x="{fmt(x)}" y="{fmt(STATS_Y)}" text-anchor="end">{parts}</text>')
    a("</g>")

    a("</svg>")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("".join(o))
    print(
        f"wrote {OUT}  ({int(WIDTH)}x{int(HEIGHT)}px, {data['total']} contributions, "
        f"longest {longest}d, current {current}d)"
    )


if __name__ == "__main__":
    main()
