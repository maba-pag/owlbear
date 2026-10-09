"""``delivery-migrate``: run one fenced Delivery state migration step offline.

Every step except ``propose`` takes the workspace controller lock exclusively and refuses while a
Delivery controller (MCP or Cockpit) runs. The project root defaults to the current directory, as
the controller derives its workspace from its working directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from owlbear_delivery import state_migration
from owlbear_delivery.state_migration import MigrationError, MigrationJournal, MigrationProposal

_STEPS = ("apply", "resume", "verify", "abort")


def _proposal_payload(proposal: MigrationProposal) -> dict[str, object]:
    return {
        "status": "proposed",
        "migration_id": proposal.migration_id,
        "source_format": proposal.source_format,
        "target_format": proposal.target_format,
        "steps": list(proposal.steps),
        "release": proposal.release,
        "entries": [entry.model_dump(mode="json") for entry in proposal.entries],
        "staging": f"{state_migration.MIGRATION_STATE_ROOT}/{proposal.migration_id}/stage",
    }


def _journal_payload(journal: MigrationJournal) -> dict[str, object]:
    return {
        "status": journal.state,
        "migration_id": journal.migration_id,
        "source_format": journal.source_format,
        "target_format": journal.target_format,
        "batches": [batch.model_dump(mode="json") for batch in journal.batches],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="delivery-migrate", description=__doc__.splitlines()[0])
    parser.add_argument("--project-root", type=Path, default=None, help="workspace root (default: cwd)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("propose", help="stage registered rewrites and the format marker; writes no record")
    for name in _STEPS:
        command = commands.add_parser(name)
        command.add_argument("migration_id")
    return parser


def run(argv: list[str] | None = None) -> tuple[int, dict[str, object]]:
    """Execute one step and return its exit status and JSON payload."""
    args = _parser().parse_args(argv)
    root = (args.project_root or Path.cwd()).resolve()
    try:
        if args.command == "propose":
            return 0, _proposal_payload(state_migration.propose(root))
        # Controllers older than the lock take none; the lock alone cannot prove that none runs.
        state_migration.require_no_controller_process(root)
        if args.command == "abort":
            result = state_migration.abort(root, args.migration_id)
            return 0, {**_journal_payload(result.journal), "namespace_removed": result.namespace_removed}
        journal = getattr(state_migration, args.command)(root, args.migration_id)
        return 0, _journal_payload(journal)
    except MigrationError as exc:
        return 1, {"status": "refused", "code": exc.code, "detail": exc.detail, "locator": exc.locator}


def main(argv: list[str] | None = None) -> int:
    """Console entry point: print one JSON object; exit 1 on a typed refusal."""
    code, payload = run(argv)
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return code


if __name__ == "__main__":  # pragma: no cover - console entry point.
    raise SystemExit(main())
