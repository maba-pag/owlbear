"""Project workspace scaffolding.

Orchestrates creation of new project directories with templates, git init,
kanban-md init, and registration in :class:`~owlbear.projects.store.ProjectStore`.

Usage::

    from owlbear.projects.workspace import ProjectWorkspace

    ws = ProjectWorkspace(project_root=Path("~/projects"), store=store)
    path = ws.create_project("my-app", "python-uv")
"""

from __future__ import annotations

import json
import logging
import subprocess
import textwrap
from typing import TYPE_CHECKING

from owlbear.projects.models import _slugify

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear.projects.store import ProjectStore

__all__ = ["ProjectWorkspace"]

logger = logging.getLogger(__name__)

# Valid template names
TEMPLATES = frozenset({"bare", "python-uv", "python-pip", "node"})

# ---------------------------------------------------------------------------
# Shared file content
# ---------------------------------------------------------------------------

_GITIGNORE_BASE = textwrap.dedent("""\
    # Python
    __pycache__/
    *.py[cod]
    *.egg-info/
    dist/
    build/
    .venv/
    .eggs/

    # IDE
    .vscode/
    .idea/

    # OS
    .DS_Store
    Thumbs.db

    # Kanban
    kanban/activity.jsonl
""")

_GITIGNORE_NODE_EXTRA = textwrap.dedent("""\

    # Node
    node_modules/
    dist/
    .env
""")


def _default_run_cmd(args: list[str]) -> None:
    """Run a subprocess command, raising on failure."""
    subprocess.run(args, check=True, capture_output=True)  # noqa: S603


# ---------------------------------------------------------------------------
# Template scaffolders
# ---------------------------------------------------------------------------


def _scaffold_bare(project_dir: Path, name: str) -> None:
    """Create minimal project files: README.md and .gitignore."""
    (project_dir / "README.md").write_text(
        f"# {name}\n\nCreated by OwlBear.\n",
        encoding="utf-8",
    )
    (project_dir / ".gitignore").write_text(_GITIGNORE_BASE, encoding="utf-8")


def _scaffold_python_uv(project_dir: Path, name: str) -> None:
    """Scaffold a Python project with uv/hatchling layout."""
    _scaffold_bare(project_dir, name)

    slug = _slugify(name)
    pkg_name = slug.replace("-", "_")

    # pyproject.toml — uv-compatible with hatchling backend
    pyproject = textwrap.dedent(f"""\
        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"

        [project]
        name = "{slug}"
        version = "0.1.0"
        description = ""
        requires-python = ">=3.12"
        dependencies = []

        [tool.hatch.build.targets.wheel]
        packages = ["src/{pkg_name}"]
    """)
    (project_dir / "pyproject.toml").write_text(pyproject, encoding="utf-8")

    # Source package: src/{pkg_name}/__init__.py
    src_pkg = project_dir / "src" / pkg_name
    src_pkg.mkdir(parents=True)
    (src_pkg / "__init__.py").write_text(f'"""Top-level package for {name}."""\n', encoding="utf-8")

    # Test directory
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")

    # .python-version
    (project_dir / ".python-version").write_text("3.12\n", encoding="utf-8")


def _scaffold_python_pip(project_dir: Path, name: str) -> None:
    """Scaffold a Python project with setuptools/pip layout."""
    _scaffold_bare(project_dir, name)

    slug = _slugify(name)
    pkg_name = slug.replace("-", "_")

    # pyproject.toml — pip-style with setuptools
    pyproject = textwrap.dedent(f"""\
        [build-system]
        requires = ["setuptools>=68.0", "wheel"]
        build-backend = "setuptools.build_meta"

        [project]
        name = "{slug}"
        version = "0.1.0"
        description = ""
        requires-python = ">=3.12"
        dependencies = []

        [tool.setuptools.packages.find]
        where = ["src"]
    """)
    (project_dir / "pyproject.toml").write_text(pyproject, encoding="utf-8")

    # requirements.txt
    (project_dir / "requirements.txt").write_text(
        "# Add project dependencies here\n", encoding="utf-8"
    )

    # Source package: src/{pkg_name}/__init__.py
    src_pkg = project_dir / "src" / pkg_name
    src_pkg.mkdir(parents=True)
    (src_pkg / "__init__.py").write_text(f'"""Top-level package for {name}."""\n', encoding="utf-8")

    # Test directory: tests/__init__.py
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")


