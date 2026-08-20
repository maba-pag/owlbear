"""Classify dependency-update diffs for focused CI proof."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


_PYTHON_FILES = {".python-version", "pyproject.toml", "uv.lock"}
_SHARED_NODE_RUNTIME_FILES = {"serve/cockpit/web/.nvmrc"}
_COCKPIT_NODE_FILES = {
    "serve/cockpit/web/.nvmrc",
    "serve/cockpit/web/package-lock.json",
    "serve/cockpit/web/package.json",
}
_ROOT_NODE_FILES = {"package-lock.json", "package.json"}
_DIAGRAM_NODE_FILES = {
    ".owlbear/scripts/export-diagrams/package-lock.json",
    ".owlbear/scripts/export-diagrams/package.json",
}
_PDS_PACKAGES = (
    "@porsche-design-system/components-js",
    "@porsche-design-system/components-react",
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
    workflows: bool
    megalinter: bool
    renovate: bool

    @property
    def compatibility(self) -> bool:
        """Return whether a non-runtime compatibility proof is required."""
        return self.precommit or self.workflows or self.megalinter or self.renovate

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


def classify_dependency_change(paths: Iterable[str], diff: str) -> DependencyScope:
    """Classify changed paths and dependency declarations into proof surfaces."""
    changed = {path for path in paths if path}
    python = bool(changed & _PYTHON_FILES) or any(
        path.startswith("serve/") and path.endswith("/pyproject.toml") for path in changed
    )
    node = bool(changed & _COCKPIT_NODE_FILES)
    shared_node_runtime = bool(changed & _SHARED_NODE_RUNTIME_FILES)
    root_node = bool(changed & _ROOT_NODE_FILES)
    diagrams = bool(changed & _DIAGRAM_NODE_FILES)
    workflows = any(path.startswith(".github/workflows/") for path in changed)
    megalinter = ".mega-linter.yml" in changed
    renovate = ".github/renovate.json" in changed
    precommit = ".pre-commit-config.yaml" in changed

    return DependencyScope(
        python=python,
        node=node,
        shared_node_runtime=shared_node_runtime,
        root_node=root_node,
        diagrams=diagrams,
        pds=node and any(package in diff for package in _PDS_PACKAGES),
        precommit=precommit,
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
    parser.add_argument("--github-output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    scope = classify_dependency_change(
        _read_paths(args.paths_file),
        args.diff_file.read_text(encoding="utf-8"),
    )
    values = scope.github_outputs()
    _write_outputs(args.github_output, values)
    with args.summary.open("a", encoding="utf-8") as summary:
        summary.write("## Dependency classification\n\n")
        summary.write(f"```json\n{json.dumps(values, indent=2)}\n```\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
