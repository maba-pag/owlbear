"""Tests for bearclaw decisions CLI subcommands (list/show/resolve).

TDD RED phase: tests define expected behavior of ``bearclaw decisions``
using CliRunner, tmp_path-backed decision directories, and the interactive
resolve flow.

See kanban tasks #778 (tests spec), #777 (implementation) for acceptance criteria.
Research: docs/research/bearclaw-decision-commands.md, docs/research/bearclaw-decision-tests.md
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from bearclaw.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_decision_file(  # noqa: PLR0913
    pending_dir: Path,
    *,
    task_id: str = "123",
    title: str = "Should we adopt library X?",
    urgency: str = "blocking",
    decision_type: str = "feature-gate",
    status: str = "pending",
    agent: str = "researcher",
    created: str = "2026-03-13",
    options: str | None = None,
    filename: str | None = None,
) -> Path:
    """Create a well-formed decision request file in *pending_dir*."""
    pending_dir.mkdir(parents=True, exist_ok=True)
    if options is None:
        options = dedent("""\
            ## Options

            ### A: Adopt library X

            - Effort: ~2 days

            ### B: Build custom

            - Effort: ~5 days
        """)
    content = dedent(f"""\
        ---
        task_id: {task_id}
        agent: {agent}
        created: {created}
        status: {status}
        urgency: {urgency}
        decision_type: {decision_type}
        ---

        # Decision: {title}

        ## Context

        Some context for the decision.

        {options}

        ## Recommendation

        .85 confidence — Option A.
    """)
    fname = filename or f"{task_id}-test-decision.md"
    path = pending_dir / fname
    path.write_text(content, encoding="utf-8")
    return path


def _patch_decisions_dir(tmp_path: Path):
    """Return a context manager patching DECISIONS_DIR to tmp_path/decisions."""
    decisions_dir = tmp_path / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    (decisions_dir / "pending").mkdir(exist_ok=True)
    (decisions_dir / "resolved").mkdir(exist_ok=True)
    return patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestFromAC_DecisionsRegistration:
    """AC: Registered in cli.py via app.add_typer(decisions_app)."""

    def test_decisions_in_main_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "decisions" in result.output

    def test_decisions_help_lists_subcommands(self) -> None:
        result = runner.invoke(app, ["decisions", "--help"])
        assert result.exit_code == 0
        for cmd in ("list", "show", "resolve"):
            assert cmd in result.output


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------


class TestFromAC_DecisionsConstants:
    """AC: Module constants DECISIONS_DIR, PENDING, RESOLVED (relative to cwd)."""

    def test_decisions_dir_is_docs_decisions(self) -> None:
        from bearclaw.commands.decisions import DECISIONS_DIR

        assert Path("docs/decisions") == DECISIONS_DIR

    def test_pending_subdir(self) -> None:
        from bearclaw.commands.decisions import DECISIONS_DIR, PENDING

        assert PENDING == DECISIONS_DIR / "pending"

    def test_resolved_subdir(self) -> None:
        from bearclaw.commands.decisions import DECISIONS_DIR, RESOLVED

        assert RESOLVED == DECISIONS_DIR / "resolved"


# ---------------------------------------------------------------------------
# _parse_decision_file
# ---------------------------------------------------------------------------


class TestFromAC_ParseDecisionFile:
    """AC: _parse_decision_file returns (frontmatter_dict, body_str) or raises ValueError."""

    def test_parse_valid_file(self, tmp_path: Path) -> None:
        from bearclaw.commands.decisions import _parse_decision_file

        pending = tmp_path / "pending"
        path = _make_decision_file(pending, task_id="42", title="Test decision")
        fm, body = _parse_decision_file(path)
        assert isinstance(fm, dict)
        assert fm["task_id"] == 42 or fm["task_id"] == "42"
        assert isinstance(body, str)
        assert "Test decision" in body

    def test_parse_extracts_all_frontmatter_fields(self, tmp_path: Path) -> None:
        from bearclaw.commands.decisions import _parse_decision_file

        pending = tmp_path / "pending"
        path = _make_decision_file(
            pending,
            task_id="99",
            urgency="advisory",
            decision_type="scope-decision",
            agent="architect",
            created="2026-03-01",
        )
        fm, _ = _parse_decision_file(path)
        assert fm["urgency"] == "advisory"
        assert fm["decision_type"] == "scope-decision"
        assert fm["agent"] == "architect"

    def test_parse_raises_on_no_frontmatter(self, tmp_path: Path) -> None:
        from bearclaw.commands.decisions import _parse_decision_file

        path = tmp_path / "bad.md"
        path.write_text("# Just a heading\n\nNo frontmatter here.", encoding="utf-8")
        with pytest.raises(ValueError, match=r"[Ff]rontmatter|[Mm]alformed"):
            _parse_decision_file(path)

    def test_parse_raises_on_incomplete_delimiters(self, tmp_path: Path) -> None:
        from bearclaw.commands.decisions import _parse_decision_file

        path = tmp_path / "half.md"
        path.write_text("---\ntask_id: 1\nNo closing delimiter", encoding="utf-8")
        with pytest.raises(ValueError, match=r"[Ff]rontmatter|[Mm]alformed|delimiter"):
            _parse_decision_file(path)

    def test_parse_raises_on_invalid_yaml(self, tmp_path: Path) -> None:
        from bearclaw.commands.decisions import _parse_decision_file

        path = tmp_path / "invalid.md"
        path.write_text("---\n: [bad yaml\n---\n\nBody text.", encoding="utf-8")
        with pytest.raises(ValueError, match=r"[Ff]rontmatter|[Mm]alformed|[Yy]AML|yaml"):
            _parse_decision_file(path)

    def test_parse_raises_value_error_not_type_error_on_yaml_list(self, tmp_path: Path) -> None:
        """AC: raises ValueError (not TypeError) when frontmatter is a YAML list.

        A YAML list is malformed frontmatter — the AC requires ValueError for all
        malformed-frontmatter cases, not TypeError.
        """
        from bearclaw.commands.decisions import _parse_decision_file

        path = tmp_path / "list_yaml.md"
        path.write_text("---\n- item1\n- item2\n---\n\nBody.", encoding="utf-8")
        with pytest.raises(ValueError, match=r"[Mm]alformed|mapping"):
            _parse_decision_file(path)


# ---------------------------------------------------------------------------
# decisions list
# ---------------------------------------------------------------------------


class TestFromAC_DecisionsList:
    """AC: 'bearclaw decisions list' scans pending/ for *.md, outputs Rich Table."""

    def test_list_no_pending_shows_message(self, tmp_path: Path) -> None:
        with _patch_decisions_dir(tmp_path):
            result = runner.invoke(app, ["decisions", "list"])
        assert result.exit_code == 1
        assert "no pending" in result.output.lower() or "No pending" in result.output

    def test_list_one_decision_shows_table(self, tmp_path: Path) -> None:
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        _make_decision_file(
            pending,
            task_id="100",
            title="Adopt library X",
            urgency="blocking",
            decision_type="feature-gate",
        )
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "list"])
        assert result.exit_code == 0
        assert "100" in result.output
        assert "blocking" in result.output
        assert "feature-gate" in result.output

    def test_list_shows_title_from_h1(self, tmp_path: Path) -> None:
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        _make_decision_file(pending, task_id="200", title="Use Redis for caching")
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "list"])
        assert result.exit_code == 0
        assert "Use Redis for caching" in result.output

    def test_list_multiple_decisions(self, tmp_path: Path) -> None:
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        _make_decision_file(pending, task_id="300", title="Decision A", filename="300-a.md")
        _make_decision_file(pending, task_id="301", title="Decision B", filename="301-b.md")
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "list"])
        assert result.exit_code == 0
        assert "300" in result.output
        assert "301" in result.output

    def test_list_shows_age_column(self, tmp_path: Path) -> None:
        """Table has an Age column showing days since created."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        _make_decision_file(pending, task_id="400", created="2026-03-01")
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "list"])
        assert result.exit_code == 0
        # The table should contain the Age column header and a numeric value
        assert "Age" in result.output or "age" in result.output

    def test_list_skips_malformed_files_gracefully(self, tmp_path: Path) -> None:
        """Malformed files are skipped without crashing the list."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        pending.mkdir(parents=True, exist_ok=True)
        # One valid, one malformed
        _make_decision_file(pending, task_id="500", title="Valid file", filename="500-valid.md")
        (pending / "999-broken.md").write_text("Not valid frontmatter", encoding="utf-8")
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "list"])
        assert result.exit_code == 0
        assert "500" in result.output


# ---------------------------------------------------------------------------
# decisions show
# ---------------------------------------------------------------------------


class TestFromAC_DecisionsShow:
    """AC: 'bearclaw decisions show {task_id}' displays full content via rich.markdown."""

    def test_show_found_displays_content(self, tmp_path: Path) -> None:
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        _make_decision_file(pending, task_id="600", title="Show me this")
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "show", "600"])
        assert result.exit_code == 0
        assert "Show me this" in result.output

    def test_show_not_found_exits_with_error(self, tmp_path: Path) -> None:
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        (decisions_dir / "pending").mkdir(exist_ok=True)
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "show", "999"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "No decision" in result.output

    def test_show_argument_is_string(self, tmp_path: Path) -> None:
        """task_id argument type is str (not int)."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        _make_decision_file(pending, task_id="abc", title="Non-numeric ID")
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "show", "abc"])
        assert result.exit_code == 0
        assert "Non-numeric ID" in result.output

    def test_show_searches_by_frontmatter_task_id(self, tmp_path: Path) -> None:
        """Finds file by scanning frontmatter task_id field, not filename."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        # Filename doesn't match task_id
        _make_decision_file(
            pending, task_id="700", title="Scan by frontmatter", filename="weird-name.md"
        )
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "show", "700"])
        assert result.exit_code == 0
        assert "Scan by frontmatter" in result.output


# ---------------------------------------------------------------------------
# decisions resolve
# ---------------------------------------------------------------------------


class TestFromAC_DecisionsResolve:
    """AC: 'bearclaw decisions resolve {task_id}' interactive flow."""

    def test_resolve_full_flow(self, tmp_path: Path) -> None:
        """Full interactive resolve: choose option → enter notes → confirm → file moves."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        resolved = decisions_dir / "resolved"
        resolved.mkdir(exist_ok=True)
        path = _make_decision_file(pending, task_id="800", title="Resolve this")
        fname = path.name

        # Input: choose "A", notes "Looks good", confirm "y"
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "resolve", "800"], input="A\nLooks good\ny\n")
        assert result.exit_code == 0
        # File moved from pending to resolved
        assert not (pending / fname).exists()
        assert (resolved / fname).exists()

    def test_resolve_writes_resolution_section(self, tmp_path: Path) -> None:
        """Resolved file contains ## Resolution section with choice and notes."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        resolved = decisions_dir / "resolved"
        resolved.mkdir(exist_ok=True)
        path = _make_decision_file(pending, task_id="810", title="Resolution written")
        fname = path.name

        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            runner.invoke(app, ["decisions", "resolve", "810"], input="B\nCustom is better\ny\n")
        resolved_content = (resolved / fname).read_text(encoding="utf-8")
        assert "## Resolution" in resolved_content
        assert "Custom is better" in resolved_content

    def test_resolve_updates_frontmatter_status(self, tmp_path: Path) -> None:
        """Resolved file has status: resolved in frontmatter."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        resolved = decisions_dir / "resolved"
        resolved.mkdir(exist_ok=True)
        path = _make_decision_file(pending, task_id="820")
        fname = path.name

        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            runner.invoke(app, ["decisions", "resolve", "820"], input="A\nnotes\ny\n")
        resolved_content = (resolved / fname).read_text(encoding="utf-8")
        assert "status: resolved" in resolved_content

    def test_resolve_not_found_exits_with_error(self, tmp_path: Path) -> None:
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        (decisions_dir / "pending").mkdir(exist_ok=True)
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "resolve", "999"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "No decision" in result.output

    def test_resolve_cancel_does_not_move_file(self, tmp_path: Path) -> None:
        """Answering 'n' to confirm leaves the file in pending."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        resolved = decisions_dir / "resolved"
        resolved.mkdir(exist_ok=True)
        path = _make_decision_file(pending, task_id="830")
        fname = path.name

        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            runner.invoke(app, ["decisions", "resolve", "830"], input="A\nnotes\nn\n")
        # File should still be in pending
        assert (pending / fname).exists()
        assert not (resolved / fname).exists()

    def test_resolve_extracts_options_from_headings(self, tmp_path: Path) -> None:
        """Options are extracted from ### A: ..., ### B: ... headings."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        resolved = decisions_dir / "resolved"
        resolved.mkdir(exist_ok=True)
        options_text = dedent("""\
            ## Options

            ### A: Use Redis

            - Fast, well-known

            ### B: Use Memcached

            - Simple, lightweight

            ### C: Use SQLite

            - Already have it
        """)
        _make_decision_file(
            pending,
            task_id="840",
            options=options_text,
        )
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(
                app, ["decisions", "resolve", "840"], input="C\nSQLite wins\ny\n"
            )
        assert result.exit_code == 0

    def test_resolve_missing_options_falls_back_to_freetext(self, tmp_path: Path) -> None:
        """AC: When ## Options section not found, fall back to free-text input."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        resolved = decisions_dir / "resolved"
        resolved.mkdir(exist_ok=True)
        # Create file with no ## Options section
        _make_decision_file(pending, task_id="850", options="")
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(
                app, ["decisions", "resolve", "850"], input="Go with plan Z\nExtra notes\ny\n"
            )
        assert result.exit_code == 0
        assert not (pending / "850-test-decision.md").exists()
        assert (resolved / "850-test-decision.md").exists()


# ---------------------------------------------------------------------------
# Graceful error messages
# ---------------------------------------------------------------------------


class TestFromAC_DecisionsErrors:
    """AC: Graceful error messages via typer.echo + typer.Exit(code=1)."""

    def test_list_missing_pending_dir_shows_error(self, tmp_path: Path) -> None:
        """If pending/ doesn't exist, exits with code 1 and graceful message (no traceback)."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        # Don't create pending/
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "list"])
        assert result.exit_code == 1
        # Should NOT have a Python traceback
        assert "Traceback" not in result.output

    def test_list_empty_pending_exits_with_code_1(self, tmp_path: Path) -> None:
        """AC: typer.Exit(code=1) is required when pending/ exists but has no decisions.

        The AC mandates typer.Exit(code=1) for the 'no pending decisions' error
        path. Returning normally (exit code 0) violates the contract.
        """
        with _patch_decisions_dir(tmp_path):
            result = runner.invoke(app, ["decisions", "list"])
        assert result.exit_code == 1
        assert "no pending" in result.output.lower()

    def test_show_malformed_file_shows_error(self, tmp_path: Path) -> None:
        """Malformed frontmatter shows graceful error, not traceback."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        pending.mkdir(exist_ok=True)
        (pending / "bad-file.md").write_text("No frontmatter\nJust text.", encoding="utf-8")
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "show", "bad"])
        # Either not found or malformed — either way graceful
        assert result.exit_code == 1
        assert "Traceback" not in result.output

    def test_resolve_creates_resolved_dir_if_missing(self, tmp_path: Path) -> None:
        """resolved/ is created if it doesn't exist during resolve."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        _make_decision_file(pending, task_id="860")
        # Don't create resolved/ dir — should be auto-created
        with patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir):
            result = runner.invoke(app, ["decisions", "resolve", "860"], input="A\nnotes\ny\n")
        assert result.exit_code == 0
        assert (decisions_dir / "resolved" / "860-test-decision.md").exists()


