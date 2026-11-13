# Verification log

This file records the checks that were actually run, how they were run, and what was observed.
**Mocked** means the check used a fake embedder and/or a fake LLM. **Real** means it used the real
local models through Ollama. **Pending** means the check has not been run yet.

Build environment: Linux x86_64 laptop, AMD Ryzen 7 PRO 8840HS (16 threads), 10 GB RAM (about 4 GB free
during the tests), no discrete GPU, Python 3.14.4, Google Chrome 157 (headless). Date: 2026-11-13.

## Summary

| # | Check | Type | Status |
|---|---|---|---|
| 1 | Host resources checked before choosing the model | Real | Done |
| 2 | `docker compose up` with health checks, volumes and model pull | Real | **Pending: Docker is not installed in the build environment** |
| 3 | `docker-compose.yml` validated against the Compose Specification JSON schema | Static | Pass |
| 4 | Pinned Python packages support Python 3.12 (the Docker base image) | Static | Pass |
| 5 | Index build with `nomic-embed-text` (Ollama 0.40.16 on CPU, outside Docker) | Real | Pass: 27 sections in 2.9 s |
| 6 | `pytest`: unit and API tests | **Mocked** | Pass: 31/31 |
| 7 | Retrieval evaluation (no LLM) | Real | 26/28 (dev 16/16, holdout 5/6, holdout2 5/6) |
| 8 | End-to-end evaluation (retrieval + generation + citation checks) | Real | 27/28 (dev 16/16, holdout 6/6, holdout2 5/6) |
| 9 | Smoke test against the running web app (`scripts/smoke_test.py`) | Real, outside Docker | Pass: 7/7 |
| 10 | Browser check: UI answer, citation link opens the cited section | Real, outside Docker | Pass |
| 11 | Network exposure: app and Ollama listen on 127.0.0.1 only | Real, outside Docker | Pass |

## 1. Host resources

```
nproc                      -> 16
free -h                    -> Mem total 10Gi, available 4.3Gi
df -h /                    -> 72G available
nvidia-smi                 -> not present (CPU only)
```

Decision: `qwen2.5:1.5b` (986 MB on disk, about 1.6 GB RAM loaded) for chat and `nomic-embed-text`
(274 MB on disk, about 0.5 GB RAM) for embeddings. Together they fit in the available memory on CPU.

## 2. Docker Compose stack: pending

```
docker --version           -> bash: docker: command not found
sudo -n true               -> sudo: interactive authentication is required
```

Docker could not be installed without the owner's password, so the Compose stack has **not been run yet**.
Everything below was therefore tested with the same code running directly on the host, with Ollama
0.40.16 (the same version as the `ollama/ollama:0.40.16` image) started from its official release archive
in user space and bound to `127.0.0.1:11434`.

To complete this check on a machine with Docker:

```bash
docker compose up -d --build
docker compose ps                       # expected: ollama (healthy), model-pull exited (0), app (healthy)
curl -s http://127.0.0.1:8000/health    # expected: "status": "ok"
python3 scripts/smoke_test.py           # expected: 7/7 checks passed
docker compose exec app python -m app.index --rebuild
docker compose exec app python -m app.evaluate e2e
docker compose restart app && docker compose ps   # index and models persist (no new model download)
```

## 3. Static check of the Compose file

`docker-compose.yml` was parsed with PyYAML and validated with `jsonschema` against
`compose-spec.json` from the compose-spec repository: **valid**. Confirmed from the parsed file: three
services (`ollama`, `model-pull`, `app`); `app` publishes only `127.0.0.1:${APP_PORT:-8000}:8000`; `ollama`
publishes no port; `app` waits for `model-pull` with `service_completed_successfully`.

## 4. Python 3.12 compatibility of pinned packages

PyPI metadata checked for the pinned versions: numpy 2.5.4 (`>=3.12`, cp312 manylinux wheel available),
pydantic-core 2.50.4 (cp312 wheel available), fastapi 0.162.5, starlette 1.10.0 and uvicorn 0.54.0 (pure
Python, `>=3.10`/`>=3.11`). Not yet confirmed by an actual image build (see check 2).

## 5. Index build (real)

```
python -m app.index --rebuild
-> Indexed 27 sections with nomic-embed-text in 2.9s
```

## 6. pytest (mocked)

```
pytest -q  ->  31 passed
```

All tests use a fake hashing embedder and fake LLM responses. They cover: knowledge-base parsing and
anchors, SQLite index persistence, the three retrieval gates, citation filtering, step support and
re-attribution, HTML-entity clean-up, prompt separation, JSON retry, model-abort retry, generation failure,
and the API (citation links resolve to section anchors on the rendered guide page).

## 7. Retrieval evaluation (real embeddings, no LLM)

