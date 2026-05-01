"""Failing tests for #1195: resolve_pending_drs collision protection in resolved/.

AC coverage:
  ac1-happy    — move to resolved/ succeeds without overwrite when basename conflicts
  ac1-edge     — moved path is distinct from pre-existing resolved file
  ac1-boundary — collision-protected path appears in returned list
  ac2          — original resolved file content preserved byte-for-byte after collision
  ac3-happy    — first conflict yields -2.md suffix
  ac3-edge     — two pre-existing conflicts yield -3.md (next-free allocation)
  ac3-boundary — three pre-existing conflicts yield -4.md
  ac4          — collision detection does not overwrite (O_EXCL or equivalent)
  ac5-approved — approved resolution path applies collision protection
  ac5-rejected — rejected resolution path applies collision protection
  ac5-needs-info — needs-info resolution path applies collision protection

All tests FAIL (RED phase) — resolve_pending_drs currently uses path.replace() which
silently overwrites pre-existing resolved/ files; collision protection not yet implemented.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.decisions import resolve_pending_drs

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SENTINEL = "ORIGINAL CONTENT MUST NOT CHANGE"


def _make_dirs(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Return (decisions_dir, pending_dir, resolved_dir) with directories created."""
    decisions_dir = tmp_path / "decisions"
    pending_dir = decisions_dir / "pending"
    resolved_dir = decisions_dir / "resolved"
    pending_dir.mkdir(parents=True)
    resolved_dir.mkdir(parents=True)
    return decisions_dir, pending_dir, resolved_dir


def _write_dr(
    pending_dir: Path, filename: str, response: str, task_id: int = 42
) -> Path:
    """Write a minimal DR file into pending_dir with the given response."""
    content = (
        "---\n"
        f"task_id: {task_id}\n"
        "agent: builder\n"
        "request_type: approach-selection\n"
        "created: '2026-04-30'\n"
        f"response: {response}\n"
        "---\n\n## Body\nTest.\n"
    )
    path = pending_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def _write_resolved(
    resolved_dir: Path, filename: str, content: str = _SENTINEL
) -> Path:
    """Write a pre-existing file in resolved/ to simulate a collision."""
    path = resolved_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def _mock_engine() -> MagicMock:
    return MagicMock(spec=KanbanEngine)


# ---------------------------------------------------------------------------
# AC1 (td:2): Move to resolved/ succeeds without overwrite when basename conflicts
# ---------------------------------------------------------------------------