# ---------------------------------------------------------------------------
# _extract_options helper
# ---------------------------------------------------------------------------


class TestFromAC_ExtractOptions:
    """AC: decisions resolve extracts options from ## Options subsection headings only."""

    def test_extract_options_does_not_include_headings_after_next_h2(self) -> None:
        """Headings in sections after ## Options are not extracted as options.

        _extract_options must stop at the next ## heading. Options that appear
        under a different H2 section (e.g. ## Recommendation) are not options.
        """
        from bearclaw.commands.decisions import _extract_options

        body = (
            "## Options\n\n"
            "### A: First option\n\n"
            "## Other Section\n\n"
            "### B: Should not be extracted\n"
        )
        options = _extract_options(body)
        assert options == ["A: First option"]


# ---------------------------------------------------------------------------
# Resolve atomicity (reviewer data-safety finding)
# ---------------------------------------------------------------------------


class TestFromAC_DecisionsResolveAtomicity:
    """AC: Graceful errors — pending file must not be mutated if the resolve move fails."""

    def test_resolve_pending_file_unchanged_if_move_fails(self, tmp_path: Path) -> None:
        """Pending file frontmatter must not be mutated when shutil.move raises.

        The resolve command writes status: resolved and ## Resolution to the pending
        file *before* moving it. If the move fails, the pending file is left in a
        corrupted state. The contract requires the pending file to remain unmodified.
        """
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        resolved = decisions_dir / "resolved"
        resolved.mkdir(exist_ok=True)
        path = _make_decision_file(pending, task_id="870")
        fname = path.name

        with (
            patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir),
            patch("bearclaw.commands.decisions.shutil.move", side_effect=OSError("disk full")),
        ):
            runner.invoke(app, ["decisions", "resolve", "870"], input="A\nnotes\ny\n")

        assert (pending / fname).exists(), "pending file should still exist after failed move"
        pending_content = (pending / fname).read_text(encoding="utf-8")
        assert "status: pending" in pending_content, (
            "pending file frontmatter must not be mutated to 'resolved' when move fails"
        )

    def test_resolve_pending_file_has_no_resolution_section_if_move_fails(
        self, tmp_path: Path
    ) -> None:
        """Pending file must not contain ## Resolution section after a failed move."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        resolved = decisions_dir / "resolved"
        resolved.mkdir(exist_ok=True)
        path = _make_decision_file(pending, task_id="871")
        fname = path.name

        with (
            patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir),
            patch("bearclaw.commands.decisions.shutil.move", side_effect=OSError("io error")),
        ):
            runner.invoke(app, ["decisions", "resolve", "871"], input="A\nnotes\ny\n")

        assert (pending / fname).exists()
        pending_content = (pending / fname).read_text(encoding="utf-8")
        assert "## Resolution" not in pending_content, (
            "pending file must not contain ## Resolution section when move fails"
        )

    def test_resolve_consistent_state_after_post_move_write_failure(
        self, tmp_path: Path
    ) -> None:
        """After shutil.move succeeds but write_text raises, resolved file must have
        correct content or not exist at all.

        Current failure mode: resolved file is stranded with original pending content
        (status: pending, no ## Resolution) after the post-move write_text raises.
        That is an inconsistent partial state — a pending-content file living at the
        resolved/ path — a data-safety violation with no rollback.

        The contract requires that on write failure after the move, one of:
        - The resolved file contains correct content (status: resolved + ## Resolution), OR
        - The resolved file does not exist (clean rollback / atomic write-then-rename).
        """
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        pending = decisions_dir / "pending"
        resolved_dir = decisions_dir / "resolved"
        resolved_dir.mkdir(exist_ok=True)
        path = _make_decision_file(pending, task_id="880")
        fname = path.name

        _original_write_text = Path.write_text

        def _fail_resolved_write(self: Path, *args: object, **kwargs: object) -> None:
            if "resolved" in str(self.parent):
                msg = "simulated disk full after move"
                raise OSError(msg)
            _original_write_text(self, *args, **kwargs)  # type: ignore[arg-type]

        with (
            patch("bearclaw.commands.decisions.DECISIONS_DIR", decisions_dir),
            patch.object(Path, "write_text", _fail_resolved_write),
        ):
            runner.invoke(app, ["decisions", "resolve", "880"], input="A\nnotes\ny\n")

        resolved_file = resolved_dir / fname
        if resolved_file.exists():
            content = resolved_file.read_text(encoding="utf-8")
            assert "status: resolved" in content, (
                "resolved file must not be left with pending content after post-move write failure"
            )
            assert "## Resolution" in content, (
                "resolved file must contain ## Resolution section after post-move write failure"
            )
