#!/usr/bin/env python3
"""Smoke test against a RUNNING instance (real models). Standard library only.

    python3 scripts/smoke_test.py                       # default http://127.0.0.1:8000
    python3 scripts/smoke_test.py --base-url http://127.0.0.1:8000

Checks:
  1. /health returns 200 (Ollama reachable, both models pulled, index not empty).
  2. Sample "vpn-auth" is answered from the VPN guide; every citation was retrieved for this answer
     and its link opens a guide page that contains the cited section anchor.
  3. Sample "unsupported-software" and "vague" get no steps and no citations (the assistant declines to guess).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

RESULTS: list[tuple[str, bool, str]] = []


def call(base: str, path: str, payload: dict | None = None, timeout: float = 300) -> tuple[int, str]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(base + path, data=data,
                                     headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def answer(base: str, ticket: str) -> dict:
    started = time.perf_counter()
    status, body = call(base, "/api/answer", {"ticket": ticket})
    data = json.loads(body)
    data["_status"], data["_seconds"] = status, round(time.perf_counter() - started, 1)
    return data


def citations_resolve(base: str, data: dict) -> tuple[bool, str]:
    retrieved = {h["id"] for h in data["retrieval"]["hits"] if h["used_as_context"]}
    for citation in data["citations"]:
        if citation["id"] not in retrieved:
            return False, f"{citation['id']} was not retrieved for this answer"
        path, anchor = citation["url"].split("#", 1)
        status, page = call(base, path)
        if status != 200 or f"id='{anchor}'" not in page:
            return False, f"{citation['url']} does not resolve to a section anchor"
    return True, ", ".join(c["id"] for c in data["citations"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    base = parser.parse_args().base_url.rstrip("/")

    status, body = call(base, "/health", timeout=30)
    check("health endpoint is 200", status == 200, body[:300])

    samples = {s["id"]: s["ticket"] for s in json.loads(call(base, "/api/samples")[1])}

    vpn = answer(base, samples["vpn-auth"])
    check("vpn-auth: HTTP 200", vpn["_status"] == 200, f"{vpn['_seconds']} s")
    check("vpn-auth: grounded answer mode", vpn.get("mode") == "answer", vpn.get("mode", ""))
    check("vpn-auth: cites the VPN guide",
          any(c["doc_id"] == "vpn-connection" for c in vpn.get("citations", [])))
    ok, detail = citations_resolve(base, vpn)
    check("vpn-auth: every citation was retrieved and its link resolves", ok and bool(vpn.get("citations")), detail)

    for sample_id in ("unsupported-software", "vague"):
        data = answer(base, samples[sample_id])
        check(f"{sample_id}: declines to guess (no steps, no citations)",
              data["_status"] == 200 and not data["steps"] and not data["citations"],
              f"mode={data.get('mode')}, gate={data['retrieval']['gate']}, {data['_seconds']} s")

    failed = [name for name, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