class TestFromAC_ResolvePendingDrsCollision:
    """Collision-protection tests for resolve_pending_drs(), AC1-AC5."""

    # AC1 — happy path: approved DR with a basename conflict in resolved/
    def test_ac1_happy_approved_move_succeeds_without_overwrite(
        self, tmp_path: Path
    ) -> None:
        """AC1 happy: approved DR moves even when resolved/ already has a file with the same name."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "42-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved")
        # Pre-existing conflict in resolved/
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        # The DR must be resolved (something must have been moved)
        assert len(result) == 1, f"Expected 1 moved file, got {len(result)}: {result}"
        # The pre-existing resolved file must NOT have been overwritten
        existing_content = (resolved_dir / filename).read_text(encoding="utf-8")
        assert existing_content == _SENTINEL, (
            "Pre-existing resolved file must be preserved byte-for-byte; "
            f"got: {existing_content!r}"
        )

    # AC1 — edge: the moved path is distinct from the pre-existing resolved file
    def test_ac1_edge_moved_path_is_distinct_when_conflict_exists(
        self, tmp_path: Path
    ) -> None:
        """AC1 edge: the path returned for the moved file differs from the original basename."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "99-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=99)
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        assert len(result) == 1
        moved_path = result[0]
        # The moved path must NOT be the exact same name as the pre-existing file
        assert moved_path.name != filename, (
            f"Collision must produce a distinct filename; got {moved_path.name!r}"
        )

    # AC1 — boundary: the collision-protected path appears in the returned list
    def test_ac1_boundary_collision_protected_path_in_returned_list(
        self, tmp_path: Path
    ) -> None:
        """AC1 boundary: resolve_pending_drs returns the new (suffixed) path, not the original."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "55-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=55)
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        assert result, "Result list must not be empty when a DR is resolved"
        moved_path = result[0]
        assert moved_path.exists(), f"Returned path must exist on disk: {moved_path}"
        assert moved_path.parent == resolved_dir, "Moved path must be inside resolved/"
        assert moved_path.name != filename, (
            "Collision-protected path must differ from pre-existing filename; "
            f"got {moved_path.name!r} which matches the conflict"
        )

    # ---------------------------------------------------------------------------
    # AC2 (td:1): Original resolved file content preserved byte-for-byte
    # ---------------------------------------------------------------------------

    def test_ac2_original_resolved_content_preserved_byte_for_byte(
        self, tmp_path: Path
    ) -> None:
        """AC2: The pre-existing resolved file retains its exact bytes after a collision."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "10-approach-selection.md"
        original_bytes = (
            b"PRECIOUS ORIGINAL CONTENT\xc3\xa9"  # non-ASCII to catch encoding bugs
        )
        (resolved_dir / filename).write_bytes(original_bytes)
        _write_dr(pending_dir, filename, response="approved", task_id=10)

        resolve_pending_drs(decisions_dir, engine)

        actual_bytes = (resolved_dir / filename).read_bytes()
        assert actual_bytes == original_bytes, (
            "Pre-existing resolved file must be preserved byte-for-byte after collision move; "
            f"expected {original_bytes!r}, got {actual_bytes!r}"
        )

    # ---------------------------------------------------------------------------
    # AC3 (td:2): Counter suffix; next-free allocation
    # ---------------------------------------------------------------------------

    def test_ac3_happy_first_collision_uses_dash_2_suffix(self, tmp_path: Path) -> None:
        """AC3 happy: when resolved/ already has the base name, the moved file gets -2.md."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "7-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=7)
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        assert len(result) == 1
        moved = result[0]
        assert moved.name == "7-approach-selection-2.md", (
            f"First collision must produce '-2.md' suffix; got {moved.name!r}"
        )

    def test_ac3_edge_two_preexisting_conflicts_yield_dash_3_suffix(
        self, tmp_path: Path
    ) -> None:
        """AC3 edge: when resolved/ has both base and -2 variant, next-free is -3.md."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "20-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=20)
        _write_resolved(resolved_dir, "20-approach-selection.md")
        _write_resolved(resolved_dir, "20-approach-selection-2.md")

        result = resolve_pending_drs(decisions_dir, engine)

        assert len(result) == 1
        moved = result[0]
        assert moved.name == "20-approach-selection-3.md", (
            f"With base and -2 taken, next free must be '-3.md'; got {moved.name!r}"
        )

    def test_ac3_boundary_three_preexisting_conflicts_yield_dash_4_suffix(
        self, tmp_path: Path
    ) -> None:
        """AC3 boundary: three pre-existing variants → next-free counter lands at -4.md."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "33-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=33)
        _write_resolved(resolved_dir, "33-approach-selection.md")
        _write_resolved(resolved_dir, "33-approach-selection-2.md")
        _write_resolved(resolved_dir, "33-approach-selection-3.md")

        result = resolve_pending_drs(decisions_dir, engine)

        assert len(result) == 1
        moved = result[0]
        assert moved.name == "33-approach-selection-4.md", (
            f"Three pre-existing variants → next free must be '-4.md'; got {moved.name!r}"
        )

    # ---------------------------------------------------------------------------
    # AC4 (td:1): Non-overwriting mechanism (O_EXCL or equivalent)
    # ---------------------------------------------------------------------------

    def test_ac4_mechanism_does_not_overwrite_resolved_file(
        self, tmp_path: Path
    ) -> None:
        """AC4: The collision mechanism must not overwrite the pre-existing resolved file."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "77-approach-selection.md"
        existing_content = "DO NOT TOUCH ME"
        _write_resolved(resolved_dir, filename, content=existing_content)
        _write_dr(pending_dir, filename, response="needs-info", task_id=77)

        resolve_pending_drs(decisions_dir, engine)

        # The original file must be untouched
        after_content = (resolved_dir / filename).read_text(encoding="utf-8")
        assert after_content == existing_content, (
            f"Non-overwriting mechanism must preserve the existing resolved file; "
            f"expected {existing_content!r}, got {after_content!r}"
        )
        # And a suffixed copy must now exist
        suffixed = resolved_dir / "77-approach-selection-2.md"
        assert suffixed.exists(), (
            "A collision-suffixed file must have been created in resolved/"
        )

    # ---------------------------------------------------------------------------
    # AC5 (td:1): Both resolution paths apply collision protection
    # ---------------------------------------------------------------------------

    def test_ac5_approved_path_applies_collision_protection(
        self, tmp_path: Path
    ) -> None:
        """AC5 approved: the approved branch applies the same collision-protection logic."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "100-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=100)
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        assert result, "Approved DR must be moved to resolved/"
        moved = result[0]
        assert moved.name != filename, (
            "Approved branch must not overwrite pre-existing resolved file"
        )
        # Verify original untouched
        assert (resolved_dir / filename).read_text(encoding="utf-8") == _SENTINEL

    def test_ac5_rejected_path_applies_collision_protection(
        self, tmp_path: Path
    ) -> None:
        """AC5 rejected: the rejected branch applies the same collision-protection logic."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "200-approach-selection.md"
        _write_dr(pending_dir, filename, response="rejected", task_id=200)
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        assert result, "Rejected DR must be moved to resolved/"
        moved = result[0]
        assert moved.name != filename, (
            "Rejected branch must not overwrite pre-existing resolved file"
        )
        assert (resolved_dir / filename).read_text(encoding="utf-8") == _SENTINEL

    def test_ac5_needs_info_path_applies_collision_protection(
        self, tmp_path: Path
    ) -> None:
        """AC5 needs-info: the needs-info branch applies the same collision-protection logic."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "300-approach-selection.md"
        _write_dr(pending_dir, filename, response="needs-info", task_id=300)
        _write_resolved(resolved_dir, filename)

        result = resolve_pending_drs(decisions_dir, engine)

        assert result, "Needs-info DR must be moved to resolved/"
        moved = result[0]
        assert moved.name != filename, (
            "Needs-info branch must not overwrite pre-existing resolved file"
        )
        assert (resolved_dir / filename).read_text(encoding="utf-8") == _SENTINEL

    # ---------------------------------------------------------------------------
    # Retry gaps: collision-path source-removal and mechanism proof (reviewer Required Follow-up)
    # ---------------------------------------------------------------------------

    def test_ac1_collision_case_pending_source_file_removed_after_move(
        self, tmp_path: Path
    ) -> None:
        """AC1 retry gap: pending source file must be deleted after a collision-protected move."""
        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "11-approach-selection.md"
        pending_file = _write_dr(pending_dir, filename, response="approved", task_id=11)
        _write_resolved(resolved_dir, filename)  # force collision path

        resolve_pending_drs(decisions_dir, engine)

        assert not pending_file.exists(), (
            "Pending source file must be removed from pending/ after collision-protected move; "
            f"{pending_file} still exists"
        )

    def test_ac4_collision_helper_uses_o_excl_exclusive_create_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC4 mechanism retry gap: collision helper uses O_CREAT|O_EXCL, not exists-then-write."""
        import os as os_mod

        real_open = os_mod.open
        observed_flags: list[int] = []

        def spy_open(path: object, flags: int, mode: int = 0o777) -> int:
            observed_flags.append(flags)
            return real_open(path, flags, mode)  # type: ignore[arg-type]

        monkeypatch.setattr("owlbear_kanban.decisions.os.open", spy_open)

        decisions_dir, pending_dir, resolved_dir = _make_dirs(tmp_path)
        engine = _mock_engine()

        filename = "22-approach-selection.md"
        _write_dr(pending_dir, filename, response="approved", task_id=22)
        _write_resolved(resolved_dir, filename)  # force collision so helper is invoked

        resolve_pending_drs(decisions_dir, engine)

        assert observed_flags, (
            "os.open must be called by the collision helper during resolution"
        )
        o_creat = os_mod.O_CREAT
        o_excl = os_mod.O_EXCL
        matching = [f for f in observed_flags if (f & o_creat) and (f & o_excl)]
        assert matching, (
            "Collision helper must use O_CREAT|O_EXCL for atomic exclusive-create; "
            "no matching os.open call found"
        )
