"""Regression checks for linter and formatter policy boundaries."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_JSONC_LINE_COMMENT = re.compile(r"(?m)^\s*//.*$")
_SEED_ONLY_CLI2_IGNORES = frozenset({".owlbear/hooks"})
_SEED_PROFILE_OMISSIONS = frozenset({".owlbear/target"})
_P01_SHARED_EXCLUDED_PATHS = (
    "package.egg-info/PKG-INFO",
    ".owlbear/completed/change.json",
    ".owlbear/delivery/packages/package.whl",
    ".owlbear/delivery/runtime/frontier.json",
    ".owlbear/doc-index.md",
    ".owlbear/py-index.md",
    ".owlbear/ts-index.md",
    ".owlbear/legacy/old.md",
    ".owlbear/memory/entry.md",
    ".owlbear/research/notes.md",
    ".owlbear/target/output.json",
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
    ".owlbear/ideas.md",
    "store/audit/history.txt",
    "generated/output.txt",
    ".owlbear/target.md",
)
_P04_LOCAL_ESLINT_SCOPE = r"^serve/cockpit/web/(src|e2e)/.*\.(ts|tsx)$"
_P04_CI_ESLINT_SCOPE = r"^serve/cockpit/web/.*\.(ts|tsx)$"
_P04_SCOPE_SAMPLES = (
    ("serve/cockpit/web/src/CockpitShell.tsx", True, True),
    ("serve/cockpit/web/e2e/smoke.spec.ts", True, True),
    ("serve/cockpit/web/vitest.setup.ts", False, True),
    ("serve/cockpit/web/scripts/run-e2e.mjs", False, False),
)
_P05_STYLELINT_SCOPE = r"^serve/cockpit/web/src/.*\.css$"
_P05_SCOPE_SAMPLES = (
    ("serve/cockpit/web/src/custom-tokens.css", True),
    ("serve/cockpit/web/public/porsche-design-system/future.css", False),
    ("serve/cockpit/dist/assets/index.css", False),
)
_P08_JSON_SCOPE = r"(^|/).*\.(json|jsonc)$"
_P08_JSON_SCOPE_SAMPLES = (
    ("package.json", True),
    (".vscode/settings.json", True),
    (".vscode/mcp.json", True),
    (".markdownlint-cli2.jsonc", True),
    ("serve/cockpit/web/src/App.tsx", False),
)
_P08_JSON_IGNORE_MARKERS = (
    '".owlbear/delivery/packages/**"',
    '".owlbear/research/**"',
    '".owlbear/sources/**"',
    '".venv/**"',
    '"**/.venv/**"',
    '"node_modules/**"',
    '"test-results/**"',
    '"megalinter-reports/**"',
    '"store/audit/*.db"',
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
]
_M09_PACKAGE_MARKDOWN_PATH = ".owlbear/delivery/packages/website-to-knowledge-vertical/design.md"
_M09_RUNTIME_MARKDOWN_PATH = ".owlbear/delivery/runtime/changes/current.md"
_M09_WORKTREE_MARKDOWN_PATH = ".owlbear/delivery/worktrees/change.md"
_M09_GENERATED_INDEX_MARKDOWN_PATHS = (
    ".owlbear/doc-index.md",
    ".owlbear/py-index.md",
    ".owlbear/ts-index.md",
)
_M09_LEGACY_MARKDOWN_PATHS = (
    ".owlbear/legacy/briefs/README.md",
    ".owlbear/legacy/completed/knowledge-source-contract-alignment/design.md",
    ".owlbear/legacy/openspec-final/content/changes/complete-browser-content-acquisition/design.md",
    ".owlbear/legacy/target-cutover/changes/content/replace-delivery-pipeline/design.md",
    ".owlbear/legacy/target-cutover-incidents/20260802/README.md",
    ".owlbear/legacy/target-delivery-cutover-design/20260804/README.md",
    ".owlbear/legacy/target-delivery-cutover-runtime/20260804/README.md",
)
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
_M09_TARGET_MARKDOWN_PATH = ".owlbear/target/runtime.md"
_X04_FORMATTERS = {
    "[json]": "vscode.json-language-features",
    "[jsonc]": "vscode.json-language-features",
    "[markdown]": "DavidAnson.vscode-markdownlint",
    "[powershell]": "ms-vscode.powershell",
    "[python]": "charliermarsh.ruff",
    "[toml]": "tamasfe.even-better-toml",
    "[xml]": "redhat.vscode-xml",
}
_P06_TYPECHECK_SCOPE = r"^serve/cockpit/web/(src/.*\.(ts|tsx)|vite\.config\.ts|vitest\.setup\.ts)$"
_P06_SCOPE_SAMPLES = (
    ("serve/cockpit/web/src/CockpitShell.tsx", True),
    ("serve/cockpit/web/vite.config.ts", True),
    ("serve/cockpit/web/vitest.setup.ts", True),
    ("serve/cockpit/web/e2e/smoke.spec.ts", False),
    ("serve/cockpit/web/playwright.config.ts", False),
)


def _normalize_pattern(pattern: str, *, cli2: bool) -> str:
    normalized = pattern.strip()
    if cli2:
        normalized = normalized.removesuffix("/**")
    normalized = normalized.removesuffix("/")
    return normalized.removeprefix("**/")


def _read_bare_ignores(path: Path) -> set[str]:
    return {
        _normalize_pattern(line, cli2=False)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _read_cli2_ignores(path: Path) -> set[str]:
    payload = json.loads(_JSONC_LINE_COMMENT.sub("", path.read_text(encoding="utf-8")))
    assert isinstance(payload, dict)
    ignores = payload.get("ignores")
    assert isinstance(ignores, list)
    assert all(isinstance(ignore, str) for ignore in ignores)
    return {_normalize_pattern(ignore, cli2=True) for ignore in ignores}


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


def _read_megalinter_excludes(config: dict[str, object]) -> tuple[re.Pattern[str], frozenset[str]]:
    pattern = config.get("FILTER_REGEX_EXCLUDE")
    directories = config.get("ADDITIONAL_EXCLUDED_DIRECTORIES")
    assert isinstance(pattern, str)
    assert isinstance(directories, list)
    assert all(isinstance(directory, str) for directory in directories)
    return re.compile(pattern), frozenset(directories)


def _is_megalinter_excluded(
    path: str,
    pattern: re.Pattern[str],
    directories: frozenset[str],
) -> bool:
    return pattern.search(path) is not None or any(directory in Path(path).parts for directory in directories)


def test_markdownlint_ignore_authorities_share_normalized_policy() -> None:
    root_bare = _read_bare_ignores(_ROOT / ".markdownlintignore")
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    seed_bare = _read_bare_ignores(_ROOT / "seed/.markdownlintignore")
    seed_cli2 = _read_cli2_ignores(_ROOT / "seed/.markdownlint-cli2.jsonc")

    assert root_bare == root_cli2
    assert seed_bare | _SEED_PROFILE_OMISSIONS == root_bare
    assert seed_cli2 | _SEED_PROFILE_OMISSIONS == root_bare | _SEED_ONLY_CLI2_IGNORES


def test_markdownlint_inline_html_allows_only_agent_sections() -> None:
    for path in (_ROOT / ".markdownlint.json", _ROOT / "seed/.markdownlint.json"):
        config = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(config, dict)
        assert config.get("MD033") == {"allowed_elements": _M04_ALLOWED_ELEMENTS}

    assert "<strong>" not in (_ROOT / "setup/sharing-guide.md").read_text(encoding="utf-8")


def test_markdownlint_rule_authorities_and_source_suppression_remain_explicit() -> None:
    expected_front_matter_title = r"^\s*(?:title|name|description)\s*[:=]"
    for path in (_ROOT / ".markdownlint.json", _ROOT / "seed/.markdownlint.json"):
        config = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(config, dict)
        assert config.get("MD013") is False
        assert config.get("MD024") == {"siblings_only": True}
        assert config.get("MD029") == {"style": "ordered"}
        assert config.get("MD041") == {"front_matter_title": expected_front_matter_title}
        assert config.get("MD060") == {"style": "compact"}

    source_lines = (_ROOT / ".owlbear/sources/overview.md").read_text(encoding="utf-8").splitlines()
    assert source_lines[0] == "<!-- markdownlint-disable MD060 -->"


def test_delivery_packages_remain_excluded_from_markdown_consumers() -> None:
    root_bare = _read_bare_ignores(_ROOT / ".markdownlintignore")
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    seed_bare = _read_bare_ignores(_ROOT / "seed/.markdownlintignore")
    seed_cli2 = _read_cli2_ignores(_ROOT / "seed/.markdownlint-cli2.jsonc")
    category = ".owlbear/delivery/packages"

    assert category in root_bare
    assert category in root_cli2
    assert category in seed_bare
    assert category in seed_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    megalinter_exclude, megalinter_directories = _read_megalinter_excludes(
        _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    )
    assert precommit_exclude.search(_M09_PACKAGE_MARKDOWN_PATH) is not None
    assert _is_megalinter_excluded(
        _M09_PACKAGE_MARKDOWN_PATH,
        megalinter_exclude,
        megalinter_directories,
    )


def test_delivery_runtime_remains_excluded_from_markdown_consumers() -> None:
    root_bare = _read_bare_ignores(_ROOT / ".markdownlintignore")
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    seed_bare = _read_bare_ignores(_ROOT / "seed/.markdownlintignore")
    seed_cli2 = _read_cli2_ignores(_ROOT / "seed/.markdownlint-cli2.jsonc")
    category = ".owlbear/delivery/runtime"

    assert category in root_bare
    assert category in root_cli2
    assert category in seed_bare
    assert category in seed_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    megalinter_exclude, megalinter_directories = _read_megalinter_excludes(
        _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    )
    assert precommit_exclude.search(_M09_RUNTIME_MARKDOWN_PATH) is not None
    assert _is_megalinter_excluded(
        _M09_RUNTIME_MARKDOWN_PATH,
        megalinter_exclude,
        megalinter_directories,
    )


def test_broad_worktree_ignore_covers_delivery_worktrees() -> None:
    root_bare = _read_bare_ignores(_ROOT / ".markdownlintignore")
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    seed_bare = _read_bare_ignores(_ROOT / "seed/.markdownlintignore")
    seed_cli2 = _read_cli2_ignores(_ROOT / "seed/.markdownlint-cli2.jsonc")
    scoped_category = ".owlbear/delivery/worktrees"

    assert "worktrees" in root_bare
    assert "worktrees" in root_cli2
    assert "worktrees" in seed_bare
    assert "worktrees" in seed_cli2
    assert scoped_category not in root_bare | root_cli2 | seed_bare | seed_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    megalinter_exclude, megalinter_directories = _read_megalinter_excludes(
        _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    )
    assert precommit_exclude.search(_M09_WORKTREE_MARKDOWN_PATH) is not None
    assert _is_megalinter_excluded(
        _M09_WORKTREE_MARKDOWN_PATH,
        megalinter_exclude,
        megalinter_directories,
    )


def test_generated_indexes_remain_excluded_from_markdown_consumers() -> None:
    root_bare = _read_bare_ignores(_ROOT / ".markdownlintignore")
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    seed_bare = _read_bare_ignores(_ROOT / "seed/.markdownlintignore")
    seed_cli2 = _read_cli2_ignores(_ROOT / "seed/.markdownlint-cli2.jsonc")

    for path in _M09_GENERATED_INDEX_MARKDOWN_PATHS:
        assert path in root_bare
        assert path in root_cli2
        assert path in seed_bare
        assert path in seed_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    megalinter_exclude, megalinter_directories = _read_megalinter_excludes(
        _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    )
    assert all(precommit_exclude.search(path) is not None for path in _M09_GENERATED_INDEX_MARKDOWN_PATHS)
    assert all(
        _is_megalinter_excluded(path, megalinter_exclude, megalinter_directories)
        for path in _M09_GENERATED_INDEX_MARKDOWN_PATHS
    )


def test_legacy_archive_remains_excluded_from_markdown_consumers() -> None:
    root_bare = _read_bare_ignores(_ROOT / ".markdownlintignore")
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    seed_bare = _read_bare_ignores(_ROOT / "seed/.markdownlintignore")
    seed_cli2 = _read_cli2_ignores(_ROOT / "seed/.markdownlint-cli2.jsonc")

    assert ".owlbear/legacy" in root_bare
    assert ".owlbear/legacy" in root_cli2
    assert ".owlbear/legacy" in seed_bare
    assert ".owlbear/legacy" in seed_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    megalinter_exclude, megalinter_directories = _read_megalinter_excludes(
        _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    )
    assert all(precommit_exclude.search(path) is not None for path in _M09_LEGACY_MARKDOWN_PATHS)
    assert all(
        _is_megalinter_excluded(path, megalinter_exclude, megalinter_directories) for path in _M09_LEGACY_MARKDOWN_PATHS
    )


def test_memory_store_remains_excluded_from_markdown_consumers() -> None:
    root_bare = _read_bare_ignores(_ROOT / ".markdownlintignore")
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    seed_bare = _read_bare_ignores(_ROOT / "seed/.markdownlintignore")
    seed_cli2 = _read_cli2_ignores(_ROOT / "seed/.markdownlint-cli2.jsonc")

    assert ".owlbear/memory" in root_bare
    assert ".owlbear/memory" in root_cli2
    assert ".owlbear/memory" in seed_bare
    assert ".owlbear/memory" in seed_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    megalinter_exclude, megalinter_directories = _read_megalinter_excludes(
        _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    )
    assert all(precommit_exclude.search(path) is not None for path in _M09_MEMORY_MARKDOWN_PATHS)
    assert all(
        _is_megalinter_excluded(path, megalinter_exclude, megalinter_directories) for path in _M09_MEMORY_MARKDOWN_PATHS
    )


def test_research_archive_remains_excluded_from_markdown_consumers() -> None:
    root_bare = _read_bare_ignores(_ROOT / ".markdownlintignore")
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    seed_bare = _read_bare_ignores(_ROOT / "seed/.markdownlintignore")
    seed_cli2 = _read_cli2_ignores(_ROOT / "seed/.markdownlint-cli2.jsonc")

    assert ".owlbear/research" in root_bare
    assert ".owlbear/research" in root_cli2
    assert ".owlbear/research" in seed_bare
    assert ".owlbear/research" in seed_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    megalinter_exclude, megalinter_directories = _read_megalinter_excludes(
        _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    )
    assert all(precommit_exclude.search(path) is not None for path in _M09_RESEARCH_MARKDOWN_PATHS)
    assert all(
        _is_megalinter_excluded(path, megalinter_exclude, megalinter_directories)
        for path in _M09_RESEARCH_MARKDOWN_PATHS
    )


def test_sources_document_is_included_in_markdown_consumers() -> None:
    root_bare = _read_bare_ignores(_ROOT / ".markdownlintignore")
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    seed_bare = _read_bare_ignores(_ROOT / "seed/.markdownlintignore")
    seed_cli2 = _read_cli2_ignores(_ROOT / "seed/.markdownlint-cli2.jsonc")

    assert ".owlbear/sources" not in root_bare
    assert ".owlbear/sources" not in root_cli2
    assert ".owlbear/sources" not in seed_bare
    assert ".owlbear/sources" not in seed_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    megalinter_exclude, megalinter_directories = _read_megalinter_excludes(
        _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    )
    assert precommit_exclude.search(_M09_SOURCES_MARKDOWN_PATH) is None
    assert not _is_megalinter_excluded(_M09_SOURCES_MARKDOWN_PATH, megalinter_exclude, megalinter_directories)


def test_target_runtime_remains_excluded_from_markdown_consumers() -> None:
    root_bare = _read_bare_ignores(_ROOT / ".markdownlintignore")
    root_cli2 = _read_cli2_ignores(_ROOT / ".markdownlint-cli2.jsonc")
    seed_bare = _read_bare_ignores(_ROOT / "seed/.markdownlintignore")
    seed_cli2 = _read_cli2_ignores(_ROOT / "seed/.markdownlint-cli2.jsonc")

    assert ".owlbear/target" in root_bare
    assert ".owlbear/target" in root_cli2
    assert ".owlbear/target" not in seed_bare
    assert ".owlbear/target" not in seed_cli2

    config = _read_yaml_mapping(_ROOT / ".pre-commit-config.yaml")
    precommit_exclude = _read_precommit_exclude(config)
    megalinter_exclude, megalinter_directories = _read_megalinter_excludes(
        _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    )
    assert precommit_exclude.search(_M09_TARGET_MARKDOWN_PATH) is not None
    assert _is_megalinter_excluded(_M09_TARGET_MARKDOWN_PATH, megalinter_exclude, megalinter_directories)


def test_precommit_and_megalinter_share_exclusion_taxonomy() -> None:
    precommit_pattern = _read_precommit_exclude(_read_yaml_mapping(_ROOT / ".pre-commit-config.yaml"))
    megalinter_pattern, megalinter_directories = _read_megalinter_excludes(
        _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    )

    for path in (*_P01_SHARED_EXCLUDED_PATHS, *_P01_SHARED_INCLUDED_PATHS):
        precommit_excluded = precommit_pattern.search(path) is not None
        megalinter_excluded = _is_megalinter_excluded(path, megalinter_pattern, megalinter_directories)
        assert precommit_excluded == megalinter_excluded, path

    assert all(precommit_pattern.search(path) is not None for path in _P01_SHARED_EXCLUDED_PATHS)
    assert all(precommit_pattern.search(path) is None for path in _P01_SHARED_INCLUDED_PATHS)


def test_frontend_eslint_local_ci_scope_contract() -> None:
    precommit_hooks = _read_precommit_local_hooks(_read_yaml_mapping(_ROOT / ".pre-commit-config.yaml"))
    local_pattern = re.compile(_P04_LOCAL_ESLINT_SCOPE)
    ci_pattern = re.compile(_P04_CI_ESLINT_SCOPE)

    for hook_id in ("eslint-frontend", "eslint-frontend-check"):
        hook = precommit_hooks[hook_id]
        assert hook.get("files") == _P04_LOCAL_ESLINT_SCOPE
        assert hook.get("pass_filenames") is False
        entry = hook.get("entry")
        assert isinstance(entry, str)
        assert "serve/cockpit/web/src/" in entry
        assert "serve/cockpit/web/e2e/" in entry

    megalinter = _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    assert megalinter.get("TYPESCRIPT_ES_FILTER_REGEX_INCLUDE") == _P04_CI_ESLINT_SCOPE

    for path, local_expected, ci_expected in _P04_SCOPE_SAMPLES:
        assert bool(local_pattern.search(path)) is local_expected, path
        assert bool(ci_pattern.search(path)) is ci_expected, path


def test_frontend_stylelint_local_ci_scope_contract() -> None:
    precommit_hooks = _read_precommit_local_hooks(_read_yaml_mapping(_ROOT / ".pre-commit-config.yaml"))
    stylelint_pattern = re.compile(_P05_STYLELINT_SCOPE)

    for hook_id in ("stylelint-frontend-fix", "stylelint-frontend-check", "stylelint-frontend-lax"):
        hook = precommit_hooks[hook_id]
        assert hook.get("files") == _P05_STYLELINT_SCOPE
        assert hook.get("pass_filenames") is False
        entry = hook.get("entry")
        assert isinstance(entry, str)
        assert "npm --prefix serve/cockpit/web run lint:css" in entry

    megalinter = _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    assert megalinter.get("CSS_STYLELINT_FILTER_REGEX_INCLUDE") == _P05_STYLELINT_SCOPE

    for path, expected in _P05_SCOPE_SAMPLES:
        assert bool(stylelint_pattern.search(path)) is expected, path


def test_json_eslint_replaces_jsonlint_with_local_ci_scope_contract() -> None:
    megalinter = _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    enabled = megalinter.get("ENABLE_LINTERS")
    assert isinstance(enabled, list)
    assert "JSON_JSONLINT" not in enabled
    assert "JAVASCRIPT_ES" in enabled
    assert megalinter.get("JAVASCRIPT_ES_FILTER_REGEX_INCLUDE") == _P08_JSON_SCOPE
    assert megalinter.get("JAVASCRIPT_ES_FILE_EXTENSIONS") == [".json", ".jsonc"]
    assert megalinter.get("JAVASCRIPT_ES_CONFIG_FILE") == "eslint-json.config.cjs"
    assert megalinter.get("JAVASCRIPT_ES_RULES_PATH") == "."

    root_package = json.loads((_ROOT / "package.json").read_text(encoding="utf-8"))
    assert isinstance(root_package, dict)
    root_scripts = root_package.get("scripts")
    assert isinstance(root_scripts, dict)
    assert "lint:json" not in root_scripts
    assert not (_ROOT / "scripts/lint-json.mjs").exists()

    package = json.loads((_ROOT / "serve/cockpit/web/package.json").read_text(encoding="utf-8"))
    assert isinstance(package, dict)
    dependencies = package.get("devDependencies")
    scripts = package.get("scripts")
    assert isinstance(dependencies, dict)
    assert isinstance(scripts, dict)
    assert dependencies.get("@eslint/json") == "^2.0.1"
    assert "lint:json" not in scripts

    config_text = (_ROOT / "eslint-json.config.cjs").read_text(encoding="utf-8")
    assert 'language: "json/json"' in config_text
    assert 'language: "json/jsonc"' in config_text
    assert '".vscode/*.json"' in config_text
    assert "allowTrailingCommas: true" in config_text
    assert all(marker in config_text for marker in _P08_JSON_IGNORE_MARKERS)

    precommit_hooks = _read_precommit_local_hooks(_read_yaml_mapping(_ROOT / ".pre-commit-config.yaml"))
    json_hook = precommit_hooks["eslint-json"]
    assert json_hook.get("files") == r".*(\.json|\.jsonc)$"
    assert json_hook.get("pass_filenames") is False
    assert json_hook.get("entry") == "uv run lint-json"

    for path, expected in _P08_JSON_SCOPE_SAMPLES:
        assert bool(re.search(_P08_JSON_SCOPE, path)) is expected, path


def test_editorconfig_python_indentation_delegation_is_shared() -> None:
    megalinter = _read_yaml_mapping(_ROOT / ".mega-linter.yml")
    assert megalinter.get("EDITORCONFIG_EDITORCONFIG_CHECKER_ARGUMENTS") == ("-f github-actions --disable-indent-size")

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


def test_frontend_typecheck_trigger_covers_project_inputs() -> None:
    precommit_hooks = _read_precommit_local_hooks(_read_yaml_mapping(_ROOT / ".pre-commit-config.yaml"))
    typecheck_hook = precommit_hooks["typecheck-frontend"]
    typecheck_pattern = re.compile(_P06_TYPECHECK_SCOPE)

    assert typecheck_hook.get("files") == _P06_TYPECHECK_SCOPE
    assert typecheck_hook.get("pass_filenames") is False
    assert typecheck_hook.get("stages") == ["manual"]

    tsconfig = json.loads((_ROOT / "serve/cockpit/web/tsconfig.json").read_text(encoding="utf-8"))
    assert isinstance(tsconfig, dict)
    assert tsconfig.get("include") == ["src", "vite.config.ts", "vitest.setup.ts"]

    for path, expected in _P06_SCOPE_SAMPLES:
        assert bool(typecheck_pattern.search(path)) is expected, path
