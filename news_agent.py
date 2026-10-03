"""
Daily AI + Healthcare news digest.

Fetches items from a curated list of RSS feeds, splits them into three
clearly separated sections, and emails a tidy HTML digest.

Run manually:    python news_agent.py
Run on schedule: see .github/workflows/daily-newsletter.yml
"""

import os
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import feedparser

# ---------------------------------------------------------------------------
# Configuration - edit these lists as you find feeds that work better for
# you. If a feed URL breaks (news sites change these more often than you'd
# expect), the script skips it and prints a warning rather than crashing.
# ---------------------------------------------------------------------------

AI_FEEDS = [
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
]

HEALTHCARE_BROAD_FEEDS = [
    ("MobiHealthNews", "https://www.mobihealthnews.com/feed"),
    ("Fierce Healthcare", "https://www.fiercehealthcare.com/rss.xml"),
    ("STAT News", "https://www.statnews.com/feed/"),
]

# Feeds scanned for the "specific" section. No outlet publishes a dedicated
# telemedicine/GLP-1 feed, so we pull from broader pharma/health feeds and
# filter down by keyword instead.
SPECIFIC_SOURCE_FEEDS = [
    ("Fierce Pharma", "https://www.fiercepharma.com/rss.xml"),
    ("Endpoints News", "https://endpts.com/feed/"),
    ("STAT News", "https://www.statnews.com/feed/"),
    ("MobiHealthNews", "https://www.mobihealthnews.com/feed"),
]

SPECIFIC_KEYWORDS = [
    "telemedicine", "telehealth", "weight loss", "weight-loss", "obesity",
    "glp-1", "glp1", "semaglutide", "tirzepatide", "ozempic", "wegovy",
    "zepbound", "mounjaro",
]

MAX_ITEMS_PER_SECTION = 8
MAX_AGE_HOURS = 30  # only include items published within this window

SENDER_EMAIL = os.environ["SENDER_EMAIL"]
SENDER_APP_PASSWORD = os.environ["SENDER_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]


def fetch_entries(feeds):
    """Fetch and flatten entries from a list of (label, url) feeds."""
    entries = []
    for label, url in feeds:
        try:
            parsed = feedparser.parse(url)
            if parsed.bozo and not parsed.entries:
                print(f"[warn] could not parse feed '{label}' ({url}): {parsed.bozo_exception}")
                continue
            for e in parsed.entries:
                entries.append({
                    "source": label,
                    "title": e.get("title", "(no title)"),
                    "link": e.get("link", ""),
                    "summary": e.get("summary", ""),
                    "published_parsed": e.get("published_parsed") or e.get("updated_parsed"),
                })
        except Exception as exc:
            print(f"[warn] failed to fetch feed '{label}' ({url}): {exc}")
    return entries


def recent_only(entries, max_age_hours):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    kept = []
    for e in entries:
        if e["published_parsed"] is None:
            kept.append(e)  # keep undated items rather than silently dropping them
            continue
        published = datetime(*e["published_parsed"][:6], tzinfo=timezone.utc)
        if published >= cutoff:
            kept.append(e)
    return kept


def dedupe(entries):
    seen = set()
    unique = []
    for e in entries:
        key = e["link"] or e["title"]
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


def sort_and_limit(entries, limit):
    def sort_key(e):
        return e["published_parsed"] or (1970, 1, 1, 0, 0, 0)
    entries.sort(key=sort_key, reverse=True)
    return entries[:limit]


def matches_keywords(entry, keywords):
    haystack = (entry["title"] + " " + entry["summary"]).lower()
    return any(k in haystack for k in keywords)


def build_section(entries, limit):
    entries = dedupe(entries)
    entries = recent_only(entries, MAX_AGE_HOURS)
    return sort_and_limit(entries, limit)


def section_html(title, entries):
    if not entries:
        items_html = "<p style='color:#666;'>No fresh items today.</p>"
    else:
        rows = []
        for e in entries:
            rows.append(
                f"<li style='margin-bottom:10px;'>"
                f"<a href='{e['link']}' style='font-weight:600; text-decoration:none; color:#1a3c6e;'>{e['title']}</a>"
                f"<br><span style='color:#888; font-size:12px;'>{e['source']}</span>"
                f"</li>"
            )
        items_html = "<ul style='list-style:none; padding-left:0;'>" + "".join(rows) + "</ul>"
    return f"<h2 style='border-bottom:2px solid #ddd; padding-bottom:4px;'>{title}</h2>{items_html}"


def build_email_html(ai_items, health_broad_items, health_specific_items):
    date_str = datetime.now().strftime("%A, %d %B %Y")
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width:640px; margin:auto;">
      <h1 style="color:#1a3c6e;">Daily AI &amp; Healthcare Digest - {date_str}</h1>
      {section_html("AI News", ai_items)}
      {section_html("Digital Health &amp; Healthtech (broad)", health_broad_items)}
      {section_html("Telemedicine &amp; Weight-loss / GLP-1 (specific)", health_specific_items)}
      <p style="color:#999; font-size:11px; margin-top:30px;">
        Generated automatically. Source shown under each headline.
      </p>
    </body>
    </html>
    """


def send_email(html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Daily AI & Healthcare Digest - {datetime.now().strftime('%d %b %Y')}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())


def main():
    ai_raw = fetch_entries(AI_FEEDS)
    health_broad_raw = fetch_entries(HEALTHCARE_BROAD_FEEDS)
    specific_source_raw = fetch_entries(SPECIFIC_SOURCE_FEEDS)

    ai_items = build_section(ai_raw, MAX_ITEMS_PER_SECTION)
    health_broad_items = build_section(health_broad_raw, MAX_ITEMS_PER_SECTION)

    specific_candidates = [e for e in specific_source_raw if matches_keywords(e, SPECIFIC_KEYWORDS)]
    health_specific_items = build_section(specific_candidates, MAX_ITEMS_PER_SECTION)

    html = build_email_html(ai_items, health_broad_items, health_specific_items)
    send_email(html)
    print(
        f"Sent digest: {len(ai_items)} AI, "
        f"{len(health_broad_items)} broad health, "
        f"{len(health_specific_items)} specific items."
    )


if __name__ == "__main__":
    main()
