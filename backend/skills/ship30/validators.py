"""
skills/ship30/validators.py

Post-generation validation for Ship 30 for 30 essays.

If the draft fails word-count or structural checks, the caller gets a
structured result indicating what's wrong so it can re-prompt once.
"""

import re
from dataclasses import dataclass


@dataclass
class ValidationResult:
    passed: bool
    word_count: int
    issues: list[str]


_MIN_WORDS = 1_000
_MAX_WORDS = 1_500
_MIN_H2_SECTIONS = 2
_MAX_BOLD_PHRASES = 12   # generous upper bound; prompt says 8 but allow some slack
_REQUIRED_SECTIONS = ["takeaway", "sources"]


def validate_ship30_essay(essay: str) -> ValidationResult:
    """
    Validate a generated Ship 30 essay against structural rules.

    Returns a ValidationResult with:
      - passed: True if all checks pass
      - word_count: actual word count
      - issues: list of human-readable failure reasons
    """
    issues: list[str] = []

    # ── Word count ──────────────────────────────────────────────────────────
    words = essay.split()
    word_count = len(words)
    if word_count < _MIN_WORDS:
        issues.append(f"Essay is too short ({word_count} words, minimum {_MIN_WORDS}).")
    elif word_count > _MAX_WORDS:
        issues.append(f"Essay is too long ({word_count} words, maximum {_MAX_WORDS}).")

    # ── H2 sections ─────────────────────────────────────────────────────────
    h2_sections = re.findall(r"^##\s+.+", essay, re.MULTILINE)
    if len(h2_sections) < _MIN_H2_SECTIONS:
        issues.append(
            f"Too few ## sections ({len(h2_sections)}, minimum {_MIN_H2_SECTIONS})."
        )

    # ── Required section names (case-insensitive) ────────────────────────────
    essay_lower = essay.lower()
    for required in _REQUIRED_SECTIONS:
        if required not in essay_lower:
            issues.append(f"Missing required section: '{required}'.")

    # ── Bold usage ───────────────────────────────────────────────────────────
    bold_count = len(re.findall(r"\*\*[^*]+\*\*", essay))
    if bold_count > _MAX_BOLD_PHRASES:
        issues.append(
            f"Excessive bold usage ({bold_count} phrases, maximum {_MAX_BOLD_PHRASES}). "
            "Remove some **bold** to improve skimmability."
        )

    # ── Opening hook ────────────────────────────────────────────────────────
    # We just check that the essay doesn't start with a heading — the hook must be prose
    first_non_empty = next((line.strip() for line in essay.split("\n") if line.strip()), "")
    if first_non_empty.startswith("#"):
        issues.append("Essay must start with a prose hook, not a heading.")

    return ValidationResult(
        passed=len(issues) == 0,
        word_count=word_count,
        issues=issues,
    )


def build_correction_prompt(original_draft: str, issues: list[str]) -> str:
    """
    Build a correction instruction to re-prompt once if the draft failed validation.
    """
    issues_text = "\n".join(f"- {issue}" for issue in issues)
    return (
        f"The essay draft has the following issues that must be fixed:\n{issues_text}\n\n"
        f"Revise the essay to fix all issues while keeping the same topic, "
        f"grounding, and narrative structure. Return only the revised essay in Markdown."
    )
