#!/usr/bin/env python3
"""
Automated Morning News Digest
------------------------------
Fetches Tech, World, and Gaming news via RSS feeds,
summarizes them using Claude AI, and emails the digest to you.

Setup:
  pip install feedparser anthropic

Required environment variables (or fill in the CONFIG section below):
  ANTHROPIC_API_KEY   - your Anthropic API key
  SMTP_EMAIL          - your Gmail address
  SMTP_APP_PASSWORD   - your Gmail App Password (16-char)
  RECIPIENT_EMAIL     - email to send the digest to
"""

import feedparser
import anthropic
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIG — fill these in or set as env vars
# ─────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY",  "YOUR_ANTHROPIC_API_KEY")
SMTP_EMAIL         = os.getenv("SMTP_EMAIL",          "your_gmail@gmail.com")
SMTP_APP_PASSWORD  = os.getenv("SMTP_APP_PASSWORD",   "your_app_password_here")
RECIPIENT_EMAIL    = os.getenv("RECIPIENT_EMAIL",      "your_gmail@gmail.com")
SEND_TIME_HOUR     = 7   # 24-hour format (7 = 7:00 AM)

# ─────────────────────────────────────────────
#  RSS FEEDS
# ─────────────────────────────────────────────
RSS_FEEDS = {
    "🖥️ Tech News": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
    ],
    "🌍 World News": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.reuters.com/reuters/worldNews",
    ],
    "🎮 Gaming News": [
        "https://feeds.feedburner.com/ign/news",
        "https://kotaku.com/rss",
    ],
}

ARTICLES_PER_FEED = 3   # how many articles to pull from each feed


# ─────────────────────────────────────────────
#  STEP 1: Fetch articles from RSS feeds
# ─────────────────────────────────────────────
def fetch_articles():
    all_sections = {}

    for category, urls in RSS_FEEDS.items():
        articles = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:ARTICLES_PER_FEED]:
                    title   = entry.get("title", "No title")
                    link    = entry.get("link", "")
                    summary = entry.get("summary", entry.get("description", ""))
                    # Strip basic HTML tags from summary
                    import re
                    summary = re.sub(r"<[^>]+>", "", summary).strip()
                    summary = summary[:300] + "..." if len(summary) > 300 else summary
                    articles.append({"title": title, "link": link, "summary": summary})
            except Exception as e:
                print(f"  ⚠️  Could not fetch {url}: {e}")

        all_sections[category] = articles

    return all_sections


# ─────────────────────────────────────────────
#  STEP 2: Summarize with Claude
# ─────────────────────────────────────────────
def summarize_with_claude(sections: dict) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Build the raw news text to send to Claude
    raw_text = ""
    for category, articles in sections.items():
        raw_text += f"\n\n=== {category} ===\n"
        for a in articles:
            raw_text += f"\nTitle: {a['title']}\nSummary: {a['summary']}\nURL: {a['link']}\n"

    prompt = f"""You are a friendly morning news assistant. 
Below are raw RSS news articles across three categories: Tech, World, and Gaming.

Your job:
1. Write a warm, engaging morning briefing email body (no subject line).
2. Use the three category headers: 🖥️ Tech News, 🌍 World News, 🎮 Gaming News.
3. Under each header, write 2-4 short bullet points summarizing the top stories in plain English.
4. Keep each bullet to 1-2 sentences max.
5. Include the article URL in parentheses after each bullet.
6. End with a friendly one-line sign-off.
7. Do NOT make up stories — only use what's provided below.

--- RAW ARTICLES ---
{raw_text}
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


# ─────────────────────────────────────────────
#  STEP 3: Send the email
# ─────────────────────────────────────────────
def send_email(body: str):
    today = datetime.now().strftime("%A, %B %d, %Y")
    subject = f"☀️ Your Morning News Digest — {today}"

    # Build HTML version for nicer rendering
    html_body = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 650px; margin: auto; color: #222;">
      <h2 style="color:#2d6cdf;">☀️ Morning News Digest</h2>
      <p style="color:#888; font-size:13px;">{today}</p>
      <hr style="border:none; border-top:1px solid #eee;">
      <div style="white-space: pre-wrap; line-height:1.7; font-size:15px;">{body}</div>
      <hr style="border:none; border-top:1px solid #eee; margin-top:30px;">
      <p style="font-size:11px; color:#aaa;">
        Automated digest powered by Claude AI &amp; Python.<br>
        To unsubscribe, simply stop running the script or the scheduled task.
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_EMAIL
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print(f"  ✅  Digest sent to {RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"  ❌  Failed to send email: {e}")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def run_digest():
    print(f"\n📰 Running morning news digest — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    print("  🔍 Fetching articles...")
    sections = fetch_articles()
    total = sum(len(v) for v in sections.values())
    print(f"  📦 Fetched {total} articles across {len(sections)} categories")

    print("  🤖 Summarizing with Claude...")
    summary = summarize_with_claude(sections)

    print("  📧 Sending email...")
    send_email(summary)

    print("  🎉 Done!\n")


if __name__ == "__main__":
    run_digest()
