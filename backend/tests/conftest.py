"""
tests/conftest.py

Shared pytest fixtures and configuration.
"""

import pytest


# Tell pytest-asyncio to use "auto" mode for all tests in this suite
# (avoids having to mark every async test explicitly)
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
