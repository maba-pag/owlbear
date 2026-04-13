"""RED phase tests for task #827: Migrate task_io.py from PyYAML to ruamel.yaml.

AC coverage:
  AC1 - task_io.py uses ruamel.yaml instead of pyyaml
  AC2 - _NoTimestampLoader replaced; timestamp strings preserved as-is
  AC3 - pyyaml removed from serve/kanban/pyproject.toml deps
  AC4 - All task I/O tests pass (round-trip fidelity, timestamp preservation, encoding)
        → existing test_kanban_task_io.py covers behavioral contract
  AC5 - YAML output format unchanged (null literals, string quoting, list style)
"""

from __future__ import annotations

import inspect
from pathlib import Path

from owlbear_kanban import task_io
from owlbear_kanban.models import Task
from owlbear_kanban.task_io import write_task


# ===========================================================================
# TestFromAC_LibraryMigration (AC1, AC2, AC3)
# ===========================================================================


class TestFromAC_LibraryMigration:
    """AC1-AC3: task_io.py uses ruamel.yaml; _NoTimestampLoader removed; pyyaml gone."""

    # --- AC1: ruamel.yaml imported; pyyaml absent ---

    def test_task_io_does_not_import_pyyaml(self) -> None:
        """task_io.py must not contain 'import yaml' (the pyyaml package)."""
        source = inspect.getsource(task_io)
        # "import yaml" at module level means PyYAML — must be gone after migration
        assert "import yaml" not in source

    def test_task_io_imports_from_ruamel_yaml(self) -> None:
        """task_io.py must import YAML or related symbols from ruamel.yaml."""
        source = inspect.getsource(task_io)
        assert "ruamel" in source

    # --- AC2: _NoTimestampLoader replaced by ruamel equivalent ---

    def test_no_timestamp_loader_class_absent_from_module(self) -> None:
        """_NoTimestampLoader class must not exist in task_io namespace post-migration."""
        assert not hasattr(task_io, "_NoTimestampLoader")

    def test_no_timestamp_loader_not_in_source(self) -> None:
        """_NoTimestampLoader string must not appear anywhere in task_io source."""
        source = inspect.getsource(task_io)
        assert "_NoTimestampLoader" not in source

    def test_no_safeloader_reference_in_source(self) -> None:
        """yaml.SafeLoader (pyyaml class) must not appear in task_io source."""
        source = inspect.getsource(task_io)
        # SafeLoader is the pyyaml inheritance hook used by _NoTimestampLoader
        assert "SafeLoader" not in source

    # --- AC3: pyyaml removed from kanban pyproject.toml ---

    def test_pyyaml_removed_from_kanban_pyproject_deps(self) -> None:
        """pyyaml must not appear in serve/kanban/pyproject.toml dependencies."""
        pyproject_path = Path(__file__).parent.parent / "serve" / "kanban" / "pyproject.toml"
        content = pyproject_path.read_text(encoding="utf-8")
        assert "pyyaml" not in content.lower()


# ===========================================================================
# TestFromAC_OutputFormatUnchanged (AC5)
# ===========================================================================


class TestFromAC_OutputFormatUnchanged:
    """AC5: YAML output format unchanged — null literals, timestamps, list block style."""

    def test_timestamps_written_unquoted_in_frontmatter(self, tmp_path: Path) -> None:
        """write_task must write timestamp strings unquoted (no surrounding quotes)."""
        ts = "2026-04-09T03:24:26.6974428+02:00"
        record = Task(
            id=2,
            title="Timestamp quote test",
            status="todo",
            priority="important",
            created=ts,
            updated=ts,
        )
        out = tmp_path / "2-timestamp-quote-test.md"
        write_task(out, record)
        content = out.read_text(encoding="utf-8")
        # Must appear verbatim without quotes ('...' or "...")
        assert f"created: {ts}" in content
        assert f"updated: {ts}" in content


# ===========================================================================
# TestFromAC_HelperFunctions (AC2 — _make_yaml; AC3 — _to_plain)
# ===========================================================================


class TestFromAC_HelperFunctions:
    """AC2: _make_yaml() helper exists; AC3: _to_plain() helper exists."""

    def test_make_yaml_helper_exists_in_module(self) -> None:
        """_make_yaml() function must be present in task_io namespace after migration."""
        assert hasattr(task_io, "_make_yaml"), (
            "_make_yaml() not found — AC2 requires replacing _NoTimestampLoader with _make_yaml()"
        )

    def test_to_plain_helper_exists_in_module(self) -> None:
        """_to_plain() function must be present in task_io namespace after migration."""
        assert hasattr(task_io, "_to_plain"), (
            "_to_plain() not found — AC requires adding _to_plain() for CommentedMap → dict conversion"
        )
