"""Contract tests for the EntityExtractor benchmark corpus and gold schema.

Tests fail while the corpus loader/manifest under tests/benchmarks/ is absent.
When the corpus fixture module exists, these tests assert the full corpus contract:
minimum sample count, both source kinds, unique stable labels, pure-data loading,
and gold keys typed as (normalized_name, entity_type) over EntityType strings.

Task: #911
"""

from __future__ import annotations

import re

import pydantic_ai.models

from owlbear.memory.knowledge.models import EntityType

# Block real LLM calls — corpus loading must be pure-data and model-free.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False

# These imports drive the RED failure — the corpus module does not exist yet.
# All tests fail at collection with ImportError until #912 implements the fixtures.
from tests.benchmarks.entity_extractor_corpus import (  # noqa: E402
    ENTITY_EXTRACTOR_CORPUS,
    CorpusSample,
    GoldEntity,
    load_corpus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ENTITY_TYPES: frozenset[str] = frozenset(e.value for e in EntityType)
_VALID_SOURCE_KINDS: frozenset[str] = frozenset({"python", "markdown"})

# uuid4().hex produces 32 lowercase hex chars; uuid4() canonical form uses dashes.
_UUID_HEX_RE = re.compile(r"^[0-9a-f]{32}$")
_UUID_CANONICAL_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

# origin_path must point into the OwlBear source tree.
_OWLBEAR_PATH_PREFIXES = ("src/", "tests/", "src\\", "tests\\")


def _is_uuid_like(value: str) -> bool:
    return bool(_UUID_HEX_RE.match(value) or _UUID_CANONICAL_RE.match(value))


# ---------------------------------------------------------------------------
# AC 1 — module exports expected names
# ---------------------------------------------------------------------------


class TestFromAC_CorpusModule:
    """AC 1 — corpus loader/manifest module is importable and exposes expected symbols."""

    def test_corpus_constant_is_a_list(self) -> None:
        """ENTITY_EXTRACTOR_CORPUS must be a list (sequence contract)."""
        assert isinstance(ENTITY_EXTRACTOR_CORPUS, list)

    def test_load_corpus_is_callable(self) -> None:
        """load_corpus must be a callable exported by the corpus module."""
        assert callable(load_corpus)

    def test_corpus_sample_type_is_exported(self) -> None:
        """CorpusSample type must be re-exported from the corpus module."""
        assert CorpusSample is not None

    def test_gold_entity_type_is_exported(self) -> None:
        """GoldEntity type must be re-exported from the corpus module."""
        assert GoldEntity is not None


# ---------------------------------------------------------------------------
# AC 2 — ordered corpus contract: ≥8 samples, both kinds, unique stable labels
# ---------------------------------------------------------------------------


class TestFromAC_CorpusContract:
    """AC 2 — corpus has ≥8 trimmed samples, python+markdown kinds, unique labels."""

    def test_corpus_has_at_least_eight_samples(self) -> None:
        """Corpus must contain at least 8 samples (AC minimum)."""
        samples = load_corpus()
        assert len(samples) >= 8, f"Expected ≥ 8 corpus samples, got {len(samples)}"

    def test_corpus_has_python_source_kind(self) -> None:
        """At least one sample must have source_kind == 'python'."""
        samples = load_corpus()
        kinds = {s.source_kind for s in samples}
        assert "python" in kinds, f"No 'python' source_kind found; present kinds: {kinds}"

    def test_corpus_has_markdown_source_kind(self) -> None:
        """At least one sample must have source_kind == 'markdown'."""
        samples = load_corpus()
        kinds = {s.source_kind for s in samples}
        assert "markdown" in kinds, f"No 'markdown' source_kind found; present kinds: {kinds}"

    def test_source_labels_are_unique(self) -> None:
        """All source_label values must be unique across the corpus."""
        samples = load_corpus()
        labels = [s.source_label for s in samples]
        duplicates = {lbl for lbl in labels if labels.count(lbl) > 1}
        assert not duplicates, f"Duplicate source_label values found: {duplicates}"

    def test_source_labels_are_non_empty_strings(self) -> None:
        """Every source_label must be a non-empty stripped string."""
        samples = load_corpus()
        for sample in samples:
            assert isinstance(sample.source_label, str), (
                f"source_label is not a str: {sample.source_label!r}"
            )
            assert sample.source_label.strip(), "source_label is blank or whitespace-only"

    def test_samples_have_non_empty_text(self) -> None:
        """Every sample must carry non-empty checked-in text."""
        samples = load_corpus()
        for sample in samples:
            assert isinstance(sample.text, str), f"text field is not a str: {sample.text!r}"
            assert sample.text.strip(), f"text is blank for sample '{sample.source_label}'"

    def test_source_kind_values_are_valid(self) -> None:
        """All source_kind values must be 'python' or 'markdown'."""
        samples = load_corpus()
        for sample in samples:
            assert sample.source_kind in _VALID_SOURCE_KINDS, (
                f"Invalid source_kind '{sample.source_kind}' on "
                f"sample '{sample.source_label}'; "
                f"expected one of {sorted(_VALID_SOURCE_KINDS)}"
            )

    def test_samples_have_non_empty_origin_path(self) -> None:
        """Every sample must carry a non-empty origin_path for provenance."""
        samples = load_corpus()
        for sample in samples:
            assert isinstance(sample.origin_path, str), (
                f"origin_path is not a str on sample '{sample.source_label}'"
            )
            assert sample.origin_path.strip(), (
                f"origin_path is blank for sample '{sample.source_label}'"
            )

    def test_corpus_samples_carry_gold_entities_field(self) -> None:
        """Every CorpusSample must expose a gold_entities attribute (may be empty list)."""
        samples = load_corpus()
        for sample in samples:
            assert hasattr(sample, "gold_entities"), (
                f"CorpusSample '{sample.source_label}' has no gold_entities field"
            )
            assert isinstance(sample.gold_entities, list), (
                f"gold_entities on '{sample.source_label}' is not a list"
            )

    def test_sample_text_is_trimmed(self) -> None:
        """Every sample.text must be pre-trimmed (no leading/trailing whitespace).

        The AC requires 'trimmed OwlBear excerpts' — text must already be
        stripped, not just non-empty after stripping.
        """
        samples = load_corpus()
        for sample in samples:
            assert sample.text == sample.text.strip(), (
                f"sample '{sample.source_label}' has leading/trailing whitespace "
                "in text; corpus requires pre-trimmed excerpts"
            )

    def test_source_labels_are_not_uuid_like(self) -> None:
        """Every source_label must be human-readable, not a UUID or opaque ID.

        The AC requires 'unique stable human-readable source_label values' —
        UUID-like strings are not human-readable.
        """
        samples = load_corpus()
        for sample in samples:
            assert not _is_uuid_like(sample.source_label), (
                f"source_label '{sample.source_label}' looks like a UUID; "
                "labels must be human-readable, not generated IDs"
            )

    def test_origin_path_references_owlbear_source_tree(self) -> None:
        """Every origin_path must point into the OwlBear source tree.

        The AC requires 'trimmed OwlBear excerpts', so each sample must come
        from src/ or tests/ — not an arbitrary external path.
        """
        samples = load_corpus()
        for sample in samples:
            assert sample.origin_path.startswith(_OWLBEAR_PATH_PREFIXES), (
                f"origin_path '{sample.origin_path}' on sample "
                f"'{sample.source_label}' does not reference the OwlBear source "
                "tree; expected a path starting with src/ or tests/"
            )


# ---------------------------------------------------------------------------
# AC 3 — gold keyed by (normalized_name, entity_type), valid EntityType strings
# ---------------------------------------------------------------------------


class TestFromAC_GoldKeyContract:
    """AC 3 — gold annotations use (normalized_name, entity_type); no UUID keys."""

    def test_gold_entities_have_normalized_name(self) -> None:
        """Each GoldEntity must expose a normalized_name attribute."""
        samples = load_corpus()
        for sample in samples:
            for gold in sample.gold_entities:
                assert hasattr(gold, "normalized_name"), (
                    f"GoldEntity missing normalized_name on sample '{sample.source_label}'"
                )

    def test_gold_entities_have_entity_type(self) -> None:
        """Each GoldEntity must expose an entity_type attribute."""
        samples = load_corpus()
        for sample in samples:
            for gold in sample.gold_entities:
                assert hasattr(gold, "entity_type"), (
                    f"GoldEntity missing entity_type on sample '{sample.source_label}'"
                )

    def test_gold_entity_type_values_match_entitytype_strings(self) -> None:
        """All entity_type values in gold must match current EntityType string values."""
        samples = load_corpus()
        for sample in samples:
            for gold in sample.gold_entities:
                assert gold.entity_type in _VALID_ENTITY_TYPES, (
                    f"entity_type '{gold.entity_type}' on sample "
                    f"'{sample.source_label}' is not a valid EntityType value; "
                    f"valid values: {sorted(_VALID_ENTITY_TYPES)}"
                )

    def test_gold_entity_type_is_not_generic_entity_string(self) -> None:
        """entity_type must not be the generic string 'entity' or 'Entity'."""
        samples = load_corpus()
        for sample in samples:
            for gold in sample.gold_entities:
                assert gold.entity_type not in {"entity", "Entity"}, (
                    f"entity_type '{gold.entity_type}' is a generic label, "
                    "not a valid EntityType value"
                )

    def test_gold_normalized_name_is_not_uuid(self) -> None:
        """normalized_name must not be a UUID hex or canonical UUID string."""
        samples = load_corpus()
        for sample in samples:
            for gold in sample.gold_entities:
                name = gold.normalized_name
                assert not _is_uuid_like(name), (
                    f"normalized_name '{name}' looks like a UUID (hex or canonical); "
                    "gold keys must be human-readable text, not generated IDs"
                )

    def test_gold_normalized_name_is_non_empty_string(self) -> None:
        """Every normalized_name must be a non-empty, non-whitespace string."""
        samples = load_corpus()
        for sample in samples:
            for gold in sample.gold_entities:
                assert isinstance(gold.normalized_name, str), (
                    f"normalized_name is not a str on sample '{sample.source_label}'"
                )
                assert gold.normalized_name.strip(), (
                    f"normalized_name is blank for a GoldEntity on sample '{sample.source_label}'"
                )

    def test_at_least_one_sample_has_gold_entities(self) -> None:
        """At least one corpus sample must have a non-empty gold_entities list."""
        samples = load_corpus()
        any_gold = any(len(s.gold_entities) > 0 for s in samples)
        assert any_gold, (
            "No corpus sample carries any gold_entities — "
            "fixtures are incomplete or gold annotations are missing"
        )

    def test_gold_entity_type_not_derived_from_entity_id(self) -> None:
        """Gold entry fields must not include an 'id' attribute (UUID-backed identity)."""
        samples = load_corpus()
        for sample in samples:
            for gold in sample.gold_entities:
                assert not hasattr(gold, "id"), (
                    f"GoldEntity on sample '{sample.source_label}' has an 'id' "
                    "attribute — gold keys must use (normalized_name, entity_type), "
                    "never Entity.id"
                )


# ---------------------------------------------------------------------------
# AC 4 — pure-data loading: order preserved, no live crawl, no model call
# ---------------------------------------------------------------------------


class TestFromAC_PureDataLoading:
    """AC 4 — loading is pure-data: model-free, crawl-free, manifest-order preserved."""

    def test_load_corpus_is_model_free(self) -> None:
        """load_corpus() must not trigger any LLM call.

        pydantic_ai.models.ALLOW_MODEL_REQUESTS is False for this module.
        Any LLM call would raise ModelRequestForbiddenError, failing this test.
        """
        samples = load_corpus()
        # Reaching here means no LLM call was made.
        assert samples is not None

    def test_load_corpus_returns_sequence_not_generator(self) -> None:
        """load_corpus() return value must be indexable (list), not a generator."""
        samples = load_corpus()
        assert isinstance(samples, list), (
            f"load_corpus() returned {type(samples).__name__}, expected list"
        )

    def test_manifest_order_preserved_by_load_corpus(self) -> None:
        """load_corpus() must return samples in the same order as ENTITY_EXTRACTOR_CORPUS."""
        loaded = load_corpus()
        assert len(loaded) == len(ENTITY_EXTRACTOR_CORPUS), (
            f"load_corpus() returned {len(loaded)} samples "
            f"but ENTITY_EXTRACTOR_CORPUS has {len(ENTITY_EXTRACTOR_CORPUS)}"
        )
        for i, (loaded_sample, manifest_sample) in enumerate(
            zip(loaded, ENTITY_EXTRACTOR_CORPUS, strict=True)
        ):
            assert loaded_sample.source_label == manifest_sample.source_label, (
                f"Order mismatch at position {i}: "
                f"got '{loaded_sample.source_label}', "
                f"expected '{manifest_sample.source_label}'"
            )

    def test_load_corpus_is_deterministic_across_calls(self) -> None:
        """Two consecutive calls to load_corpus() must return identically ordered results."""
        first = [s.source_label for s in load_corpus()]
        second = [s.source_label for s in load_corpus()]
        assert first == second, (
            "load_corpus() returned different orders on two consecutive calls — "
            "corpus loading is not deterministic"
        )

    def test_corpus_sample_fields_are_statically_accessible(self) -> None:
        """All CorpusSample fields must be accessible without IO or computation."""
        samples = load_corpus()
        for sample in samples:
            # Plain attribute reads — no filesystem access, no model call, no network.
            _ = sample.source_label
            _ = sample.source_kind
            _ = sample.origin_path
            _ = sample.text
            _ = sample.gold_entities

    def test_load_corpus_result_is_not_empty(self) -> None:
        """load_corpus() must return a non-empty list."""
        samples = load_corpus()
        assert len(samples) > 0, "load_corpus() returned an empty list"

    def test_corpus_constant_and_load_corpus_agree_on_count(self) -> None:
        """ENTITY_EXTRACTOR_CORPUS and load_corpus() must report the same sample count."""
        assert len(load_corpus()) == len(ENTITY_EXTRACTOR_CORPUS)

    def test_load_corpus_does_not_crawl_repo(self) -> None:
        """load_corpus() must not crawl the filesystem to discover corpus data.

        The AC requires 'no live repo crawl is required' — the corpus must be
        statically embedded or checked-in, not discovered by walking directories.
        Any call to os.walk, os.scandir, or pathlib glob/iterdir during
        load_corpus() would indicate a live crawl and must not occur.
        """
        from unittest.mock import patch

        def _fail_crawl(*_args: object, **_kwargs: object) -> object:
            msg = (
                "load_corpus() attempted a filesystem crawl; corpus must be "
                "pure checked-in static data, not dynamically discovered"
            )
            raise AssertionError(msg)

        with (
            patch("os.walk", side_effect=_fail_crawl),
            patch("os.scandir", side_effect=_fail_crawl),
            patch("pathlib.Path.iterdir", side_effect=_fail_crawl),
            patch("pathlib.Path.glob", side_effect=_fail_crawl),
            patch("pathlib.Path.rglob", side_effect=_fail_crawl),
        ):
            # Reaching here means load_corpus() made no crawl calls.
            result = load_corpus()
        assert result is not None

    def test_load_corpus_does_not_read_live_files(self) -> None:
        """load_corpus() must not perform any live filesystem reads.

        AC4 requires corpus loading to be pure-data only with no live repo crawl.
        A pure-data corpus must have its text statically embedded — calling
        open(), Path.read_text(), or Path.read_bytes() at load time means the
        loader is reading live repo files rather than using checked-in static data.
        This closes the gap left by test_load_corpus_does_not_crawl_repo, which
        only blocks directory-traversal calls but not direct file reads.
        """
        from unittest.mock import patch

        def _fail_read(*_args: object, **_kwargs: object) -> object:
            msg = (
                "load_corpus() attempted a live file read (open/read_text/read_bytes); "
                "corpus text must be pure checked-in static data, not read from "
                "live repo files at load time"
            )
            raise AssertionError(msg)

        with (
            patch("builtins.open", side_effect=_fail_read),
            patch("pathlib.Path.read_text", side_effect=_fail_read),
            patch("pathlib.Path.read_bytes", side_effect=_fail_read),
        ):
            # Reaching here means load_corpus() made no direct file read calls.
            result = load_corpus()
        assert result is not None
