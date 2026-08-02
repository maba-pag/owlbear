"""Guardrail tests that keep Kanban storage test writes scoped to tmp_path.

These checks are static and intentionally conservative: write targets must be
provably derived from tmp_path-like roots and must not escape via parent hops.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_KANBAN_TESTS = _REPO_ROOT / "serve" / "kanban" / "tests"
_TARGET_PATTERNS = (
    "test_runtime_transaction.py",
    "test_snapshot.py",
    "test_target_admission.py",
    "test_target_cutover.py",
    "test_target_runtime.py",
)
_WRITE_METHODS = {"write_text", "write_bytes", "touch", "mkdir", "rmdir", "unlink"}


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
        "source",
        "staging",
        "task_path",
        "worktree",
    }


def _is_safe_path_expr(  # noqa: C901, PLR0911, PLR0912
    node: ast.AST,
    safe_names: set[str],
    tmp_aliases: set[str] | None = None,
) -> bool:
    if isinstance(node, ast.Name):
        return node.id in safe_names

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = node.value
        return not value.startswith(("/", "~", ".."))

    if isinstance(node, ast.JoinedStr):
        first_literal = ""
        for item in node.values:
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                first_literal = item.value
                break
        return not first_literal.startswith(("/", "~", ".."))

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _is_safe_path_expr(node.left, safe_names) and _is_safe_path_expr(node.right, safe_names)

    if isinstance(node, ast.Attribute):
        if node.attr in {"home", "cwd", "root"}:
            return False
        if node.attr == "parent":
            parent_unsafe_names = safe_names if tmp_aliases is None else tmp_aliases
            if isinstance(node.value, ast.Name) and node.value.id in parent_unsafe_names:
                return False
            return _is_safe_path_expr(node.value, safe_names, tmp_aliases)
        if node.attr == "parents":
            return False
        return _is_safe_path_expr(node.value, safe_names, tmp_aliases)

    if isinstance(node, ast.Subscript):
        # Covers patterns like tmp_path.parents[0].
        return False

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "Path" and node.args:
            return all(_is_safe_path_expr(arg, safe_names, tmp_aliases) for arg in node.args)
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "joinpath",
            "resolve",
            "absolute",
        }:
            if not _is_safe_path_expr(node.func.value, safe_names, tmp_aliases):
                return False
            return all(_is_safe_path_expr(arg, safe_names, tmp_aliases) for arg in node.args)

    return False


def _collect_tmp_aliases(tree: ast.AST) -> set[str]:
    """Collect direct aliases of tmp_path to block parent-escape patterns."""
    aliases = {"tmp_path"}
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if (
                    isinstance(target, ast.Name)
                    and isinstance(node.value, ast.Name)
                    and node.value.id in aliases
                    and target.id not in aliases
                ):
                    aliases.add(target.id)
                    changed = True
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and isinstance(node.value, ast.Name)
                and node.value.id in aliases
                and node.target.id not in aliases
            ):
                aliases.add(node.target.id)
                changed = True
    return aliases


def _collect_safe_names(tree: ast.AST) -> set[str]:  # noqa: C901
    safe_names = {
        "tmp_path",
        "base_dir",
        "kanban_dir",
        "tasks_dir",
        "archive_dir",
        "quarantine_dir",
        "source",
        "staging",
        "tracked",
        "worktree",
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
    def test_kanban_storage_test_files_exist(self) -> None:
        files = _target_files()
        assert files, "Expected storage tests under serve/kanban/tests/"

    def test_kanban_storage_tests_write_only_to_tmp_path_derived_targets(self) -> None:  # noqa: C901
        violations: list[str] = []

        for path in _target_files():
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            safe_names = _collect_safe_names(tree)
            tmp_aliases = _collect_tmp_aliases(tree)

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue

                target = _extract_write_target(node)

                if target is None:
                    continue

                target_src = ast.get_source_segment(source, target) or "<expr>"
                if not _is_safe_path_expr(target, safe_names, tmp_aliases):
                    rel = path.relative_to(_REPO_ROOT)
                    violations.append(f"{rel}:{node.lineno} -> not tmp_path-derived: {target_src}")

        assert not violations, (
            "Kanban storage tests must not write outside tmp_path; "
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

    def test_extract_write_target_detects_rmdir_calls(self) -> None:
        """AC-C46 (refined): _extract_write_target must flag .rmdir() method calls.

        The refined AC-C46 adds ``rmdir`` to the enforced write-method set
        (it appears in ``test_storage_1050.py:939,966``).  The current
        implementation only checks ``{"write_text", "write_bytes", "touch",
        "mkdir"}`` in ``_WRITE_METHODS``, so ``.rmdir()`` calls return ``None``
        from ``_extract_write_target`` and are not guarded.
        """
        source = "some_path.rmdir()"
        tree = ast.parse(source, mode="eval")
        call_node = tree.body
        assert isinstance(call_node, ast.Call)
        result = _extract_write_target(call_node)
        assert result is not None, (
            "_extract_write_target must detect .rmdir() as a write target.  "
            "Refined AC-C46 adds rmdir to the enforced write-method set, but "
            "_WRITE_METHODS = " + repr(_WRITE_METHODS) + " does not include it, "
            "leaving storage-test rmdir() calls unguarded."
        )

    def test_extract_write_target_detects_unlink_calls(self) -> None:
        """AC-C46 (refined): _extract_write_target must flag .unlink() method calls.

        The refined AC-C46 adds ``unlink`` to the enforced write-method set.
        The current ``_WRITE_METHODS`` set does not include it, so storage tests
        that call ``.unlink()`` on non-``tmp_path`` paths escape the guard.
        """
        source = "some_path.unlink()"
        tree = ast.parse(source, mode="eval")
        call_node = tree.body
        assert isinstance(call_node, ast.Call)
        result = _extract_write_target(call_node)
        assert result is not None, (
            "_extract_write_target must detect .unlink() as a write target.  "
            "Refined AC-C46 adds unlink to the enforced write-method set, but "
            "_WRITE_METHODS = " + repr(_WRITE_METHODS) + " does not include it, "
            "leaving storage-test unlink() calls unguarded."
        )

    def test_is_safe_path_expr_rejects_relative_parent_hop(self) -> None:
        """AC-C46 (v2 refined): ``_is_safe_path_expr`` must reject ``../`` relative
        path traversal, not only absolute (``/``) and home (``~``) prefixes.

        A string constant ``"../escape.txt"`` starts with ``".."`` and resolves
        outside any ``tmp_path`` subtree when joined.  The current implementation
        only checks ``startswith(("/", "~"))`` at line 52, so ``"../escape.txt"``
        is treated as safe and would not be flagged as a write-target violation.

        Per architect v2 refined AC-C46: add ``".."`` to the prefix tuple so
        direct parent-traversal escapes are rejected.
        """
        source = '"../escape.txt"'
        tree = ast.parse(source, mode="eval")
        const_node = tree.body
        assert isinstance(const_node, ast.Constant)
        result = _is_safe_path_expr(const_node, {"tmp_path"})
        assert not result, (
            '"../escape.txt" starts with ".." and escapes the tmp_path subtree; '
            "_is_safe_path_expr must return False for it.  "
            'Add ".." to the startswith tuple at line 52 of test_deny_code_writes.py '
            "to enforce the architect v2 refined AC-C46 relative-parent-hop rule."
        )

    def test_is_safe_path_expr_rejects_path_multi_arg_with_absolute_segment(
        self,
    ) -> None:
        """AC-C46 (v9): Path(tmp_path, "/outside.txt") must be rejected.

        pathlib resolves ``Path(tmp_path, "/outside.txt")`` to ``/outside.txt``
        because an absolute segment overrides all preceding components.  The
        current implementation only checks ``args[0]`` (``tmp_path`` → safe)
        and ignores ``args[1]`` (``"/outside.txt"`` → starts with ``/``),
        so this expression is incorrectly classified as safe.

        Fix: validate ALL ``Path()`` args, mirroring the ``joinpath`` handler.
        """
        source = 'Path(tmp_path, "/outside.txt")'
        expr = ast.parse(source, mode="eval").body
        result = _is_safe_path_expr(expr, {"tmp_path"})
        assert not result, (
            'Path(tmp_path, "/outside.txt") must be rejected: pathlib resolves '
            "absolute segments to override preceding path components, so the "
            "write target escapes tmp_path.  _is_safe_path_expr currently checks "
            "only args[0] and must validate ALL Path() arguments instead."
        )
