# Apartment Hunt Bot — Implementation Plan

## Overview

A locally-running Python bot that monitors Facebook groups for apartment listings,
filters them based on your personal criteria, and sends real-time alerts to your
Telegram account. Full Hebrew support throughout.

---

## Architecture

```
apartment-hunt-bot/
├── config/
│   └── settings.yaml          # All user preferences (cities, rooms, filters)
├── scraper/
│   └── facebook_scraper.py    # Logs into Facebook, polls group posts
├── parser/
│   └── listing_parser.py      # Extracts structured data from Hebrew post text
├── filter/
│   └── listing_filter.py      # Applies your criteria to parsed listings
├── notifier/
│   └── telegram_notifier.py   # Sends formatted alerts via Telegram Bot API
├── storage/
│   └── seen_posts.db          # SQLite — tracks post IDs already processed
├── models/
│   └── listing.py             # Data class: Listing(id, city, rooms, price, ...)
├── main.py                    # Scheduler loop — ties everything together
├── requirements.txt
└── .env                       # Secrets: FB credentials, Telegram token (git-ignored)
```

---

## Components

### 1. Facebook Scraper (`scraper/facebook_scraper.py`)

**Approach:** Playwright (headless Chromium) — logs in with your personal
Facebook account and scrapes the group feeds. This is the most reliable method
for private groups that require membership.

- Logs in once, persists the session cookie to avoid repeated logins
- Scrolls each configured group feed on a set interval (e.g., every 10 minutes)
- Extracts: post ID, author, timestamp, full post text, image URLs, post URL
- Stores each new post in SQLite; skips already-seen post IDs

> **Note:** Facebook ToS technically disallows scraping, but personal use on
> your own account for private consumption is very low risk. No commercial use.

---

### 2. Listing Parser (`parser/listing_parser.py`)

Converts raw Hebrew post text into a structured `Listing` object using regex
patterns and optional LLM assist for ambiguous posts.

**Extracted fields:**

| Field | Example Hebrew patterns |
|---|---|
| Rooms | `3 חדרים`, `3.5 חד'`, `דירת 4 חדרים` |
| Price | `6,500 ₪`, `6500 לחודש`, `שכירות 7000` |
| City | `תל אביב`, `רמת גן`, `גבעתיים` |
| Neighborhood | `פלורנטין`, `הצפון הישן`, `קריית קציר` |
| Floor | `קומה 3`, `קומה גבוהה`, `קומת קרקע` |
| Broker | `ללא תיווך`, `דמי תיווך`, `עמלת תיווך` |
| Balcony | `מרפסת`, `מרפסת שמש` |
| Parking | `חניה`, `חנייה פרטית` |
| Shelter | `ממ"ד`, `מרחב מוגן` |
| Size (sqm) | `80 מ"ר`, `75 מטר` |
| Available from | `פנויה מיידית`, `כניסה ב-1.8`, `זמין מ-` |

Fallback: if regex confidence is low, send the raw post as-is to Telegram
with a "needs manual review" tag.

---

### 3. Filter Engine (`filter/listing_filter.py`)

Applies your `settings.yaml` criteria to each parsed listing:

- **Hard filters** (listing is dropped if it fails any of these):
  - City not in your list
  - Rooms outside your range
  - Price above your max
  - Neighborhood not in your list (if you specify neighborhoods)

- **Soft filters** (listing passes but gets a lower score):
  - Missing a preferred feature (balcony, parking, shelter)
  - Floor outside your preferred range

- **Scoring:** listings that match more preferred features get a higher score,
  shown as stars in the Telegram message (e.g., ⭐⭐⭐ = 3/5 features matched)

---

### 4. Telegram Notifier (`notifier/telegram_notifier.py`)

Uses `python-telegram-bot` library to send you a formatted message for each
matching listing.

**Message format:**
```
🏠 דירה חדשה — תל אביב, פלורנטין

📍 עיר: תל אביב | שכונה: פלורנטין
🛏  חדרים: 3
💰 מחיר: 6,500 ₪/חודש
🏢 קומה: 3
✅ ללא תיווך  |  🌿 מרפסת  |  🚗 חניה  |  🛡 ממ"ד

⭐⭐⭐⭐ (4/5 features matched)

🔗 קישור לפוסט: [לחץ כאן](https://facebook.com/groups/...)
👤 מפרסם: [שם המפרסם]
🕐 פורסם: לפני 5 דקות
```

---

### 5. Storage (`storage/seen_posts.db`)

SQLite database with two tables:

