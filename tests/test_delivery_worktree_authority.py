"""Structural guardrails for managed Change worktree creation."""

from __future__ import annotations

import ast
import re
import shlex
from pathlib import Path
from typing import NamedTuple

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
_GITHUB_PROVIDER_SOURCE = _REPO_ROOT / "serve/delivery-github/src/owlbear_delivery_github/github.py"
_FORBIDDEN_PROVIDER_TERMS = re.compile(
    r"(?:/merge\b|auto.?merge|update.?branch|enablePullRequestAutoMerge)", re.IGNORECASE
)
_FORBIDDEN_FIELD_PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:merge_method|mergeMethod)(?![A-Za-z0-9])")
_FORBIDDEN_CAPABILITY_PATTERNS = (
    re.compile(r"/merge(?:\b|/)", re.IGNORECASE),
    re.compile(r"(?:auto.?merge|enablePullRequestAutoMerge)", re.IGNORECASE),
    re.compile(r"(?:merge[_]?pull[_]?request|update[_]?pull[_]?request[_]?branch)", re.IGNORECASE),
)
_AUTOMATION_GOVERNANCE_PATTERN = re.compile(
    r"(?ix)(?<![A-Za-z0-9])(?:"
    r"(?:workflow|automation)[ _-]*(?:approval|blocking|block|risk(?:[ _-]*class(?:ifier)?)?)"
    r"(?:[ _-]*(?:gate|policy|class(?:ifier)?))?|"
    r"(?:approval|blocking|block|risk(?:[ _-]*class(?:ifier)?)?)[ _-]*(?:workflow|automation)"
    r"[ _-]*(?:gate|policy|class(?:ifier)?)"
    r")(?![A-Za-z0-9])"
)
_FORBIDDEN_GIT_ADMIN_PATH_PATTERN = re.compile(
    r"(?:\$GIT_DIR|\$GIT_COMMON_DIR|\.git[\\/]worktrees(?:[\\/]|\b)|"
    r"[\"']\.git[\"']\s*[,/]\s*[\"']worktrees[\"']|"
    r"\b[A-Za-z_]*(?:^|_)(?:git|admin)(?:_|$)[A-Za-z0-9_]*\s*/\s*[\"']worktrees[\"'])",
    re.IGNORECASE,
)
_ALLOWED_PROVIDER_REST_CALLS = {
    "read_repository": ("GET", "_repository_endpoint(repository)"),
    "read_pull_request": ("GET", 'f"{_repository_endpoint(repository)}/pulls/{number}"'),
    "find_pull_request": ("GET", 'f"{_repository_endpoint(request.repository)}/pulls?{query}"'),
    "create_draft_pull_request": ("POST", 'f"{_repository_endpoint(request.repository)}/pulls"'),
    "update_pull_request": ("PATCH", 'f"{_repository_endpoint(request.repository)}/pulls/{request.number}"'),
}
_ALLOWED_PROVIDER_GRAPHQL_CALLS = frozenset(
    {
        ("_graphql", "set_pull_request_draft_state", "mutation"),
        ("_graphql_query", "_observe_check_page", "_OBSERVE_CHECKS_QUERY"),
    }
)
_ALLOWED_PROVIDER_DOCUMENTS = frozenset({"_READY_MUTATION", "_DRAFT_MUTATION", "_OBSERVE_CHECKS_QUERY"})
_SUBPROCESS_APIS = frozenset({"Popen", "check_call", "check_output", "run"})
_SHELL_APIS = frozenset({"popen", "system"})
_GIT_HELPER_NAME_PATTERN = re.compile(r"(?:^|_)git(?:_|$)", re.IGNORECASE)
_GIT_CONTROL_KEYWORDS = frozenset(
    {"check", "cmd", "command", "cwd", "env", "environment", "input", "input_bytes", "input_text", "shell"}
)
_GIT_UPDATE_HEAD_OK_KEYWORDS = frozenset({"update_head_ok"})
_URL_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_UPDATE_HEAD_OK_FLAGS = frozenset({"--update-head-ok", "-u"})
_GIT_GLOBAL_OPTIONS_WITH_VALUES = frozenset(
    {"-C", "-c", "--config-env", "--exec-path", "--git-dir", "--namespace", "--super-prefix", "--work-tree"}
)
_SHELL_COMMAND_PREFIXES = frozenset({"!", "-", "run:", "do", "done", "elif", "else", "if", "then", "until", "while"})
_SHELL_COMMAND_SEPARATORS = frozenset({"&", "&&", ";", "|", "||"})


class _FetchInvocation(NamedTuple):
    arguments: tuple[ast.AST, ...]
    keyword_refspecs: tuple[ast.AST, ...] = ()
    unresolved_update_head_ok: tuple[ast.AST, ...] = ()


def _source_files() -> tuple[Path, ...]:
    return _production_python_files()


def _production_python_files() -> tuple[Path, ...]:
    roots = (
        *_SOURCE_ROOTS,
        _REPO_ROOT / "setup",
        _REPO_ROOT / "seed",
        _REPO_ROOT / ".owlbear/hooks",
        _REPO_ROOT / ".owlbear/scripts",
    )
    return tuple(sorted(path for root in roots if root.is_dir() for path in root.rglob("*.py") if path.is_file()))


