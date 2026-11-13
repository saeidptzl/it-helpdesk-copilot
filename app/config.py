"""Runtime configuration, read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _str(name: str, default: str) -> str:
    value = os.getenv(name)
    return default if value is None or value.strip() == "" else value.strip()


def _raw(name: str, default: str) -> str:
    """Like _str, but an explicitly empty value is kept (used for embedding prefixes)."""
    value = os.getenv(name)
    return default if value is None else value


def _int(name: str, default: int) -> int:
    return int(_str(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(_str(name, str(default)))


def _bool(name: str, default: bool) -> bool:
    return _str(name, "true" if default else "false").lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # Ollama and models
    ollama_url: str
    chat_model: str
    embed_model: str
    embed_query_prefix: str
    embed_doc_prefix: str
    llm_timeout_s: float
    num_ctx: int
    temperature: float
    num_predict: int
    repeat_penalty: float

    # Data locations
    kb_dir: Path
    index_path: Path
    samples_path: Path

    # Retrieval
    top_k: int
    min_score: float
    context_window: float
    ambiguity_margin: float
    confident_score: float
    min_grounding: float
    min_shared_terms: int

    # Web server
    host: str
    port: int
    max_ticket_chars: int
    auto_index: bool


def load_settings() -> Settings:
    return Settings(
        ollama_url=_str("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
        chat_model=_str("CHAT_MODEL", "qwen2.5:1.5b"),
        embed_model=_str("EMBED_MODEL", "nomic-embed-text"),
        # nomic-embed-text expects task prefixes; set both to "" for other embedding models.
        embed_query_prefix=_raw("EMBED_QUERY_PREFIX", "search_query: "),
        embed_doc_prefix=_raw("EMBED_DOC_PREFIX", "search_document: "),
        llm_timeout_s=_float("LLM_TIMEOUT_S", 240.0),
        num_ctx=_int("NUM_CTX", 4096),
        temperature=_float("TEMPERATURE", 0.1),
        num_predict=_int("NUM_PREDICT", 800),
        repeat_penalty=_float("REPEAT_PENALTY", 1.1),
        kb_dir=Path(_str("KB_DIR", str(BASE_DIR / "kb"))),
        index_path=Path(_str("INDEX_PATH", str(BASE_DIR / "data" / "index.sqlite3"))),
        samples_path=Path(_str("SAMPLES_PATH", str(BASE_DIR / "samples" / "tickets.json"))),
        top_k=_int("TOP_K", 4),
        # Calibrated for nomic-embed-text on eval/eval_set.json (see README "Calibration").
        min_score=_float("MIN_SCORE", 0.60),
        context_window=_float("CONTEXT_WINDOW", 0.10),
        ambiguity_margin=_float("AMBIGUITY_MARGIN", 0.035),
        confident_score=_float("CONFIDENT_SCORE", 0.70),
        min_grounding=_float("MIN_GROUNDING", 0.35),
        min_shared_terms=_int("MIN_SHARED_TERMS", 2),
        host=_str("HOST", "127.0.0.1"),
        port=_int("PORT", 8000),
        max_ticket_chars=_int("MAX_TICKET_CHARS", 4000),
        auto_index=_bool("AUTO_INDEX", True),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
