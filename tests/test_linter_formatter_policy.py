"""Regression checks for linter and formatter policy boundaries."""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from owlbear_tools import quality

_ROOT = Path(__file__).resolve().parents[1]
_JSONC_LINE_COMMENT = re.compile(r"(?m)^\s*//.*$")
_P01_SHARED_EXCLUDED_PATHS = (
    "package.egg-info/PKG-INFO",
    ".owlbear/delivery/packages/package.whl",
    ".owlbear/delivery/runtime/frontier.json",
    ".owlbear/memory/entry.md",
    ".owlbear/research/notes.md",
    "store/audit/history.db",
    "store/knowledge/entities.db",
    "generated/.benchmarks/results.json",
    "nested/.ruff_cache/metadata.json",
    "environment/.venv/bin/python",
    "src/__pycache__/module.pyc",
    "cache/_cache/value.json",
    "generated/artifacts/output.bin",
    "build/output.txt",
    "coverage/index.html",
    "dist/bundle.js",
    "downloads/archive.zip",
    "htmlcov/index.html",
    "node_modules/package/index.js",
    "parts/package/file",
    "playwright-report/index.html",
    "scratch/debug.txt",
    "sdist/package.tar.gz",
    "test-results/results.json",
    "wheels/package.whl",
    "worktrees/change/file.py",
)
_P01_SHARED_INCLUDED_PATHS = (
    "src/example.py",
    ".owlbear/README.md",
    "store/audit/history.txt",
    "generated/output.txt",
)
_P08_JSON_SCOPE = r"(^|/).*\.(json|jsonc)$"
_P08_JSON_SCOPE_SAMPLES = (
    ("package.json", True),
    (".vscode/settings.json", True),
    (".vscode/mcp.json", True),
    (".markdownlint-cli2.jsonc", True),
    ("serve/delivery-next/src/owlbear_delivery_next/web/ui.mjs", False),
)
_M04_ALLOWED_ELEMENTS = [
    "agents",
    "boundaries",
    "critical_rules",
    "examples",
    "output_format",
    "path",
    "persona",
    "required_reading",
    "tools",
]
_M09_PACKAGE_MARKDOWN_PATH = ".owlbear/delivery/packages/website-to-knowledge-vertical/design.md"
_M09_RUNTIME_MARKDOWN_PATH = ".owlbear/delivery/runtime/changes/current.md"
_M09_WORKTREE_MARKDOWN_PATH = ".owlbear/delivery/worktrees/change.md"
_M09_MEMORY_MARKDOWN_PATHS = (
    ".owlbear/memory/4c207941-f94b-4abd-a6e3-67b73ed1020a.md",
    ".owlbear/memory/45d05ede-bf24-4f64-9810-87a88e46084a.md",
    ".owlbear/memory/knowledge-package-enforces-type-checking-1kwl0t.md",
)
_M09_RESEARCH_MARKDOWN_PATHS = (
    ".owlbear/research/1004-ad-hoc-critic-invocation.md",
    ".owlbear/research/wip-continuity-store.md",
    ".owlbear/research/environment-audit-research-workflow.md",
    ".owlbear/research/linter-formatter-rule-audit.md",
    ".owlbear/research/cockpit-work-items-redesign-evidence/opus-final-plan-review.md",
)
_M09_SOURCES_MARKDOWN_PATH = ".owlbear/sources/overview.md"
_X04_FORMATTERS = {
    "[json]": "biomejs.biome",
    "[javascript][javascriptreact][jsonc][typescript][typescriptreact][css]": "biomejs.biome",
    "[markdown]": "DavidAnson.vscode-markdownlint",
    "[python]": "charliermarsh.ruff",
    "[toml]": "tamasfe.even-better-toml",
}


def _normalize_pattern(pattern: str) -> str:
    normalized = pattern.strip().removesuffix("/**").removesuffix("/")
    return normalized.removeprefix("**/")


def _read_cli2_ignores(path: Path) -> set[str]:
    payload = json.loads(_JSONC_LINE_COMMENT.sub("", path.read_text(encoding="utf-8")))
    assert isinstance(payload, dict)
    ignores = payload.get("ignores")
    assert isinstance(ignores, list)
    assert all(isinstance(ignore, str) for ignore in ignores)
    return {_normalize_pattern(ignore) for ignore in ignores}


def _markdownlint_rules() -> dict[str, object]:
    """The rules live in the cli2 file's ``config``."""
    root = json.loads(_JSONC_LINE_COMMENT.sub("", (_ROOT / ".markdownlint-cli2.jsonc").read_text(encoding="utf-8")))
    assert isinstance(root, dict)
    assert isinstance(root.get("config"), dict)
    assert not (_ROOT / ".markdownlint.json").exists()  # it would override the cli2 file's config
    return root["config"]


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _read_precommit_exclude(config: dict[str, object]) -> re.Pattern[str]:
    pattern = config.get("exclude")
    assert isinstance(pattern, str)
    return re.compile(pattern)