def _production_command_files() -> tuple[Path, ...]:
    roots = (_REPO_ROOT / ".github/workflows", _REPO_ROOT / ".owlbear/hooks", _REPO_ROOT / ".owlbear/scripts")
    suffixes = {".bash", ".sh", ".yaml", ".yml"}
    excluded_parts = {".venv", "dist", "node_modules"}
    return tuple(
        sorted(
            path
            for root in roots
            if root.is_dir()
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix in suffixes
            and not any(part in excluded_parts for part in path.relative_to(root).parts)
        )
    )


def _fixture_path(name: str) -> Path:
    return _REPO_ROOT / "tests/fixtures/delivery-authority" / name


def _production_frontend_files() -> tuple[Path, ...]:
    root = _REPO_ROOT / "serve/cockpit/web"
    excluded_parts = {"__tests__", "dist", "e2e", "node_modules", "public"}
    return tuple(
        sorted(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix in {".js", ".jsx", ".ts", ".tsx"}
            and not any(part in excluded_parts for part in path.relative_to(root).parts)
            and not path.stem.endswith((".spec", ".test"))
        )
    )


def _agent_files() -> tuple[Path, ...]:
    roots = tuple(
        _REPO_ROOT / name
        for name in (
            ".owlbear/instructions",
            ".owlbear/prompts",
            ".owlbear/skills",
            "share/agents",
            "share/instructions",
            "share/prompts",
            "share/skills",
            ".github/skills",
        )
    )
    files = [path for root in roots if root.is_dir() for path in root.rglob("*.md") if path.is_file()]
    copilot_instructions = _REPO_ROOT / ".github/copilot-instructions.md"
    if copilot_instructions.is_file():
        files.append(copilot_instructions)
    return tuple(sorted(files))


def _production_capability_files() -> tuple[Path, ...]:
    return tuple(sorted((*_production_python_files(), *_production_frontend_files(), *_agent_files())))


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


class _ProviderCallVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.functions: list[str] = []
        self.rest_calls: list[tuple[str, str | None, str | None]] = []
        self.graphql_calls: list[tuple[str, str, str | None]] = []

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"_rest", "_graphql", "_graphql_query"}:
            function = self.functions[-1] if self.functions else "<module>"
            if node.func.attr == "_rest":
                method = _literal_string(node.args[1]) if len(node.args) > 1 else None
                endpoint = ast.get_source_segment(self._source, node.args[2]) if len(node.args) > 2 else None
                self.rest_calls.append((function, method, endpoint))
            else:
                query = self._query_name(node.args[1]) if len(node.args) > 1 else None
                self.graphql_calls.append((node.func.attr, function, query))
        self.generic_visit(node)

    def _query_name(self, body: ast.AST) -> str | None:
        if not isinstance(body, ast.Dict):
            return None
        for key, value in zip(body.keys, body.values, strict=False):
            if _literal_string(key) == "query":
                return value.id if isinstance(value, ast.Name) else None
        return None

    def scan(self) -> None:
        self._source = self.path.read_text(encoding="utf-8")
        self.visit(ast.parse(self._source, filename=str(self.path)))


def _provider_rest_violations(path: Path) -> tuple[str, ...]:
    visitor = _ProviderCallVisitor(path)
    visitor.scan()
    violations: list[str] = []
    seen: dict[str, int] = {}
    for function, method, endpoint in visitor.rest_calls:
        seen[function] = seen.get(function, 0) + 1
        expected = _ALLOWED_PROVIDER_REST_CALLS.get(function)
        if expected is None:
            violations.append(f"unexpected REST operation in {function}")
            continue
        expected_method, expected_endpoint = expected
        normalized_endpoint = "".join((endpoint or "").split())
        if (method, normalized_endpoint) != (expected_method, expected_endpoint):
            violations.append(f"unexpected REST shape in {function}: {method} {endpoint}")
        if _FORBIDDEN_PROVIDER_TERMS.search(endpoint or ""):
            violations.append(f"forbidden REST route in {function}: {endpoint}")
    for function in _ALLOWED_PROVIDER_REST_CALLS:
        if seen.get(function, 0) != 1:
            violations.append(f"expected exactly one REST call in {function}")
    return tuple(violations)


def _provider_graphql_violations(path: Path) -> tuple[str, ...]:
    source = path.read_text(encoding="utf-8")
    module = ast.parse(source, filename=str(path))
    documents: dict[str, str] = {}
    for node in ast.walk(module):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
        else:
            targets = ()
        for target in targets:
            value = getattr(node, "value", None)
            if (
                isinstance(target, ast.Name)
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
                and value.value.lstrip().startswith(("mutation", "query"))
            ):
                documents[target.id] = value.value
    visitor = _ProviderCallVisitor(path)
    visitor.scan()
    violations = [
        f"unexpected GraphQL document {name}" for name in documents if name not in _ALLOWED_PROVIDER_DOCUMENTS
    ]
    violations.extend(
        f"forbidden GraphQL document content in {name}"
        for name, document in documents.items()
        if _FORBIDDEN_PROVIDER_TERMS.search(document)
    )
    violations.extend(
        f"unexpected GraphQL call shape: {call!r}"
        for call in visitor.graphql_calls
        if call not in _ALLOWED_PROVIDER_GRAPHQL_CALLS
    )
    draft_calls = ("_graphql", "set_pull_request_draft_state", "mutation")
    if draft_calls in visitor.graphql_calls and not _has_fixed_draft_mutation_binding(module):
        violations.append("draft-state GraphQL mutation is not bound to the fixed documents")
    return tuple(violations)


