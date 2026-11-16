import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.listing_parser import ListingParser
from filter.listing_filter import ListingFilter

# Mirrors config/settings.yaml
SETTINGS = {
    "search": {
        "cities": ["תל אביב", "רמת גן", "גבעתיים"],
        "neighborhoods": {
            "גבעתיים": ["קריית יוסף", "סיטי", 'הל"ה', "בורוכוב"],
            "רמת גן":  ["הראשונים", "הבורסה", "תל בנימין", "חשמונאים", "גפן"],
            "תל אביב": ["הצפון הישן", "צמרות איילון", "מונטיפיורי", "נחלת יצחק"],
        },
        "rooms":    {"min": 2, "max": 3},
        "price":    {"max": 6000, "skip_if_no_price": True},
        "floor":    {"min": None, "max": None},
        "features": {"no_broker": True, "balcony": False, "parking": False, "shelter": False},
    }
}


def raw(text, post_id="1"):
    return {"post_id": post_id, "post_url": "https://facebook.com/test", "text": text, "author": ""}


class TestParser(unittest.TestCase):
    def setUp(self):
        self.parser = ListingParser(SETTINGS)

    # ------------------------------------------------------------------ #
    # The exact post the user shared — this must pass everything
    # ------------------------------------------------------------------ #
    def test_real_borokhov_post(self):
        text = (
            "ללא תיווך -שכונת קריית בורוכוב רמת גן\n"
            "דירת גן כ- 30 מטר\n"
            "2 חדרים חדשה\n"
            "גינה מקסימה כ20 מטר\n"
            "קרובה לתחבורה צבורית ולכל היציאות\n"
            "מחיר -4,400 ש'ח כולל ארנונה , מים , אינטרנט ועד בית למעט חשמל .\n"
            "2 טלויזיות + בסיס מיטה , ארון 3 דלתות\n"
            "חניה בקרבת מקום\n"
            "כניסה בחודש יוני (גמיש) 👌\n"
            "0509978977 -דניאל"
        )
        listing = self.parser.parse(raw(text))
        self.assertEqual(listing.city, "רמת גן",      "city should be רמת גן")
        self.assertEqual(listing.neighborhood, "בורוכוב", "neighborhood should be בורוכוב")
        self.assertEqual(listing.rooms, 2.0,            "rooms should be 2")
        self.assertEqual(listing.price, 4400,           "price should be 4400")
        self.assertFalse(listing.has_broker,            "should have no broker")
        self.assertTrue(listing.parking,                "should detect parking")

    # ------------------------------------------------------------------ #
    # Rooms
    # ------------------------------------------------------------------ #
    def test_rooms_plain(self):
        self.assertEqual(self.parser.parse(raw("3 חדרים בתל אביב")).rooms, 3.0)

    def test_rooms_half(self):
        self.assertEqual(self.parser.parse(raw("2.5 חדרים")).rooms, 2.5)

    def test_rooms_geresh(self):
        self.assertEqual(self.parser.parse(raw("3 חד' להשכרה")).rooms, 3.0)

    def test_rooms_dirat(self):
        self.assertEqual(self.parser.parse(raw("דירת 3 חדרים")).rooms, 3.0)

    # ------------------------------------------------------------------ #
    # Price
    # ------------------------------------------------------------------ #
    def test_price_shekel_sign(self):
        self.assertEqual(self.parser.parse(raw("שכירות 5,500 ₪ לחודש")).price, 5500)

    def test_price_shin_double_quote(self):
        self.assertEqual(self.parser.parse(raw('מחיר 5500 ש"ח')).price, 5500)

    def test_price_shin_single_quote(self):
        self.assertEqual(self.parser.parse(raw("מחיר 5500 ש'ח")).price, 5500)

    def test_price_lchodesh(self):
        self.assertEqual(self.parser.parse(raw("6,000 לחודש")).price, 6000)

    def test_price_with_dash(self):
        # "מחיר -4,400 ש'ח" — dash between label and number
        self.assertEqual(self.parser.parse(raw("מחיר -4,400 ש'ח")).price, 4400)

    def test_price_too_low_ignored(self):
        # Phone numbers like 050 should not be treated as prices
        self.assertIsNone(self.parser.parse(raw("050-1234567 ללא מחיר")).price)

    # ------------------------------------------------------------------ #
    # City
    # ------------------------------------------------------------------ #
    def test_city_tel_aviv(self):
        self.assertEqual(self.parser.parse(raw("דירה בתל אביב")).city, "תל אביב")

    def test_city_ramat_gan_abbreviation(self):
        self.assertEqual(self.parser.parse(raw('דירה ב ר"ג')).city, "רמת גן")

    def test_city_givatayim(self):
        self.assertEqual(self.parser.parse(raw("גבעתיים 3 חדרים")).city, "גבעתיים")

    def test_city_inferred_from_neighborhood(self):
        # No city name in text, but neighborhood implies city
        listing = self.parser.parse(raw("דירה בהצפון הישן, 3 חדרים, 5500 ₪"))
        self.assertEqual(listing.city, "תל אביב")

    # ------------------------------------------------------------------ #
    # Neighborhood
    # ------------------------------------------------------------------ #
    def test_neighborhood_borokhov(self):
        listing = self.parser.parse(raw("קריית בורוכוב רמת גן"))
        self.assertEqual(listing.neighborhood, "בורוכוב")

    def test_neighborhood_north_tel_aviv(self):
        listing = self.parser.parse(raw("הצפון הישן תל אביב"))
        self.assertEqual(listing.neighborhood, "הצפון הישן")

    def test_neighborhood_none_when_not_mentioned(self):
        listing = self.parser.parse(raw("דירה בתל אביב 3 חדרים"))
        self.assertIsNone(listing.neighborhood)

    # ------------------------------------------------------------------ #
    # Broker
    # ------------------------------------------------------------------ #
    def test_no_broker_explicit(self):
        self.assertFalse(self.parser.parse(raw("ללא תיווך")).has_broker)

    def test_no_broker_bli(self):
        self.assertFalse(self.parser.parse(raw("בלי תיווך")).has_broker)

    def test_has_broker_dmai(self):
        self.assertTrue(self.parser.parse(raw("דמי תיווך חצי חודש")).has_broker)

    def test_has_broker_metavech(self):
        self.assertTrue(self.parser.parse(raw("פנו למתווך")).has_broker)

    # ------------------------------------------------------------------ #
    # Features
    # ------------------------------------------------------------------ #
    def test_balcony(self):
        self.assertTrue(self.parser.parse(raw("מרפסת גדולה")).balcony)

    def test_parking(self):
        self.assertTrue(self.parser.parse(raw("חניה פרטית")).parking)
        self.assertTrue(self.parser.parse(raw("חנייה בחצר")).parking)

    def test_shelter(self):
        self.assertTrue(self.parser.parse(raw('יש ממ"ד')).shelter)
        self.assertTrue(self.parser.parse(raw("מרחב מוגן")).shelter)

    # ------------------------------------------------------------------ #
    # Floor
    # ------------------------------------------------------------------ #
    def test_floor_number(self):
        self.assertEqual(self.parser.parse(raw("קומה 4")).floor, 4)

    def test_floor_ground(self):
        self.assertEqual(self.parser.parse(raw("קומת קרקע")).floor, 0)

    def test_floor_word(self):
        self.assertEqual(self.parser.parse(raw("קומה שלישית")).floor, 3)


