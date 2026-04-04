"""CLI entrypoint for the OwlBear analysis pipeline."""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

from owlbear_orchestrator.analysis.analyze import analyze
from owlbear_orchestrator.analysis.formatters import format_json, format_markdown

_DEFAULT_AUDIT_DIR = Path("data/audit/")
_DEFAULT_WINDOW = timedelta(days=36500)  # scan all history


def main(argv: list[str] | None = None) -> int:
    """Parse argv, run analyze(), format results, print to stdout. Returns exit code."""
    parser = argparse.ArgumentParser(description="OwlBear analysis pipeline")
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        dest="format",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=None,
        metavar="HOURS",
        help="Time window in hours (default: scan all history)",
    )
    parser.add_argument(
        "--audit-dir",
        default=str(_DEFAULT_AUDIT_DIR),
        metavar="PATH",
        help="Path to audit log directory (default: data/audit/)",
    )

    args = parser.parse_args(argv)

    audit_dir = Path(args.audit_dir)
    window = timedelta(hours=args.window) if args.window is not None else _DEFAULT_WINDOW

    try:
        proposals = analyze(audit_dir, window=window)
        if args.format == "json":
            sys.stdout.write(format_json(proposals) + "\n")
        else:
            sys.stdout.write(format_markdown(proposals) + "\n")
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Error: {exc}\n")
        return 1
    else:
        return 0
