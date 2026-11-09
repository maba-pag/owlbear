"""Current imports and named code consumers for unobserved CI dependency blocks."""

from __future__ import annotations

import ast
import posixpath
import re
from collections import defaultdict
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from testmon.process_code import Module, bytes_to_string_and_fsha, methods_to_checksums

from owlbear_tools.test_dependencies import is_test_module
from owlbear_tools.test_symbols import (
    _definitions,
    _names,
    fixture_registry,
    http_get,
    reference_map,
    resource_aliases,
    resource_path,
    resource_reads,
    resource_scope,
)


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


def _navigation_route(argument: ast.expr) -> str | None:
    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
        text = argument.value
    elif isinstance(argument, ast.JoinedStr):
        text = ""
        for index, part in enumerate(argument.values):
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                text += part.value
            elif index and "?" not in text and "#" not in text:
                return None
    else:
        return None
    path = urlsplit(text).path
    return re.sub(r"^/p/[^/]*(?=/|$)", "", path) or ("/" if path else None)


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
        self.fixtures = {
            path: metadata
            for path, metadata in fixture_registry(self.trees, self.bindings).items()
            if metadata[0] or Path(path).name == "conftest.py" or path in self.tests
        }
        self.references = {
            name: reference_map(definitions, self.fixtures.get(name, (set(), set()))[0])
            for name, definitions in self.definitions.items()
        }
        self.local_symbols = {
            path: set().union(self.definitions[path], self.fixtures.get(path, (set(), set()))[0], *references.values())
            for path, references in self.references.items()
        }
        for path, (fixtures, autouse) in self.fixtures.items():
            for test in self.tests:
                if (
                    test == path or (Path(path).name == "conftest.py" and Path(test).is_relative_to(Path(path).parent))
                ) and (autouse or fixtures & _names(self.trees[test])):
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
                if "/src/" not in caller and caller not in found:
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
                    if f"{local}.*" in self.local_symbols.get(caller, set()):
                        names.add(f"{local}.*")
                elif symbol == "*":
                    names.add(local)
                    names.update(affected)
                elif symbol in affected:
                    names.add(local)
        if dependency != caller and dependency in self.fixtures and caller in self.tests:
            names.update(self._fixture_dependents(caller, dependency, affected))
        return names

    def _fixture_dependents(self, caller: str, dependency: str, affected: set[str]) -> set[str]:
        fixtures, autouse = self.fixtures[dependency]
        implicit = Path(dependency).name == "conftest.py" and Path(caller).is_relative_to(Path(dependency).parent)
        imported = {
            symbol
            for local, choices in self.bindings[caller].items()
            if isinstance(self.definitions[caller].get(local), (ast.Import, ast.ImportFrom))
            for module, symbol in choices
            if module == dependency
        }
        names = affected & fixtures if implicit else set()
        if autouse & affected and (implicit or imported & autouse or "*" in imported):
            names.update(symbol for symbol in self.definitions[caller] if symbol.rsplit(".", 1)[-1].startswith("test_"))
        return names

    def _local_names(self, caller: str, names: set[str]) -> set[str]:
        names &= self.local_symbols.get(caller, set())
        while True:
            fixtures, autouse = self.fixtures.get(caller, (set(), set()))
            additions = {
                symbol
                for symbol, references in self.references.get(caller, {}).items()
                if references & names
                or any(
                    ".".join(parts[:end]) in names
                    for reference in references
                    for parts in [reference.split(".")]
                    for end in range(1, len(parts))
                )
                or any(
                    not scope or symbol.startswith(f"{scope}.")
                    for fixture in names & fixtures
                    for scope in [fixture.rpartition(".")[0]]
                    if fixture.rsplit(".", 1)[-1] in references
                    or (fixture in autouse and symbol.rsplit(".", 1)[-1].startswith("test_"))
                )
            } - names
            if not additions:
                return names
            names.update(additions)

    def block_hashes(self, path: str, symbols: set[str]) -> set[int]:
        """Native integer checksums of the named functions, never the unknown/global block."""
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
            if symbol in symbols or symbol.split(".", 1)[0] in symbols or "pytestmark" in symbols
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

    def resource_readers(self, resource: str) -> dict[str, set[str]]:
        """Owned runtime readers, not temporary test corpora sharing a filename suffix."""
        affected: dict[str, set[str]] = defaultdict(set)
        aliases: dict[str, set[str]] = defaultdict(set)
        for path, definitions in self.references.items():
            scope = self.definitions[path]
            symbols = {
                symbol
                for symbol, references in definitions.items()
                if resource in references
                or any(
                    (pattern := resource_path(node, path, self.modules, resource_scope(scope[symbol], scope), scope))
                    is not None
                    and pattern.startswith(resource.split("/src/", 1)[0] + "/src/")
                    and PurePosixPath(resource).full_match(pattern)
                    for node in ast.walk(self.definitions[path][symbol])
                    if isinstance(node, (ast.Call, ast.BinOp))
                )
            }
            if symbols:
                affected[path].update(self.affected(path, symbols).get(path, set()))
                aliases[path].update(
                    symbol
                    for symbol in symbols
                    if isinstance(self.definitions[path].get(symbol), (ast.Assign, ast.AnnAssign))
                )
        for path, names in aliases.items():
            aliases[path] = resource_aliases(self.definitions.get(path, {}), names)
        pending = [path for path, names in aliases.items() if names]
        while pending:
            dependency = pending.pop()
            for caller in self.reverse.get(dependency, set()):
                names = self._dependent_names(caller, dependency, aliases[dependency])
                names &= self.local_symbols.get(caller, set())
                names = resource_aliases(self.definitions.get(caller, {}), names | aliases[caller])
                if names - aliases[caller]:
                    aliases[caller].update(names)
                    pending.append(caller)
                if reads := resource_reads(self.definitions.get(caller, {}), names):
                    affected[caller].update(reads)
        if not affected:
            msg = f"No current runtime-resource readers resolved for {resource} in {self.root}"
            raise RuntimeError(msg)
        return dict(affected)

    def outside_nodes(self, paths: set[str], candidates: set[str], *, required: bool = True) -> set[str]:
        """Named page, source-reader and child-process consumers supplied by the ordinary router."""
        if required and len(paths) > 1:
            for page in sorted(path for path in paths if "/web/" in path):
                self.outside_nodes({page}, candidates)
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
        helpers = {
            path for path in self.trees if path not in self.tests and ("/tests/" in path or path.startswith("tests/"))
        }
        for test in candidates | self.fixtures.keys() | helpers:
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
                computed = any(
                    re.search(
                        "".join(
                            re.escape(part.value) if isinstance(part, ast.Constant) else ".*" for part in node.values
                        ),
                        label,
                    )
                    for expression in ast.walk(definition)
                    if (isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Div))
                    or (
                        isinstance(expression, ast.Call)
                        and (
                            (
                                isinstance(expression.func, ast.Name)
                                and expression.func.id in {"Path", "PurePath", "open"}
                            )
                            or (
                                isinstance(expression.func, ast.Attribute)
                                and expression.func.attr
                                in {"joinpath", "read_text", "read_bytes", "open", "glob", "rglob"}
                            )
                        )
                    )
                    for node in ast.walk(expression)
                    if isinstance(node, ast.JoinedStr)
                    and any(
                        isinstance(part, ast.Constant)
                        and isinstance(part.value, str)
                        and any(suffix and suffix in part.value for suffix in suffixes)
                        for part in node.values
                    )
                    for label in labels
                )
                wildcard = globs and (
                    any(f"*{suffix}" in literal for suffix in suffixes for literal in literals)
                    or ("*" in literals and bool(suffixes & literals))
                )
                child = subprocess and any(namespace in literal for namespace in namespaces for literal in literals)
                navigates = bool(routes) and any(
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and (
                        node.func.attr in {"goto", "wait_for_url", "to_have_url"}
                        or http_get(node, definition, self.trees[test])
                    )
                    and node.args
                    and ((route := _navigation_route(node.args[0])) is None or route in routes)
                    for node in ast.walk(definition)
                )
                if named or computed or wildcard or child or navigates:
                    symbols.add(symbol)
            if symbols:
                selected.update(self.test_nodes(self.affected(test, symbols)))
        if required and pages and not selected:
            msg = f"No current file-reading/page/import consumers resolved for task paths {sorted(pages)}"
            raise RuntimeError(msg)
        return selected
