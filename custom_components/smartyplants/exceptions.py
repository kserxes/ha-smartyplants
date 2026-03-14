"""Exceptions for the SmartyPlants API client."""


class SmartyPlantsError(Exception):
    """Base exception for SmartyPlants API errors."""


class SmartyPlantsAuthError(SmartyPlantsError):
    """Raised when authentication fails irrecoverably.

    For example: refresh token expired, bad credentials.
    """


class SmartyPlantsConnectionError(SmartyPlantsError):
    """Raised when the API is unreachable."""
