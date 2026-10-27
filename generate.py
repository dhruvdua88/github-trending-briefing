#!/usr/bin/env python3
"""Rebuild index.html from github.com/trending, the GitHub API and Hacker News.

Design rules this file follows:

1. Every number on the page comes from a payload saved in the same run. The
   payloads are gzipped into archive/raw/<date>/ and hashed into build.json, so
   any figure can be re-derived afterwards by verify.py.
2. A missing GitHub board is fatal: the page would be meaningless, so the run
   exits non-zero and the last good deploy stays live.
3. A missing Hacker News feed is not fatal: the page publishes with a visible
   "degraded" banner instead of pretending the feed is empty.
4. Nothing is invented. A repository without a written-up use case gets its
   README quoted and is labelled as such.

Environment:
    GITHUB_TOKEN  optional but recommended (60 -> 5,000 API requests/hour).
"""

from __future__ import annotations

import datetime
import gzip
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from content import CAT_HINTS, CAT_LABELS, CONTENT

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "archive"
RAW = ARCHIVE / "raw"
KEEP_RAW_DAYS = 14

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
REPO_SLUG = os.environ.get("PAGES_REPO_SLUG", "dhruvdua88/github-trending-briefing")
REPO_URL = f"https://github.com/{REPO_SLUG}"

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
        "Seven days of accumulation, which filters out the single-day spikes. These are the things developers keep coming back to, before anyone has forgotten them.",
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
BOARD_TITLES = {key: title for key, title, *_ in BOARDS}

TAG_SLUGS = {"agents", "design", "media", "money", "security", "dev", "office", "fun"}
HN_WINDOW_HOURS = 24


# --------------------------------------------------------------------- plumbing
def http_get(url: str, accept: str = "text/html") -> bytes:
    headers = {"User-Agent": UA, "Accept": accept}
    if TOKEN and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {TOKEN}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def save_raw(date_dir: Path, name: str, url: str, payload: bytes) -> dict:
    """Gzip a payload into the archive and return its provenance record."""
    date_dir.mkdir(parents=True, exist_ok=True)
    target = date_dir / f"{name}.gz"
    target.write_bytes(gzip.compress(payload, compresslevel=9))
    return {
        "url": url,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "stored": str(target.relative_to(ROOT)),
    }


def num(text: str) -> int:
    found = re.search(r"([\d,]+)", text or "")
    return int(found.group(1).replace(",", "")) if found else 0


def fmt(value) -> str:
    return f"{value:,}" if isinstance(value, int) else ""


def esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def shorten(text: str, limit: int = 120) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "\u2026"