def _has_fixed_draft_mutation_binding(module: ast.Module) -> bool:
    method = next(
        (
            node
            for node in ast.walk(module)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "set_pull_request_draft_state"
        ),
        None,
    )
    if method is None:
        return False
    bindings: list[ast.AST] = []
    for node in ast.walk(method):
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
            value = node.value
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == "mutation" for target in targets):
            bindings.append(value)
    if len(bindings) != 1 or not isinstance(bindings[0], ast.IfExp):
        return False
    branches = {branch.id for branch in (bindings[0].body, bindings[0].orelse) if isinstance(branch, ast.Name)}
    return branches == {"_DRAFT_MUTATION", "_READY_MUTATION"}


class _ScopeBindingsVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.bindings: dict[str, ast.AST] = {}

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.bindings[target.id] = node.value
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.value is not None:
            self.bindings[node.target.id] = node.value
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        if isinstance(node.target, ast.Name):
            self.bindings[node.target.id] = node.value
        self.generic_visit(node)

    def visit_FunctionDef(self, _node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, _node: ast.AsyncFunctionDef) -> None:
        return

    def visit_ClassDef(self, _node: ast.ClassDef) -> None:
        return

    def visit_Lambda(self, _node: ast.Lambda) -> None:
        return


def _scope_bindings(scope: ast.AST) -> dict[str, ast.AST]:
    visitor = _ScopeBindingsVisitor()
    visitor.generic_visit(scope)
    return visitor.bindings


def _resolved_literal(node: ast.AST, bindings: dict[str, ast.AST], seen: tuple[str, ...] = ()) -> str | None:
    literal = _literal_string(node)
    if literal is not None:
        return literal
    if isinstance(node, ast.Name) and node.id in bindings and node.id not in seen:
        return _resolved_literal(bindings[node.id], bindings, (*seen, node.id))
    return None


def _resolved_boolean(node: ast.AST, bindings: dict[str, ast.AST], seen: tuple[str, ...] = ()) -> bool | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.Name) and node.id in bindings and node.id not in seen:
        return _resolved_boolean(bindings[node.id], bindings, (*seen, node.id))
    return None


def _resolved_expression(node: ast.AST, bindings: dict[str, ast.AST], seen: tuple[str, ...] = ()) -> ast.AST:
    if isinstance(node, ast.Name) and node.id in bindings and node.id not in seen:
        return _resolved_expression(bindings[node.id], bindings, (*seen, node.id))
    return node


def _resolved_sequence(
    node: ast.AST,
    bindings: dict[str, ast.AST],
    seen: tuple[str, ...] = (),
) -> tuple[ast.AST, ...] | None:
    if isinstance(node, (ast.List, ast.Tuple)):
        return tuple(node.elts)
    if isinstance(node, ast.Name) and node.id in bindings and node.id not in seen:
        return _resolved_sequence(bindings[node.id], bindings, (*seen, node.id))
    return None


def _is_git_executable(node: ast.AST, bindings: dict[str, ast.AST], seen: tuple[str, ...] = ()) -> bool:
    if _resolved_literal(node, bindings) == "git":
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "resolve_git_executable":
        return True
    if isinstance(node, ast.Name) and node.id in bindings and node.id not in seen:
        return _is_git_executable(bindings[node.id], bindings, (*seen, node.id))
    return False


def _string_shape(node: ast.AST, source: str, bindings: dict[str, ast.AST], seen: tuple[str, ...] = ()) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in bindings and node.id not in seen:
            return _string_shape(bindings[node.id], source, bindings, (*seen, node.id))
        return f"{{{node.id}}}"
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                parts.append(_string_shape(value.value, source, bindings, seen))
        return "".join(parts)
    return ast.get_source_segment(source, node) or ""


