"""MOCKED retrieval tests: fake hashing embedder, real SQLite index and real gate logic."""

import pytest

from app.index import VectorIndex
from app.retrieval import GATE_EMPTY_INDEX, GATE_LOW_EVIDENCE, GATE_LOW_SCORE, GATE_NO_CLEAR_MATCH, GATE_OK
from tests.conftest import make_retriever


def test_printer_ticket_retrieves_printer_guide(retriever):
    result = retriever.retrieve("printer PRN-OPS-02 offline, print jobs stuck in the print queue")
    assert result.gate == GATE_OK
    assert result.hits[0].doc_id == "printer-connectivity"
    assert result.context and all(h.score >= retriever.min_score for h in result.context)


def test_unrelated_text_is_blocked_by_low_score_gate(retriever):
    result = retriever.retrieve("zxqv plmok wertyu")
    assert result.gate == GATE_LOW_SCORE
    assert result.context == []


def test_empty_index_gate(tmp_path):
    retriever = make_retriever(VectorIndex(tmp_path / "missing.sqlite3"))
    assert retriever.retrieve("vpn").gate == GATE_EMPTY_INDEX


def test_no_clear_match_gate_blocks_near_ties(index):
    # With a huge margin and an unreachable confidence level, every ticket counts as a near-tie.
    retriever = make_retriever(index, ambiguity_margin=1.0, confident_score=1.0)
    result = retriever.retrieve("printer offline")
    assert result.gate == GATE_NO_CLEAR_MATCH
    assert result.context == []


def test_index_persists_across_instances(index):
    reopened = VectorIndex(index.path)
    assert reopened.count() == index.count() > 0
    assert reopened.meta()["embed_model"] == "fake-embed"


def test_dimension_mismatch_is_reported(index):
    with pytest.raises(ValueError, match="Rebuild the index"):
        index.search([1.0, 0.0, 0.0], 3)


def test_low_evidence_gate_requires_shared_concrete_words(index):
    retriever = make_retriever(index, min_score=-1.0, min_shared_terms=2)
    vague = retriever.retrieve("zxqv plmok wertyu")
    assert vague.gate == GATE_LOW_EVIDENCE and vague.context == []
    concrete = retriever.retrieve("printer PRN-OPS-02 offline, print jobs stuck in the print queue")
    assert concrete.gate == GATE_OK and len(concrete.shared_terms) >= 2
