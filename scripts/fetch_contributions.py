#!/usr/bin/env python3
"""Scrape the public GitHub contribution calendar into data/contributions.json.

Usage:
    python scripts/fetch_contributions.py [username]

No authentication needed -- this reads the same public fragment the profile
page uses. Only requests and beautifulsoup4 are required, which is why the
GitHub Action installs just those two.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("GH_USERNAME", "MarkockiAdam")
URL = "https://github.com/users/{}/contributions"
OUT = os.path.join("data", "contributions.json")
TIMEOUT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; profile-art/1.0; +https://github.com/{})",
    "Accept": "text/html",
    "X-Requested-With": "XMLHttpRequest",
}

COUNT_RE = re.compile(r"^\s*(\d+)\s+contribution", re.I)


def fetch(username):
    headers = dict(HEADERS)
    headers["User-Agent"] = headers["User-Agent"].format(username)
    resp = requests.get(URL.format(username), headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def parse(html):
    soup = BeautifulSoup(html, "html.parser")

    # Counts only exist in the tooltips, which point back at each cell by id.
    counts = {}
    for tip in soup.find_all("tool-tip"):
        target = tip.get("for")
        if not target:
            continue
        match = COUNT_RE.match(tip.get_text(strip=True))
        counts[target] = int(match.group(1)) if match else 0

    days = []
    for td in soup.select("td.ContributionCalendar-day"):
        date = td.get("data-date")
        if not date:
            continue
        days.append(
            {
                "date": date,
                "level": int(td.get("data-level") or 0),
                "count": counts.get(td.get("id"), 0),
            }
        )

    if not days:
        raise SystemExit("error: no contribution cells found -- did the page markup change?")

    days.sort(key=lambda d: d["date"])
    return days


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else USERNAME
    print(f"fetching contributions for {username}")

    days = parse(fetch(username))
    payload = {
        "username": username,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"from": days[0]["date"], "to": days[-1]["date"]},
        "total": sum(d["count"] for d in days),
        "days": days,
    }

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")

    print(
        f"wrote {OUT}  ({len(days)} days, {payload['total']} contributions, "
        f"{payload['range']['from']} -> {payload['range']['to']})"
    )


if __name__ == "__main__":
    main()