class _FetchVisitor(ast.NodeVisitor):
    def __init__(self, source: str, module: ast.Module) -> None:
        self.source = source
        self.module_bindings = _scope_bindings(module)
        self.bindings = self.module_bindings
        self.subprocess_modules = self._imported_modules(module, "subprocess")
        self.subprocess_functions = self._imported_functions(module, "subprocess")
        self.os_modules = self._imported_modules(module, "os")
        self.os_functions = self._imported_functions(module, "os")
        self.class_depth = 0
        self.function_depth = 0
        self.class_bindings: list[dict[str, ast.AST]] = []
        self.violations: list[str] = []

    @staticmethod
    def _imported_modules(module: ast.Module, module_name: str) -> frozenset[str]:
        aliases = {module_name}
        for node in module.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == module_name:
                        aliases.add(alias.asname or module_name)
        return frozenset(aliases)

    @staticmethod
    def _imported_functions(module: ast.Module, module_name: str) -> frozenset[str]:
        aliases: set[str] = set()
        for node in module.body:
            if isinstance(node, ast.ImportFrom) and node.module == module_name:
                aliases.update(alias.asname or alias.name for alias in node.names)
        return frozenset(aliases)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        previous_bindings = self.bindings
        base_bindings = self.module_bindings if self.class_depth and not self.function_depth else previous_bindings
        parameters = {
            argument.arg
            for argument in (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            )
        }
        if node.args.vararg is not None:
            parameters.add(node.args.vararg.arg)
        if node.args.kwarg is not None:
            parameters.add(node.args.kwarg.arg)
        self.bindings = {name: value for name, value in base_bindings.items() if name not in parameters}
        self.bindings.update(_scope_bindings(node))
        self.function_depth += 1
        self.generic_visit(node)
        self.function_depth -= 1
        self.bindings = previous_bindings

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        previous_bindings = self.bindings
        previous_class_depth = self.class_depth
        class_bindings = _scope_bindings(node)
        self.bindings = {**self.module_bindings, **class_bindings}
        self.class_bindings.append(class_bindings)
        self.class_depth += 1
        for statement in node.body:
            self.visit(statement)
        self.class_depth = previous_class_depth
        self.class_bindings.pop()
        self.bindings = previous_bindings

    @staticmethod
    def _call_attribute(node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        if isinstance(node.func, ast.Name):
            return node.func.id
        return None

    def _is_git_helper_call(self, node: ast.Call) -> bool:
        name = self._call_attribute(node)
        return name is not None and _GIT_HELPER_NAME_PATTERN.search(name) is not None

    def _is_subprocess_call(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Name):
            return node.func.id in self.subprocess_functions
        return (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in self.subprocess_modules
            and node.func.attr in _SUBPROCESS_APIS
        )

    def _is_shell_call(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Name):
            return node.func.id in self.os_functions
        return (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in self.os_modules
            and node.func.attr in _SHELL_APIS
        )

    def _shell_fetch_shape(self, node: ast.Call) -> str | None:
        if not (self._is_shell_call(node) or (self._is_subprocess_call(node) and node.args)):
            return None
        command = (
            node.args[0]
            if node.args
            else next(
                (keyword.value for keyword in node.keywords if keyword.arg == "args"),
                None,
            )
        )
        if command is None:
            return None
        shape = _string_shape(command, self.source, self.bindings)
        return shape if re.search(r"\bgit\s+fetch\b", shape) else None

    def _helper_keyword_arguments(self, node: ast.Call) -> _FetchInvocation:
        keyword_arguments: list[ast.AST] = []
        keyword_refspecs: list[ast.AST] = []
        unresolved_update_head_ok: list[ast.AST] = []
        for keyword in node.keywords:
            if keyword.arg is None:
                keyword_arguments.append(ast.Starred(value=keyword.value, ctx=ast.Load()))
            elif keyword.arg in _GIT_UPDATE_HEAD_OK_KEYWORDS:
                resolved_boolean = _resolved_boolean(keyword.value, self.bindings)
                if resolved_boolean is True:
                    keyword_arguments.append(ast.Constant(value="--update-head-ok"))
                elif resolved_boolean is None:
                    unresolved_update_head_ok.append(keyword.value)
            elif keyword.arg == "remote" or keyword.arg in _GIT_CONTROL_KEYWORDS:
                continue
            else:
                keyword_refspecs.append(keyword.value)
        return _FetchInvocation(tuple(keyword_arguments), tuple(keyword_refspecs), tuple(unresolved_update_head_ok))

    def _fetch_arguments(self, node: ast.Call) -> _FetchInvocation | None:
        if self._is_git_helper_call(node):
            command_index = next(
                (
                    index
                    for index, argument in enumerate(node.args)
                    if _resolved_literal(argument, self.bindings) == "fetch"
                ),
                None,
            )
            if command_index is None:
                command_keyword = next(
                    (
                        keyword.value
                        for keyword in node.keywords
                        if keyword.arg in {"command", "cmd"}
                        and _resolved_literal(keyword.value, self.bindings) == "fetch"
                    ),
                    None,
                )
                if command_keyword is None:
                    return None
                command_arguments = list(node.args)
            else:
                command_arguments = list(node.args[command_index + 1 :])
            keyword_invocation = self._helper_keyword_arguments(node)
            command_arguments.extend(keyword_invocation.arguments)
            return _FetchInvocation(
                tuple(command_arguments),
                keyword_invocation.keyword_refspecs,
                keyword_invocation.unresolved_update_head_ok,
            )

        if not self._is_subprocess_call(node):
            return None
        command = (
            node.args[0]
            if node.args
            else next(
                (keyword.value for keyword in node.keywords if keyword.arg == "args"),
                None,
            )
        )
        if command is None:
            return None
        command_vector = _resolved_sequence(command, self.bindings)
        if command_vector is None or not command_vector or not _is_git_executable(command_vector[0], self.bindings):
            return None
        command_index = next(
            (
                index
                for index, argument in enumerate(command_vector)
                if _resolved_literal(argument, self.bindings) == "fetch"
            ),
            None,
        )
        return None if command_index is None else _FetchInvocation(tuple(command_vector[command_index + 1 :]))

    def _refspec_arguments(self, arguments: tuple[ast.AST, ...]) -> tuple[ast.AST, ...]:
        remote_seen = False
        refspecs: list[ast.AST] = []
        for argument in arguments:
            literal = _resolved_literal(argument, self.bindings)
            if not remote_seen:
                if literal is not None and literal.startswith("-"):
                    continue
                remote_seen = True
                continue
            if literal is not None and literal.startswith("-"):
                continue
            refspecs.append(argument)
        return tuple(refspecs)

    def _argument_expression(self, argument: ast.AST) -> ast.AST:
        if isinstance(argument, ast.Attribute) and isinstance(argument.value, ast.Name) and argument.value.id == "self":
            for bindings in reversed(self.class_bindings):
                if argument.attr in bindings:
                    return _resolved_expression(bindings[argument.attr], self.bindings)
        return _resolved_expression(argument, self.bindings)

    def _argument_shape(self, argument: ast.AST) -> str:
        if isinstance(argument, ast.Attribute) and isinstance(argument.value, ast.Name) and argument.value.id == "self":
            for bindings in reversed(self.class_bindings):
                if argument.attr in bindings:
                    return _string_shape(bindings[argument.attr], self.source, self.bindings)
        return _string_shape(argument, self.source, self.bindings)

    def _record_refspec_violation(self, node: ast.Call, argument: ast.AST) -> None:
        shape = self._argument_shape(argument)
        if ":" not in shape:
            if not isinstance(self._argument_expression(argument), (ast.Constant, ast.JoinedStr)):
                self.violations.append(f"fetch has an unresolved explicit refspec at line {node.lineno}: {shape}")
            return
        if _URL_SCHEME_PATTERN.match(shape):
            return
        destination = shape.rsplit(":", maxsplit=1)[1]
        if not destination.startswith("refs/remotes/"):
            self.violations.append(f"fetch has an unsafe explicit destination at line {node.lineno}: {shape}")

    def _record_refspec_violations(self, node: ast.Call, invocation: _FetchInvocation) -> None:
        for argument in (*self._refspec_arguments(invocation.arguments), *invocation.keyword_refspecs):
            self._record_refspec_violation(node, argument)

    def _record_fetch_violations(self, node: ast.Call, invocation: _FetchInvocation) -> None:
        arguments = invocation.arguments
        if any(isinstance(argument, ast.Starred) for argument in arguments):
            self.violations.append(f"fetch forwards unpacked arguments at line {node.lineno}")
        literals = tuple(_resolved_literal(argument, self.bindings) for argument in arguments)
        update_flag = next((literal for literal in literals if literal in _UPDATE_HEAD_OK_FLAGS), None)
        if update_flag is not None:
            self.violations.append(f"fetch uses update-head-ok option {update_flag} at line {node.lineno}")
        if "--refmap=" not in literals:
            self.violations.append(f"fetch lacks an empty refmap at line {node.lineno}")
        for _ in invocation.unresolved_update_head_ok:
            self.violations.append(f"fetch has an unresolved update-head-ok option at line {node.lineno}")
        self._record_refspec_violations(node, invocation)

    def visit_Call(self, node: ast.Call) -> None:
        shell_shape = self._shell_fetch_shape(node)
        if shell_shape is not None:
            self.violations.append(f"fetch uses an unstructured shell command at line {node.lineno}: {shell_shape}")
            self.generic_visit(node)
            return
        invocation = self._fetch_arguments(node)
        if invocation is not None:
            self._record_fetch_violations(node, invocation)
        self.generic_visit(node)


def _fetch_violations(path: Path) -> tuple[str, ...]:
    source = path.read_text(encoding="utf-8")
    module = ast.parse(source, filename=str(path))
    visitor = _FetchVisitor(source, module)
    visitor.visit(module)
    return tuple(visitor.violations)


def _logical_shell_lines(source: str) -> tuple[tuple[int, str], ...]:
    lines = source.splitlines()
    logical_lines: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        line_number = index + 1
        line = lines[index]
        folded_match = re.match(r"^(?P<indent>\s*)(?:-\s+)?run:\s*>\s*[+-]?\s*$", line)
        if folded_match:
            base_indent = len(folded_match.group("indent"))
            content: list[str] = []
            next_index = index + 1
            while next_index < len(lines):
                next_line = lines[next_index]
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_line.strip() and next_indent <= base_indent:
                    break
                if next_line.strip():
                    content.append(next_line.strip())
                next_index += 1
            if content:
                logical_lines.append((line_number, " ".join(content)))
                index = next_index
                continue

        inline_match = re.match(r"^\s*(?:-\s+)?run:\s+(?P<command>.+?)\s*$", line)
        if inline_match and not re.match(r"^[|>]\s*[+-]?\s*$", inline_match.group("command")):
            command = _unwrap_inline_command(inline_match.group("command"))
            logical_lines.append((line_number, command))
            index += 1
            continue

        command = line.rstrip()
        while command.endswith("\\") and index + 1 < len(lines):
            command = command[:-1].rstrip() + " " + lines[index + 1].lstrip()
            index += 1
        logical_lines.append((line_number, command))
        index += 1
    return tuple(logical_lines)


def _unwrap_inline_command(command: str) -> str:
    if len(command) < 2 or command[0] != command[-1] or command[0] not in {"'", '"'}:
        return command
    try:
        parsed = shlex.split(command)
    except ValueError:
        return command
    body = command[1:-1]
    return body if len(parsed) == 1 and parsed[0] == body else command


def _shell_tokens(command: str) -> tuple[str, ...] | None:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()`")
    lexer.whitespace_split = True
    lexer.commenters = "#"
    try:
        return tuple(lexer)
    except ValueError:
        return None


def _shell_command_prefix(tokens: tuple[str, ...], command_index: int) -> tuple[str, ...]:
    for index in range(command_index - 1, -1, -1):
        if tokens[index] in {"(", "$(", "`"}:
            return tokens[index + 1 : command_index]
    return tokens[:command_index]


def _is_shell_assignment(token: str) -> bool:
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token) is not None


