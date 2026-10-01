"""Unit tests for application configuration helpers."""

from app.config import Settings


def test_cors_origins_ignores_empty_entries():
    settings = Settings(cors_origins="http://localhost:5173, ,http://localhost:3000,")

    assert settings.cors_origins_list == [
        "http://localhost:5173",
        "http://localhost:3000",
    ]