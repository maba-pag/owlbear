"""Guardrail tests that keep storage-suite writes scoped to tmp_path.

These checks are static and intentionally conservative: write targets must be
provably derived from tmp_path-like roots and must not escape via parent hops.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_KANBAN_TESTS = _REPO_ROOT / "serve" / "kanban" / "tests"
_TARGET_PATTERNS = (
    "test_storage*.py",
    "test_activity_store*.py",
    "test_corruption*.py",
)
_WRITE_METHODS = {"write_text", "write_bytes", "touch", "mkdir"}


def _target_files() -> list[Path]:
    files: set[Path] = set()
    for pattern in _TARGET_PATTERNS:
        files.update(_KANBAN_TESTS.glob(pattern))
    return sorted(files)


def _name_is_tmp_root(name: str) -> bool:
    return name in {
        "tmp_path",
        "base_dir",
        "kanban_dir",
        "tasks_dir",
        "archive_dir",
        "quarantine_dir",
        "path",
        "task_path",
    }


def _is_safe_path_expr(node: ast.AST, safe_names: set[str]) -> bool:  # noqa: C901, PLR0911, PLR0912
    if isinstance(node, ast.Name):
        return node.id in safe_names

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = node.value
        return not value.startswith(("/", "~"))

    if isinstance(node, ast.JoinedStr):
        return True

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _is_safe_path_expr(node.left, safe_names) and _is_safe_path_expr(
            node.right, safe_names
        )

    if isinstance(node, ast.Attribute):
        if node.attr in {"home", "cwd", "root"}:
            return False
        if node.attr == "parent":
            if isinstance(node.value, ast.Name) and node.value.id == "tmp_path":
                return False
            return _is_safe_path_expr(node.value, safe_names)
        if node.attr == "parents":
            return False
        return _is_safe_path_expr(node.value, safe_names)

    if isinstance(node, ast.Subscript):
        # Covers patterns like tmp_path.parents[0].
        return False

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "Path" and node.args:
            return _is_safe_path_expr(node.args[0], safe_names)
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "joinpath",
            "resolve",
            "absolute",
        }:
            if not _is_safe_path_expr(node.func.value, safe_names):
                return False
            return all(_is_safe_path_expr(arg, safe_names) for arg in node.args)

    return False


def _collect_safe_names(tree: ast.AST) -> set[str]:  # noqa: C901
    safe_names = {
        "tmp_path",
        "base_dir",
        "kanban_dir",
        "tasks_dir",
        "archive_dir",
        "quarantine_dir",
    }

    # Seed with function parameters that are commonly tmp roots in helpers/fixtures.
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in node.args.args:
                if _name_is_tmp_root(arg.arg):
                    safe_names.add(arg.arg)

    # Fixed-point to propagate safe derivations through assignments.
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if _is_safe_path_expr(node.value, safe_names):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id not in safe_names:
                            safe_names.add(target.id)
                            changed = True
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.value is not None
                and _is_safe_path_expr(node.value, safe_names)
                and node.target.id not in safe_names
            ):
                    safe_names.add(node.target.id)
                    changed = True

    return safe_names


def _extract_write_target(node: ast.Call) -> ast.AST | None:
    if isinstance(node.func, ast.Attribute) and node.func.attr in _WRITE_METHODS:
        return node.func.value
    if isinstance(node.func, ast.Name) and node.func.id == "open" and node.args:
        return node.args[0]
    return None


class TestDenyCodeWrites:
    def test_storage_related_test_files_exist(self) -> None:
        files = _target_files()
        assert files, "Expected storage-related tests under serve/kanban/tests/"

    def test_storage_tests_write_only_to_tmp_path_derived_targets(self) -> None:  # noqa: C901
        violations: list[str] = []

        for path in _target_files():
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            safe_names = _collect_safe_names(tree)

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue

                target = _extract_write_target(node)

                if target is None:
                    continue

                target_src = ast.get_source_segment(source, target) or "<expr>"
                if not _is_safe_path_expr(target, safe_names):
                    rel = path.relative_to(_REPO_ROOT)
                    violations.append(
                        f"{rel}:{node.lineno} -> not tmp_path-derived: {target_src}"
                    )

        assert not violations, (
            "Storage-related tests must not write outside tmp_path; "
            "found non-compliant write targets:\n" + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# AC-C46 enforcement quality — prove the deny-writes guard is not bypassable
# ---------------------------------------------------------------------------


class TestFromAC_DenyWritesEnforcement:
    """AC-C46: _is_safe_path_expr must prove tmp_path containment, not just heuristics.

    The current implementation has two known bypass paths that allow writes
    outside ``tmp_path`` to be classified as safe:

    1. ``ast.JoinedStr`` (f-strings) are unconditionally trusted, even when
       the first element is an absolute-path prefix like ``"/tmp/"``.
    2. ``alias.parent`` is trusted when ``alias`` is a safe name derived from
       ``tmp_path`` — only the literal pattern ``tmp_path.parent`` is blocked.

    Both tests fail in RED phase, proving the guard must be strengthened.
    """

    def test_is_safe_path_expr_rejects_fstring_with_absolute_prefix(self) -> None:
        """f-strings whose first interpolated chunk is an absolute path must be rejected.

        ``f"/tmp/{name}"`` resolves to an absolute path beginning with ``/``.
        The current implementation returns ``True`` for all ``ast.JoinedStr``
        nodes unconditionally, which allows absolute-path escapes via
        f-string interpolation.
        """
        source = 'f"/tmp/{name}"'
        tree = ast.parse(source, mode="eval")
        fstring_node = tree.body
        assert isinstance(fstring_node, ast.JoinedStr)
        result = _is_safe_path_expr(fstring_node, {"tmp_path", "name"})
        assert not result, (
            'f"/tmp/{name}" starts with the absolute prefix "/" and must be rejected '
            "by _is_safe_path_expr.  The current implementation treats all f-strings as "
            "safe, allowing absolute-path escapes via f-string interpolation."
        )

    def test_is_safe_path_expr_rejects_aliased_tmp_path_parent(self) -> None:
        """alias.parent must be rejected when alias is a safe name derived from tmp_path.

        ``base = tmp_path; base.parent`` resolves to the directory that contains
        ``tmp_path``, escaping the intended isolation.  The current implementation
        only blocks the literal pattern ``tmp_path.parent``; it recurses into
        ``_is_safe_path_expr(base, safe_names)`` for alias.parent, which returns
        ``True`` because ``base`` is a propagated safe name.
        """
        source = "base.parent"
        tree = ast.parse(source, mode="eval")
        attr_node = tree.body
        assert isinstance(attr_node, ast.Attribute)
        # base is a safe alias of tmp_path (propagated via _collect_safe_names)
        safe_names: set[str] = {"tmp_path", "base"}
        result = _is_safe_path_expr(attr_node, safe_names)
        assert not result, (
            "base.parent must not be considered a safe write target even when base "
            "is derived from tmp_path.  The current implementation recurses to "
            "_is_safe_path_expr(base) → True, making base.parent appear safe. "
            "Any .parent access on a safe (tmp-derived) name must be rejected."
        )
