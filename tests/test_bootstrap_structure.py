"""Structural tests for bootstrap/ package split (task #480)."""

from __future__ import annotations

from pathlib import Path


PKG = Path("src/owlbear/bootstrap")


class TestBootstrapPackageLayout:
    """Verify directory/file layout matches AC."""

    def test_is_package(self) -> None:
        assert PKG.is_dir()
        assert (PKG / "__init__.py").is_file()

    def test_submodules_exist(self) -> None:
        for name in ("hooks", "channel", "knowledge", "toolsets", "registry"):
            assert (PKG / f"{name}.py").is_file(), f"Missing {name}.py"

    def test_old_monolith_deleted(self) -> None:
        assert not Path("src/owlbear/bootstrap.py").is_file()

    def test_init_under_200_lines(self) -> None:
        lines = (PKG / "__init__.py").read_text(encoding="utf-8").splitlines()
        assert len(lines) < 200, f"__init__.py has {len(lines)} lines"

    def test_no_c901_plr0912_plr0915_noqa(self) -> None:
        for py in PKG.glob("*.py"):
            content = py.read_text(encoding="utf-8")
            for code in ("C901", "PLR0912", "PLR0915"):
                assert code not in content, f"{py.name} still has {code}"


class TestReExports:
    """All symbols importable from owlbear.bootstrap (AC #11)."""

    def test_all_public_symbols(self) -> None:
        from owlbear.bootstrap import (
            BootstrapResult,
            ComponentStatus,
            StartupSummary,
            bootstrap,
            build_agent_registry,
            build_hooks,
            build_mcp_registry,
            build_toolsets,
            create_channel,
        )

        assert all([
            BootstrapResult,
            ComponentStatus,
            StartupSummary,
            bootstrap,
            build_agent_registry,
            build_hooks,
            build_mcp_registry,
            build_toolsets,
            create_channel,
        ])

    def test_private_helpers_importable(self) -> None:
        from owlbear.bootstrap import (
            _KnowledgeInfra,
            _add_project_toolset,
            _build_bookmark_toolset,
            _build_knowledge_infra,
            _build_knowledge_source_toolset,
            _build_knowledge_toolset,
            _build_screenshot_components,
            _build_web_search_toolset,
            _patch_project_toolset_agent,
            _resolve_active_project,
        )

        assert all([
            _KnowledgeInfra,
            _add_project_toolset,
            _build_bookmark_toolset,
            _build_knowledge_infra,
            _build_knowledge_source_toolset,
            _build_knowledge_toolset,
            _build_screenshot_components,
            _build_web_search_toolset,
            _patch_project_toolset_agent,
            _resolve_active_project,
        ])
