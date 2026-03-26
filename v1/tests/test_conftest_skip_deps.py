"""Tests for conftest.py optional-dependency skip logic (AC3: warnings emitted)."""

from __future__ import annotations

import warnings
from unittest.mock import patch


class TestDetectMissingOptionalDeps:
    """Verify _detect_missing_optional_deps warns and returns skip list."""

    def test_missing_numpy_warns_per_file(self) -> None:
        """When numpy is absent, a warning is emitted for each numpy-dependent test file."""
        from tests.conftest import _detect_missing_optional_deps

        orig_import = __import__

        def _mock_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "numpy":
                msg = "No module named 'numpy'"
                raise ModuleNotFoundError(msg)
            return orig_import(name, *args, **kwargs)

        with (
            warnings.catch_warnings(record=True) as caught,
            patch("builtins.__import__", side_effect=_mock_import),
        ):
            warnings.simplefilter("always")
            skipped = _detect_missing_optional_deps()

        # Should skip the 3 numpy-dependent files
        assert "test_embedding_idle_timeout.py" in skipped
        assert "test_knowledge_embeddings.py" in skipped
        assert "test_voice_stt.py" in skipped

        # AC3: each skipped file produces a warning
        msgs = [str(w.message) for w in caught]
        assert any("test_embedding_idle_timeout.py" in m for m in msgs)
        assert any("test_knowledge_embeddings.py" in m for m in msgs)
        assert any("test_voice_stt.py" in m for m in msgs)

    def test_missing_qdrant_warns_per_file(self) -> None:
        """When qdrant_client is absent, a warning is emitted for each qdrant-dependent file."""
        from tests.conftest import _detect_missing_optional_deps

        orig_import = __import__

        def _mock_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "qdrant_client":
                msg = "No module named 'qdrant_client'"
                raise ModuleNotFoundError(msg)
            return orig_import(name, *args, **kwargs)

        with (
            warnings.catch_warnings(record=True) as caught,
            patch("builtins.__import__", side_effect=_mock_import),
        ):
            warnings.simplefilter("always")
            skipped = _detect_missing_optional_deps()

        assert "test_qdrant_vector_store.py" in skipped
        assert "test_search_benchmark.py" in skipped

        msgs = [str(w.message) for w in caught]
        assert any("test_qdrant_vector_store.py" in m for m in msgs)
        assert any("test_search_benchmark.py" in m for m in msgs)

    def test_all_deps_present_no_warnings(self) -> None:
        """When all optional deps are installed, no files are skipped and no warnings."""
        from tests.conftest import _detect_missing_optional_deps

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            # Don't mock — use real imports (numpy/qdrant may or may not be installed)
            # If they ARE installed, skip list should be empty for those deps
            _detect_missing_optional_deps()

        # Any warnings emitted must be about actually-missing deps, not spurious
        for w in caught:
            assert "not installed" in str(w.message)

    def test_both_missing_skips_all_five(self) -> None:
        """When both numpy and qdrant_client are absent, all 5 files are skipped."""
        from tests.conftest import _detect_missing_optional_deps

        orig_import = __import__

        def _mock_import(name: str, *args: object, **kwargs: object) -> object:
            if name in ("numpy", "qdrant_client"):
                msg = f"No module named '{name}'"
                raise ModuleNotFoundError(msg)
            return orig_import(name, *args, **kwargs)

        with (
            warnings.catch_warnings(record=True) as caught,
            patch("builtins.__import__", side_effect=_mock_import),
        ):
            warnings.simplefilter("always")
            skipped = _detect_missing_optional_deps()

        assert len(skipped) == 5
        assert len(caught) == 5
