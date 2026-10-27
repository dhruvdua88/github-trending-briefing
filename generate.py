#!/usr/bin/env python3
"""Rebuild index.html from github.com/trending + the GitHub API.

Standard library only, on purpose: the scheduled job should never fail because
a dependency drifted. Run with:

    python generate.py

Environment:
    GITHUB_TOKEN  optional; raises the API rate limit from 60 to 5,000 requests
                  per hour. The workflow supplies it automatically.

If anything fails, the previous index.html is left untouched and the script
exits non-zero, so the workflow fails loudly instead of publishing a blank page.
"""

from __future__ import annotations

import datetime
import html
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from content import CAT_HINTS, CAT_LABELS, CONTENT

ROOT = Path(__file__).resolve().parent
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

REPO_SLUG = os.environ.get("PAGES_REPO_SLUG", "dhruvdua88/github-trending-briefing")
REPO_URL = f"https://github.com/{REPO_SLUG}"

# key, heading, deck, trending URL param, delta wording, cards shown
BOARDS = [
    (
        "today",
        "Today",
        "Ranked by stars gained in the last 24 hours. This board rewards a launch, a viral post or a sudden wave of curiosity &mdash; the noisiest signal of the three, so read the use cases rather than the numbers.",
        "daily",
        "stars today",
        10,
    ),
    (
        "week",
        "This week",
        "Seven days of accumulation, which filters out the single-day spikes. These are the things developers keep coming back to, and where the more durable tools tend to sit, before anyone has forgotten them.",
        "weekly",
        "stars this week",
        12,
    ),
    (
        "month",
        "This month",
        "Thirty days, the slowest and most useful signal of the three. Anything here has survived a month of attention &mdash; and the enterprise and infrastructure work that never trends for a day surfaces on this board first.",
        "monthly",
        "stars this month",
        12,
    ),
]

TAG_SLUGS = {"agents", "design", "media", "money", "security", "dev", "office", "fun"}


# --------------------------------------------------------------------- fetching
def get(url: str, accept: str = "text/html") -> bytes:
    headers = {"User-Agent": UA, "Accept": accept}
    if TOKEN and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {TOKEN}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def num(text: str) -> int:
    found = re.search(r"([\d,]+)", text or "")
    return int(found.group(1).replace(",", "")) if found else 0


def fetch_board(since: str) -> list[dict]:
    raw = get(f"https://github.com/trending?since={since}").decode("utf-8", "replace")
    articles = re.findall(r'<article class="Box-row">(.*?)</article>', raw, re.S)
    if not articles:
        raise RuntimeError(f"github.com/trending?since={since} returned no rows (markup changed?)")

    rows = []
    for art in articles:
        name_m = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"', art)
        if not name_m:
            continue
        repo = name_m.group(1).strip("/")
        desc_m = re.search(r'<p class="[^"]*color-fg-muted[^"]*">\s*(.*?)\s*</p>', art, re.S)
        lang_m = re.search(r'itemprop="programmingLanguage">([^<]+)<', art)
        delta_m = re.search(r"([\d,]+)\s+stars\s+(?:today|this week|this month)", art)
        stars_m = re.search(
            r'href="/%s/stargazers"[^>]*>(?:.*?)</svg>\s*([\d,]+)' % re.escape(repo), art, re.S
        )
        rows.append(
            {
                "repo": repo,
                "desc": html.unescape(re.sub(r"<[^>]+>", "", desc_m.group(1))).strip()
                if desc_m
                else "",
                "lang": (lang_m.group(1).strip() if lang_m else ""),
                "stars_page": num(stars_m.group(1)) if stars_m else None,
                "delta": num(delta_m.group(1)) if delta_m else 0,
            }
        )
    return rows


def fetch_meta(repo: str) -> dict:
    try:
        payload = json.loads(
            get(f"https://api.github.com/repos/{repo}", "application/vnd.github+json")
        )
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return {}
    return {
        "stars": payload.get("stargazers_count"),
        "lang": payload.get("language"),
        "desc": payload.get("description") or "",
        "topics": payload.get("topics") or [],
    }


