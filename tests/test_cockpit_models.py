"""Cockpit model cleanup and stale-reference regression tests.

Promoted from the task-scoped suite for task #1146.

AC coverage:
  - AC1: TaskSummaryOut, TaskDetailOut, TaskListOut, SessionOut, SessionListOut
         removed from owlbear_cockpit/models.py; only BoardOut remains.
  - AC1: Field and model_validator imports removed from models.py (no longer needed).
  - AC2: Dead imports and test classes removed from affected test files.
  - AC3: Stale comments/docstrings referencing removed model names updated.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).parent
_COCKPIT_SRC = Path(__file__).parent.parent / "serve" / "cockpit" / "src" / "owlbear_cockpit"

# Provenance: promoted from task-scoped suite for task #1146.

# ---------------------------------------------------------------------------
# AC1: Dead models are not importable from owlbear_cockpit.models
# ---------------------------------------------------------------------------


class TestFromAC_DeadModelsRemoved:
    """AC1: Five dead Pydantic models must no longer exist in owlbear_cockpit.models.

    Each model served cockpit routes that were rewritten in #1082 to use engine models
    directly.  After removal, attempting to import any of these names must raise ImportError.
    """

    def test_task_summary_out_raises_import_error(self) -> None:
        """TaskSummaryOut must not be importable — raises ImportError after removal."""
        with pytest.raises(ImportError):
            from owlbear_cockpit.models import TaskSummaryOut  # noqa: PLC0415, F401

    def test_task_detail_out_raises_import_error(self) -> None:
        """TaskDetailOut must not be importable — raises ImportError after removal."""
        with pytest.raises(ImportError):
            from owlbear_cockpit.models import TaskDetailOut  # noqa: PLC0415, F401

    def test_task_list_out_raises_import_error(self) -> None:
        """TaskListOut must not be importable — raises ImportError after removal."""
        with pytest.raises(ImportError):
            from owlbear_cockpit.models import TaskListOut  # noqa: PLC0415, F401

    def test_session_out_raises_import_error(self) -> None:
        """SessionOut must not be importable — raises ImportError after removal."""
        with pytest.raises(ImportError):
            from owlbear_cockpit.models import SessionOut  # noqa: PLC0415, F401

    def test_session_list_out_raises_import_error(self) -> None:
        """SessionListOut must not be importable — raises ImportError after removal."""
        with pytest.raises(ImportError):
            from owlbear_cockpit.models import SessionListOut  # noqa: PLC0415, F401

    def test_models_module_has_exactly_one_pydantic_model_class(self) -> None:
        """Boundary: models.py must contain exactly one BaseModel subclass (BoardOut).

        Currently 6 classes exist; after removal only BoardOut remains.
        """
        from pydantic import BaseModel  # noqa: PLC0415
        import owlbear_cockpit.models as m  # noqa: PLC0415

        model_classes = [
            v for _k, v in inspect.getmembers(m, inspect.isclass) if issubclass(v, BaseModel) and v is not BaseModel
        ]
        assert len(model_classes) == 1, (
            f"Expected exactly 1 BaseModel subclass (BoardOut), "
            f"got {len(model_classes)}: {[c.__name__ for c in model_classes]}"
        )

    def test_board_out_is_the_remaining_pydantic_model(self) -> None:
        """The single remaining BaseModel subclass must be BoardOut."""
        from pydantic import BaseModel  # noqa: PLC0415
        import owlbear_cockpit.models as m  # noqa: PLC0415

        model_classes = [
            v for _k, v in inspect.getmembers(m, inspect.isclass) if issubclass(v, BaseModel) and v is not BaseModel
        ]
        names = [c.__name__ for c in model_classes]
        assert names == ["BoardOut"], f"Remaining model must be exactly ['BoardOut'], got {names}"


# ---------------------------------------------------------------------------
# AC1: Field and model_validator imports cleaned up in models.py
# ---------------------------------------------------------------------------


class TestFromAC_ModelsImportsClean:
    """AC1: After removing dead models, unused pydantic imports must be removed.

    BoardOut only needs BaseModel.  Field (used by TaskSummaryOut, TaskDetailOut,
    TaskListOut) and model_validator (used by TaskDetailOut) have no remaining
    consumers and must be dropped from the import line.
    """

    def test_models_py_does_not_import_field(self) -> None:
        """models.py source must not import Field from pydantic."""
        source = (_COCKPIT_SRC / "models.py").read_text(encoding="utf-8")
        assert "Field" not in source, "models.py still imports or uses 'Field' — remove it along with dead models (AC1)"

    def test_models_py_does_not_import_model_validator(self) -> None:
        """models.py source must not import model_validator from pydantic."""
        source = (_COCKPIT_SRC / "models.py").read_text(encoding="utf-8")
        assert "model_validator" not in source, (
            "models.py still imports or uses 'model_validator' — remove it along with dead models (AC1)"
        )


# ---------------------------------------------------------------------------
# AC2: Dead imports removed from durable test_cockpit_read_api.py
# ---------------------------------------------------------------------------


class TestFromAC_TestImports930Clean:
    """AC2: test_cockpit_read_api.py must not import the three removed models.

    Tests that asserted importability of TaskSummaryOut, TaskDetailOut, and SessionOut
    (TestFromAC_NewModulesImportable and TestFromAC_PydanticResponseModels) must be
    removed because importing them will raise ImportError post-cleanup.
    """

    def test_930_does_not_import_task_summary_out(self) -> None:
        """test_cockpit_read_api.py must not import TaskSummaryOut."""
        source = (_TESTS_DIR / "test_cockpit_read_api.py").read_text(encoding="utf-8")
        assert "import TaskSummaryOut" not in source, (
            "test_cockpit_read_api.py still imports TaskSummaryOut — "
            "remove test_models_task_summary_out_importable and the pydantic subclass test (AC2)"
        )

    def test_930_does_not_import_task_detail_out(self) -> None:
        """test_cockpit_read_api.py must not import TaskDetailOut."""
        source = (_TESTS_DIR / "test_cockpit_read_api.py").read_text(encoding="utf-8")
        assert "import TaskDetailOut" not in source, (
            "test_cockpit_read_api.py still imports TaskDetailOut — "
            "remove test_models_task_detail_out_importable and the pydantic subclass test (AC2)"
        )

    def test_930_does_not_import_session_out(self) -> None:
        """test_cockpit_read_api.py must not import SessionOut."""
        source = (_TESTS_DIR / "test_cockpit_read_api.py").read_text(encoding="utf-8")
        assert "import SessionOut" not in source, (
            "test_cockpit_read_api.py still imports SessionOut — "
            "remove test_models_session_out_importable and the pydantic subclass test (AC2)"
        )


# ---------------------------------------------------------------------------
# AC2: Dead test methods removed from test_cockpit_read_api.py
# ---------------------------------------------------------------------------


class TestFromAC_TestReadApiClean:
    """AC2: test_cockpit_read_api.py must not contain the two dead test methods.

    test_task_detail_out_model_has_claimed_field and
    test_task_detail_out_model_null_claimed_by_yields_claimed_false are redundant
    now that TaskDetailOut is removed; the same behavior is covered by
    TestFromAC_TaskDetailClaimedFields methods in the same file.
    """

    def test_read_api_no_dead_method_has_claimed_field(self) -> None:
        """test_cockpit_read_api.py must not contain test_task_detail_out_model_has_claimed_field."""
        source = (_TESTS_DIR / "test_cockpit_read_api.py").read_text(encoding="utf-8")
        assert "test_task_detail_out_model_has_claimed_field" not in source, (
            "Dead test method 'test_task_detail_out_model_has_claimed_field' "
            "still present in test_cockpit_read_api.py — remove it (AC2)"
        )

    def test_read_api_no_dead_method_null_claimed_by(self) -> None:
        """test_cockpit_read_api.py must not contain test_task_detail_out_model_null_claimed_by_yields_claimed_false."""
        source = (_TESTS_DIR / "test_cockpit_read_api.py").read_text(encoding="utf-8")
        assert "test_task_detail_out_model_null_claimed_by_yields_claimed_false" not in source, (
            "Dead test method 'test_task_detail_out_model_null_claimed_by_yields_claimed_false' "
            "still present in test_cockpit_read_api.py — remove it (AC2)"
        )


# ---------------------------------------------------------------------------
# AC2: Dead test class removed from test_occ_frontend_wire.py
# ---------------------------------------------------------------------------


class TestFromAC_Test1137Clean:
    """AC2: test_occ_frontend_wire.py must not contain TestFromAC_TaskSummaryOutUpdatedField.

    This class tested that TaskSummaryOut.model_fields contains 'updated'.  Since
    TaskSummaryOut is being removed, the entire class is dead and must be deleted.
    """

    def test_1137_no_task_summary_out_updated_field_class(self) -> None:
        """TestFromAC_TaskSummaryOutUpdatedField class must not exist in 1137."""
        source = (_TESTS_DIR / "test_occ_frontend_wire.py").read_text(encoding="utf-8")
        assert "TestFromAC_TaskSummaryOutUpdatedField" not in source, (
            "Dead class 'TestFromAC_TaskSummaryOutUpdatedField' still present in "
            "test_occ_frontend_wire.py — remove the entire class (AC2)"
        )

    def test_1137_does_not_import_task_summary_out(self) -> None:
        """test_occ_frontend_wire.py must not import TaskSummaryOut."""
        source = (_TESTS_DIR / "test_occ_frontend_wire.py").read_text(encoding="utf-8")
        assert "import TaskSummaryOut" not in source, (
            "test_occ_frontend_wire.py still imports TaskSummaryOut — remove imports along with the dead class (AC2)"
        )


# ---------------------------------------------------------------------------
# AC3: Stale comments/docstrings updated in test_cockpit_mutation_race.py
# ---------------------------------------------------------------------------


class TestFromAC_CommentRefs1131Clean:
    """AC3: test_cockpit_mutation_race.py must not reference TaskDetailOut.

    The module docstring and _TASK_DETAIL_KEYS comment cite 'TaskDetailOut' by name.
    After model removal these references are stale and must be updated.
    """

    def test_1131_module_docstring_no_task_detail_out(self) -> None:
        """Module docstring of test_cockpit_mutation_race.py must not reference 'TaskDetailOut'."""
        source = (_TESTS_DIR / "test_cockpit_mutation_race.py").read_text(encoding="utf-8")
        # Module docstring is the first triple-quoted string in the file.
        # It currently contains "AC5a/AC5b: ... all 14 TaskDetailOut keys".
        module_doc_end = source.find('"""', 3)
        module_doc = source[: module_doc_end + 3]
        assert "TaskDetailOut" not in module_doc, (
            "Module docstring in test_cockpit_mutation_race.py still references "
            "'TaskDetailOut' — update AC5a/AC5b lines to drop the model name (AC3)"
        )

    def test_1131_task_detail_keys_comment_no_task_detail_out(self) -> None:
        """_TASK_DETAIL_KEYS comment context must not reference 'TaskDetailOut'."""
        source = (_TESTS_DIR / "test_cockpit_mutation_race.py").read_text(encoding="utf-8")
        # Find the _TASK_DETAIL_KEYS constant and inspect the surrounding 3 lines
        # (the comment typically appears on the line immediately before).
        idx = source.find("_TASK_DETAIL_KEYS")
        assert idx != -1, "_TASK_DETAIL_KEYS constant not found in test_cockpit_mutation_race.py"
        # Walk back to find up to 3 preceding newlines for context.
        context_start = source.rfind("\n", 0, idx)
        context_start = source.rfind("\n", 0, max(0, context_start - 1))
        context_start = source.rfind("\n", 0, max(0, context_start - 1))
        context_end = source.find("\n", idx) + 1
        context = source[context_start:context_end]
        assert "TaskDetailOut" not in context, (
            f"Context around _TASK_DETAIL_KEYS still references 'TaskDetailOut':\n{context!r}\n"
            "— update the comment to a generic description (AC3)"
        )


