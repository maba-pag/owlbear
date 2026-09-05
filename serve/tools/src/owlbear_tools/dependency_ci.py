"""Classify dependency-update diffs for focused CI proof."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping


_PYTHON_FILES = {".python-version", "pyproject.toml", "uv.lock"}
_SHARED_NODE_RUNTIME_FILES = {"serve/cockpit/web/.nvmrc"}
_COCKPIT_NODE_FILES = {
    "serve/cockpit/web/.nvmrc",
    "serve/cockpit/web/package-lock.json",
    "serve/cockpit/web/package.json",
}
_ROOT_NODE_FILES = {"package-lock.json", "package.json"}
_DIAGRAM_FILES = {".owlbear/scripts/diagrams/archify.lock.json"}
_RUFF_TOOLCHAIN_FILES = {
    ".github/scripts/check_ruff_toolchain.py",
}
_RUFF_SNAPSHOT_FILES = {
    ".github/workflows/megalinter.yml",
    ".mega-linter.yml",
    ".pre-commit-config.yaml",
    "pyproject.toml",
    "uv.lock",
}
_RUFF_PRE_COMMIT_REPOSITORY = "https://github.com/astral-sh/ruff-pre-commit"
_RUFF_DEPENDENCY_PATTERN = re.compile(r"^ruff(?:\[[^\]]+\])?(?:\s*[<>=!~].*)?$", re.IGNORECASE)
_RUFF_PRE_COMMIT_REPOSITORY_BLOCK = re.compile(
    rf"(?ms)^[ \t]*-[ \t]+repo:[ \t]*{re.escape(_RUFF_PRE_COMMIT_REPOSITORY)}[ \t]*(?:#.*)?\n"
    r"(?P<body>.*?)(?=^[ \t]*-[ \t]+repo:|\Z)",
)
_RUFF_PRE_COMMIT_REVISION = re.compile(r"(?m)^[ \t]+rev:[ \t]*(?P<revision>\S+)")
_MEGALINTER_ACTION_REFERENCE = re.compile(
    r"(?m)^[ \t]*uses:[ \t]*oxsecurity/megalinter(?:/flavors/[a-z0-9-]+)?@[^\s#]+(?:[ \t]+#.*)?$",
)
_PDS_PACKAGES = (
    "@porsche-design-system/components-js",
    "@porsche-design-system/components-react",
)


def _raise_runtime_error(message: str) -> NoReturn:
    """Raise one named dependency-classification failure."""
    raise RuntimeError(message)


def _git_executable() -> str:
    """Return the available Git executable used for snapshot reads."""
    executable = shutil.which("git")
    if executable is None:
        _raise_runtime_error("git is required for dependency snapshot classification")
    return executable


def _read_revision_files(root: Path, revision: str, paths: Iterable[str]) -> dict[str, str | None]:
    """Read selected files from one validated Git revision."""
    git = _git_executable()
    verified = subprocess.run(  # noqa: S603
        [git, "rev-parse", "--verify", f"{revision}^{{commit}}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if verified.returncode:
        detail = verified.stderr.strip() or verified.stdout.strip() or "unknown Git revision"
        _raise_runtime_error(f"unable to resolve dependency snapshot revision {revision}: {detail}")

    contents: dict[str, str | None] = {}
    for path in sorted(paths):
        exists = subprocess.run(  # noqa: S603
            [git, "cat-file", "-e", f"{revision}:{path}"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if exists.returncode:
            contents[path] = None
            continue
        shown = subprocess.run(  # noqa: S603
            [git, "show", f"{revision}:{path}"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if shown.returncode:
            detail = shown.stderr.strip() or shown.stdout.strip() or "unable to read file"
            _raise_runtime_error(f"unable to read {path} from {revision}: {detail}")
        contents[path] = shown.stdout
    return contents


def _collect_ruff_dependencies(value: object) -> list[str]:
    """Collect Ruff requirement strings from parsed TOML dependency sections."""
    if isinstance(value, str):
        candidate = value.strip()
        return [candidate] if _RUFF_DEPENDENCY_PATTERN.fullmatch(candidate) is not None else []
    if isinstance(value, dict):
        return [dependency for child in value.values() for dependency in _collect_ruff_dependencies(child)]
    if isinstance(value, list):
        return [dependency for child in value for dependency in _collect_ruff_dependencies(child)]
    return []


def _ruff_dependency_values(content: str | None) -> tuple[str, ...] | None:
    """Return normalized Ruff requirements from one root Python manifest."""
    if content is None:
        return ()
    try:
        document = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return None
    values = _collect_ruff_dependencies(document.get("project", {}))
    values.extend(_collect_ruff_dependencies(document.get("dependency-groups", {})))
    return tuple(sorted(values))


def _ruff_lock_values(content: str | None) -> tuple[str, ...] | None:
    """Return Ruff package versions from one uv lockfile."""
    if content is None:
        return ()
    try:
        document = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return None
    packages = document.get("package", [])
    if not isinstance(packages, list):
        return None
    versions: list[str] = []
    for package in packages:
        if not isinstance(package, dict) or package.get("name") != "ruff":
            continue
        version = package.get("version")
        if not isinstance(version, str):
            return None
        versions.append(version)
    return tuple(sorted(versions))


def _ruff_pre_commit_values(content: str | None) -> tuple[str, ...] | None:
    """Return Ruff pre-commit revisions from one hook manifest."""
    if content is None:
        return ()
    if _RUFF_PRE_COMMIT_REPOSITORY not in content:
        return ()
    matches = list(_RUFF_PRE_COMMIT_REPOSITORY_BLOCK.finditer(content))
    if not matches:
        return None
    revisions: list[str] = []
    for match in matches:
        revision = _RUFF_PRE_COMMIT_REVISION.search(match.group("body"))
        if revision is None:
            return None
        revisions.append(revision.group("revision").strip("\"'"))
    return tuple(sorted(revisions))


def _config_value(content: str, key: str) -> str | None:
    """Read one top-level scalar YAML field without requiring third-party parsing."""
    match = re.search(rf"(?m)^{re.escape(key)}:[ \t]*(?P<value>[^#\r\n]+)", content)
    if match is None:
        return None
    return match.group("value").strip().strip("\"'")


def _megalinter_metadata(content: str | None) -> tuple[str, str] | None:
    """Return the MegaLinter flavor and version that select the runtime image."""
    if content is None:
        return None
    flavor = _config_value(content, "MEGALINTER_FLAVOR") or "all"
    version = _config_value(content, "MEGALINTER_VERSION")
    return None if version is None else (flavor, version)


def _megalinter_action_values(content: str | None) -> tuple[str, ...]:
    """Return full MegaLinter action reference lines from one workflow."""
    if content is None:
        return ()
    return tuple(_MEGALINTER_ACTION_REFERENCE.findall(content))


def _changed_snapshot_value(
    path: str,
    before_files: Mapping[str, str | None] | None,
    after_files: Mapping[str, str | None] | None,
    extractor: Callable[[str | None], object],
) -> bool:
    """Return whether one parsed value changed, conservatively on parse failure."""
    if before_files is None or after_files is None:
        return False
    before = before_files.get(path)
    after = after_files.get(path)
    if before == after:
        return False
    before_value = extractor(before)  # type: ignore[operator]
    after_value = extractor(after)  # type: ignore[operator]
    return before_value is None or after_value is None or before_value != after_value


def _ruff_toolchain_changed(
    changed: set[str],
    before_files: Mapping[str, str | None] | None,
    after_files: Mapping[str, str | None] | None,
) -> bool:
    """Return whether a maintained Ruff or MegaLinter version declaration changed."""
    if changed & _RUFF_TOOLCHAIN_FILES:
        return True
    return (
        _changed_snapshot_value("pyproject.toml", before_files, after_files, _ruff_dependency_values)
        or _changed_snapshot_value("uv.lock", before_files, after_files, _ruff_lock_values)
        or _changed_snapshot_value(
            ".pre-commit-config.yaml",
            before_files,
            after_files,
            _ruff_pre_commit_values,
        )
        or _changed_snapshot_value(".mega-linter.yml", before_files, after_files, _megalinter_metadata)
        or _changed_snapshot_value(
            ".github/workflows/megalinter.yml",
            before_files,
            after_files,
            _megalinter_action_values,
        )
    )


@dataclass(frozen=True, slots=True)
class DependencyScope:
    """Proof surfaces affected by one pull-request diff."""

    python: bool
    node: bool
    shared_node_runtime: bool
    root_node: bool
    diagrams: bool
    pds: bool
    precommit: bool
    ruff_toolchain: bool
    workflows: bool
    megalinter: bool
    renovate: bool

    @property
    def compatibility(self) -> bool:
        """Return whether a non-runtime compatibility proof is required."""
        return self.precommit or self.ruff_toolchain or self.workflows or self.megalinter or self.renovate

    @property
    def applicable(self) -> bool:
        """Return whether the diff contains a maintained dependency surface."""
        return (
            self.python
            or self.node
            or self.shared_node_runtime
            or self.root_node
            or self.diagrams
            or self.compatibility
        )

    def github_outputs(self) -> dict[str, str]:
        """Serialize classifications as GitHub Actions boolean outputs."""
        values = asdict(self) | {"applicable": self.applicable, "compatibility": self.compatibility}
        return {key: str(value).lower() for key, value in values.items()}


def classify_dependency_change(
    paths: Iterable[str],
    diff: str,
    *,
    before_files: Mapping[str, str | None] | None = None,
    after_files: Mapping[str, str | None] | None = None,
) -> DependencyScope:
    """Classify changed paths and dependency declarations into proof surfaces."""
    changed = {path for path in paths if path}
    python = bool(changed & _PYTHON_FILES) or any(
        path.startswith("serve/") and path.endswith("/pyproject.toml") for path in changed
    )
    node = bool(changed & _COCKPIT_NODE_FILES)
    shared_node_runtime = bool(changed & _SHARED_NODE_RUNTIME_FILES)
    root_node = bool(changed & _ROOT_NODE_FILES)
    diagrams = bool(changed & _DIAGRAM_FILES) or any(
        path.startswith((".owlbear/scripts/diagrams/", "share/diagrams/")) for path in changed
    )
    workflows = any(path.startswith(".github/workflows/") for path in changed)
    megalinter = ".mega-linter.yml" in changed
    renovate = ".github/renovate.json" in changed
    precommit = ".pre-commit-config.yaml" in changed
    ruff_toolchain = _ruff_toolchain_changed(changed, before_files, after_files)

    return DependencyScope(
        python=python,
        node=node,
        shared_node_runtime=shared_node_runtime,
        root_node=root_node,
        diagrams=diagrams,
        pds=node and any(package in diff for package in _PDS_PACKAGES),
        precommit=precommit,
        ruff_toolchain=ruff_toolchain,
        workflows=workflows,
        megalinter=megalinter,
        renovate=renovate,
    )


def _read_paths(path: Path) -> list[str]:
    """Read a NUL-delimited changed-path file."""
    return [value.decode("utf-8") for value in path.read_bytes().split(b"\0") if value]


def _write_outputs(path: Path, values: dict[str, str]) -> None:
    """Append classified values to a GitHub Actions output file."""
    with path.open("a", encoding="utf-8") as output:
        for key, value in values.items():
            output.write(f"{key}={value}\n")


def main() -> int:
    """Classify files supplied by a workflow and publish GitHub outputs."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--paths-file", type=Path, required=True)
    parser.add_argument("--diff-file", type=Path, required=True)
    parser.add_argument("--base-ref")
    parser.add_argument("--head-ref")
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--github-output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    paths = _read_paths(args.paths_file)
    if (args.base_ref is None) != (args.head_ref is None):
        parser.error("--base-ref and --head-ref must be supplied together")
    before_files = after_files = None
    if args.base_ref is not None and args.head_ref is not None:
        snapshot_paths = set(paths) & _RUFF_SNAPSHOT_FILES
        before_files = _read_revision_files(args.repository_root, args.base_ref, snapshot_paths)
        after_files = _read_revision_files(args.repository_root, args.head_ref, snapshot_paths)

    scope = classify_dependency_change(
        paths,
        args.diff_file.read_text(encoding="utf-8"),
        before_files=before_files,
        after_files=after_files,
    )
    values = scope.github_outputs()
    _write_outputs(args.github_output, values)
    with args.summary.open("a", encoding="utf-8") as summary:
        summary.write("## Dependency classification\n\n")
        summary.write(f"```json\n{json.dumps(values, indent=2)}\n```\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
