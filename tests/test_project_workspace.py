"""Tests for ProjectWorkspace — scaffolding new project directories.

TDD tests for tasks #365 (core + bare template) and #366 (python-uv,
python-pip, node templates).  Subprocess calls (git, kanban-md) are mocked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear.projects.store import ProjectStore
from owlbear.projects.workspace import ProjectWorkspace

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Return a temp directory to serve as project_root."""
    return tmp_path / "projects"


@pytest.fixture
def store(tmp_path: Path) -> ProjectStore:
    """Return a ProjectStore backed by a temp directory."""
    return ProjectStore(tmp_path / "store")


@pytest.fixture
def run_cmd() -> MagicMock:
    """Mock callable replacing subprocess usage for git/kanban-md."""
    return MagicMock()


@pytest.fixture
def workspace(
    project_root: Path, store: ProjectStore, run_cmd: MagicMock
) -> ProjectWorkspace:
    """Return a ProjectWorkspace with mocked subprocess runner."""
    return ProjectWorkspace(
        project_root=project_root,
        store=store,
        run_cmd=run_cmd,
    )


# ===========================================================================
# Task #365 — Config field: project_root
# ===========================================================================


class TestProjectRootConfig:
    """OwlBearSettings must have a project_root field."""

    def test_default_project_root(self) -> None:
        """project_root defaults to ~/projects."""
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings()
        assert settings.project_root == Path.home() / "projects"

    def test_project_root_override(self, tmp_path: Path) -> None:
        """project_root can be overridden via env or constructor."""
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings(project_root=tmp_path / "custom")
        assert settings.project_root == tmp_path / "custom"


# ===========================================================================
# Task #365 — ProjectWorkspace.create_project() bare template
# ===========================================================================


