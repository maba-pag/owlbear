"""Finalize the external bootstrap carrier after native terminal proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from owlbear_kanban import (
    BootstrapFinalizationError,
    BootstrapFinalizationRequest,
    BootstrapFinalizationResult,
    LegacySnapshotError,
    finalize_bootstrap_carrier,
)


def run(workspace: Path, request_path: Path) -> BootstrapFinalizationResult:
    """Load one request document and execute the core finalization transaction."""
    request = BootstrapFinalizationRequest.model_validate_json(request_path.read_bytes())
    return finalize_bootstrap_carrier(workspace, request)


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
    except ValidationError as exc:
        _print(
            {
                "ok": False,
                "error": {
                    "code": "ERR_BOOTSTRAP_FINALIZATION_REQUEST_INVALID",
                    "detail": str(exc),
                },
            }
        )
        return 2
    except (BootstrapFinalizationError, LegacySnapshotError) as exc:
        _print({"ok": False, "error": {"code": exc.code, "detail": str(exc)}})
        return 2
    _print({"ok": True, "result": result.model_dump(mode="json")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
