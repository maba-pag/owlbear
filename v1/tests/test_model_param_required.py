"""Tests: model parameter required in bootstrap helpers and AgentRegistry (#806).

TDD RED phase — these tests assert ``TypeError`` when ``chat_model`` /
``default_model`` is omitted.  They should all **fail** until #551 removes
the default values, making the parameters positional-or-keyword-required.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_knowledge_infra_mock() -> MagicMock:
    """Return a lightweight stand-in for ``_KnowledgeInfra``."""
    return MagicMock(name="KnowledgeInfra")


def _dummy_resolver(name: str) -> MagicMock:
    return MagicMock(name=f"toolset-{name}")


# ---------------------------------------------------------------------------
# Contract: chat_model / default_model is required (no default)
# ---------------------------------------------------------------------------


class TestFromAC_ModelParamRequired:
    """Each function must raise TypeError when chat_model / default_model
    is omitted — proving the parameter has no default value.

    Currently all four functions declare ``chat_model|default_model = "gpt-4o"``,
    so these tests will **fail** (no TypeError raised).  After #551 removes
    the defaults, they will pass.
    """

    def test_build_knowledge_infra_requires_chat_model(self, tmp_path: Path) -> None:
        """_build_knowledge_infra(workspace) without chat_model → TypeError."""
        from owlbear.bootstrap.knowledge import _build_knowledge_infra

        with pytest.raises(TypeError, match="chat_model"):
            _build_knowledge_infra(tmp_path)

    def test_build_knowledge_toolset_requires_chat_model(self, tmp_path: Path) -> None:
        """_build_knowledge_toolset(workspace, infra) without chat_model → TypeError."""
        from owlbear.bootstrap.knowledge import _build_knowledge_toolset

        infra = _make_knowledge_infra_mock()

        with pytest.raises(TypeError, match="chat_model"):
            _build_knowledge_toolset(tmp_path, infra)

    def test_build_bookmark_toolset_requires_chat_model(self, tmp_path: Path) -> None:
        """_build_bookmark_toolset(infra, workspace) without chat_model → TypeError."""
        from owlbear.bootstrap.knowledge import _build_bookmark_toolset

        infra = _make_knowledge_infra_mock()

        with pytest.raises(TypeError, match="chat_model"):
            _build_bookmark_toolset(infra, tmp_path)

    def test_agent_registry_requires_default_model(self, tmp_path: Path) -> None:
        """AgentRegistry(agents_dir, resolver) without default_model → TypeError."""
        from owlbear.core.agent_registry import AgentRegistry

        with pytest.raises(TypeError, match="default_model"):
            AgentRegistry(tmp_path, _dummy_resolver)
