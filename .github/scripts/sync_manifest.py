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
    return payload


def paths_for_scope(scope: str, manifest: dict[str, Any] | None = None) -> list[str]:
    """Return ordered, duplicate-free paths for one sync scope."""
    data = _load_manifest() if manifest is None else manifest
    scopes = data["scopes"]
    scope_names = tuple(scopes) if scope == "all" else (scope,)
    paths: list[str] = []
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


def main() -> int:
    """Print a manifest projection for shell workflow consumers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("projection", choices=("paths", "excluded"))
    parser.add_argument("scope", nargs="?")
    args = parser.parse_args()

    if args.projection == "paths":
        if args.scope is None:
            parser.error("paths requires a scope")
        values = paths_for_scope(args.scope)
    else:
        if args.scope is not None:
            parser.error("excluded does not accept a scope")
        values = consumer_excluded_paths()
    print(" ".join(values))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
