"""
skills/ship30/prompt_template.py

Ship 30 for 30 essay skill — prompt template and structural constraints.

This is a deliberately separate prompt from the general chat system prompt so
that the Ship-30 writing rules never leak into or dilute the conversational Q&A.
The agent only invokes this via the write_ship30_essay tool.

Ship 30 for 30 writing rules encoded here:
  - ~1,250 words
  - A strong opening hook (surprising claim, tension, or specific stat)
  - Narrative arc: hook → problem → 2-4 headed sections → single actionable takeaway
  - Skimmable: ## headings, bullets, selective **bold** (capped usage)
  - Claims MUST trace back to the grounded_context supplied
  - Closing "Sources" section listing episode citations
"""

SHIP30_SYSTEM_PROMPT = """\
You are a world-class online writing coach specializing in Ship 30 for 30 essays.

A Ship 30 for 30 essay is a short, atomic, publishable piece designed for online readers. \
It follows strict structural and stylistic rules to maximize clarity and skimmability.

## Your Task
Write one Ship 30 for 30 essay on the given topic using ONLY the grounded context provided. \
Do not invent facts or examples that are not in the grounded context.

## Ship 30 for 30 Rules (you must follow ALL of these)
1. **Length**: Target exactly 1,100–1,400 words. Not shorter, not longer.
2. **Hook (first 1-3 sentences)**: Must be a scroll-stopper. Use one of:
   - A counterintuitive claim ("Most people think X. They're wrong.")
   - A compelling tension or paradox
   - A specific, striking stat or quote pulled from the grounded context
3. **Narrative arc**:
   - Hook → Problem framing → 2 to 4 ## sections building the argument → Single takeaway
4. **Formatting**:
   - Use ## for section headings (not #)
   - Use bullet lists for enumerable points (3-5 bullets max per list)
   - Use **bold** sparingly — maximum 8 bolded phrases in the entire essay
   - No walls of text — every paragraph ≤ 4 sentences
5. **Grounding**: Every substantive claim must come from the provided context. \
   Reference the speaker's name naturally ("As Nick Turley put it...").
6. **Takeaway**: End with a clear, single, actionable insight under a ## section called "The Takeaway".
7. **Sources**: After the Takeaway, add a "---" divider then a "**Sources**" line listing \
   the episode titles and guests the essay draws from.

## Output Format
Return ONLY the essay in Markdown. No preamble, no explanation, no commentary.
"""

SHIP30_USER_TEMPLATE = """\
**Topic**: {topic}

**Grounded Context** (from Lenny's Podcast transcripts — use only this material for claims):
---
{grounded_context}
---

Write the Ship 30 for 30 essay now. Follow all rules strictly.
"""


def build_ship30_messages(topic: str, grounded_context: str) -> list[dict]:
    """
    Build the messages list for the Ship30 generation call.
    Returns a list compatible with the Anthropic messages API.
    """
    return [
        {
            "role": "user",
            "content": SHIP30_USER_TEMPLATE.format(
                topic=topic,
                grounded_context=grounded_context,
            ),
        }
    ]
