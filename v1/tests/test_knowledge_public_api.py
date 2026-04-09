"""Tests for knowledge __init__.py public API surface (task #839)."""

from __future__ import annotations


class TestFromAC_KnowledgePublicAPI:
    """__all__ must be defined and contain exactly the 14 AC symbols."""

    EXPECTED_EXPORTS: frozenset[str] = frozenset(
        {
            "Document",
            "Edge",
            "Entity",
            "EntityType",
            "RelationType",
            "DocumentStatus",
            "GraphStore",
            "IngestPipeline",
            "KnowledgeQueryService",
            "BookmarkStore",
            "IngestResult",
            "EmbeddingProvider",
            "VectorStoreProtocol",
            "init_db",
        }
    )

    def test_all_is_defined(self) -> None:
        import owlbear.memory.knowledge

        assert hasattr(owlbear.memory.knowledge, "__all__"), "__all__ must be defined"

    def test_all_is_sequence(self) -> None:
        import owlbear.memory.knowledge

        assert isinstance(owlbear.memory.knowledge.__all__, (tuple, list)), (
            "__all__ must be tuple or list"
        )

    def test_all_contains_all_expected_names(self) -> None:
        import owlbear.memory.knowledge

        actual = set(owlbear.memory.knowledge.__all__)
        missing = self.EXPECTED_EXPORTS - actual
        assert not missing, f"Missing from __all__: {missing}"

    def test_all_has_no_unexpected_names(self) -> None:
        import owlbear.memory.knowledge

        actual = set(owlbear.memory.knowledge.__all__)
        extra = actual - self.EXPECTED_EXPORTS
        assert not extra, f"Unexpected entries in __all__: {extra}"

    def test_all_exact_set_equality(self) -> None:
        import owlbear.memory.knowledge

        actual = set(owlbear.memory.knowledge.__all__)
        assert actual == self.EXPECTED_EXPORTS, (
            f"__all__ mismatch.\n"
            f"  Extra:   {actual - self.EXPECTED_EXPORTS}\n"
            f"  Missing: {self.EXPECTED_EXPORTS - actual}"
        )

    def test_expected_exports_count(self) -> None:
        import owlbear.memory.knowledge

        assert len(owlbear.memory.knowledge.__all__) == len(self.EXPECTED_EXPORTS), (
            f"Expected {len(self.EXPECTED_EXPORTS)} exports, "
            f"got {len(owlbear.memory.knowledge.__all__)}"
        )