def _read_precommit_local_hooks(config: dict[str, object]) -> dict[str, dict[str, object]]:
    repositories = config.get("repos")
    assert isinstance(repositories, list)
    for repository in repositories:
        assert isinstance(repository, dict)
        if repository.get("repo") != "local":
            continue
        hooks = repository.get("hooks")
        assert isinstance(hooks, list)
        local_hooks: dict[str, dict[str, object]] = {}
        for hook in hooks:
            assert isinstance(hook, dict)
            hook_id = hook.get("id")
            if isinstance(hook_id, str):
                local_hooks[hook_id] = hook
        return local_hooks
    message = "pre-commit local repository is missing"
    raise AssertionError(message)


def _read_precommit_hook(config: dict[str, object], hook_id: str) -> dict[str, object]:
    repositories = config.get("repos")
    assert isinstance(repositories, list)
    for repository in repositories:
        assert isinstance(repository, dict)
        hooks = repository.get("hooks")
        if not isinstance(hooks, list):
            continue
        for hook in hooks:
            assert isinstance(hook, dict)
            if hook.get("id") == hook_id:
                return hook
    message = f"pre-commit hook is missing: {hook_id}"
    raise AssertionError(message)


def test_every_hook_the_lint_runner_calls_runs_in_the_manual_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    """The runner passes `--hook-stage manual`; a hook absent from that stage fails `uv run lint` (TD-204)."""
    monkeypatch.chdir(_ROOT)
    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    default_stages = config.get("default_stages")
    hooks = [hook for repository in config["repos"] for hook in repository["hooks"]]
    called = {*quality._PRECOMMIT_CHECK_HOOKS.values(), *quality._unclaimed_hooks()}  # noqa: SLF001
    called |= {name for names in quality._PRECOMMIT_FIX_HOOKS.values() for name in names if name}  # noqa: SLF001

    for name in sorted(called):
        matches = [hook for hook in hooks if name in {hook.get("id"), hook.get("alias")}]
        assert matches, name
        assert all("manual" in hook.get("stages", default_stages) for hook in matches), name


def test_markdownlint_ignores_live_in_the_cli2_config_only() -> None:
    assert not (_ROOT / ".markdownlintignore").exists()  # markdownlint-cli2 does not read it


def test_markdownlint_inline_html_allows_only_agent_sections() -> None:
    assert _markdownlint_rules().get("MD033") == {"allowed_elements": _M04_ALLOWED_ELEMENTS}

    assert "<strong>" not in (_ROOT / "setup/sharing-guide.md").read_text(encoding="utf-8")


def test_markdownlint_rule_authorities_and_source_suppression_remain_explicit() -> None:
    expected_front_matter_title = r"^\s*(?:title|name|description)\s*[:=]"
    config = _markdownlint_rules()
    assert config.get("MD013") is False
    assert config.get("MD024") == {"siblings_only": True}
    assert config.get("MD029") == {"style": "ordered"}
    assert config.get("MD041") == {"front_matter_title": expected_front_matter_title}
    assert config.get("MD060") == {"style": "compact"}

    source_lines = (_ROOT / ".owlbear/sources/overview.md").read_text(encoding="utf-8").splitlines()
    assert source_lines[0] == "<!-- markdownlint-disable MD060 -->"


def test_delivery_packages_remain_excluded_from_markdown_consumers() -> None:
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    category = ".owlbear/delivery/packages"

    assert category in root_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    assert precommit_exclude.search(_M09_PACKAGE_MARKDOWN_PATH) is not None


def test_delivery_runtime_remains_excluded_from_markdown_consumers() -> None:
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    category = ".owlbear/delivery/runtime"

    assert category in root_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    assert precommit_exclude.search(_M09_RUNTIME_MARKDOWN_PATH) is not None


def test_broad_worktree_ignore_covers_delivery_worktrees() -> None:
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    scoped_category = ".owlbear/delivery/worktrees"

    assert "worktrees" in root_cli2
    assert scoped_category not in root_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    assert precommit_exclude.search(_M09_WORKTREE_MARKDOWN_PATH) is not None


def test_memory_store_remains_excluded_from_markdown_consumers() -> None:
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")

    assert ".owlbear/memory" in root_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    assert all(precommit_exclude.search(path) is not None for path in _M09_MEMORY_MARKDOWN_PATHS)


def test_research_archive_remains_excluded_from_markdown_consumers() -> None:
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")

    assert ".owlbear/research" in root_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    assert all(precommit_exclude.search(path) is not None for path in _M09_RESEARCH_MARKDOWN_PATHS)


