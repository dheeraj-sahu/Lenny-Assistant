"""
agent/tools/ship30_tool.py

Tool definition and handler for write_ship30_essay.

Invokes the Ship30 skill (separate system prompt + validation) to generate a
structured essay grounded in previously retrieved content.
Re-prompts once if the draft fails structural validation.
"""

import anthropic as _anthropic

from agent.provider_resolver import build_anthropic_client, get_active_model
from core.logging import get_logger
from skills.ship30.prompt_template import SHIP30_SYSTEM_PROMPT, build_ship30_messages
from skills.ship30.validators import build_correction_prompt, validate_ship30_essay

logger = get_logger(__name__)

# ── Anthropic tool definition ─────────────────────────────────────────────────

WRITE_SHIP30_TOOL_DEFINITION = {
    "name": "write_ship30_essay",
    "description": (
        "Write a Ship 30 for 30-style essay (~1,250 words) grounded in the provided context. "
        "Only invoke this when the user explicitly asks to turn content into a Ship 30 essay. "
        "The tool enforces structure: hook, 2-4 headed sections, single takeaway, citations."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The topic of the essay (1-2 sentences).",
            },
            "grounded_context": {
                "type": "string",
                "description": (
                    "The grounded transcript content to base the essay on. "
                    "Include the relevant chunks and citations from search_transcripts."
                ),
            },
        },
        "required": ["topic", "grounded_context"],
    },
}


# ── Tool handler ──────────────────────────────────────────────────────────────

def handle_write_ship30_essay(topic: str, grounded_context: str) -> dict:
    """
    Generate a Ship 30 essay using a dedicated system prompt.
    Validates the draft and re-prompts once if it fails structural checks.

    Returns:
        {"essay": str, "word_count": int, "validation_passed": bool}
    """
    client = build_anthropic_client()
    model = get_active_model()

    messages = build_ship30_messages(topic, grounded_context)

    logger.info("ship30_generation_start", topic=topic[:80], model=model)

    # ── First attempt ──────────────────────────────────────────────────────
    response = client.messages.create(
        model=model,
        system=SHIP30_SYSTEM_PROMPT,
        messages=messages,
        max_tokens=2_500,
    )
    draft = response.content[0].text

    validation = validate_ship30_essay(draft)
    logger.info(
        "ship30_validation",
        passed=validation.passed,
        word_count=validation.word_count,
        issues=validation.issues,
    )

    if validation.passed:
        return {
            "essay": draft,
            "word_count": validation.word_count,
            "validation_passed": True,
        }

    # ── One correction attempt ─────────────────────────────────────────────
    logger.info("ship30_correction_attempt", issues=validation.issues)
    correction_prompt = build_correction_prompt(draft, validation.issues)
    correction_messages = messages + [
        {"role": "assistant", "content": draft},
        {"role": "user", "content": correction_prompt},
    ]

    correction_response = client.messages.create(
        model=model,
        system=SHIP30_SYSTEM_PROMPT,
        messages=correction_messages,
        max_tokens=2_500,
    )
    corrected = correction_response.content[0].text
    final_validation = validate_ship30_essay(corrected)

    logger.info(
        "ship30_correction_result",
        passed=final_validation.passed,
        word_count=final_validation.word_count,
    )

    return {
        "essay": corrected,
        "word_count": final_validation.word_count,
        "validation_passed": final_validation.passed,
    }
