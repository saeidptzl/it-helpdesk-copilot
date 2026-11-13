"""FastAPI application: web UI, answer API, knowledge-base pages and health checks."""

from __future__ import annotations

import html
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import markdown
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .config import Settings, get_settings
from .index import VectorIndex, build_index, index_status
from .kb import Guide, load_guides
from .ollama_client import OllamaClient, OllamaError
from .pipeline import LLM, TicketError, answer_ticket, retrieval_info
from .retrieval import Retriever

log = logging.getLogger("helpdesk_copilot")
STATIC_DIR = Path(__file__).resolve().parent / "static"


@dataclass
class Services:
    settings: Settings
    client: OllamaClient | None
    index: VectorIndex
    retriever: Retriever
    llm: LLM


def build_services(settings: Settings) -> Services:
    client = OllamaClient(settings.ollama_url, settings.llm_timeout_s)
    index = VectorIndex(settings.index_path)

    def embed_query(text: str) -> list[float]:
        return client.embed(settings.embed_model, [settings.embed_query_prefix + text])[0]

    def llm(system: str, user: str, schema: dict, attempt: int = 1) -> str:
        # The retry uses a slightly higher temperature so a failed or looping first answer is not repeated.
        temperature = settings.temperature if attempt == 1 else min(settings.temperature + 0.3, 1.0)
        return client.chat_json(settings.chat_model, system, user, schema, num_ctx=settings.num_ctx,
                                temperature=temperature, num_predict=settings.num_predict,
                                repeat_penalty=settings.repeat_penalty)

    retriever = Retriever(index, embed_query, top_k=settings.top_k, min_score=settings.min_score,
                          context_window=settings.context_window, ambiguity_margin=settings.ambiguity_margin,
                          confident_score=settings.confident_score, min_shared_terms=settings.min_shared_terms)
    return Services(settings=settings, client=client, index=index, retriever=retriever, llm=llm)


class TicketIn(BaseModel):
    ticket: str


def create_app(services: Services | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        svc = app.state.services
        if svc.client is not None and svc.settings.auto_index and svc.index.count() == 0:
            try:
                count = build_index(svc.settings, svc.client)
                log.warning("Index was empty: indexed %d knowledge-base sections.", count)
            except OllamaError as exc:
                log.warning("Index is empty and could not be built yet: %s", exc)
        yield

    app = FastAPI(title="IT Helpdesk Copilot", version=__version__, lifespan=lifespan)
    app.state.services = services or build_services(get_settings())
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    def svc() -> Services:
        return app.state.services

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/samples")
    def samples() -> list[dict[str, str]]:
        path = svc().settings.samples_path
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    @app.post("/api/answer")
    def answer(body: TicketIn) -> dict[str, Any]:
        s = svc()
        try:
            return answer_ticket(body.ticket, s.retriever, s.llm, max_chars=s.settings.max_ticket_chars,
                                 model_name=s.settings.chat_model, min_grounding=s.settings.min_grounding)
        except TicketError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/retrieve")
    def retrieve(q: str = Query(..., min_length=1, max_length=4000)) -> dict[str, Any]:
        s = svc()
        try:
            return retrieval_info(s.retriever.retrieve(q), s.retriever)
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/kb", response_class=HTMLResponse)
    def kb_index() -> str:
        guides = load_guides(svc().settings.kb_dir)
        items = "".join(
            f'<li><a href="/kb/{html.escape(g.doc_id)}">{html.escape(g.title)}</a> '
            f'<span class="muted">({len(g.sections)} sections)</span></li>' for g in guides
        )
        return _page("Knowledge base", f"<h1>Knowledge base</h1><ul>{items}</ul>")

    @app.get("/kb/{doc_id}", response_class=HTMLResponse)
    def kb_guide(doc_id: str) -> str:
        guide = next((g for g in load_guides(svc().settings.kb_dir) if g.doc_id == doc_id), None)
        if guide is None:
            raise HTTPException(status_code=404, detail="Guide not found")
        return _page(guide.title, _render_guide(guide))

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health")
    def health() -> JSONResponse:
        s = svc()
        report: dict[str, Any] = {"version": __version__, "chat_model": s.settings.chat_model,
                                  "embed_model": s.settings.embed_model}
        problems: list[str] = []
        if s.client is not None:
            try:
                report["ollama_version"] = s.client.version()
                models = s.client.list_models()
                for key, name in (("chat_model_available", s.settings.chat_model),
                                  ("embed_model_available", s.settings.embed_model)):
                    report[key] = name in models
                    if name not in models:
                        problems.append(f"model '{name}' is not pulled")
            except OllamaError as exc:
                report["ollama_error"] = str(exc)
                problems.append("ollama unreachable")
        report["index"] = index_status(s.settings)
        if report["index"]["sections"] == 0:
            problems.append("index is empty")
        if report["index"]["stale"]:
            report["index_hint"] = "Knowledge base or embedding model changed: run `python -m app.index --rebuild`."
        report["status"] = "ok" if not problems else "degraded"
        report["problems"] = problems
        return JSONResponse(report, status_code=200 if not problems else 503)

    return app


def _render_guide(guide: Guide) -> str:
    parts = [f"<p class='crumbs'><a href='/'>&larr; Copilot</a> &middot; <a href='/kb'>Knowledge base</a></p>",
             f"<h1>{html.escape(guide.title)}</h1>"]
    meta = " &middot; ".join(f"{html.escape(k)}: {html.escape(v)}" for k, v in guide.meta.items() if k != "id")
    if meta:
        parts.append(f"<p class='muted'>{meta}</p>")
    if guide.intro:
        parts.append(markdown.markdown(guide.intro))
    for section in guide.sections:
        parts.append(
            f"<section id='{html.escape(section.anchor)}'>"
            f"<h2><a class='anchor' href='#{html.escape(section.anchor)}'>#</a> {html.escape(section.heading)}</h2>"
            f"<p class='sid'>Section id: <code>{html.escape(section.id)}</code></p>"
            f"{markdown.markdown(section.text, extensions=['sane_lists'])}</section>"
        )
    return "\n".join(parts)


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(title)} - IT Helpdesk Copilot</title>"
        "<link rel='stylesheet' href='/static/style.css'></head>"
        f"<body class='kb-page'><main class='kb'>{body}</main></body></html>"
    )


app = create_app()  # uvicorn entry point: app.main:app
