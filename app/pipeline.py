"""End-to-end answer pipeline: retrieve -> gate -> generate -> validate citations."""

from __future__ import annotations

import html
import json
import re
import time
from typing import Any, Callable

from .ollama_client import OllamaGenerationError
from .prompts import ANSWER_SCHEMA, SYSTEM_PROMPT, build_user_message
from .text import support_score
from .retrieval import (GATE_EMPTY_INDEX, GATE_LOW_EVIDENCE, GATE_LOW_SCORE, GATE_NO_CLEAR_MATCH, GATE_OK,
                        Hit, RetrievalResult, Retriever)

# llm(system_prompt, user_message, json_schema, attempt=1) -> raw JSON text
LLM = Callable[..., str]

MODE_ANSWER = "answer"
MODE_CLARIFY = "clarify"
MODE_NO_SOURCES = "insufficient_sources"

MAX_STEPS = 5
SUPPORT_TOLERANCE = 0.1  # proposed citations within this of the best support are kept


class TicketError(ValueError):
    """Raised for empty or oversized tickets."""


def answer_ticket(ticket: str, retriever: Retriever, llm: LLM, *, max_chars: int = 4000,
                  model_name: str = "", min_grounding: float = 0.0) -> dict[str, Any]:
    ticket = (ticket or "").strip()
    if not ticket:
        raise TicketError("The ticket is empty.")
    if len(ticket) > max_chars:
        raise TicketError(f"The ticket is longer than {max_chars} characters.")

    started = time.perf_counter()
    retrieval = retriever.retrieve(ticket)

    if retrieval.gate != GATE_OK:
        response = _no_sources_response(retrieval)
        response["diagnostics"] = {"llm_called": False, "model": model_name,
                                   "latency_ms": round((time.perf_counter() - started) * 1000)}
        response["retrieval"] = retrieval_info(retrieval, retriever)
        return response

    user_message = build_user_message(ticket, retrieval.context)
    parsed, attempts, errors = _generate(llm, user_message)
    if parsed is None:
        response = _no_sources_response(retrieval, reason="generation_failed")
        response["diagnostics"] = {"llm_called": True, "attempts": attempts, "model": model_name,
                                   "generation_errors": errors,
                                   "latency_ms": round((time.perf_counter() - started) * 1000)}
        response["retrieval"] = retrieval_info(retrieval, retriever)
        return response

    response = _validate(parsed, retrieval, min_grounding)
    response["diagnostics"].update({"llm_called": True, "attempts": attempts, "model": model_name,
                                    "generation_errors": errors,
                                    "latency_ms": round((time.perf_counter() - started) * 1000)})
    response["retrieval"] = retrieval_info(retrieval, retriever)
    return response


def _generate(llm: LLM, user_message: str) -> tuple[dict[str, Any] | None, int, list[str]]:
    """Call the model; retry once if the output is not a JSON object or the model aborts."""
    errors: list[str] = []
    for attempt in (1, 2):
        message = user_message if attempt == 1 else user_message + "\n\nReturn valid JSON only."
        try:
            raw = llm(SYSTEM_PROMPT, message, ANSWER_SCHEMA, attempt=attempt)
        except OllamaGenerationError as exc:
            errors.append(f"attempt {attempt}: {exc}")
            continue
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            errors.append(f"attempt {attempt}: output was not valid JSON")
            continue
        if isinstance(data, dict):
            return data, attempt, errors
        errors.append(f"attempt {attempt}: output was not a JSON object")
    return None, 2, errors


def _text(value: Any) -> str:
    """Model output as plain text. Sources are sent HTML-escaped, so undo entities the model copies (&gt;)."""
    return html.unescape(str(value or "")).strip()


def _clean_id(value: Any) -> str:
    return re.sub(r"^[\s\[\(\"'`]+|[\s\]\)\"'`.,;]+$", "", str(value))


def grounding_score(step_text: str, source_texts: list[str]) -> float:
    """Best support of a step by any of the given source texts (see app.text.support_score)."""
    return max((support_score(step_text, text) for text in source_texts), default=0.0)


