"""Structural guardrails for managed Change worktree creation."""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SOURCE_ROOTS = tuple(sorted(path for path in (_REPO_ROOT / "serve").glob("*/src") if path.is_dir()))
_RETIRED_PRODUCER_SYMBOLS = frozenset(
    {
        ("TargetMCPAdapter", "list_integration_ready_changes"),
        ("TargetMCPAdapter", "integrate_ready_change"),
        ("TargetMCPAdapter", "prepare_external_completion"),
        ("DeliveryRuntime", "completion_capture_bytes"),
        ("DeliveryRuntime", "publish_integration_completion"),
        ("DeliveryRuntime", "publish_integration_attention"),
        ("PortfolioCoordinator", "publish_finding"),
        ("PortfolioApplication", "show_integration_repair_context"),
        ("PortfolioApplication", "create_integration_repair_candidate"),
        ("PortfolioApplication", "admit_reviewed_integration_repair"),
        ("PortfolioApplication", "publish_integration_repair_authority_attention"),
        ("TargetMCPAdapter", "show_integration_repair_context"),
        ("TargetMCPAdapter", "create_integration_repair_candidate"),
        ("TargetMCPAdapter", "admit_reviewed_integration_repair"),
        ("TargetMCPAdapter", "publish_integration_repair_authority_attention"),
        ("ChangeWorkspaceManager", "integrate"),
        ("ChangeWorkspaceManager", "_publish_integration_finding"),
    }
)
_RETIRED_PRODUCER_CLASS_NAMES = frozenset({"IntegrationFinding", "IntegrationResult"})
_INVENTORY_FUNCTIONS = frozenset(
    {
        "list_registered",
        "list_retained",
        "list_retained_change_worktrees",
        "_registered_worktrees",
        "_registered_worktrees_all",
        "_change_branch_heads",
        "_coordination_attention",
        "_filesystem_change_ids",
        "_registered_attention",
        "_retained_attention",
        "_retained_worktree",
        "_worktree_present",
        "_cleanup_attention",
        "_cleanup_filesystem_attention",
        "_cleanup_registration_attention",
        "_cleanup_registered_record_attention",
        "_cleanup_head_attention",
        "_cleanup_content_attention",
        "_cleanup_intent_attention",
    }
)
_MUTATING_GIT_COMMANDS = frozenset(
    {
        ("worktree", "add"),
        ("worktree", "remove"),
        ("branch",),
        ("reset",),
        ("checkout",),
        ("update-ref",),
    }
)
_REGISTER_WORKTREE_CALLERS = frozenset(
    {
        ("ChangeWorkspaceManager", "ensure"),
        ("ChangeWorkspaceManager", "restart"),
        ("ChangeWorkspaceManager", "restore_worktree"),
    }
)
_REMOVE_WORKTREE_CALLERS = frozenset(
    {
        ("ChangeWorkspaceManager", "cleanup"),
        ("ChangeWorkspaceManager", "recover"),
        ("<module>", "_remove_worktrees"),
    }
)
_COMPLETION_CALLERS = frozenset({("PortfolioApplication", "observe_acceptance")})
_DISPOSITION_CAPTURE_EXEMPTIONS = frozenset({"capture_change_disposition", "resolve_change_disposition"})


def _source_files() -> tuple[Path, ...]:
    return tuple(sorted(path for root in _SOURCE_ROOTS for path in root.rglob("*.py")))


