"""Minimal HTTP client for the Ollama API (embeddings and JSON chat)."""

from __future__ import annotations

from typing import Any

import httpx


class OllamaError(RuntimeError):
    """Raised when Ollama is unreachable or a model is missing."""


class OllamaGenerationError(OllamaError):
    """Raised when the model itself fails on an input (aborted prediction or timeout)."""


class OllamaClient:
    def __init__(self, base_url: str, timeout_s: float = 240.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=httpx.Timeout(timeout_s, connect=5.0))

    def _request(self, method: str, path: str, *, generation: bool = False, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            error = OllamaGenerationError if generation else OllamaError
            raise error(f"Ollama did not answer in time ({exc.__class__.__name__}).") from exc
        except httpx.HTTPError as exc:
            raise OllamaError(
                f"Ollama is not reachable at {self.base_url} ({exc.__class__.__name__}). "
                "Check that the Ollama service is running."
            ) from exc
        if response.status_code == 404:
            detail = _error_text(response)
            raise OllamaError(f"Ollama returned 404: {detail}. Pull the model first, e.g. `ollama pull <model>`.")
        if generation and response.status_code >= 500:
            # e.g. "prediction aborted, token repeat limit reached": the model failed on this input.
            raise OllamaGenerationError(f"Generation failed (HTTP {response.status_code}): {_error_text(response)}")
        if response.status_code >= 400:
            raise OllamaError(f"Ollama returned HTTP {response.status_code}: {_error_text(response)}")
        return response.json()

    def version(self) -> str:
        return str(self._request("GET", "/api/version").get("version", "unknown"))

    def list_models(self) -> set[str]:
        names: set[str] = set()
        for model in self._request("GET", "/api/tags").get("models", []):
            name = model.get("name") or model.get("model") or ""
            names.add(name)
            if name.endswith(":latest"):
                names.add(name[: -len(":latest")])
        return names

    def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        data = self._request("POST", "/api/embed", json={"model": model, "input": texts})
        embeddings = data.get("embeddings") or []
        if len(embeddings) != len(texts):
            raise OllamaError(f"Expected {len(texts)} embeddings from {model}, got {len(embeddings)}")
        return embeddings

    def chat_json(self, model: str, system: str, user: str, schema: dict[str, Any], *,
                  num_ctx: int, temperature: float, num_predict: int, repeat_penalty: float) -> str:
        payload = {
            "model": model,
            "stream": False,
            "format": schema,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": temperature, "num_ctx": num_ctx, "num_predict": num_predict,
                        "repeat_penalty": repeat_penalty},
        }
        data = self._request("POST", "/api/chat", generation=True, json=payload)
        return str(data.get("message", {}).get("content", ""))


def _error_text(response: httpx.Response) -> str:
    try:
        return str(response.json().get("error", response.text))
    except ValueError:
        return response.text[:200]
