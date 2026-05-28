from __future__ import annotations

"""Failing tests for #1868: resolve_decision() in owlbear_kanban.decisions.

AC coverage:
  ac1-import           — resolve_decision importable from owlbear_kanban.decisions
  ac2-stale-resolved   — raises ConcurrencyError('ERR_STALE') when DR has non-pending response
  ac2-stale-non-pending— raises ConcurrencyError for any non-pending response value
  ac3-response-field   — frontmatter response field updated to provided response value
  ac3-resolved-by      — frontmatter resolved_by field updated to provided resolved_by value
  ac4-response-section — ## Response section appended to body containing response value
  ac5-notes-included   — notes text included in response section when notes is not None
  ac5-notes-none       — notes NOT included when notes=None
  ac6-persist          — rewritten frontmatter + body persisted to the file (before move)
  ac7-append-summary   — engine.edit_task called with append_body=canonical_summary(response, body)
  ac8-unblock-approved — engine.edit_task(task_id, blocked=False) called when response='approved'
  ac8-unblock-rejected — engine.edit_task(task_id, blocked=False) called when response='rejected'
  ac9-no-unblock       — engine.edit_task(task_id, blocked=False) NOT called for 'needs-info'
  ac10-fnf-swallow     — FileNotFoundError from engine.edit_task caught, not propagated
  ac11-return-path     — returns resolved Path from move_to_resolved
  ac11-resolved-dir    — resolved dir is path.parent.parent / 'resolved'
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from owlbear_kanban import KanbanEngine
from owlbear_kanban.decisions import canonical_summary, resolve_decision
from owlbear_kanban.errors import ConcurrencyError


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_pending_dir(tmp_path: Path) -> Path:
    """Create pending/ directory under tmp_path/decisions/ and return it."""
    pending = tmp_path / "decisions" / "pending"
    pending.mkdir(parents=True)
    return pending


def _write_dr(
    pending_dir: Path,
    *,
    task_id: int = 42,
    response: str = "pending",
    filename: str | None = None,
) -> Path:
    """Write a minimal DR file with the given response into pending_dir."""
    if filename is None:
        filename = f"{task_id}-approach-selection.md"
    content = (
        "---\n"
        f"task_id: {task_id}\n"
        "agent: builder\n"
        "request_type: approach-selection\n"
        "created: '2026-04-01'\n"
        f"response: {response}\n"
        "---\n\n"
        "## Question\nShould we proceed?\n"
    )
    path = pending_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def _parse_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a DR file."""
    from ruamel.yaml import YAML

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    close_idx = next(i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---")
    frontmatter_text = "\n".join(lines[1:close_idx])
    return YAML(typ="safe").load(frontmatter_text) or {}


def _mock_engine() -> MagicMock:
    """Return a MagicMock with spec=KanbanEngine."""
    return MagicMock(spec=KanbanEngine)


# ---------------------------------------------------------------------------
# TestFromAC_ResolveDecision
# ---------------------------------------------------------------------------


class TestResolveDecision:
    """Tests for resolve_decision() mapped to all 11 AC lines."""

    # ------------------------------------------------------------------
    # AC1 — importable
    # ------------------------------------------------------------------

    def test_importable(self) -> None:
        """AC1: resolve_decision is importable from owlbear_kanban.decisions."""
        from owlbear_kanban.decisions import resolve_decision as fn  # noqa: F401

        assert callable(fn)

    # ------------------------------------------------------------------
    # AC2 — ConcurrencyError when not pending
    # ------------------------------------------------------------------

    def test_raises_concurrency_error_when_already_approved(self, tmp_path: Path) -> None:
        """AC2: DR with response='approved' raises ConcurrencyError with code ERR_STALE."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir, response="approved")
        engine = _mock_engine()

        with pytest.raises(ConcurrencyError) as exc_info:
            resolve_decision(path, "approved", engine)

        assert exc_info.value.code == "ERR_STALE"

    def test_raises_concurrency_error_for_needs_info_response(self, tmp_path: Path) -> None:
        """AC2: DR with response='needs-info' also raises ConcurrencyError(ERR_STALE)."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir, response="needs-info")
        engine = _mock_engine()

        with pytest.raises(ConcurrencyError) as exc_info:
            resolve_decision(path, "approved", engine)

        assert exc_info.value.code == "ERR_STALE"

    # ------------------------------------------------------------------
    # AC3 — frontmatter update
    # ------------------------------------------------------------------

    def test_frontmatter_response_updated(self, tmp_path: Path) -> None:
        """AC3: Resolved file has response field set to the provided response value."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir)
        engine = _mock_engine()

        resolved = resolve_decision(path, "approved", engine)

        fm = _parse_frontmatter(resolved)
        assert fm["response"] == "approved"

    def test_frontmatter_resolved_by_default(self, tmp_path: Path) -> None:
        """AC3: resolved_by defaults to 'unknown' when not provided."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir)
        engine = _mock_engine()

        resolved = resolve_decision(path, "rejected", engine)

        fm = _parse_frontmatter(resolved)
        assert fm["resolved_by"] == "unknown"

    def test_frontmatter_resolved_by_custom_value(self, tmp_path: Path) -> None:
        """AC3: resolved_by is set to the provided argument value."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir)
        engine = _mock_engine()

        resolved = resolve_decision(path, "approved", engine, resolved_by="cockpit-api")

        fm = _parse_frontmatter(resolved)
        assert fm["resolved_by"] == "cockpit-api"

    # ------------------------------------------------------------------
    # AC4 — ## Response section appended to body
    # ------------------------------------------------------------------

    def test_response_section_appended_to_body(self, tmp_path: Path) -> None:
        """AC4: ## Response markdown section appended to body containing response value."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir)
        engine = _mock_engine()

        resolved = resolve_decision(path, "approved", engine)

        text = resolved.read_text(encoding="utf-8")
        assert "## Response" in text
        assert "approved" in text

    def test_response_section_contains_response_value(self, tmp_path: Path) -> None:
        """AC4: response value explicitly present inside the ## Response section."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir)
        engine = _mock_engine()

        resolved = resolve_decision(path, "rejected", engine)

        text = resolved.read_text(encoding="utf-8")
        # The section must follow the ## Response header
        response_section = text[text.index("## Response") :]
        assert "rejected" in response_section

    def test_original_dr_body_preserved_before_response_section(self, tmp_path: Path) -> None:
        """AC4: original DR body content is preserved and appears before the ## Response section.

        An implementation that replaced the body with only the Response section
        would satisfy the two weaker AC4 tests above but fail this one.
        """
        pending_dir = _make_pending_dir(tmp_path)
        # _write_dr writes "## Question\nShould we proceed?\n" as the body
        path = _write_dr(pending_dir)
        engine = _mock_engine()

        resolved = resolve_decision(path, "approved", engine)

        text = resolved.read_text(encoding="utf-8")
        response_idx = text.index("## Response")
        content_before_response = text[:response_idx]
        # Original body content must survive in the file and appear before ## Response
        assert "Should we proceed?" in content_before_response

    # ------------------------------------------------------------------
    # AC5 — notes handling
    # ------------------------------------------------------------------

    def test_notes_included_when_provided(self, tmp_path: Path) -> None:
        """AC5: notes text appears in the appended response section when notes is not None."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir)
        engine = _mock_engine()
        note_text = "Approved after second review."

        resolved = resolve_decision(path, "approved", engine, notes=note_text)

        text = resolved.read_text(encoding="utf-8")
        assert note_text in text

    def test_notes_appear_within_response_section(self, tmp_path: Path) -> None:
        """AC5: notes text appears within the ## Response section (between heading and next ## or EOF).

        The weaker test above only proves the note exists somewhere in the file.
        This test proves structural placement: notes must be inside the ## Response block.
        An implementation that wrote notes outside the section would still pass the weaker test.
        """
        import re

        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir)
        engine = _mock_engine()
        note_text = "Approved after second review."

        resolved = resolve_decision(path, "approved", engine, notes=note_text)

        text = resolved.read_text(encoding="utf-8")
        assert "## Response" in text, "## Response section must exist"
        after_response = text.split("## Response", 1)[1]
        next_heading = re.search(r"\n##\s", after_response)
        response_section = after_response[: next_heading.start()] if next_heading else after_response
        assert note_text in response_section

    def test_notes_not_present_when_none(self, tmp_path: Path) -> None:
        """AC5: no spurious notes line when notes=None."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir)
        engine = _mock_engine()

        resolved = resolve_decision(path, "approved", engine, notes=None)

        text = resolved.read_text(encoding="utf-8")
        # The body should have ## Response but no extra notes line
        response_idx = text.index("## Response")
        response_section = text[response_idx:]
        # lines after the header: should only be the response line, no dangling None
        lines_after = [ln for ln in response_section.splitlines() if ln.strip()]
        assert all("None" not in ln for ln in lines_after)

    # ------------------------------------------------------------------
    # AC6 — persist rewritten file to path (before move)
    # ------------------------------------------------------------------

    def test_file_is_persisted_with_updated_frontmatter_and_body(self, tmp_path: Path) -> None:
        """AC6: Both updated frontmatter and appended body section are persisted to disk."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir, task_id=99)
        engine = _mock_engine()

        resolved = resolve_decision(path, "approved", engine)

        # The resolved file must exist and contain both pieces
        text = resolved.read_text(encoding="utf-8")
        assert "response:" in text or "response :" in text  # frontmatter persisted
        assert "## Response" in text  # body section persisted

    # ------------------------------------------------------------------
    # AC7 — engine.edit_task append_body
    # ------------------------------------------------------------------

    def test_appends_canonical_summary_to_task(self, tmp_path: Path) -> None:
        """AC7: engine.edit_task called with append_body=canonical_summary(response, original_body)."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir, task_id=42)
        engine = _mock_engine()

        resolve_decision(path, "approved", engine)

        # At least one call must have append_body keyword
        append_calls = [c for c in engine.edit_task.call_args_list if "append_body" in c.kwargs]
        assert len(append_calls) >= 1

    def test_canonical_summary_content_correct(self, tmp_path: Path) -> None:
        """AC7: the append_body value equals canonical_summary(response, original_body)."""
        pending_dir = _make_pending_dir(tmp_path)
        original_body = "\n## Question\nShould we proceed?\n"
        path = _write_dr(pending_dir, task_id=42)
        engine = _mock_engine()

        resolve_decision(path, "approved", engine)

        expected_summary = canonical_summary("approved", original_body)
        append_calls = [c for c in engine.edit_task.call_args_list if "append_body" in c.kwargs]
        actual_append = append_calls[0].kwargs["append_body"]
        assert actual_append == expected_summary

    def test_edit_task_called_with_correct_task_id(self, tmp_path: Path) -> None:
        """AC7: engine.edit_task is called with the task_id from the DR frontmatter."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir, task_id=77)
        engine = _mock_engine()

        resolve_decision(path, "approved", engine)

        called_ids = [c.args[0] for c in engine.edit_task.call_args_list]
        assert 77 in called_ids

    def test_edit_task_carries_task_id_and_append_body_in_same_call(self, tmp_path: Path) -> None:
        """AC7: a single engine.edit_task call carries both task_id (from frontmatter) and append_body=canonical_summary.

        The weaker tests above prove content and task_id separately.
        This test proves both appear on the same call — a regression that appended the summary
        to the wrong task_id would pass the weaker tests but fail here.
        """
        pending_dir = _make_pending_dir(tmp_path)
        original_body = "\n## Question\nShould we proceed?\n"
        path = _write_dr(pending_dir, task_id=42)
        engine = _mock_engine()

        resolve_decision(path, "approved", engine)

        expected_summary = canonical_summary("approved", original_body)
        matching_calls = [
            c
            for c in engine.edit_task.call_args_list
            if c.args and c.args[0] == 42 and c.kwargs.get("append_body") == expected_summary
        ]
        assert len(matching_calls) == 1

    # ------------------------------------------------------------------
    # AC8 — unblock on approved / rejected
    # ------------------------------------------------------------------

    def test_unblocks_task_when_approved(self, tmp_path: Path) -> None:
        """AC8: engine.edit_task(task_id, blocked=False) called when response='approved'."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir, task_id=42)
        engine = _mock_engine()

        resolve_decision(path, "approved", engine)

        unblock_calls = [c for c in engine.edit_task.call_args_list if c.kwargs.get("blocked") is False]
        assert len(unblock_calls) >= 1
        assert unblock_calls[0].args[0] == 42

    def test_unblocks_task_when_rejected(self, tmp_path: Path) -> None:
        """AC8: engine.edit_task(task_id, blocked=False) called when response='rejected'."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir, task_id=42)
        engine = _mock_engine()

        resolve_decision(path, "rejected", engine)

        unblock_calls = [c for c in engine.edit_task.call_args_list if c.kwargs.get("blocked") is False]
        assert len(unblock_calls) >= 1

    # ------------------------------------------------------------------
    # AC9 — no unblock for needs-info
    # ------------------------------------------------------------------

    def test_no_unblock_for_needs_info(self, tmp_path: Path) -> None:
        """AC9: engine.edit_task(task_id, blocked=False) NOT called when response='needs-info'."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir, task_id=42)
        engine = _mock_engine()

        resolve_decision(path, "needs-info", engine)

        unblock_calls = [c for c in engine.edit_task.call_args_list if c.kwargs.get("blocked") is False]
        assert len(unblock_calls) == 0

    # ------------------------------------------------------------------
    # AC10 — FileNotFoundError swallowed
    # ------------------------------------------------------------------

    def test_filenotfounderror_from_append_body_not_propagated(self, tmp_path: Path) -> None:
        """AC10: FileNotFoundError from engine.edit_task(append_body) is caught internally."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir, task_id=42)
        engine = _mock_engine()
        engine.edit_task.side_effect = FileNotFoundError("task not in engine")

        # Must not raise
        resolve_decision(path, "approved", engine)

    def test_filenotfounderror_from_unblock_not_propagated(self, tmp_path: Path) -> None:
        """AC10: FileNotFoundError from engine.edit_task(blocked=False) is caught internally."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir, task_id=42)
        engine = _mock_engine()

        call_count = 0

        def selective_side_effect(*_args: object, **kwargs: object) -> None:
            nonlocal call_count
            call_count += 1
            if kwargs.get("blocked") is False:
                msg = "task not in engine for unblock"
                raise FileNotFoundError(msg)

        engine.edit_task.side_effect = selective_side_effect

        # Must not raise even when the unblock call fails with FileNotFoundError
        resolve_decision(path, "approved", engine)

    def test_resolution_returns_resolved_path_when_edit_task_raises_fnf(self, tmp_path: Path) -> None:
        """AC10: resolve_decision returns a resolved Path even when engine.edit_task raises FileNotFoundError.

        Non-propagation alone permits early-exit after swallowing the error.
        This test proves the function continues to completion and returns the resolved path.
        """
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir, task_id=42)
        engine = _mock_engine()
        engine.edit_task.side_effect = FileNotFoundError("task not in engine")

        result = resolve_decision(path, "approved", engine)

        expected_resolved_dir = path.parent.parent / "resolved"
        assert isinstance(result, Path)
        assert result.parent == expected_resolved_dir

    def test_pending_file_removed_when_edit_task_raises_fnf(self, tmp_path: Path) -> None:
        """AC10: pending file is removed (moved to resolved) even when engine.edit_task raises FileNotFoundError."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir, task_id=42)
        original_pending_path = path
        engine = _mock_engine()
        engine.edit_task.side_effect = FileNotFoundError("task not in engine")

        resolve_decision(path, "approved", engine)

        assert not original_pending_path.exists()

    # ------------------------------------------------------------------
    # AC11 — returns resolved Path in .../resolved/
    # ------------------------------------------------------------------

    def test_returns_path_object(self, tmp_path: Path) -> None:
        """AC11: resolve_decision returns a Path instance."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir)
        engine = _mock_engine()

        result = resolve_decision(path, "approved", engine)

        assert isinstance(result, Path)

    def test_returns_path_in_resolved_dir(self, tmp_path: Path) -> None:
        """AC11: returned Path is in path.parent.parent / 'resolved' directory."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir)
        engine = _mock_engine()
        expected_resolved_dir = path.parent.parent / "resolved"

        result = resolve_decision(path, "approved", engine)

        assert result.parent == expected_resolved_dir

    def test_resolved_dir_created_when_absent(self, tmp_path: Path) -> None:
        """AC11: resolved/ directory is created if it doesn't already exist."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir)
        engine = _mock_engine()
        resolved_dir = path.parent.parent / "resolved"
        assert not resolved_dir.exists()

        resolve_decision(path, "approved", engine)

        assert resolved_dir.exists()

    def test_original_pending_file_removed(self, tmp_path: Path) -> None:
        """AC11: original pending path is removed after resolution (moved, not copied)."""
        pending_dir = _make_pending_dir(tmp_path)
        path = _write_dr(pending_dir)
        engine = _mock_engine()

        resolve_decision(path, "approved", engine)

        assert not path.exists()
