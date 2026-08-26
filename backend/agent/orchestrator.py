"""
agent/orchestrator.py

The Agent Orchestrator wires the Claude Agent SDK multi-turn agent loop:
  user message → think → [tool calls] → think → final answer

It:
  1. Builds the conversation context from session history.
  2. Sends the messages to the configured LLM provider (Ollama or Anthropic).
  3. Handles tool calls (search_transcripts, write_ship30_essay, generate_artifact).
  4. Streams token deltas back to the caller via an async generator.
  5. Emits structured events: {"type": "token", "delta": "..."}, {"type": "done"},
     {"type": "sources", "sources": [...]}, {"type": "artifact_id", "artifact_id": "..."}

The orchestrator never imports "Ollama" or "Anthropic" by name — it uses the
resolved client from provider_resolver.py.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent.provider_resolver import build_anthropic_client, get_active_model
from agent.system_prompt import SYSTEM_PROMPT
from agent.tools.artifact_tool import (
    GENERATE_ARTIFACT_TOOL_DEFINITION,
    handle_generate_artifact,
)
from agent.tools.search_transcripts_tool import (
    SEARCH_TRANSCRIPTS_TOOL_DEFINITION,
    handle_search_transcripts,
)
from agent.tools.ship30_tool import (
    WRITE_SHIP30_TOOL_DEFINITION,
    handle_write_ship30_essay,
)
from core.logging import get_logger
from persistence.models import Message

logger = get_logger(__name__)

# All tools registered with the agent
ALL_TOOLS = [
    SEARCH_TRANSCRIPTS_TOOL_DEFINITION,
    WRITE_SHIP30_TOOL_DEFINITION,
    GENERATE_ARTIFACT_TOOL_DEFINITION,
]

# Max tokens for the agent's response
MAX_TOKENS = 4_096


def _build_messages(history: list[Message], new_user_message: str) -> list[dict]:
    """
    Convert SQLAlchemy Message objects to the Anthropic messages API format.
    Limits history to the last 20 turns to stay within context-window budget.
    """
    # Include up to the last 20 messages (10 turns) for context
    recent_history = history[-20:] if len(history) > 20 else history

    messages = []
    for msg in recent_history:
        # Skip the latest user message — we'll add new_user_message explicitly
        messages.append({"role": msg.role, "content": msg.content})

    # The new user message is already persisted before we're called,
    # so we pop it from history (it's the last item) and add as the user turn
    if messages and messages[-1]["role"] == "user":
        messages[-1]["content"] = new_user_message
    else:
        messages.append({"role": "user", "content": new_user_message})

    return messages


class AgentOrchestrator:
    """
    Runs the multi-turn Claude agent loop and streams results.
    One instance per request — not a singleton.
    """

    def __init__(self):
        self._client = build_anthropic_client()
        self._model = get_active_model()
        self._all_citations: list[dict] = []
        self._artifact_id: str | None = None

    async def run_stream(
        self,
        session_id: uuid.UUID,
        user_message: str,
        history: list[Message],
        db: AsyncSession,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Run the agent loop and yield structured events.

        Yields dicts with one of these shapes:
          {"type": "token",       "delta": str}
          {"type": "sources",     "sources": list}
          {"type": "artifact_id", "artifact_id": str}
          {"type": "done"}
        """
        messages = _build_messages(history, user_message)

        logger.info(
            "agent_run_start",
            session_id=str(session_id),
            model=self._model,
            history_len=len(messages),
        )

        # ── Agentic loop ──────────────────────────────────────────────────────
        # We run up to 5 tool-call rounds to prevent infinite loops
        max_rounds = 5
        current_round = 0

        while current_round < max_rounds:
            current_round += 1
            logger.info("agent_round", round=current_round, model=self._model)

            # Stream the response
            full_response_text = ""
            tool_calls_requested = []

            # Use the Anthropic streaming API
            with self._client.messages.stream(
                model=self._model,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=ALL_TOOLS,
                max_tokens=MAX_TOKENS,
            ) as stream:
                for event in stream:
                    event_type = type(event).__name__

                    # Stream text tokens
                    if event_type == "RawContentBlockDeltaEvent":
                        delta = event.delta
                        if hasattr(delta, "text"):
                            full_response_text += delta.text
                            yield {"type": "token", "delta": delta.text}

                    # Collect tool use blocks
                    elif event_type == "RawContentBlockStopEvent":
                        pass  # handled below via final_message

                # Get the complete message after streaming
                final_message = stream.get_final_message()

            # ── Process the completed message ─────────────────────────────────
            stop_reason = final_message.stop_reason
            logger.info("agent_response", stop_reason=stop_reason, round=current_round)

            # Append the assistant message to conversation context
            messages.append({"role": "assistant", "content": final_message.content})

            # ── Check for tool calls ──────────────────────────────────────────
            if stop_reason == "tool_use":
                tool_results = []

                for block in final_message.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input
                    tool_use_id = block.id

                    logger.info("tool_called", tool=tool_name, input_keys=list(tool_input.keys()))

                    # ── Dispatch to tool handlers ─────────────────────────────
                    try:
                        if tool_name == "search_transcripts":
                            result = handle_search_transcripts(
                                query=tool_input.get("query", ""),
                                topic_hint=tool_input.get("topic_hint"),
                            )
                            if result.get("citations"):
                                self._all_citations.extend(result["citations"])
                                yield {"type": "sources", "sources": self._all_citations}

                            tool_result_content = result["formatted_text"]

                        elif tool_name == "write_ship30_essay":
                            result = handle_write_ship30_essay(
                                topic=tool_input.get("topic", ""),
                                grounded_context=tool_input.get("grounded_context", ""),
                            )
                            tool_result_content = json.dumps(result)

                        elif tool_name == "generate_artifact":
                            result = await handle_generate_artifact(
                                content=tool_input.get("content", ""),
                                artifact_type=tool_input.get("artifact_type", "markdown"),
                                title=tool_input.get("title"),
                                session_id=session_id,
                                db=db,
                            )
                            self._artifact_id = result["artifact_id"]
                            yield {"type": "artifact_id", "artifact_id": self._artifact_id}
                            tool_result_content = json.dumps(result)

                        else:
                            tool_result_content = f"Unknown tool: {tool_name}"
                            logger.warning("unknown_tool", tool=tool_name)

                    except Exception as exc:
                        logger.exception("tool_error", tool=tool_name, error=str(exc))
                        tool_result_content = f"Tool error: {str(exc)}"

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": tool_result_content,
                        }
                    )

                # Feed tool results back into the conversation
                messages.append({"role": "user", "content": tool_results})
                # Continue the loop to get the agent's next response

            else:
                # stop_reason == "end_turn" or "max_tokens" — we're done
                break

        # ── End of loop ───────────────────────────────────────────────────────
        logger.info(
            "agent_run_complete",
            session_id=str(session_id),
            citations=len(self._all_citations),
            has_artifact=bool(self._artifact_id),
        )

        yield {"type": "done"}
