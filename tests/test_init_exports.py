"""Public import inventory for the target delivery package."""

from __future__ import annotations

import importlib

import owlbear_kanban


def test_target_and_snapshot_exports_remain_callable() -> None:
    required = {
        "TargetAuthorityRegistry",
        "TargetRuntime",
        "WorkItemProjector",
        "authorize_target_mutation",
        "cut_over_target_runtime",
        "create_legacy_snapshot",
    }

    assert required <= set(owlbear_kanban.__all__)
    assert all(callable(getattr(owlbear_kanban, name)) for name in required)


def test_legacy_runtime_exports_and_modules_are_absent() -> None:
    removed = {
        "AgentView",
        "BoardConfig",
        "KanbanEngine",
        "Task",
        "TaskSummary",
        "WorkSession",
        "atomic_write",
        "pick_dispatchable",
    }

    assert removed.isdisjoint(owlbear_kanban.__all__)
    assert all(not hasattr(owlbear_kanban, name) for name in removed)
    for module in ("engine", "models", "storage", "migrate", "decisions"):
        try:
            importlib.import_module(f"owlbear_kanban.{module}")
        except ModuleNotFoundError:
            continue
        raise AssertionError(f"retired module remains importable: {module}")
