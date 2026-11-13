"""MOCKED API tests: FastAPI TestClient with a fake embedder and a fake LLM (no Ollama)."""

import dataclasses
import json
import re

import pytest
from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import Services, create_app
from tests.conftest import KB_DIR, ROOT, make_retriever

PRINTER_TICKET = "printer PRN-OPS-02 offline and print jobs stuck in the print queue"


@pytest.fixture
def client(index):
    settings = dataclasses.replace(load_settings(), kb_dir=KB_DIR, index_path=index.path,
                                   samples_path=ROOT / "samples" / "tickets.json", auto_index=False)
    retriever = make_retriever(index)

    def fake_llm(system, user, schema, attempt=1):
        ids = re.findall(r'<source id="([^"]+)"', user)
        return json.dumps({"summary": "Printer is offline.", "steps": [{"text": "Clear the queue.", "source_ids": ids[:1]}],
                           "needs_more_info": False, "clarifying_question": "", "escalate": False,
                           "escalation_reason": "", "draft_reply": "Hello, please try again."})

    app = create_app(Services(settings=settings, client=None, index=index, retriever=retriever, llm=fake_llm))
    with TestClient(app) as test_client:
        yield test_client


def test_home_page_and_samples(client):
    assert "IT Helpdesk Copilot" in client.get("/").text
    samples = client.get("/api/samples").json()
    assert {"vpn-auth", "unsupported-software"} <= {s["id"] for s in samples}


def test_answer_citations_resolve_to_rendered_anchors(client):
    data = client.post("/api/answer", json={"ticket": PRINTER_TICKET}).json()
    assert data["mode"] == "answer" and data["citations"]
    for citation in data["citations"]:
        path, anchor = citation["url"].split("#")
        page = client.get(path)
        assert page.status_code == 200
        assert f"id='{anchor}'" in page.text


def test_empty_ticket_is_rejected(client):
    assert client.post("/api/answer", json={"ticket": "  "}).status_code == 422


def test_unknown_guide_is_404(client):
    assert client.get("/kb/does-not-exist").status_code == 404


def test_health_endpoints(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["index"]["sections"] > 0