def guess_cat(desc: str, topics: list[str]) -> str:
    blob = " ".join([desc.lower(), " ".join(topics).lower()])
    for cat, hints in CAT_HINTS:
        if any(hint in blob for hint in hints):
            return cat
    return "agents"


# ---------------------------------------------------------------- hacker news
HN_ALGOLIA = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=60"
HN_FIREBASE = "https://hacker-news.firebaseio.com/v0"


def _story(raw: dict, object_id=None) -> dict | None:
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    if "is hiring" in title.lower():
        return None
    oid = object_id or raw.get("objectID")
    url = raw.get("url") or f"https://news.ycombinator.com/item?id={oid}"
    host = urllib.parse.urlparse(url).netloc.replace("www.", "")
    return {
        "title": title,
        "url": url,
        "thread": f"https://news.ycombinator.com/item?id={oid}",
        "host": host or "news.ycombinator.com",
        "points": int(raw.get("points") or 0),
        "comments": int(raw.get("num_comments") or raw.get("descendants") or 0),
    }


def fetch_hn(limit: int = 8) -> list[dict]:
    """Front page of Hacker News, points-descending. Empty list on failure."""
    stories: list[dict] = []
    try:
        data = json.loads(get(HN_ALGOLIA, "application/json"))
        stories = [x for x in (_story(h) for h in data.get("hits") or []) if x]
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
        print(f"  HN algolia failed ({exc}); trying firebase", file=sys.stderr)

    if not stories:
        try:
            ids = json.loads(get(f"{HN_FIREBASE}/topstories.json", "application/json"))[:40]
            for oid in ids:
                try:
                    item = json.loads(get(f"{HN_FIREBASE}/item/{oid}.json", "application/json"))
                except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
                    continue
                if not item or item.get("dead") or item.get("deleted"):
                    continue
                story = _story(item, object_id=oid)
                if story:
                    stories.append(story)
                if len(stories) >= 24:
                    break
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
            print(f"  HN firebase failed ({exc}); skipping the section", file=sys.stderr)
            return []

    seen, picked = set(), []
    for story in sorted(stories, key=lambda x: x["points"], reverse=True):
        key = story["url"].split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        picked.append(story)
        if len(picked) >= limit:
            break
    return picked


def hn_section(stories: list[dict]) -> str:
    if not stories:
        return ""
    rows = "\n      ".join(
        f'<li><a href="{esc(s["thread"])}" target="_blank" rel="noopener">{esc(s["title"])}</a>'
        f'<span class="hn-meta"><span class="hn-host">{esc(s["host"])}</span>'
        f'<span class="hn-pts">{fmt(s["points"])} points</span>'
        f'<span class="hn-cmt">{fmt(s["comments"])} comments</span></span></li>'
        for s in stories
    )
    return f"""
  <section class="hn" id="hn">
    <header class="section-head">
      <h2>Meanwhile, on Hacker News</h2>
      <p class="deck">The front page of Hacker News at build time, sorted by points. Headlines and links only &mdash; the titles are other people&rsquo;s words, so there is no commentary of mine layered on top.</p>
    </header>
    <ol class="hn-list">
      {rows}
    </ol>
    <p class="hn-note">Links open the Hacker News discussion. Points and comment counts are from the same run as the GitHub boards above, so everything on this page is one morning&rsquo;s snapshot.</p>
  </section>"""


# --------------------------------------------------------------------- rendering
def esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def shorten(text: str, limit: int = 120) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "\u2026"


def fmt(n: int | None) -> str:
    return f"{n:,}" if isinstance(n, int) else ""


