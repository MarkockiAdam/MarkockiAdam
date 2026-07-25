#!/usr/bin/env python3
"""Render a neofetch-style info card as an animated SVG terminal.

Usage:
    python scripts/make_info_card.py
    STATIC=1 python scripts/make_info_card.py

Writes profile-card.svg. Edit ROWS / PUBLIC_WORK below to change the written
content. Counters still come from data/profile-stats.json.

Both this and the portrait pad out to theme.CARD_H so they sit level in the
README table, so the two scripts can run in either order.

Row kinds:
    ("host",)              the user@host banner plus its underline
    ("kv", key, value)     aligned key / value pair
    ("sec", title)         section heading
    ("bul", text)          bullet line
    ("gap",)               blank line
    ("projects",)          curated showcase from PUBLIC_WORK
    ("counters",)          public repo / star / follower tallies
    ("swatch",)            the colour blocks neofetch prints at the bottom
"""

import json
import os
import xml.sax.saxutils as xu

from theme import (
    AMBER, BLUE, BRIGHT, CARD_H, CYAN, DIM, GREEN, MONO, MUTED, PURPLE, RED,
    TEXT, fmt, glow_filter, window_chrome,
)

OUT = "profile-card.svg"
STATS = os.path.join("data", "profile-stats.json")
STATIC = os.environ.get("STATIC") == "1"

USER = "markockiadam"
HOST = "github"
TITLE = "neofetch"

# Curated showcase -- (display name, kind). Kept here so the nightly stats
# refresh cannot replace them with whatever was pushed last.
PUBLIC_WORK = [
    ("Yoink", "iOS app"),
    ("BookWorm", "iOS app"),
    ("TimeBox", ""),
    ("TerraCracovianum", "website"),
    ("Herkules", "iOS app"),
    ("Easel", "iOS app"),
    ("FlashBack", "iOS app"),
    ("Projekt: Budzet Polski", "website"),
]

# Dot colours for the project list (language colours are no longer shown).
PROJECT_DOTS = [GREEN, BLUE, AMBER, PURPLE, CYAN, RED, TEXT, MUTED]

ROWS = [
    ("host",),
    ("kv", "Now", "International Relations @ Cracow University of Economics"),
    ("kv", "Also", "Swift Student Challenge 2026 Winner"),
    ("kv", "Focus", "iOS apps + Polish civic tech"),
    ("kv", "Where", "Krakow, Poland"),
    ("kv", "Web", "markockiadam.com"),
    ("gap",),
    ("sec", "Currently"),
    ("bul", "Building tiny projects for Terra Cracovianum"),
    ("bul", "Learning SwiftUI in depth"),
    ("bul", "Looking for help distributing my mobile apps"),
    ("gap",),
    ("sec", "Public work"),
    ("projects",),
    ("gap",),
    ("counters",),
    ("swatch",),
]

FONT = 10.5
CHAR_W = FONT * 0.6
LINE_H = 16.0

PAD_X = 18.0
BODY_TOP = 44.0
PAD_BOTTOM = 16.0
KEY_COL = 8

WIDTH = 490.0

CYCLE = 16.0
LEAD_IN = 0.6
LINE_DUR = 0.26

SWATCHES = [RED, AMBER, GREEN, BLUE, PURPLE, CYAN, TEXT, DIM]


def load_stats():
    if not os.path.exists(STATS):
        return None
    with open(STATS, encoding="utf-8") as fh:
        return json.load(fh)