def test_sources_document_is_included_in_markdown_consumers() -> None:
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")

    assert ".owlbear/sources" not in root_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    assert precommit_exclude.search(_M09_SOURCES_MARKDOWN_PATH) is None


def test_precommit_exclusion_taxonomy() -> None:
    precommit_pattern = _read_precommit_exclude(_read_yaml_mapping(_ROOT / ".pre-commit-config.yaml"))

    assert all(precommit_pattern.search(path) is not None for path in _P01_SHARED_EXCLUDED_PATHS)
    assert all(precommit_pattern.search(path) is None for path in _P01_SHARED_INCLUDED_PATHS)


def test_biome_replaces_frontend_and_json_scanners() -> None:
    root_package = json.loads((_ROOT / "package.json").read_text(encoding="utf-8"))
    assert isinstance(root_package, dict)
    assert "lint:json" not in root_package.get("scripts", {})
    assert not (_ROOT / "scripts/lint-json.mjs").exists()
    dependencies = root_package.get("devDependencies")
    assert isinstance(dependencies, dict)
    assert "@biomejs/biome" in dependencies
    assert not {"@eslint/json", "eslint", "stylelint", "typescript-eslint"} & set(dependencies)

    precommit_hooks = _read_precommit_local_hooks(_read_yaml_mapping(_ROOT / ".pre-commit-config.yaml"))
    biome_hook = precommit_hooks["biome-check"]
    assert biome_hook.get("pass_filenames", True) is True
    assert "stages" not in biome_hook
    assert "check --write" in biome_hook.get("entry", "")

    workflow = (_ROOT / ".github/workflows/static.yml").read_text(encoding="utf-8")
    assert "uv run --no-sync lint --no-fix\n" in workflow

    for path, expected in _P08_JSON_SCOPE_SAMPLES:
        assert bool(re.search(_P08_JSON_SCOPE, path)) is expected, path


def test_biome_json_scope_excludes_generated_and_machine_managed_paths() -> None:
    biome = json.loads((_ROOT / "biome.json").read_text(encoding="utf-8"))
    assert isinstance(biome, dict)
    files = biome.get("files")
    assert isinstance(files, dict)
    includes = files.get("includes")
    assert isinstance(includes, list)
    assert "**/*.json" in includes
    assert "**/*.jsonc" in includes
    assert all(isinstance(include, str) for include in includes)
    assert {
        "!**/.owlbear/delivery/packages",
        "!**/.owlbear/delivery/runtime",
        "!**/.owlbear/memory",
        "!**/.owlbear/research",
        "!**/.owlbear/sources",
        "!**/.owlbear/legacy",
        "!**/.owlbear/target",
        "!**/scratch",
        "!**/worktrees",
    }.issubset(includes)


@pytest.fixture
def biome_workspace(tmp_path: Path) -> Path:
    if shutil.which("node") is None or not (_ROOT / quality.BIOME).exists():
        pytest.skip("Root Node dependencies are required for Biome integration checks")
    for relative in (Path("biome.json"), Path(".editorconfig"), Path(".gitignore"), Path(".owlbear/.gitignore")):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_ROOT / relative, destination)
    (tmp_path / "node_modules").symlink_to(_ROOT / "node_modules", target_is_directory=True)
    hook = _read_precommit_local_hooks(_read_yaml_mapping(_ROOT / ".pre-commit-config.yaml"))["biome-check"]
    (tmp_path / ".pre-commit-config.yaml").write_text(
        yaml.safe_dump({"repos": [{"repo": "local", "hooks": [hook]}]}), encoding="utf-8"
    )
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S603, S607
    return tmp_path


