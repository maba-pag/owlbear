"""``delivery-repair``: classify Delivery state offline and apply fenced repair proposals.

``classify`` and ``propose`` write no authoritative byte. ``apply``, ``resume``, ``verify`` and
``abort`` take the workspace controller lock exclusively and refuse while any Delivery controller
runs (stop Delivery MCP and Cockpit first). User-confirmed operations need ``--confirm`` with the
exact proposal ID. Output never contains record values or absolute paths.

Only the standard library is imported at module load: when Delivery itself cannot be imported, the
command still reports a maintenance finding beside the stdlib inspector's findings (N08 I7).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_FINDINGS = "findings"
_INVALID_INVOCATION = 2
_OFFLINE_COMMANDS = frozenset({"propose", "apply", "resume", "verify", "abort"})
# I1: no running process is exempt, so the user keeps every controller stopped through the whole repair.
MAINTENANCE_PRECONDITION = (
    "Offline maintenance: stop Delivery MCP and every Cockpit process for this project before apply, "
    "and do not restart any of them until delivery-repair verify or abort has finished."
)


class _InvocationError(Exception):
    """A command-line error that must not echo the caller's input."""


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:  # type: ignore[override]
        raise _InvocationError


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="delivery-repair", description=__doc__.splitlines()[0], add_help=False)
    parser.add_argument("--project-root", type=Path, default=None)
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    classify = commands.add_parser("classify", add_help=False)
    classify.add_argument("--change-id", default=None)
    classify.add_argument("--format", choices=("json", "text"), default="json")
    commands.add_parser("propose", add_help=False).add_argument("finding_id")
    apply = commands.add_parser("apply", add_help=False)
    apply.add_argument("--proposal", required=True)
    apply.add_argument("--confirm", default=None)
    for name in ("resume", "verify", "abort"):
        commands.add_parser(name, add_help=False).add_argument("proposal_id")
    return parser


def _maintenance(error: BaseException, root: Path) -> dict[str, object]:
    """C09: Delivery could not be imported; report the class only, beside the stdlib inspector."""
    finding = {
        "finding_id": "C09:controller-import",
        "catalogue": "C09",
        "code": "controller-import-failed",
        "scope": "workspace",
        "locator": "owlbear_delivery",
        "route": "maintenance",
        "operation": "maintenance route (programme section 11.2)",
        "owner": "user: approve a reviewed platform fix and upgrade",
        "resume_condition": "after a reviewed controller release imports, rerun delivery-repair classify",
        "exception_class": type(error).__name__,
    }
    from owlbear_tools import delivery_diagnostics  # noqa: PLC0415 - stdlib-only bootstrap, loaded only here.

    try:
        inspection = delivery_diagnostics.inspect_delivery(root)
    except OSError, ValueError:
        inspection = {"status": "unavailable", "diagnostic_codes": []}
    return {
        "status": _FINDINGS,
        _FINDINGS: [finding],
        "inspector": {
            "status": inspection.get("status"),
            "diagnostic_codes": inspection.get("diagnostic_codes", []),
        },
    }


def _journal_payload(journal: object) -> dict[str, object]:
    return {
        "status": journal.state,  # type: ignore[attr-defined]
        "proposal_id": journal.migration_id,  # type: ignore[attr-defined]
        "kind": journal.kind,  # type: ignore[attr-defined]
    }


def _proposal_payload(proposal: object, migration_state_root: str) -> dict[str, object]:
    proposal_id = proposal.proposal_id  # type: ignore[attr-defined]
    return {
        "status": "proposed",
        "proposal_id": proposal_id,
        "finding_id": proposal.finding_id,  # type: ignore[attr-defined]
        "operation": proposal.operation,  # type: ignore[attr-defined]
        "policy": proposal.policy,  # type: ignore[attr-defined]
        "consequence": proposal.consequence,  # type: ignore[attr-defined]
        "paths": [
            {"locator": entry.locator, "role": entry.role, "change": _path_change(entry)}
            for entry in proposal.entries  # type: ignore[attr-defined]
        ],
        "backup": f"{migration_state_root}/{proposal_id}/backup",
        "staging": f"{migration_state_root}/{proposal_id}/stage",
    }


def _path_change(entry: object) -> str:
    before, after = entry.before_sha256, entry.after_sha256  # type: ignore[attr-defined]
    if before == after:
        return "unchanged"
    return "absent" if after is None else "set"


def run(argv: list[str] | None = None) -> tuple[int, dict[str, object], str]:
    """Execute one command and return its exit status, payload and output format."""
    try:
        args = _parser().parse_args(argv)
    except _InvocationError:
        return _INVALID_INVOCATION, {"status": "invalid-invocation"}, "json"
    output = getattr(args, "format", "json")
    root = (args.project_root or Path.cwd()).resolve()
    try:
        from owlbear_delivery import state_migration, state_repair  # noqa: PLC0415 - I7: imported inside main only.
    except Exception as exc:  # noqa: BLE001 - any import failure is a C09 maintenance finding (I7).
        return 1, _maintenance(exc, root), output
    try:
        code, payload = _execute(args, root, state_repair, state_migration)
    except state_migration.MigrationError as exc:
        code, payload = 1, {"status": "refused", "code": exc.code, "detail": exc.detail, "locator": exc.locator}
    if args.command in _OFFLINE_COMMANDS:
        payload["precondition"] = MAINTENANCE_PRECONDITION
    return code, payload, output


def _execute(args: argparse.Namespace, root: Path, repair: object, migration: object) -> tuple[int, dict[str, object]]:
    command = args.command
    if command == "classify":
        report = repair.classify(root, args.change_id)  # type: ignore[attr-defined]
        findings = [finding.as_dict() for finding in report.findings]
        return (1 if findings else 0), {"status": _FINDINGS if findings else "healthy", _FINDINGS: findings}
    if command == "propose":
        proposal = repair.propose(root, args.finding_id)  # type: ignore[attr-defined]
        return 0, _proposal_payload(proposal, migration.MIGRATION_STATE_ROOT)  # type: ignore[attr-defined]
    if command == "apply":
        journal = repair.apply(root, args.proposal, confirm=args.confirm)  # type: ignore[attr-defined]
        return 0, _journal_payload(journal)
    if command == "abort":
        result = repair.abort(root, args.proposal_id)  # type: ignore[attr-defined]
        return 0, {**_journal_payload(result.journal), "namespace_removed": result.namespace_removed}
    journal = getattr(repair, command)(root, args.proposal_id)
    return 0, _journal_payload(journal)


def _text(payload: dict[str, object]) -> str:
    findings = payload.get(_FINDINGS)
    if not isinstance(findings, list):
        return json.dumps(payload, indent=2, sort_keys=True)
    if not findings:
        return "healthy: no findings"
    return "\n".join(
        f"{item['finding_id']}: {item['route']} -> {item['operation']} (owner: {item['owner']}; "
        f"resume: {item['resume_condition']})"
        for item in findings
    )


def main(argv: list[str] | None = None) -> int:
    """Console entry point: print one JSON object (or text for ``classify --format text``)."""
    code, payload, output_format = run(argv)
    output = _text(payload) if output_format == "text" else json.dumps(payload, indent=2, sort_keys=True)
    sys.stdout.write(output + "\n")
    return code


if __name__ == "__main__":  # pragma: no cover - console entry point.
    raise SystemExit(main())
