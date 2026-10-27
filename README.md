# What's hot on GitHub — a daily briefing

One static page, rebuilt every morning by GitHub Actions, that explains what is trending on GitHub and on Hacker News in plain English — with a concrete use case for each project, for people who do not write code.

**Live:** https://dhruvdua88.github.io/github-trending-briefing/
**Archive:** https://dhruvdua88.github.io/github-trending-briefing/archive/
**Build manifest:** https://dhruvdua88.github.io/github-trending-briefing/build.json

Three leaderboards from [`github.com/trending`](https://github.com/trending) — 24 hours, 7 days, 30 days — re-sorted strictly by stars gained, plus Hacker News stories from the last 24 hours.

## How it stays current

Everything happens in GitHub Actions. Nothing runs on a personal machine; no laptop needs to be awake.

| Step | What it does | When |
| --- | --- | --- |
| Rebuild | fetch boards, API, Hacker News → render `index.html` | 03:45 UTC (09:15 IST) daily |
| Verify | re-read the archived payloads, recompute a delta, check freshness | before every deploy |
| Commit | `index.html`, `build.json`, `archive/` | only when something changed |
| Deploy | publish `_site` to GitHub Pages | after a verified rebuild |

GitHub sometimes starts scheduled runs a few minutes late. The page prints its own build time, so a late run is visible rather than silently wrong.

## It refuses to lie

`generate.py` writes the raw payloads it used — the three board HTML files and the Hacker News feed — into `archive/raw/<date>/`, gzipped, with their SHA-256 in `build.json`.

`verify.py` then runs as a separate step and does not trust the generator:

1. every archived payload still hashes to what `build.json` claims;
2. the #1 repository on the daily board carries the same star delta on the page as the raw HTML says;
3. the snapshot is under 8 hours old;
4. the page's status marker agrees with `build.json` (banner present iff the build was degraded);
5. no unreplaced template tokens survived.

If any check fails the workflow stops and the previous deploy stays live.

Failure policy is deliberately split:

- **Any GitHub board missing → hard fail.** The page would be meaningless, so nothing is published.
- **Hacker News missing → degraded publish.** Both the timestamped Firebase feed and the Algolia front page are tried; if neither answers, the page publishes with a visible banner naming the missing source. Real data, partial morning, stated plainly.

## Sources

- `https://github.com/trending?since=daily|weekly|monthly` — boards and star deltas
- `https://api.github.com/repos/{owner}/{repo}` — stars, language, topics, creation date, last-commit date
- `https://api.github.com/repos/{owner}/{repo}/readme` — only for trending repos with no write-up yet, quoted not paraphrased
- `https://hacker-news.firebaseio.com/v0` — top stories with timestamps, filtered to the last 24 hours
- `https://hn.algolia.com/api/v1/search?tags=front_page` — fallback if Firebase fails

Every card also prints its own evidence: stars per day since the repo was created, and when it last received a commit. A repo climbing faster than a codebase usually earns is flagged on the card rather than quietly praised.

## Editing the write-ups

All prose lives in [`content.py`](content.py), one entry per repository:

```python
"cloudflare/security-audit-skill": {
    "cat": "security",
    "what": "Cloudflare's instructions for making a coding agent perform a multi-stage security review…",
    "use": "If a portal touches client KYC, PAN or bank data, run this review before it goes live.",
},
```

`cat` drives the filter chips: `agents`, `design`, `media`, `money`, `security`, `dev`, `office`, `fun`.

A repository that trends without an entry still appears — GitHub's own description, or a quoted README paragraph, plus an explicit note that no write-up exists. Nothing is invented from the name.

## Archive

One file per morning under `archive/`, plus an index. Published pages are not retro-edited; a correction shows up as another day's page.

Raw payloads are kept for 14 days and then pruned, so the repository does not grow without limit. The rendered pages stay.

## Running it locally (optional)

Only for changing the generator itself:

```bash
GITHUB_TOKEN=ghp_… python3 generate.py   # token avoids the 60 req/hour limit
python3 verify.py                        # must pass before you commit
```

Standard library only — no dependencies to install.

## What this is not

No repository here is installed, audited or endorsed. Star counts measure attention, not safety. Be careful with anything that asks for access to accounts, files or email.

## Licence

MIT — see [LICENSE](LICENSE).
