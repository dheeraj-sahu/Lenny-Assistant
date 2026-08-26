"""
agent/tools/search_transcripts_tool.py

Tool definition and handler for search_transcripts.

This is the ONLY channel through which the agent can bring factual claims about
Lenny's podcast into the conversation. Structuring it as an explicit tool rather
than pre-filling the context is intentional: it makes retrieval visible, logged,
and auditable in the agent's tool-use trace.
"""

from retrieval.retrieval_service import (
    chunks_to_citations,
    format_chunks_for_prompt,
    retrieve,
)

# ── Anthropic tool definition ─────────────────────────────────────────────────

SEARCH_TRANSCRIPTS_TOOL_DEFINITION = {
    "name": "search_transcripts",
    "description": (
        "Search Lenny's Podcast transcript knowledge base for relevant content. "
        "Use this before making ANY substantive claim about product management, growth, "
        "pricing, retention, hiring, or other topics covered in the podcast. "
        "Returns transcript chunks with speaker, episode, and timestamp information."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language search query. Be specific.",
            },
            "topic_hint": {
                "type": "string",
                "description": (
                    "Optional topic keyword to narrow results (e.g. 'pricing', 'growth', "
                    "'retention', 'hiring'). Leave empty for broad queries."
                ),
            },
        },
        "required": ["query"],
    },
}


# ── Tool handler ──────────────────────────────────────────────────────────────

def handle_search_transcripts(query: str, topic_hint: str | None = None) -> dict:
    """
    Execute a retrieval call and return a structured tool result.

    Returns:
        A dict with:
          - found: bool
          - formatted_text: str  (for injection into the next agent prompt)
          - citations: list[dict]  (for the SSE done event sources[])
          - top_score: float
    """
    result = retrieve(query=query, topic_hint=topic_hint)

    if not result.found:
        return {
            "found": False,
            "formatted_text": (
                "No relevant transcript content found for this query. "
                "The knowledge base does not support an answer to this question."
            ),
            "citations": [],
            "top_score": 0.0,
        }

    return {
        "found": True,
        "formatted_text": format_chunks_for_prompt(result.chunks),
        "citations": chunks_to_citations(result.chunks),
        "top_score": result.top_score,
    }
