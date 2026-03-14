"""Conftest for live API tests.

Overrides HA test framework's socket blocking so we can make real
HTTP requests to the SmartyPlants API.
"""

import pytest
from pytest_socket import _remove_restrictions


@pytest.fixture(autouse=True)
def _allow_real_network():
    """Re-enable real sockets and remove connect restrictions."""
    _remove_restrictions()
    yield


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """Override the root conftest fixture - not needed for live tests."""
    yield
