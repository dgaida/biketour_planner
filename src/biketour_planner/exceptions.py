"""Custom exceptions for Bike Tour Planner."""


class BikeTourPlannerError(Exception):
    """Base exception for all application errors."""

    pass


class ExternalServiceError(BikeTourPlannerError, ValueError):
    """Raised when an external service is unavailable or returns an error."""

    def __init__(self, service: str, details: str):
        self.service = service
        self.details = details
        # Inherit from ValueError to maintain compatibility with existing tests
        super().__init__(f"{service} error: {details}")


class GeocodingError(ExternalServiceError):
    """Geocoding service error."""

    def __init__(self, address: str, details: str):
        super().__init__("Geocoding", f"Failed to geocode '{address}': {details}")


class RoutingError(ExternalServiceError):
    """Routing service error."""

    def __init__(self, details: str):
        super().__init__("Routing", details)


class ParsingError(BikeTourPlannerError, ValueError):
    """Raised when input data (HTML, GPX) cannot be parsed."""

    pass
