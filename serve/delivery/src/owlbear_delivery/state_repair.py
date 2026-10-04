"""Offline Delivery repair (N08-A): classify findings and apply fenced proposals below composition.

``classify`` gives every finding exactly one route, owner and resume condition (I8). Only the catalogued
offline operations write: C01 ``host-local-reset``, C02 ``tracked-record-restore`` and C03
``transaction-replay``; they run through ``state_migration`` as same-format repairs (D1) under its fence,
journal and backup. Unknown corruption is preserved and only diagnosed (C07). Nothing here calls
``load_delivery_application`` or constructs ``PortfolioApplication`` (R2).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import ValidationError

from owlbear_delivery import state_migration
from owlbear_delivery.acceptance import CompletionReceiptConflictError, CompletionReceiptStore
from owlbear_delivery.change_workspace import ChangeWorkspaceManager
from owlbear_delivery.delivery_admission import DeliveryAdmissionReceipt
from owlbear_delivery.delivery_application_loader import (
    DeliveryApplicationLoadError,
    DeliveryHostConfig,
    DeliveryStartupConfig,
    _DeliveryHostConfigOverrides,
    _derive_paths,
    _validate_git_config,
)
from owlbear_delivery.design_package import DesignPackageConflictError, verify_package_content
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.runtime_support import parse_delivery_frontier
from owlbear_delivery.runtime_transaction import (
    MoveTransactionParticipant,
    PendingTransaction,
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionManifestError,
    TransactionPathError,
)
from owlbear_delivery.state_formats import (
    DELIVERY_STATE_ROOT,
    FORMAT_MARKER,
    MIGRATIONS_ROOT,
    TRANSACTION_ROOTS,
    CapabilityReport,
    TransactionRoot,
    classify_kind,
    classify_record,
    scan_capability,
    transaction_root,
)
from owlbear_delivery.state_migration import (
    MIGRATION_STATE_ROOT,
    AbortResult,
    ControllerProcessSource,
    MigrationError,
    MigrationJournal,
    RepairEntry,
    RepairManifest,
    RepairParticipant,
    RepairProposal,
    live_journals,
    owner_rejections,
    path_digest,
    repair_proposal,
    require_no_open_journal,
)
from owlbear_delivery.workspace_models import ChangeCoordination

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery.state_migration import FailureHook

type Route = Literal["offline", "migrate", "upgrade", "online", "environment", "contained", "maintenance"]

HOST_LOCAL = "runtime/host.local.json"
HOST = "runtime/host.json"
CONFIG = "config.json"
CANONICAL_HOST_LOCAL = b'{"schema_version":1}\n'
_TRACKED_RECORDS = (CONFIG, HOST)
_PACKAGE_FILES = ("authority.json", "design.md", "intent.md", "manifest.json")
_SELF_HANDLED_KINDS = frozenset(
    {"config", "host", "host_local", "frontier", "admission", "package_manifest", "package_authority"}
)
_GIT_TIMEOUT_SECONDS = 30
_REPAIRER = "delivery-repair (/repair-delivery)"
_MAINTAINER = "Delivery maintainers (contained; no supported repair)"
_RESTART = "restart Delivery MCP and Cockpit after delivery-repair verify succeeds"


@dataclass(frozen=True, slots=True)
class RepairFinding:
    """One classified finding with exactly one route (I8); locators are Delivery-root-relative."""

    finding_id: str
    catalogue: str
    code: str
    scope: str
    locator: str
    route: Route
    operation: str
    owner: str
    resume_condition: str

    def as_dict(self) -> dict[str, str]:
        """Return the finding as plain strings."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RepairReport:
    """Every finding of one classification, in stable order."""

    findings: tuple[RepairFinding, ...] = ()

    @property
    def finding_ids(self) -> tuple[str, ...]:
        """Return the sorted finding IDs."""
        return tuple(sorted(finding.finding_id for finding in self.findings))


def _finding(  # noqa: PLR0913, PLR0917 - every finding names each routing field explicitly (I8).
    catalogue: str,
    code: str,
    locator: str,
    route: Route,
    operation: str,
    owner: str,
    resume_condition: str,
    *,
    scope: str = "workspace",
    key: str | None = None,
) -> RepairFinding:
    return RepairFinding(
        f"{catalogue}:{key or locator}", catalogue, code, scope, locator, route, operation, owner, resume_condition
    )


def _contained(code: str, locator: str, *, scope: str = "workspace") -> RepairFinding:
    return _finding(
        "C07",
        code,
        locator,
        "contained",
        "none",
        _MAINTAINER,
        "state stays preserved and refused; resume after the owner supplies a supported route",
        scope=scope,
    )


_CHANGE_SCOPED_RUNTIME = frozenset({"changes", "finalization-reports", "proof-attempts"})


