"""Tests for DispatchContext frozen-dataclass contract — task #959.

Covers: DispatchContext must be a frozen dataclass whose fields cannot be
mutated after construction, and whose instances are hashable.

The formatter and delegation forwarding contracts are covered by the
existing tests/test_delegation.py suite from #958.
"""

from __future__ import annotations

import dataclasses

import pytest

from owlbear.core.delegation import DispatchContext

# ---------------------------------------------------------------------------
# Frozen DispatchContext carrier
# (AC: DispatchContext must be a frozen dataclass)
# ---------------------------------------------------------------------------


class TestFromAC_FrozenDispatchContext:
    """DispatchContext is a frozen dataclass — mutations raise FrozenInstanceError."""

    # -- Error paths: each field must be immutable -------------------------

    def test_mutating_workspace_root_raises(self) -> None:
        """Assigning a new value to workspace_root raises FrozenInstanceError."""
        ctx = DispatchContext(workspace_root="/project", channel_name="slack")
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.workspace_root = "/mutated"  # type: ignore[misc]

    def test_mutating_channel_name_raises(self) -> None:
        """Assigning a new value to channel_name raises FrozenInstanceError."""
        ctx = DispatchContext(workspace_root="/project", channel_name="slack")
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.channel_name = "mutated-channel"  # type: ignore[misc]

    def test_mutating_task_id_raises(self) -> None:
        """Assigning a new value to task_id raises FrozenInstanceError."""
        ctx = DispatchContext(workspace_root="/project", channel_name="slack", task_id="959")
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.task_id = "000"  # type: ignore[misc]

    def test_mutating_task_title_raises(self) -> None:
        """Assigning a new value to task_title raises FrozenInstanceError."""
        ctx = DispatchContext(
            workspace_root="/project",
            channel_name="slack",
            task_title="Original Title",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.task_title = "Mutated Title"  # type: ignore[misc]

    def test_mutating_task_status_raises(self) -> None:
        """Assigning a new value to task_status raises FrozenInstanceError."""
        ctx = DispatchContext(workspace_root="/project", channel_name="slack", task_status="todo")
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.task_status = "done"  # type: ignore[misc]

    # -- Edge: setting an optional field that starts as None ---------------

    def test_setting_optional_field_from_none_raises(self) -> None:
        """Setting task_id when it was not provided at construction raises FrozenInstanceError.

        A non-frozen dataclass silently allows this; a frozen one must reject it.
        """
        ctx = DispatchContext(workspace_root="/project", channel_name="slack")
        assert ctx.task_id is None  # pre-condition: field starts as None
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.task_id = "injected-at-runtime"  # type: ignore[misc]

    # -- Boundary: frozen dataclasses must be hashable ---------------------

    def test_instance_is_hashable(self) -> None:
        """hash() on a DispatchContext instance must not raise.

        Default (non-frozen) dataclasses set __hash__ = None when eq=True,
        making instances unhashable. A frozen dataclass generates __hash__
        automatically and must be usable as a dict key or set element.
        """
        ctx = DispatchContext(
            workspace_root="/project",
            channel_name="slack",
            task_id="42",
            task_title="Feature",
            task_status="todo",
        )
        # Must not raise TypeError: unhashable type
        h = hash(ctx)
        assert isinstance(h, int)

    def test_equal_instances_have_equal_hashes(self) -> None:
        """Two identically constructed DispatchContext instances hash to the same value."""
        ctx_a = DispatchContext(workspace_root="/project", channel_name="slack", task_id="1")
        ctx_b = DispatchContext(workspace_root="/project", channel_name="slack", task_id="1")
        assert hash(ctx_a) == hash(ctx_b)
