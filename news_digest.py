#!/usr/bin/env python3
"""
Automated Morning News Digest (Groq Edition — Beautiful HTML)
--------------------------------------------------------------
Fetches Tech, World, and Gaming news via RSS feeds,
summarizes them using Groq AI (free), and emails a
beautifully formatted HTML digest to you.

Setup:
  pip install feedparser groq

Required environment variables:
  GROQ_API_KEY        - your Groq API key (free at console.groq.com)
  SMTP_EMAIL          - your Gmail address
  SMTP_APP_PASSWORD   - your Gmail App Password (16-char)
  RECIPIENT_EMAIL     - email to send the digest to
"""

import feedparser
import os
import re
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from groq import Groq

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
GROQ_API_KEY      = os.getenv("GROQ_API_KEY",       "YOUR_GROQ_API_KEY")
SMTP_EMAIL        = os.getenv("SMTP_EMAIL",          "your_gmail@gmail.com")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD",   "your_app_password_here")
RECIPIENT_EMAIL   = os.getenv("RECIPIENT_EMAIL",     "your_gmail@gmail.com")

# ─────────────────────────────────────────────
#  RSS FEEDS
# ─────────────────────────────────────────────
RSS_FEEDS = {
    "Tech": {
        "icon": "💻",
        "color": "#6366f1",
        "urls": [
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
        ],
    },
    "World": {
        "icon": "🌍",
        "color": "#10b981",
        "urls": [
            "http://feeds.bbci.co.uk/news/world/rss.xml",
            "https://feeds.reuters.com/reuters/worldNews",
        ],
    },
    "Gaming": {
        "icon": "🎮",
        "color": "#f59e0b",
        "urls": [
            "https://feeds.feedburner.com/ign/news",
            "https://kotaku.com/rss",
        ],
    },
}

ARTICLES_PER_FEED = 4


# ─────────────────────────────────────────────
#  STEP 1: Fetch articles
# ─────────────────────────────────────────────
def fetch_articles():
    all_sections = {}
    for category, config in RSS_FEEDS.items():
        articles = []
        for url in config["urls"]:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:ARTICLES_PER_FEED]:
                    title   = entry.get("title", "No title")
                    link    = entry.get("link", "#")
                    summary = entry.get("summary", entry.get("description", ""))
                    summary = re.sub(r"<[^>]+>", "", summary).strip()
                    summary = summary[:400] + "..." if len(summary) > 400 else summary
                    articles.append({"title": title, "link": link, "summary": summary})
            except Exception as e:
                print(f"  ⚠️  Could not fetch {url}: {e}")
        all_sections[category] = articles
    return all_sections


# ─────────────────────────────────────────────
#  STEP 2: Summarize with Groq → structured JSON
# ─────────────────────────────────────────────
def summarize_with_groq(sections: dict) -> dict:
    client = Groq(api_key=GROQ_API_KEY)

    raw_text = ""
    for category, articles in sections.items():
        raw_text += f"\n\n=== {category} ===\n"
        for a in articles:
            raw_text += f"\nTitle: {a['title']}\nSummary: {a['summary']}\nURL: {a['link']}\n"

    prompt = f"""You are a morning news assistant. Summarize the articles below into a structured JSON digest.

Return ONLY valid JSON (no markdown, no backticks, no explanation) in this exact format:
{{
  "intro": "A warm, engaging 2-sentence morning greeting that references today's top themes across tech, world, and gaming.",
  "sections": [
    {{
      "category": "Tech",
      "stories": [
        {{
          "headline": "Short punchy rewritten headline (max 10 words)",
          "summary": "2-3 sentence plain English summary of what happened and why it matters.",
          "url": "https://...",
          "tag": "One-word tag e.g. AI, Privacy, Hardware, Apps, Science"
        }}
      ]
    }},
    {{
      "category": "World",
      "stories": [
        {{
          "headline": "...",
          "summary": "...",
          "url": "...",
          "tag": "..."
        }}
      ]
    }},
    {{
      "category": "Gaming",
      "stories": [
        {{
          "headline": "...",
          "summary": "...",
          "url": "...",
          "tag": "..."
        }}
      ]
    }}
  ]
}}

Rules:
- Include exactly 3 stories per category (pick the most interesting ones)
- Summaries must be informative and written in plain, friendly English
- Only use stories from the data provided — do not invent anything
- Tags should be short single words

--- RAW ARTICLES ---
{raw_text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)


# ─────────────────────────────────────────────
#  STEP 3: Build beautiful HTML email
# ─────────────────────────────────────────────
def build_html(digest: dict) -> str:
    today   = datetime.now().strftime("%A, %B %d, %Y")
    intro   = digest.get("intro", "Good morning! Here's your daily news digest.")
    sections = digest.get("sections", [])

    category_meta = {
        "Tech":   {"icon": "💻", "color": "#6366f1", "light": "#eef2ff"},
        "World":  {"icon": "🌍", "color": "#10b981", "light": "#ecfdf5"},
        "Gaming": {"icon": "🎮", "color": "#f59e0b", "light": "#fffbeb"},
    }

    sections_html = ""
    for section in sections:
        cat    = section["category"]
        meta   = category_meta.get(cat, {"icon": "📰", "color": "#6366f1", "light": "#eef2ff"})
        stories = section.get("stories", [])

        stories_html = ""
        for story in stories:
            tag  = story.get("tag", "News")
            stories_html += f"""
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
              <tr>
                <td style="background:#ffffff; border:1px solid #e5e7eb; border-radius:10px; padding:20px;">
                  <div style="margin-bottom:8px;">
                    <span style="display:inline-block; background:{meta['light']}; color:{meta['color']}; font-size:10px; font-weight:700; letter-spacing:1.2px; text-transform:uppercase; padding:3px 10px; border-radius:20px;">{tag}</span>
                  </div>
                  <h3 style="margin:0 0 8px 0; font-size:16px; font-weight:700; color:#111827; line-height:1.4; font-family: Georgia, serif;">{story['headline']}</h3>
                  <p style="margin:0 0 14px 0; font-size:14px; color:#4b5563; line-height:1.7;">{story['summary']}</p>
                  <a href="{story['url']}" style="display:inline-block; font-size:12px; font-weight:600; color:{meta['color']}; text-decoration:none; letter-spacing:0.3px;">Read full story →</a>
                </td>
              </tr>
            </table>"""

        sections_html += f"""
        <!-- {cat} Section -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:36px;">
          <tr>
            <td>
              <!-- Section header -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
                <tr>
                  <td style="border-left: 4px solid {meta['color']}; padding-left:14px;">
                    <span style="font-size:22px;">{meta['icon']}</span>
                    <span style="font-size:20px; font-weight:800; color:{meta['color']}; font-family:Georgia,serif; vertical-align:middle; margin-left:8px;">{cat} News</span>
                  </td>
                </tr>
              </table>
              {stories_html}
            </td>
          </tr>
        </table>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Morning Digest — {today}</title>
