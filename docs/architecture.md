# Architecture

```mermaid
flowchart LR
    T["Support ticket<br/>(web UI)"] --> API["FastAPI app<br/>/api/answer"]
    API --> E["Embed ticket<br/>nomic-embed-text"]
    E --> R["Search SQLite index<br/>cosine similarity over guide sections"]
    KB[("Knowledge base<br/>kb/*.md")] -. "python -m app.index --rebuild" .-> R
    R --> G{"Retrieval gates<br/>score, clear leading guide,<br/>shared concrete words?"}
    G -- "no" --> D["Decline to guess:<br/>clarifying question +<br/>escalation suggestion<br/>(LLM not called)"]
    G -- "yes: top sections" --> L["Local LLM via Ollama<br/>qwen2.5:1.5b, JSON schema"]
    L --> V["Validate steps:<br/>keep steps supported by a retrieved section,<br/>cite that section, drop the rest"]
    V --> A["Cited answer:<br/>summary, steps [n],<br/>draft reply for review"]
    A --> UI["Citation links open<br/>/kb/&lt;guide&gt;#&lt;section&gt;"]
```

Docker Compose runs three services:

| Service | Image | Purpose | Storage |
|---|---|---|---|
| `ollama` | `ollama/ollama:0.40.16` | Serves the chat and embedding models. Not published to the host. | volume `ollama-models` |
| `model-pull` | `ollama/ollama:0.40.16` | One-shot job that pulls `CHAT_MODEL` and `EMBED_MODEL`. | same volume |
| `app` | built from `Dockerfile` | FastAPI web UI and API on `127.0.0.1:8000`. Builds the index on first start. | volume `index-data` (`/data/index.sqlite3`) |
