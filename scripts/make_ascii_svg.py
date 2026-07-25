#!/usr/bin/env python3
"""Render data/portrait.png as a self-typing ASCII portrait in an SVG terminal.

Usage:
    python scripts/make_ascii_svg.py          # animated
    STATIC=1 python scripts/make_ascii_svg.py # everything visible, no SMIL

Writes avi-ascii.svg. The card pads out to theme.CARD_H so it sits level with
the info card in the README table.

Tuning knobs (all environment variables):
    COLS         characters across            (default 90)
    GAMMA        <1 brightens, >1 darkens     (default 1.1)
    CROP_BOTTOM  fraction of the portrait to  (default 0.72)
                 keep, measured from the top
    WHITE_FLOOR  luminance mapped to the      (default 246)
                 densest glyph
    BLACK_CEIL   luminance mapped to blank    (default 10)
"""

import os
import xml.sax.saxutils as xu

import numpy as np
from PIL import Image

from theme import (
    AMBER, BLUE, CARD_H, DIM, GREEN, GREEN_DEEP, GREEN_SOFT, MONO, TEXT, fmt,
    glow_filter, window_chrome,
)

SRC = os.path.join("data", "portrait.png")
OUT = "avi-ascii.svg"

COLS = int(os.environ.get("COLS", 90))
CROP_BOTTOM = float(os.environ.get("CROP_BOTTOM", 0.72))
GAMMA = float(os.environ.get("GAMMA", 1.1))
WHITE_FLOOR = float(os.environ.get("WHITE_FLOOR", 246))
BLACK_CEIL = float(os.environ.get("BLACK_CEIL", 10))
STATIC = os.environ.get("STATIC") == "1"

# Dark -> dense. Index 0 is blank, so the removed background stays empty.
RAMP = " .:-=+*#%@"

# Everything inside the subject silhouette gets at least this ramp index, so
# dark hair does not dissolve into the dark terminal background.
MIN_LEVEL_IN_MASK = 1
ALPHA_FLOOR = 24

FONT = 6.5                 # px
CHAR_W = FONT * 0.6        # nominal monospace advance
LINE_H = FONT * 1.0

# Monospace faces vary slightly in advance width (Menlo 0.602em, Consolas
# 0.55em). Leave a little slack so the art never overflows the card, and let
# the reveal clip run past the nominal edge so nothing is cut off early.
WIDTH_SLACK = 1.04

PAD_X = 16.0
BODY_TOP = 34.0            # below the title bar
BODY_GAP = 10.0            # between art and the prompt line
PROMPT_H = 26.0

CYCLE = 16.0               # seconds for one full loop
TYPE_FRAC = 0.42           # share of the cycle spent drawing the portrait
PROMPT_DUR = 1.1           # seconds to type the prompt line

PROMPT_PREFIX = "markockiadam@github:~$ whoami "
PROMPT_VALUE = "Adam Markocki"
TITLE = "portrait.sh"


def build_ascii():
    img = Image.open(SRC).convert("RGBA")

    # Crop to a bust so the face gets more of the character budget.
    if 0 < CROP_BOTTOM < 1:
        img = img.crop((0, 0, img.width, int(img.height * CROP_BOTTOM)))

    rows = max(1, round(COLS * (img.height / img.width) * (CHAR_W / LINE_H)))

    small = img.resize((COLS, rows), Image.LANCZOS)
    lum = np.array(small.convert("L"), dtype=np.float32)
    alpha = np.array(small.split()[-1])

    span = max(WHITE_FLOOR - BLACK_CEIL, 1.0)
    norm = np.clip((lum - BLACK_CEIL) / span, 0.0, 1.0) ** GAMMA
    level = np.rint(norm * (len(RAMP) - 1)).astype(int)

    inside = alpha > ALPHA_FLOOR
    level[inside] = np.maximum(level[inside], MIN_LEVEL_IN_MASK)
    level[~inside] = 0

    lines = ["".join(RAMP[v] for v in row) for row in level]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def keytimes(vals):
    return ";".join(fmt(v) for v in vals)


