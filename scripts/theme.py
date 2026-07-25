"""Shared palette and helpers for the three SVG terminals.

Keeping this in one place means a colour change lands on the portrait, the
info card and the heatmap at once, instead of drifting between them.
"""

# Surfaces
BG = "#0b0f14"
CHROME = "#12181f"
CHROME_EDGE = "#1c2530"
BORDER = "#222c38"

# Text
DIM = "#4a5563"
MUTED = "#8b949e"
TEXT = "#c9d1d9"
BRIGHT = "#e6edf3"

# Accents
GREEN = "#39d353"
GREEN_SOFT = "#7ee787"
GREEN_DEEP = "#1f9e4a"
BLUE = "#58a6ff"
AMBER = "#f0b429"
PURPLE = "#bc8cff"
CYAN = "#39c5cf"
RED = "#ff5f57"

# Contribution levels, darkest to brightest.
LEVELS = ["#151b23", "#0e4429", "#006d32", "#26a641", "#39d353"]
LEVEL_EMPTY_STROKE = "#20272f"

TRAFFIC_LIGHTS = ("#ff5f57", "#febc2e", "#28c840")

MONO = ('ui-monospace, SFMono-Regular, Menlo, Consolas, '
        '&quot;DejaVu Sans Mono&quot;, monospace')

# The portrait and the info card sit side by side in the README, so both pad
# out to this height rather than each guessing at the other's. Raise it if
# either one's content outgrows it -- the scripts warn when that happens.
CARD_H = 412.0

# Language colours, matching GitHub's own so they read as familiar.
LANG_COLORS = {
    "Swift": "#F05138",
    "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A",
    "Python": "#3572A5",
    "HTML": "#E34C26",
    "CSS": "#663399",
    "Shell": "#89E051",
    "C": "#555555",
    "C++": "#F34B7D",
    "Objective-C": "#438EFF",
    "Ruby": "#701516",
    "Go": "#00ADD8",
    "Rust": "#DEA584",
    "Java": "#B07219",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
    "Vue": "#41B883",
    "SCSS": "#C6538C",
    "Makefile": "#427819",
}
FALLBACK_LANG_COLOR = "#6e7681"


def fmt(x):
    """Trim floats to something compact but still precise enough for SVG."""
    return f"{x:.4g}"


def window_chrome(a, width, height, title, radius=10.0):
    """Emit the rounded terminal window: body, title bar, lights and title.

    `a` is an append callable (usually `list.append`).
    """
    a(
        f'<rect x="0.5" y="0.5" width="{fmt(width - 1)}" height="{fmt(height - 1)}" '
        f'rx="{fmt(radius)}" fill="{BG}" stroke="{BORDER}"/>'
    )
    a(
        f'<path d="M0.5 {fmt(radius + 0.5)}a{fmt(radius)} {fmt(radius)} 0 0 1 '
        f'{fmt(radius)}-{fmt(radius)}h{fmt(width - 2 * radius - 1)}'
        f'a{fmt(radius)} {fmt(radius)} 0 0 1 {fmt(radius)} {fmt(radius)}V24H0.5z" '
        f'fill="{CHROME}"/>'
    )
    a(f'<line x1="0.5" y1="24" x2="{fmt(width - 0.5)}" y2="24" stroke="{CHROME_EDGE}"/>')
    for i, col in enumerate(TRAFFIC_LIGHTS):
        a(f'<circle cx="{fmt(16 + i * 14)}" cy="12.5" r="4.5" fill="{col}"/>')
    a(
        f'<text x="{fmt(width / 2)}" y="16" text-anchor="middle" font-family="{MONO}" '
        f'font-size="9" fill="{DIM}">{title}</text>'
    )


def glow_filter(a, ident="glow", blur=1.6, strength=0.55):
    """A soft phosphor bloom, the way a CRT smears bright text slightly."""
    a(
        f'<filter id="{ident}" x="-12%" y="-12%" width="124%" height="124%">'
        f'<feGaussianBlur stdDeviation="{fmt(blur)}" result="b"/>'
        f'<feComponentTransfer in="b" result="d">'
        f'<feFuncA type="linear" slope="{fmt(strength)}"/>'
        f"</feComponentTransfer>"
        f'<feMerge><feMergeNode in="d"/><feMergeNode in="SourceGraphic"/></feMerge>'
        f"</filter>"
    )
