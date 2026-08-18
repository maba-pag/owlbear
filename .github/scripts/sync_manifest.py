"""Read the dev-to-main consumer sync manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_MANIFEST_PATH = Path(__file__).resolve().parent.parent / "sync-manifest.json"
_INVALID_OBJECT_MESSAGE = "sync manifest must be a JSON object"
_INVALID_FIELDS_MESSAGE = "sync manifest must define scopes and consumer_excluded_paths"
_INVALID_EXCLUDED_MESSAGE = "consumer_excluded_paths must contain non-empty strings"
_INVALID_GROUPS_MESSAGE = "scope_groups must define valid scopes and paths"
_INVALID_SOURCE_ONLY_MESSAGE = "source_only_paths must contain non-empty strings"


def _load_manifest(path: Path = _MANIFEST_PATH) -> dict[str, Any]:
    """Load and validate the sync manifest."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(_INVALID_OBJECT_MESSAGE)
    scopes = payload.get("scopes")
    excluded_paths = payload.get("consumer_excluded_paths")
    if not isinstance(scopes, dict) or not isinstance(excluded_paths, list):
        raise TypeError(_INVALID_FIELDS_MESSAGE)
    for scope_name, paths in scopes.items():
        if (
            not isinstance(scope_name, str)
            or not isinstance(paths, list)
            or not all(isinstance(path, str) and path for path in paths)
        ):
            message = f"invalid paths for sync scope: {scope_name!r}"
            raise TypeError(message)
    if not all(isinstance(path, str) and path for path in excluded_paths):
        raise TypeError(_INVALID_EXCLUDED_MESSAGE)
    scope_groups = payload.get("scope_groups", {})
    _validate_scope_groups(scope_groups, scopes)
    source_only_paths = payload.get("source_only_paths", [])
    _validate_source_only_paths(source_only_paths)
    return payload


def _validate_scope_groups(scope_groups: object, scopes: dict[str, Any]) -> None:
    """Validate optional manifest groups and their referenced scopes."""
    if not isinstance(scope_groups, dict):
        raise TypeError(_INVALID_GROUPS_MESSAGE)
    for group_name, group in scope_groups.items():
        if not isinstance(group_name, str) or not isinstance(group, dict):
            raise TypeError(_INVALID_GROUPS_MESSAGE)
        group_scopes = group.get("scopes")
        group_paths = group.get("paths")
        if (
            not isinstance(group_scopes, list)
            or not all(isinstance(scope, str) and scope in scopes for scope in group_scopes)
            or not isinstance(group_paths, list)
            or not all(isinstance(path, str) and path for path in group_paths)
        ):
            raise TypeError(_INVALID_GROUPS_MESSAGE)


def _validate_source_only_paths(source_only_paths: object) -> None:
    """Validate source paths that are transformed before publication."""
    if not isinstance(source_only_paths, list) or not all(isinstance(path, str) and path for path in source_only_paths):
        raise TypeError(_INVALID_SOURCE_ONLY_MESSAGE)


def paths_for_scope(scope: str, manifest: dict[str, Any] | None = None) -> list[str]:
    """Return ordered, duplicate-free paths for one sync scope."""
    data = _load_manifest() if manifest is None else manifest
    scopes = data["scopes"]
    scope_names = tuple(scopes) if scope == "all" else (scope,)
    paths: list[str] = []
    if scope == "all":
        for group in data.get("scope_groups", {}).values():
            for path in group.get("paths", []):
                if path not in paths:
                    paths.append(path)
    for scope_name in scope_names:
        scope_paths = scopes.get(scope_name)
        if scope_paths is None:
            message = f"unknown sync scope: {scope}"
            raise ValueError(message)
        for path in scope_paths:
            if path not in paths:
                paths.append(path)
    return paths


def consumer_excluded_paths(manifest: dict[str, Any] | None = None) -> list[str]:
    """Return paths that must never be published to the consumer branch."""
    data = _load_manifest() if manifest is None else manifest
    return list(data["consumer_excluded_paths"])


def scope_names_for_group(group: str, manifest: dict[str, Any] | None = None) -> list[str]:
    """Return the ordered sync scopes in one manifest group."""
    data = _load_manifest() if manifest is None else manifest
    group_data = data.get("scope_groups", {}).get(group)
    if group_data is None:
        message = f"unknown sync scope group: {group}"
        raise ValueError(message)
    return list(group_data["scopes"])


def paths_for_group(group: str, manifest: dict[str, Any] | None = None) -> list[str]:
    """Return ordered, duplicate-free paths for one manifest group."""
    data = _load_manifest() if manifest is None else manifest
    group_data = data.get("scope_groups", {}).get(group)
    if group_data is None:
        message = f"unknown sync scope group: {group}"
        raise ValueError(message)
    paths: list[str] = []
    for path in group_data["paths"]:
        if path not in paths:
            paths.append(path)
    for scope in group_data["scopes"]:
        for path in paths_for_scope(scope, data):
            if path not in paths:
                paths.append(path)
    return paths


def source_only_paths(manifest: dict[str, Any] | None = None) -> list[str]:
    """Return source paths that map to generated or otherwise different consumer paths."""
    data = _load_manifest() if manifest is None else manifest
    return list(data.get("source_only_paths", []))


def main() -> int:
    """Print a manifest projection for shell workflow consumers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("projection", choices=("paths", "group-paths", "scopes", "excluded", "source-only"))
    parser.add_argument("scope", nargs="?")
    args = parser.parse_args()

    if args.projection == "paths":
        if args.scope is None:
            parser.error("paths requires a scope")
        values = paths_for_scope(args.scope)
    elif args.projection == "group-paths":
        if args.scope is None:
            parser.error("group-paths requires a group")
        values = paths_for_group(args.scope)
    elif args.projection == "scopes":
        if args.scope is None:
            parser.error("scopes requires a group")
        values = scope_names_for_group(args.scope)
    elif args.projection == "source-only":
        if args.scope is not None:
            parser.error("source-only does not accept a scope")
        values = source_only_paths()
    else:
        if args.scope is not None:
            parser.error("excluded does not accept a scope")
        values = consumer_excluded_paths()
    print(" ".join(values))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