def _literal_string(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _scope_name(scope: list[str]) -> str:
    return scope[-1] if scope else "<module>"


def _sequence_contains_worktree_add(node: ast.AST) -> bool:
    if isinstance(node, ast.Starred):
        return _sequence_contains_worktree_add(node.value)
    if not isinstance(node, (ast.List, ast.Tuple)):
        return False
    return any(
        _literal_string(left) == "worktree" and _literal_string(right) == "add"
        for left, right in zip(node.elts, node.elts[1:], strict=False)
    ) or any(_sequence_contains_worktree_add(item) for item in node.elts)


def _call_contains_worktree_add(node: ast.Call) -> bool:
    return any(
        _literal_string(left) == "worktree" and _literal_string(right) == "add"
        for left, right in zip(node.args, node.args[1:], strict=False)
    ) or any(_sequence_contains_worktree_add(argument) for argument in node.args)


class _WorktreeAddVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.matches: list[tuple[int, tuple[str, ...], tuple[str, ...], str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if _call_contains_worktree_add(node):
            source = ast.get_source_segment(self._source, node) or "<call>"
            self.matches.append((node.lineno, tuple(self.classes), tuple(self.functions), source))
        self.generic_visit(node)

    def scan(self) -> None:
        self._source = self.path.read_text(encoding="utf-8")
        self.visit(ast.parse(self._source, filename=str(self.path)))


class _ManagedWorktreeRegistrationVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.matches: list[tuple[int, tuple[str, ...], tuple[str, ...]]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr == "_register_worktree":
            self.matches.append((node.lineno, tuple(self.classes), tuple(self.functions)))
        self.generic_visit(node)

    def scan(self) -> None:
        self.visit(ast.parse(self.path.read_text(encoding="utf-8"), filename=str(self.path)))


class _ManagedWorktreeRemovalVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.matches: list[tuple[int, tuple[str, ...], tuple[str, ...]]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr == "remove_worktree":
            self.matches.append((node.lineno, tuple(self.classes), tuple(self.functions)))
        self.generic_visit(node)

    def scan(self) -> None:
        self.visit(ast.parse(self.path.read_text(encoding="utf-8"), filename=str(self.path)))


class _CompletionCallVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.matches: list[tuple[int, tuple[str, ...], tuple[str, ...]]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr == "complete_change":
            self.matches.append((node.lineno, tuple(self.classes), tuple(self.functions)))
        self.generic_visit(node)

    def scan(self) -> None:
        self.visit(ast.parse(self.path.read_text(encoding="utf-8"), filename=str(self.path)))


class _RuntimeMutationVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.in_runtime = False
        self.methods: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.name == "DeliveryRuntime":
            self.in_runtime = True
            self.generic_visit(node)
            self.in_runtime = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self.in_runtime:
            self.methods[node.name] = node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if self.in_runtime:
            self.methods[node.name] = node

    def scan(self) -> None:
        self.visit(ast.parse(self.path.read_text(encoding="utf-8"), filename=str(self.path)))


def _has_attribute_call(node: ast.AST, attribute: str) -> bool:
    return any(
        isinstance(item, ast.Call)
        and isinstance(item.func, ast.Attribute)
        and isinstance(item.func.value, ast.Name)
        and item.func.value.id == "self"
        and item.func.attr == attribute
        for item in ast.walk(node)
    )


def _has_named_call(node: ast.AST, name: str) -> bool:
    return any(
        isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id == name
        for item in ast.walk(node)
    )


def _worktree_add_matches() -> list[tuple[Path, int, tuple[str, ...], tuple[str, ...], str]]:
    matches: list[tuple[Path, int, tuple[str, ...], tuple[str, ...], str]] = []
    for path in _source_files():
        visitor = _WorktreeAddVisitor(path)
        visitor.scan()
        matches.extend(
            (path, lineno, classes, functions, source) for lineno, classes, functions, source in visitor.matches
        )
    return matches


class _RetiredProducerVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.matches: list[tuple[int, str, tuple[str, ...], tuple[str, ...]]] = []

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if self.classes and (self.classes[-1], node.name) in _RETIRED_PRODUCER_SYMBOLS:
            self.matches.append((node.lineno, node.name, tuple(self.classes), tuple(self.functions)))
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.name in _RETIRED_PRODUCER_CLASS_NAMES:
            self.matches.append((node.lineno, node.name, tuple(self.classes), tuple(self.functions)))
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def scan(self) -> None:
        self.visit(ast.parse(self.path.read_text(encoding="utf-8"), filename=str(self.path)))


def _retired_producer_definitions() -> list[tuple[Path, int, str, tuple[str, ...], tuple[str, ...]]]:
    matches: list[tuple[Path, int, str, tuple[str, ...], tuple[str, ...]]] = []
    for path in _source_files():
        visitor = _RetiredProducerVisitor(path)
        visitor.scan()
        matches.extend((path, lineno, name, classes, functions) for lineno, name, classes, functions in visitor.matches)
    return matches


def test_delivery_source_has_one_managed_worktree_add_implementation() -> None:
    matches = _worktree_add_matches()

    assert len(matches) == 1, "Expected exactly one source-level worktree-add implementation:\n" + "\n".join(
        f"{path.relative_to(_REPO_ROOT)}:{lineno}" for path, lineno, _classes, _functions, _source in matches
    )
    path, _lineno, classes, functions, source = matches[0]
    assert path == _REPO_ROOT / "serve/delivery/src/owlbear_delivery/change_workspace.py"
    assert classes == ("ChangeWorkspaceManager",)
    assert functions == ("_register_worktree",)
    assert "--detach" not in source


def test_worktree_registration_has_only_named_lifecycle_callers() -> None:
    matches: list[tuple[Path, int, tuple[str, ...], tuple[str, ...]]] = []
    for path in _source_files():
        visitor = _ManagedWorktreeRegistrationVisitor(path)
        visitor.scan()
        matches.extend((path, lineno, classes, functions) for lineno, classes, functions in visitor.matches)

    actual = {
        (_scope_name(list(classes)), _scope_name(list(functions))) for _path, _line, classes, functions in matches
    }
    assert actual == _REGISTER_WORKTREE_CALLERS, "Unexpected worktree registration callers: " + repr(matches)


def test_worktree_removal_has_only_named_cleanup_caller() -> None:
    matches: list[tuple[Path, int, tuple[str, ...], tuple[str, ...]]] = []
    for path in _source_files():
        visitor = _ManagedWorktreeRemovalVisitor(path)
        visitor.scan()
        matches.extend((path, lineno, classes, functions) for lineno, classes, functions in visitor.matches)

    actual = {
        (_scope_name(list(classes)), _scope_name(list(functions))) for _path, _line, classes, functions in matches
    }
    assert actual == _REMOVE_WORKTREE_CALLERS, "Unexpected worktree removal callers: " + repr(matches)


def _is_none_guard(node: ast.AST, name: str) -> bool:
    return (
        isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Name)
        and node.left.id == name
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.Is)
        and len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Constant)
        and node.comparators[0].value is None
    )


def test_completion_has_one_application_callsite_and_merged_latch_guard() -> None:
    matches: list[tuple[Path, int, tuple[str, ...], tuple[str, ...]]] = []
    for path in _source_files():
        visitor = _CompletionCallVisitor(path)
        visitor.scan()
        matches.extend((path, lineno, classes, functions) for lineno, classes, functions in visitor.matches)

    actual = {
        (_scope_name(list(classes)), _scope_name(list(functions))) for _path, _line, classes, functions in matches
    }
    assert actual == _COMPLETION_CALLERS, "Unexpected completion callsites: " + repr(matches)

    runtime = _REPO_ROOT / "serve/delivery/src/owlbear_delivery/delivery_runtime.py"
    module = ast.parse(runtime.read_text(encoding="utf-8"), filename=str(runtime))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "DeliveryRuntime"
    )
    completion = next(
        node
        for node in runtime_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "complete_change"
    )
    assert any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "latch" for target in node.targets)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "frontier"
        and node.value.attr == "merged_pull_request_latch"
        for node in ast.walk(completion)
    )
    assert any(
        isinstance(node, ast.If) and any(_is_none_guard(test, "latch") for test in ast.walk(node.test))
        for node in ast.walk(completion)
    )


