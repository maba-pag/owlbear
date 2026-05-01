"""Failing tests for #1228: dead adapter functions removed from adapter.py.

RED phase — all tests must fail until the builder removes list_tasks, show_task,
board_config, and list_sessions from owlbear_cockpit.adapter, and updates __all__
to contain only 'valid_transitions'.

AC coverage:
  - list_tasks, show_task, board_config, list_sessions removed from adapter.__all__
  - list_tasks, show_task, board_config, list_sessions removed as attributes
  - __all__ updated to contain only 'valid_transitions'
"""

from __future__ import annotations


class TestFromAC_AdapterDeadCodeRemoval:
    """Tests that dead adapter functions are removed and valid_transitions is retained.

    Covers AC5 (td:1): dead adapter functions removed from adapter.py;
    valid_transitions retained; __all__ updated.

    All tests FAIL in RED phase because the dead functions still exist.
    After builder removes them, all tests pass.
    """

    def test_all_contains_only_valid_transitions(self) -> None:
        """adapter.__all__ must be exactly ['valid_transitions'] — no dead symbols."""
        from owlbear_cockpit import adapter  # noqa: PLC0415

        # Currently __all__ = ['board_config', 'list_sessions', 'list_tasks',
        #                       'show_task', 'valid_transitions'] — 5 items → FAILS
        assert adapter.__all__ == ["valid_transitions"], (
            f"adapter.__all__ must contain only 'valid_transitions', got {adapter.__all__!r}"
        )

    def test_list_tasks_not_in_adapter(self) -> None:
        """list_tasks must be removed from the adapter module entirely."""
        from owlbear_cockpit import adapter  # noqa: PLC0415

        assert not hasattr(adapter, "list_tasks"), (
            "adapter.list_tasks still exists — it must be removed per AC5"
        )

    def test_show_task_not_in_adapter(self) -> None:
        """show_task must be removed from the adapter module entirely."""
        from owlbear_cockpit import adapter  # noqa: PLC0415

        assert not hasattr(adapter, "show_task"), (
            "adapter.show_task still exists — it must be removed per AC5"
        )

    def test_board_config_not_in_adapter(self) -> None:
        """board_config must be removed from the adapter module entirely."""
        from owlbear_cockpit import adapter  # noqa: PLC0415

        assert not hasattr(adapter, "board_config"), (
            "adapter.board_config still exists — it must be removed per AC5"
        )

    def test_list_sessions_not_in_adapter(self) -> None:
        """list_sessions must be removed from the adapter module entirely."""
        from owlbear_cockpit import adapter  # noqa: PLC0415

        assert not hasattr(adapter, "list_sessions"), (
            "adapter.list_sessions still exists — it must be removed per AC5"
        )
