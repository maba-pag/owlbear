"""Tests for task #940: Switch read_task() to YAML12SafeLoader (PyYAML).

AC coverage:
  1.  YAML12SafeLoader importable from owlbear_kanban.storage
  2.  YAML12SafeLoader is yaml.SafeLoader subclass
  3.  YAML12SafeLoader defined at module level (class attr on task_io, not a function)
  4.  yaml_implicit_resolvers deep-copied before mutation — global SafeLoader not corrupted
  5.  timestamp resolver (tag:yaml.org,2002:timestamp) stripped from YAML12SafeLoader
  6.  YAML 1.1 bool aliases (yes/no/on/off) stripped — parse as strings under YAML12SafeLoader
  7.  YAML 1.2 bool resolver re-added — true/False/TRUE/FALSE all parse as Python bool
  8.  read_task() calls yaml.load() with Loader=YAML12SafeLoader (pyyaml, not ruamel)
  9.  _to_plain() removed from task_io (dead code after read path switch to PyYAML)
  10. pyyaml>=6.0.3 declared in serve/kanban/pyproject.toml [project.dependencies]
  11. Regression: 7-digit (Go-style) timestamps preserved as strings through read_task()
  12. Regression: 6-digit (Python-style) timestamps preserved as strings through read_task()
  13. Regression: YAML 1.1 words (yes/no/on/off) in string fields not coerced when reading file
  14. Integration: write_task() → read_task() → Task.model_validate() round-trip (bool, str|None,
      tags, timestamps, extra fields)

All tests FAIL in RED phase — YAML12SafeLoader not yet defined in task_io.py.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_CONFIG_YAML = """\
statuses:
- research
- backlog
- todo
- in-progress
- review
- docs
- done
priorities:
- someday
- nice-to-have
- important
- needed
- critical
claim_timeout: 1h
next_id: 100
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
    research: researcher
    backlog: architect
    todo: builder
    in-progress: reviewer
    review: reviewer
    docs: doc-writer
    done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: []
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
tasks_dir: tasks
archive_dir: archive
activity_log: false
"""


def _make_kanban_dir(base_dir: Path) -> Path:
    """Create a minimal board layout expected by write_task()."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# TestFromAC_YAML12SafeLoader — class definition & parsing contract
# ---------------------------------------------------------------------------