def wrap(text, limit):
    words, lines, cur = text.split(), [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if len(cand) > limit and cur:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def expand(stats):
    """Flatten ROWS into concrete render lines, wrapping long values."""
    avail = int((WIDTH - PAD_X * 2) / CHAR_W)
    out = []
    for row in ROWS:
        kind = row[0]
        if kind == "host":
            banner = f"{USER}@{HOST}"
            out.append(("host", banner))
            out.append(("rule", "-" * len(banner)))
        elif kind == "kv":
            _, key, val = row
            for i, chunk in enumerate(wrap(val, avail - KEY_COL - 2)):
                out.append(("kv", key if i == 0 else "", chunk))
        elif kind == "sec":
            out.append(("sec", row[1]))
        elif kind == "bul":
            for i, chunk in enumerate(wrap(row[1], avail - 4)):
                out.append(("bul", chunk, i == 0))
        elif kind == "gap":
            out.append(("gap",))
        elif kind == "projects":
            for idx, (name, label) in enumerate(PUBLIC_WORK):
                out.append(("project", name, label, idx))
        elif kind == "counters":
            if stats:
                out.append(("counters", stats))
        elif kind == "swatch":
            out.append(("swatch",))
    return out


def main():
    stats = load_stats()
    if stats is None:
        print(f"  note: {STATS} missing -- run fetch_profile_stats.py for live figures")

    lines = expand(stats)
    n = len(lines)
    natural = BODY_TOP + n * LINE_H + PAD_BOTTOM
    if natural > CARD_H:
        print(f"  note: content needs {int(natural)}px, above CARD_H={int(CARD_H)} "
              f"-- raise CARD_H in theme.py to keep the two cards level")
    height = max(natural, CARD_H)

    o = []
    a = o.append
    a(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(WIDTH)}" '
        f'height="{fmt(height)}" viewBox="0 0 {fmt(WIDTH)} {fmt(height)}" '
        f'role="img" aria-label="Profile info card for Adam Markocki">'
    )
    a("<title>markockiadam@github - neofetch</title>")

    a("<defs>")
    glow_filter(a, "cardglow", blur=1.1, strength=0.4)
    for i in range(n):
        t0 = (LEAD_IN + i * LINE_DUR) / CYCLE
        t1 = (LEAD_IN + (i + 1) * LINE_DUR) / CYCLE
        y = BODY_TOP + i * LINE_H - LINE_H
        a(f'<clipPath id="l{i}">')
        # Finished value in markup; SMIL overrides it from t=0 where it runs.
        a(f'<rect x="0" y="{fmt(y)}" height="{fmt(LINE_H * 1.6)}" width="{fmt(WIDTH)}">')
        if not STATIC:
            a(
                f'<animate attributeName="width" values="0;0;{fmt(WIDTH)};{fmt(WIDTH)}" '
                f'keyTimes="0;{fmt(t0)};{fmt(min(t1, 1))};1" dur="{fmt(CYCLE)}s" '
                f'repeatCount="indefinite"/>'
            )
        a("</rect></clipPath>")
    a("</defs>")

    window_chrome(a, WIDTH, height, TITLE)

    a(f'<g font-family="{MONO}" font-size="{fmt(FONT)}" xml:space="preserve">')

    key_x = PAD_X + KEY_COL * CHAR_W + CHAR_W

    for i, row in enumerate(lines):
        y = BODY_TOP + i * LINE_H
        clip = f' clip-path="url(#l{i})"'
        kind = row[0]

        if kind == "host":
            a(
                f'<text{clip} x="{fmt(PAD_X)}" y="{fmt(y)}" font-weight="bold" '
                f'filter="url(#cardglow)" fill="{GREEN}">{xu.escape(USER)}'
                f'<tspan fill="{DIM}">@</tspan>'
                f'<tspan fill="{BLUE}">{xu.escape(HOST)}</tspan></text>'
            )
        elif kind == "rule":
            a(f'<text{clip} x="{fmt(PAD_X)}" y="{fmt(y)}" fill="{DIM}">{row[1]}</text>')
        elif kind == "kv":
            _, key, val = row
            if key:
                a(
                    f'<text{clip} x="{fmt(PAD_X)}" y="{fmt(y)}" font-weight="bold" '
                    f'fill="{GREEN}">{xu.escape(key)}</text>'
                )
            a(
                f'<text{clip} x="{fmt(key_x)}" y="{fmt(y)}" fill="{TEXT}">'
                f"{xu.escape(val)}</text>"
            )
        elif kind == "sec":
            a(
                f'<text{clip} x="{fmt(PAD_X)}" y="{fmt(y)}" font-weight="bold" '
                f'fill="{AMBER}">{xu.escape(row[1])}</text>'
            )
        elif kind == "bul":
            marker = "-" if row[2] else " "
            a(
                f'<text{clip} x="{fmt(PAD_X)}" y="{fmt(y)}" fill="{DIM}">{marker}'
                f'<tspan fill="{MUTED}"> {xu.escape(row[1])}</tspan></text>'
            )
        elif kind == "project":
            name = xu.escape(row[1])
            label = row[2]
            colour = PROJECT_DOTS[row[3] % len(PROJECT_DOTS)]
            kind_tspan = (
                f'<tspan fill="{DIM}">  {xu.escape(label)}</tspan>' if label else ""
            )
            a(f'<g{clip}>')
            a(f'<circle cx="{fmt(PAD_X + 3)}" cy="{fmt(y - 3.5)}" r="3.5" fill="{colour}"/>')
            a(
                f'<text x="{fmt(PAD_X + 13)}" y="{fmt(y)}" fill="{TEXT}">{name}'
                f"{kind_tspan}</text>"
            )
            a("</g>")
        elif kind == "counters":
            st = row[1]
            bits = [
                (str(st["public_repos"]), "public repos"),
                (str(st["stars"]), "stars"),
                (str(st["followers"]), "followers"),
            ]
            parts = f'<tspan fill="{DIM}">  &#183;  </tspan>'.join(
                f'<tspan fill="{BRIGHT}">{v}</tspan><tspan fill="{DIM}"> {k}</tspan>'
                for v, k in bits
            )
            a(f'<text{clip} x="{fmt(PAD_X)}" y="{fmt(y)}">{parts}</text>')
        elif kind == "swatch":
            a(f'<g{clip}>')
            for j, col in enumerate(SWATCHES):
                a(
                    f'<rect x="{fmt(PAD_X + j * 22)}" y="{fmt(y - 9)}" width="18" '
                    f'height="10" rx="2" fill="{col}"/>'
                )
            a("</g>")

    a("</g>")
    a("</svg>")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("".join(o))
    print(f"wrote {OUT}  ({n} lines, {int(WIDTH)}x{int(height)}px)")


if __name__ == "__main__":
    main()