def _git_fetch_index(tokens: tuple[str, ...]) -> int | None:
    for index, token in enumerate(tokens):
        if token != "git" or any(
            prefix not in _SHELL_COMMAND_PREFIXES
            and prefix not in {"command", "env", "sudo"}
            and not _is_shell_assignment(prefix)
            and not (prefix.startswith("-") and "sudo" in tokens[:index])
            for prefix in _shell_command_prefix(tokens, index)
        ):
            continue
        option_index = index + 1
        while option_index < len(tokens):
            option = tokens[option_index]
            if option == "fetch":
                return option_index
            if option in _GIT_GLOBAL_OPTIONS_WITH_VALUES:
                option_index += 2
                continue
            if any(option.startswith(f"{name}=") for name in _GIT_GLOBAL_OPTIONS_WITH_VALUES):
                option_index += 1
                continue
            if option.startswith("-"):
                option_index += 1
                continue
            break
    return None


def _shell_segments(tokens: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    segments: list[tuple[str, ...]] = []
    current: list[str] = []
    for token in tokens:
        if token in _SHELL_COMMAND_SEPARATORS:
            if current:
                segments.append(tuple(current))
                current = []
            continue
        current.append(token)
    if current:
        segments.append(tuple(current))
    return tuple(segments)


def _text_fetch_reasons(arguments: tuple[str, ...]) -> tuple[str, ...]:
    reasons: list[str] = []
    update_flag = next((argument for argument in arguments if argument in _UPDATE_HEAD_OK_FLAGS), None)
    if update_flag is not None:
        reasons.append(f"uses update-head-ok option {update_flag}")

    remote_seen = False
    for argument in arguments:
        if not remote_seen:
            if argument == "--" or not argument.startswith("-"):
                remote_seen = True
            continue
        if argument.startswith("-") or _URL_SCHEME_PATTERN.match(argument):
            continue
        if ":" not in argument:
            continue
        destination = argument.rsplit(":", maxsplit=1)[1].lstrip("+^")
        if not destination.startswith("refs/remotes/"):
            reasons.append(f"unsafe explicit destination {argument}")
    return tuple(reasons)


def _fetch_text_violations(path: Path) -> tuple[str, ...]:
    violations: list[str] = []
    for line_number, line in _logical_shell_lines(path.read_text(encoding="utf-8")):
        tokens = _shell_tokens(line)
        if tokens is None:
            if re.search(r"\bgit\b.*\bfetch\b", line):
                violations.append(f"fetch source could not tokenize command at line {line_number}")
            continue
        for segment in _shell_segments(tokens):
            fetch_index = _git_fetch_index(segment)
            if fetch_index is None:
                continue
            reasons = _text_fetch_reasons(segment[fetch_index + 1 :])
            if reasons:
                violations.append(f"fetch source contains unsafe command at line {line_number}: {'; '.join(reasons)}")
    return tuple(violations)


def _merge_method_violations(paths: tuple[Path, ...]) -> tuple[str, ...]:
    return tuple(
        f"{path.relative_to(_REPO_ROOT)}:{line_number}"
        for path in paths
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if _FORBIDDEN_FIELD_PATTERN.search(line)
    )


def _forbidden_capability_violations(paths: tuple[Path, ...]) -> tuple[str, ...]:
    return tuple(
        f"{path.relative_to(_REPO_ROOT)}:{line_number}"
        for path in paths
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if any(pattern.search(line) for pattern in _FORBIDDEN_CAPABILITY_PATTERNS)
    )


def _automation_governance_files() -> tuple[Path, ...]:
    delivery_roots = tuple(
        root for root in _SOURCE_ROOTS if root.parent.name in {"delivery", "delivery-mcp", "delivery-github"}
    )
    optional_agent_root = _REPO_ROOT / ".owlbear/agents"
    source_files = (
        path
        for root in (*delivery_roots, optional_agent_root)
        if root.is_dir()
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".md"}
    )
    return tuple(sorted({*_agent_files(), *source_files}))