class TestFromAC_YAML12SafeLoader:
    """Verifies YAML12SafeLoader class definition, subclassing, and parsing behavior."""

    # -- AC 1: importable -----------------------------------------------------

    def test_class_is_importable_from_task_io(self) -> None:
        """YAML12SafeLoader must be importable from owlbear_kanban.storage."""
        from owlbear_kanban.storage import YAML12SafeLoader

        assert YAML12SafeLoader is not None

    # -- AC 2: subclass -------------------------------------------------------

    def test_class_is_yaml_safeloader_subclass(self) -> None:
        """YAML12SafeLoader must subclass yaml.SafeLoader."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader

        assert issubclass(YAML12SafeLoader, yaml.SafeLoader)

    # -- AC 3: module-level class ---------------------------------------------

    def test_class_defined_at_module_level(self) -> None:
        """YAML12SafeLoader must be a class attribute of the task_io module (not a closure)."""
        import inspect

        import owlbear_kanban.storage as _task_io
        from owlbear_kanban.storage import YAML12SafeLoader

        assert YAML12SafeLoader is _task_io.YAML12SafeLoader
        assert inspect.isclass(YAML12SafeLoader)

    # -- AC 4: deep copy — global SafeLoader not corrupted --------------------

    def test_resolvers_deep_copied_global_safeloader_not_mutated(self) -> None:
        """Defining YAML12SafeLoader must not strip resolvers from yaml.SafeLoader globally."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader  # noqa: F401 — triggers class definition

        all_tags_in_safeloader = {
            tag
            for resolvers in yaml.SafeLoader.yaml_implicit_resolvers.values()
            for tag, _ in resolvers
        }
        assert "tag:yaml.org,2002:timestamp" in all_tags_in_safeloader, (
            "yaml.SafeLoader.yaml_implicit_resolvers must not be mutated globally; "
            "YAML12SafeLoader must deep-copy resolvers before stripping tags"
        )

    # -- AC 5: timestamp resolver stripped ------------------------------------

    def test_timestamp_7digit_fractional_preserved_as_string(self) -> None:
        """7-digit (Go nanosecond) timestamps must be returned as str, not datetime."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader

        ts = "2026-04-09T03:24:26.6974428+02:00"
        result = yaml.load(f"created: {ts}", Loader=YAML12SafeLoader)

        assert isinstance(result["created"], str), (
            f"7-digit timestamp must parse as str, got {type(result['created']).__name__}"
        )
        assert result["created"] == ts

    def test_timestamp_6digit_fractional_preserved_as_string(self) -> None:
        """6-digit (Python microsecond) timestamps must be returned as str, not datetime."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader

        ts = "2026-04-17T20:16:32.171661+00:00"
        result = yaml.load(f"updated: {ts}", Loader=YAML12SafeLoader)

        assert isinstance(result["updated"], str), (
            f"6-digit timestamp must parse as str, got {type(result['updated']).__name__}"
        )
        assert result["updated"] == ts

    # -- AC 6: YAML 1.1 bool aliases → strings --------------------------------

    def test_yaml11_yes_parses_as_string(self) -> None:
        """Unquoted 'yes' must parse as str 'yes', not bool True (YAML 1.2 semantics)."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader

        result = yaml.load("value: yes", Loader=YAML12SafeLoader)

        assert not isinstance(result["value"], bool), "yes must not be coerced to bool"
        assert result["value"] == "yes"

    def test_yaml11_no_parses_as_string(self) -> None:
        """Unquoted 'no' must parse as str 'no', not bool False (YAML 1.2 semantics)."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader

        result = yaml.load("value: no", Loader=YAML12SafeLoader)

        assert not isinstance(result["value"], bool), "no must not be coerced to bool"
        assert result["value"] == "no"

    def test_yaml11_on_parses_as_string(self) -> None:
        """Unquoted 'on' must parse as str 'on', not bool True (YAML 1.2 semantics)."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader

        result = yaml.load("value: on", Loader=YAML12SafeLoader)

        assert not isinstance(result["value"], bool), "on must not be coerced to bool"
        assert result["value"] == "on"

    def test_yaml11_off_parses_as_string(self) -> None:
        """Unquoted 'off' must parse as str 'off', not bool False (YAML 1.2 semantics)."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader

        result = yaml.load("value: off", Loader=YAML12SafeLoader)

        assert not isinstance(result["value"], bool), "off must not be coerced to bool"
        assert result["value"] == "off"

    # -- AC 7: YAML 1.2 bool resolver re-added --------------------------------

    def test_yaml12_lowercase_true_parses_as_bool(self) -> None:
        """YAML 1.2 'true' must parse as Python bool True."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader

        result = yaml.load("blocked: true", Loader=YAML12SafeLoader)

        assert result["blocked"] is True

    def test_yaml12_lowercase_false_parses_as_bool(self) -> None:
        """YAML 1.2 'false' must parse as Python bool False."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader

        result = yaml.load("blocked: false", Loader=YAML12SafeLoader)

        assert result["blocked"] is False

    def test_yaml12_title_case_true_parses_as_bool(self) -> None:
        """YAML 1.2 'True' (title-case) must parse as Python bool True."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader

        result = yaml.load("blocked: True", Loader=YAML12SafeLoader)

        assert result["blocked"] is True

    def test_yaml12_all_caps_false_parses_as_bool(self) -> None:
        """YAML 1.2 'FALSE' (all-caps) must parse as Python bool False."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader

        result = yaml.load("blocked: FALSE", Loader=YAML12SafeLoader)

        assert result["blocked"] is False

    # -- Boundary: null preserved ---------------------------------------------

    def test_null_value_preserved_as_none(self) -> None:
        """null YAML values must parse as Python None (null resolver must not be stripped)."""
        import yaml

        from owlbear_kanban.storage import YAML12SafeLoader

        result = yaml.load("parent: null\nblock_reason: null", Loader=YAML12SafeLoader)

        assert result["parent"] is None
        assert result["block_reason"] is None


