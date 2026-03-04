"""Tests for benchmark harness utilities — API contract (TDD stubs).

Tests define the expected interface for corpus loading, ranx object
construction, and latency recording.  Stubs raise ``NotImplementedError``
until tasks #377-380 provide real implementations.

Task: #381
"""

from __future__ import annotations

from collections import defaultdict

import pytest

from tests.benchmarks.corpus import load_nfcorpus
from tests.benchmarks.harness import (
    build_qrels,
    build_run,
    make_latency_tracker,
    record_latency,
)

# ---------------------------------------------------------------------------
# Synthetic fixtures (no real BEIR data / model downloads)
# ---------------------------------------------------------------------------

MINI_CORPUS: dict[str, str] = {
    "d1": "Information security management systems standard.",
    "d2": "Quality management systems requirements.",
    "d3": "Risk management guidelines and framework.",
}

MINI_QUERIES: dict[str, str] = {
    "q1": "security management standard",
    "q2": "quality assurance requirements",
}

MINI_QRELS: dict[str, dict[str, int]] = {
    "q1": {"d1": 2, "d3": 1},
    "q2": {"d2": 2},
}

MINI_RESULTS: dict[str, dict[str, float]] = {
    "q1": {"d1": 0.95, "d3": 0.42, "d2": 0.10},
    "q2": {"d2": 0.88, "d1": 0.15},
}


# ===================================================================
# Corpus loading tests
# ===================================================================


@pytest.mark.api
@pytest.mark.benchmark
class TestLoadNfcorpus:
    """Contract: load_nfcorpus() returns (corpus, queries, qrels)."""

    def test_returns_three_tuple(self):
        """load_nfcorpus must return exactly 3 elements."""
        result = load_nfcorpus()
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_corpus_is_dict_str_str(self):
        """corpus maps doc_id (str) → doc_text (str)."""
        corpus, _queries, _qrels = load_nfcorpus()
        assert isinstance(corpus, dict)
        assert len(corpus) > 0
        for doc_id, text in corpus.items():
            assert isinstance(doc_id, str)
            assert isinstance(text, str)

    def test_queries_is_dict_str_str(self):
        """queries maps query_id (str) → query_text (str)."""
        _corpus, queries, _qrels = load_nfcorpus()
        assert isinstance(queries, dict)
        assert len(queries) > 0
        for qid, text in queries.items():
            assert isinstance(qid, str)
            assert isinstance(text, str)

    def test_qrels_structure(self):
        """qrels maps query_id → {doc_id: int_relevance}."""
        _corpus, _queries, qrels = load_nfcorpus()
        assert isinstance(qrels, dict)
        assert len(qrels) > 0
        for qid, judgments in qrels.items():
            assert isinstance(qid, str)
            assert isinstance(judgments, dict)
            for doc_id, score in judgments.items():
                assert isinstance(doc_id, str)
                assert isinstance(score, int)

    def test_qrels_query_ids_subset_of_queries(self):
        """Every query_id in qrels should appear in queries."""
        _corpus, queries, qrels = load_nfcorpus()
        for qid in qrels:
            assert qid in queries, f"qrels query_id {qid!r} not in queries"

    def test_qrels_doc_ids_subset_of_corpus(self):
        """Every doc_id in qrels should appear in corpus."""
        corpus, _queries, qrels = load_nfcorpus()
        for judgments in qrels.values():
            for doc_id in judgments:
                assert doc_id in corpus, f"qrels doc_id {doc_id!r} not in corpus"


# ===================================================================
# Qrels construction tests
# ===================================================================


@pytest.mark.benchmark
class TestBuildQrels:
    """Contract: build_qrels() produces a valid ranx.Qrels."""

    def test_returns_qrels_object(self):
        """build_qrels must return a ranx.Qrels instance."""
        ranx = pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        assert isinstance(qrels, ranx.Qrels)

    def test_qrels_contains_all_queries(self):
        """Resulting Qrels must contain every query from the input."""
        pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        # ranx.Qrels exposes query IDs via .keys() or iteration
        qrels_ids = set(qrels.keys())
        assert qrels_ids == set(MINI_QRELS.keys())

    def test_qrels_preserves_relevance_scores(self):
        """Relevance scores must be faithfully transferred."""
        pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        # For "q1", d1 should have relevance 2
        assert qrels["q1"]["d1"] == 2
        assert qrels["q1"]["d3"] == 1


# ===================================================================
# Run construction tests
# ===================================================================


@pytest.mark.benchmark
class TestBuildRun:
    """Contract: build_run() produces a valid ranx.Run."""

    def test_returns_run_object(self):
        """build_run must return a ranx.Run instance."""
        ranx = pytest.importorskip("ranx")
        run = build_run(MINI_RESULTS)
        assert isinstance(run, ranx.Run)

    def test_run_contains_all_queries(self):
        """Resulting Run must contain every query from the input."""
        pytest.importorskip("ranx")
        run = build_run(MINI_RESULTS)
        run_ids = set(run.keys())
        assert run_ids == set(MINI_RESULTS.keys())

    def test_run_preserves_scores(self):
        """Document scores must be faithfully transferred."""
        pytest.importorskip("ranx")
        run = build_run(MINI_RESULTS)
        assert run["q1"]["d1"] == pytest.approx(0.95)

    def test_run_empty_input(self):
        """build_run with empty dict should still return a Run."""
        ranx = pytest.importorskip("ranx")
        run = build_run({})
        assert isinstance(run, ranx.Run)


# ===================================================================
# Latency recording tests
# ===================================================================


@pytest.mark.benchmark
class TestLatencyRecording:
    """Contract: latency tracker is dict[str, list[float]]."""

    def test_make_latency_tracker_returns_defaultdict(self):
        """make_latency_tracker returns a defaultdict(list)."""
        tracker = make_latency_tracker()
        assert isinstance(tracker, defaultdict)
        # Accessing a missing key should produce an empty list
        assert tracker["nonexistent"] == []

    def test_record_latency_appends(self):
        """record_latency appends elapsed time to the mode's list."""
        tracker = make_latency_tracker()
        record_latency(tracker, "dense", 0.012)
        record_latency(tracker, "dense", 0.015)
        record_latency(tracker, "sparse", 0.008)

        assert tracker["dense"] == [pytest.approx(0.012), pytest.approx(0.015)]
        assert tracker["sparse"] == [pytest.approx(0.008)]

    def test_latency_structure_mode_to_floats(self):
        """Tracker values are list[float] keyed by mode string."""
        tracker = make_latency_tracker()
        record_latency(tracker, "dense", 0.05)
        record_latency(tracker, "hybrid", 0.03)

        for mode, times in tracker.items():
            assert isinstance(mode, str)
            assert isinstance(times, list)
            for t in times:
                assert isinstance(t, float)

    def test_latency_multiple_modes_independent(self):
        """Each mode accumulates independently."""
        tracker = make_latency_tracker()
        for i in range(5):
            record_latency(tracker, "dense", float(i) * 0.01)
        for i in range(3):
            record_latency(tracker, "sparse", float(i) * 0.02)

        assert len(tracker["dense"]) == 5
        assert len(tracker["sparse"]) == 3
        assert "hybrid" not in tracker

    def test_latency_empty_tracker(self):
        """Fresh tracker has no keys."""
        tracker = make_latency_tracker()
        assert len(tracker) == 0
