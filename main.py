import os
import sys
from pathlib import Path

from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv
import yaml

load_dotenv()

from scraper.facebook_scraper import FacebookScraper
from parser.listing_parser import ListingParser
from filter.listing_filter import ListingFilter
from notifier.telegram_notifier import TelegramNotifier
from storage.db import Database


def load_settings() -> dict:
    path = Path(__file__).parent / "config" / "settings.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def poll(
    scraper: FacebookScraper,
    parser: ListingParser,
    filter_: ListingFilter,
    notifier: TelegramNotifier,
    db: Database,
    settings: dict,
    seed_only: bool = False,
):
    groups = settings["facebook"]["groups"]
    sent = 0
    for url in groups:
        for raw in scraper.scrape_group(url):
            if db.is_seen(raw["post_id"]):
                continue
            db.mark_seen(raw["post_id"])
            if seed_only:
                continue
            listing = parser.parse(raw)
            if filter_.matches(listing):
                score = filter_.score(listing)
                notifier.send_listing(listing, score)
                sent += 1
                logger.info(
                    f"Sent: {listing.city} / {listing.neighborhood} | "
                    f"{listing.rooms} חד' | {listing.price} ₪"
                )
    if not seed_only:
        logger.info(f"Poll complete — {sent} new matches sent")


def main():
    logger.add("apartment_bot.log", rotation="1 week", retention="1 month", encoding="utf-8")

    settings = load_settings()

    fb_email    = os.getenv("FACEBOOK_EMAIL")
    fb_password = os.getenv("FACEBOOK_PASSWORD")
    tg_token    = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat_id  = os.getenv("TELEGRAM_CHAT_ID")

    missing = [k for k, v in {
        "FACEBOOK_EMAIL":    fb_email,
        "FACEBOOK_PASSWORD": fb_password,
        "TELEGRAM_BOT_TOKEN": tg_token,
        "TELEGRAM_CHAT_ID":  tg_chat_id,
    }.items() if not v]
    if missing:
        logger.error(f"Missing .env variables: {', '.join(missing)}")
        sys.exit(1)

    db       = Database()
    parser   = ListingParser(settings)
    filter_  = ListingFilter(settings)
    notifier = TelegramNotifier(tg_token, tg_chat_id)
    scraper  = FacebookScraper(settings, fb_email, fb_password)

    try:
        scraper.start()

        if db.total_seen() == 0:
            logger.info("First run — seeding existing posts without sending notifications")
            notifier.send_text(
                "🤖 <b>Apartment bot started!</b>\n\n"
                "Scanning existing posts now — no notifications for old listings.\n"
                "You'll be notified about new listings from here on."
            )
            poll(scraper, parser, filter_, notifier, db, settings, seed_only=True)
            notifier.send_text("✅ Ready. Watching for new listings every 30 minutes...")
        else:
            notifier.send_text("🤖 Apartment bot restarted. Watching for new listings...")
            poll(scraper, parser, filter_, notifier, db, settings)

        interval = settings["facebook"]["poll_interval_minutes"]
        scheduler = BlockingScheduler(timezone="Asia/Jerusalem")
        scheduler.add_job(
            poll,
            "interval",
            minutes=interval,
            args=[scraper, parser, filter_, notifier, db, settings],
        )
        logger.info(f"Scheduler running — polling every {interval} minutes")
        scheduler.start()

    except KeyboardInterrupt:
        logger.info("Stopped by user (Ctrl+C)")
        notifier.send_text("🛑 Apartment bot stopped.")
    except Exception as e:
        logger.exception(f"Bot crashed: {e}")
        try:
            notifier.send_text(f"❌ Bot crashed:\n<code>{e}</code>")
        except Exception:
            pass
        raise
    finally:
        scraper.stop()
        db.close()


if __name__ == "__main__":
    main()
