"""Domain errors. Each maps to an HTTP status and a message the frontend shows to the user."""


class ItineraryError(Exception):
    status_code = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class CityNotFound(ItineraryError):
    status_code = 404

    def __init__(self, query: str):
        super().__init__(f"We couldn't find a city called “{query}”. Check the spelling and try again.")


class NotEnoughAttractions(ItineraryError):
    status_code = 422

    def __init__(self, city: str, days: int):
        super().__init__(
            f"We couldn't find enough attractions in {city} for {days} days. Try fewer days or a larger city."
        )


class UpstreamError(ItineraryError):
    status_code = 502

    def __init__(self, detail: str = ""):
        super().__init__("The itinerary service is having trouble reaching Google. Try again in a minute.")
        self.detail = detail  # for logs only


class PlanningTimeout(ItineraryError):
    status_code = 504

    def __init__(self) -> None:
        super().__init__("Planning took too long. Try again.")


class NotConfigured(ItineraryError):
    status_code = 500

    def __init__(self) -> None:
        super().__init__("The itinerary service isn't configured yet. Try again later.")


class ItineraryNotFound(ItineraryError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("This itinerary link doesn't exist or was removed. Check that you copied the whole link.")


class NotSignedIn(ItineraryError):
    status_code = 401

    def __init__(self) -> None:
        super().__init__("Sign in to save itineraries.")


class StorageError(ItineraryError):
    status_code = 503

    def __init__(self, detail: str = ""):
        super().__init__("Saved and shared itineraries are unavailable right now. Try again in a minute.")
        self.detail = detail  # for logs only