# ---------------------------------------------------------------------------
# AC3: Stale comments updated in test_cockpit_mutation_api.py
# ---------------------------------------------------------------------------


class TestFromAC_CommentRefs1132Clean:
    """AC3: test_cockpit_mutation_api.py must not reference TaskDetailOut."""

    def test_1132_no_task_detail_out_docstring(self) -> None:
        """test_cockpit_mutation_api.py docstrings must not reference 'TaskDetailOut'."""
        source = (_TESTS_DIR / "test_cockpit_mutation_api.py").read_text(encoding="utf-8")
        assert "TaskDetailOut" not in source, (
            "test_cockpit_mutation_api.py still references 'TaskDetailOut' — "
            "update or remove the stale docstring/comment (AC3)"
        )


# ---------------------------------------------------------------------------
# AC3: Stale comments updated in test_cockpit_mutation_api.py
# ---------------------------------------------------------------------------


class TestFromAC_CommentRefsMutationApiClean:
    """AC3: test_cockpit_mutation_api.py must not reference TaskDetailOut."""

    def test_mutation_api_no_task_detail_out_shape_comment(self) -> None:
        """test_cockpit_mutation_api.py must not reference 'TaskDetailOut'."""
        source = (_TESTS_DIR / "test_cockpit_mutation_api.py").read_text(encoding="utf-8")
        assert "TaskDetailOut" not in source, (
            "test_cockpit_mutation_api.py still references 'TaskDetailOut' — "
            "update the stale release response shape comment (AC3)"
        )


