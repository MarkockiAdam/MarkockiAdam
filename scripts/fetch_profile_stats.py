#!/usr/bin/env python3
"""Collect public profile stats into data/profile-stats.json.

Usage:
    python scripts/fetch_profile_stats.py [username]

Feeds the info card real numbers and real project names instead of hardcoded
ones. Set GITHUB_TOKEN to lift the rate limit (the workflow passes the
built-in one).

A note on languages: this reports each repo's *primary* language and counts
repos, not bytes. Byte totals are badly skewed here -- one vendored fork
outweighs a dozen hand-written projects, while weighting every repo equally
lets a pile of one-page privacy-policy sites dominate instead. Counting repos
by primary language is the same measure GitHub itself shows, and it needs no
extra API calls.
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests

USERNAME = os.environ.get("GH_USERNAME", "MarkockiAdam")
API = "https://api.github.com"
OUT = os.path.join("data", "profile-stats.json")
TIMEOUT = 30
TOP_LANGS = 5
RECENT = 5

# Repos that exist only to host a privacy policy or terms page. They are real
# but they say nothing about the work, so they stay out of the project list.
BOILERPLATE = ("-privacy", "privacy-", "-legal", "-policy", "policy-")


def session():
    s = requests.Session()
    s.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "profile-art/1.0",
        }
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


def get(s, url, **kw):
    r = s.get(url, timeout=TIMEOUT, **kw)
    if r.status_code == 403 and "rate limit" in r.text.lower():
        raise SystemExit("error: GitHub rate limit hit. Set GITHUB_TOKEN and try again.")
    r.raise_for_status()
    return r.json()


def repos(s, username):
    out, page = [], 1
    while True:
        batch = get(
            s,
            f"{API}/users/{username}/repos",
            params={"per_page": 100, "page": page, "type": "owner", "sort": "updated"},
        )
        out.extend(batch)
        if len(batch) < 100:
            return out
        page += 1


def is_boilerplate(name):
    low = name.lower()
    return any(token in low for token in BOILERPLATE)


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else USERNAME
    s = session()

    print(f"fetching profile stats for {username}")
    user = get(s, f"{API}/users/{username}")
    owned = [r for r in repos(s, username) if not r["fork"] and not r["archived"]]

    counts = {}
    for repo in owned:
        if repo["language"]:
            counts[repo["language"]] = counts.get(repo["language"], 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_LANGS]

    # The profile repo itself is not a project worth listing on the profile.
    showcase = [
        r for r in owned
        if not is_boilerplate(r["name"]) and r["name"].lower() != username.lower()
    ]

    payload = {
        "username": username,
        "name": user.get("name"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "public_repos": len(owned),
        "followers": user.get("followers", 0),
        "stars": sum(r["stargazers_count"] for r in owned),
        "languages": [{"name": n, "repos": c} for n, c in ranked],
        "recent": [
            {
                "name": r["name"],
                "language": r["language"],
                "description": (r["description"] or "").strip(),
                "stars": r["stargazers_count"],
            }
            for r in showcase[:RECENT]
        ],
    }

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")

    print(f"wrote {OUT}  ({len(owned)} public repos, {payload['stars']} stars)")
    print("  languages: " + ", ".join(f"{n} x{c}" for n, c in ranked))
    print("  recent:    " + ", ".join(r["name"] for r in payload["recent"]))


if __name__ == "__main__":
    main()