</head>
<body style="margin:0; padding:0; background-color:#f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6; padding: 32px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%;">

          <!-- HEADER -->
          <tr>
            <td style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 60%, #4338ca 100%); border-radius:14px 14px 0 0; padding:40px 40px 36px;">
              <p style="margin:0 0 6px 0; font-size:11px; letter-spacing:3px; text-transform:uppercase; color:#a5b4fc;">Daily Briefing</p>
              <h1 style="margin:0 0 4px 0; font-size:36px; font-weight:900; color:#ffffff; font-family:Georgia,serif; letter-spacing:-0.5px;">Morning Digest</h1>
              <p style="margin:0 0 20px 0; font-size:13px; color:#a5b4fc; letter-spacing:0.5px;">{today}</p>
              <div style="height:1px; background:rgba(165,180,252,0.25); margin-bottom:20px;"></div>
              <p style="margin:0; font-size:15px; color:#c7d2fe; line-height:1.7; font-style:italic;">{intro}</p>
            </td>
          </tr>

          <!-- QUICK NAV PILLS -->
          <tr>
            <td style="background:#ffffff; padding:16px 40px; border-bottom: 1px solid #e5e7eb;">
              <span style="display:inline-block; background:#eef2ff; color:#6366f1; font-size:11px; font-weight:700; padding:5px 14px; border-radius:20px; margin-right:8px; letter-spacing:0.5px;">💻 Tech</span>
              <span style="display:inline-block; background:#ecfdf5; color:#10b981; font-size:11px; font-weight:700; padding:5px 14px; border-radius:20px; margin-right:8px; letter-spacing:0.5px;">🌍 World</span>
              <span style="display:inline-block; background:#fffbeb; color:#f59e0b; font-size:11px; font-weight:700; padding:5px 14px; border-radius:20px; letter-spacing:0.5px;">🎮 Gaming</span>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="background:#f9fafb; padding:32px 32px 8px;">
              {sections_html}
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background:#ffffff; border-radius:0 0 14px 14px; padding:24px 40px; border-top:1px solid #e5e7eb; text-align:center;">
              <p style="margin:0 0 4px 0; font-size:12px; color:#9ca3af;">Delivered by your Morning Digest bot · Powered by Groq AI</p>
              <p style="margin:0; font-size:11px; color:#d1d5db;">To stop receiving this, disable the GitHub Action workflow.</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""


# ─────────────────────────────────────────────
#  STEP 4: Send the email
# ─────────────────────────────────────────────
def send_email(html: str):
    today   = datetime.now().strftime("%A, %B %d, %Y")
    subject = f"☀️ Morning Digest — {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_EMAIL
    msg["To"]      = RECIPIENT_EMAIL

    # Plain text fallback
    plain = f"Morning Digest — {today}\n\nOpen this email in an HTML-capable client to view your digest."
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

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

    print("  🤖 Summarizing with Groq...")
    digest = summarize_with_groq(sections)

    print("  🎨 Building HTML email...")
    html = build_html(digest)

    print("  📧 Sending email...")
    send_email(html)

    print("  🎉 Done!\n")


if __name__ == "__main__":
    run_digest()
