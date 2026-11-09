"""Original workspace runner ownership, including uv options and Python module entries."""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path, PurePosixPath

from owlbear_delivery_next.change_flow import worktree

UV_SWITCHES = frozenset(
    {
        "--locked",
        "--frozen",
        "--offline",
        "--no-sync",
        "--no-project",
        "--no-config",
        "--quiet",
        "--verbose",
        "-q",
        "-v",
    }
)
PYTHON_SWITCHES = frozenset({"-I", "-S", "-s", "-E", "-B", "-O", "-OO", "-u", "-q", "-v", "-h", "-V"})


def _inline_python(rest: list[str]) -> bool:
    while rest:
        option = rest[0]
        if option in {"-c", "-"} or option.startswith("-c"):
            return True
        if option == "-m" or not option.startswith("-"):
            break
        if option in {"-W", "-X", "--check-hash-based-pycs"}:
            rest = rest[2:]
        elif option in PYTHON_SWITCHES or option.startswith(("-W", "-X")):
            rest = rest[1:]
        else:
            return True
    return False


def _inline_shell(rest: list[str]) -> bool:
    while rest:
        option = rest[0]
        if option == "--command" or (option.startswith("-") and not option.startswith("--") and "c" in option):
            return True
        if option in {"-o", "+o", "--rcfile", "--init-file"}:
            rest = rest[2:]
        elif (option.startswith("-") and not option.startswith("--")) or option in {
            "--noprofile",
            "--norc",
            "--noediting",
            "--restricted",
            "--posix",
            "--verbose",
        }:
            rest = rest[1:]
        elif option.startswith("-"):
            return True
        else:
            break
    return False


def _opaque_interpreter(words: list[str]) -> bool:
    for index, word in enumerate(words):
        name = PurePosixPath(word).name
        if re.fullmatch(r"python(?:\d+(?:\.\d+)*)?", name) and _inline_python(words[index + 1 :]):
            return True
        if name in {"sh", "bash", "zsh", "dash", "fish"} and _inline_shell(words[index + 1 :]):
            return True
    return False


def _uv_scripts(words: list[str]) -> set[str] | None:
    invoked: set[str] = set()
    for index, word in enumerate(words):
        if PurePosixPath(word).name != "uv":
            continue
        rest = words[index + 1 :]
        while rest and rest[0] in UV_SWITCHES:
            rest = rest[1:]
        if not rest or rest[0].startswith("-"):
            return None
        if rest[0] != "run":
            continue
        rest = rest[1:]
        while rest and rest[0] in UV_SWITCHES:
            rest = rest[1:]
        if rest and rest[0] == "--":
            rest = rest[1:]
        if not rest or rest[0].startswith("-") or rest[0] in {";", "&&", "||", "|"}:
            return None
        invoked.add(rest[0])
    return invoked


def console_script(path: str, words: list[str], source: Path) -> bool:
    """Names owned by the unchanged command; uncertain uv parsing conservatively holds every path."""
    invoked = _uv_scripts(words)
    if invoked is None or _opaque_interpreter(words):
        return True
    modules = {words[i + 1] for i in range(len(words) - 1) if words[i] == "-m"}
    if not invoked and not modules:
        return False
    manifests = worktree.git(source, "ls-files", "*pyproject.toml").splitlines()
    for name in manifests:
        manifest = source / name
        try:
            project = tomllib.loads(manifest.read_text(encoding="utf-8")).get("project", {})
        except tomllib.TOMLDecodeError as error:
            error.add_note(f"unchanged check manifest: {manifest}")
            raise
        for command, target in project.get("scripts", {}).items():
            module = target.split(":", 1)[0]
            if command not in invoked and module not in modules:
                continue
            package = manifest.parent.relative_to(source)
            filename = module.replace(".", "/") + ".py"
            for relative in (package / "src" / filename, package / filename):
                if relative.as_posix() == path:
                    return True
            if module == "owlbear_tools.testing" and path in _selector_inputs(source, package, module):
                return True
    return False


def _selector_inputs(source: Path, package: Path, entry: str) -> set[str]:
    found: set[str] = set()
    seen: set[str] = set()
    pending = [entry]
    while pending:
        module = pending.pop()
        if module in seen or not (module == "owlbear_tools" or module.startswith("owlbear_tools.")):
            continue
        seen.add(module)
        name = module.replace(".", "/")
        for root in (source / package / "src", source / package):
            for path in (root / f"{name}.py", root / name / "__init__.py"):
                found.add(path.relative_to(source).as_posix())
                if not path.is_file():
                    continue
                parent = module.split(".") if path.name == "__init__.py" else module.split(".")[:-1]
                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
                    if isinstance(node, ast.Import):
                        pending.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        prefix = parent[: len(parent) - node.level + 1] if node.level else []
                        imported = ".".join([*prefix, *([node.module] if node.module else [])])
                        pending.append(imported)
                        pending.extend(f"{imported}.{alias.name}" for alias in node.names if alias.name != "*")
    return found
