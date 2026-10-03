# Daily AI & Healthcare Digest

A small Python "agent" that fetches recent items from a curated list of RSS
feeds, splits them into three sections, and emails you a daily digest. It
runs on GitHub's own scheduler, so nothing needs to stay switched on at home.

## How it works (the "why")

- **RSS instead of scraping or a news API**: RSS is free, needs no API key,
  and is far less likely to break than scraping a webpage's HTML (which
  changes its structure often). A paid news API would add cost and a key to
  manage for no real benefit at this stage.
- **Keyword filtering for the "specific" section**: no outlet publishes a
  dedicated "telemedicine + GLP-1" feed, so the script instead scans broader
  pharma/health feeds and keeps only items whose title or summary contains
  one of your keywords (see `SPECIFIC_KEYWORDS` in `news_agent.py`).
- **GitHub Actions instead of your own machine**: Actions gives you a free
  scheduled job that runs even if your laptop is off, and it's a genuinely
  useful thing to have on a CV/portfolio as a working example of a deployed,
  scheduled script.
- **Gmail SMTP with an "app password"** instead of a transactional email
  service: it's free and takes five minutes to set up, at the cost of being
  a little less robust than a dedicated provider (fine for one email/day).

## One-time setup

### 1. Create the GitHub repository
1. Create a new **private** repository on GitHub (private, since your email
   address will be referenced, even though it's stored as a secret).
2. Push these four files into it (`news_agent.py`, `requirements.txt`,
   `README.md`, and the `.github/workflows/daily-newsletter.yml` folder).

### 2. Create a Gmail "app password"
Gmail won't let a script log in with your normal password.
1. Turn on 2-Step Verification on the Google account you'll send from
   (Google Account → Security → 2-Step Verification).
2. Go to Google Account → Security → **App passwords**.
3. Create one for "Mail" / "Other (custom name)" - call it `news-agent`.
4. Copy the 16-character password it generates (spaces don't matter).

### 3. Add GitHub repository secrets
In your repo: **Settings → Secrets and variables → Actions → New repository
secret**. Add three:

| Secret name           | Value                                      |
|------------------------|---------------------------------------------|
| `SENDER_EMAIL`          | the Gmail address you generated the app password for |
| `SENDER_APP_PASSWORD`   | the 16-character app password              |
| `RECIPIENT_EMAIL`       | where you want the digest sent (can be the same address) |

Secrets are encrypted and never appear in logs - this is the correct way to
handle credentials in a public/private repo, never hard-code them in the
`.py` file itself.

### 4. Test it
- Locally: `pip install -r requirements.txt`, then set the three variables
  as environment variables and run `python news_agent.py`.
- On GitHub: go to the **Actions** tab, select "Daily AI & Healthcare
  Newsletter", click **Run workflow** to trigger it manually without waiting
  for the schedule.

## Things worth knowing as you iterate

- **Feed URLs break.** News sites restructure their sites occasionally,
  which changes RSS paths. If a section is consistently empty, check the
  feed URL still resolves by opening it in a browser - it should show raw
  XML, not a 404.
- **Cron is UTC and ignores daylight saving.** The schedule is fixed in UTC,
  so the Munich delivery time shifts by an hour when clocks change unless
  you manually adjust the cron line twice a year.
- **A natural next step**, once this is running reliably, would be piping
  each day's raw items through the Claude API (which you're already
  planning to get hands-on with) to have it write a one-line "why this
  matters for healthcare product work" note per item, rather than just
  listing headlines. Happy to help build that layer once the basic version
  is working end to end for you.
