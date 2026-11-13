"""Retrieve knowledge-base sections for a ticket and decide whether they are good enough to use.

Three gates protect generation (all thresholds are configurable, see README "Calibration"):

1. low_score      - the best section scores below MIN_SCORE: nothing in the knowledge base is close.
2. no_clear_match - the best section is below CONFIDENT_SCORE *and* the best section of another guide
                    is within AMBIGUITY_MARGIN of it. Vague tickets ("it's not working") and requests
                    no guide covers ("install Photoshop") typically look like this: several guides
                    match weakly and almost equally. Real matches have one clearly leading guide.
3. low_evidence   - the ticket shares fewer than MIN_SHARED_TERMS concrete words (service names, symptoms,
                    error text, devices) with the best guide. Embeddings can find a weak semantic match for
                    "something is weird with my computer"; this lexical check asks for concrete evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .index import VectorIndex
from .text import content_tokens

QueryEmbedder = Callable[[str], list[float]]

GATE_OK = "ok"
GATE_EMPTY_INDEX = "empty_index"
GATE_LOW_SCORE = "low_score"
GATE_NO_CLEAR_MATCH = "no_clear_match"
GATE_LOW_EVIDENCE = "low_evidence"


@dataclass(frozen=True)
class Hit:
    section_id: str
    doc_id: str
    doc_title: str
    heading: str
    anchor: str
    text: str
    score: float

    @property
    def url(self) -> str:
        return f"/kb/{self.doc_id}#{self.anchor}"


@dataclass
class RetrievalResult:
    hits: list[Hit]                                   # top-k sections, best first
    context: list[Hit] = field(default_factory=list)  # sections passed to the model
    gate: str = GATE_OK
    top_score: float = 0.0
    doc_margin: float = 0.0                           # best guide score minus best score of any other guide
    guide_scores: dict[str, float] = field(default_factory=dict)
    guide_titles: dict[str, str] = field(default_factory=dict)
    shared_terms: list[str] = field(default_factory=list)  # ticket words found in the best guide

    @property
    def context_ids(self) -> set[str]:
        return {h.section_id for h in self.context}

    def closest_guides(self, n: int = 2) -> list[str]:
        ranked = sorted(self.guide_scores.items(), key=lambda kv: -kv[1])[:n]
        return [self.guide_titles.get(doc, doc) for doc, _ in ranked]


class Retriever:
    def __init__(self, index: VectorIndex, embed_query: QueryEmbedder, *, top_k: int, min_score: float,
                 context_window: float, ambiguity_margin: float, confident_score: float,
                 min_shared_terms: int = 0) -> None:
        self.index = index
        self.embed_query = embed_query
        self.top_k = top_k
        self.min_score = min_score
        self.context_window = context_window
        self.ambiguity_margin = ambiguity_margin
        self.confident_score = confident_score
        self.min_shared_terms = min_shared_terms

    def retrieve(self, ticket: str) -> RetrievalResult:
        total = self.index.count()
        if total == 0:
            return RetrievalResult(hits=[], gate=GATE_EMPTY_INDEX)

        # Exact search over every section (cheap for a small KB) so per-guide scores are complete.
        ranked = self.index.search(self.embed_query(ticket), total)
        all_hits = [Hit(c.id, c.doc_id, c.doc_title, c.heading, c.anchor, c.text, round(score, 4))
                    for c, score in ranked]
        guide_scores: dict[str, float] = {}
        guide_titles: dict[str, str] = {}
        for hit in all_hits:
            guide_scores.setdefault(hit.doc_id, hit.score)
            guide_titles.setdefault(hit.doc_id, hit.doc_title)

        top = all_hits[0].score
        others = [score for doc, score in guide_scores.items() if doc != all_hits[0].doc_id]
        margin = round(top - max(others), 4) if others else 1.0
        result = RetrievalResult(hits=all_hits[: self.top_k], top_score=top, doc_margin=margin,
                                 guide_scores=guide_scores, guide_titles=guide_titles)

        guide_text = self.index.doc_texts().get(all_hits[0].doc_id, "")
        result.shared_terms = sorted(content_tokens(ticket) & content_tokens(guide_text))

        if top < self.min_score:
            result.gate = GATE_LOW_SCORE
        elif top < self.confident_score and margin < self.ambiguity_margin:
            result.gate = GATE_NO_CLEAR_MATCH
        elif len(result.shared_terms) < self.min_shared_terms:
            result.gate = GATE_LOW_EVIDENCE
        else:
            result.context = [h for h in result.hits
                              if h.score >= self.min_score and h.score >= top - self.context_window]
        return result
