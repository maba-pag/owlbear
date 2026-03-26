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

# Pre-compiled regex for gold alignment normalization.
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    """Lowercase and strip all non-alphanumeric characters for loose substring matching.

    Used to compare gold entity normalized_names against excerpt text without
    being tripped up by spaces, underscores, or camelCase boundaries:
    'hook reaction rule' -> 'hookreactionrule'
    'HookReactionRule'  -> 'hookreactionrule'
    """
    return _NON_ALNUM_RE.sub("", text.lower())


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

    def test_corpus_module_import_does_not_do_filesystem_io(self) -> None:
        """Module-level code must not perform any filesystem IO at import time.

        AC4 requires 'no live repo crawl is required' and pure-data only loading.
        The corpus constant ENTITY_EXTRACTOR_CORPUS must be statically defined,
        not built by reading live repo files during module initialisation
        ("import-time IO").

        This test covers the gap left by test_load_corpus_does_not_crawl_repo
        and test_load_corpus_does_not_read_live_files: those tests patch IO calls
        inside load_corpus(), but cannot detect IO done at import time because
        the corpus module is already loaded at collection before any test method
        runs.

        Strategy: compile the module source before applying patches (so our own
        file read is not intercepted), then exec the compiled bytecode in a
        namespace where all filesystem IO functions raise AssertionError.  Any
        import-time IO in the module body will trip the guard and fail the test.
        """
        from pathlib import Path
        from unittest.mock import patch

        corpus_path = Path(__file__).parent / "entity_extractor_corpus.py"
        # Read + compile BEFORE patches are active so our own read is not
        # intercepted by the guards below.
        source = corpus_path.read_text(encoding="utf-8")
        code = compile(source, str(corpus_path), "exec")

        def _fail_io(*_args, **_kwargs):
            msg = (
                "entity_extractor_corpus performed filesystem IO at module import "
                "time; all corpus data must be statically embedded, not read from "
                "live repo files during module initialisation"
            )
            raise AssertionError(msg)

        namespace = {
            "__name__": "_test_import_io_purity",
            "__file__": str(corpus_path),
            "__package__": "tests.benchmarks",
        }
        with (
            patch("os.walk", side_effect=_fail_io),
            patch("os.scandir", side_effect=_fail_io),
            patch("pathlib.Path.iterdir", side_effect=_fail_io),
            patch("pathlib.Path.glob", side_effect=_fail_io),
            patch("pathlib.Path.rglob", side_effect=_fail_io),
            patch("builtins.open", side_effect=_fail_io),
            patch("pathlib.Path.read_text", side_effect=_fail_io),
            patch("pathlib.Path.read_bytes", side_effect=_fail_io),
        ):
            exec(code, namespace)  # noqa: S102


# ---------------------------------------------------------------------------
# AC 1 (gap) — corpus provenance: origin_path files exist, text is verbatim
# ---------------------------------------------------------------------------