def _change_scope(locator: str) -> str:
    parts = locator.split("/")
    if len(parts) > 2 and parts[0] == "runtime" and parts[1] in _CHANGE_SCOPED_RUNTIME:  # noqa: PLR2004
        return parts[2]
    if len(parts) > 1 and parts[0] == "packages" and parts[1] != "transactions":
        return parts[1]
    return "workspace"


@dataclass(frozen=True, slots=True)
class _Workspace:
    root: Path
    delivery: Path

    @classmethod
    def of(cls, workspace_root: Path) -> _Workspace:
        root = workspace_root.resolve()
        return cls(root, root / DELIVERY_STATE_ROOT)

    def read(self, locator: str) -> bytes | None:
        """Read one regular record without following links; ``None`` when absent."""
        path = self.delivery / locator
        if path.is_symlink() or (path.exists() and not path.is_file()):
            msg = "record is not a regular file"
            raise ValueError(msg)
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify(workspace_root: Path, change_id: str | None = None, *, verifying: str | None = None) -> RepairReport:
    """Classify Delivery state offline without writing; ``verifying`` drops only that repair journal (I9)."""
    workspace = _Workspace.of(workspace_root)
    report = scan_capability(workspace.root)
    if report.format_status == "newer":
        return RepairReport((_newer(FORMAT_MARKER),))
    if not report.complete:
        return RepairReport((_contained("inspection-incomplete", "."),))
    if not workspace.delivery.is_dir():
        return RepairReport()
    tracked = _tracked_findings(workspace, report)
    environment = _environment_findings(workspace)
    findings = [
        *_journal_findings(workspace, verifying),
        *_record_findings(report),
        *tracked,
        *_package_findings(workspace),
        *_change_findings(workspace, report),
        *_transaction_findings(workspace, report, startup_refused=bool(tracked or environment)),
        *environment,
    ]
    unique = {finding.finding_id: finding for finding in findings}
    selected = (
        finding for finding in unique.values() if change_id is None or finding.scope in {"workspace", change_id}
    )
    return RepairReport(tuple(sorted(selected, key=lambda finding: finding.finding_id)))


def _newer(locator: str) -> RepairFinding:
    return _finding(
        "C05",
        "state-newer-than-controller",
        locator,
        "upgrade",
        "/upgrade-delivery",
        "user: upgrade to a release whose registry includes this format (never a downgrade)",
        "after the upgrade the newer controller starts on this state",
        scope=_change_scope(locator),
    )


def _record_findings(report: CapabilityReport) -> list[RepairFinding]:
    findings: list[RepairFinding] = []
    migration_required = report.format_status == "migration-required"
    for record in report.records:
        if record.status == "newer":
            findings.append(_newer(record.locator))
        elif record.status == "migration-required":
            migration_required = True
        elif record.status in {"unknown-version", "unreadable"} and record.kind_id not in _SELF_HANDLED_KINDS:
            findings.append(_contained(f"record-{record.status}", record.locator, scope=_change_scope(record.locator)))
    if migration_required:
        findings.append(
            _finding(
                "C04",
                "state-migration-required",
                FORMAT_MARKER,
                "migrate",
                "delivery-migrate propose, apply, verify",
                "delivery-migrate (registered migration, N02-B)",
                "after delivery-migrate verify succeeds the controller starts",
                key="state-migration-required",
            )
        )
    return findings


# --- Journals (journal-state table) -------------------------------------------


_MIGRATE_COMMANDS = {
    "backed-up": "resume or abort",
    "applying": "resume or abort",
    "applied": "verify",
    "aborting": "abort",
}
_REPAIR_COMMANDS = {**_MIGRATE_COMMANDS, "applied": "verify or abort", "verified": "verify"}


def _journal_findings(workspace: _Workspace, verifying: str | None) -> list[RepairFinding]:
    try:
        entries = live_journals(workspace.root)
    except MigrationError, OSError:
        return [_contained("journal-invalid", MIGRATIONS_ROOT)]
    open_entries = [
        entry
        for entry in entries
        if (entry.journal is None or entry.journal.state != "verified" or entry.journal.kind == "repair")
        and not _is_verifying(entry.journal, verifying)
    ]
    if any(entry.journal is None for entry in open_entries) or len(open_entries) > 1:
        return [_contained("journal-invalid", entry.locator) for entry in open_entries]
    if open_entries:
        return [_journal_route(open_entries[0].locator, open_entries[0].journal)]  # type: ignore[arg-type]
    namespace = workspace.delivery / MIGRATIONS_ROOT
    if not entries and namespace.is_dir() and not namespace.is_symlink():
        return [_cleanup_route(workspace)]
    return []


def _is_verifying(journal: MigrationJournal | None, verifying: str | None) -> bool:
    return (
        journal is not None
        and verifying is not None
        and journal.migration_id == verifying
        and journal.kind == "repair"
        and journal.state == "applied"
    )