# ---------------------------------------------------------------------------
# TestFromAC_ReadTaskPyYAML — read_task() uses PyYAML YAML12SafeLoader
# ---------------------------------------------------------------------------


class TestFromAC_ReadTaskPyYAML:
    """Verifies read_task() uses yaml.load + YAML12SafeLoader and _to_plain is removed."""

    # -- AC 8a: task_io imports yaml module -----------------------------------

    def test_pyyaml_imported_at_module_level_in_task_io(self) -> None:
        """task_io must expose a 'yaml' attribute — pyyaml imported at module level."""
        import owlbear_kanban.storage as _task_io

        assert hasattr(_task_io, "yaml"), (
            "task_io must import yaml (pyyaml) at module level so read_task() can use it"
        )

    # -- AC 8b: read_task calls yaml.load with YAML12SafeLoader ---------------

    def test_read_task_calls_yaml_load_with_yaml12_loader(self, tmp_path: Path) -> None:
        """read_task() must call yaml.load(fm, Loader=YAML12SafeLoader), not ruamel's load."""
        from unittest.mock import patch

        from owlbear_kanban.storage import YAML12SafeLoader, read_task

        content = (
            "---\n"
            "id: 1\ntitle: Test Task\nstatus: todo\npriority: needed\n"
            "created: 2026-04-09T03:24:26.6974428+02:00\n"
            "updated: 2026-04-17T20:16:32.171661+00:00\n"
            "blocked: false\ntags: []\ndepends_on: []\nparent: null\n"
            "block_reason: null\nclaimed_by: null\nclaimed_at: null\n"
            "---\n## Body\n"
        )
        task_file = tmp_path / "1-test-task.md"
        task_file.write_text(content, encoding="utf-8")

        with patch("owlbear_kanban.storage.yaml") as mock_yaml:
            mock_yaml.load.return_value = {
                "id": 1,
                "title": "Test Task",
                "status": "todo",
                "priority": "needed",
                "created": "2026-04-09T03:24:26.6974428+02:00",
                "updated": "2026-04-17T20:16:32.171661+00:00",
                "blocked": False,
                "tags": [],
                "depends_on": [],
                "parent": None,
                "block_reason": None,
                "claimed_by": None,
                "claimed_at": None,
            }
            read_task(task_file)

        assert mock_yaml.load.called, "yaml.load must be called in read_task()"
        call_args = mock_yaml.load.call_args
        loader_arg = call_args.kwargs.get("Loader") or (
            call_args.args[1] if len(call_args.args) > 1 else None
        )
        assert loader_arg is YAML12SafeLoader, (
            f"yaml.load must be called with Loader=YAML12SafeLoader, got Loader={loader_arg!r}"
        )

    # -- AC 9: _to_plain removed ----------------------------------------------

    def test_to_plain_removed_from_task_io(self) -> None:
        """_to_plain() must be removed from task_io — dead code after PyYAML migration."""
        import owlbear_kanban.storage as _task_io

        assert not hasattr(_task_io, "_to_plain"), (
            "_to_plain must be removed from task_io.py; "
            "PyYAML returns plain dicts natively — _to_plain is dead code after read path switch"
        )

    # -- AC 11/12: timestamp regression via read_task() -----------------------

    def test_read_task_preserves_7digit_timestamp_as_string(
        self, tmp_path: Path
    ) -> None:
        """read_task() must preserve 7-digit Go-style timestamps verbatim in Task.created."""
        from owlbear_kanban.storage import YAML12SafeLoader, read_task  # noqa: F401

        ts_7 = "2026-04-09T03:24:26.6974428+02:00"
        ts_6 = "2026-04-17T20:16:32.171661+00:00"
        content = (
            "---\n"
            "id: 42\ntitle: Timestamp Regression\nstatus: todo\npriority: needed\n"
            f"created: {ts_7}\nupdated: {ts_6}\n"
            "blocked: false\ntags: []\ndepends_on: []\nparent: null\n"
            "block_reason: null\nclaimed_by: null\nclaimed_at: null\n"
            "---\n"
        )
        task_file = tmp_path / "42-timestamp-regression.md"
        task_file.write_text(content, encoding="utf-8")

        task = read_task(task_file)

        assert task.created == ts_7, (
            f"7-digit timestamp must be preserved verbatim; got {task.created!r}"
        )
        assert task.updated == ts_6, (
            f"6-digit timestamp must be preserved verbatim; got {task.updated!r}"
        )

    # -- AC 13: YAML 1.1 coercion regression via read_task() -----------------

    def test_read_task_yaml11_string_fields_not_coerced(self, tmp_path: Path) -> None:
        """read_task() must not coerce yes/no/on/off in string fields when parsing files."""
        from owlbear_kanban.storage import YAML12SafeLoader, read_task  # noqa: F401

        # Simulate a file with unquoted YAML 1.1 bool aliases in string fields
        # (as might be written by a Go-based tool like kanban-md)
        content = (
            "---\n"
            "id: 5\ntitle: Boolean Coercion Test\nstatus: todo\npriority: needed\n"
            "created: 2026-04-09T03:24:26.6974428+02:00\n"
            "updated: 2026-04-17T20:16:32.171661+00:00\n"
            "blocked: false\n"
            "block_reason: no\n"  # unquoted 'no' — YAML 1.1 SafeLoader coerces to False
            "claimed_by: yes\n"  # unquoted 'yes' — YAML 1.1 SafeLoader coerces to True
            "tags:\n  - on\n  - off\n"  # unquoted on/off — YAML 1.1 coerces to True/False
            "depends_on: []\nparent: null\nclaimed_at: null\n"
            "---\n"
        )
        task_file = tmp_path / "5-coercion-test.md"
        task_file.write_text(content, encoding="utf-8")

        task = read_task(task_file)

        assert task.block_reason == "no", (
            f"block_reason 'no' must not be coerced to bool False; got {task.block_reason!r}"
        )
        assert task.tags == ["on", "off"], (
            f"tags with on/off values must survive as strings; got {task.tags!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_Dependencies — pyyaml declared in serve/kanban/pyproject.toml
# ---------------------------------------------------------------------------


class TestFromAC_Dependencies:
    """Verifies pyyaml is an explicit declared dependency of the owlbear-kanban package."""

    def test_pyyaml_declared_in_kanban_pyproject(self) -> None:
        """pyyaml>=6.0.3 must be listed in serve/kanban/pyproject.toml [project.dependencies]."""
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            data = tomllib.load(f)

        deps: list[str] = data["project"]["dependencies"]
        assert any("pyyaml" in dep.lower() for dep in deps), (
            f"pyyaml>=6.0.3 must be declared in serve/kanban/pyproject.toml [project.dependencies]; found: {deps}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_WriteReadRoundTrip — integration: write_task → read_task → validate
# ---------------------------------------------------------------------------


class TestFromAC_WriteReadRoundTrip:
    """Integration tests: write_task() → read_task() → Task.model_validate() round-trips."""

    def test_yaml11_string_fields_survive_write_read_roundtrip(
        self, tmp_path: Path
    ) -> None:
        """YAML 1.1 words written by write_task must be readable as strings by read_task."""
        from owlbear_kanban.storage import YAML12SafeLoader, read_task, write_task  # noqa: F401
        from owlbear_kanban.models import Task

        task = Task(
            id=1,
            title="YAML 1.1 String Survival",
            status="todo",
            priority="needed",
            created="2026-04-09T03:24:26.6974428+02:00",
            updated="2026-04-17T20:16:32.171661+00:00",
            blocked=False,
            block_reason="no",  # YAML 1.1 SafeLoader would coerce this to False
            tags=["on", "off"],  # YAML 1.1 SafeLoader would coerce on→True, off→False
        )
        kanban_dir = _make_kanban_dir(tmp_path)
        task_file = write_task(task, kanban_dir)

        loaded = read_task(task_file)

        assert loaded.block_reason == "no", (
            f"block_reason 'no' must survive as string; got {loaded.block_reason!r}"
        )
        assert loaded.tags == ["on", "off"], (
            f"tags ['on', 'off'] must survive as strings; got {loaded.tags!r}"
        )

    def test_roundtrip_bool_fields_preserved(self, tmp_path: Path) -> None:
        """bool fields (blocked=True) must survive write→read as Python True, not strings."""
        from owlbear_kanban.storage import YAML12SafeLoader, read_task, write_task  # noqa: F401
        from owlbear_kanban.models import Task

        task = Task(
            id=2,
            title="Bool Round-Trip",
            status="in-progress",
            priority="critical",
            created="2026-04-09T03:24:26.6974428+02:00",
            updated="2026-04-17T20:16:32.171661+00:00",
            blocked=True,
            block_reason="waiting on reviewer",
        )
        kanban_dir = _make_kanban_dir(tmp_path)
        task_file = write_task(task, kanban_dir)

        loaded = read_task(task_file)

        assert loaded.blocked is True, (
            f"blocked=True must survive as bool True; got {loaded.blocked!r}"
        )

    def test_full_roundtrip_with_7digit_timestamp_and_extra_fields(
        self, tmp_path: Path
    ) -> None:
        """Full write→read→model_validate round-trip: all field types including 7-digit ts."""
        from owlbear_kanban.storage import YAML12SafeLoader, read_task, write_task  # noqa: F401
        from owlbear_kanban.models import Task

        ts_7 = "2026-04-09T03:24:26.6974428+02:00"
        ts_6 = "2026-04-17T20:16:32.171661+00:00"

        task = Task(
            id=99,
            title="Realistic Round-Trip Test",
            status="review",
            priority="important",
            created=ts_7,
            updated=ts_6,
            blocked=False,
            tags=["cockpit", "engine", "phase-0"],
            parent=10,
            depends_on=[11, 12],
            block_reason=None,
            body="## Notes\n\nSome body text.\n",
        )
        kanban_dir = _make_kanban_dir(tmp_path)
        task_file = write_task(task, kanban_dir)

        loaded = read_task(task_file)
        validated = Task.model_validate(loaded.model_dump())

        assert validated.id == 99
        assert validated.created == "2026-04-09T01:24:26.697442+00:00", (
            "created timestamp should be normalized to UTC +00:00 with microsecond precision; "
            f"got {validated.created!r}"
        )
        assert validated.updated == ts_6, (
            f"6-digit timestamp must survive; got {validated.updated!r}"
        )
        assert validated.blocked is False
        assert validated.tags == ["cockpit", "engine", "phase-0"]
        assert validated.parent == 10
        assert validated.depends_on == [11, 12]
        assert validated.block_reason is None
        assert "Some body text." in validated.body

    def test_write_task_calls_make_yaml_for_ruamel_output(self, tmp_path: Path) -> None:
        """write_task() must call _make_yaml() — asserts ruamel.yaml is used, not pyyaml.dump.

        Replacing _make_yaml() with yaml.dump() would pass the data-equivalence round-trip
        tests but would silently break comment/formatting fidelity for human-edited tasks.
        This test catches that swap mechanistically.
        """
        from unittest.mock import patch

        from owlbear_kanban.models import Task
        from owlbear_kanban.storage import write_task

        task = Task(
            id=3,
            title="Write Task Mechanism",
            status="todo",
            priority="needed",
            created="2026-04-09T03:24:26.6974428+02:00",
            updated="2026-04-17T20:16:32.171661+00:00",
            blocked=False,
        )
        kanban_dir = _make_kanban_dir(tmp_path)

        with patch("owlbear_kanban.storage._make_yaml") as mock_make_yaml:
            write_task(task, kanban_dir)

        assert mock_make_yaml.called, (
            "_make_yaml() must be called in write_task() — "
            "write path must use ruamel.yaml for round-trip fidelity, not pyyaml"
        )
