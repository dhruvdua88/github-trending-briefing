#!/usr/bin/env python3
"""Check the built page against the payloads saved during the build.

This is the external check for the pipeline, run by the workflow before anything
is deployed. It does not trust generate.py's own output: it re-reads the gzipped
payloads from archive/raw/<date>/, re-parses them, and compares the numbers that
ended up on the page.

Checks
  1. build.json exists and is coherent (date, status, three boards, HN count).
  2. Each archived payload still matches the SHA-256 recorded in build.json.
  3. The #1 repository on the daily board carries the same star delta on the page
     as the raw board HTML says it does.
  4. The snapshot is fresh (under 8 hours old) — a stale build must not deploy.
  5. The page's own status marker agrees with build.json (banner present iff
     the build was degraded).

Exit code 0 = verified, 1 = anything above failed.
"""

from __future__ import annotations

import datetime
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

import generate as g

ROOT = Path(__file__).resolve().parent
MAX_AGE_HOURS = 8
failures: list[str] = []
notes: list[str] = []


def check(condition: bool, message: str) -> None:
    if condition:
        notes.append(f"ok   {message}")
    else:
        failures.append(message)


def main() -> int:
    build_path = ROOT / "build.json"
    page_path = ROOT / "index.html"

    check(build_path.exists(), "build.json exists")
    check(page_path.exists(), "index.html exists")
    if failures:
        return report()

    build = json.loads(build_path.read_text(encoding="utf-8"))
    page = page_path.read_text(encoding="utf-8")

    # 1. coherence
    for board in ("today", "week", "month"):
        check(build.get("boards", {}).get(board, 0) > 0, f"board '{board}' had rows at build time")
    check(build.get("status") in {"ok", "degraded"}, "status is 'ok' or 'degraded'")

    # 2. payload integrity
    for name, record in build.get("sources", {}).items():
        stored = ROOT / record["stored"]
        check(stored.exists(), f"{name}: archived payload present")
        if not stored.exists():
            continue
        raw = gzip.decompress(stored.read_bytes())
        digest = hashlib.sha256(raw).hexdigest()
        check(
            digest == record["sha256"],
            f"{name}: sha256 matches build.json ({digest[:12]}…)",
        )

    # 3. recompute one delta from the archived board and find it on the page
    date = build["date"]
    daily_raw = gzip.decompress((ROOT / f"archive/raw/{date}/trending-daily.html.gz").read_bytes())
    rows = g.parse_board(daily_raw)
    check(bool(rows), "archived daily board parses back into rows")
    if rows:
        top = max(rows, key=lambda r: r["delta"])
        anchor = page.find(f'href="https://github.com/{top["repo"]}"')
        check(anchor != -1, f"#1 daily repo {top['repo']} appears on the page")
        if anchor != -1:
            window = page[anchor : anchor + 1600]
            match = re.search(r"&plus;([\d,]+)", window)
            shown = int(match.group(1).replace(",", "")) if match else None
            check(
                shown == top["delta"],
                f"delta for {top['repo']} recomputed from archive: page {shown} vs raw {top['delta']}",
            )
        notes.append(f"info #1 daily = {top['repo']} (+{top['delta']:,})")

    # 4. freshness
    generated = datetime.datetime.fromisoformat(build["generated_at"])
    age = datetime.datetime.now(generated.tzinfo) - generated
    check(
        age < datetime.timedelta(hours=MAX_AGE_HOURS),
        f"snapshot is fresh ({age.total_seconds() / 3600:.1f}h old, limit {MAX_AGE_HOURS}h)",
    )

    # 5. page agrees with build status
    banner = 'class="banner"' in page
    if build["status"] == "degraded":
        check(banner, "degraded build shows the banner")
        check(
            all(name in page for name in build.get("degraded", [])),
            "every degraded source is named on the page",
        )
    else:
        check(not banner, "clean build shows no banner")
        check(
            build.get("hacker_news", {}).get("count", 0) > 0,
            f"Hacker News contributed {build.get('hacker_news', {}).get('count', 0)} stories",
        )

    check(not re.findall(r"\{\{[A-Z_]+\}\}", page), "no unreplaced template tokens")

    return report()


def report() -> int:
    for line in notes:
        print(line)
    for line in failures:
        print(f"FAIL {line}")
    if failures:
        print(f"\n{len(failures)} check(s) failed — not deploying")
        return 1
    print(f"\nall {len(notes)} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