`python -m app.evaluate retrieval` -> **26/28**. Full table: [eval/results/retrieval-latest.md](../eval/results/retrieval-latest.md).

- `ho-dns` fails the top-1 criterion: the VPN guide ranks first by 0.002, but the DNS guide is in the model
  context.
- `h2-share` is a false decline: the backup guide scores within `AMBIGUITY_MARGIN` of the shared-drive guide.

## 8. End-to-end evaluation (real models)

`python -m app.evaluate e2e` -> **27/28**. Full table: [eval/results/e2e-latest.md](../eval/results/e2e-latest.md).

For each answered ticket the check requires: mode `answer`, the expected guide among the cited guides,
every cited id among the sections retrieved for that ticket, and every cited id an existing section anchor.
For decline cases it requires no steps and no citations. The prompt-injection ticket must not leak the
system prompt. The only failure is `h2-share` (false decline, see above).

## 9. Smoke test against the running app (real)

`python3 scripts/smoke_test.py` with the app on `127.0.0.1:8000`:

```
[PASS] health endpoint is 200
[PASS] vpn-auth: HTTP 200 - 10.3 s
[PASS] vpn-auth: grounded answer mode - answer
[PASS] vpn-auth: cites the VPN guide
[PASS] vpn-auth: every citation was retrieved and its link resolves - vpn-connection#troubleshooting-steps
[PASS] unsupported-software: declines to guess (no steps, no citations) - mode=insufficient_sources, gate=no_clear_match
[PASS] vague: declines to guess (no steps, no citations) - mode=insufficient_sources, gate=no_clear_match
7/7 checks passed
```

## 10. Browser check (real)

Headless Chrome opened `http://127.0.0.1:8000/?sample=vpn-auth&run=1`, which fills in the VPN sample and
submits it. After the answer arrived, the rendered page showed the badge "Grounded answer" and step
citation links only to `vpn-connection` sections. Opening `/kb/vpn-connection#quick-checks` scrolled to and
highlighted the "Quick checks" section. Screenshots: [screenshot.png](screenshot.png) (VPN ticket) and
[screenshot-decline.png](screenshot-decline.png) (Photoshop request, no matching guide).

The generated text varies slightly between runs (temperature 0.1). In the screenshot run the steps were
attributed to `vpn-connection#quick-checks`; in the smoke-test run to `vpn-connection#troubleshooting-steps`.

## 11. Network exposure (real)

```
ss -ltnp | grep -E ":8000|:11434"
LISTEN 127.0.0.1:11434  (ollama)
LISTEN 127.0.0.1:8000   (python -m app)
```

## Problems found during verification and fixed before publishing

1. `.dockerignore` excluded `*.md`, which would have removed the knowledge base (`kb/*.md`) from the image.
   Found in review before any build; the rule now excludes only `README.md` and `LICENSE`.
2. On one ticket the model looped and Ollama aborted with "token repeat limit reached" (HTTP 500), which
   crashed the evaluation. Now: a dedicated `OllamaGenerationError`, one retry at a higher temperature, an
   output cap (`NUM_PREDICT`), a repetition penalty and `maxItems` limits in the JSON schema; a second
   failure returns a "generation failed" response instead of an error.
3. A vague ticket ("something is weird with my computer") passed the embedding gates and the model
   answered with invented steps ("Disk Management", "Resize Volume") while citing a real section.
   Added the shared-terms gate (`MIN_SHARED_TERMS`) and the step-support check with citation
   re-attribution (`MIN_GROUNDING`). Both thresholds were calibrated on the `dev` tickets only, and the six
   `holdout2` tickets were written afterwards, before their first run.
4. The model copied HTML-escaped text (`&gt;`) from the sources into its answer. Model output is now
   unescaped before display.
5. For the VPN sample the model skipped the step that matches the ticket detail ("changed my password").
   Added a prompt rule to start with steps that match the ticket's specific details.
6. A unit test (`test_fingerprint_changes_when_content_changes`) did not modify the guide it tested.
   Fixed the test.
7. In the image, `eval/` was owned by root while the app runs as the unprivileged `copilot` user, so
   `docker compose exec app python -m app.evaluate ...` could not write its results file. Found in review;
   the Dockerfile now copies `eval/` with `--chown=copilot:copilot`. (Not yet confirmed by a build, see check 2.)

## Known limitations

- `AMBIGUITY_MARGIN` is fragile: it caused the `h2-share` false decline.
- Six holdout2 tickets are far too few to estimate accuracy; the results show behaviour, not a benchmark.
- The step-support check is lexical. It proves that a step restates text from its cited section, not that
  the advice fits the ticket.
- The 1.5B model on CPU is slow (about 10 to 27 seconds per answer) and its wording varies between runs.
