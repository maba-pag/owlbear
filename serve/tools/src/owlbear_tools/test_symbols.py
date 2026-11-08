"""Python definitions, references and fixture identities for current test consumers."""

from __future__ import annotations

import ast


def fixture_names(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Fixture identities, including those applied without an explicit request."""
    fixtures, autouse = set(), set()
    for symbol, node in _definitions(tree).items():
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            called = decorator.func if isinstance(decorator, ast.Call) else decorator
            if (isinstance(called, ast.Attribute) and called.attr == "fixture") or (
                isinstance(called, ast.Name) and called.id == "fixture"
            ):
                fixtures.add(symbol)
                if isinstance(decorator, ast.Call) and any(
                    keyword.arg == "autouse" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                    for keyword in decorator.keywords
                ):
                    autouse.add(symbol)
    return fixtures, autouse


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
            and item.func.id in {"getattr", "hasattr"}
            and item.args[1:]
            and isinstance(item.args[0], (ast.Name, ast.Attribute))
        ):
            attribute = item.args[1]
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
