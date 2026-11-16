import requests
from loguru import logger
from models.listing import Listing


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.chat_id = chat_id
        self._api = f"https://api.telegram.org/bot{bot_token}"

    def send_listing(self, listing: Listing, score: int):
        self._send(self._format(listing, score))

    def send_text(self, text: str):
        self._send(text)

    # ------------------------------------------------------------------ #

    def _format(self, listing: Listing, score: int) -> str:
        location = listing.city or "?"
        if listing.neighborhood:
            location += f" — {listing.neighborhood}"

        lines = ["🏠 <b>דירה חדשה!</b>", "", f"📍 {location}"]

        if listing.rooms is not None:
            r = int(listing.rooms) if listing.rooms == int(listing.rooms) else listing.rooms
            lines.append(f"🛏 {r} חדרים")

        if listing.price:
            lines.append(f"💰 {listing.price:,} ₪/חודש")

        if listing.floor is not None:
            lines.append(f"🏢 קומה {listing.floor}")

        lines.append("✅ ללא תיווך")

        extras = []
        if listing.balcony:
            extras.append("🌿 מרפסת")
        if listing.parking:
            extras.append("🚗 חניה")
        if listing.shelter:
            extras.append('🛡 ממ"ד')
        if extras:
            lines.append(" | ".join(extras))

        if score > 0:
            lines += ["", "⭐" * score]

        lines += ["", f'🔗 <a href="{listing.post_url}">קישור לפוסט</a>']

        if listing.author:
            lines.append(f"👤 {listing.author}")

        return "\n".join(lines)

    def _send(self, text: str):
        try:
            resp = requests.post(
                f"{self._api}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                timeout=10,
            )
            if not resp.ok:
                logger.error(f"Telegram error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
