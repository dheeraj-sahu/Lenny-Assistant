"""
artifacts/sanitizer.py

Server-side HTML sanitization using nh3 (Rust-based, fast, WHATWG-compliant).

Defense layer 1: strip dangerous HTML before persisting to the database.
Defense layer 2 (in the frontend): sandboxed iframe rendering.

What is ALLOWED:
  - Standard text formatting: p, br, h1-h6, strong, em, b, i, u, s
  - Lists: ul, ol, li
  - Tables: table, thead, tbody, tr, th, td
  - Links: a[href] (http/https only)
  - Images: img[src, alt, width, height] (http/https src only)
  - Code: code, pre
  - Structural: div, span, section, article, header, footer, nav, main
  - Styling attributes: class, id, style (filtered inline properties)

What is BLOCKED (stripped completely):
  - <script> tags and all JavaScript
  - Inline event handlers (onclick, onload, onerror, etc.)
  - <iframe>, <object>, <embed>, <applet>
  - External resource loaders: <link rel="stylesheet"> pointing to unknown origins
  - data: URIs in src/href
  - javascript: protocol in href
"""

import re
from typing import Literal

import nh3

from core.logging import get_logger

logger = get_logger(__name__)

# Tags that are fully allowed (nh3 strips everything not in this set)
_ALLOWED_TAGS = {
    "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "b", "i", "u", "s", "del", "ins", "mark",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
    "a",
    "img",
    "code", "pre", "blockquote",
    "div", "span", "section", "article", "header", "footer", "nav", "main", "aside",
    "figure", "figcaption",
    "details", "summary",
}

# Per-tag allowed attributes
_ALLOWED_ATTRS: dict[str, set[str]] = {
    "a": {"href", "title", "target", "rel"},
    "img": {"src", "alt", "width", "height", "title"},
    "td": {"colspan", "rowspan", "align", "valign"},
    "th": {"colspan", "rowspan", "align", "valign", "scope"},
    "*": {"class", "id"},  # allowed on all tags
}

# URL schemes allowed in href/src
_ALLOWED_URL_SCHEMES = {"http", "https"}


def sanitize_html(raw_html: str) -> tuple[str, list[str]]:
    """
    Sanitize raw HTML using nh3.

    Returns:
        (sanitized_html, list_of_what_was_stripped)
    """
    stripped_items: list[str] = []

    # Log and track if script tags were present (before nh3 removes them)
    if re.search(r"<script", raw_html, re.IGNORECASE):
        stripped_items.append("script_tags")
    if re.search(r"\bon\w+\s*=", raw_html, re.IGNORECASE):
        stripped_items.append("event_handlers")
    if re.search(r"javascript:", raw_html, re.IGNORECASE):
        stripped_items.append("javascript_urls")
    if re.search(r"<(iframe|object|embed|applet)", raw_html, re.IGNORECASE):
        stripped_items.append("embedded_frames")

    # nh3 does the actual sanitization
    sanitized = nh3.clean(
        raw_html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        url_schemes=_ALLOWED_URL_SCHEMES,
        strip_comments=True,
    )

    if stripped_items:
        logger.warning(
            "html_sanitized",
            stripped=stripped_items,
            original_len=len(raw_html),
            sanitized_len=len(sanitized),
        )

    return sanitized, stripped_items


def sanitize_content(content: str, artifact_type: Literal["markdown", "html"]) -> str:
    """
    Dispatch sanitization based on artifact type.
    Markdown artifacts are returned as-is (rendered client-side via react-markdown,
    which is safe by default). Only HTML goes through nh3.
    """
    if artifact_type == "html":
        sanitized, _ = sanitize_html(content)
        return sanitized
    # For markdown: no server-side mutation; react-markdown handles safe rendering
    return content