def _scaffold_node(project_dir: Path, name: str) -> None:
    """Scaffold a Node.js/TypeScript project."""
    _scaffold_bare(project_dir, name)

    slug = _slugify(name)

    # Append node-specific gitignore entries
    gitignore_path = project_dir / ".gitignore"
    existing = gitignore_path.read_text(encoding="utf-8")
    gitignore_path.write_text(existing + _GITIGNORE_NODE_EXTRA, encoding="utf-8")

    # package.json
    package = {
        "name": slug,
        "version": "0.1.0",
        "description": "",
        "main": "src/index.ts",
        "scripts": {
            "build": "tsc",
            "start": "node dist/index.js",
        },
        "keywords": [],
        "license": "ISC",
    }
    (project_dir / "package.json").write_text(
        json.dumps(package, indent=2) + "\n", encoding="utf-8"
    )

    # src/
    (project_dir / "src").mkdir()

    # tsconfig.json
    tsconfig = {
        "compilerOptions": {
            "target": "ES2022",
            "module": "Node16",
            "moduleResolution": "Node16",
            "outDir": "dist",
            "rootDir": "src",
            "strict": True,
            "esModuleInterop": True,
            "skipLibCheck": True,
        },
        "include": ["src"],
    }
    (project_dir / "tsconfig.json").write_text(
        json.dumps(tsconfig, indent=2) + "\n", encoding="utf-8"
    )


# Template dispatch table
_SCAFFOLDERS: dict[str, Callable[[Path, str], None]] = {
    "bare": _scaffold_bare,
    "python-uv": _scaffold_python_uv,
    "python-pip": _scaffold_python_pip,
    "node": _scaffold_node,
}


# ---------------------------------------------------------------------------
# ProjectWorkspace
# ---------------------------------------------------------------------------


class ProjectWorkspace:
    """Orchestrates creation of new project directories.

    Args:
        project_root (Path): Base directory under which new projects are created.
        store (ProjectStore): :class:`ProjectStore` for registering created projects.
        run_cmd (Callable[[list[str]], None] | None): Callable that runs a
            subprocess command given a list of args.
            Defaults to :func:`subprocess.run` with ``check=True``.
            Pass a mock in tests to avoid real git/kanban-md calls.
    """

    def __init__(
        self,
        project_root: Path,
        store: ProjectStore,
        run_cmd: Callable[[list[str]], None] | None = None,
    ) -> None:
        self._project_root = project_root
        self._store = store
        self._run_cmd = run_cmd or _default_run_cmd

    def create_project(self, name: str, template: str) -> Path:
        """Create a new project directory with the given template.

        Steps:

        1. Validate template name
        2. Resolve and create project directory
        3. Run template scaffolder (files)
        4. ``git init``
        5. ``kanban-md init``
        6. Register in :class:`ProjectStore`

        Returns the path to the created project directory.

        Raises:
            ValueError: If the template is unknown or the project name is a duplicate.
            FileExistsError: If the target directory already exists.
        """
        # 1. Validate template
        if template not in TEMPLATES:
            msg = f"Unknown template '{template}'. Valid: {sorted(TEMPLATES)}"
            raise ValueError(msg)

        # 2. Check for duplicate name in store (before touching filesystem)
        try:
            self._store.get_by_name(name)
        except KeyError:
            pass  # Good — name is not taken
        else:
            msg = f"Project '{name}' already exists"
            raise ValueError(msg)

        # 3. Resolve directory
        slug = _slugify(name)
        project_dir = self._project_root / slug
        if project_dir.exists():
            msg = f"Directory already exists: {project_dir}"
            raise FileExistsError(msg)
        project_dir.mkdir(parents=True)

        # 3. Scaffold files
        scaffolder = _SCAFFOLDERS[template]
        scaffolder(project_dir, name)

        # 4. git init
        self._run_cmd(["git", "init", str(project_dir)])

        # 5. kanban-md init
        kanban_dir = str(project_dir / "kanban")
        self._run_cmd(["kanban-md", "init", "--dir", kanban_dir])

        # 6. Register in store
        self._store.create(name, project_dir)

        logger.info("Created project '%s' at %s (template=%s)", name, project_dir, template)
        return project_dir
