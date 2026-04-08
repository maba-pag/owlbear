"""RED-phase tests for removal of dead SourceType.CRAWL stubs (#703).

Verifies that:
- AC1: SourceType.CRAWL is removed from the SourceType enum
- AC2: All crawl-related code removed from refresh.py (CrawlHandler type alias,
  crawl_handler constructor param, _handle_crawl method)
- AC3: "crawl" removed from loader YAML schema
- AC6: No CRAWL/crawl_handler references remain in knowledge engine source

All tests FAIL against the current implementation and PASS after removal.
"""

from __future__ import annotations

import inspect

import pytest


# ---------------------------------------------------------------------------
# AC1 — SourceType.CRAWL removed from enum
# ---------------------------------------------------------------------------


class TestFromAC_SourceTypeCrawlRemoval:  # noqa: N801
    """SourceType enum must not expose a CRAWL member after dead-code removal."""

    def test_source_type_has_no_crawl_member(self) -> None:
        """CRAWL attribute must not exist on SourceType."""
        from owlbear_knowledge.models import SourceType

        assert not hasattr(SourceType, "CRAWL"), (
            "SourceType.CRAWL still exists — AC1 not satisfied"
        )

    def test_source_type_valid_values_only(self) -> None:
        """SourceType enum values must be exactly {url_list, file_glob} — crawl removed."""
        from owlbear_knowledge.models import SourceType

        expected = {"url_list", "file_glob"}
        actual = {e.value for e in SourceType}
        assert actual == expected, (
            f"SourceType still contains unexpected values: {actual - expected}"
        )

    def test_knowledge_source_rejects_crawl_source_type(self) -> None:
        """KnowledgeSource must reject source_type='crawl' after CRAWL is removed from enum."""
        from datetime import UTC, datetime

        import pydantic

        from owlbear_knowledge.models import KnowledgeSource

        now = datetime.now(tz=UTC).isoformat()
        with pytest.raises(pydantic.ValidationError):
            KnowledgeSource(
                name="dead-crawl-source",
                source_type="crawl",  # type: ignore[arg-type]
                enabled=True,
                priority=0,
                config={},
                scope="global",
                created_at=now,
                updated_at=now,
            )


# ---------------------------------------------------------------------------
# AC2 — All crawl-related code removed from refresh.py
# ---------------------------------------------------------------------------


class TestFromAC_RefreshPyCrawlRemoval:  # noqa: N801
    """refresh.py must not export CrawlHandler or house crawl_handler / _handle_crawl."""

    def test_crawl_handler_type_alias_removed(self) -> None:
        """CrawlHandler type alias must not exist at module level in refresh.py."""
        import owlbear_knowledge.refresh as refresh_mod

        assert not hasattr(refresh_mod, "CrawlHandler"), (
            "CrawlHandler type alias still exported from refresh.py — AC2 not satisfied"
        )

    def test_refresh_orchestrator_no_crawl_handler_param(self) -> None:
        """RefreshOrchestrator.__init__ must not accept a crawl_handler parameter."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        sig = inspect.signature(RefreshOrchestrator.__init__)
        assert "crawl_handler" not in sig.parameters, (
            "RefreshOrchestrator.__init__ still has crawl_handler param — AC2 not satisfied"
        )

    def test_refresh_orchestrator_no_handle_crawl_method(self) -> None:
        """RefreshOrchestrator must not have a _handle_crawl method."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        assert not hasattr(RefreshOrchestrator, "_handle_crawl"), (
            "RefreshOrchestrator._handle_crawl still exists — AC2 not satisfied"
        )


# ---------------------------------------------------------------------------
# AC3 — "crawl" removed from loader YAML schema
# ---------------------------------------------------------------------------


class TestFromAC_LoaderCrawlRemoval:  # noqa: N801
    """loader.py YAML schema must not accept 'crawl' as a valid source type."""

    def test_parse_manifest_rejects_crawl_source_type(self) -> None:
        """Parsing a YAML manifest with type: crawl must raise YAMLValidationError."""
        import strictyaml

        from owlbear_knowledge.loader import parse_manifest

        manifest_yaml = """\
sources:
  - name: dead-crawl-source
    type: crawl
    config:
      start_url: https://example.com
"""
        with pytest.raises(strictyaml.YAMLValidationError):
            parse_manifest(manifest_yaml)
