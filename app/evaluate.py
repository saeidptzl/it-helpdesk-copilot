"""Evaluate retrieval and the full pipeline against eval/eval_set.json using the real local models.

    python -m app.evaluate retrieval      # embeddings + gate only (no LLM)
    python -m app.evaluate e2e            # retrieval + generation + citation checks

Expectations per case:
  {"guide": "<doc id>"}       retrieval: gate passes and the top section belongs to that guide
                              e2e: mode "answer", that guide is cited, every citation was retrieved
                                   and points to an existing section anchor
  {"behavior": "decline"}     retrieval: gate blocks generation (no section is used as context)
                              e2e: no troubleshooting steps and no citations (asks or escalates)
Results are printed and written to eval/results/<mode>-latest.md.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

from .config import BASE_DIR, get_settings
from .kb import all_sections, load_guides
from .main import build_services
from .pipeline import MODE_ANSWER, answer_ticket

EVAL_PATH = BASE_DIR / "eval" / "eval_set.json"
RESULTS_DIR = BASE_DIR / "eval" / "results"


def run_retrieval(services, cases) -> tuple[list[dict], int]:
    rows, passed = [], 0
    for case in cases:
        result = services.retriever.retrieve(case["ticket"])
        top_doc = result.hits[0].doc_id if result.hits else "-"
        expect = case["expect"]
        context_docs = {h.doc_id for h in result.context}
        if "guide" in expect:
            ok = result.gate == "ok" and top_doc == expect["guide"]
            expected = expect["guide"]
            in_context = "yes" if expect["guide"] in context_docs else "no"
        else:
            ok = result.gate != "ok"
            expected = "gate blocks"
            in_context = "n/a"
        passed += ok
        rows.append({"id": case["id"], "split": case.get("split", "dev"), "expected": expected,
                     "top_section": result.hits[0].section_id if result.hits else "-",
                     "top_score": f"{result.top_score:.3f}", "guide_margin": f"{result.doc_margin:.3f}",
                     "shared_terms": len(result.shared_terms),
                     "gate": result.gate, "expected_guide_in_context": in_context,
                     "pass": "PASS" if ok else "FAIL"})
    return rows, passed


def run_e2e(services, cases, anchors: set[str]) -> tuple[list[dict], int]:
    rows, passed = [], 0
    s = services.settings
    for case in cases:
        started = time.perf_counter()
        try:
            out = answer_ticket(case["ticket"], services.retriever, services.llm, max_chars=s.max_ticket_chars,
                                model_name=s.chat_model, min_grounding=s.min_grounding)
        except Exception as exc:  # record the failure and continue with the next case
            rows.append({"id": case["id"], "split": case.get("split", "dev"), "expected": str(case["expect"]),
                         "mode": "error", "cited": "-", "escalate": "-", "attempts": "-",
                         "seconds": f"{time.perf_counter() - started:.1f}",
                         "pass": f"FAIL ({exc.__class__.__name__}: {str(exc)[:80]})"})
            continue
        seconds = time.perf_counter() - started
        retrieved = {h["id"] for h in out["retrieval"]["hits"] if h["used_as_context"]}
        cited = [c["id"] for c in out["citations"]]
        cited_docs = {c["doc_id"] for c in out["citations"]}
        citations_valid = all(cid in retrieved and cid in anchors for cid in cited)
        expect = case["expect"]
        notes = []
        if "guide" in expect:
            ok = out["mode"] == MODE_ANSWER and expect["guide"] in cited_docs and citations_valid
            expected = expect["guide"]
            if not citations_valid:
                notes.append("citation not retrieved")
            forbidden = expect.get("must_not_contain")
            if forbidden and forbidden.lower() in json.dumps(out).lower():
                ok = False
                notes.append("leaked system prompt")
        else:
            ok = not out["steps"] and not out["citations"]
            expected = "decline (ask/escalate)"
        passed += ok
        print(f"  {case['id']}: {'PASS' if ok else 'FAIL'} mode={out['mode']} {seconds:.1f}s", file=sys.stderr, flush=True)
        rows.append({"id": case["id"], "split": case.get("split", "dev"), "expected": expected, "mode": out["mode"],
                     "cited": ", ".join(cited) or "-", "escalate": "yes" if out["escalation"]["recommended"] else "no",
                     "attempts": out["diagnostics"].get("attempts", 0),
                     "ungrounded_removed": len(out["diagnostics"].get("ungrounded_steps", [])),
                     "reattributed": out["diagnostics"].get("reattributed_steps", 0), "seconds": f"{seconds:.1f}", "pass": "PASS" if ok else "FAIL" + (f" ({'; '.join(notes)})" if notes else "")})
    return rows, passed


def _split_summary(rows: list[dict]) -> str:
    parts = []
    for split in ("dev", "holdout", "holdout2"):
        subset = [r for r in rows if r.get("split") == split]
        if subset:
            ok = sum(1 for r in subset if r["pass"] == "PASS")
            parts.append(f"{split}: {ok}/{len(subset)}")
    return ", ".join(parts)


def to_markdown(title: str, rows: list[dict], passed: int, settings, extra: str) -> str:
    headers = list(rows[0].keys()) if rows else []
    lines = [f"# {title}", "",
             f"- Date: {time.strftime('%Y-%m-%d %H:%M %Z')}",
             f"- Chat model: `{settings.chat_model}` | Embedding model: `{settings.embed_model}`",
             f"- TOP_K={settings.top_k}, MIN_SCORE={settings.min_score}, CONFIDENT_SCORE={settings.confident_score}, "
             f"AMBIGUITY_MARGIN={settings.ambiguity_margin}, CONTEXT_WINDOW={settings.context_window}, "
             f"MIN_GROUNDING={settings.min_grounding}, MIN_SHARED_TERMS={settings.min_shared_terms}",
             "- Splits: `dev` calibrated all thresholds; `holdout` was written before its first run and never used "
             "for calibration, but was seen before the last design change; `holdout2` was written after the last "
             "design change and before its first run.",
             f"- Host: {platform.system()} {platform.machine()}, Python {platform.python_version()}",
             f"- {extra}", "",
             f"**Result: {passed}/{len(rows)} passed** ({_split_summary(rows)})", "",
             "| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        lines.append("| " + " | ".join(str(row[h]).replace("|", "\\|") for h in headers) + " |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["retrieval", "e2e"])
    parser.add_argument("--only", help="comma-separated case ids")
    parser.add_argument("--no-write", action="store_true", help="do not write eval/results/*.md")
    args = parser.parse_args(argv)

    settings = get_settings()
    services = build_services(settings)
    cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    if services.index.count() == 0:
        print("The index is empty. Run `python -m app.index --rebuild` first.", file=sys.stderr)
        return 2

    if args.mode == "retrieval":
        rows, passed = run_retrieval(services, cases)
        title, extra = "Retrieval evaluation (real embeddings, no LLM)", "Generation is not called in this mode."
    else:
        anchors = {s.id for s in all_sections(load_guides(settings.kb_dir))}
        rows, passed = run_e2e(services, cases, anchors)
        title, extra = "End-to-end evaluation (real local models)", "Each case calls the real chat model via Ollama."

    report = to_markdown(title, rows, passed, settings, extra)
    print(report)
    if not args.no_write and not args.only:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / f"{args.mode}-latest.md").write_text(report, encoding="utf-8")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