def _validate(data: dict[str, Any], retrieval: RetrievalResult, min_grounding: float = 0.0) -> dict[str, Any]:
    """Keep only steps supported by retrieved sections and attribute each step to its supporting section.

    The model proposes `source_ids`, but the application decides the final citations: the retrieved section
    whose text supports the step best is always cited, and a proposed id is kept as well only if it was
    retrieved for this ticket and supports the step almost as well (within SUPPORT_TOLERANCE). Steps that
    no retrieved section supports (best support < min_grounding) are removed.
    """
    allowed = {h.section_id: h for h in retrieval.context}
    steps: list[dict[str, Any]] = []
    invalid_ids: list[str] = []
    dropped = 0
    reattributed = 0
    ungrounded: list[dict[str, Any]] = []

    raw_steps = data.get("steps") if isinstance(data.get("steps"), list) else []
    for step in raw_steps:
        if not isinstance(step, dict):
            dropped += 1
            continue
        text = _text(step.get("text"))
        ids = step.get("source_ids") if isinstance(step.get("source_ids"), list) else []
        proposed: list[str] = []
        for raw_id in ids:
            cleaned = _clean_id(raw_id)
            if cleaned in allowed and cleaned not in proposed:
                proposed.append(cleaned)
            elif cleaned not in allowed:
                invalid_ids.append(cleaned)
        if not text:
            dropped += 1
            continue

        support = {sid: support_score(text, f"{hit.heading}\n{hit.text}") for sid, hit in allowed.items()}
        best = max(support, key=support.get) if support else None
        if best is None or support[best] <= 0 or support[best] < min_grounding:
            dropped += 1
            ungrounded.append({"text": text[:160], "best_support": support[best] if best else 0.0})
            continue
        # The best-supporting retrieved section is always cited; a section the model proposed is kept as
        # well only if it supports the step almost as well.
        citations = [best] + [sid for sid in proposed
                              if sid != best and support[sid] >= max(min_grounding, support[best] - SUPPORT_TOLERANCE)]
        if set(citations) != set(proposed):
            reattributed += 1
        steps.append({"text": text, "citations": citations, "support": support[best]})
    steps = steps[:MAX_STEPS]

    cited: list[str] = []
    for step in steps:
        for cid in step["citations"]:
            if cid not in cited:
                cited.append(cid)
    citations = [_citation(allowed[cid]) for cid in cited]

    needs_more_info = bool(data.get("needs_more_info")) or not steps
    question = _text(data.get("clarifying_question"))
    if needs_more_info and not question:
        question = ("Could you describe exactly what happens, which service or device is affected, "
                    "and the full error message?")

    mode = MODE_ANSWER if steps else MODE_CLARIFY
    return {
        "mode": mode,
        "summary": _text(data.get("summary")),
        "steps": steps,
        "citations": citations,
        "clarifying_question": question if needs_more_info else "",
        "escalation": {
            "recommended": bool(data.get("escalate")),
            "reason": _text(data.get("escalation_reason")) if data.get("escalate") else "",
        },
        "draft_reply": _text(data.get("draft_reply")),
        "diagnostics": {"dropped_steps": dropped, "reattributed_steps": reattributed,
                        "invalid_citation_ids": invalid_ids[:10], "ungrounded_steps": ungrounded,
                        "min_grounding": min_grounding},
    }


def _citation(hit: Hit) -> dict[str, Any]:
    return {"id": hit.section_id, "doc_id": hit.doc_id, "guide": hit.doc_title,
            "section": hit.heading, "url": hit.url, "score": hit.score}


def _no_sources_response(retrieval: RetrievalResult, reason: str | None = None) -> dict[str, Any]:
    reason = reason or retrieval.gate
    if reason == GATE_EMPTY_INDEX:
        summary = "The knowledge-base index is empty, so no guidance can be given yet."
        question = ""
        escalation = {"recommended": False, "reason": ""}
    elif reason == "generation_failed":
        summary = "The local model did not return a valid answer for this ticket."
        question = "Please review the ticket manually or try again."
        escalation = {"recommended": True, "reason": "Automatic drafting failed; a human agent should handle this ticket."}
    else:  # GATE_LOW_SCORE, GATE_NO_CLEAR_MATCH or GATE_LOW_EVIDENCE
        closest = " and ".join(retrieval.closest_guides(2))
        if reason == GATE_NO_CLEAR_MATCH:
            summary = (f"No single guide clearly covers this ticket (closest weak matches: {closest}), "
                       "so the assistant does not guess troubleshooting steps.")
        elif reason == GATE_LOW_EVIDENCE:
            summary = ("The ticket does not name a specific symptom, error message, device or service that "
                       f"matches a guide (closest weak match: {retrieval.closest_guides(1)[0]}), so the assistant "
                       "does not guess troubleshooting steps.")
        else:
            summary = "No internal guide covers this ticket closely enough to suggest troubleshooting steps."
        question = ("Could you describe the problem in more detail: what are you trying to do, which device or "
                    "service is affected, and what error message do you see?")
        escalation = {
            "recommended": True,
            "reason": ("Not covered by the knowledge base. If the extra details do not match an existing guide "
                       "(for example purchases, new software, hardware replacement or access approvals), route "
                       "the ticket to a human agent instead of guessing."),
        }

    draft = ("Hello,\n\nThank you for contacting the IT Service Desk. To help you quickly, could you tell us "
             "which device or service is affected, what exactly happens, and the full text of any error "
             "message?\n\nKind regards,\nIT Service Desk")
    if reason == GATE_EMPTY_INDEX:
        draft = ""
    return {
        "mode": MODE_NO_SOURCES,
        "summary": summary,
        "steps": [],
        "citations": [],
        "clarifying_question": question,
        "escalation": escalation,
        "draft_reply": draft,
        "reason": reason,
    }


def retrieval_info(retrieval: RetrievalResult, retriever: Retriever) -> dict[str, Any]:
    used = retrieval.context_ids
    return {
        "gate": retrieval.gate,
        "top_score": retrieval.top_score,
        "min_score": retriever.min_score,
        "doc_margin": retrieval.doc_margin,
        "shared_terms": retrieval.shared_terms,
        "min_shared_terms": retriever.min_shared_terms,
        "ambiguity_margin": retriever.ambiguity_margin,
        "confident_score": retriever.confident_score,
        "hits": [{"id": h.section_id, "guide": h.doc_title, "section": h.heading, "url": h.url,
                  "score": h.score, "used_as_context": h.section_id in used} for h in retrieval.hits],
    }


__all__ = ["answer_ticket", "TicketError", "MODE_ANSWER", "MODE_CLARIFY", "MODE_NO_SOURCES",
           "GATE_OK", "GATE_LOW_SCORE", "GATE_NO_CLEAR_MATCH", "GATE_LOW_EVIDENCE", "GATE_EMPTY_INDEX"]
