import re
from models.listing import Listing


FLOOR_WORDS = {
    "קרקע": 0, "ראשון": 1, "ראשונה": 1, "שני": 2, "שנייה": 2,
    "שלישי": 3, "שלישית": 3, "רביעי": 4, "רביעית": 4,
    "חמישי": 5, "חמישית": 5, "שישי": 6, "שישית": 6,
    "שביעי": 7, "שביעית": 7,
}

CITY_ALIASES = {
    "תל אביב": ["תל אביב", 'ת"א', "ת״א", "תל-אביב"],
    "רמת גן":  ["רמת גן",  'ר"ג', "ר״ג", "רמת-גן"],
    "גבעתיים": ["גבעתיים", "גבעתים"],
}


class ListingParser:
    def __init__(self, settings: dict):
        self.neighborhoods: dict[str, list[str]] = settings["search"]["neighborhoods"]

    def parse(self, raw: dict) -> Listing:
        text = raw["text"]
        listing = Listing(
            post_id=raw["post_id"],
            post_url=raw["post_url"],
            raw_text=text,
            author=raw.get("author", ""),
        )
        listing.city         = self._extract_city(text)
        listing.neighborhood = self._extract_neighborhood(text)
        # Infer city from neighborhood when city not explicitly mentioned
        if listing.city is None and listing.neighborhood is not None:
            listing.city = self._city_from_neighborhood(listing.neighborhood)
        listing.rooms      = self._extract_rooms(text)
        listing.price      = self._extract_price(text)
        listing.floor      = self._extract_floor(text)
        listing.has_broker = self._extract_broker(text)
        listing.balcony    = bool(re.search(r"מרפסת", text))
        listing.parking    = bool(re.search(r"חניי?ה", text))
        listing.shelter    = bool(re.search(r'ממ["״]?ד|מרחב\s+מוגן', text))
        return listing

    # ------------------------------------------------------------------ #

    def _extract_rooms(self, text: str):
        patterns = [
            r"(\d+(?:[.,]\d+)?)\s*(?:חדרים|חדר)\b",
            r"(\d+(?:[.,]\d+)?)\s*חד['׳״]",
            r"דירת\s+(\d+(?:[.,]\d+)?)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                try:
                    return float(m.group(1).replace(",", "."))
                except ValueError:
                    continue
        return None

    def _extract_price(self, text: str):
        patterns = [
            r"(\d[\d,]+)\s*₪",                        # 5,500 ₪
            r"(\d[\d,]+)\s*ש[\"'׳״]ח",               # ש"ח / ש'ח
            r"(?:שכירות|מחיר|עלות)\s*[:\-]?\s*(\d[\d,]+)",
            r"(\d[\d,]+)\s*(?:לחודש|בחודש)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                val = int(m.group(1).replace(",", ""))
                if 1000 <= val <= 50000:
                    return val
        return None

    def _extract_city(self, text: str):
        for canonical, aliases in CITY_ALIASES.items():
            for alias in aliases:
                if alias in text:
                    return canonical
        return None

    def _extract_neighborhood(self, text: str):
        for hoods in self.neighborhoods.values():
            for hood in hoods:
                if hood in text:
                    return hood
        return None

    def _city_from_neighborhood(self, neighborhood: str):
        for city, hoods in self.neighborhoods.items():
            if neighborhood in hoods:
                return city
        return None

    def _extract_broker(self, text: str) -> bool:
        no_broker_patterns = [
            r"ללא\s+תיווך", r"בלי\s+תיווך", r"אין\s+תיווך",
        ]
        for p in no_broker_patterns:
            if re.search(p, text):
                return False  # explicitly no broker

        has_broker_patterns = [
            r"דמי\s+תיווך", r"עמלת\s+תיווך",
            r"מתווך",   # covers למתווך, המתווך, etc.
            r"תיווך",   # catches any remaining mention of the word
        ]
        for p in has_broker_patterns:
            if re.search(p, text):
                return True

        return False  # not mentioned → assume no broker

    def _extract_floor(self, text: str):
        m = re.search(r"קומה\s+(\d+)", text)
        if m:
            return int(m.group(1))
        m = re.search(r"קומת\s+(\w+)", text)
        if m:
            return FLOOR_WORDS.get(m.group(1))
        m = re.search(r"קומה\s+(\w+)", text)
        if m:
            return FLOOR_WORDS.get(m.group(1))
        return None