- `seen_posts(post_id, group_id, seen_at)` — prevents duplicate alerts
- `sent_listings(post_id, sent_at, score)` — history of what was sent to you

---

### 6. Scheduler (`main.py`)

Runs a polling loop using `APScheduler`:

- Every N minutes: scrape all configured groups
- Process new posts through parser → filter → notifier pipeline
- Sends a daily summary at a configured time (optional)
- Handles errors gracefully — logs failures, sends a Telegram alert if the bot
  crashes or Facebook login expires

---

## Settings File (`config/settings.yaml`)

```yaml
search:
  cities:
    - תל אביב
    - רמת גן
    - גבעתיים

  neighborhoods:
    גבעתיים:
      - קריית יוסף
      - סיטי
      - הל״ה
      - בורכוב
    רמת גן:
      - הראשונים
      - הבורסה
      - תל בנימין
      - חשמונאים
      - גפן
    תל אביב:
      - הצפון הישן
      - צמרות איילון
      - מונטיפיורי
      - נחלת יצחק

  rooms:
    min: 2
    max: 3

  price:
    max: 6000           # NIS per month — skip posts with no price listed
    skip_if_no_price: true

  floor:
    min: null           # no minimum floor requirement
    max: null

  features:
    no_broker: true     # hard filter — drop all listings with broker fees
    balcony: false      # preferred, not required
    parking: false      # preferred, not required
    shelter: false      # preferred, not required

  available_within_days: 60

facebook:
  groups:
    - https://www.facebook.com/share/g/18G39HFzpo/
    - https://www.facebook.com/share/g/1Cp4bFkySH/
    - https://www.facebook.com/share/g/1GhZ3p67LV/
    - https://www.facebook.com/share/g/18axWjkF14/
    - https://www.facebook.com/share/g/14akgef1HmM/
  poll_interval_minutes: 30
  session_file: .fb_session.json

telegram:
  bot_token: ""         # set in .env instead
  chat_id: ""           # your personal Telegram chat ID

notifications:
  daily_summary: true
  daily_summary_time: "09:00"
  alert_on_bot_error: true
```

---

## Tech Stack

| Purpose | Library |
|---|---|
| Facebook scraping | `playwright` (async, Chromium) |
| Scheduling | `apscheduler` |
| Telegram messaging | `python-telegram-bot` |
| Hebrew text parsing | `re` (regex), `python-dateutil` |
| Data models | `dataclasses` or `pydantic` |
| Storage | `sqlite3` (stdlib) |
| Config | `pyyaml` |
| Secrets | `python-dotenv` |
| Logging | `loguru` |

**Python version:** 3.11+

---

## Confirmed Settings

All inputs have been provided:

| Setting | Value |
|---|---|
| Cities | תל אביב, רמת גן, גבעתיים |
| Rooms | 2–3 |
| Max rent | 6,000 ₪/month |
| No price listed | Skip |
| Broker | Hard filter — drop all brokered listings |
| Floor min | None |
| Facebook groups | 5 groups (from facebook_groups.txt) |
| Poll interval | 30 minutes |
| Neighborhoods | See settings.yaml above |

---

## Implementation Phases

### Phase 1 — Core Pipeline (MVP)
- [ ] `settings.yaml` config structure
- [ ] Playwright Facebook login + session persistence
- [ ] Scrape posts from one group
- [ ] Basic Hebrew regex parser
- [ ] Hard-filter logic
- [ ] Telegram bot sends a message

### Phase 2 — Full Feature Set
- [ ] Multi-group support
- [ ] Soft filters + scoring
- [ ] SQLite deduplication
- [ ] All Hebrew field extractors (floor, shelter, parking, etc.)
- [ ] Graceful error handling + bot-crash alerts

### Phase 3 — Polish
- [ ] Daily summary digest
- [ ] `/status` Telegram command to check if bot is alive
- [ ] `/pause` and `/resume` Telegram commands
- [ ] Logging to file with rotation

---

## Notes & Risks

- **Facebook login stability:** Facebook may occasionally require 2FA or
  CAPTCHA. The bot will detect this and alert you on Telegram so you can
  re-authenticate manually.
- **Hebrew parsing accuracy:** Apartment posts vary widely in format. The parser
  will handle common patterns well, but unusual posts may be sent as raw text
  for you to review manually.
- **Rate limiting:** Polling too frequently may trigger Facebook's bot detection.
  10-minute intervals are a safe default.
- **Session expiry:** Facebook sessions typically last 30–90 days. The bot will
  alert you when a re-login is needed.