def test_runtime_frontier_writers_use_the_central_mutability_policy() -> None:
    runtime_path = _REPO_ROOT / "serve/delivery/src/owlbear_delivery/delivery_runtime.py"
    visitor = _RuntimeMutationVisitor(runtime_path)
    visitor.scan()
    writers = {
        name
        for name, node in visitor.methods.items()
        if _has_attribute_call(node, "_replace")
        or _has_named_call(node, "_require_change_mutable")
        or name == "complete_change"
    }
    normal_writers = writers - _DISPOSITION_CAPTURE_EXEMPTIONS

    from owlbear_delivery.delivery_runtime import _NORMAL_CHANGE_MUTATIONS

    assert normal_writers == _NORMAL_CHANGE_MUTATIONS
    assert all(_has_named_call(visitor.methods[name], "_require_change_mutable") for name in normal_writers)
    assert _has_named_call(visitor.methods["capture_change_disposition"], "is_change_terminal")
    resolver = visitor.methods["resolve_change_disposition"]
    assert any(isinstance(node, ast.Name) and node.id == "expected_disposition_id" for node in ast.walk(resolver))
    assert _has_named_call(resolver, "_require_no_active_change_claim")
    assert any(
        isinstance(node, ast.Dict)
        and any(
            isinstance(key, ast.Constant)
            and key.value == "change_disposition"
            and isinstance(value, ast.Constant)
            and value.value is None
            for key, value in zip(node.keys, node.values, strict=False)
        )
        for node in ast.walk(resolver)
    )
    assert any(
        isinstance(node, ast.Dict)
        and any(
            isinstance(key, ast.Constant)
            and key.value == "change_disposition_resolution"
            and isinstance(value, ast.Name)
            and value.id == "resolution"
            for key, value in zip(node.keys, node.values, strict=False)
        )
        for node in ast.walk(resolver)
    )