def main():
    lines = build_ascii()
    rows = len(lines)

    art_w = COLS * CHAR_W
    art_h = rows * LINE_H
    width = art_w * WIDTH_SLACK + PAD_X * 2
    natural = BODY_TOP + art_h + BODY_GAP + PROMPT_H
    if natural > CARD_H:
        print(f"  note: portrait needs {int(natural)}px, above CARD_H={int(CARD_H)} "
              f"-- raise CARD_H in theme.py to keep the two cards level")
    height = max(natural, CARD_H)

    type_total = CYCLE * TYPE_FRAC
    row_dur = type_total / rows
    eps = 0.0015                      # instant carriage return, in cycle fraction
    t_typed = type_total / CYCLE      # normalised time the art finishes
    t_prompt_end = t_typed + PROMPT_DUR / CYCLE

    # The prompt sits at the bottom of the card, so extra padding lands
    # between the art and the prompt rather than below everything.
    prompt_y = height - PROMPT_H + 15
    art_left = (width - art_w) / 2
    prompt_full = len(PROMPT_PREFIX) + len(PROMPT_VALUE)

    o = []
    a = o.append
    a(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(width)}" '
        f'height="{fmt(height)}" viewBox="0 0 {fmt(width)} {fmt(height)}" '
        f'role="img" aria-label="ASCII portrait of Adam Markocki">'
    )
    a("<title>Adam Markocki - ASCII portrait</title>")

    a("<defs>")
    a(
        f'<linearGradient id="phosphor" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{GREEN_SOFT}"/>'
        f'<stop offset="0.55" stop-color="{GREEN}"/>'
        f'<stop offset="1" stop-color="{GREEN_DEEP}"/>'
        "</linearGradient>"
    )
    glow_filter(a, "crt", blur=1.4, strength=0.5)
    # One clip per row: width animates 0 -> full during that row's slot.
    for i in range(rows):
        t0 = (i * row_dur) / CYCLE
        t1 = ((i + 1) * row_dur) / CYCLE
        y = BODY_TOP + i * LINE_H - LINE_H
        a(f'<clipPath id="r{i}">')
        # Markup carries the *finished* value; SMIL overrides it from t=0 when
        # it runs. A viewer that ignores SMIL therefore sees the completed art
        # rather than an empty card.
        a(f'<rect x="0" y="{fmt(y)}" height="{fmt(LINE_H * 2)}" width="{fmt(width)}">')
        if not STATIC:
            a(
                f'<animate attributeName="width" values="0;0;{fmt(width)};{fmt(width)}" '
                f'keyTimes="{keytimes([0, t0, t1, 1])}" dur="{fmt(CYCLE)}s" '
                f'repeatCount="indefinite"/>'
            )
        a("</rect></clipPath>")

    # Prompt line reveals character by character once the art is done.
    a('<clipPath id="prompt">')
    a(f'<rect x="0" y="{fmt(prompt_y - 14)}" height="22" width="{fmt(width)}">')
    if not STATIC:
        a(
            f'<animate attributeName="width" values="0;0;{fmt(width)};{fmt(width)}" '
            f'keyTimes="{keytimes([0, t_typed, t_prompt_end, 1])}" '
            f'dur="{fmt(CYCLE)}s" repeatCount="indefinite"/>'
        )
    a("</rect></clipPath>")
    a("</defs>")

    window_chrome(a, width, height, TITLE)

    # The portrait itself. Centred rather than left-aligned: the block then
    # stays balanced in the card whatever advance width the viewer's monospace
    # font actually has.
    a(
        f'<g font-family="{MONO}" font-size="{fmt(FONT)}" fill="url(#phosphor)" '
        f'xml:space="preserve" text-anchor="middle" filter="url(#crt)">'
    )
    for i, line in enumerate(lines):
        y = BODY_TOP + i * LINE_H
        a(
            f'<text clip-path="url(#r{i})" x="{fmt(width / 2)}" y="{fmt(y)}">'
            f"{xu.escape(line)}</text>"
        )
    a("</g>")

    # Roaming cursor: rides the end of whichever row is being drawn.
    if not STATIC:
        xs, xt, ys, yt = [], [], [], []
        for i in range(rows):
            t0 = (i * row_dur) / CYCLE
            t1 = ((i + 1) * row_dur) / CYCLE
            xs += [art_left, art_left + art_w]
            xt += [t0, max(t1 - eps, t0 + eps / 2)]
            ys += [BODY_TOP + i * LINE_H - LINE_H + 1.5] * 2
            yt += [t0, max(t1 - eps, t0 + eps / 2)]
        xs.append(art_left + art_w)
        xt.append(1)
        ys.append(ys[-1])
        yt.append(1)
        # Opacity 0 in markup: without SMIL this cursor has nowhere sensible
        # to sit, so it should simply not appear.
        a(
            f'<rect x="{fmt(art_left)}" y="{fmt(BODY_TOP)}" width="{fmt(CHAR_W)}" '
            f'height="{fmt(LINE_H)}" fill="{GREEN}" opacity="0">'
        )
        a(
            f'<animate attributeName="x" values="{";".join(fmt(v) for v in xs)}" '
            f'keyTimes="{keytimes(xt)}" dur="{fmt(CYCLE)}s" repeatCount="indefinite"/>'
        )
        a(
            f'<animate attributeName="y" values="{";".join(fmt(v) for v in ys)}" '
            f'keyTimes="{keytimes(yt)}" dur="{fmt(CYCLE)}s" calcMode="discrete" '
            f'repeatCount="indefinite"/>'
        )
        a(
            f'<animate attributeName="opacity" values="0.9;0.9;0;0" '
            f'keyTimes="{keytimes([0, t_typed, min(t_typed + eps, 1), 1])}" '
            f'dur="{fmt(CYCLE)}s" repeatCount="indefinite"/>'
        )
        a("</rect>")

    # Prompt line.
    a(
        f'<g font-family="{MONO}" font-size="{fmt(FONT + 2.5)}" xml:space="preserve" '
        f'clip-path="url(#prompt)">'
    )
    a(
        f'<text x="{fmt(PAD_X)}" y="{fmt(prompt_y)}" fill="{GREEN}">'
        f'markockiadam<tspan fill="{DIM}">@</tspan>'
        f'<tspan fill="{BLUE}">github</tspan>'
        f'<tspan fill="{DIM}">:~$ </tspan>'
        f'<tspan fill="{TEXT}">whoami </tspan>'
        f'<tspan fill="{AMBER}">{xu.escape(PROMPT_VALUE)}</tspan>'
        "</text>"
    )
    a("</g>")

    # Blinking cursor parked after the answer.
    cur_x = PAD_X + prompt_full * (FONT + 2.5) * 0.6 + 2
    a(
        f'<rect x="{fmt(cur_x)}" y="{fmt(prompt_y - (FONT + 2.5) + 1)}" '
        f'width="{fmt((FONT + 2.5) * 0.6)}" height="{fmt(FONT + 2.5)}" '
        f'fill="{AMBER}" opacity="1">'
    )
    if not STATIC:
        blink = [t_prompt_end + (1 - t_prompt_end) * f
                 for f in (0.14, 0.28, 0.43, 0.57, 0.72, 0.86, 1)]
        a(
            f'<animate attributeName="opacity" values="0;0;1;0;1;0;1;0;1" '
            f'keyTimes="{keytimes([0, t_prompt_end] + blink)}" '
            f'dur="{fmt(CYCLE)}s" calcMode="discrete" repeatCount="indefinite"/>'
        )
    a("</rect>")

    a("</svg>")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("".join(o))
    print(f"wrote {OUT}  ({COLS}x{rows} chars, {int(width)}x{int(height)}px)")


if __name__ == "__main__":
    main()