def _journal_route(locator: str, journal: MigrationJournal) -> RepairFinding:
    tool = "delivery-repair" if journal.kind == "repair" else "delivery-migrate"
    commands = (_REPAIR_COMMANDS if journal.kind == "repair" else _MIGRATE_COMMANDS)[journal.state]
    return _finding(
        "C04",
        "state-migration-incomplete",
        locator,
        "offline" if journal.kind == "repair" else "migrate",
        f"{tool} {commands} {journal.migration_id}",
        tool,
        f"after {tool} finishes this {journal.kind} journal the controller starts",
    )


def _cleanup_route(workspace: _Workspace) -> RepairFinding:
    """An empty namespace left after an archive: route to the newest archived journal's cleanup (I3)."""
    archives = sorted(
        (path for path in (workspace.root / MIGRATION_STATE_ROOT).glob("*/journal.json") if path.is_file()),
        key=lambda path: path.stat().st_mtime_ns,
    )
    journal = None
    if archives:
        try:
            journal = MigrationJournal.model_validate_json(archives[-1].read_bytes(), strict=True)
        except ValidationError, ValueError:
            journal = None
    commands = {("migration", "aborted"): "delivery-migrate abort", ("repair", "verified"): "delivery-repair verify"}
    commands["repair", "aborted"] = "delivery-repair abort"
    command = commands.get((journal.kind, journal.state)) if journal is not None else None
    if journal is None or command is None:
        return _contained("migration-namespace-empty", MIGRATIONS_ROOT)
    return _finding(
        "C04",
        "migration-namespace-cleanup",
        MIGRATIONS_ROOT,
        "offline" if journal.kind == "repair" else "migrate",
        f"{command} {journal.migration_id}",
        command.split(" ", 1)[0],
        "after the cleanup every gated release reads the workspace as before",
    )


# --- Host-local overrides, configuration and host baseline (C01, C02) -------------


def _parse_host_local(content: bytes) -> None:
    _DeliveryHostConfigOverrides.model_validate_json(content)


def _parse_host(content: bytes) -> None:
    DeliveryHostConfig.model_validate_json(content)


def _parse_config(content: bytes) -> DeliveryStartupConfig:
    return DeliveryStartupConfig.model_validate_json(content, strict=True)


_OWNERS: dict[str, Callable[[bytes], object]] = {
    HOST_LOCAL: _parse_host_local,
    HOST: _parse_host,
    CONFIG: _parse_config,
}


def _owner_rejects(locator: str, content: bytes, report: CapabilityReport) -> bool:
    status = next((record.status for record in report.records if record.locator == locator), "current")
    if status in {"unknown-version", "unreadable"}:
        return True
    try:
        _OWNERS[locator](content)
    except TypeError, ValueError, ValidationError:
        return True
    return False


def _status(report: CapabilityReport, locator: str) -> str | None:
    return next((record.status for record in report.records if record.locator == locator), None)


def _tracked_findings(workspace: _Workspace, report: CapabilityReport) -> list[RepairFinding]:
    findings: list[RepairFinding] = []
    for locator in (HOST_LOCAL, *_TRACKED_RECORDS):
        if _status(report, locator) == "newer":
            continue
        try:
            content = workspace.read(locator)
        except OSError, ValueError:
            findings.append(_contained("record-unsafe", locator))
            continue
        if content is None:
            if locator == CONFIG:
                findings.append(_environment("config-missing", CONFIG))
            continue
        record = next((item for item in report.records if item.locator == locator), None)
        if record is not None and record.status == "unknown-version" and not record.version_absent:
            # An explicit unsupported version is not invalid content: contain it before any replacement (C07).
            findings.append(_contained("record-unknown-version", locator))
            continue
        if not _owner_rejects(locator, content, report):
            continue
        findings.append(_host_local_finding() if locator == HOST_LOCAL else _restore_finding(workspace, locator))
    return findings


def _host_local_finding() -> RepairFinding:
    return _finding(
        "C01",
        "host-local-invalid",
        HOST_LOCAL,
        "offline",
        "C01 host-local-reset",
        f"{_REPAIRER}; user-confirmed",
        _RESTART,
    )


def _restore_finding(workspace: _Workspace, locator: str, files: tuple[str, ...] = ()) -> RepairFinding:
    try:
        restorable = _head_restore(workspace, locator, files) is not None
    except _GitUnavailableError:
        return _environment("git-unavailable", locator)
    if not restorable:
        return _contained("record-unrestorable", locator, scope=_change_scope(locator))
    return _finding(
        "C02",
        "tracked-record-invalid",
        locator,
        "offline",
        "C02 tracked-record-restore",
        f"{_REPAIRER}; user-confirmed",
        _RESTART,
        scope=_change_scope(locator),
    )


class _GitUnavailableError(RuntimeError):
    """Git could not be run; tracked-record restoration is an environment finding (C08)."""