# ---------------------------------------------------------------------------
# AC3: Stale comments updated in test_cockpit_kanban_routes.py
# ---------------------------------------------------------------------------


class TestFromAC_CommentRefsCockpitKanbanRoutesClean:
    """AC3: test_cockpit_kanban_routes.py must not reference removed model names.

    The promoted durable route suite must not reintroduce stale model-name comments.
    """

    def test_kanban_routes_no_task_list_out_in_comments(self) -> None:
        """test_cockpit_kanban_routes.py must not reference 'TaskListOut'."""
        source = (_TESTS_DIR / "test_cockpit_kanban_routes.py").read_text(encoding="utf-8")
        assert "TaskListOut" not in source, (
            "test_cockpit_kanban_routes.py still references 'TaskListOut' — update the stale comment (AC3)"
        )

    def test_kanban_routes_no_task_detail_out_in_comments(self) -> None:
        """test_cockpit_kanban_routes.py must not reference 'TaskDetailOut'."""
        source = (_TESTS_DIR / "test_cockpit_kanban_routes.py").read_text(encoding="utf-8")
        assert "TaskDetailOut" not in source, (
            "test_cockpit_kanban_routes.py still references 'TaskDetailOut' — update the stale comments (AC3)"
        )

    def test_kanban_routes_no_session_list_out_in_comments(self) -> None:
        """test_cockpit_kanban_routes.py must not reference 'SessionListOut'."""
        source = (_TESTS_DIR / "test_cockpit_kanban_routes.py").read_text(encoding="utf-8")
        assert "SessionListOut" not in source, (
            "test_cockpit_kanban_routes.py still references 'SessionListOut' — update the stale comment (AC3)"
        )

    def test_kanban_routes_no_session_out_in_comments(self) -> None:
        """test_cockpit_kanban_routes.py must not reference 'SessionOut'."""
        source = (_TESTS_DIR / "test_cockpit_kanban_routes.py").read_text(encoding="utf-8")
        assert "SessionOut" not in source, (
            "test_cockpit_kanban_routes.py still references 'SessionOut' — update the stale comment (AC3)"
        )


