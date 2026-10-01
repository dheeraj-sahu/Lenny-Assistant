"""Unit tests for request schema normalization and validation."""

import pytest
from pydantic import ValidationError

from schemas.message_schemas import SendMessageRequest


def test_send_message_strips_surrounding_whitespace():
    request = SendMessageRequest(content="  How do I improve retention?  ")

    assert request.content == "How do I improve retention?"


def test_send_message_rejects_blank_content():
    with pytest.raises(ValidationError):
        SendMessageRequest(content="   ")