def test_target_sync_runtime_writers_bind_operation_names_before_replacement() -> None:
    runtime_path = _REPO_ROOT / "serve/delivery/src/owlbear_delivery/delivery_runtime.py"
    visitor = _RuntimeMutationVisitor(runtime_path)
    visitor.scan()

    for method_name in ("record_resolved_target_sync", "record_target_sync_abort"):
        method = visitor.methods[method_name]
        mutability_guards = [
            node
            for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_require_change_mutable"
        ]
        replacements = [
            node
            for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
            and node.func.attr == "_replace"
        ]

        assert any(len(node.args) >= 2 and _literal_string(node.args[1]) == method_name for node in mutability_guards)
        assert mutability_guards
        assert replacements
        assert max(node.lineno for node in mutability_guards) < min(node.lineno for node in replacements)


def test_delivery_source_has_no_retired_local_integration_producers() -> None:
    matches = _retired_producer_definitions()

    assert not matches, "Retired local Integration producers were reintroduced:\n" + "\n".join(
        f"{path.relative_to(_REPO_ROOT)}:{lineno} {name}" for path, lineno, name, _classes, _functions in matches
    )


class _InventoryMutationVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.functions: list[str] = []
        self.matches: list[tuple[int, str]] = []

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if node.name in _INVENTORY_FUNCTIONS:
            self.functions.append(node.name)
            self.generic_visit(node)
            self.functions.pop()
            return
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:
        if self.functions:
            literals = tuple(_literal_string(argument) for argument in node.args)
            for command in _MUTATING_GIT_COMMANDS:
                if literals[: len(command)] == command:
                    self.matches.append((node.lineno, f"{command!r}: {ast.get_source_segment(self._source, node)}"))
        self.generic_visit(node)

    def scan(self) -> None:
        self._source = self.path.read_text(encoding="utf-8")
        self.visit(ast.parse(self._source, filename=str(self.path)))


def test_retained_inventory_path_is_structurally_read_only() -> None:
    matches: list[tuple[Path, int, str]] = []
    for path in _source_files():
        visitor = _InventoryMutationVisitor(path)
        visitor.scan()
        matches.extend((path, lineno, source) for lineno, source in visitor.matches)

    assert not matches, "Retained worktree inventory references Git mutation operations:\n" + "\n".join(
        f"{path.relative_to(_REPO_ROOT)}:{lineno} {source}" for path, lineno, source in matches
    )