# ---------------------------------------------------------------------------
# AC3 (Cycle 2): _TASK_DETAIL_KEYS constant in test_cockpit_mutation_race.py
# ---------------------------------------------------------------------------




class TestFromAC_CommentRefs1137DocstringClean:
    """AC3 (Cycle 2): test_occ_frontend_wire.py module docstring must not name TaskSummaryOut.

    The module docstring's AC1 bullet still references 'TaskSummaryOut (cockpit models.py)'
    which is a dead model after #1146.  The reference must be removed or reworded.
    """

    def test_1137_module_docstring_no_task_summary_out(self) -> None:
        """Module docstring of test_occ_frontend_wire.py must not contain 'TaskSummaryOut'."""
        source = (_TESTS_DIR / "test_occ_frontend_wire.py").read_text(encoding="utf-8")
        # Extract the module docstring (everything up to and including the closing triple-quote).
        doc_end = source.find('"""', 3)
        module_doc = source[: doc_end + 3]
        assert "TaskSummaryOut" not in module_doc, (
            "Module docstring of test_occ_frontend_wire.py still references "
            "'TaskSummaryOut' — remove or rephrase the AC1 bullet (AC3)"
        )


# ---------------------------------------------------------------------------
# AC3 (Cycle 2): residual 'TaskSummaryOut' / 'TaskDetailOut' in test_cockpit_read_api.py
# ---------------------------------------------------------------------------


class TestFromAC_CommentRefsReadApiClean:
    """AC3 (Cycle 2): test_cockpit_read_api.py must not reference removed model names.

    Section comments and class docstrings at lines ~498, ~506-507, ~587, ~595 still
    cite 'TaskSummaryOut' and 'TaskDetailOut' as context for existing tests.
    Those references are stale after model removal and must be updated.
    """

    def test_read_api_no_task_summary_out_in_comments(self) -> None:
        """test_cockpit_read_api.py must not reference 'TaskSummaryOut'."""
        source = (_TESTS_DIR / "test_cockpit_read_api.py").read_text(encoding="utf-8")
        assert "TaskSummaryOut" not in source, (
            "test_cockpit_read_api.py still references 'TaskSummaryOut' in comments or "
            "docstrings — update section headers and class docstrings (AC3)"
        )

    def test_read_api_no_task_detail_out_in_comments(self) -> None:
        """test_cockpit_read_api.py must not reference 'TaskDetailOut'."""
        source = (_TESTS_DIR / "test_cockpit_read_api.py").read_text(encoding="utf-8")
        assert "TaskDetailOut" not in source, (
            "test_cockpit_read_api.py still references 'TaskDetailOut' in comments or "
            "docstrings — update section headers and class docstrings (AC3)"
        )
