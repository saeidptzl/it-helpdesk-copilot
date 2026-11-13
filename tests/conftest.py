"""Shared fixtures. Every test in this folder is MOCKED: it uses a fake hashing embedder and fake LLMs.

Real-model checks (Ollama + nomic-embed-text + qwen2.5:1.5b) live in `python -m app.evaluate`.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np
import pytest

from app.index import VectorIndex
from app.kb import all_sections, kb_fingerprint, load_guides
from app.retrieval import Retriever

ROOT = Path(__file__).resolve().parent.parent
KB_DIR = ROOT / "kb"
DIM = 512


def fake_embed(text: str) -> list[float]:
    """MOCK embedding: hashed bag of words. Deterministic, no model needed."""
    vector = np.zeros(DIM, dtype=np.float32)
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        vector[int(hashlib.md5(token.encode()).hexdigest(), 16) % DIM] += 1.0
    return vector.tolist()


@pytest.fixture
def guides():
    return load_guides(KB_DIR)


@pytest.fixture
def index(tmp_path, guides):
    idx = VectorIndex(tmp_path / "index.sqlite3")
    idx.rebuild(all_sections(guides), lambda texts: [fake_embed(t) for t in texts], "fake-embed",
                kb_fingerprint(guides))
    return idx


def make_retriever(index, **overrides):
    params = dict(top_k=4, min_score=0.15, context_window=1.0, ambiguity_margin=0.0, confident_score=1.0,
                  min_shared_terms=0)
    params.update(overrides)
    return Retriever(index, fake_embed, **params)


@pytest.fixture
def retriever(index):
    return make_retriever(index)