class TestFromAC_CorpusProvenance:
    """AC 1 gap — every sample origin_path must exist on disk and the text must
    be a verbatim excerpt of that file's content.

    The reviewer found that:
    - 4 markdown samples reference tests/benchmarks/fixtures/*.md (nonexistent)
    - Python sample texts are synthetic prose not found in the referenced files
    - 1 Python sample references src/owlbear/tools/approval_gate.py (nonexistent)

    These tests enforce that AC1's "trimmed OwlBear samples" requirement is
    actually satisfied by the checked-in corpus data.

    Retry-cycle addition: closes the LAX AC1 gap reported in Review Evidence.
    """

    def test_origin_path_files_exist_on_disk(self) -> None:
        """Every origin_path must resolve to a file that actually exists in the workspace.

        AC1 requires 'trimmed OwlBear samples' — each sample must be sourced
        from a real, checked-in file.  A nonexistent origin_path indicates the
        corpus was populated with synthetic data rather than actual excerpts from
        the project source tree.
        """
        from pathlib import Path

        root = Path(__file__).parent.parent.parent
        samples = load_corpus()
        missing: list[tuple[str, str]] = []
        for sample in samples:
            # Normalize path separators so tests pass on Windows and Linux.
            rel = sample.origin_path.replace("\\", "/")
            if not (root / rel).exists():
                missing.append((sample.source_label, sample.origin_path))
        assert not missing, (
            "The following corpus samples have origin_path values that do not "
            "resolve to an existing file in the workspace.\n"
            "AC1 requires trimmed excerpts from real, checked-in OwlBear files.\n"
            "Missing files:\n"
            + "\n".join(f"  '{lbl}': {path}" for lbl, path in missing)
        )

    def test_sample_text_is_verbatim_excerpt_of_origin_file(self) -> None:
        """Every sample.text must appear verbatim (as a substring) in origin_path.

        AC1 requires 'trimmed OwlBear samples' — 'trimmed' means the text is an
        actual excerpt of the referenced checked-in file.  Synthetic or paraphrased
        prose that does not appear in the file content fails this contract.

        Samples whose origin_path does not exist are reported as failures by
        test_origin_path_files_exist_on_disk; this test also reports them so the
        full set of violations is visible in a single run.
        """
        from pathlib import Path

        root = Path(__file__).parent.parent.parent
        samples = load_corpus()
        failures: list[str] = []
        for sample in samples:
            rel = sample.origin_path.replace("\\", "/")
            abs_path = root / rel
            if not abs_path.exists():
                failures.append(
                    f"  '{sample.source_label}': origin_path '{sample.origin_path}' "
                    "does not exist — cannot verify text provenance"
                )
                continue
            file_content = abs_path.read_text(encoding="utf-8")
            if sample.text not in file_content:
                failures.append(
                    f"  '{sample.source_label}': text not found verbatim in "
                    f"'{sample.origin_path}'.\n"
                    f"    Expected substring: {sample.text[:120]!r}..."
                )
        assert not failures, (
            "The following corpus samples have text that is not a verbatim excerpt "
            "of the referenced origin_path file.\n"
            "AC1 requires trimmed OwlBear samples (real excerpts, not synthetic prose):\n"
            + "\n".join(failures)
        )


# ---------------------------------------------------------------------------
# AC 2 (gap) — gold alignment: each gold entity's normalized_name must be
# derivable from the excerpt text (retry-cycle addition, reviewer FAIL #2)
# ---------------------------------------------------------------------------


