"""One-way migration from retired Delivery state roots to canonical ownership."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from owlbear_delivery.change_workspace import CapacityLedger, ChangeCoordination
from owlbear_delivery.delivery_runtime import (
    DeliveryFrontier,
    DeliveryIntegrationCompletion,
    parse_delivery_frontier,
)
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.storage_io import atomic_write, locked_roots
from owlbear_delivery.target_contract import DeliveryContract

_ARCHIVE_RELATIVE = Path(".owlbear/legacy/delivery-state-migration")
_LEGACY_TARGET_RELATIVE = Path(".owlbear/target")
_LEGACY_WORKTREES_RELATIVE = Path(".owlbear/worktrees")
_RUNTIME_RELATIVE = Path(".owlbear/delivery/runtime")
_WORKTREES_RELATIVE = Path(".owlbear/delivery/worktrees")
_PRESERVED_WORKTREES_RELATIVE = Path(".owlbear/scratch/delivery-state-migration-worktrees")
_JOURNAL_RELATIVE = Path(".owlbear/delivery/migration.json")
RETIREMENT_JOURNAL_RELATIVE = Path(".owlbear/delivery/integration-retirement.json")


class DeliveryStateMigrationError(RuntimeError):
    """Retired Delivery state cannot be migrated without ambiguity or loss."""


_MIGRATION_FAILURES = (DeliveryStateMigrationError, OSError)


@dataclass(frozen=True)
class _RegisteredWorktree:
    path: Path
    head: str
    branch: str | None


@dataclass(frozen=True)
class _MigrationChange:
    change_id: str
    coordination: ChangeCoordination
    frontier: DeliveryFrontier
    legacy_completion: DeliveryIntegrationCompletion | None
    source_worktree: Path
    target_worktree: Path
    registered: bool


@dataclass(frozen=True)
class DeliveryStateMigrationPlan:
    """Validated paths and identities for one migration attempt."""

    repository_root: Path
    legacy_target: Path
    legacy_worktrees: Path
    runtime_target: Path
    worktree_target: Path
    preserved_worktree_target: Path
    archive_root: Path
    changes: tuple[_MigrationChange, ...]
    preserved_worktrees: tuple[_RegisteredWorktree, ...]
    already_migrated: bool = False


class _JournalMove(BaseModel):
    source: Path
    target: Path


class _MigrationJournal(BaseModel):
    schema_version: int = 1
    repository_root: Path
    legacy_target: Path
    legacy_worktrees: Path
    runtime_target: Path
    worktree_target: Path
    preserved_worktree_target: Path
    archive_root: Path
    legacy_worktrees_existed: bool
    moves: tuple[_JournalMove, ...]


def _fail(detail: str) -> None:
    raise DeliveryStateMigrationError(detail)


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


def _load_model[Model: BaseModel](path: Path, model_type: type[Model]) -> Model:
    try:
        return model_type.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as exc:
        _fail(f"invalid migration authority: {path}")
        raise AssertionError from exc


def _require_empty_destination(path: Path) -> None:
    if path.is_symlink() or (path.exists() and (not path.is_dir() or any(path.iterdir()))):
        _fail(f"migration destination must be absent or empty: {path}")


def _require_symlink_free_tree(root: Path) -> None:
    if root.is_symlink() or not root.is_dir():
        _fail(f"retired Delivery state path is unsafe: {root}")
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        parent = Path(directory)
        for name in (*directory_names, *file_names):
            if (parent / name).is_symlink():
                _fail(f"retired Delivery state contains a symlink: {parent / name}")


def _load_migration_frontier(path: Path) -> tuple[DeliveryFrontier, DeliveryIntegrationCompletion | None]:
    try:
        payload = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"retired Delivery frontier is malformed: {path}")
        raise AssertionError from exc
    if not isinstance(payload, dict):
        _fail(f"retired Delivery frontier is malformed: {path}")
    result_id = payload.get("integration_result_id")
    completion_payload = payload.get("integration_completion")
    legacy_completion = None
    if result_id is not None or completion_payload is not None:
        try:
            legacy_completion = DeliveryIntegrationCompletion.model_validate(completion_payload)
        except (TypeError, ValidationError) as exc:
            _fail(f"retired Delivery Integration completion is invalid: {path}")
            raise AssertionError from exc
        if result_id != legacy_completion.completion_id:
            _fail(f"retired Delivery Integration completion identity differs: {path}")
        payload = dict(payload)
        payload.pop("integration_result_id", None)
        payload.pop("integration_completion", None)
    try:
        frontier, _canonical = parse_delivery_frontier(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        )
    except (TypeError, ValueError, ValidationError) as exc:
        _fail(f"retired Delivery frontier is invalid: {path}")
        raise AssertionError from exc
    return frontier, legacy_completion


def _runtime_authority(
    legacy_target: Path,
) -> tuple[dict[str, DeliveryContract], dict[str, DeliveryFrontier], dict[str, DeliveryIntegrationCompletion]]:
    changes_root = legacy_target / "delivery/changes"
    if not changes_root.is_dir() or changes_root.is_symlink():
        _fail("retired Delivery changes are missing or unsafe")
    contracts: dict[str, DeliveryContract] = {}
    frontiers: dict[str, DeliveryFrontier] = {}
    legacy_completions: dict[str, DeliveryIntegrationCompletion] = {}
    for change_root in sorted(changes_root.iterdir()):
        if not change_root.is_dir() or change_root.is_symlink():
            _fail(f"retired Delivery change path is unsafe: {change_root}")
        contract = _load_model(change_root / "contract.json", DeliveryContract)
        frontier, legacy_completion = _load_migration_frontier(change_root / "frontier.json")
        if contract.change_id != change_root.name:
            _fail(f"retired Delivery change identity mismatch: {change_root}")
        contracts[contract.change_id] = contract
        frontiers[contract.change_id] = frontier
        if legacy_completion is not None:
            legacy_completions[contract.change_id] = legacy_completion
    return contracts, frontiers, legacy_completions


def _require_quiescent(frontiers: dict[str, DeliveryFrontier], capacity: CapacityLedger) -> None:
    if capacity.change_ids:
        _fail("active capacity holders block Delivery state migration")
    for change_id, frontier in frontiers.items():
        if frontier.integration_repair_claim is not None or any(
            binding.active_claim is not None for binding in frontier.bindings
        ):
            _fail(f"active Delivery claim blocks migration: {change_id}")


def _coordination_authority(runtime_root: Path) -> tuple[CapacityLedger, dict[str, ChangeCoordination]]:
    capacity = _load_model(runtime_root / "capacity.json", CapacityLedger)
    coordination_root = runtime_root / "coordination"
    if not coordination_root.is_dir() or coordination_root.is_symlink():
        _fail("retired Delivery coordination is missing or unsafe")
    coordinations = {}
    for path in sorted(coordination_root.glob("*.json")):
        coordination = _load_model(path, ChangeCoordination)
        if coordination.change_id != path.stem:
            _fail(f"retired coordination identity mismatch: {path}")
        if coordination.writer is not None:
            _fail(f"active Delivery writer blocks migration: {coordination.change_id}")
        coordinations[coordination.change_id] = coordination
    return capacity, coordinations


def _validate_registered_change_worktree(
    root: Path,
    change_id: str,
    coordination: ChangeCoordination,
    registration: _RegisteredWorktree,
    *,
    terminal: bool,
) -> None:
    if registration.path.is_symlink() or not registration.path.is_dir():
        _fail(f"registered worktree is missing or unsafe: {change_id}")
    if registration.branch != coordination.branch:
        _fail(f"registered worktree identity differs from reviewed coordination: {change_id}")
    branch_head = _git(root, "rev-parse", coordination.branch).stdout.decode().strip()
    if registration.head != branch_head:
        _fail(f"registered worktree head differs from its branch: {change_id}")
    if not terminal and registration.head != coordination.last_reviewed_commit:
        _fail(f"nonterminal worktree differs from its reviewed boundary: {change_id}")


def _migration_changes(
    root: Path,
    frontiers: dict[str, DeliveryFrontier],
    coordinations: dict[str, ChangeCoordination],
    registered: tuple[_RegisteredWorktree, ...],
    legacy_completions: dict[str, DeliveryIntegrationCompletion],
) -> tuple[tuple[_MigrationChange, ...], tuple[_RegisteredWorktree, ...]]:
    if set(frontiers) != set(coordinations):
        _fail("retired runtime and coordination Change identities differ")
    legacy_root = (root / _LEGACY_WORKTREES_RELATIVE).resolve()
    target_root = (root / _WORKTREES_RELATIVE).resolve()
    registrations = {item.path: item for item in registered}
    changes = []
    owned_paths = set()
    for change_id in sorted(frontiers):
        frontier = frontiers[change_id]
        coordination = coordinations[change_id]
        source = (legacy_root / change_id).resolve()
        target = (target_root / change_id).resolve()
        if coordination.worktree_path.resolve() not in {source, target}:
            _fail(f"coordination names an unexpected worktree path: {change_id}")
        registration = registrations.get(source) or registrations.get(target)
        if registration is not None:
            _validate_registered_change_worktree(
                root,
                change_id,
                coordination,
                registration,
                terminal=frontier.change_completion is not None or change_id in legacy_completions,
            )
            owned_paths.add(registration.path)
        elif frontier.change_completion is None and change_id not in legacy_completions:
            _fail(f"nonterminal Change has no registered worktree: {change_id}")
        changes.append(
            _MigrationChange(
                change_id,
                coordination,
                frontier,
                legacy_completions.get(change_id),
                source,
                target,
                registration is not None,
            )
        )
    preserved = tuple(
        item for item in registered if item.path.is_relative_to(legacy_root) and item.path not in owned_paths
    )
    for worktree in preserved:
        if worktree.path.is_symlink() or not worktree.path.is_dir():
            _fail(f"preserved registered worktree is missing or unsafe: {worktree.path}")
    return tuple(changes), preserved


def plan_delivery_state_migration(root: Path) -> DeliveryStateMigrationPlan:
    """Validate one migration without changing files or Git registrations."""
    repository_root = root.expanduser().resolve()
    if (repository_root / RETIREMENT_JOURNAL_RELATIVE).exists():
        _fail("interrupted Integration retirement requires recovery before path migration")
    if (repository_root / _JOURNAL_RELATIVE).exists():
        _fail("interrupted Delivery migration requires recovery with --apply")
    registered = _registered_worktrees(repository_root)
    if not registered or registered[0].path != repository_root:
        _fail("Delivery migration must run from the primary Git worktree")
    legacy_target = repository_root / _LEGACY_TARGET_RELATIVE
    legacy_worktrees = repository_root / _LEGACY_WORKTREES_RELATIVE
    archive_root = repository_root / _ARCHIVE_RELATIVE
    runtime_target = repository_root / _RUNTIME_RELATIVE
    worktree_target = repository_root / _WORKTREES_RELATIVE
    preserved_worktree_target = repository_root / _PRESERVED_WORKTREES_RELATIVE
    if not legacy_target.exists():
        if archive_root.is_dir() and runtime_target.is_dir() and not legacy_worktrees.exists():
            return DeliveryStateMigrationPlan(
                repository_root,
                legacy_target,
                legacy_worktrees,
                runtime_target,
                worktree_target,
                preserved_worktree_target,
                archive_root,
                (),
                (),
                already_migrated=True,
            )
        _fail("retired Delivery target state is absent")
    if legacy_target.is_symlink() or not legacy_target.is_dir():
        _fail("retired Delivery target path is unsafe")
    _require_symlink_free_tree(legacy_target)
    if archive_root.exists():
        _fail(f"migration archive already exists: {archive_root}")
    _require_empty_destination(runtime_target)
    _require_empty_destination(worktree_target)
    _require_empty_destination(preserved_worktree_target)
    _contracts, frontiers, legacy_completions = _runtime_authority(legacy_target)
    capacity, coordinations = _coordination_authority(legacy_target / "target-runtime")
    _require_quiescent(frontiers, capacity)
    changes, preserved_worktrees = _migration_changes(
        repository_root,
        frontiers,
        coordinations,
        registered,
        legacy_completions,
    )
    return DeliveryStateMigrationPlan(
        repository_root,
        legacy_target,
        legacy_worktrees,
        runtime_target,
        worktree_target,
        preserved_worktree_target,
        archive_root,
        changes,
        preserved_worktrees,
    )


def _stage_runtime(plan: DeliveryStateMigrationPlan, staging: Path) -> None:
    legacy_runtime = plan.legacy_target / "target-runtime"
    shutil.copytree(plan.legacy_target / "delivery/changes", staging / "changes")
    shutil.copy2(legacy_runtime / "capacity.json", staging / "capacity.json")
    coordination_root = staging / "claims/changes"
    coordination_root.mkdir(parents=True)
    for change in plan.changes:
        updated = change.coordination.model_copy(update={"worktree_path": change.target_worktree})
        (coordination_root / f"{change.change_id}.json").write_bytes(updated.model_dump_json().encode() + b"\n")
    verification = legacy_runtime / "integration-verification"
    for kind in ("requests", "receipts"):
        source = verification / kind
        if source.is_dir():
            shutil.copytree(source, staging / "claims/integration-verification" / kind)


def _validate_staging(plan: DeliveryStateMigrationPlan, staging: Path) -> None:
    _load_model(staging / "capacity.json", CapacityLedger)
    for change in plan.changes:
        change_root = staging / "changes" / change.change_id
        contract = _load_model(change_root / "contract.json", DeliveryContract)
        frontier, legacy_completion = _load_migration_frontier(change_root / "frontier.json")
        coordination = _load_model(
            staging / "claims/changes" / f"{change.change_id}.json",
            ChangeCoordination,
        )
        if contract.change_id != change.change_id or coordination.worktree_path != change.target_worktree:
            _fail(f"staged Delivery identity mismatch: {change.change_id}")
        if frontier != change.frontier or legacy_completion != change.legacy_completion:
            _fail(f"staged Delivery frontier changed: {change.change_id}")


def _journal_for_plan(plan: DeliveryStateMigrationPlan) -> _MigrationJournal:
    moves = [
        _JournalMove(source=change.source_worktree, target=change.target_worktree)
        for change in plan.changes
        if change.registered
    ]
    for worktree in plan.preserved_worktrees:
        relative = worktree.path.relative_to(plan.legacy_worktrees.resolve())
        moves.append(_JournalMove(source=worktree.path, target=plan.preserved_worktree_target / relative))
    return _MigrationJournal(
        repository_root=plan.repository_root,
        legacy_target=plan.legacy_target,
        legacy_worktrees=plan.legacy_worktrees,
        runtime_target=plan.runtime_target,
        worktree_target=plan.worktree_target,
        preserved_worktree_target=plan.preserved_worktree_target,
        archive_root=plan.archive_root,
        legacy_worktrees_existed=plan.legacy_worktrees.exists(),
        moves=tuple(moves),
    )


def _validate_journal(root: Path, journal: _MigrationJournal) -> None:
    expected = {
        "repository_root": root,
        "legacy_target": root / _LEGACY_TARGET_RELATIVE,
        "legacy_worktrees": root / _LEGACY_WORKTREES_RELATIVE,
        "runtime_target": root / _RUNTIME_RELATIVE,
        "worktree_target": root / _WORKTREES_RELATIVE,
        "preserved_worktree_target": root / _PRESERVED_WORKTREES_RELATIVE,
        "archive_root": root / _ARCHIVE_RELATIVE,
    }
    identity_differs = any(getattr(journal, field).resolve() != path.resolve() for field, path in expected.items())
    if journal.schema_version != 1 or identity_differs:
        _fail("migration journal identity is invalid")
    legacy_root = journal.legacy_worktrees.resolve()
    allowed_targets = (journal.worktree_target.resolve(), journal.preserved_worktree_target.resolve())
    if len({move.source.resolve() for move in journal.moves}) != len(journal.moves):
        _fail("migration journal contains duplicate worktree sources")
    if len({move.target.resolve() for move in journal.moves}) != len(journal.moves):
        _fail("migration journal contains duplicate worktree targets")
    for move in journal.moves:
        source = move.source.resolve()
        target = move.target.resolve()
        if not source.is_relative_to(legacy_root) or not any(
            target.is_relative_to(allowed_root) for allowed_root in allowed_targets
        ):
            _fail("migration journal contains an unsafe worktree move")


def _write_journal(plan: DeliveryStateMigrationPlan) -> Path:
    journal_path = plan.repository_root / _JOURNAL_RELATIVE
    if journal_path.exists() or journal_path.parent.is_symlink() or not journal_path.parent.is_dir():
        _fail("migration journal destination is unsafe")
    journal = _journal_for_plan(plan)
    atomic_write(journal_path, journal.model_dump_json() + "\n")
    return journal_path


def _load_journal(root: Path) -> _MigrationJournal:
    journal_path = root / _JOURNAL_RELATIVE
    if journal_path.is_symlink() or not journal_path.is_file():
        _fail("migration journal path is unsafe")
    journal = _load_model(journal_path, _MigrationJournal)
    _validate_journal(root, journal)
    return journal


def _publish_migration(plan: DeliveryStateMigrationPlan, staging: Path) -> None:
    _stage_runtime(plan, staging)
    _validate_staging(plan, staging)
    plan.worktree_target.mkdir(parents=True, exist_ok=True)
    for change in plan.changes:
        if change.registered and change.source_worktree.exists():
            _git(plan.repository_root, "worktree", "move", str(change.source_worktree), str(change.target_worktree))
    if plan.preserved_worktrees:
        plan.preserved_worktree_target.mkdir(parents=True)
    for worktree in plan.preserved_worktrees:
        relative = worktree.path.relative_to(plan.legacy_worktrees.resolve())
        target = plan.preserved_worktree_target / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _git(plan.repository_root, "worktree", "move", str(worktree.path), str(target))
    staging.rename(plan.runtime_target)
    plan.archive_root.mkdir(parents=True)
    plan.legacy_target.rename(plan.archive_root / "target")
    if plan.legacy_worktrees.exists():
        plan.legacy_worktrees.rename(plan.archive_root / "worktrees")


def _remove_empty_directory(path: Path) -> None:
    if path.exists() and not any(path.iterdir()):
        path.rmdir()


def _remove_empty_tree(path: Path) -> None:
    if not path.exists():
        return
    for directory, _directory_names, _file_names in os.walk(path, topdown=False):
        _remove_empty_directory(Path(directory))


def _restore_archived_directory(source: Path, destination: Path) -> None:
    if source.exists() and destination.exists():
        _fail(f"migration recovery found both archived and retired state: {destination}")
    if source.exists():
        source.rename(destination)


def _recover_migration(root: Path) -> None:
    journal_path = root / _JOURNAL_RELATIVE
    if not journal_path.exists():
        return
    journal = _load_journal(root)
    archived_worktrees = journal.archive_root / "worktrees"
    archived_target = journal.archive_root / "target"
    if journal.legacy_worktrees_existed:
        _restore_archived_directory(archived_worktrees, journal.legacy_worktrees)
    _restore_archived_directory(archived_target, journal.legacy_target)
    registrations = {worktree.path for worktree in _registered_worktrees(root)}
    for move in reversed(journal.moves):
        source = move.source.resolve()
        target = move.target.resolve()
        if source in registrations and target in registrations:
            _fail(f"migration recovery found duplicate worktree registrations: {source}")
        if target in registrations:
            source.parent.mkdir(parents=True, exist_ok=True)
            _git(root, "worktree", "move", str(target), str(source))
            registrations.remove(target)
            registrations.add(source)
        elif source not in registrations:
            _fail(f"migration recovery cannot locate registered worktree: {source}")
    staging = journal.runtime_target.parent / ".runtime-migration"
    for copied_runtime in (journal.runtime_target, staging):
        if copied_runtime.exists():
            if copied_runtime.is_symlink() or not copied_runtime.is_dir():
                _fail(f"migration recovery found unsafe copied runtime: {copied_runtime}")
            shutil.rmtree(copied_runtime)
    _remove_empty_directory(journal.archive_root)
    _remove_empty_tree(journal.preserved_worktree_target)
    _remove_empty_directory(journal.worktree_target)
    journal_path.unlink()


def _apply_delivery_state_migration(root: Path) -> DeliveryStateMigrationPlan:
    delivery_root = root / ".owlbear/delivery"
    with locked_roots((delivery_root,)):
        _recover_migration(root)
        plan = plan_delivery_state_migration(root)
        if plan.already_migrated:
            return plan
        staging = plan.runtime_target.parent / ".runtime-migration"
        if staging.exists():
            _fail(f"stale migration staging path requires inspection: {staging}")
        journal_path = _write_journal(plan)
        staging.mkdir(parents=True)
        try:
            _publish_migration(plan, staging)
            journal_path.unlink()
        except _MIGRATION_FAILURES:
            _recover_migration(plan.repository_root)
            raise
        return plan


def apply_delivery_state_migration(plan: DeliveryStateMigrationPlan) -> None:
    """Apply one validated migration while retaining exact retired roots."""
    _apply_delivery_state_migration(plan.repository_root)


def main() -> None:
    """Preview or apply the one-way Delivery state migration."""
    parser = argparse.ArgumentParser(prog="migrate-delivery-state")
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true", help="Apply the validated one-way migration")
    arguments = parser.parse_args()
    try:
        if arguments.apply:
            plan = _apply_delivery_state_migration(arguments.path.expanduser().resolve())
        else:
            plan = plan_delivery_state_migration(arguments.path)
    except DeliveryStateMigrationError as exc:
        parser.error(str(exc))
    disposition = "already migrated" if plan.already_migrated else "applied" if arguments.apply else "ready"
    print(f"Delivery state migration: {disposition}")  # noqa: T201
    if not plan.already_migrated:
        print(f"Changes: {', '.join(change.change_id for change in plan.changes)}")  # noqa: T201
        if plan.preserved_worktrees:
            names = ", ".join(str(worktree.path.name) for worktree in plan.preserved_worktrees)
            print(f"Preserved non-Delivery worktrees: {names}")  # noqa: T201
        print(f"Archive: {plan.archive_root}")  # noqa: T201
