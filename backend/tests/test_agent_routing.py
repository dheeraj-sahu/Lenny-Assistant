"""
tests/test_agent_routing.py

Unit tests for agent tool routing logic:
  - Ship30 validator
  - HTML sanitizer
  - Artifact type classification
"""

import pytest

from artifacts.sanitizer import sanitize_html
from artifacts.artifact_service import classify_artifact_type
from skills.ship30.validators import validate_ship30_essay


# ── Ship30 validator ─────────────────────────────────────────────────────────

def _make_essay(word_count: int = 1_200) -> str:
    """Generate a synthetic essay with the right structure."""
    words = " ".join(["word"] * word_count)
    return (
        f"Most founders get this wrong — and it costs them everything.\n\n"
        f"{words}\n\n"
        f"## Section One\n\nContent here.\n\n"
        f"## Section Two\n\nMore content.\n\n"
        f"## The Takeaway\n\nDo the thing.\n\n"
        f"---\n\n**Sources**\n- Episode 1"
    )


def test_ship30_valid_essay():
    essay = _make_essay(1_200)
    result = validate_ship30_essay(essay)
    assert result.passed is True
    assert result.issues == []


def test_ship30_too_short():
    essay = _make_essay(500)
    result = validate_ship30_essay(essay)
    assert result.passed is False
    assert any("short" in i.lower() for i in result.issues)


def test_ship30_too_long():
    essay = _make_essay(1_600)
    result = validate_ship30_essay(essay)
    assert result.passed is False
    assert any("long" in i.lower() for i in result.issues)


def test_ship30_missing_takeaway():
    essay = (
        "Hook sentence here.\n\n" + " ".join(["word"] * 1_100) + "\n\n"
        "## Section One\n\nContent.\n\n## Section Two\n\nMore.\n\n"
        "---\n\n**Sources**\n- Ep 1"
        # No "The Takeaway" section
    )
    result = validate_ship30_essay(essay)
    assert result.passed is False
    assert any("takeaway" in i.lower() for i in result.issues)


def test_ship30_starts_with_heading():
    essay = "## Wrong Start\n\n" + " ".join(["word"] * 1_200)
    result = validate_ship30_essay(essay)
    assert result.passed is False
    assert any("hook" in i.lower() for i in result.issues)


# ── HTML sanitizer ───────────────────────────────────────────────────────────

def test_sanitizer_removes_script_tags():
    html = "<p>Hello</p><script>alert('xss')</script>"
    sanitized, stripped = sanitize_html(html)
    assert "<script>" not in sanitized
    assert "script_tags" in stripped


def test_sanitizer_removes_event_handlers():
    html = '<p onclick="evil()">Click me</p>'
    sanitized, stripped = sanitize_html(html)
    assert "onclick" not in sanitized
    assert "event_handlers" in stripped


def test_sanitizer_removes_javascript_href():
    html = '<a href="javascript:alert(1)">Click</a>'
    sanitized, stripped = sanitize_html(html)
    assert "javascript:" not in sanitized


def test_sanitizer_keeps_safe_html():
    html = "<h2>Title</h2><p>Some <strong>bold</strong> text.</p><ul><li>Item</li></ul>"
    sanitized, stripped = sanitize_html(html)
    assert "<h2>" in sanitized
    assert "<strong>" in sanitized
    assert "<ul>" in sanitized
    assert stripped == []


def test_sanitizer_removes_iframe():
    html = "<p>Content</p><iframe src='evil.com'></iframe>"
    sanitized, stripped = sanitize_html(html)
    assert "<iframe" not in sanitized
    assert "embedded_frames" in stripped


# ── Artifact type classification ─────────────────────────────────────────────

def test_classify_markdown():
    content = "# Hello\n\nThis is **markdown** content."
    assert classify_artifact_type(content) == "markdown"


def test_classify_html_doctype():
    content = "<!DOCTYPE html><html><body><p>Hi</p></body></html>"
    assert classify_artifact_type(content) == "html"


def test_classify_html_tags():
    content = "<div><p>Some content</p><ul><li>Item</li></ul></div>"
    assert classify_artifact_type(content) == "html"
