"""Tests verifying all subpackages are importable."""

from __future__ import annotations


class TestSubpackageImports:
    """Verify every subpackage under owlbear is importable."""

    def test_import_owlbear(self) -> None:
        import owlbear

        assert owlbear.__version__ == "0.1.0"

    def test_import_core(self) -> None:
        import owlbear.core  # noqa: F401

    def test_import_providers(self) -> None:
        import owlbear.providers  # noqa: F401

    def test_import_tools(self) -> None:
        import owlbear.tools  # noqa: F401

    def test_import_channels(self) -> None:
        import owlbear.channels  # noqa: F401

    def test_import_memory(self) -> None:
        import owlbear.memory  # noqa: F401

    def test_import_skills(self) -> None:
        import owlbear.skills  # noqa: F401

    def test_import_bearclaw(self) -> None:
        import bearclaw  # noqa: F401
