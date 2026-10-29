"""TD-171, TD-173: each folder is one layer and imports only itself and the folders before it; the root holds only
``__init__.py`` and the ``__main__.py`` forwarder to the dispatcher."""

import ast
from importlib.resources import files
from pathlib import Path

ROOT = Path(str(files("owlbear_delivery_next")))
NAME = "owlbear_delivery_next"
ORDER = [
    "git", "github", "local_system", "change_contracts", "change_flow", "impeccable", "settings", "state_store",
    "improvement", "runtimes", "workflow_steps", "impeccable_runs", "project_host", "commands", "machine_host",
]  # fmt: skip
MODULES = {
    ".".join(p.relative_to(ROOT).with_suffix("").parts): p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts
}


def _layer(module: str) -> str:
    folder = module.split(".", maxsplit=1)[0]
    return folder if folder in ORDER else "commands"  # the root's forwarder starts the dispatcher, the top layer


def _imports(path: Path) -> set[str]:
    """The package modules a file imports, type-only imports included: they are dependencies too."""
    out = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(NAME):
            rest = node.module[len(NAME) :].lstrip(".")
            out |= {f"{rest}.{a.name}" if rest else a.name for a in node.names} | ({rest} if rest else set())
        elif isinstance(node, ast.Import):
            out |= {a.name[len(NAME) + 1 :] for a in node.names if a.name.startswith(f"{NAME}.")}
    return {m.removesuffix(".__init__") for m in out if m in MODULES or f"{m}.__init__" in MODULES}


def test_the_root_holds_only_the_package_and_its_forwarder() -> None:
    assert sorted(p.name for p in ROOT.glob("*.py")) == ["__init__.py", "__main__.py"]
    assert sorted(p.name for p in ROOT.iterdir() if p.is_dir() and p.name != "__pycache__") == sorted(
        [*ORDER, "agents", "skills", "web", "golden"]
    )


def test_each_layer_imports_only_itself_and_the_layers_before_it() -> None:
    upward = {
        (m, d) for m, path in MODULES.items() for d in _imports(path) if ORDER.index(_layer(d)) > ORDER.index(_layer(m))
    }
    assert sorted(upward) == []