def _automation_governance_violations(paths: tuple[Path, ...]) -> tuple[str, ...]:
    return tuple(
        f"{path.relative_to(_REPO_ROOT)}:{line_number}"
        for path in paths
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if _AUTOMATION_GOVERNANCE_PATTERN.search(line)
    )


def _git_admin_path_violations(paths: tuple[Path, ...]) -> tuple[str, ...]:
    return tuple(
        f"{path.relative_to(_REPO_ROOT)}:{line_number}"
        for path in paths
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if _FORBIDDEN_GIT_ADMIN_PATH_PATTERN.search(line)
    )


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


def test_github_provider_exposes_only_fixed_non_merge_operations() -> None:
    rest_violations = _provider_rest_violations(_GITHUB_PROVIDER_SOURCE)
    graphql_violations = _provider_graphql_violations(_GITHUB_PROVIDER_SOURCE)

    assert not rest_violations, "Unexpected GitHub REST provider operation:\n" + "\n".join(rest_violations)
    assert not graphql_violations, "Unexpected GitHub GraphQL provider operation:\n" + "\n".join(graphql_violations)


def test_forbidden_provider_fixture_is_rejected_by_the_provider_gate() -> None:
    fixture = _fixture_path("forbidden-provider.py")

    assert _provider_rest_violations(fixture)
    assert _provider_graphql_violations(fixture)