class TestFromAC_GoldAlignmentContract:
    """Retry-cycle gap: reviewer found that gold annotations are not tied to
    the excerpt text — several samples pair a trimmed excerpt with gold entities
    whose names do not appear in that chunk at all.

    A benchmark corpus is only useful for recall measurement if the gold
    annotations reference entities that are actually present in (or directly
    derivable from) the excerpt being scored.  A gold label unrelated to the
    text produces false recall failures that measure corpus labeling error
    rather than extractor quality.

    These tests enforce the alignment contract: every gold entity's
    normalized_name, after lowercasing and stripping non-alphanumeric chars,
    must appear as a substring in the similarly normalized sample text.
    """

    def test_each_gold_entity_normalized_name_appears_in_sample_text(
        self,
    ) -> None:
        """Every gold entity normalized_name must be present in the corresponding
        sample text after space/case normalization.

        Normalization: lowercase + strip all non-alphanumeric characters.
        This collapses 'hook reaction rule' and 'HookReactionRule' to the same
        slug so concept names expressed with spaces still match the identifier
        form in source text.

        Fails when gold entities are unrelated to the excerpt (e.g. gold
        'run_daemon' on text '_TRANSIENT_MAX_RETRIES = 3').
        """
        samples = load_corpus()
        failures: list[str] = []
        for sample in samples:
            slug_text = _slug(sample.text)
            for gold in sample.gold_entities:
                slug_name = _slug(gold.normalized_name)
                if slug_name and slug_name not in slug_text:
                    failures.append(
                        f"  sample '{sample.source_label}': "
                        f"gold '{gold.normalized_name}' (slug: '{slug_name}') "
                        f"not found in text {sample.text[:80]!r}"
                    )
        assert not failures, (
            "The following gold entities are not present (even after "
            "space/case normalization) in the corresponding excerpt text.\n"
            "Gold labels must be extractable from the excerpt so the benchmark "
            "measures extractor recall, not corpus labeling error:\n"
            + "\n".join(failures)
        )

    def test_every_sample_has_at_least_one_gold_entity_present_in_text(
        self,
    ) -> None:
        """Every non-empty-gold sample must have at least one entity whose
        normalized_name appears in the excerpt text.

        This is a per-sample gate: at minimum one gold annotation must be
        grounded in the excerpt so the sample contributes meaningful signal
        to recall measurement.
        """
        samples = load_corpus()
        failures: list[str] = []
        for sample in samples:
            if not sample.gold_entities:
                continue
            slug_text = _slug(sample.text)
            found_any = any(
                _slug(gold.normalized_name) in slug_text
                for gold in sample.gold_entities
                if _slug(gold.normalized_name)
            )
            if not found_any:
                failures.append(
                    f"  sample '{sample.source_label}': none of "
                    f"{[g.normalized_name for g in sample.gold_entities]} "
                    f"found in text {sample.text[:80]!r}"
                )
        assert not failures, (
            "The following samples have no gold entity appearing in the excerpt text.\n"
            "Every benchmark sample must contain at least one of its gold entities "
            "to be usable for recall measurement:\n"
            + "\n".join(failures)
        )

    def test_gold_alignment_holds_for_python_samples(self) -> None:
        """Python corpus samples must have all gold entities' names present in
        the excerpt text.

        Python entity names (class names, function names, constants) that are
        annotated as gold should be verbatim identifiers occurring in the source
        excerpt.  After slug normalization they must appear as substrings of the
        normalized text.
        """
        samples = load_corpus()
        failures: list[str] = []
        for sample in samples:
            if sample.source_kind != "python":
                continue
            slug_text = _slug(sample.text)
            for gold in sample.gold_entities:
                slug_name = _slug(gold.normalized_name)
                if slug_name and slug_name not in slug_text:
                    failures.append(
                        f"  '{sample.source_label}': gold '{gold.normalized_name}' "
                        f"(slug: '{slug_name}') not found in Python excerpt "
                        f"{sample.text[:80]!r}"
                    )
        assert not failures, (
            "Python corpus samples must have gold entity names appearing in the excerpt.\n"
            "Python identifiers (class names, function names, constants) should be "
            "substrings of the source excerpt after slug normalization:\n"
            + "\n".join(failures)
        )

    def test_gold_alignment_holds_for_markdown_samples(self) -> None:
        """Markdown corpus samples must have all gold entities' names present
        in the excerpt text.

        Concept and pattern names are expressed with spaces in normalized form
        (e.g. 'module layering').  After slug normalization ('modulelayering')
        they must appear as substrings of the normalized excerpt text.
        """
        samples = load_corpus()
        failures: list[str] = []
        for sample in samples:
            if sample.source_kind != "markdown":
                continue
            slug_text = _slug(sample.text)
            for gold in sample.gold_entities:
                slug_name = _slug(gold.normalized_name)
                if slug_name and slug_name not in slug_text:
                    failures.append(
                        f"  '{sample.source_label}': gold '{gold.normalized_name}' "
                        f"(slug: '{slug_name}') not found in Markdown excerpt "
                        f"{sample.text[:80]!r}"
                    )
        assert not failures, (
            "Markdown corpus samples must have gold entity names appearing in the excerpt.\n"
            "Concept and pattern names (after slug normalization) must be substrings "
            "of the excerpt text:\n"
            + "\n".join(failures)
        )