class TestCreateProjectBare:
    """ProjectWorkspace.create_project(name, 'bare') scaffolds a minimal project."""

    def test_returns_project_path(self, workspace: ProjectWorkspace) -> None:
        """create_project returns the path to the new project directory."""
        result = workspace.create_project("My Project", "bare")
        assert isinstance(result, Path)
        assert result.name == "my-project"

    def test_creates_project_directory(self, workspace: ProjectWorkspace) -> None:
        """The project directory is created on disk."""
        result = workspace.create_project("My Project", "bare")
        assert result.is_dir()

    def test_creates_readme(self, workspace: ProjectWorkspace) -> None:
        """Bare template produces a README.md with the project name."""
        result = workspace.create_project("My Project", "bare")
        readme = result / "README.md"
        assert readme.exists()
        content = readme.read_text(encoding="utf-8")
        assert "My Project" in content

    def test_creates_gitignore(self, workspace: ProjectWorkspace) -> None:
        """Bare template produces a .gitignore."""
        result = workspace.create_project("My Project", "bare")
        gitignore = result / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text(encoding="utf-8")
        assert "__pycache__" in content

    def test_calls_git_init(
        self, workspace: ProjectWorkspace, run_cmd: MagicMock
    ) -> None:
        """create_project calls git init in the project directory."""
        result = workspace.create_project("My Project", "bare")
        run_cmd.assert_any_call(["git", "init", str(result)])

    def test_calls_kanban_init(
        self, workspace: ProjectWorkspace, run_cmd: MagicMock
    ) -> None:
        """create_project calls kanban-md init for the project."""
        workspace.create_project("My Project", "bare")
        # Should call kanban-md init with --dir pointing to project kanban dir
        kanban_calls = [
            c
            for c in run_cmd.call_args_list
            if any("kanban" in str(a).lower() for a in c.args[0])
        ]
        assert len(kanban_calls) >= 1

    def test_registers_in_store(
        self, workspace: ProjectWorkspace, store: ProjectStore
    ) -> None:
        """The project is registered in the ProjectStore."""
        result = workspace.create_project("My Project", "bare")
        project = store.get_by_name("My Project")
        assert project.workspace_path == result

    def test_duplicate_name_raises(self, workspace: ProjectWorkspace) -> None:
        """Creating a project with a duplicate name raises ValueError."""
        workspace.create_project("My Project", "bare")
        with pytest.raises(ValueError, match="already exists"):
            workspace.create_project("My Project", "bare")

    def test_invalid_template_raises(self, workspace: ProjectWorkspace) -> None:
        """An unknown template name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown template"):
            workspace.create_project("My Project", "unknown-template")

    def test_directory_already_exists_raises(
        self, workspace: ProjectWorkspace, project_root: Path
    ) -> None:
        """If the target directory already exists, raise FileExistsError."""
        target = project_root / "my-project"
        target.mkdir(parents=True)
        with pytest.raises(FileExistsError, match="already exists"):
            workspace.create_project("My Project", "bare")

    def test_git_init_called_before_kanban_init(
        self, workspace: ProjectWorkspace, run_cmd: MagicMock
    ) -> None:
        """git init is called before kanban-md init (order matters)."""
        workspace.create_project("My Project", "bare")
        calls = [c.args[0] for c in run_cmd.call_args_list]
        git_idx = next(i for i, c in enumerate(calls) if "git" in c)
        kanban_idx = next(
            i for i, c in enumerate(calls) if any("kanban" in str(a).lower() for a in c)
        )
        assert git_idx < kanban_idx


# ===========================================================================
# Task #366 — python-uv template
# ===========================================================================


class TestPythonUvTemplate:
    """create_project(name, 'python-uv') scaffolds a Python/uv project."""

    def test_creates_pyproject_toml(self, workspace: ProjectWorkspace) -> None:
        """python-uv creates a pyproject.toml with uv build-system."""
        result = workspace.create_project("My Lib", "python-uv")
        toml = result / "pyproject.toml"
        assert toml.exists()
        content = toml.read_text(encoding="utf-8")
        assert "[project]" in content
        assert "my-lib" in content

    def test_creates_src_package(self, workspace: ProjectWorkspace) -> None:
        """python-uv creates src/{slug}/__init__.py."""
        result = workspace.create_project("My Lib", "python-uv")
        init = result / "src" / "my_lib" / "__init__.py"
        assert init.exists()

    def test_creates_tests_dir(self, workspace: ProjectWorkspace) -> None:
        """python-uv creates tests/ directory with __init__.py."""
        result = workspace.create_project("My Lib", "python-uv")
        tests_init = result / "tests" / "__init__.py"
        assert tests_init.exists()

    def test_creates_python_version(self, workspace: ProjectWorkspace) -> None:
        """python-uv creates .python-version file."""
        result = workspace.create_project("My Lib", "python-uv")
        pv = result / ".python-version"
        assert pv.exists()
        assert "3.12" in pv.read_text(encoding="utf-8")

    def test_has_bare_files(self, workspace: ProjectWorkspace) -> None:
        """python-uv also includes bare template files (README, .gitignore)."""
        result = workspace.create_project("My Lib", "python-uv")
        assert (result / "README.md").exists()
        assert (result / ".gitignore").exists()

    def test_calls_git_and_kanban(
        self, workspace: ProjectWorkspace, run_cmd: MagicMock
    ) -> None:
        """python-uv still runs git init and kanban-md init."""
        workspace.create_project("My Lib", "python-uv")
        calls_flat = " ".join(str(c) for c in run_cmd.call_args_list)
        assert "git" in calls_flat
        assert "kanban" in calls_flat.lower()

    def test_registers_in_store(
        self, workspace: ProjectWorkspace, store: ProjectStore
    ) -> None:
        """python-uv project is registered in the store."""
        workspace.create_project("My Lib", "python-uv")
        project = store.get_by_name("My Lib")
        assert project.status == "active"

    def test_pyproject_has_uv_source_layout(
        self, workspace: ProjectWorkspace
    ) -> None:
        """pyproject.toml uses hatchling build backend (uv-compatible)."""
        result = workspace.create_project("My Lib", "python-uv")
        content = (result / "pyproject.toml").read_text(encoding="utf-8")
        assert "hatchling" in content


# ===========================================================================
# Task #366 — python-pip template
# ===========================================================================


class TestPythonPipTemplate:
    """create_project(name, 'python-pip') scaffolds a pip-style Python project."""

    def test_creates_pyproject_toml(self, workspace: ProjectWorkspace) -> None:
        """python-pip creates a pyproject.toml with setuptools backend."""
        result = workspace.create_project("My App", "python-pip")
        toml = result / "pyproject.toml"
        assert toml.exists()
        content = toml.read_text(encoding="utf-8")
        assert "[project]" in content
        assert "setuptools" in content

    def test_creates_requirements_txt(self, workspace: ProjectWorkspace) -> None:
        """python-pip creates an empty requirements.txt."""
        result = workspace.create_project("My App", "python-pip")
        req = result / "requirements.txt"
        assert req.exists()

    def test_creates_src_package(self, workspace: ProjectWorkspace) -> None:
        """python-pip creates src/{slug}/__init__.py."""
        result = workspace.create_project("My App", "python-pip")
        init = result / "src" / "my_app" / "__init__.py"
        assert init.exists()

    def test_creates_tests_dir(self, workspace: ProjectWorkspace) -> None:
        """python-pip creates tests/ with __init__.py."""
        result = workspace.create_project("My App", "python-pip")
        assert (result / "tests" / "__init__.py").exists()

    def test_has_bare_files(self, workspace: ProjectWorkspace) -> None:
        """python-pip includes bare template files."""
        result = workspace.create_project("My App", "python-pip")
        assert (result / "README.md").exists()
        assert (result / ".gitignore").exists()

    def test_registers_in_store(
        self, workspace: ProjectWorkspace, store: ProjectStore
    ) -> None:
        """python-pip project is registered."""
        workspace.create_project("My App", "python-pip")
        assert store.get_by_name("My App").status == "active"


# ===========================================================================
# Task #366 — node template
# ===========================================================================


class TestNodeTemplate:
    """create_project(name, 'node') scaffolds a Node/TS project."""

    def test_creates_package_json(self, workspace: ProjectWorkspace) -> None:
        """node template creates package.json with project name."""
        result = workspace.create_project("My App", "node")
        pkg = result / "package.json"
        assert pkg.exists()
        content = pkg.read_text(encoding="utf-8")
        assert "my-app" in content

    def test_creates_src_dir(self, workspace: ProjectWorkspace) -> None:
        """node template creates src/ directory."""
        result = workspace.create_project("My App", "node")
        assert (result / "src").is_dir()

    def test_creates_tsconfig(self, workspace: ProjectWorkspace) -> None:
        """node template creates tsconfig.json."""
        result = workspace.create_project("My App", "node")
        assert (result / "tsconfig.json").exists()

    def test_has_bare_files(self, workspace: ProjectWorkspace) -> None:
        """node template includes bare files."""
        result = workspace.create_project("My App", "node")
        assert (result / "README.md").exists()
        assert (result / ".gitignore").exists()

    def test_registers_in_store(
        self, workspace: ProjectWorkspace, store: ProjectStore
    ) -> None:
        """node project is registered."""
        workspace.create_project("My App", "node")
        assert store.get_by_name("My App").status == "active"

    def test_node_gitignore_has_node_modules(
        self, workspace: ProjectWorkspace
    ) -> None:
        """node .gitignore includes node_modules/."""
        result = workspace.create_project("My App", "node")
        content = (result / ".gitignore").read_text(encoding="utf-8")
        assert "node_modules" in content