def test_delivery_fetch_vectors_are_remote_tracking_only() -> None:
    violations = tuple(
        f"{path.relative_to(_REPO_ROOT)}: {violation}"
        for path in _production_python_files()
        for violation in _fetch_violations(path)
    )
    text_violations = tuple(
        f"{path.relative_to(_REPO_ROOT)}: {violation}"
        for path in _production_command_files()
        for violation in _fetch_text_violations(path)
    )

    assert not violations + text_violations, "Unsafe Delivery fetch vector:\n" + "\n".join(violations + text_violations)


def test_command_inventory_excludes_vendored_sources() -> None:
    paths = _production_command_files()

    assert paths
    assert all("node_modules" not in path.parts for path in paths)


def test_forbidden_fetch_fixture_is_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_violations(_fixture_path("forbidden-fetch.py"))

    assert {
        int(violation.rsplit("line ", maxsplit=1)[1].split(":", maxsplit=1)[0])
        for violation in violations
        if "uses update-head-ok option" in violation
    } == {10, 23, 33}
    assert {
        int(violation.rsplit("line ", maxsplit=1)[1].split(":", maxsplit=1)[0])
        for violation in violations
        if "lacks an empty refmap" in violation
    } == {10, 19, 23, 33}
    assert {
        int(violation.rsplit("line ", maxsplit=1)[1].split(":", maxsplit=1)[0])
        for violation in violations
        if "unsafe explicit destination" in violation
    } == {10, 23, 33, 46}
    assert any("forwards unpacked arguments" in violation for violation in violations)


def test_forbidden_fetch_aliases_are_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_violations(_fixture_path("forbidden-fetch-aliases.py"))

    assert {
        int(violation.rsplit("line ", maxsplit=1)[1].split(":", maxsplit=1)[0])
        for violation in violations
        if "uses update-head-ok option" in violation
    } == {11, 18, 25, 31, 35, 52}
    assert {
        int(violation.rsplit("line ", maxsplit=1)[1].split(":", maxsplit=1)[0])
        for violation in violations
        if "unsafe explicit destination" in violation
    } == {11, 18, 25, 31, 35, 52}
    assert any("unstructured shell command" in violation for violation in violations)


def test_forbidden_keyword_fetch_refspec_is_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_violations(_fixture_path("forbidden-fetch-keyword.py"))

    assert len(violations) == 1
    assert "unsafe explicit destination" in violations[0]


def test_forbidden_boolean_fetch_keyword_is_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_violations(_fixture_path("forbidden-fetch-boolean.py"))

    assert len(violations) == 1
    assert "update-head-ok option" in violations[0]


def test_keyword_refspec_without_positional_remote_is_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_violations(_fixture_path("forbidden-fetch-keyword-only.py"))

    assert len(violations) == 1
    assert "unsafe explicit destination" in violations[0]


def test_forbidden_fetch_script_fixture_is_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_text_violations(_fixture_path("forbidden-fetch.sh"))

    assert len(violations) == 3
    assert {"3", "4", "5"} == {
        violation.split(":", maxsplit=1)[0].rsplit(" ", maxsplit=1)[-1] for violation in violations
    }
    assert sum("uses update-head-ok option" in violation for violation in violations) == 1
    assert sum("unsafe explicit destination" in violation for violation in violations) == 3


def test_valid_fetch_script_fixture_is_not_rejected_by_the_fetch_gate() -> None:
    assert not _fetch_text_violations(_fixture_path("valid-fetch.sh"))


def test_forbidden_folded_fetch_fixture_is_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_text_violations(_fixture_path("forbidden-fetch.yml"))

    assert len(violations) == 1
    assert "line 3" in violations[0]
    assert "uses update-head-ok option" in violations[0]
    assert "unsafe explicit destination" in violations[0]


def test_forbidden_inline_fetch_fixture_is_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_text_violations(_fixture_path("forbidden-fetch-inline.yml"))

    assert len(violations) == 1
    assert "line 3" in violations[0]
    assert "uses update-head-ok option" in violations[0]
    assert "unsafe explicit destination" in violations[0]


