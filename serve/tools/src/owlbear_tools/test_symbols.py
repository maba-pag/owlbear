"""Python definitions, references and fixture identities for current test consumers."""

from __future__ import annotations

import ast
from pathlib import PurePosixPath


def fixture_names(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Fixture identities, including those applied without an explicit request."""
    aliases = {
        alias.asname or alias.name
        for node in getattr(tree, "body", [])
        if isinstance(node, ast.ImportFrom) and node.module == "pytest"
        for alias in node.names
        if alias.name == "fixture"
    }
    fixtures, autouse = set(), set()
    for symbol, node in _definitions(tree).items():
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            called = decorator.func if isinstance(decorator, ast.Call) else decorator
            if (isinstance(called, ast.Attribute) and called.attr == "fixture") or (
                isinstance(called, ast.Name) and called.id in {"fixture", *aliases}
            ):
                fixtures.add(symbol)
                if isinstance(decorator, ast.Call) and any(
                    keyword.arg == "autouse" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                    for keyword in decorator.keywords
                ):
                    autouse.add(symbol)
    return fixtures, autouse


def fixture_registry(
    trees: dict[str, ast.Module], bindings: dict[str, dict[str, set[tuple[str, str]]]]
) -> dict[str, tuple[set[str], set[str]]]:
    """Resolve current imported fixture identities, including re-exported autouse metadata."""
    registry = {path: fixture_names(tree) for path, tree in trees.items()}
    while True:
        size = sum(len(names) for pair in registry.values() for names in pair)
        for path, imports in bindings.items():
            definitions = _definitions(trees[path])
            for local, choices in imports.items():
                if not isinstance(definitions.get(local), (ast.Import, ast.ImportFrom)):
                    continue
                for dependency, symbol in choices:
                    for target, names in zip(registry[path], registry.get(dependency, (set(), set())), strict=True):
                        if symbol == "*":
                            target.update(names)
                        elif symbol in names:
                            target.add(local)
        if size == sum(len(names) for pair in registry.values() for names in pair):
            return registry


def _names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            names.add(item.id)
        elif isinstance(item, ast.arg):
            names.add(item.arg)
        elif isinstance(item, ast.Attribute):
            parts = [item.attr]
            value = item.value
            while isinstance(value, ast.Attribute):
                parts.append(value.attr)
                value = value.value
            if isinstance(value, ast.Name):
                names.add(".".join([value.id, *reversed(parts)]))
        elif isinstance(item, ast.Constant) and isinstance(item.value, str):
            names.add(item.value)  # Includes usefixtures/getfixturevalue requests.
        elif (
            isinstance(item, ast.Call)
            and isinstance(item.func, ast.Name)
            and item.func.id in {"getattr", "hasattr", "vars"}
            and item.args
            and (item.func.id == "vars" or item.args[1:])
            and isinstance(item.args[0], (ast.Name, ast.Attribute))
        ):
            attribute = None if item.func.id == "vars" else item.args[1]
            name = attribute.value if isinstance(attribute, ast.Constant) and isinstance(attribute.value, str) else "*"
            names.add(f"{ast.unparse(item.args[0])}.{name}")
    return names


def _definitions(tree: ast.AST) -> dict[str, ast.AST]:
    definitions: dict[str, ast.AST] = {}
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions[node.name] = node
            if isinstance(node, ast.ClassDef):
                definitions.update(
                    (f"{node.name}.{item.name}", item)
                    for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                definitions.update((item.id, node) for item in ast.walk(target) if isinstance(item, ast.Name))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            definitions.update((alias.asname or alias.name.split(".")[0], node) for alias in node.names)
    return definitions


def _http_constructors(tree: ast.AST) -> set[str]:
    constructors: set[str] = set()
    kinds = {"TestClient", "Client", "AsyncClient", "Session"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            ("httpx", "requests", "fastapi.testclient", "starlette.testclient")
        ):
            constructors.update(alias.asname or alias.name for alias in node.names if alias.name in kinds)
        elif isinstance(node, ast.Import):
            constructors.update(
                f"{alias.asname or alias.name}.{kind}"
                for alias in node.names
                if alias.name in {"httpx", "requests"}
                for kind in kinds
            )
    return constructors


def resource_aliases(definitions: dict[str, ast.AST], names: set[str]) -> set[str]:
    """Transport path aliases through direct assignments, not dependent functions or classes."""
    aliases = set(names)
    while True:
        additions = {
            symbol
            for symbol, node in definitions.items()
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            and isinstance(node.value, (ast.Name, ast.Attribute))
            and ast.unparse(node.value) in aliases
        }
        if not additions - aliases:
            return aliases
        aliases.update(additions)


def resource_reads(definitions: dict[str, ast.AST], aliases: set[str]) -> set[str]:
    """Individual functions reading an exact resolved path alias."""
    references = reference_map(definitions, set())
    return {
        symbol
        for symbol, definition in definitions.items()
        if isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef))
        for owned in [aliases & references[symbol]]
        if any(
            isinstance(node, ast.Call)
            and (
                (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"read_text", "read_bytes", "open"}
                    and ast.unparse(node.func.value) in owned
                )
                or (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "open"
                    and node.args
                    and ast.unparse(node.args[0]) in owned
                )
            )
            for node in ast.walk(definition)
        )
    }


def resource_path(
    node: ast.AST,
    source: str,
    modules: dict[str, set[str]],
    definitions: dict[str, ast.AST],
    module_bindings: dict[str, ast.AST],
) -> str | None:
    """Resolve literal source/package-relative paths without consulting the filesystem."""
    if isinstance(node, ast.Name) and node.id == "__file__":
        return source
    if (
        definitions
        and isinstance(node, ast.Name)
        and isinstance(definition := definitions.get(node.id), (ast.Assign, ast.AnnAssign))
    ):
        value = definition.value
        if (
            isinstance(definition, ast.Assign)
            and len(definition.targets) == 1
            and isinstance(definition.targets[0], (ast.Tuple, ast.List))
            and isinstance(value, (ast.Tuple, ast.List))
        ):
            value = next(
                (
                    item
                    for target, item in zip(definition.targets[0].elts, value.elts, strict=True)
                    if isinstance(target, ast.Name) and target.id == node.id
                ),
                None,
            )
        defining = module_bindings if module_bindings and module_bindings.get(node.id) is definition else definitions
        remaining = defining | {node.id: node}
        unvisited = {name: value for name, value in module_bindings.items() if value is not definition}
        return resource_path(value, source, modules, remaining, unvisited) if value is not None else None
    if isinstance(node, ast.JoinedStr):
        return _resource_template(node, source, modules, definitions, module_bindings)
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        return next(
            (
                path
                for value in node.values
                if (path := resource_path(value, source, modules, definitions, module_bindings)) is not None
            ),
            None,
        )
    return _resource_literal(node, source, modules, definitions, module_bindings)


def resource_scope(node: ast.AST, module: dict[str, ast.AST]) -> dict[str, ast.AST]:
    """Keep formal parameters from inheriting same-named module paths."""
    local = _definitions(node)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        local = {
            parameter.arg: parameter
            for parameter in ast.walk(node.args)
            if isinstance(parameter, ast.arg) and parameter.arg in module
        } | local
    return module | local


def reference_map(module: dict[str, ast.AST], fixtures: set[str]) -> dict[str, set[str]]:
    """Module references with lexical shadowing distinct from fixture injection."""
    return {symbol: _reference_names(node, module, fixtures) for symbol, node in module.items()}


def _reference_names(node: ast.AST, module: dict[str, ast.AST], fixtures: set[str]) -> set[str]:
    """Keep global dependencies separate from shadowing locals and fixture requests."""
    scope = resource_scope(node, module)
    declared = {name for item in ast.walk(node) if isinstance(item, ast.Global) for name in item.names}
    hidden = {name for name in module.keys() - fixtures - declared if scope.get(name) is not module[name]}
    return {name for name in _names(node) if name.split(".", 1)[0] not in hidden}


def _resource_template(
    node: ast.JoinedStr,
    source: str,
    modules: dict[str, set[str]],
    definitions: dict[str, ast.AST],
    module_bindings: dict[str, ast.AST],
) -> str | None:
    parts: list[str] = []
    for part in node.values:
        if isinstance(part, ast.Constant) and isinstance(part.value, str):
            parts.append(part.value)
        elif isinstance(part, ast.FormattedValue) and part.conversion == -1 and part.format_spec is None:
            value = resource_path(part.value, source, modules, definitions, module_bindings)
            if value is None and (not isinstance(part.value, ast.Name) or part.value.id in definitions):
                return None
            parts.append(value if value is not None else "*")
        else:
            return None
    return "".join(parts)


def _resource_literal(
    node: ast.AST,
    source: str,
    modules: dict[str, set[str]],
    definitions: dict[str, ast.AST],
    module_bindings: dict[str, ast.AST],
) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute) and node.attr == "parent":
        parent = resource_path(node.value, source, modules, definitions, module_bindings)
        return str(PurePosixPath(parent).parent) if parent is not None else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        parent = resource_path(node.left, source, modules, definitions, module_bindings)
        child = resource_path(node.right, source, modules, definitions, module_bindings)
        if child is None and isinstance(node.right, ast.Name) and node.right.id not in (definitions or {}):
            child = "*"
        return str(PurePosixPath(parent) / child) if parent is not None and child is not None else None
    if not isinstance(node, ast.Call):
        return None
    return _resource_call(node, source, modules, definitions, module_bindings)


def _resource_call(
    node: ast.Call,
    source: str,
    modules: dict[str, set[str]],
    definitions: dict[str, ast.AST],
    module_bindings: dict[str, ast.AST],
) -> str | None:
    if isinstance(node.func, ast.Name):
        return _resource_named_call(node, source, modules, definitions, module_bindings)
    if isinstance(node.func, ast.Attribute):
        parent = resource_path(node.func.value, source, modules, definitions, module_bindings)
        if parent is not None and node.func.attr == "joinpath":
            parts = [resource_path(arg, source, modules, definitions, module_bindings) for arg in node.args]
            return str(PurePosixPath(parent, *filter(None, parts))) if None not in parts else None
        if parent is not None and node.func.attr in {"read_text", "read_bytes", "open", "resolve"}:
            return parent
        if parent is not None and node.func.attr == "with_name" and node.args:
            name = resource_path(node.args[0], source, modules, definitions, module_bindings)
            return str(PurePosixPath(parent).with_name(name)) if name is not None else None
    return None


def _resource_named_call(
    node: ast.Call,
    source: str,
    modules: dict[str, set[str]],
    definitions: dict[str, ast.AST],
    module_bindings: dict[str, ast.AST],
) -> str | None:
    if not isinstance(node.func, ast.Name):
        return None
    name, args = node.func.id, node.args
    if definitions and isinstance(definition := definitions.get(name), (ast.FunctionDef, ast.AsyncFunctionDef)):
        returns = [statement.value for statement in definition.body if isinstance(statement, ast.Return)]
        defining = module_bindings if module_bindings and module_bindings.get(name) is definition else definitions
        remaining = defining | _definitions(definition)
        remaining.update(
            (parameter.arg, parameter) for parameter in ast.walk(definition.args) if isinstance(parameter, ast.arg)
        )
        del remaining[name]
        unvisited = {symbol: value for symbol, value in module_bindings.items() if value is not definition}
        if len(returns) == 1 and returns[0] is not None:
            return resource_path(returns[0], source, modules, remaining, unvisited)
    if name == "files" and args:
        package = resource_path(args[0], source, modules, definitions, module_bindings)
        roots = {
            str(PurePosixPath(path).parent)
            for path in modules.get(package or "", set())
            if path.endswith("/__init__.py")
        }
        return next(iter(roots)) if len(roots) == 1 else None
    if name == "str" and args:
        return resource_path(args[0], source, modules, definitions, module_bindings)
    if name in {"Path", "PurePath", "PurePosixPath"} and args:
        parts = [resource_path(arg, source, modules, definitions, module_bindings) for arg in args]
        return str(PurePosixPath(*filter(None, parts))) if None not in parts else None
    return None


def _http_response(call: ast.Call, definition: ast.AST) -> bool:
    properties = {"status_code", "headers", "text", "content", "json", "raise_for_status"}
    references = _names(definition)
    for node in ast.walk(definition):
        if isinstance(node, ast.Attribute) and node.value is call and node.attr in properties:
            return True
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is call:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(
                f"{name}.{attribute}" in references
                for target in targets
                for name in _names(target)
                for attribute in properties
            ):
                return True
    return False


def http_get(call: ast.Call, definition: ast.AST, tree: ast.AST) -> bool:
    """HTTP response use or a constructed HTTP client, never an arbitrary mapping's get."""
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "get":
        return False
    if _http_response(call, definition):
        return True
    constructors = _http_constructors(tree)
    receiver = call.func.value
    values: list[ast.expr | None] = [receiver]
    for node in ast.walk(definition):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(ast.unparse(target) == ast.unparse(receiver) for target in targets):
                values.append(node.value)
        elif (
            isinstance(node, ast.withitem)
            and node.optional_vars is not None
            and ast.unparse(node.optional_vars) == ast.unparse(receiver)
        ):
            values.append(node.context_expr)
    return any(isinstance(value, ast.Call) and ast.unparse(value.func) in constructors for value in values)
