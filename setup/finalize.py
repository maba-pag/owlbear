"""Finalize one pre-cutover workspace into the target delivery runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from owlbear_kanban import (
    TargetAuthorityRegistry,
    TargetCutoverError,
    TargetCutoverRequest,
    TargetCutoverResult,
    TargetRuntime,
    cut_over_target_runtime,
)


def _smoke_target_runtime(workspace: Path, request: TargetCutoverRequest) -> None:
    """Load every staged authority and runtime before receipt publication."""
    target_root = workspace / request.target_path
    authorities = TargetAuthorityRegistry(target_root).list_authorities()
    if authorities != request.authorities:
        message = "staged target authorities differ from the cutover request"
        raise RuntimeError(message)
    for authority in authorities:
        TargetRuntime(authority, target_root / "changes" / authority.change_id).list_frontier()


def run(workspace: Path, request_path: Path) -> TargetCutoverResult:
    """Load one request document and execute the target cutover transaction."""
    request = TargetCutoverRequest.model_validate_json(request_path.read_bytes())
    return cut_over_target_runtime(workspace.resolve(), request, smoke=_smoke_target_runtime)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    return parser


def _print(payload: object) -> None:
    print(json.dumps(payload, sort_keys=True, indent=2))


def main(argv: list[str] | None = None) -> int:
    """CLI entry point returning structured success or failure."""
    args = _build_parser().parse_args(argv)
    try:
        result = run(args.workspace, args.request)
    except (OSError, ValidationError) as exc:
        _print(
            {
                "ok": False,
                "error": {
                    "code": "ERR_TARGET_CUTOVER_REQUEST_INVALID",
                    "detail": str(exc),
                },
            }
        )
        return 2
    except TargetCutoverError as exc:
        _print({"ok": False, "error": {"code": exc.code, "detail": str(exc)}})
        return 2
    _print({"ok": True, "result": result.model_dump(mode="json")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