def _head_blob(workspace: _Workspace, locator: str) -> bytes | None:
    return _git_blob(workspace, f"HEAD:{DELIVERY_STATE_ROOT}/{locator}")


def _git_blob(workspace: _Workspace, spec: str) -> bytes | None:
    try:
        git = resolve_git_executable()
        completed = subprocess.run(  # noqa: S603 - resolved Git executable and fixed argument vector.
            (git, "-C", str(workspace.root), "cat-file", "blob", spec),
            check=False,
            capture_output=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        raise _GitUnavailableError from exc
    return completed.stdout if completed.returncode == 0 else None


def _head_restore(workspace: _Workspace, locator: str, files: tuple[str, ...]) -> dict[str, bytes] | None:
    """Return the differing ``HEAD`` bytes that verify with their owner (D4), or ``None``."""
    if files:
        return _head_package(workspace, locator, files)
    head = _head_blob(workspace, locator)
    if (
        head is None
        or _owner_rejects(locator, head, CapabilityReport())
        or scan_bytes_status(locator, head) != "current"
        or head == workspace.read(locator)
    ):
        return None
    return {locator: head}


def _head_package(workspace: _Workspace, locator: str, files: tuple[str, ...]) -> dict[str, bytes] | None:
    """The ``HEAD`` package must verify against its manifest and match an existing admission."""
    change_id = locator.split("/")[1]
    head_files = {name: _head_blob(workspace, f"{locator}/{name}") for name in files}
    content = {name: value for name, value in head_files.items() if value is not None}
    if len(content) != len(files):
        return None
    try:
        head = verify_package_content(change_id, content)
    except DesignPackageConflictError, ValueError:
        return None
    if not _matches_admission(workspace, change_id, head.package_id, content["authority.json"]):
        return None
    differing = {
        f"{locator}/{name}": value for name, value in content.items() if workspace.read(f"{locator}/{name}") != value
    }
    return differing or None


def scan_bytes_status(locator: str, content: bytes) -> str:
    """Classify candidate bytes for one tracked record with the registry, as the gate would."""
    kind = classify_kind(locator)
    return "unrecognized" if kind is None else classify_record(kind, locator, content).status


def _matches_admission(workspace: _Workspace, change_id: str, package_id: str, authority: bytes) -> bool:
    """An admitted Change's ``HEAD`` package must be exactly the package its admission checkpoint verified (D4).

    The receipt's ``checkpoint_commit`` holds the package bytes the admission published; their verified
    manifest identity and contract digest are the admitted identity. Missing or inconsistent checkpoint
    evidence keeps the package contained.
    """
    admission = workspace.read(f"runtime/changes/{change_id}/admission.json")
    if admission is None:
        return True
    try:
        receipt = DeliveryAdmissionReceipt.model_validate_json(admission, strict=True)
    except ValidationError, ValueError:
        return False
    checkpoint = {name: _git_blob(workspace, f"{receipt.checkpoint_commit}:{name}") for name in _PACKAGE_FILES}
    if any(value is None for value in checkpoint.values()):
        return False
    try:
        admitted = verify_package_content(change_id, {name: value or b"" for name, value in checkpoint.items()})
    except DesignPackageConflictError, ValueError:
        return False
    return (
        hashlib.sha256(admitted.authority_bytes).hexdigest() == receipt.contract_digest
        and admitted.package_id == package_id
        and admitted.authority_bytes == authority
    )


def _package_findings(workspace: _Workspace) -> list[RepairFinding]:
    root = workspace.delivery / "packages"
    if not root.is_dir():
        return []
    findings = []
    for directory in sorted(root.iterdir()):
        if directory.name.startswith(".") or directory.name == "transactions":
            continue
        locator = f"packages/{directory.name}"
        try:
            content = {name: workspace.read(f"{locator}/{name}") for name in _PACKAGE_FILES}
        except OSError, ValueError:
            findings.append(_contained("package-unsafe", locator, scope=directory.name))
            continue
        if any(value is None for value in content.values()) or not directory.is_dir():
            findings.append(_contained("package-incomplete", locator, scope=directory.name))
            continue
        try:
            verify_package_content(
                directory.name, {name: value for name, value in content.items() if value is not None}
            )
        except DesignPackageConflictError, ValueError:
            findings.append(_restore_finding(workspace, locator, _PACKAGE_FILES))
    return findings


# --- Per-Change records (C06, C07; V20) --------------------------------------------


def _change_findings(workspace: _Workspace, report: CapabilityReport) -> list[RepairFinding]:
    findings = [
        _contained("record-owner-invalid", locator, scope=_change_scope(locator))
        for locator in owner_rejections(workspace.root, report, skip=_SELF_HANDLED_KINDS)
    ]
    findings.extend(_completion_findings(workspace))
    findings.extend(_worktree_findings(workspace))
    changes = workspace.delivery / "runtime/changes"
    if not changes.is_dir():
        return findings
    for directory in sorted(changes.iterdir()):
        if not directory.is_dir() or directory.is_symlink():
            continue
        change_id = directory.name
        findings.extend(_frontier_finding(workspace, change_id))
        admission = f"runtime/changes/{change_id}/admission.json"
        try:
            content = workspace.read(admission)
            if content is not None:
                DeliveryAdmissionReceipt.model_validate_json(content, strict=True)
        except OSError, ValidationError, ValueError:
            findings.append(_contained("receipt-invalid", admission, scope=change_id))
    return findings


def _completion_findings(workspace: _Workspace) -> list[RepairFinding]:
    """V20: a completion receipt whose stored identity or file name does not match its bytes is contained."""
    completions = workspace.delivery / "runtime/completions"
    if not completions.is_dir() or completions.is_symlink():
        return []
    store = CompletionReceiptStore(workspace.delivery / "runtime")
    findings = []
    for directory in sorted(completions.iterdir()):
        try:
            store.read(directory.name)
        except CompletionReceiptConflictError, OSError, ValueError:
            locator = f"runtime/completions/{directory.name}"
            findings.append(_contained("completion-invalid", locator, scope=directory.name))
    return findings


def _worktree_findings(workspace: _Workspace) -> list[RepairFinding]:
    """C06: a coordinated Change whose worktree is missing (and never cleaned up) routes to its online recovery."""
    root = workspace.delivery / "runtime/coordination/changes"
    if not root.is_dir() or root.is_symlink():
        return []
    findings = []
    for path in sorted(root.glob("*.json")):
        coordination = _coordination(path)
        if coordination is None or coordination.worktree_cleanup is not None:
            continue
        expected = workspace.delivery / "worktrees" / coordination.change_id
        if ChangeWorkspaceManager._worktree_present(expected):  # noqa: SLF001 - the owner's attention reader.
            continue
        findings.append(
            _finding(
                "C06",
                "worktree-missing",
                f"worktrees/{coordination.change_id}",
                "online",
                "recover_change_worktree",
                "Delivery MCP (/resolve-delivery-attention); confirmed_recovery",
                "the controller starts with this Change's worktree attention; the online recovery recreates it",
                scope=coordination.change_id,
            )
        )
    return findings


def _coordination(path: Path) -> ChangeCoordination | None:
    try:
        content = path.read_bytes()
        try:
            return ChangeCoordination.model_validate_json(content)
        except ValidationError:
            return ChangeCoordination.model_validate_json(state_migration.coordination_1_to_2(content))
    except OSError, TypeError, ValueError:
        return None


def _frontier_finding(workspace: _Workspace, change_id: str) -> list[RepairFinding]:
    locator = f"runtime/changes/{change_id}/frontier.json"
    content: bytes | None = None
    try:
        content = workspace.read(locator)
        if content is None:
            return []
        parse_delivery_frontier(content)
    except OSError, TypeError, ValueError:
        pass
    else:
        return []
    if content is not None and _single_missing_provenance(content):
        return [
            _finding(
                "C06",
                "request-provenance-missing",
                locator,
                "online",
                "repair_stranded_frontier",
                "Delivery MCP (/resolve-delivery-attention); confirmed_repair",
                "the controller starts with this Change unavailable; the online repair restores it",
                scope=change_id,
            )
        ]
    if scan_bytes_status(locator, content or b"") == "newer":
        return []
    return [_contained("frontier-invalid", locator, scope=change_id)]


def _single_missing_provenance(content: bytes) -> bool:
    try:
        payload = json.loads(content)
    except UnicodeDecodeError, RecursionError, ValueError:
        return False
    bindings = payload.get("bindings") if isinstance(payload, dict) else None
    missing = 0
    for binding in bindings if isinstance(bindings, list) else ():
        requests = binding.get("requests") if isinstance(binding, dict) else None
        for request in requests if isinstance(requests, list) else ():
            resolution = request.get("resolution") if isinstance(request, dict) else None
            if not isinstance(resolution, dict):
                continue
            text = resolution.get("response_text")
            if isinstance(text, str) and text.strip() and resolution.get("provenance") is None:
                missing += 1
    return missing == 1


# --- Pending transactions (C03, C07) -------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Pending:
    root: TransactionRoot
    root_locator: str
    pending: PendingTransaction

    @property
    def locator(self) -> str:
        return f"{self.root_locator}/transactions/{self.pending.name}"


def _root_directories(workspace: _Workspace, root: TransactionRoot) -> list[str]:
    if "/" not in root.pattern and "[" not in root.pattern:
        return [root.pattern] if (workspace.delivery / root.pattern).is_dir() else []
    parent = root.pattern.rsplit("/", 1)[0]
    base = workspace.delivery / parent
    if not base.is_dir():
        return []
    return [
        f"{parent}/{child.name}"
        for child in sorted(base.iterdir())
        if child.is_dir() and not child.is_symlink() and transaction_root(f"{parent}/{child.name}") is root
    ]


def _all_manifest_locators(workspace: _Workspace) -> list[str]:
    """Every pending manifest under any ``transactions`` directory (worktrees and journals excluded)."""
    found = []
    for directory, directory_names, file_names in os.walk(workspace.delivery):
        relative = Path(directory).relative_to(workspace.delivery).as_posix()
        if relative == ".":
            directory_names[:] = [name for name in directory_names if name != "worktrees"]
        if Path(directory).name == "transactions":
            prefix = "" if relative == "." else f"{relative}/"
            found.extend(f"{prefix}{name}" for name in file_names if name.endswith(".yaml"))
    return sorted(found)


def registered_pending(workspace_root: Path) -> tuple[list[_Pending], list[str]]:
    """Validate every manifest of every registered root with its owner validator; return pending and invalid."""
    workspace = _Workspace.of(workspace_root)
    pending: list[_Pending] = []
    invalid: list[str] = []
    for root in TRANSACTION_ROOTS:
        for root_locator in _root_directories(workspace, root):
            directory = workspace.delivery / root_locator
            allowed = tuple(directory if item == "." else workspace.delivery / item for item in root.participant_roots)
            try:
                found = RuntimeTransaction.read_pending(
                    directory, roots=allowed, contained=root.validator == "contained"
                )
            except TransactionManifestError, TransactionPathError, OSError, ValueError:
                invalid.append(f"{root_locator}/transactions")
                continue
            pending.extend(_Pending(root, root_locator, item) for item in found)
    covered = {item.locator for item in pending}
    invalid.extend(locator for locator in _all_manifest_locators(workspace) if locator not in covered)
    return pending, invalid


def replay_shape(
    workspace_root: Path, pending: list[_Pending]
) -> tuple[tuple[RepairEntry, ...], tuple[RepairManifest, ...], tuple[RepairParticipant, ...]]:
    """Exact before and after digests of every participant and manifest; a broken precondition raises."""
    workspace = _Workspace.of(workspace_root)
    entries: list[RepairEntry] = []
    manifests: list[RepairManifest] = []
    participants: list[RepairParticipant] = []
    for item in sorted(pending, key=lambda candidate: candidate.locator):
        for participant in item.pending.transaction.participants:
            shape, records = _participant_shape(workspace, item.locator, participant)
            participants.append(shape)
            entries.extend(records)
        manifests.append(
            RepairManifest(
                locator=item.locator, root=item.root_locator, validator=item.root.validator, sha256=item.pending.sha256
            )
        )
    entries.extend(
        RepairEntry(locator=manifest.locator, role="manifest", before_sha256=manifest.sha256) for manifest in manifests
    )
    locators = [entry.locator for entry in entries]
    if len(locators) != len(set(locators)):
        msg = "two pending manifests share a path"
        raise ValueError(msg)
    return tuple(entries), tuple(manifests), tuple(participants)


def _relative(workspace: _Workspace, path: Path) -> str:
    return path.relative_to(workspace.delivery).as_posix()


def _digest(workspace: _Workspace, locator: str) -> str | None:
    try:
        return path_digest(workspace.root, locator)
    except MigrationError as exc:
        raise ValueError(exc.detail) from exc


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _participant_shape(
    workspace: _Workspace, manifest: str, participant: object
) -> tuple[RepairParticipant, list[RepairEntry]]:
    """Bind every participant path, unchanged and absent ones included, so a drift there stops replay (I4)."""

    def entry(locator: str, before: str | None, after: str | None) -> RepairEntry:
        return RepairEntry(
            locator=locator, role="participant", manifest=manifest, before_sha256=before, after_sha256=after
        )

    if isinstance(participant, MoveTransactionParticipant):
        source = _relative(workspace, participant.source())
        destination = _relative(workspace, participant.destination())
        current_source, current_destination = _digest(workspace, source), _digest(workspace, destination)
        expected, moved = _sha(participant.expected_content), _sha(participant.destination_content)
        if not (
            (current_source == expected and current_destination is None)
            or (current_destination == moved and current_source in {expected, None})
        ):
            msg = "move participant precondition does not hold"
            raise ValueError(msg)
        records = [entry(source, current_source, None), entry(destination, current_destination, moved)]
        return RepairParticipant(manifest=manifest, kind="move", destination=destination, source=source), records
    destination = _relative(workspace, participant.destination())  # type: ignore[attr-defined]
    current = _digest(workspace, destination)
    if isinstance(participant, ReplacementTransactionParticipant):
        after, allowed, kind = (
            _sha(participant.replacement_content),
            {_sha(participant.expected_content)},
            "replacement",
        )
    else:
        after, allowed, kind = _sha(participant.content), {None}, "immutable"  # type: ignore[attr-defined]
    if current != after and current not in allowed:
        msg = "participant precondition does not hold"
        raise ValueError(msg)
    shape = RepairParticipant(manifest=manifest, kind=kind, destination=destination)  # type: ignore[arg-type]
    return shape, [entry(destination, current, after)]


def _start_refused(report: CapabilityReport) -> bool:
    return any(not refusal.locator.startswith(MIGRATIONS_ROOT) for refusal in report.refusals)


def _transaction_findings(
    workspace: _Workspace, report: CapabilityReport, *, startup_refused: bool
) -> list[RepairFinding]:
    """C03 only while start is refused before replay: by the gate, or by the loader's read-only checks."""
    pending, invalid = registered_pending(workspace.root)
    if not invalid:
        try:
            replay_shape(workspace.root, pending)
        except ValueError, ValidationError:
            invalid = [item.locator for item in pending]
    if invalid:
        locators = sorted({*invalid, *(item.locator for item in pending)})
        return [
            _contained("transaction-manifest-invalid", locator, scope=_change_scope(locator)) for locator in locators
        ]
    if not pending or not (startup_refused or _start_refused(report)):
        return []
    return [
        _finding(
            "C03",
            "transactions-pending",
            "transactions",
            "offline",
            "C03 transaction-replay",
            f"{_REPAIRER}; engine replay",
            "after delivery-repair verify the remaining refusal names its own route",
        )
    ]


# --- Environment (C08) ----------------------------------------------------------


def _environment(code: str, locator: str) -> RepairFinding:
    return _finding(
        "C08",
        code,
        locator,
        "environment",
        "setup/init.py",
        "agent: rerun setup/init.py for this project with the option named by the locator",
        "after the environment is corrected the controller starts",
    )


def _environment_findings(workspace: _Workspace) -> list[RepairFinding]:
    try:
        content = workspace.read(CONFIG)
        config = _parse_config(content) if content is not None else None
    except OSError, TypeError, ValueError, ValidationError:
        return []
    if config is None:
        return []
    try:
        _validate_git_config(config, _derive_paths(workspace.root))
    except DeliveryApplicationLoadError as exc:
        return [_environment("environment-invalid", f"environment:{exc.field}")]
    return []


# ---------------------------------------------------------------------------
# Proposals and the offline operations
# ---------------------------------------------------------------------------


_CONSEQUENCES = {
    "C01": (
        "runtime/host.local.json is replaced by canonical empty overrides, so host tuning returns to "
        "runtime/host.json defaults; the original bytes stay in the backup under .owlbear/delivery-migrations/<id>"
    ),
    "C02": (
        "the working-tree bytes are replaced by the verifying HEAD version, discarding uncommitted edits; "
        "the edited bytes stay in the backup under .owlbear/delivery-migrations/<id>"
    ),
    "C03": "every pending transaction is completed exactly as recorded; the manifests and before-state are backed up",
}


def propose(workspace_root: Path, finding_id: str) -> RepairProposal:
    """Stage one fenced proposal for a current C01-C03 finding; writes no authoritative byte."""
    workspace = _Workspace.of(workspace_root)
    if scan_capability(workspace.root).format_status == "newer":
        raise MigrationError(code="repair-format-unsupported", detail="Delivery state is newer than this controller")
    require_no_open_journal(workspace.root)
    proposal, staged = _build(workspace, finding_id)
    state_migration.write_repair_stage(workspace.root, proposal, staged)
    return proposal


def _build(workspace: _Workspace, finding_id: str) -> tuple[RepairProposal, dict[str, bytes]]:
    report = classify(workspace.root)
    finding = next((item for item in report.findings if item.finding_id == finding_id), None)
    if finding is None:
        raise MigrationError(code="repair-not-supported", detail="no current finding has this ID")
    if finding.catalogue not in _CONSEQUENCES:
        raise MigrationError(
            code="repair-not-supported", detail=f"{finding.catalogue} findings route to {finding.route}, not offline"
        )
    staged: dict[str, bytes] = {}
    manifests: tuple[RepairManifest, ...] = ()
    participants: tuple[RepairParticipant, ...] = ()
    if finding.catalogue != "C03" and _all_manifest_locators(workspace):
        raise MigrationError(
            code="repair-not-supported",
            detail="a RuntimeTransaction manifest is pending; replay or contain it (C03, C07) before this repair",
        )
    if finding.catalogue == "C01":
        before = workspace.read(HOST_LOCAL)
        entries = (_record_entry(HOST_LOCAL, before, CANONICAL_HOST_LOCAL),)
        staged[HOST_LOCAL] = CANONICAL_HOST_LOCAL
    elif finding.catalogue == "C02":
        files = _PACKAGE_FILES if finding.locator.startswith("packages/") else ()
        restore = _head_restore(workspace, finding.locator, files) or {}
        entries = tuple(
            _record_entry(locator, workspace.read(locator), head) for locator, head in sorted(restore.items())
        )
        staged.update(restore)
    else:
        pending, invalid = registered_pending(workspace.root)
        if invalid:  # pragma: no cover - classify reports C07 instead of C03.
            raise MigrationError(code="repair-not-supported", detail="a pending manifest fails its owner validator")
        entries, manifests, participants = replay_shape(workspace.root, pending)
    proposal = repair_proposal(
        operation={"C01": "host-local-reset", "C02": "tracked-record-restore"}.get(
            finding.catalogue, "transaction-replay"
        ),  # type: ignore[arg-type]
        finding_id=finding_id,
        format_value=scan_capability(workspace.root).format,
        policy="engine-replay" if finding.catalogue == "C03" else "user-confirmed",
        consequence=_CONSEQUENCES[finding.catalogue],
        entries=entries,
        manifests=manifests,
        participants=participants,
        findings=report.finding_ids,
    )
    return proposal, staged


def _record_entry(locator: str, before: bytes | None, after: bytes) -> RepairEntry:
    if before is None:  # pragma: no cover - C01 and C02 replace existing bytes only (D3).
        msg = "C01 and C02 never create a record"
        raise MigrationError(code="repair-proposal-stale", detail=msg, locator=locator)
    return RepairEntry(locator=locator, before_sha256=_sha(before), after_sha256=_sha(after))


def _current(workspace_root: Path, proposal: RepairProposal) -> RepairProposal:
    """Re-derive the proposal from disk at ``apply`` (I4): any drift makes it differ."""
    try:
        rebuilt, _staged = _build(_Workspace.of(workspace_root), proposal.finding_id)
    except ValueError as exc:
        raise MigrationError(code="repair-proposal-stale", detail="the repaired state changed") from exc
    return rebuilt


def owner_check(workspace_root: Path, proposal: RepairProposal) -> None:
    """I9 owner postcondition: the addressed owner accepts the repaired records; raise ``ValueError`` otherwise."""
    workspace = _Workspace.of(workspace_root)
    if proposal.operation == "transaction-replay":
        if any(workspace.read(manifest.locator) is not None for manifest in proposal.manifests):
            msg = "a replayed manifest is still pending"
            raise ValueError(msg)
        return
    for entry in proposal.entries:
        content = workspace.read(entry.locator)
        if content is None:
            msg = "a repaired record is missing"
            raise ValueError(msg)
        if entry.locator in _OWNERS:
            _OWNERS[entry.locator](content)
        elif entry.locator.startswith("packages/"):
            change_id = entry.locator.split("/")[1]
            files = {name: workspace.read(f"packages/{change_id}/{name}") or b"" for name in _PACKAGE_FILES}
            try:
                verify_package_content(change_id, files)
            except DesignPackageConflictError as exc:
                raise ValueError(str(exc)) from exc


def _verification_findings(workspace_root: Path, proposal_id: str) -> tuple[str, ...]:
    return classify(workspace_root, verifying=proposal_id).finding_ids


def apply(
    workspace_root: Path,
    proposal_id: str,
    *,
    confirm: str | None = None,
    processes: ControllerProcessSource | None = None,
    failure: FailureHook | None = None,
) -> MigrationJournal:
    """Apply one staged repair (U1: user-confirmed operations need ``confirm`` equal to the proposal ID)."""
    return state_migration.apply_repair(
        workspace_root, proposal_id, confirm=confirm, current=_current, processes=processes, failure=failure
    )


def resume(
    workspace_root: Path,
    proposal_id: str,
    *,
    processes: ControllerProcessSource | None = None,
    failure: FailureHook | None = None,
) -> MigrationJournal:
    """Continue a crashed repair from durable state."""
    return state_migration.resume_repair(workspace_root, proposal_id, processes=processes, failure=failure)


def verify(
    workspace_root: Path,
    proposal_id: str,
    *,
    processes: ControllerProcessSource | None = None,
    failure: FailureHook | None = None,
) -> MigrationJournal:
    """Scoped verification (I9), archive and namespace cleanup (I3)."""
    return state_migration.verify_repair(
        workspace_root,
        proposal_id,
        owner_check=owner_check,
        classify=_verification_findings,
        processes=processes,
        failure=failure,
    )


def abort(
    workspace_root: Path,
    proposal_id: str,
    *,
    processes: ControllerProcessSource | None = None,
    failure: FailureHook | None = None,
) -> AbortResult:
    """Restore the complete before-state and archive the repair as aborted."""
    return state_migration.abort_repair(workspace_root, proposal_id, processes=processes, failure=failure)


__all__ = [
    "CANONICAL_HOST_LOCAL",
    "RepairFinding",
    "RepairReport",
    "abort",
    "apply",
    "classify",
    "owner_check",
    "propose",
    "registered_pending",
    "replay_shape",
    "resume",
    "verify",
]
