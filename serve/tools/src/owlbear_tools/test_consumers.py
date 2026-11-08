"""Current imports and named code consumers for unobserved CI dependency blocks."""

from __future__ import annotations

import ast
import posixpath
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from testmon.process_code import Module, bytes_to_string_and_fsha, methods_to_checksums

from owlbear_tools.test_dependencies import is_test_module


def fixture_names(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Fixture identities, including those applied without an explicit request."""
    fixtures, autouse = set(), set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            called = decorator.func if isinstance(decorator, ast.Call) else decorator
            if (isinstance(called, ast.Attribute) and called.attr == "fixture") or (
                isinstance(called, ast.Name) and called.id == "fixture"
            ):
                fixtures.add(node.name)
                if isinstance(decorator, ast.Call) and any(
                    keyword.arg == "autouse" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                    for keyword in decorator.keywords
                ):
                    autouse.add(node.name)
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


def changed_symbols(before: Module | None, current: Module | None) -> set[str]:
    """Names whose definitions changed, rather than every import-time module footprint."""
    old = _definitions(ast.parse(before.source_code)) if before is not None else {}
    new = _definitions(ast.parse(current.source_code)) if current is not None else {}
    return {
        name
        for name in old.keys() | new.keys()
        if name not in old
        or name not in new
        or ast.dump(old[name], include_attributes=False) != ast.dump(new[name], include_attributes=False)
    }


def _asset_reference(path: str, literal: str) -> str | None:
    reference = literal.split("?", 1)[0]
    web = path.split("/web/", 1)[0] + "/web"
    for kind, directory in (("lit-html", "vendor/lit-html"), ("pds", "pds")):
        prefix = f"/assets/{kind}/"
        if reference.startswith(prefix):
            return f"{web}/{directory}/" + reference.removeprefix(prefix).split("/", 1)[1]
    for prefix, replacement in (("/assets/page/", f"{web}/pages/"), ("/assets/", f"{web}/")):
        if reference.startswith(prefix):
            return replacement + reference.removeprefix(prefix)
    return posixpath.normpath(str(Path(path).parent / reference)) if reference.startswith(".") else None


class _Consumers:
    """Real imports, named uses and requested/autouse conftest fixtures."""

    def __init__(self, root: Path, files: set[str]) -> None:
        self.root, self.files = root, files
        self.texts = {
            name: bytes_to_string_and_fsha((root / name).read_bytes())[0]
            for name in files
            if name.endswith(".py")
            and (root / name).is_file()
            and (name.startswith(("serve/", "tests/")) or name == "conftest.py")
        }
        self.trees = {name: ast.parse(text, filename=name) for name, text in self.texts.items()}
        self.tests = {name for name in self.texts if is_test_module(name)}
        self.reverse: dict[str, set[str]] = defaultdict(set)
        self.modules: dict[str, set[str]] = defaultdict(set)
        self.identities: dict[str, str] = {}
        for name in (path for path in files if path.endswith(".py")):
            parts = Path(name).with_suffix("").parts
            parts = parts[parts.index("src") + 1 :] if "src" in parts else parts
            identity = ".".join(parts).removesuffix(".__init__")
            self.identities[name] = identity
            self.modules[identity].add(name)
            if "/tests/" in name or name.startswith("tests/"):
                self.modules[Path(name).stem].add(name)
        self.bindings = {name: self._bindings(name, tree) for name, tree in self.trees.items()}
        self.definitions = {name: _definitions(tree) for name, tree in self.trees.items()}
        self.references = {
            name: {symbol: _names(node) for symbol, node in definitions.items()}
            for name, definitions in self.definitions.items()
        }
        self.fixtures = {
            path: fixture_names(tree) for path, tree in self.trees.items() if Path(path).name == "conftest.py"
        }
        for path, (fixtures, autouse) in self.fixtures.items():
            for test in self.tests:
                if Path(test).is_relative_to(Path(path).parent) and (autouse or fixtures & _names(self.trees[test])):
                    self.reverse[path].add(test)

    def _choices(self, name: str, caller: str) -> set[str]:
        choices = self.modules.get(name, set())
        local = {path for path in choices if Path(path).parent == Path(caller).parent}
        return local or choices

    def _bindings(self, path: str, tree: ast.AST) -> dict[str, set[tuple[str, str]]]:
        bindings: dict[str, set[tuple[str, str]]] = defaultdict(set)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for local, dependency, symbol in self._import_bindings(path, node):
                    bindings[local].add((dependency, symbol))
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "import_module"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                for dependency in self._choices(node.args[0].value, path):
                    bindings[node.args[0].value].add((dependency, "*"))
        for choices in bindings.values():
            for dependency, _ in choices:
                if dependency != path:
                    self.reverse[dependency].add(path)
        return bindings

    def _import_bindings(self, path: str, node: ast.Import | ast.ImportFrom) -> list[tuple[str, str, str]]:
        found: list[tuple[str, str, str]] = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.extend(
                    (alias.asname or alias.name, dependency, "") for dependency in self._choices(alias.name, path)
                )
            return found
        identity = self.identities[path]
        package = identity if Path(path).name == "__init__.py" else identity.rsplit(".", 1)[0]
        prefix = package.split(".")[: 1 - node.level or None] if node.level else []
        module = ".".join([*prefix, node.module or ""]).strip(".")
        for alias in node.names:
            submodules = self._choices(f"{module}.{alias.name}", path)
            found.extend(
                (alias.asname or alias.name, dependency, "" if submodules else alias.name)
                for dependency in submodules or self._choices(module, path)
            )
        return found

    def callers(self, paths: set[str]) -> set[str]:
        found, pending = set(paths), list(paths)
        while pending:
            for caller in self.reverse.get(pending.pop(), set()):
                if "/src/" in caller and caller not in found:
                    found.add(caller)
                    pending.append(caller)
        return found

    def tests_for(self, paths: set[str]) -> set[str]:
        found, pending, tests = set(paths), list(paths), set()
        while pending:
            for caller in self.reverse.get(pending.pop(), set()):
                if caller in self.tests:
                    tests.add(caller)
                elif "/src/" not in caller and caller not in found:
                    found.add(caller)
                    pending.append(caller)
        return tests

    def affected(self, source: str, symbols: set[str]) -> dict[str, set[str]]:
        """Propagate named uses, not the incidental global block shared by all importers."""
        affected: dict[str, set[str]] = defaultdict(set)
        affected[source].update(symbols)
        pending = [source]
        while pending:
            dependency = pending.pop()
            for caller in {dependency, *self.reverse.get(dependency, set())}:
                names = set(affected[caller]) | self._dependent_names(caller, dependency, affected[dependency])
                names = self._local_names(caller, names)
                if names - affected[caller]:
                    affected[caller].update(names)
                    pending.append(caller)
        return dict(affected)

    def _dependent_names(self, caller: str, dependency: str, affected: set[str]) -> set[str]:
        names: set[str] = set()
        for local, choices in self.bindings.get(caller, {}).items():
            for imported, symbol in choices:
                if imported != dependency:
                    continue
                if not symbol:
                    names.update(f"{local}.{name}" for name in affected)
                elif symbol == "*":
                    names.add(local)
                    names.update(affected)
                elif symbol in affected:
                    names.add(local)
        if dependency in self.fixtures and caller in self.tests:
            fixtures, autouse = self.fixtures[dependency]
            if autouse & affected:
                names.update(self.definitions[caller])
            names.update(affected & fixtures)
        return names

    def _local_names(self, caller: str, names: set[str]) -> set[str]:
        while True:
            additions = {
                symbol
                for symbol, references in self.references.get(caller, {}).items()
                if references & names
                or any(reference.startswith(f"{name}.") for reference in references for name in names)
            } - names
            if not additions:
                return names
            names.update(additions)

    def block_hashes(self, path: str, symbols: set[str], module: Module | None = None) -> set[int]:
        """Native integer checksums of the named functions, never the unknown/global block."""
        if module is None:
            module = Module(source_code=self.texts[path]) if path in self.texts else None
        if module is None:
            return set()
        names = {symbol.rsplit(".", 1)[-1] for symbol in symbols}
        names.update(
            symbol.rsplit(".", 1)[-1] for symbol in self.definitions.get(path, {}) if symbol.split(".", 1)[0] in symbols
        )
        checksums = methods_to_checksums([block.checksum for block in module.blocks])
        return {
            checksum
            for block, checksum in zip(module.blocks, checksums, strict=True)
            if block.name in names and block.name not in {"unknown", "<module>"}
        }

    def test_nodes(self, affected: dict[str, set[str]]) -> set[str]:
        """Function selectors also retain parametrizations absent from Linux observations."""
        return {
            f"{path}::{symbol.replace('.', '::')}"
            for path, symbols in affected.items()
            if path in self.tests
            for symbol in self.definitions[path]
            if symbol in symbols or symbol.split(".", 1)[0] in symbols
            if symbol.rsplit(".", 1)[-1].startswith("test_")
            and isinstance(self.definitions[path][symbol], (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def platform_nodes(self, paths: set[str], affected: dict[str, set[str]] | None = None) -> set[str]:
        """Platform/skip code in individual tests and the helpers/fixtures those tests use."""
        nodes: set[str] = set()
        for path in paths:
            definitions = self.definitions.get(path, {})
            symbols = {
                symbol
                for symbol, definition in definitions.items()
                if affected is None or symbol in affected.get(path, set())
                if any(
                    name in {"sys.platform", "platform.system", "os.name", "pytest.mark.skip", "pytest.mark.skipif"}
                    for name in _names(definition)
                )
            }
            if "pytestmark" in symbols:
                symbols.update(definitions)
            if symbols:
                nodes.update(self.test_nodes(self.affected(path, symbols)))
        return nodes

    def page_routes(self, paths: set[str]) -> set[str]:
        """Served pages reached by changed assets through their actual relative imports."""
        changed = {path for path in paths if "/web/" in path}
        if not changed:
            return set()
        pages: dict[str, str] = {}
        for path, definitions in self.definitions.items():
            definition = definitions.get("PAGES")
            if path.endswith("/project_host/pages.py") and isinstance(definition, (ast.Assign, ast.AnnAssign)):
                web = Path(path).parent.parent / "web"
                for route, _title, name in ast.literal_eval(definition.value):
                    pages[str(web / name)] = route
        roots = {str(Path(page).parent) for page in pages}
        assets = {
            path: (self.root / path).read_text(encoding="utf-8")
            for path in self.files
            if any(path.startswith(f"{root}/") for root in roots)
            and Path(path).suffix in {".html", ".mjs", ".js", ".css"}
            and (self.root / path).is_file()
        }
        reverse: dict[str, set[str]] = defaultdict(set)
        for path, text in assets.items():
            web = path.split("/web/", 1)[0] + "/web"
            references = re.findall(
                r"""(?:from\s+|import\s*(?:\(\s*)?|(?:src|href)\s*=\s*|url\(\s*)['"]([^'"]+)""", text
            )
            for dependency in filter(None, (_asset_reference(path, reference) for reference in references)):
                reverse[dependency].add(path)
            for marker, dependency in (
                ("<!-- base -->", "base.css"),
                ("<!-- ask -->", "ask.js"),
                ("<!-- tabs -->", "pages/menu/menu.mjs"),
            ):
                if marker in text:
                    reverse[f"{web}/{dependency}"].add(path)
        reached, pending = set(changed), set(changed)
        while pending:
            callers = set().union(*(reverse[path] for path in pending)) - reached
            reached.update(callers)
            pending = callers
        return {
            route
            for page, route in pages.items()
            if page in reached
            or any(path.startswith(f"{Path(page).parent}/pages/{Path(page).stem}/") for path in changed)
        }

    def outside_nodes(self, paths: set[str], candidates: set[str]) -> set[str]:
        """Named page, source-reader and child-process consumers supplied by the ordinary router."""
        python = {path for path in paths if path.endswith(".py")}
        pages = paths - python
        routes = self.page_routes(pages)
        labels = set(paths) | {Path(path).name for path in paths}
        labels.update(f"/{Path(path).stem}" for path in pages)
        modules = {
            self.identities[path] for path in self.callers(python) if path in self.identities and "/src/" in path
        }
        namespaces = {module.split(".", 1)[0] for module in modules}
        suffixes = {Path(path).suffix for path in paths}
        selected: set[str] = set()
        for test in candidates | self.fixtures.keys():
            definitions = self.definitions.get(test, {})
            symbols: set[str] = set()
            references = _names(self.trees[test]) if test in self.trees else set()
            globs = (
                any(
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"glob", "rglob"}
                    for node in ast.walk(self.trees[test])
                )
                if test in self.trees
                else False
            )
            subprocess = "sys.executable" in references and bool(
                references & {"subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_output"}
            )
            for symbol, definition in definitions.items():
                literals = {
                    node.value
                    for node in ast.walk(definition)
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)
                }
                named = any(
                    label in literal for label in labels for literal in literals if "/" in label or "." in label
                )
                wildcard = globs and any(f"*{suffix}" in literal for suffix in suffixes for literal in literals)
                child = subprocess and any(namespace in literal for namespace in namespaces for literal in literals)
                navigates = any(
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"goto", "get"}
                    and node.args
                    and urlsplit(
                        "".join(
                            item.value
                            for item in ast.walk(node.args[0])
                            if isinstance(item, ast.Constant) and isinstance(item.value, str)
                        )
                        or "/"
                    ).path
                    in routes
                    for node in ast.walk(definition)
                )
                if named or wildcard or child or navigates:
                    symbols.add(symbol)
            if symbols:
                selected.update(self.test_nodes(self.affected(test, symbols)))
        if pages and not selected:
            msg = f"No current page/import consumers resolved for task paths {sorted(pages)}"
            raise RuntimeError(msg)
        return selected