def ago(when: datetime.datetime) -> str:
    delta = datetime.datetime.now(datetime.timezone.utc) - when
    hours = delta.total_seconds() / 3600
    if hours < 1:
        return "under an hour ago"
    if hours < 24:
        return f"{int(hours)}h ago"
    days = int(hours // 24)
    if days < 45:
        return f"{days} days ago"
    return f"{int(days // 30)} months ago"


# ------------------------------------------------------------------- github data
def fetch_board(since: str) -> tuple[list[dict], bytes]:
    url = f"https://github.com/trending?since={since}"
    raw = http_get(url)
    rows = parse_board(raw)
    if not rows:
        raise RuntimeError(f"{url} returned no rows — GitHub markup has changed")
    return rows, raw


def parse_board(raw: bytes) -> list[dict]:
    markup = raw.decode("utf-8", "replace")
    rows = []
    for article in re.findall(r'<article class="Box-row">(.*?)</article>', markup, re.S):
        name = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"', article)
        if not name:
            continue
        repo = name.group(1).strip("/")
        desc = re.search(r'<p class="[^"]*color-fg-muted[^"]*">\s*(.*?)\s*</p>', article, re.S)
        lang = re.search(r'itemprop="programmingLanguage">([^<]+)<', article)
        delta = re.search(r"([\d,]+)\s+stars\s+(?:today|this week|this month)", article)
        stars = re.search(
            r'href="/%s/stargazers"[^>]*>(?:.*?)</svg>\s*([\d,]+)' % re.escape(repo), article, re.S
        )
        rows.append(
            {
                "repo": repo,
                "desc": html.unescape(re.sub(r"<[^>]+>", "", desc.group(1))).strip()
                if desc
                else "",
                "lang": lang.group(1).strip() if lang else "",
                "stars_page": num(stars.group(1)) if stars else None,
                "delta": num(delta.group(1)) if delta else 0,
            }
        )
    return rows


def fetch_meta(repo: str) -> dict:
    try:
        payload = json.loads(
            http_get(f"https://api.github.com/repos/{repo}", "application/vnd.github+json")
        )
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return {}
    return {
        "stars": payload.get("stargazers_count"),
        "forks": payload.get("forks_count"),
        "lang": payload.get("language"),
        "desc": payload.get("description") or "",
        "topics": payload.get("topics") or [],
        "created_at": payload.get("created_at"),
        "pushed_at": payload.get("pushed_at"),
    }


def fetch_readme(repo: str) -> str:
    """First meaningful prose paragraph from the repo's README, or ''."""
    try:
        text = http_get(
            f"https://api.github.com/repos/{repo}/readme", "application/vnd.github.raw"
        ).decode("utf-8", "replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return ""
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block or block[0] in "#`|<![>*~":
            continue
        block = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", block)
        block = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", block)
        block = re.sub(r"[*_`]", "", block)
        block = " ".join(block.split())
        if len(block) > 60:
            return shorten(block, 200)
    return ""


# ---------------------------------------------------------------- hacker news
HN_FIREBASE = "https://hacker-news.firebaseio.com/v0"
HN_ALGOLIA = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=60"


def hn_from_firebase(limit: int) -> list[dict]:
    ids = json.loads(http_get(f"{HN_FIREBASE}/topstories.json", "application/json"))[:70]
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=HN_WINDOW_HOURS)
    stories = []
    for oid in ids:
        try:
            item = json.loads(http_get(f"{HN_FIREBASE}/item/{oid}.json", "application/json"))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
            continue
        if not item or item.get("dead") or item.get("deleted") or item.get("type") != "story":
            continue
        posted = datetime.datetime.fromtimestamp(item.get("time", 0), datetime.timezone.utc)
        if posted < cutoff:
            continue
        title = (item.get("title") or "").strip()
        if not title or "is hiring" in title.lower():
            continue
        url = item.get("url") or f"https://news.ycombinator.com/item?id={oid}"
        stories.append(
            {
                "title": title,
                "url": url,
                "thread": f"https://news.ycombinator.com/item?id={oid}",
                "host": urllib.parse.urlparse(url).netloc.replace("www.", "")
                or "news.ycombinator.com",
                "points": int(item.get("score") or 0),
                "comments": int(item.get("descendants") or 0),
                "posted": posted,
            }
        )
        if len(stories) >= 60:
            break
    return pick_hn(stories, limit)


def hn_from_algolia(limit: int) -> list[dict]:
    data = json.loads(http_get(HN_ALGOLIA, "application/json"))
    stories = []
    for hit in data.get("hits") or []:
        title = (hit.get("title") or "").strip()
        if not title or "is hiring" in title.lower():
            continue
        oid = hit.get("objectID")
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={oid}"
        stories.append(
            {
                "title": title,
                "url": url,
                "thread": f"https://news.ycombinator.com/item?id={oid}",
                "host": urllib.parse.urlparse(url).netloc.replace("www.", "")
                or "news.ycombinator.com",
                "points": int(hit.get("points") or 0),
                "comments": int(hit.get("num_comments") or 0),
                "posted": datetime.datetime.fromtimestamp(
                    hit.get("created_at_i") or 0, datetime.timezone.utc
                ),
            }
        )
    return pick_hn(stories, limit)


def pick_hn(stories: list[dict], limit: int) -> list[dict]:
    seen, picked = set(), []
    for story in sorted(stories, key=lambda s: s["points"], reverse=True):
        key = story["url"].split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        picked.append(story)
        if len(picked) >= limit:
            break
    return picked


def fetch_hn(limit: int = 8) -> tuple[list[dict], bytes, str, str]:
    """(stories, archived payload, source name, url used)."""
    for name, fn, url in (
        ("firebase", hn_from_firebase, f"{HN_FIREBASE}/topstories.json"),
        ("algolia", hn_from_algolia, HN_ALGOLIA),
    ):
        try:
            stories = fn(limit)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
            print(f"  HN {name} failed: {exc}", file=sys.stderr)
            continue
        if not stories:
            print(f"  HN {name}: nothing inside the {HN_WINDOW_HOURS}h window", file=sys.stderr)
            continue
        payload = json.dumps(
            [
                {
                    **{k: v for k, v in s.items() if k != "posted"},
                    "posted": s["posted"].isoformat(),
                }
                for s in stories
            ],
            ensure_ascii=False,
            indent=1,
        ).encode()
        return stories, payload, name, url
    return [], b"[]", "none", HN_FIREBASE


# ---------------------------------------------------------------- repo evidence
def evidence(meta: dict) -> tuple[str, list[str]]:
    """(a small human line about the repo, warning flags worth printing)."""
    parts, flags = [], []
    stars = meta.get("stars")

    if meta.get("created_at"):
        try:
            born = datetime.datetime.fromisoformat(meta["created_at"].replace("Z", "+00:00"))
            age_days = max(
                (datetime.datetime.now(datetime.timezone.utc) - born).days, 30
            )
            if stars:
                per_day = round(stars / age_days)
                parts.append(f"{fmt(per_day)} stars/day since {born:%b %Y}")
                if per_day >= 1000 and stars >= 50_000:
                    flags.append(
                        f"climb is faster than a codebase usually earns ({fmt(per_day)}/day)"
                    )
        except ValueError:
            pass

    if meta.get("pushed_at"):
        try:
            last = datetime.datetime.fromisoformat(meta["pushed_at"].replace("Z", "+00:00"))
            parts.append(f"last commit {ago(last)}")
            if (datetime.datetime.now(datetime.timezone.utc) - last).days > 180:
                flags.append("no commits in over six months")
        except ValueError:
            pass

    return " &middot; ".join(parts), flags


def guess_cat(desc: str, topics: list[str]) -> str:
    blob = " ".join([(desc or "").lower(), " ".join(topics or []).lower()])
    for cat, hints in CAT_HINTS:
        if any(hint in blob for hint in hints):
            return cat
    return "agents"


# --------------------------------------------------------------------- rendering
def card(index: int, entry: dict, wording: str, also: str, first_board: str | None) -> str:
    repo = entry["repo"]
    curated = CONTENT.get(repo)
    cat = curated["cat"] if curated else guess_cat(entry.get("desc", ""), entry.get("topics", []))
    if cat not in TAG_SLUGS:
        cat = "agents"

    if first_board:
        what_html = (
            f'<p class="what repeated">Written up under {first_board} above &mdash; '
            "still climbing, on a second timescale.</p>"
        )
    elif curated:
        what_html = f'<p class="what">{esc(curated["what"])}</p>'
    elif entry.get("readme"):
        what_html = (
            f'<p class="what">&ldquo;{esc(entry["readme"])}&rdquo; '
            '<span class="src">quoted from its README</span></p>'
        )
    else:
        what_html = (
            f'<p class="what">{esc(shorten(entry.get("desc") or "No description on GitHub yet.", 240))}</p>'
        )

    if curated:
        use_html = f'<p class="use"><span class="use-label">Use it to</span> {esc(curated["use"])}</p>'
    else:
        use_html = (
            '<p class="use pending">No plain-English write-up yet &mdash; this one has just '
            "arrived on the board. The words above are GitHub&rsquo;s, not mine.</p>"
        )

    line, flags = evidence(entry)
    evidence_html = f'<p class="evidence">{line}</p>' if line else ""
    flags_html = "".join(f'<span class="flag">{flag}</span>' for flag in flags)

    total = entry.get("stars") or entry.get("stars_page")
    lang = entry.get("lang") or "Unknown"

    return f"""
      <li class="row" data-cat="{cat}">
        <div class="rank" aria-hidden="true">{index:02d}</div>
        <div class="body">
          <h3><a href="https://github.com/{esc(repo)}" target="_blank" rel="noopener">{esc(repo)}</a></h3>
          {what_html}
          {use_html}
          {evidence_html}
          <p class="foot">
            <span class="tag tag-{cat}">{esc(CAT_LABELS[cat])}</span>
            {also}
            {flags_html}
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


def hn_section(stories: list[dict], source: str) -> str:
    if not stories:
        return """
  <section class="hn" id="hn">
    <header class="section-head">
      <h2>Meanwhile, on Hacker News</h2>
      <p class="deck">Unavailable at build time. Both the Firebase and Algolia endpoints were
      tried; neither returned stories inside the window. The GitHub boards above are unaffected.</p>
    </header>
  </section>"""

    rows = []
    for story in stories:
        age = ago(story["posted"]) if isinstance(story["posted"], datetime.datetime) else ""
        rows.append(
            f'<li><a href="{esc(story["thread"])}" target="_blank" rel="noopener">{esc(story["title"])}</a>'
            f'<span class="hn-meta"><span class="hn-host">{esc(story["host"])}</span>'
            f'<span class="hn-pts">{fmt(story["points"])} points</span>'
            f'<span class="hn-cmt">{fmt(story["comments"])} comments</span>'
            f'<span class="hn-age">{esc(age)}</span></span></li>'
        )
    window = (
        "the last 24 hours, by points"
        if source == "firebase"
        else "the current front page, by points"
    )
    return f"""
  <section class="hn" id="hn">
    <header class="section-head">
      <h2>Meanwhile, on Hacker News</h2>
      <p class="deck">Stories from {window}. Headlines and links only &mdash; the titles are other
      people&rsquo;s words, so there is no commentary of mine layered on top.</p>
    </header>
    <ol class="hn-list">
      {''.join(rows)}
    </ol>
    <p class="hn-note">Each link opens the Hacker News discussion. Points, comment counts and
    posting times come from the same run as the GitHub boards above, so everything here is one
    morning&rsquo;s snapshot &mdash; not a live feed.</p>
  </section>"""


def status_banner(degraded: list[str]) -> str:
    if not degraded:
        return ""
    return (
        '<div class="banner" role="status"><strong>Degraded build.</strong> '
        f"These sources did not answer this morning: {esc(', '.join(degraded))}. "
        "Everything shown is real, but part of the morning is missing. The next scheduled run "
        "tries again, and yesterday&rsquo;s page stays in the archive untouched.</div>"
    )


def ticker_item(repo: str, delta: int, period: str) -> str:
    return (
        f'<span class="tick"><b>{esc(repo.split("/")[-1])}</b> '
        f'<span class="tick-num">&plus;{fmt(delta)}</span> '
        f'<span class="tick-per">{period}</span></span>'
    )


def archive_index(entries: list[tuple[str, str, str]]) -> str:
    """Standalone index of the dated snapshots."""
    rows = "\n".join(
        f'<li><a href="{date}.html">{date}</a><span>{esc(top)}</span></li>'
        for date, top, _ in entries
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Archive — What's hot on GitHub</title>
<style>
body{{margin:0;background:#e8ede3;color:#10201a;font:400 1.05rem/1.6 Georgia,serif;
background-image:radial-gradient(rgba(16,32,26,.055) 1px,transparent 1px);background-size:5px 5px}}
.wrap{{max-width:760px;margin:0 auto;padding:3rem 1.6rem 4rem}}
h1{{font-family:"Bricolage Grotesque","Helvetica Neue",Arial,sans-serif;font-weight:800;
font-size:clamp(2rem,6vw,3rem);letter-spacing:-.03em;line-height:1;margin:0 0 .5rem}}
p.lede{{color:#3d4d44;margin:0 0 2rem;max-width:52ch}}
ul{{list-style:none;margin:0;padding:0;border-top:2px solid #10201a}}
li{{display:flex;gap:1.2rem;justify-content:space-between;align-items:baseline;
padding:.8rem 0;border-bottom:1px solid rgba(16,32,26,.18);
font-family:"Bricolage Grotesque",Arial,sans-serif;font-size:.95rem}}
li a{{text-decoration:none;font-weight:600;font-variant-numeric:tabular-nums}}
li a:hover{{text-decoration:underline}}
li span{{color:#5a6a5f;font-size:.85rem;text-align:right}}
.back{{display:inline-block;margin-top:2rem;font-family:"Bricolage Grotesque",Arial,sans-serif;
font-size:.85rem;text-decoration:none;border-bottom:2px solid #d9451f}}
</style></head>
<body><div class="wrap">
<h1>Archive</h1>
<p class="lede">One page per morning, newest first. Each file is the briefing exactly as it was
published that day &mdash; numbers are not quietly corrected afterwards.</p>
<ul>
{rows}
</ul>
<a class="back" href="../index.html">Today&rsquo;s briefing</a>
</div></body></html>
"""


def prune_raw(today: datetime.date) -> list[str]:
    removed = []
    if not RAW.exists():
        return removed
    for child in sorted(RAW.iterdir()):
        try:
            stamp = datetime.date.fromisoformat(child.name)
        except ValueError:
            continue
        if (today - stamp).days > KEEP_RAW_DAYS:
            for item in child.iterdir():
                item.unlink()
            child.rmdir()
            removed.append(child.name)
    return removed


# -------------------------------------------------------------------------- main
def main() -> int:
    now = datetime.datetime.now(IST)
    today = now.date()
    date_dir = RAW / today.isoformat()
    sources: dict[str, dict] = {}
    degraded: list[str] = []

    boards: dict[str, list[dict]] = {}
    for key, _title, _deck, since, _wording, _limit in BOARDS:
        rows, raw = fetch_board(since)
        sources[f"trending-{since}"] = save_raw(
            date_dir, f"trending-{since}.html", f"https://github.com/trending?since={since}", raw
        )
        boards[key] = rows
        print(f"  {since}: {len(rows)} rows", file=sys.stderr)

    hn_stories, hn_payload, hn_source, hn_url = fetch_hn()
    sources["hacker-news"] = save_raw(date_dir, "hacker-news.json", hn_url, hn_payload)
    if hn_stories:
        print(f"  hacker news: {len(hn_stories)} stories via {hn_source}", file=sys.stderr)
    else:
        degraded.append("Hacker News")
        print("  hacker news: unavailable", file=sys.stderr)

    cache: dict[str, dict] = {}
    for key in boards:
        for entry in boards[key]:
            repo = entry["repo"]
            if repo not in cache:
                cache[repo] = fetch_meta(repo)
                if repo not in CONTENT and not cache[repo].get("desc"):
                    cache[repo]["readme"] = fetch_readme(repo)
                print(f"  api: {repo}", file=sys.stderr)
            entry.update({k: v for k, v in cache[repo].items() if k != "desc"})
            if not entry.get("desc"):
                entry["desc"] = cache[repo].get("desc", "")

    for key in boards:
        boards[key].sort(key=lambda e: e["delta"], reverse=True)

    memberships: dict[str, list[str]] = {}
    for key in boards:
        for entry in boards[key]:
            memberships.setdefault(entry["repo"], []).append(key)

    sections, shown, one_liners, first_seen = [], set(), [], {}
    for key, title, deck, _since, wording, limit in BOARDS:
        cards = []
        for index, entry in enumerate(boards[key]):
            repo = entry["repo"]
            others = [BOARD_TITLES[b] for b in memberships[repo] if b != key]
            also = (
                f'<span class="also">also on {" and ".join(o.lower() for o in others)}</span>'
                if others
                else ""
            )
            if index < limit:
                first = first_seen.get(repo)
                cards.append(
                    card(index + 1, entry, wording, also, BOARD_TITLES[first] if first else None)
                )
                shown.add(repo)
                first_seen.setdefault(repo, key)
            elif repo not in shown:
                one_liners.append((repo, entry.get("desc") or "", key))
        sections.append(section(key, title, deck, cards))

    seen, rest_rows = set(), []
    for repo, desc, key in one_liners:
        if repo in seen:
            continue
        seen.add(repo)
        rest_rows.append(
            f'<li><span class="r-name"><a href="https://github.com/{esc(repo)}" '
            f'target="_blank" rel="noopener">{esc(repo)}</a></span>'
            f'<span>{esc(shorten(desc))} '
            f'<span class="r-board">({BOARD_TITLES[key].lower()})</span></span></li>'
        )

    ticker = "".join(
        ticker_item(e["repo"], e["delta"], short)
        for key, short in (("today", "24h"), ("week", "7d"), ("month", "30d"))
        for e in boards[key][:6]
    )
    ticker += "".join(
        f'<span class="tick"><b>{esc(s["title"][:34])}</b> '
        f'<span class="tick-hn">{fmt(s["points"])} points</span> '
        f'<span class="tick-per">HN</span></span>'
        for s in hn_stories[:3]
    )

    day_top = boards["today"][0]
    month_top = boards["month"][0]

    build = {
        "generated_at": now.replace(microsecond=0).isoformat(),
        "date": today.isoformat(),
        "commit": os.environ.get("GITHUB_SHA", ""),
        "run_url": os.environ.get("RUN_URL", ""),
        "status": "degraded" if degraded else "ok",
        "degraded": degraded,
        "boards": {k: len(v) for k, v in boards.items()},
        "cards_written_up": len(shown),
        "one_liners": len(rest_rows),
        "hacker_news": {"count": len(hn_stories), "source": hn_source},
        "sources": sources,
    }

    page = (ROOT / "template.html").read_text(encoding="utf-8")
    replacements = {
        "{{STATUS_BANNER}}": status_banner(degraded),
        "{{TICKER}}": ticker,
        "{{CHIPS}}": "".join(
            f'<button class="chip" type="button" data-filter="{slug}">{esc(label)}</button>'
            for slug, label in CAT_LABELS.items()
        ),
        "{{BOARDS}}": "\n".join(sections),
        "{{HN_SECTION}}": hn_section(hn_stories, hn_source),
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
        "{{ARCHIVE_DATE_ISO}}": today.isoformat(),
        "{{BUILD_STATUS}}": build["status"],
        "{{HN_SOURCE}}": hn_source,
    }
    for token, value in replacements.items():
        page = page.replace(token, value)

    leftover = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if leftover:
        print(f"unreplaced template tokens: {sorted(set(leftover))}", file=sys.stderr)
        return 1

    (ROOT / "index.html").write_text(page, encoding="utf-8")
    ARCHIVE.mkdir(exist_ok=True)
    (ARCHIVE / f"{today.isoformat()}.html").write_text(page, encoding="utf-8")

    history = sorted(
        (p.stem for p in ARCHIVE.glob("*.html") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)),
        reverse=True,
    )
    (ARCHIVE / "index.html").write_text(
        archive_index([(d, day_top["repo"].split("/")[-1], "") for d in history]),
        encoding="utf-8",
    )

    (ROOT / "build.json").write_text(json.dumps(build, indent=2) + "\n", encoding="utf-8")
    removed = prune_raw(today)

    print(
        f"wrote index.html ({len(page):,} bytes) · {len(shown)} cards · {len(rest_rows)} one-liners"
        f" · {len(hn_stories)} HN · status={build['status']}"
        + (f" · pruned raw {', '.join(removed)}" if removed else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