def card(index: int, entry: dict, board: str, wording: str, also: str, first_board: str | None = None) -> str:
    repo = entry["repo"]
    curated = CONTENT.get(repo)
    cat = curated["cat"] if curated else guess_cat(entry["desc"], entry.get("topics", []))
    if cat not in TAG_SLUGS:
        cat = "agents"

    if first_board:
        what_html = (
            f'<p class="what repeated">Written up under {first_board} above &mdash; '
            f"still climbing, on a second timescale.</p>"
        )
    else:
        what_text = curated["what"] if curated else (
            shorten(entry["desc"], 240) or "No description on GitHub yet."
        )
        what_html = f'<p class="what">{esc(what_text)}</p>'
    if curated:
        use_html = f'<p class="use"><span class="use-label">Use it to</span> {esc(curated["use"])}</p>'
    else:
        use_html = (
            '<p class="use pending">No plain-English write-up yet &mdash; this one has just '
            "arrived on the board. The description above is GitHub's own.</p>"
        )

    total = entry.get("stars") or entry.get("stars_page")
    lang = entry.get("lang") or "Unknown"

    return f"""
      <li class="row" data-cat="{cat}">
        <div class="rank" aria-hidden="true">{index:02d}</div>
        <div class="body">
          <h3><a href="https://github.com/{esc(repo)}" target="_blank" rel="noopener">{esc(repo)}</a></h3>
          {what_html}
          {use_html}
          <p class="foot">
            <span class="tag tag-{cat}">{esc(CAT_LABELS[cat])}</span>
            {also}
          </p>
        </div>
        <div class="meta">
          <span class="delta">&plus;{fmt(entry["delta"])}</span>
          <span class="per">{esc(wording)}</span>
          <span class="total">{fmt(total)} total</span>
          <span class="lang">{esc(lang)}</span>
        </div>
      </li>"""


def section(board: str, title: str, deck: str, cards: list[str]) -> str:
    return f"""
  <section class="board-section" id="{board}">
    <header class="section-head">
      <h2>{title}</h2>
      <p class="deck">{deck}</p>
    </header>
    <ol class="board">
{''.join(cards)}
    </ol>
  </section>"""


def ticker_item(repo: str, delta: int, period: str) -> str:
    short = repo.split("/")[-1]
    return (
        f'<span class="tick"><b>{esc(short)}</b> '
        f'<span class="tick-num">&plus;{fmt(delta)}</span> '
        f'<span class="tick-per">{period}</span></span>'
    )


