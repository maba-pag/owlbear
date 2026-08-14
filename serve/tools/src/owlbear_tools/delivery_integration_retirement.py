"""Retire terminal legacy Integration state after Delivery path migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from owlbear_delivery.change_workspace import CapacityLedger, ChangeCoordination, ChangeWorkspaceManager
from owlbear_delivery.completed_history import (
    CompletedHistoryCatalog,
    LegacyCompletedChangeRecord,
)
from owlbear_delivery.delivery_application_loader import DeliveryStartupConfig, load_delivery_application
from owlbear_delivery.delivery_runtime import (
    DeliveryFrontier,
    DeliveryIntegrationCompletion,
    DeliveryStage,
    parse_delivery_frontier,
)
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.storage_io import atomic_write, locked_roots
from owlbear_tools.delivery_migration import RETIREMENT_JOURNAL_RELATIVE

if TYPE_CHECKING:
    from collections.abc import Iterator

_PATH_MIGRATION_JOURNAL_RELATIVE = Path(".owlbear/delivery/migration.json")
_ARCHIVE_TARGET_RELATIVE = Path(".owlbear/legacy/delivery-state-migration/target")
_RUNTIME_RELATIVE = Path(".owlbear/delivery/runtime")
_WORKTREES_RELATIVE = Path(".owlbear/delivery/worktrees")
_LEGACY_TARGET_RELATIVE = Path(".owlbear/target")
_LEGACY_WORKTREES_RELATIVE = Path(".owlbear/worktrees")
_STAGING_RELATIVE = Path(".owlbear/scratch/delivery-integration-retirement")
_VERIFICATION_RELATIVE = Path("claims/integration-verification")
_PUBLICATION_LOCKS_RELATIVE = Path("claims/publication-locks")
_ACQUISITION_LOCK_RELATIVE = Path("claims/acquisition-lock")
_INTEGRATION_LOCK_RELATIVE = Path("claims/integration-lock")
_LEGACY_FRONTIER_SCHEMAS = frozenset(range(1, 16))
_COMPACT_RESULT_SCHEMAS = frozenset({1, 2, 3})
_RETIREMENT_FRONTIER_ALLOWED_FIELDS = frozenset({"schema_version", "bindings", "published_head", "operator_moves"})
_RETIREMENT_BINDING_ALLOWED_FIELDS = frozenset({"outcome_id", "plan_scope_id", "stage", "tasks", "results", "output"})
_SAFE_CHANGE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SAFE_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SAFE_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_VERIFICATION_PATH_PARTS = 2
_PUBLICATION_PATH_PARTS = 4
_PUBLICATION_OPERATION_ROOTS = (
    Path("publications/change-branches/operations"),
    Path("publications/pull-requests/operations"),
    Path("publications/pull-requests/summary-operations"),
    Path("publications/pull-requests/summary-receipts"),
    Path("publications/pull-requests/supersession-operations"),
    Path("publications/pull-requests/supersession-receipts"),
    Path("publications/pull-requests/draft-state-operations"),
    Path("publications/pull-requests/draft-state-receipts"),
)
_PUBLICATION_CHANGE_FILE_ROOTS = (
    Path("publications/pull-requests/check-observations"),
    Path("publications/pull-requests/pull-request-observations"),
)
_PUBLICATION_STATE_LOCK_ROOTS = (
    Path("publications/checkpoints/locks"),
    Path("publications/pull-requests/locks"),
)
_PUBLICATION_FLAT_ROOTS = frozenset(
    {
        ("change-branches", "operations"),
        ("pull-requests", "receipts"),
        ("pull-requests", "operations"),
        ("pull-requests", "summary-operations"),
        ("pull-requests", "summary-receipts"),
        ("pull-requests", "supersession-operations"),
        ("pull-requests", "supersession-receipts"),
        ("pull-requests", "publication-history"),
        ("pull-requests", "draft-state-operations"),
        ("pull-requests", "draft-state-receipts"),
    }
)
_PUBLICATION_NESTED_ROOTS = frozenset(
    {
        ("pull-requests", "check-observations"),
        ("pull-requests", "pull-request-observations"),
    }
)


class DeliveryIntegrationRetirementError(RuntimeError):
    """Obsolete Integration state cannot be retired without exact proof."""


_RETIREMENT_FAILURES = (DeliveryIntegrationRetirementError, OSError)


@dataclass(frozen=True)
class _RegisteredWorktree:
    path: Path
    head: str
    branch: str | None


@dataclass(frozen=True)
class _VerificationRecord:
    path: Path
    payload: dict[str, object]


@dataclass(frozen=True)
class _RetirementFrontier:
    frontier: DeliveryFrontier
    integration_completion: DeliveryIntegrationCompletion | None


def _publication_payload(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"Delivery publication record is malformed: {path}")
        raise AssertionError from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("change_id"), str):
        _fail(f"Delivery publication record has no Change identity: {path}")
    return payload


def _require_publication_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        _fail(f"Delivery publication record is missing or unsafe: {path}")


def _publication_operation_paths(runtime_root: Path, change_id: str) -> tuple[Path, ...]:
    paths: list[Path] = []
    for relative_root in _PUBLICATION_OPERATION_ROOTS:
        operation_root = runtime_root / relative_root
        if not (operation_root.exists() or operation_root.is_symlink()):
            continue
        _require_directory(operation_root)
        for path in sorted(operation_root.glob("*.json")):
            _require_publication_file(path)
            if _publication_payload(path).get("change_id") == change_id:
                paths.append(path)
    return tuple(paths)


def _publication_nested_paths(runtime_root: Path, change_id: str) -> tuple[Path, ...]:
    paths: list[Path] = []
    for relative_root in _PUBLICATION_CHANGE_FILE_ROOTS:
        change_root = runtime_root / relative_root / change_id
        if not (change_root.exists() or change_root.is_symlink()):
            continue
        _require_directory(change_root)
        for path in sorted(change_root.iterdir()):
            if path.suffix != ".json":
                _fail(f"Delivery publication record has an unsafe path: {path}")
            _require_publication_file(path)
            if _publication_payload(path).get("change_id") != change_id:
                _fail(f"Delivery publication record identity differs from its path: {path}")
            paths.append(path)
    return tuple(paths)


def _publication_paths(runtime_root: Path, change_id: str) -> tuple[Path, ...]:
    receipt = runtime_root / "publications/pull-requests/receipts" / f"{change_id}.json"
    history = runtime_root / "publications/pull-requests/publication-history" / f"{change_id}.json"
    paths = []
    for path in (receipt, history):
        if path.exists() or path.is_symlink():
            _require_publication_file(path)
            if _publication_payload(path)["change_id"] != change_id:
                _fail(f"Delivery publication record identity differs from its path: {path}")
            paths.append(path)
    paths.extend(_publication_operation_paths(runtime_root, change_id))
    paths.extend(_publication_nested_paths(runtime_root, change_id))
    return tuple(paths)


def _publication_state_lock_paths(runtime_root: Path, change_id: str) -> tuple[Path, ...]:
    return tuple(runtime_root / relative / change_id for relative in _PUBLICATION_STATE_LOCK_ROOTS)


@dataclass(frozen=True)
class _RetirementChange:
    change_id: str
    runtime_change_root: Path
    coordination_path: Path
    frontier: _RetirementFrontier
    frontier_bytes: bytes
    coordination: ChangeCoordination
    coordination_bytes: bytes
    worktree: _RegisteredWorktree | None
    verification_paths: tuple[Path, ...]
    publication_paths: tuple[Path, ...]
    publication_lock_path: Path
    publication_state_lock_paths: tuple[Path, ...]


@dataclass(frozen=True)
class DeliveryIntegrationRetirementPlan:
    """Validated identities and paths for one Integration retirement attempt."""

    repository_root: Path
    runtime_root: Path
    worktree_root: Path
    target_ref: str
    target_commit: str
    changes: tuple[_RetirementChange, ...]
    already_retired: bool = False


class _RetirementModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class _JournalChange(_RetirementModel):
    change_id: str
    runtime_change_root: Path
    coordination_path: Path
    stage_change_root: Path
    stage_coordination_path: Path
    verification_paths: tuple[Path, ...]
    stage_verification_paths: tuple[Path, ...]
    frontier_sha256: str
    coordination_sha256: str
    worktree_path: Path | None
    branch: str | None
    worktree_head: str | None
    publication_paths: tuple[Path, ...] = ()
    stage_publication_paths: tuple[Path, ...] = ()
    publication_sha256: tuple[str, ...] = ()
    publication_lock_path: Path
    publication_state_lock_paths: tuple[Path, ...]


class _RetirementJournal(_RetirementModel):
    schema_version: Literal[1] = 1
    phase: Literal["staged", "cleanup"] = "staged"
    repository_root: Path
    runtime_root: Path
    worktree_root: Path
    target_ref: str
    target_commit: str
    staging_root: Path
    changes: tuple[_JournalChange, ...]


@dataclass(frozen=True)
class _HistoryContext:
    repository_root: Path
    runtime_root: Path
    target_commit: str
    target_branch: str


def _fail(detail: str) -> None:
    raise DeliveryIntegrationRetirementError(detail)


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    git_executable = resolve_git_executable()
    completed = subprocess.run(  # noqa: S603 - fixed executable and bounded arguments.
        (git_executable, "-C", str(root), *arguments),
        check=False,
        capture_output=True,
    )
    if check and completed.returncode != 0:
        detail = completed.stderr.decode(errors="replace").strip() or "Git operation failed"
        _fail(detail)
    return completed


def _load_model[Model: BaseModel](path: Path, model_type: type[Model]) -> Model:
    try:
        return model_type.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as exc:
        _fail(f"invalid Delivery retirement authority: {path}")
        raise AssertionError from exc


def _has_entries(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_symlink() or not path.is_dir():
        _fail(f"Delivery retirement path is unsafe: {path}")
    return any(path.iterdir())


def _require_directory(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        _fail(f"Delivery retirement directory is missing or unsafe: {path}")


def _registered_worktrees(root: Path) -> tuple[_RegisteredWorktree, ...]:
    completed = _git(root, "worktree", "list", "--porcelain", "-z")
    records = []
    for raw_record in completed.stdout.split(b"\0\0"):
        fields = tuple(field for field in raw_record.split(b"\0") if field)
        values = {field.partition(b" ")[0]: field.partition(b" ")[2] for field in fields}
        if b"worktree" not in values or b"HEAD" not in values:
            continue
        records.append(
            _RegisteredWorktree(
                path=Path(os.fsdecode(values[b"worktree"])).resolve(),
                head=os.fsdecode(values[b"HEAD"]),
                branch=(os.fsdecode(values[b"branch"]).removeprefix("refs/heads/") if b"branch" in values else None),
            )
        )
    return tuple(records)


def _require_ordering(repository_root: Path, runtime_root: Path) -> None:
    if (repository_root / _PATH_MIGRATION_JOURNAL_RELATIVE).exists():
        _fail("interrupted Delivery path migration requires recovery before Integration retirement")
    for relative in (_LEGACY_TARGET_RELATIVE, _LEGACY_WORKTREES_RELATIVE):
        if _has_entries(repository_root / relative):
            _fail("legacy Delivery paths must be migrated before Integration retirement")
    if _has_entries(runtime_root) and not (repository_root / _ARCHIVE_TARGET_RELATIVE).is_dir():
        _fail("canonical Delivery runtime requires a completed path-migration archive")


def _load_startup_config(repository_root: Path) -> DeliveryStartupConfig:
    path = repository_root / ".owlbear/delivery/config.json"
    try:
        return DeliveryStartupConfig.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as exc:
        _fail(f"Delivery startup configuration is invalid: {path}")
        raise AssertionError from exc


def _resolve_target(repository_root: Path, target_ref: str) -> str:
    resolved = _git(repository_root, "rev-parse", "--verify", f"{target_ref}^{{commit}}", check=False)
    if resolved.returncode != 0:
        _fail(f"remote-tracking target cannot be resolved: {target_ref}")
    return resolved.stdout.decode().strip()


def _parse_retirement_frontier(content: bytes) -> _RetirementFrontier:
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise TypeError
    schema_version = payload.get("schema_version")
    result_id = payload.get("integration_result_id")
    completion_payload = payload.get("integration_completion")
    completion: DeliveryIntegrationCompletion | None = None
    if result_id is not None or completion_payload is not None:
        if type(schema_version) is not int or schema_version not in _LEGACY_FRONTIER_SCHEMAS:
            raise ValueError
        try:
            completion = DeliveryIntegrationCompletion.model_validate(completion_payload)
        except (TypeError, ValueError) as exc:
            message = "legacy Delivery Integration completion is invalid"
            raise ValueError(message) from exc
        if result_id != completion.completion_id:
            raise ValueError
        payload = dict(payload)
        payload.pop("integration_result_id", None)
        payload.pop("integration_completion", None)
    payload = _retirement_validation_payload(payload, schema_version)
    frontier, _canonical = parse_delivery_frontier(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    return _RetirementFrontier(frontier=frontier, integration_completion=completion)


def _retirement_validation_payload(payload: dict[str, object], schema_version: object) -> dict[str, object]:
    if schema_version not in _COMPACT_RESULT_SCHEMAS:
        return payload
    raw_bindings = payload.get("bindings")
    if not isinstance(raw_bindings, list):
        return payload
    bindings = []
    for raw_binding in raw_bindings:
        if not isinstance(raw_binding, dict):
            return payload
        raw_results = raw_binding.get("results", [])
        if not isinstance(raw_results, list):
            return payload
        if any(
            not isinstance(result, dict) or "observations" in result or "review" in result for result in raw_results
        ):
            raise ValueError
        binding = dict(raw_binding)
        binding["results"] = []
        bindings.append(binding)
    validation_payload = dict(payload)
    validation_payload["bindings"] = bindings
    return validation_payload


def _load_frontiers(
    runtime_root: Path,
) -> tuple[dict[str, _RetirementFrontier], dict[str, bytes], dict[str, Path]]:
    changes_root = runtime_root / "changes"
    if not changes_root.exists():
        return {}, {}, {}
    _require_directory(changes_root)
    frontiers: dict[str, _RetirementFrontier] = {}
    raw_bytes: dict[str, bytes] = {}
    change_roots: dict[str, Path] = {}
    for change_root in sorted(changes_root.iterdir()):
        if change_root.is_symlink() or not change_root.is_dir():
            _fail(f"Delivery Change runtime path is unsafe: {change_root}")
        frontier_path = change_root / "frontier.json"
        try:
            content = frontier_path.read_bytes()
            frontier = _parse_retirement_frontier(content)
        except (OSError, TypeError, ValueError) as exc:
            _fail(f"Delivery frontier is invalid: {frontier_path}")
            raise AssertionError from exc
        frontiers[change_root.name] = frontier
        raw_bytes[change_root.name] = content
        change_roots[change_root.name] = change_root
    return frontiers, raw_bytes, change_roots


def _load_coordinations(
    runtime_root: Path,
    change_ids: set[str],
) -> tuple[dict[str, ChangeCoordination], dict[str, bytes]]:
    coordination_root = runtime_root / "claims/changes"
    if not coordination_root.exists():
        if change_ids:
            _fail("Delivery Change coordination is missing")
        return {}, {}
    _require_directory(coordination_root)
    coordinations: dict[str, ChangeCoordination] = {}
    raw_bytes: dict[str, bytes] = {}
    for path in sorted(coordination_root.glob("*.json")):
        coordination = _load_model(path, ChangeCoordination)
        if coordination.change_id != path.stem:
            _fail(f"Delivery coordination identity differs from its path: {path}")
        coordinations[path.stem] = coordination
        raw_bytes[path.stem] = path.read_bytes()
    if set(coordinations) != change_ids:
        _fail("Delivery runtime and coordination Change identities differ")
    return coordinations, raw_bytes


def _require_coordination_quiescence(coordinations: dict[str, ChangeCoordination]) -> None:
    if any(
        coordination.writer is not None or coordination.publication_lease is not None
        for coordination in coordinations.values()
    ):
        _fail("active Delivery coordination lease blocks Integration retirement")


def _require_runtime_quiescence(runtime_root: Path) -> None:
    capacity = _load_model(runtime_root / "capacity.json", CapacityLedger)
    if capacity.change_ids:
        _fail("active Delivery capacity holders block Integration retirement")
    if _has_entries(runtime_root / ".runtime-transactions"):
        _fail("pending Delivery runtime transactions block Integration retirement")


def _require_frontier_quiescence(change_id: str, frontier: _RetirementFrontier) -> None:
    delivery_frontier = frontier.frontier
    if any(binding.active_claim is not None for binding in delivery_frontier.bindings):
        _fail(f"active Delivery claim blocks Integration retirement: {change_id}")
    if any(binding.recovery_attention is not None for binding in delivery_frontier.bindings):
        _fail(f"Delivery recovery attention blocks Integration retirement: {change_id}")
    if delivery_frontier.integration_attention is not None or delivery_frontier.integration_repair_claim is not None:
        _fail(f"Integration attention blocks retirement: {change_id}")


def _require_terminal_frontier(change_id: str, frontier: _RetirementFrontier) -> None:
    delivery_frontier = frontier.frontier
    if any(binding.stage != DeliveryStage.COMPLETED for binding in delivery_frontier.bindings):
        _fail(f"incomplete Integration completion blocks retirement: {change_id}")
    if any(
        binding.candidate is not None or binding.result_candidate is not None for binding in delivery_frontier.bindings
    ):
        _fail(f"unconsumed Integration candidate blocks retirement: {change_id}")
    _require_default_fields(
        delivery_frontier,
        _RETIREMENT_FRONTIER_ALLOWED_FIELDS,
        f"Delivery frontier authority blocks Integration retirement: {change_id}",
    )
    for binding in delivery_frontier.bindings:
        _require_default_fields(
            binding,
            _RETIREMENT_BINDING_ALLOWED_FIELDS,
            f"Delivery binding authority blocks Integration retirement: {change_id}",
        )


def _require_default_fields(
    model: BaseModel,
    allowed_fields: frozenset[str],
    detail: str,
) -> None:
    for field_name, field in type(model).model_fields.items():
        if field_name in allowed_fields:
            continue
        if getattr(model, field_name) != field.get_default(call_default_factory=True):
            _fail(f"{detail}: {field_name}")


def _require_quiescent(
    frontiers: dict[str, _RetirementFrontier],
    coordinations: dict[str, ChangeCoordination],
    runtime_root: Path,
) -> None:
    _require_coordination_quiescence(coordinations)
    _require_runtime_quiescence(runtime_root)
    for change_id, frontier in frontiers.items():
        _require_frontier_quiescence(change_id, frontier)
        if frontier.integration_completion is not None:
            _require_terminal_frontier(change_id, frontier)


def _change_worktree(
    repository_root: Path,
    coordination: ChangeCoordination,
    registrations: tuple[_RegisteredWorktree, ...],
) -> _RegisteredWorktree | None:
    expected_path = coordination.worktree_path.resolve()
    matching = tuple(item for item in registrations if item.path == expected_path)
    branch_matches = tuple(item for item in registrations if item.branch == coordination.branch)
    if len(matching) > 1 or len(branch_matches) > 1:
        _fail(f"Delivery Change worktree registration is ambiguous: {coordination.change_id}")
    if not matching:
        if branch_matches:
            _fail(f"Delivery Change branch is registered at an unexpected path: {coordination.change_id}")
        if expected_path.exists():
            _fail(f"Delivery Change worktree path is unregistered but present: {coordination.change_id}")
        return None
    registration = matching[0]
    if registration.branch != coordination.branch:
        _fail(f"Delivery Change worktree branch differs from coordination: {coordination.change_id}")
    if registration.path.is_symlink() or not registration.path.is_dir():
        _fail(f"Delivery Change worktree is missing or unsafe: {coordination.change_id}")
    branch_head = (
        _git(repository_root, "rev-parse", f"refs/heads/{coordination.branch}^{{commit}}").stdout.decode().strip()
    )
    if registration.head != branch_head:
        _fail(f"Delivery Change worktree head differs from its branch: {coordination.change_id}")
    status = _git(registration.path, "status", "--porcelain", "--untracked-files=all").stdout
    if status:
        _fail(f"dirty Delivery Change worktree blocks retirement: {coordination.change_id}")
    return registration


def _verification_records(verification_root: Path, kind: str) -> dict[str, _VerificationRecord]:
    directory = verification_root / kind
    if not directory.exists():
        return {}
    _require_directory(directory)
    records: dict[str, _VerificationRecord] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_bytes())
        except (OSError, json.JSONDecodeError) as exc:
            _fail(f"Integration verification record is malformed: {path}")
            raise AssertionError from exc
        if not isinstance(payload, dict):
            _fail(f"Integration verification record is malformed: {path}")
        request_id = payload.get("request_id")
        if not isinstance(request_id, str) or request_id != path.stem:
            _fail(f"Integration verification identity differs from its path: {path}")
        records[request_id] = _VerificationRecord(path, payload)
    return records


def _require_archived_verification(
    archived_root: Path,
    kind: str,
    record: _VerificationRecord,
) -> None:
    archived = archived_root / kind / record.path.name
    if not archived.is_file() or archived.read_bytes() != record.path.read_bytes():
        _fail(f"Integration verification archive differs: {record.path}")


def _verification_paths(
    repository_root: Path,
    runtime_root: Path,
    candidates: dict[str, _RetirementFrontier],
) -> dict[str, tuple[Path, ...]]:
    verification_root = runtime_root / _VERIFICATION_RELATIVE
    if not verification_root.exists():
        return dict.fromkeys(candidates, ())
    _require_directory(verification_root)
    archived_root = (
        repository_root / ".owlbear/legacy/delivery-state-migration/target/target-runtime/integration-verification"
    )
    requests = _verification_records(verification_root, "requests")
    receipts = _verification_records(verification_root, "receipts")
    _require_verification_archives(archived_root, requests, receipts, candidates)
    return _candidate_verification_paths(candidates, requests, receipts)


def _require_verification_archives(
    archived_root: Path,
    requests: dict[str, _VerificationRecord],
    receipts: dict[str, _VerificationRecord],
    candidates: dict[str, _RetirementFrontier],
) -> None:
    for record in requests.values():
        if record.payload.get("change_id") in candidates:
            _require_archived_verification(archived_root, "requests", record)
    for request_id, record in receipts.items():
        if request_id in requests:
            _require_archived_verification(archived_root, "receipts", record)


def _candidate_verification_paths(
    candidates: dict[str, _RetirementFrontier],
    requests: dict[str, _VerificationRecord],
    receipts: dict[str, _VerificationRecord],
) -> dict[str, tuple[Path, ...]]:
    paths: dict[str, tuple[Path, ...]] = dict.fromkeys(candidates, ())
    for request_id, record in requests.items():
        change_id = record.payload.get("change_id")
        if change_id not in candidates:
            continue
        completion = candidates[change_id].integration_completion
        if completion is None:
            _fail(f"Integration completion is missing: {change_id}")
        if (
            record.payload.get("completion_id") != completion.completion_id
            or record.payload.get("package_id") != completion.package_id
        ):
            _fail(f"Integration verification identity differs from completion: {change_id}")
        receipt = receipts.get(request_id)
        if receipt is None:
            _fail(f"Integration verification receipt is missing: {request_id}")
        paths[change_id] += (record.path, receipt.path)
    for request_id in receipts:
        if request_id not in requests:
            _fail(f"Integration verification receipt has no request: {request_id}")
    return paths


def _require_history_proof(context: _HistoryContext, change_id: str, frontier: _RetirementFrontier) -> None:
    completion = frontier.integration_completion
    if completion is None:
        return
    receipt_root = context.runtime_root / "completions" / change_id
    if receipt_root.exists():
        _fail(f"modern completion receipt conflicts with legacy Integration state: {change_id}")
    package_root = context.repository_root / ".owlbear/delivery/packages" / change_id
    if package_root.exists():
        _fail(f"active Design package conflicts with legacy Integration state: {change_id}")
    catalog = CompletedHistoryCatalog(
        context.repository_root,
        context.target_branch,
        context.target_commit,
        context.runtime_root,
    )
    try:
        record = catalog.show(change_id)
    except Exception as exc:  # noqa: BLE001 - all history diagnostics block destructive retirement.
        _fail(f"legacy completion cannot be verified: {change_id}: {exc}")
    if not isinstance(record, LegacyCompletedChangeRecord):
        _fail(f"legacy completion is shadowed by a modern receipt: {change_id}")
    if (
        completion.completion_id != record.completion_id
        or completion.package_id != record.package_id
        or completion.completion_path != record.historical_completion_locator
    ):
        _fail(f"legacy completion identity differs from Integration state: {change_id}")
    if (
        _git(
            context.repository_root,
            "merge-base",
            "--is-ancestor",
            completion.target_commit,
            context.target_commit,
            check=False,
        ).returncode
        != 0
    ):
        _fail(f"Integration target commit is not retained by the configured target: {change_id}")
    historical_bytes = _git(
        context.repository_root,
        "show",
        f"{completion.target_commit}:{completion.completion_path}/completion.json",
        check=False,
    )
    if historical_bytes.returncode != 0 or _digest(historical_bytes.stdout) != record.completion_id:
        _fail(f"Integration target commit does not retain the historical completion: {change_id}")


def _journal_for_plan(plan: DeliveryIntegrationRetirementPlan, staging_root: Path) -> _RetirementJournal:
    journal_changes = []
    for change in plan.changes:
        relative_verification = tuple(path.relative_to(plan.runtime_root) for path in change.verification_paths)
        relative_publication = tuple(path.relative_to(plan.runtime_root) for path in change.publication_paths)
        journal_changes.append(
            _JournalChange(
                change_id=change.change_id,
                runtime_change_root=change.runtime_change_root,
                coordination_path=change.coordination_path,
                stage_change_root=staging_root / "changes" / change.change_id,
                stage_coordination_path=staging_root / "coordination" / f"{change.change_id}.json",
                verification_paths=change.verification_paths,
                stage_verification_paths=tuple(
                    staging_root / "runtime" / relative for relative in relative_verification
                ),
                frontier_sha256=_digest(change.frontier_bytes),
                coordination_sha256=_digest(change.coordination_bytes),
                worktree_path=change.worktree.path if change.worktree is not None else None,
                branch=change.worktree.branch if change.worktree is not None else None,
                worktree_head=change.worktree.head if change.worktree is not None else None,
                publication_paths=change.publication_paths,
                stage_publication_paths=tuple(staging_root / "runtime" / relative for relative in relative_publication),
                publication_sha256=tuple(_digest(path.read_bytes()) for path in change.publication_paths),
                publication_lock_path=change.publication_lock_path,
                publication_state_lock_paths=change.publication_state_lock_paths,
            )
        )
    return _RetirementJournal(
        repository_root=plan.repository_root,
        runtime_root=plan.runtime_root,
        worktree_root=plan.worktree_root,
        target_ref=plan.target_ref,
        target_commit=plan.target_commit,
        staging_root=staging_root,
        changes=tuple(journal_changes),
    )


def _journal_relative(path: Path, root: Path, detail: str) -> Path:
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        _fail(detail)
        raise AssertionError from exc


def _require_journal_path(actual: Path, expected: Path) -> None:
    if actual.resolve() != expected.resolve():
        _fail("Integration retirement journal path identity is invalid")


def _validate_journal_worktree(change: _JournalChange, worktree_root: Path) -> None:
    if change.worktree_path is None:
        if change.branch is not None or change.worktree_head is not None:
            _fail("Integration retirement journal worktree identity is incomplete")
        return
    relative = _journal_relative(
        change.worktree_path, worktree_root, "Integration retirement journal worktree path is unsafe"
    )
    if relative.parts != (change.change_id,):
        _fail("Integration retirement journal worktree path is unsafe")
    if not change.branch or change.worktree_head is None:
        _fail("Integration retirement journal worktree identity is incomplete")
    if not _SAFE_COMMIT.fullmatch(change.worktree_head):
        _fail("Integration retirement journal worktree head is invalid")


def _validate_journal_verification(
    change: _JournalChange,
    verification_root: Path,
    staging_root: Path,
) -> None:
    if len(change.verification_paths) != len(change.stage_verification_paths):
        _fail("Integration retirement journal verification inventory is invalid")
    for actual, staged in zip(change.verification_paths, change.stage_verification_paths, strict=True):
        relative = _journal_relative(
            actual, verification_root, "Integration retirement journal verification path is unsafe"
        )
        if len(relative.parts) != _VERIFICATION_PATH_PARTS or relative.parts[0] not in {"requests", "receipts"}:
            _fail("Integration retirement journal verification path is unsafe")
        _require_journal_path(staged, staging_root / "runtime" / relative)


def _validate_publication_relative(change: _JournalChange, relative: Path) -> None:
    if not relative.parts or relative.parts[0] != "publications":
        _fail("Integration retirement journal publication path is unsafe")
    if len(relative.parts) == _PUBLICATION_PATH_PARTS:
        if relative.parts[1:3] not in _PUBLICATION_FLAT_ROOTS or not relative.parts[3].endswith(".json"):
            _fail("Integration retirement journal publication path is unsafe")
        if relative.parts[1:3] == ("pull-requests", "receipts") and relative.parts[3] != f"{change.change_id}.json":
            _fail("Integration retirement journal publication identity is invalid")
        return
    if (
        len(relative.parts) == _PUBLICATION_PATH_PARTS + 1
        and relative.parts[1:3] in _PUBLICATION_NESTED_ROOTS
        and relative.parts[3] == change.change_id
        and relative.parts[4].endswith(".json")
        and _SAFE_DIGEST.fullmatch(relative.parts[4].removesuffix(".json")) is not None
    ):
        return
    _fail("Integration retirement journal publication path is unsafe")


def _validate_journal_publication_source(
    change: _JournalChange,
    actual: Path,
    staged: Path,
    digest: str,
    phase: Literal["staged", "cleanup"],
) -> None:
    actual_present = actual.exists() or actual.is_symlink()
    staged_present = staged.exists() or staged.is_symlink()
    if actual_present and staged_present:
        _fail("Integration retirement journal publication state is duplicated")
    if not actual_present and not staged_present:
        if phase == "cleanup":
            return
        _fail("Integration retirement journal publication state is missing")
    source = actual if actual_present else staged
    _require_publication_file(source)
    if _digest(source.read_bytes()) != digest:
        _fail("Integration retirement journal publication digest differs from its source")
    if _publication_payload(source).get("change_id") != change.change_id:
        _fail("Integration retirement journal publication identity is invalid")


def _validate_journal_publication(
    change: _JournalChange,
    runtime_root: Path,
    staging_root: Path,
    phase: Literal["staged", "cleanup"],
) -> None:
    if not (len(change.publication_paths) == len(change.stage_publication_paths) == len(change.publication_sha256)):
        _fail("Integration retirement journal publication inventory is invalid")
    for actual, staged, digest in zip(
        change.publication_paths,
        change.stage_publication_paths,
        change.publication_sha256,
        strict=True,
    ):
        relative = _journal_relative(actual, runtime_root, "Integration retirement journal publication path is unsafe")
        _validate_publication_relative(change, relative)
        if not _SAFE_DIGEST.fullmatch(digest):
            _fail("Integration retirement journal publication digest is invalid")
        _require_journal_path(staged, staging_root / "runtime" / relative)
        _validate_journal_publication_source(change, actual, staged, digest, phase)


def _validate_journal_change(
    change: _JournalChange,
    journal: _RetirementJournal,
) -> None:
    runtime_root = journal.repository_root / _RUNTIME_RELATIVE
    expected_paths = (
        (change.runtime_change_root, runtime_root / "changes" / change.change_id),
        (change.coordination_path, runtime_root / "claims/changes" / f"{change.change_id}.json"),
        (change.stage_change_root, journal.staging_root / "changes" / change.change_id),
        (change.stage_coordination_path, journal.staging_root / "coordination" / f"{change.change_id}.json"),
        (change.publication_lock_path, runtime_root / _PUBLICATION_LOCKS_RELATIVE / change.change_id),
    )
    for actual, expected in expected_paths:
        _require_journal_path(actual, expected)
    _validate_journal_worktree(change, journal.repository_root / _WORKTREES_RELATIVE)
    _validate_journal_verification(change, runtime_root / _VERIFICATION_RELATIVE, journal.staging_root)
    expected_state_lock_paths = _publication_state_lock_paths(runtime_root, change.change_id)
    if change.publication_state_lock_paths != expected_state_lock_paths:
        _fail("Integration retirement journal publication lock inventory is invalid")
    _validate_journal_publication(change, runtime_root, journal.staging_root, journal.phase)


def _validate_journal(root: Path, journal: _RetirementJournal) -> None:
    repository_root = root.resolve()
    expected = {
        "repository_root": repository_root,
        "runtime_root": repository_root / _RUNTIME_RELATIVE,
        "worktree_root": repository_root / _WORKTREES_RELATIVE,
    }
    for field, path in expected.items():
        _require_journal_path(getattr(journal, field), path)
    staging_relative = _journal_relative(
        journal.staging_root,
        repository_root / _STAGING_RELATIVE,
        "Integration retirement staging path is unsafe",
    )
    if len(staging_relative.parts) != 1 or not _SAFE_CHANGE_ID.fullmatch(staging_relative.name):
        _fail("Integration retirement staging path is unsafe")
    change_ids: set[str] = set()
    for change in journal.changes:
        if not _SAFE_CHANGE_ID.fullmatch(change.change_id) or change.change_id in change_ids:
            _fail("Integration retirement journal Change identity is invalid")
        change_ids.add(change.change_id)
        _validate_journal_change(change, journal)


def _require_target_snapshot(root: Path, target_ref: str, target_commit: str) -> None:
    current = _resolve_target(root, target_ref)
    if current != target_commit:
        _fail(f"configured target moved during Integration retirement: {target_ref}")


def _require_expected_plan(
    plan: DeliveryIntegrationRetirementPlan,
    expected_target_commit: str | None,
    expected_change_ids: tuple[str, ...] | None,
) -> None:
    if expected_target_commit is not None and plan.target_commit != expected_target_commit:
        _fail("Integration retirement target differs from its planned target snapshot")
    if expected_change_ids is not None and tuple(change.change_id for change in plan.changes) != expected_change_ids:
        _fail("Integration retirement Change set differs from its planned state")


def _require_recovered_cleanup(
    journal: _RetirementJournal,
    expected_target_commit: str | None,
    expected_change_ids: tuple[str, ...] | None,
) -> None:
    if expected_target_commit is not None and journal.target_commit != expected_target_commit:
        _fail("Integration retirement target differs from its planned target snapshot")
    change_ids = tuple(change.change_id for change in journal.changes)
    if expected_change_ids is not None and change_ids != expected_change_ids:
        _fail("Integration retirement Change set differs from its planned state")


def _write_journal(journal: _RetirementJournal) -> None:
    path = journal.repository_root / RETIREMENT_JOURNAL_RELATIVE
    if path.exists() or path.parent.is_symlink() or not path.parent.is_dir():
        _fail("Integration retirement journal destination is unsafe")
    _validate_journal(journal.repository_root, journal)
    atomic_write(path, journal.model_dump_json() + "\n")


def _rewrite_journal(journal: _RetirementJournal) -> None:
    path = journal.repository_root / RETIREMENT_JOURNAL_RELATIVE
    if path.is_symlink() or not path.is_file():
        _fail("Integration retirement journal path is unsafe")
    atomic_write(path, journal.model_dump_json() + "\n")


def _load_journal(root: Path) -> _RetirementJournal:
    path = root / RETIREMENT_JOURNAL_RELATIVE
    if path.is_symlink() or not path.is_file():
        _fail("Integration retirement journal path is unsafe")
    journal = _load_model(path, _RetirementJournal)
    _validate_journal(root, journal)
    return journal


def _move(source: Path, target: Path) -> None:
    if not source.exists() or source.is_symlink():
        _fail(f"Integration retirement source is missing or unsafe: {source}")
    if target.exists() or target.is_symlink():
        _fail(f"Integration retirement destination is not empty: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)


def _stage(journal: _RetirementJournal) -> None:
    journal.staging_root.mkdir(parents=True, exist_ok=True)
    for change in journal.changes:
        if _digest((change.runtime_change_root / "frontier.json").read_bytes()) != change.frontier_sha256:
            _fail(f"Delivery frontier changed before retirement: {change.change_id}")
        if _digest(change.coordination_path.read_bytes()) != change.coordination_sha256:
            _fail(f"Delivery coordination changed before retirement: {change.change_id}")
        for path, digest in zip(change.publication_paths, change.publication_sha256, strict=True):
            if _digest(path.read_bytes()) != digest:
                _fail(f"Delivery publication record changed before retirement: {change.change_id}")
    for change in journal.changes:
        _move(change.runtime_change_root, change.stage_change_root)
        _move(change.coordination_path, change.stage_coordination_path)
        for source, target in zip(change.verification_paths, change.stage_verification_paths, strict=True):
            _move(source, target)
        for source, target in zip(change.publication_paths, change.stage_publication_paths, strict=True):
            _move(source, target)


def _remove_worktrees(root: Path, journal: _RetirementJournal) -> None:
    for change in journal.changes:
        if change.worktree_path is not None:
            if change.branch is None or change.worktree_head is None:
                _fail(f"Integration retirement worktree identity is incomplete: {change.change_id}")
            _require_branch(root, change.branch, change.worktree_head)
            try:
                ChangeWorkspaceManager.remove_worktree(root, change.worktree_path)
            except subprocess.CalledProcessError as exc:
                detail = exc.stderr.decode(errors="replace").strip() or "Git worktree removal failed"
                _fail(detail)


def _remove_publication_lock(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink() or not path.is_dir():
        _fail(f"Integration publication-lock path is unsafe: {path}")
    entries = tuple(path.iterdir())
    unexpected = tuple(entry for entry in entries if entry.name != ".storage.lock")
    if unexpected:
        _fail(f"Integration publication-lock path contains unexpected state: {path}")
    lock_file = path / ".storage.lock"
    if lock_file.exists():
        if lock_file.is_symlink() or not lock_file.is_file():
            _fail(f"Integration publication-lock file is unsafe: {lock_file}")
        lock_file.unlink()
    path.rmdir()


def _remove_publication_locks(journal: _RetirementJournal) -> None:
    for change in journal.changes:
        _remove_publication_lock(change.publication_lock_path)
        for path in change.publication_state_lock_paths:
            _remove_publication_lock(path)


def _remove_empty_staging_parent(staging_root: Path) -> None:
    parent = staging_root.parent
    if not parent.exists():
        return
    if parent.is_symlink() or not parent.is_dir():
        _fail(f"Integration retirement staging parent is unsafe: {parent}")
    if not any(parent.iterdir()):
        parent.rmdir()


def _require_branch(root: Path, branch: str, head: str) -> None:
    branch_head = _git(root, "rev-parse", f"refs/heads/{branch}^{{commit}}").stdout.decode().strip()
    if branch_head != head:
        _fail(f"retired Change branch moved during Integration retirement: {branch}")


def _validate_postconditions(root: Path, journal: _RetirementJournal) -> None:
    registrations = {item.path: item for item in _registered_worktrees(root)}
    for change in journal.changes:
        if change.runtime_change_root.exists() or change.coordination_path.exists():
            _fail(f"retired Delivery state remains present: {change.change_id}")
        if any(path.exists() for path in change.verification_paths):
            _fail(f"retired Integration verification remains present: {change.change_id}")
        if any(path.exists() for path in change.publication_paths):
            _fail(f"retired Delivery publication state remains present: {change.change_id}")
        if change.worktree_path is not None and change.worktree_path in registrations:
            _fail(f"retired Delivery worktree remains registered: {change.change_id}")
        if change.publication_lock_path.exists():
            _fail(f"retired Delivery publication lock remains registered: {change.change_id}")
        if change.branch is not None and change.worktree_head is not None:
            _require_branch(root, change.branch, change.worktree_head)
    capacity = _load_model(journal.runtime_root / "capacity.json", CapacityLedger)
    if capacity.change_ids:
        _fail("active Delivery capacity holders remain after Integration retirement")
    if _has_entries(journal.runtime_root / ".runtime-transactions"):
        _fail("pending Delivery runtime transactions remain after Integration retirement")


def _restore_worktree(root: Path, change: _JournalChange) -> None:
    if change.worktree_path is None:
        return
    registrations = _registered_worktrees(root)
    matching = tuple(item for item in registrations if item.path == change.worktree_path.resolve())
    if matching:
        if len(matching) != 1 or matching[0].branch != change.branch or matching[0].head != change.worktree_head:
            _fail(f"Integration retirement recovery found a mismatched worktree: {change.change_id}")
        return
    if change.branch is None or change.worktree_head is None:
        _fail(f"Integration retirement recovery lacks branch identity: {change.change_id}")
    if change.worktree_path.exists():
        _fail(f"Integration retirement recovery found an unregistered worktree path: {change.change_id}")
    _require_branch(root, change.branch, change.worktree_head)
    ChangeWorkspaceManager.restore_worktree(root, change.worktree_path, change.branch)


def _recover_staged_paths(sources: tuple[Path, ...], staged_paths: tuple[Path, ...], kind: str) -> None:
    for source, staged in zip(sources, staged_paths, strict=True):
        if source.exists() and staged.exists():
            _fail(f"Integration retirement recovery found both {kind} states: {source}")
        if staged.exists():
            _move(staged, source)


def _recover_change(root: Path, change: _JournalChange) -> None:
    if change.runtime_change_root.exists() and change.stage_change_root.exists():
        _fail(f"Integration retirement recovery found both runtime and staged Change state: {change.change_id}")
    if change.stage_change_root.exists():
        _move(change.stage_change_root, change.runtime_change_root)
    if change.coordination_path.exists() and change.stage_coordination_path.exists():
        _fail(f"Integration retirement recovery found both coordination states: {change.change_id}")
    if change.stage_coordination_path.exists():
        _move(change.stage_coordination_path, change.coordination_path)
    _recover_staged_paths(change.verification_paths, change.stage_verification_paths, "verification")
    _recover_staged_paths(change.publication_paths, change.stage_publication_paths, "publication")
    _restore_worktree(root, change)
    change.publication_lock_path.mkdir(parents=True, exist_ok=True)
    for path in change.publication_state_lock_paths:
        path.mkdir(parents=True, exist_ok=True)


def _recover_retirement(root: Path) -> _RetirementJournal | None:
    journal_path = root / RETIREMENT_JOURNAL_RELATIVE
    if not journal_path.exists():
        return None
    journal = _load_journal(root)
    if journal.phase == "cleanup":
        if journal.staging_root.exists():
            shutil.rmtree(journal.staging_root)
        _remove_empty_staging_parent(journal.staging_root)
        _remove_publication_locks(journal)
        journal_path.unlink()
        return journal
    for change in journal.changes:
        _recover_change(root, change)
    if journal.staging_root.exists():
        shutil.rmtree(journal.staging_root)
    _remove_empty_staging_parent(journal.staging_root)
    journal_path.unlink()
    return None


def _execute_retirement(repository_root: Path, journal: _RetirementJournal) -> None:
    try:
        _stage(journal)
        _require_target_snapshot(repository_root, journal.target_ref, journal.target_commit)
        _remove_worktrees(repository_root, journal)
        _require_target_snapshot(repository_root, journal.target_ref, journal.target_commit)
    except _RETIREMENT_FAILURES:
        _recover_retirement(repository_root)
        raise


def _execute_retirement_cleanup(repository_root: Path, journal: _RetirementJournal) -> None:
    try:
        _remove_publication_locks(journal)
        _require_target_snapshot(repository_root, journal.target_ref, journal.target_commit)
        _validate_postconditions(repository_root, journal)
    except _RETIREMENT_FAILURES:
        _recover_retirement(repository_root)
        raise


def _validate_post_retirement_startup(repository_root: Path) -> None:
    try:
        load_delivery_application(
            _load_startup_config(repository_root),
            workspace_root=repository_root,
        )
    except Exception as exc:  # noqa: BLE001 - startup failure must be reported after retirement.
        _fail(f"Delivery startup validation failed after Integration retirement: {exc}")


def _complete_retirement(repository_root: Path, journal: _RetirementJournal) -> None:
    cleanup_journal = journal.model_copy(update={"phase": "cleanup"})
    _rewrite_journal(cleanup_journal)
    try:
        if cleanup_journal.staging_root.exists():
            shutil.rmtree(cleanup_journal.staging_root)
        _remove_empty_staging_parent(cleanup_journal.staging_root)
    except OSError as exc:
        _fail(f"Integration retirement staging cleanup failed: {cleanup_journal.staging_root}")
        raise AssertionError from exc
    journal_path = repository_root / RETIREMENT_JOURNAL_RELATIVE
    try:
        journal_path.unlink()
    except OSError as exc:
        _fail(f"Integration retirement journal cleanup failed: {journal_path}")
        raise AssertionError from exc
    _validate_post_retirement_startup(repository_root)


def _retirement_change_ids(root: Path) -> tuple[str, ...]:
    journal_path = root / RETIREMENT_JOURNAL_RELATIVE
    if journal_path.exists():
        return tuple(change.change_id for change in _load_journal(root).changes)
    changes_root = root / _RUNTIME_RELATIVE / "changes"
    if not changes_root.exists():
        return ()
    _require_directory(changes_root)
    change_ids = []
    for change_root in sorted(changes_root.iterdir()):
        if change_root.is_symlink() or not change_root.is_dir():
            _fail(f"Delivery Change runtime path is unsafe: {change_root}")
        change_ids.append(change_root.name)
    return tuple(change_ids)


def _retirement_lock_roots(root: Path) -> tuple[Path, ...]:
    runtime_root = root / _RUNTIME_RELATIVE
    journal_path = root / RETIREMENT_JOURNAL_RELATIVE
    if journal_path.exists():
        _load_journal(root)
    return (
        runtime_root / _ACQUISITION_LOCK_RELATIVE,
        runtime_root / _INTEGRATION_LOCK_RELATIVE,
    )


def _retirement_publication_namespace_root(root: Path) -> Path:
    return root / _RUNTIME_RELATIVE / _PUBLICATION_LOCKS_RELATIVE


def _retirement_checkpoint_lock_roots(root: Path, change_ids: tuple[str, ...]) -> tuple[Path, ...]:
    runtime_root = root / _RUNTIME_RELATIVE
    return tuple(_publication_state_lock_paths(runtime_root, change_id)[0] for change_id in change_ids)


def _retirement_publication_lock_roots(
    root: Path,
    change_ids: tuple[str, ...] | None = None,
) -> tuple[Path, ...]:
    runtime_root = root / _RUNTIME_RELATIVE
    publication_root = runtime_root / _PUBLICATION_LOCKS_RELATIVE
    selected_change_ids = _retirement_change_ids(root) if change_ids is None else change_ids
    roots = []
    for change_id in selected_change_ids:
        roots.append(publication_root / change_id)
        roots.append(_publication_state_lock_paths(runtime_root, change_id)[1])
    return tuple(roots)


@contextmanager
def _retirement_outer_locks(
    root: Path,
    change_ids: tuple[str, ...],
    *,
    preserve_unjournaled: bool,
) -> Iterator[ExitStack]:
    child_paths = (
        *_retirement_checkpoint_lock_roots(root, change_ids),
        *_retirement_publication_lock_roots(root, change_ids),
    )
    preexisting = {path: path.exists() or path.is_symlink() for path in child_paths}
    journal_path = root / RETIREMENT_JOURNAL_RELATIVE
    entered = False
    try:
        with locked_roots(_retirement_lock_roots(root)), ExitStack() as checkpoint_locks:
            checkpoint_locks.enter_context(locked_roots(_retirement_checkpoint_lock_roots(root, change_ids)))
            with locked_roots((_retirement_publication_namespace_root(root),)):
                entered = True
                yield checkpoint_locks
    finally:
        if entered and not preserve_unjournaled and not journal_path.exists():
            for path, existed in preexisting.items():
                if not existed:
                    _remove_publication_lock(path)


def plan_delivery_integration_retirement(root: Path) -> DeliveryIntegrationRetirementPlan:
    """Validate one Integration retirement without changing files or Git registrations."""
    repository_root = root.expanduser().resolve()
    if (repository_root / RETIREMENT_JOURNAL_RELATIVE).exists():
        _fail("interrupted Integration retirement requires recovery with --apply")
    runtime_root = repository_root / _RUNTIME_RELATIVE
    worktree_root = repository_root / _WORKTREES_RELATIVE
    _require_ordering(repository_root, runtime_root)
    if not runtime_root.exists():
        if _has_entries(worktree_root):
            _fail("Delivery runtime is missing while managed worktrees remain")
        return DeliveryIntegrationRetirementPlan(
            repository_root=repository_root,
            runtime_root=runtime_root,
            worktree_root=worktree_root,
            target_ref="",
            target_commit="",
            changes=(),
            already_retired=True,
        )
    config = _load_startup_config(repository_root)
    target_ref = f"refs/remotes/{config.remote}/{config.target_branch}"
    target_commit = _resolve_target(repository_root, target_ref)
    frontiers, frontier_bytes, change_roots = _load_frontiers(runtime_root)
    coordinations, coordination_bytes = _load_coordinations(runtime_root, set(frontiers))
    _require_quiescent(frontiers, coordinations, runtime_root)
    registrations = _registered_worktrees(repository_root)
    candidates = {
        change_id: frontier for change_id, frontier in frontiers.items() if frontier.integration_completion is not None
    }
    verification = _verification_paths(repository_root, runtime_root, candidates)
    history_context = _HistoryContext(
        repository_root=repository_root,
        runtime_root=runtime_root,
        target_commit=target_commit,
        target_branch=config.target_branch,
    )
    changes = []
    for change_id, frontier in candidates.items():
        _require_history_proof(history_context, change_id, frontier)
        coordination = coordinations[change_id]
        worktree = _change_worktree(repository_root, coordination, registrations)
        publication_paths = _publication_paths(runtime_root, change_id)
        changes.append(
            _RetirementChange(
                change_id=change_id,
                runtime_change_root=change_roots[change_id],
                coordination_path=runtime_root / "claims/changes" / f"{change_id}.json",
                frontier=frontier,
                frontier_bytes=frontier_bytes[change_id],
                coordination=coordination,
                coordination_bytes=coordination_bytes[change_id],
                worktree=worktree,
                verification_paths=verification[change_id],
                publication_paths=publication_paths,
                publication_lock_path=runtime_root / _PUBLICATION_LOCKS_RELATIVE / change_id,
                publication_state_lock_paths=_publication_state_lock_paths(runtime_root, change_id),
            )
        )
    return DeliveryIntegrationRetirementPlan(
        repository_root=repository_root,
        runtime_root=runtime_root,
        worktree_root=worktree_root,
        target_ref=target_ref,
        target_commit=target_commit,
        changes=tuple(changes),
        already_retired=not changes,
    )


def _apply_delivery_integration_retirement(
    root: Path,
    *,
    expected_target_commit: str | None = None,
    expected_change_ids: tuple[str, ...] | None = None,
) -> DeliveryIntegrationRetirementPlan:
    repository_root = root.expanduser().resolve()
    runtime_root = repository_root / _RUNTIME_RELATIVE
    journal_path = repository_root / RETIREMENT_JOURNAL_RELATIVE
    if not journal_path.exists() and not runtime_root.exists():
        plan = plan_delivery_integration_retirement(repository_root)
        _require_expected_plan(plan, expected_target_commit, expected_change_ids)
        return plan
    delivery_root = repository_root / ".owlbear/delivery"
    entry_journal = _load_journal(repository_root) if journal_path.exists() else None
    if entry_journal is not None:
        lock_change_ids = tuple(change.change_id for change in entry_journal.changes)
        bound_target_commit = (
            expected_target_commit if expected_target_commit is not None else entry_journal.target_commit
        )
        bound_change_ids = expected_change_ids if expected_change_ids is not None else lock_change_ids
    else:
        initial_plan = plan_delivery_integration_retirement(repository_root)
        _require_expected_plan(initial_plan, expected_target_commit, expected_change_ids)
        if initial_plan.already_retired:
            return initial_plan
        lock_change_ids = tuple(change.change_id for change in initial_plan.changes)
        bound_target_commit = (
            expected_target_commit if expected_target_commit is not None else initial_plan.target_commit
        )
        bound_change_ids = expected_change_ids if expected_change_ids is not None else lock_change_ids
    with _retirement_outer_locks(
        repository_root,
        lock_change_ids,
        preserve_unjournaled=entry_journal is not None,
    ) as checkpoint_locks:
        with ExitStack() as publication_locks:
            publication_locks.enter_context(
                locked_roots(_retirement_publication_lock_roots(repository_root, lock_change_ids))
            )
            with locked_roots((delivery_root, runtime_root)):
                recovered_cleanup = _recover_retirement(repository_root)
                plan = plan_delivery_integration_retirement(repository_root)
                if recovered_cleanup is not None and plan.already_retired:
                    _require_recovered_cleanup(recovered_cleanup, bound_target_commit, bound_change_ids)
                    _validate_post_retirement_startup(repository_root)
                    return plan
                _require_expected_plan(plan, bound_target_commit, bound_change_ids)
                if plan.already_retired:
                    return plan
                _require_target_snapshot(repository_root, plan.target_ref, plan.target_commit)
                operation_id = _digest(
                    f"{plan.target_commit}:{','.join(change.change_id for change in plan.changes)}".encode()
                )[:32]
                staging_root = repository_root / _STAGING_RELATIVE / operation_id
                if staging_root.exists():
                    _fail(f"stale Integration retirement staging path requires inspection: {staging_root}")
                journal = _journal_for_plan(plan, staging_root)
                _write_journal(journal)
                _execute_retirement(repository_root, journal)
            checkpoint_locks.close()
        with locked_roots((delivery_root, runtime_root)):
            _execute_retirement_cleanup(repository_root, journal)
            _complete_retirement(repository_root, journal)
        return plan


def apply_delivery_integration_retirement(plan: DeliveryIntegrationRetirementPlan) -> None:
    """Apply one validated Integration retirement while retaining exact recovery state."""
    _apply_delivery_integration_retirement(
        plan.repository_root,
        expected_target_commit=plan.target_commit or None,
        expected_change_ids=tuple(change.change_id for change in plan.changes),
    )


def main() -> None:
    """Preview or apply terminal legacy Integration retirement."""
    parser = argparse.ArgumentParser(prog="retire-delivery-integration")
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true", help="Apply the validated Integration retirement")
    arguments = parser.parse_args()
    try:
        if arguments.apply:
            plan = _apply_delivery_integration_retirement(arguments.path)
        else:
            plan = plan_delivery_integration_retirement(arguments.path)
    except DeliveryIntegrationRetirementError as exc:
        parser.error(str(exc))
    disposition = "already retired" if plan.already_retired else "applied" if arguments.apply else "ready"
    print(f"Delivery Integration retirement: {disposition}")  # noqa: T201
    if plan.target_commit:
        print(f"Target snapshot: {plan.target_commit}")  # noqa: T201
    if plan.changes:
        print(f"Changes: {', '.join(change.change_id for change in plan.changes)}")  # noqa: T201


__all__ = [
    "DeliveryIntegrationRetirementError",
    "DeliveryIntegrationRetirementPlan",
    "apply_delivery_integration_retirement",
    "main",
    "plan_delivery_integration_retirement",
]