class TestFilter(unittest.TestCase):
    def setUp(self):
        self.parser = ListingParser(SETTINGS)
        self.filter = ListingFilter(SETTINGS)

    def _listing(self, text, post_id="1"):
        return self.parser.parse(raw(text, post_id))

    def test_borokhov_post_passes(self):
        text = (
            "ללא תיווך -שכונת קריית בורוכוב רמת גן\n"
            "2 חדרים\n"
            "מחיר -4,400 ש'ח\n"
            "חניה בקרבת מקום"
        )
        self.assertTrue(self.filter.matches(self._listing(text)))

    def test_fails_wrong_city(self):
        listing = self._listing("דירה בחיפה, 3 חדרים, 5000 ₪, ללא תיווך")
        self.assertFalse(self.filter.matches(listing))

    def test_fails_too_many_rooms(self):
        listing = self._listing("4 חדרים רמת גן ללא תיווך 5500 ₪")
        self.assertFalse(self.filter.matches(listing))

    def test_fails_price_too_high(self):
        listing = self._listing("3 חדרים תל אביב ללא תיווך 8,000 ₪")
        self.assertFalse(self.filter.matches(listing))

    def test_fails_no_price(self):
        listing = self._listing("3 חדרים גבעתיים ללא תיווך")
        self.assertFalse(self.filter.matches(listing))

    def test_fails_has_broker(self):
        listing = self._listing("3 חדרים רמת גן 5000 ₪ דמי תיווך חצי חודש")
        self.assertFalse(self.filter.matches(listing))

    def test_passes_no_neighborhood_mentioned(self):
        # City matches, no neighborhood in post → should still pass
        listing = self._listing("3 חדרים רמת גן ללא תיווך 5,500 ₪")
        self.assertTrue(self.filter.matches(listing))

    def test_score_all_features(self):
        listing = self._listing('מרפסת, חניה, ממ"ד')
        self.assertEqual(self.filter.score(listing), 3)

    def test_score_no_features(self):
        listing = self._listing("דירה נחמדה")
        self.assertEqual(self.filter.score(listing), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
