# What's hot on GitHub — a daily briefing

A single static page, rebuilt every morning by GitHub Actions, that explains what is trending on GitHub and on Hacker News in plain English — with a concrete use case for each project, for people who do not write code.

**Live page:** https://dhruvdua88.github.io/github-trending-briefing/

Three leaderboards from [`github.com/trending`](https://github.com/trending) — 24 hours, 7 days, 30 days — re-sorted strictly by stars gained, plus the front page of Hacker News at build time.

## How it stays current

Everything happens in GitHub Actions. Nothing runs on a personal machine, and no local computer needs to be switched on.

| Step | Where | When |
| --- | --- | --- |
| Fetch boards + render `index.html` | `.github/workflows/daily.yml` | 03:45 UTC (09:15 IST) daily |
| Commit the new page | same workflow | only when the output changed |
| Publish to GitHub Pages | same workflow | after every successful rebuild |

Sources, all public and unauthenticated apart from the workflow's own token:

- `https://github.com/trending?since=daily|weekly|monthly` — the boards and star deltas
- `https://api.github.com/repos/{owner}/{repo}` — star totals, primary language, topics
- `https://hn.algolia.com/api/v1/search?tags=front_page` — Hacker News front page, with a Firebase fallback (`hacker-news.firebaseio.com/v0`)

If a source fails, the workflow fails and the previous page stays live. It never publishes a half-built page.

## Editing the write-ups

All prose lives in [`content.py`](content.py), one entry per repository:

```python
"cloudflare/security-audit-skill": {
    "cat": "security",
    "what": "Cloudflare's instructions for making a coding agent perform a multi-stage security review…",
    "use": "If a portal touches client KYC, PAN or bank data, run this review before it goes live.",
},
```

`cat` is one of `agents`, `design`, `media`, `money`, `security`, `dev`, `office`, `fun` — it drives the filter chips. A repository that trends without an entry still appears, labelled honestly: GitHub's own description, plus a note that no write-up exists yet. Nothing is invented from the name.

Adding an entry is a plain commit; the next scheduled run picks it up.

## Refreshing by hand

Actions → **Rebuild briefing** → *Run workflow*. Same pipeline, on demand.

## Running it locally (optional)

Only needed if you are changing the generator itself:

```bash
python3 generate.py            # writes index.html
GITHUB_TOKEN=ghp_… python3 generate.py   # avoids the 60 req/hour anonymous API limit
```

Standard library only — no dependencies to install.

## What this is not

No repository here is installed, audited or endorsed. Star counts measure attention, not safety. Be careful with anything that asks for access to accounts, files or email.

## Licence

MIT — see [LICENSE](LICENSE).