def _biome_probe(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["node", str(root / quality.BIOME), *arguments],  # noqa: S607
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.biome
def test_biome_applies_width_and_excludes_generated_json(biome_workspace: Path) -> None:
    source = biome_workspace / "settings.json"
    expected = '{ "alpha": 123456789, "beta": 123456789, "gamma": 123456789, "delta": 123456789, "epsilon": 1 }\n'
    source.write_text(expected.replace(" ", ""), encoding="utf-8")
    for relative in ("nested/build/broken.json", "scratch/broken.json", ".owlbear/research/broken.json"):
        ignored = biome_workspace / relative
        ignored.parent.mkdir(parents=True, exist_ok=True)
        ignored.write_text("{broken", encoding="utf-8")
    result = _biome_probe(biome_workspace, "format", "--write", ".")
    assert result.returncode == 0, result.stderr
    assert source.read_text(encoding="utf-8") == expected
    assert _biome_probe(biome_workspace, "ci", ".").returncode == 0
    source.write_text("{broken", encoding="utf-8")
    assert _biome_probe(biome_workspace, "check", ".").returncode == 1


@pytest.mark.biome
def test_biome_staged_checks_handle_empty_ignored_and_invalid_files(biome_workspace: Path) -> None:
    arguments = ("check", "--staged", "--no-errors-on-unmatched")
    assert _biome_probe(biome_workspace, *arguments).returncode == 0
    lockfile = biome_workspace / "package-lock.json"
    lockfile.write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", str(lockfile)], cwd=biome_workspace, check=True)  # noqa: S603, S607
    assert _biome_probe(biome_workspace, *arguments).returncode == 0
    source = biome_workspace / "settings.json"
    source.write_text("{broken", encoding="utf-8")
    subprocess.run(["git", "add", str(source)], cwd=biome_workspace, check=True)  # noqa: S603, S607
    assert _biome_probe(biome_workspace, *arguments).returncode == 1
    assert source.read_text(encoding="utf-8") == "{broken"


@pytest.mark.biome
def test_biome_precommit_fixes_only_selected_files(biome_workspace: Path) -> None:
    selected = "selected.json"
    other = "other.json"
    for relative in (selected, other):
        (biome_workspace / relative).write_text('{"value":1}\n', encoding="utf-8")
    subprocess.run(["git", "add", selected, other], cwd=biome_workspace, check=True)  # noqa: S603, S607
    command = [sys.executable, "-m", "pre_commit", "run", "biome-check"]
    result = subprocess.run(  # noqa: S603
        [*command, "--files", selected], cwd=biome_workspace, capture_output=True, text=True, check=False
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert (biome_workspace / selected).read_text(encoding="utf-8") == '{ "value": 1 }\n'
    assert (biome_workspace / other).read_text(encoding="utf-8") == '{"value":1}\n'
    subprocess.run([*command, "--all-files"], cwd=biome_workspace, capture_output=True, check=False)  # noqa: S603
    result = subprocess.run(  # noqa: S603
        [*command, "--all-files"], cwd=biome_workspace, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (biome_workspace / other).read_text(encoding="utf-8") == '{ "value": 1 }\n'


def test_editorconfig_python_indentation_delegation_is_shared() -> None:
    precommit_config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    editorconfig_hook = _read_precommit_hook(
        precommit_config,
        "editorconfig-checker",
    )
    assert editorconfig_hook.get("args") == ["-disable-indent-size"]

    editorconfig = (_ROOT / ".editorconfig").read_text(encoding="utf-8")
    assert "[*.py]" in editorconfig
    assert "indent_size = 4" in editorconfig


def test_ruff_formatter_conflict_ignore_remains_explicit() -> None:
    pyproject = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tool = pyproject.get("tool")
    assert isinstance(tool, dict)
    ruff = tool.get("ruff")
    assert isinstance(ruff, dict)
    lint = ruff.get("lint")
    assert isinstance(lint, dict)
    ignored = lint.get("ignore")
    assert isinstance(ignored, list)
    assert "COM812" in ignored


def test_pytest_test_roots_do_not_share_a_package_namespace() -> None:
    test_roots = [_ROOT / "tests", *_ROOT.glob("serve/*/tests")]

    assert test_roots
    assert all(not (test_root / "__init__.py").is_file() for test_root in test_roots)


def test_vscode_settings_have_no_global_prettier_fallback() -> None:
    settings = json.loads(
        _JSONC_LINE_COMMENT.sub(
            "",
            (_ROOT / ".vscode/settings.json").read_text(encoding="utf-8"),
        )
    )
    assert isinstance(settings, dict)
    assert "editor.defaultFormatter" not in settings
    assert "esbenp.prettier-vscode" not in json.dumps(settings)


def test_vscode_language_formatter_matrix_remains_explicit() -> None:
    settings = json.loads(
        _JSONC_LINE_COMMENT.sub(
            "",
            (_ROOT / ".vscode/settings.json").read_text(encoding="utf-8"),
        )
    )
    assert isinstance(settings, dict)

    for language_scope, formatter in _X04_FORMATTERS.items():
        language_settings = settings.get(language_scope)
        assert isinstance(language_settings, dict)
        assert language_settings.get("editor.defaultFormatter") == formatter


def test_scripts_run_outside_the_pinned_python_keep_python_312_syntax() -> None:
    workflow_scripts = {
        match
        for workflow in (_ROOT / ".github" / "workflows").glob("*.yml")
        for match in re.findall(r"python3 (?:\.\./)*([\w./-]+\.py)", workflow.read_text(encoding="utf-8"))
    }
    assert workflow_scripts

    for relative in sorted(workflow_scripts):
        source = (_ROOT / relative).read_text(encoding="utf-8")
        ast.parse(source, filename=relative, feature_version=(3, 12))
