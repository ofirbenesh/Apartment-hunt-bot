from models.listing import Listing


class ListingFilter:
    def __init__(self, settings: dict):
        s = settings["search"]
        self.cities              = s["cities"]
        self.neighborhoods       = s["neighborhoods"]
        self.rooms_min           = s["rooms"]["min"]
        self.rooms_max           = s["rooms"]["max"]
        self.price_max           = s["price"]["max"]
        self.skip_no_price       = s["price"]["skip_if_no_price"]
        self.require_no_broker   = s["features"]["no_broker"]

    def matches(self, listing: Listing) -> bool:
        if listing.city not in self.cities:
            return False

        # Neighborhood is informational only — not a hard filter.
        # Too many spelling variations in real posts, and many posts skip the neighborhood name.

        if listing.rooms is None:
            return False
        if not (self.rooms_min <= listing.rooms <= self.rooms_max):
            return False

        if listing.price is None and self.skip_no_price:
            return False
        if listing.price and listing.price > self.price_max:
            return False

        if self.require_no_broker and listing.has_broker:
            return False

        return True

    def score(self, listing: Listing) -> int:
        return sum([listing.balcony, listing.parking, listing.shelter])
