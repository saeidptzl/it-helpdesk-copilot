"""Small lexical helpers used next to the embeddings: shared-term counts and step support scores."""

from __future__ import annotations

import re

STOPWORDS = {
    "that", "this", "with", "from", "your", "have", "they", "them", "then", "than", "when", "what", "will",
    "into", "only", "also", "make", "sure", "check", "please", "user", "users", "their", "there", "these",
    "those", "should", "could", "would", "after", "before", "again", "about", "which", "while", "being",
    "does", "done", "each", "other", "more", "most", "some", "such", "same", "very", "just", "over", "under",
    "ensure", "verify", "confirm", "follow", "using", "used", "step", "steps", "help", "issue", "problem",
}


def content_tokens(text: str) -> set[str]:
    """Lower-case content words of 4+ characters, cut to a 5-character prefix (restart ~ restarting)."""
    return {t[:5] for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 4 and t not in STOPWORDS}


def support_score(step_text: str, source_text: str) -> float:
    """Share of the step's content words that also appear in the source text (0.0 - 1.0)."""
    words = content_tokens(step_text)
    if not words:
        return 0.0
    return round(len(words & content_tokens(source_text)) / len(words), 3)