def test_forbidden_substitution_fetch_fixture_is_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_text_violations(_fixture_path("forbidden-fetch-substitution.sh"))

    assert len(violations) == 1
    assert "uses update-head-ok option" in violations[0]
    assert "unsafe explicit destination" in violations[0]


def test_malformed_fetch_fixture_fails_closed_in_the_text_gate() -> None:
    violations = _fetch_text_violations(_fixture_path("forbidden-fetch-malformed.txt"))

    assert len(violations) == 1
    assert "could not tokenize command" in violations[0]


def test_unknown_fetch_keyword_is_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_violations(_fixture_path("forbidden-fetch-unknown-keyword.py"))

    assert len(violations) == 1
    assert "unsafe explicit destination" in violations[0]


def test_unresolved_fetch_control_keyword_is_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_violations(_fixture_path("forbidden-fetch-unknown-control.py"))

    assert len(violations) == 1
    assert "unresolved update-head-ok option" in violations[0]


def test_forbidden_fetch_class_attributes_are_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_violations(_fixture_path("forbidden-fetch-class.py"))

    assert len(violations) == 1
    assert "refs/heads/main" in violations[0]


def test_forbidden_indirect_fetch_refspecs_are_rejected_by_the_fetch_gate() -> None:
    violations = _fetch_violations(_fixture_path("forbidden-fetch-dynamic.py"))

    assert {
        int(violation.rsplit("line ", maxsplit=1)[1].split(":", maxsplit=1)[0])
        for violation in violations
        if "unresolved explicit refspec" in violation
    } == {6, 10}


def test_fetch_url_remote_is_not_misclassified_as_a_refspec() -> None:
    assert not _fetch_violations(_fixture_path("valid-fetch-url.py"))


def test_fetch_resolution_is_isolated_to_each_function_scope() -> None:
    violations = _fetch_violations(_fixture_path("forbidden-fetch-scope.py"))

    assert len(violations) == 1
    assert "unsafe explicit destination" in violations[0]
    assert "refs/heads/main" in violations[0]


def test_delivery_models_have_no_merge_method_field() -> None:
    paths = _production_capability_files()

    assert not _merge_method_violations(paths)


def test_forbidden_merge_method_fixture_is_rejected_by_the_field_gate() -> None:
    violations = _merge_method_violations((_fixture_path("forbidden-fields.py"),))

    assert {int(violation.rsplit(":", maxsplit=1)[1]) for violation in violations} == {3, 4}


def test_cockpit_and_agents_expose_no_merge_control() -> None:
    assert not _forbidden_capability_violations(_production_capability_files())


def test_forbidden_cockpit_and_agent_fixtures_are_rejected_by_the_capability_gate() -> None:
    cockpit_fixture = _fixture_path("forbidden-cockpit.ts")
    agent_fixture = _fixture_path("forbidden-agent.agent.md")

    cockpit_violations = _forbidden_capability_violations((cockpit_fixture,))
    agent_violations = _forbidden_capability_violations((agent_fixture,))

    assert {int(violation.rsplit(":", maxsplit=1)[1]) for violation in cockpit_violations} == {2, 5}
    assert len(agent_violations) == 1


def test_delivery_automation_has_no_special_approval_or_risk_gate() -> None:
    assert not _automation_governance_violations(_automation_governance_files())


def test_delivery_automation_scan_covers_required_roots() -> None:
    paths = _automation_governance_files()
    required_roots = (
        _REPO_ROOT / "serve/delivery/src",
        _REPO_ROOT / "serve/delivery-mcp/src",
        _REPO_ROOT / "serve/delivery-github/src",
        _REPO_ROOT / "share/agents",
        _REPO_ROOT / "share/instructions",
        _REPO_ROOT / "share/prompts",
        _REPO_ROOT / "share/skills",
        _REPO_ROOT / ".owlbear/instructions",
        _REPO_ROOT / ".owlbear/prompts",
        _REPO_ROOT / ".owlbear/skills",
        _REPO_ROOT / ".github/skills",
    )

    assert all(any(path.is_relative_to(root) for path in paths) for root in required_roots)


def test_forbidden_automation_governance_fixture_is_rejected_by_the_gate() -> None:
    violations = _automation_governance_violations((_fixture_path("forbidden-automation-governance.md"),))

    assert {int(violation.rsplit(":", maxsplit=1)[1]) for violation in violations} == set(range(3, 15))


def test_valid_automation_governance_fixture_is_allowed_by_the_gate() -> None:
    assert not _automation_governance_violations((_fixture_path("valid-automation-governance.md"),))


def test_delivery_sources_have_no_git_admin_artifact_path() -> None:
    assert not _git_admin_path_violations(_production_capability_files())


def test_forbidden_git_admin_fixture_is_rejected_by_the_artifact_gate() -> None:
    violations = _git_admin_path_violations((_fixture_path("forbidden-git-admin.py"),))

    assert {int(violation.rsplit(":", maxsplit=1)[1]) for violation in violations} == {5, 9, 13, 17, 21, 25}
