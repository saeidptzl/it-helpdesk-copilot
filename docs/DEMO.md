# Five-minute interview demo

## Before the interview (not part of the 5 minutes)

```bash
cd it-helpdesk-copilot
docker compose up -d --build          # first start downloads about 1.3 GB of models
docker compose ps                      # wait until "app" shows (healthy)
python3 scripts/smoke_test.py          # should end with "7/7 checks passed"
```

Open <http://127.0.0.1:8000> and run each sample ticket once, so the model is loaded in memory
and the first answer is not slow.

## Script

**0:00 - 0:45 | The problem and the boundaries**

- "Service-desk agents answer the same VPN, DNS, drive and printer tickets every day. Answers must
  follow the internal guides, and the agent stays in control."
- Point at the notice on the page: the assistant only suggests steps and drafts a reply. It never runs
  commands, changes accounts or sends anything.
- Show the architecture diagram in the README: ticket -> retrieval -> local model -> cited answer.
  Everything runs locally in Docker; no ticket text leaves the machine.

**0:45 - 2:15 | Demo 1: the assistant finds the right guide**

1. Click the sample **"VPN: authentication failed"** and press **Analyse ticket**.
2. Read the summary, then the steps. Each step has a numbered citation.
3. Click a citation: the VPN guide opens with the cited section highlighted.
4. Show the draft reply: it is editable and must be reviewed before sending.
5. Open **Retrieval details**: the gate is `ok`, the VPN guide scores highest, and only the
   sections marked "Sent to model" can be cited. The code removes any citation the model invents.

**2:15 - 3:15 | Demo 2: the assistant declines to guess**

1. Click **"Unsupported: install new software"** (install Photoshop) and analyse it.
2. Result: **No matching guide**, no steps and no citations, a clarifying question and an
   escalation suggestion.
3. Open **Retrieval details**: the best guides match weakly and almost equally, so the retrieval
   gate stops the request and the LLM is **not called** at all (`LLM called: no`).

**3:15 - 4:00 | Robustness**

- Optionally run **"Ambiguous: it's not working"**: same behaviour.
- Mention the prompt-injection case in the evaluation set: a ticket says "ignore all previous
  instructions"; ticket text is escaped and kept in its own tag, separate from the instructions.

**4:00 - 5:00 | How it was verified, and trade-offs**

- Show `eval/results/retrieval-latest.md` and `eval/results/e2e-latest.md`: retrieval is tested
  separately from generation, with expected guides and expected "decline" behaviour, including
  holdout tickets that were not used to calibrate thresholds.
- `pytest` runs mocked unit and API tests (fake embeddings, fake LLM) in about two seconds.
- Trade-offs: a 1.5B model on CPU is slow (10-60 s) and sometimes cites fewer sections than ideal;
  thresholds were calibrated on a small set. Next steps: hybrid keyword + vector search, a
  re-ranker, a larger model on a GPU, and a ticketing-system integration that still requires a
  human to approve every reply.

## Sample tickets

| Purpose | Ticket |
|---|---|
| Finds the correct guide | Hi IT, since this morning the VPN client says "Authentication failed" every time I try to connect from home. I changed my password yesterday afternoon. I need to reach the S: drive for a report due today. - Marta (Sales) |
| Declines to guess | Please install Adobe Photoshop on my laptop, I need it for a presentation tomorrow morning. Thanks, Luca |
