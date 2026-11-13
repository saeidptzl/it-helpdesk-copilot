"""Persistent vector index stored in a single SQLite file.

Retrieval choice: section embeddings are stored as float32 blobs in SQLite and searched with an
exact (brute-force) cosine similarity in NumPy. For a knowledge base of a few hundred sections
this takes well under a millisecond, needs no extra service, survives restarts in a Docker
volume, and can be inspected with any SQLite tool.

CLI (also used as the documented index refresh command):
    python -m app.index --status
    python -m app.index --rebuild
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from .kb import Section, all_sections, kb_fingerprint, load_guides

Embedder = Callable[[list[str]], list[list[float]]]


@dataclass(frozen=True)
class IndexedChunk:
    id: str
    doc_id: str
    doc_title: str
    heading: str
    anchor: str
    text: str


class VectorIndex:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._mtime: float | None = None
        self._chunks: list[IndexedChunk] = []
        self._matrix = np.zeros((0, 0), dtype=np.float32)
        self._meta: dict[str, str] = {}

    # ---------- reading ----------
    def _maybe_reload(self) -> None:
        try:
            mtime = self.path.stat().st_mtime
        except FileNotFoundError:
            self._mtime, self._chunks, self._meta = None, [], {}
            self._matrix = np.zeros((0, 0), dtype=np.float32)
            return
        if mtime == self._mtime:
            return
        with sqlite3.connect(self.path) as conn:
            meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
            rows = conn.execute(
                "SELECT id, doc_id, doc_title, heading, anchor, text, embedding FROM chunks ORDER BY rowid"
            ).fetchall()
        chunks = [IndexedChunk(*row[:6]) for row in rows]
        if rows:
            dim = int(meta.get("dim", "0"))
            matrix = np.vstack([np.frombuffer(row[6], dtype=np.float32, count=dim) for row in rows])
        else:
            matrix = np.zeros((0, 0), dtype=np.float32)
        self._chunks, self._matrix, self._meta, self._mtime = chunks, matrix, meta, mtime

    def count(self) -> int:
        self._maybe_reload()
        return len(self._chunks)

    def meta(self) -> dict[str, str]:
        self._maybe_reload()
        return dict(self._meta)

    def doc_texts(self) -> dict[str, str]:
        """Full text (titles, headings and bodies) of every indexed guide, keyed by guide id."""
        self._maybe_reload()
        texts: dict[str, list[str]] = {}
        for chunk in self._chunks:
            texts.setdefault(chunk.doc_id, [chunk.doc_title]).append(f"{chunk.heading}\n{chunk.text}")
        return {doc_id: "\n".join(parts) for doc_id, parts in texts.items()}

    def search(self, query_vector: list[float], top_k: int) -> list[tuple[IndexedChunk, float]]:
        self._maybe_reload()
        if not self._chunks:
            return []
        query = _normalize(np.asarray(query_vector, dtype=np.float32))
        if query.shape[0] != self._matrix.shape[1]:
            raise ValueError(
                f"Query embedding has {query.shape[0]} dimensions but the index has "
                f"{self._matrix.shape[1]}. Rebuild the index after changing EMBED_MODEL."
            )
        scores = self._matrix @ query
        order = np.argsort(-scores)[:top_k]
        return [(self._chunks[i], float(scores[i])) for i in order]

    # ---------- writing ----------
    def rebuild(self, sections: list[Section], embedder: Embedder, embed_model: str, fingerprint: str) -> int:
        """Embed all sections and atomically replace the index file."""
        vectors = embedder([s.embedding_text() for s in sections]) if sections else []
        matrix = np.vstack([_normalize(np.asarray(v, dtype=np.float32)) for v in vectors]) if vectors else None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".index-", suffix=".sqlite3", dir=self.path.parent)
        os.close(fd)
        try:
            with sqlite3.connect(tmp_name) as conn:
                conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                conn.execute(
                    "CREATE TABLE chunks (id TEXT PRIMARY KEY, doc_id TEXT NOT NULL, doc_title TEXT NOT NULL, "
                    "heading TEXT NOT NULL, anchor TEXT NOT NULL, text TEXT NOT NULL, embedding BLOB NOT NULL)"
                )
                for i, section in enumerate(sections):
                    conn.execute(
                        "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (section.id, section.doc_id, section.doc_title, section.heading, section.anchor,
                         section.text, matrix[i].astype(np.float32).tobytes()),
                    )
                meta = {
                    "embed_model": embed_model,
                    "kb_fingerprint": fingerprint,
                    "dim": str(matrix.shape[1] if matrix is not None else 0),
                    "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "sections": str(len(sections)),
                }
                conn.executemany("INSERT INTO meta VALUES (?, ?)", list(meta.items()))
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        self._mtime = None
        return len(sections)


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 else vector


def build_index(settings, client) -> int:  # pragma: no cover - exercised by CLI and app startup
    guides = load_guides(settings.kb_dir)
    sections = all_sections(guides)
    prefix = settings.embed_doc_prefix

    def embedder(texts: list[str]) -> list[list[float]]:
        return client.embed(settings.embed_model, [prefix + t for t in texts])

    return VectorIndex(settings.index_path).rebuild(
        sections, embedder, settings.embed_model, kb_fingerprint(guides)
    )


def index_status(settings) -> dict[str, object]:
    guides = load_guides(settings.kb_dir)
    index = VectorIndex(settings.index_path)
    meta = index.meta()
    count = index.count()
    stale = bool(count) and (
        meta.get("kb_fingerprint") != kb_fingerprint(guides) or meta.get("embed_model") != settings.embed_model
    )
    return {
        "path": str(settings.index_path),
        "sections": count,
        "kb_sections": len(all_sections(guides)),
        "embed_model": meta.get("embed_model"),
        "built_at": meta.get("built_at"),
        "stale": stale,
    }


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - thin CLI wrapper
    from .config import get_settings
    from .ollama_client import OllamaClient, OllamaError

    parser = argparse.ArgumentParser(description="Build or inspect the knowledge-base index.")
    parser.add_argument("--rebuild", action="store_true", help="re-embed all guides and replace the index")
    parser.add_argument("--status", action="store_true", help="print index status as JSON")
    args = parser.parse_args(argv)
    settings = get_settings()

    if args.rebuild:
        client = OllamaClient(settings.ollama_url, settings.llm_timeout_s)
        try:
            started = time.perf_counter()
            count = build_index(settings, client)
        except OllamaError as exc:
            print(f"Index rebuild failed: {exc}", file=sys.stderr)
            return 1
        print(f"Indexed {count} sections with {settings.embed_model} in {time.perf_counter() - started:.1f}s "
              f"-> {settings.index_path}")
    print(json.dumps(index_status(settings), indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