# -------------------------------------------------------------------------- main
def main() -> int:
    now = datetime.datetime.now(IST)
    boards: dict[str, list[dict]] = {}
    for key, _, _, since, _, _ in BOARDS:
        boards[key] = fetch_board(since)

    hn_stories = fetch_hn()
    print(f"  {len(hn_stories)} Hacker News stories", file=sys.stderr)

    # one API call per unique repository, regardless of how many boards it is on
    cache: dict[str, dict] = {}
    for key in boards:
        for entry in boards[key]:
            repo = entry["repo"]
            if repo not in cache:
                cache[repo] = fetch_meta(repo)
                print(f"  fetched {repo}", file=sys.stderr)
            entry.update({k: v for k, v in cache[repo].items() if k != "desc"})
            if not entry.get("desc"):
                entry["desc"] = cache[repo].get("desc", "")

    for key in boards:
        boards[key].sort(key=lambda e: e["delta"], reverse=True)

    memberships: dict[str, list[str]] = {}
    best_delta: dict[str, tuple[int, str]] = {}
    for key, _, _, _, wording, _ in BOARDS:
        for entry in boards[key]:
            memberships.setdefault(entry["repo"], []).append(key)
            if entry["delta"] > best_delta.get(entry["repo"], (0, ""))[0]:
                best_delta[entry["repo"]] = (entry["delta"], key)

    board_labels = {key: title for key, title, *_ in BOARDS}
    sections, shown, one_liners, first_seen = [], set(), [], {}

    for key, title, deck, _since, wording, limit in BOARDS:
        cards = []
        for idx, entry in enumerate(boards[key]):
            repo = entry["repo"]
            others = [board_labels[b] for b in memberships[repo] if b != key]
            also = (
                f'<span class="also">also on {" and ".join(o.lower() for o in others)}</span>'
                if others
                else ""
            )
            if idx < limit:
                first = first_seen.get(repo)
                cards.append(
                    card(
                        idx + 1,
                        entry,
                        key,
                        wording,
                        also,
                        board_labels[first] if first else None,
                    )
                )
                shown.add(repo)
                first_seen.setdefault(repo, key)
            elif repo not in shown:
                one_liners.append((repo, entry.get("desc") or "", key))
        sections.append(section(key, title, deck, cards))

    # de-duplicate the one-liner list, keeping the first board it appeared on
    seen, rest_rows = set(), []
    for repo, desc, key in one_liners:
        if repo in seen:
            continue
        seen.add(repo)
        rest_rows.append(
            f'<li><span class="r-name"><a href="https://github.com/{esc(repo)}" '
            f'target="_blank" rel="noopener">{esc(repo)}</a></span>'
            f"<span>{esc(shorten(desc))} <span class=\"r-board\">({board_labels[key].lower()})</span></span></li>"
        )

    ticker = "".join(
        ticker_item(e["repo"], e["delta"], short)
        for key, short in (("today", "24h"), ("week", "7d"), ("month", "30d"))
        for e in boards[key][:6]
    )
    ticker += "".join(
        '<span class="tick"><b>%s</b> <span class="tick-hn">%s points</span> '
        '<span class="tick-per">HN</span></span>'
        % (esc(story["title"][:34]), fmt(story["points"]))
        for story in hn_stories[:3]
    )

    day_top = max(boards["today"], key=lambda e: e["delta"])
    month_top = max(boards["month"], key=lambda e: e["delta"])

    page = (ROOT / "template.html").read_text(encoding="utf-8")
    replacements = {
        "{{TICKER}}": ticker,
        "{{CHIPS}}": "".join(
            f'<button class="chip" type="button" data-filter="{slug}">{esc(label)}</button>'
            for slug, label in CAT_LABELS.items()
        ),
        "{{BOARDS}}": "\n".join(sections),
        "{{HN_SECTION}}": hn_section(hn_stories),
        "{{REST}}": "\n      ".join(rest_rows),
        "{{N_CARDS}}": str(len(shown)),
        "{{N_ONE_LINERS}}": str(len(rest_rows)),
        "{{BIG_DAY}}": fmt(day_top["delta"]),
        "{{BIG_DAY_NAME}}": esc(day_top["repo"].split("/")[-1]),
        "{{BIG_MONTH}}": fmt(month_top["delta"]),
        "{{BIG_MONTH_NAME}}": esc(month_top["repo"].split("/")[-1]),
        "{{UPDATED_HUMAN}}": now.strftime("%d %B %Y, %H:%M IST").lstrip("0"),
        "{{UPDATED_SHORT}}": now.strftime("%d %B %Y").lstrip("0"),
        "{{UPDATED_ISO}}": now.replace(microsecond=0).isoformat(),
        "{{REPO_SLUG}}": REPO_SLUG,
        "{{REPO_URL}}": REPO_URL,
        "{{HN_COUNT}}": str(len(hn_stories)),
    }
    for token, value in replacements.items():
        page = page.replace(token, value)

    leftover = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if leftover:
        print(f"unreplaced template tokens: {set(leftover)}", file=sys.stderr)
        return 1

    target = ROOT / "index.html"
    previous = target.read_text(encoding="utf-8") if target.exists() else ""
    if previous == page:
        print("index.html unchanged")
        return 0

    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=ROOT, delete=False, suffix=".tmp"
    ) as fh:
        fh.write(page)
        tmp = Path(fh.name)
    tmp.replace(target)
    print(f"wrote {target} ({len(page):,} bytes): {len(shown)} cards, {len(rest_rows)} one-liners")
    return 0


if __name__ == "__main__":
    sys.exit(main())
