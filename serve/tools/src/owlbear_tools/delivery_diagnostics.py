"""Bounded, read-only structural inspection of local Delivery records.

This module is deliberately a stdlib-only bootstrap.  It must remain usable when
the Delivery, MCP, Cockpit, and runtime packages cannot be imported.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_ENTRIES = 256
MAX_RECORD_BYTES = 1 << 20
MAX_TOTAL_BYTES = 8 << 20
MAX_LOG_BYTES = 64 << 10
_INCOMPLETE_DIAGNOSTIC_CODES = frozenset(
    {
        "ENTRY_LIMIT_EXCEEDED",
        "TOTAL_LIMIT_EXCEEDED",
        "OVERSIZED_RECORD",
        "LOG_TRUNCATED",
        "REPLACED_DURING_INSPECTION",
        "REPLACED_DURING_READ",
        "CHANGED_DURING_READ",
        "TRUNCATED_DURING_READ",
        "SYMLINK_REJECTED",
        "SPECIAL_FILE_REJECTED",
        "UNSAFE_ENTRY_NAME",
        "UNRECOGNIZED_CHANGE_ENTRY",
    }
)

SUPPORTED_VERSIONS = {
    "config": 2,
    "frontier": 18,
    "coordination": 1,
    "snapshot": 2,
    "host": 1,
    "host_local": 1,
}

_CHANGE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FIXED_ENTRY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_HOST_LOCK_NAME = re.compile(r"^[0-9a-f]{32}\.lock$")
_INVALID_CHANGE_ID = "invalid Change ID"
_INVALID_INVOCATION = "ERR_INVALID_INVOCATION"
_CHANGE_RECORD_NAME_PATTERNS = {
    "$digest": re.compile(r"^[0-9a-f]{64}$"),
    "$digest.json": re.compile(r"^[0-9a-f]{64}\.json$"),
    "$digest.raw": re.compile(r"^[0-9a-f]{64}\.raw$"),
    "$attempt.json": re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}\.json$"),
    "$claim_attempt.json": re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json$"),
    "$outcome": re.compile(r"^OUT-[0-9]{3}$"),
    "$operation": re.compile(r"^continue-[0-9a-f]{64}$"),
    "$stage": re.compile(r"^stage-[0-9a-f]{32}$"),
}
# Interrupted RuntimeTransaction/write_contained temporaries: `.tmp-<24 hex>[-<destination>]`.
_TRANSIENT_CHANGE_ENTRY = re.compile(r"^\.tmp-[0-9a-f]{24}(?:-[A-Za-z0-9][A-Za-z0-9._:-]{0,255})?$")
_REVISION_LAYOUT = {
    "contract.json": "revision_record",
    "frontier.json": "revision_record",
    "admission.json": "revision_record",
}
_RESTORATION_LAYOUT: dict[str, object] = {
    "$digest": {
        "intent.json": "restoration_record",
        "result.json": "restoration_record",
        "failure.json": "restoration_record",
        "paths": {
            "$digest": {
                "intent.json": "restoration_record",
                "result.json": "restoration_record",
                "staging.json": "restoration_record",
                "$stage": "restoration_stage",
            }
        },
    }
}
_CHANGE_RECORD_LAYOUT: dict[str, object] = {
    "contract.json": "contract",
    "admission.json": "admission",
    "state-publication.json": "state_publication",
    "revisions": {"$digest": _REVISION_LAYOUT},
    "result-receipts": {"$outcome": {"$digest.json": "result_receipt"}},
    "claim-issuers": {"$claim_attempt.json": "claim_issuer"},
    "action-receipts": {
        "$operation": {
            "intent.json": "action_intent",
            "started.json": "action_started",
            "result.json": "action_result",
        }
    },
    "invocations": {"$digest.json": "recovery_invocation"},
    "recovery-receipts": {
        "$digest": {
            "intent.json": "recovery_intent",
            "evidence.json": "recovery_evidence",
            "receipt.json": "recovery_receipt",
            "preservation": {
                "manifest.json": "preservation_manifest",
                "objects": {"$digest.raw": "preservation_object"},
                "restoration": _RESTORATION_LAYOUT,
            },
        }
    },
    "retry-ledger": {
        "current.json": "retry_ledger",
        "attempts": {"$attempt.json": "retry_attempt"},
        "outcomes": {"$digest.json": "retry_outcome"},
        "repair-bindings": {"$digest.json": "retry_repair_binding"},
        "owner-results": {"$attempt.json": "retry_owner_result"},
    },
    "planning-pause-receipts": {"$outcome": {"$digest.json": "planning_pause_receipt"}},
    "planning-retry-receipts": {"$outcome": {"$digest.json": "planning_retry_receipt"}},
    "builder-invocation-receipts": {"$digest.json": "builder_invocation_receipt"},
    "builder-plan-promotion-receipts": {"$digest.json": "builder_plan_promotion_receipt"},
    "builder-request-resolution-receipts": {"$digest.json": "builder_request_resolution_receipt"},
    "builder-handoff-change-intent-receipts": {
        "$digest": {
            "head.json": "builder_handoff_change_intent_head",
            "$digest.json": "builder_handoff_change_intent_receipt",
        }
    },
}
_CURRENT_CHANGE_RECORD_ENTRIES = frozenset(
    {
        "frontier.json",
        "transactions",
        "state-publication.json",
        "contract.json",
        "admission.json",
    }
)
# Supported schema versions per JSON kind; None marks owner models without a version field.
_CHANGE_RECORD_VERSIONS: dict[str, tuple[int, ...] | None] = {
    "contract": (2,),
    "admission": (1,),
    "state_publication": (1,),
    "result_receipt": None,
    "action_intent": None,
    "action_started": None,
    "action_result": None,
    "recovery_invocation": (1,),
    "recovery_intent": (1,),
    "recovery_evidence": (1,),
    "recovery_receipt": (1,),
    "preservation_manifest": (1,),
    "restoration_record": (1,),
    "retry_ledger": (1,),
    "retry_attempt": (1,),
    "retry_outcome": (1,),
    "retry_repair_binding": (1,),
    "retry_owner_result": (1,),
    "planning_pause_receipt": (1,),
    "planning_retry_receipt": (1,),
    "builder_invocation_receipt": (1,),
    "builder_plan_promotion_receipt": (1,),
    "builder_request_resolution_receipt": (1,),
    "builder_handoff_change_intent_head": (1,),
    "builder_handoff_change_intent_receipt": (1,),
    "claim_issuer": (1,),
}
_VERSIONLESS_REQUIRED_FIELDS: dict[str, dict[str, type]] = {
    "result_receipt": {"candidate_id": str, "claim_id": str, "digest": str, "result": dict},
    "action_intent": {"operation_id": str, "change_id": str, "kind": str},
    "action_started": {"operation_id": str, "change_id": str, "kind": str},
    "action_result": {"action": dict, "kind": str, "reason_code": str},
}
# Immutable history may retain any earlier owner schema; only its JSON-object shape is checked.
_HISTORICAL_CHANGE_KINDS = frozenset({"revision_record"})
# Opaque kinds are classified by no-follow lstat only: (pending evidence, symlink allowed).
_OPAQUE_CHANGE_KINDS = {
    "preservation_object": (False, False),
    "restoration_stage": (True, True),
    "change_transient": (True, False),
}
_CHANGE_ROOT = ".owlbear/delivery/runtime/changes/<redacted>"
_PRESERVATION_ROOT = f"{_CHANGE_ROOT}/recovery-receipts/<opaque>/preservation"
_SAFE_LOCATORS = {
    "config": ".owlbear/delivery/config.json",
    "host": ".owlbear/delivery/runtime/host.json",
    "host_local": ".owlbear/delivery/runtime/host.local.json",
    "frontier": ".owlbear/delivery/runtime/changes/<redacted>/frontier.json",
    "coordination": ".owlbear/delivery/runtime/coordination/changes/<redacted>.json",
    "snapshot": ".owlbear/delivery/state/<redacted>/snapshot.json",
    "transaction": ".owlbear/delivery/runtime/transactions/<opaque>.yaml",
    "transaction_legacy": ".owlbear/delivery/runtime/changes/<redacted>/transactions/<opaque>.yaml",
    "transaction_package": ".owlbear/delivery/packages/<redacted>/transactions/<opaque>.yaml",
    "transaction_package_root": ".owlbear/delivery/packages/transactions/<opaque>.yaml",
    "transaction_finalization": (
        ".owlbear/delivery/runtime/finalization-reports/<redacted>/transactions/<opaque>.yaml"
    ),
    "transaction_proof": ".owlbear/delivery/runtime/proof-attempts/<redacted>/transactions/<opaque>.yaml",
    "log": ".owlbear/delivery/runtime/logs/<opaque>",
    "contract": f"{_CHANGE_ROOT}/contract.json",
    "admission": f"{_CHANGE_ROOT}/admission.json",
    "state_publication": f"{_CHANGE_ROOT}/state-publication.json",
    "revision_record": f"{_CHANGE_ROOT}/revisions/<opaque>/<record>.json",
    "result_receipt": f"{_CHANGE_ROOT}/result-receipts/<outcome>/<opaque>.json",
    "action_intent": f"{_CHANGE_ROOT}/action-receipts/<opaque>/intent.json",
    "action_started": f"{_CHANGE_ROOT}/action-receipts/<opaque>/started.json",
    "action_result": f"{_CHANGE_ROOT}/action-receipts/<opaque>/result.json",
    "preservation_manifest": f"{_PRESERVATION_ROOT}/manifest.json",
    "preservation_object": f"{_PRESERVATION_ROOT}/objects/<opaque>.raw",
    "restoration_record": f"{_PRESERVATION_ROOT}/restoration/<opaque>/<record>.json",
    "restoration_stage": f"{_PRESERVATION_ROOT}/restoration/<opaque>/paths/<opaque>/<opaque>",
    "change_transient": f"{_CHANGE_ROOT}/<path>/<opaque>",
    "recovery_invocation": ".owlbear/delivery/runtime/changes/<redacted>/invocations/<opaque>.json",
    "recovery_intent": ".owlbear/delivery/runtime/changes/<redacted>/recovery-receipts/<opaque>/intent.json",
    "recovery_evidence": ".owlbear/delivery/runtime/changes/<redacted>/recovery-receipts/<opaque>/evidence.json",
    "recovery_receipt": ".owlbear/delivery/runtime/changes/<redacted>/recovery-receipts/<opaque>/receipt.json",
    "retry_ledger": ".owlbear/delivery/runtime/changes/<redacted>/retry-ledger/current.json",
    "claim_issuer": ".owlbear/delivery/runtime/changes/<redacted>/claim-issuers/<opaque>.json",
    "retry_attempt": ".owlbear/delivery/runtime/changes/<redacted>/retry-ledger/attempts/<opaque>.json",
    "retry_outcome": ".owlbear/delivery/runtime/changes/<redacted>/retry-ledger/outcomes/<opaque>.json",
    "retry_repair_binding": ".owlbear/delivery/runtime/changes/<redacted>/retry-ledger/repair-bindings/<opaque>.json",
    "retry_owner_result": ".owlbear/delivery/runtime/changes/<redacted>/retry-ledger/owner-results/<opaque>.json",
    "planning_pause_receipt": (
        ".owlbear/delivery/runtime/changes/<redacted>/planning-pause-receipts/<outcome>/<opaque>.json"
    ),
    "planning_retry_receipt": (
        ".owlbear/delivery/runtime/changes/<redacted>/planning-retry-receipts/<outcome>/<opaque>.json"
    ),
    "builder_invocation_receipt": (
        ".owlbear/delivery/runtime/changes/<redacted>/builder-invocation-receipts/<opaque>.json"
    ),
    "builder_plan_promotion_receipt": (
        ".owlbear/delivery/runtime/changes/<redacted>/builder-plan-promotion-receipts/<opaque>.json"
    ),
    "builder_request_resolution_receipt": (
        ".owlbear/delivery/runtime/changes/<redacted>/builder-request-resolution-receipts/<opaque>.json"
    ),
    "builder_handoff_change_intent_head": (
        ".owlbear/delivery/runtime/changes/<redacted>/builder-handoff-change-intent-receipts/<opaque>/head.json"
    ),
    "builder_handoff_change_intent_receipt": (
        ".owlbear/delivery/runtime/changes/<redacted>/builder-handoff-change-intent-receipts/<opaque>/<opaque>.json"
    ),
}

MAINTENANCE_PROMPT = """The offline inspection is structural evidence only. Review the bounded
diagnostic codes and the responsible Delivery owner before continuing the ordinary session.
Do not infer healthy execution, user confirmation, provenance, worker termination, approval,
or merge readiness from this report. Do not edit, delete, copy, unlock, recover, upgrade, or
repair the inspected files. Supported repair and upgrade writes are a D07 route; if that route
is unavailable, leave the state contained and request the responsible owner. Do not use Git,
network, provider, process, or manual filesystem repair commands."""
_ENTRY_LIMIT_MAINTENANCE_PROMPT = (
    "The 256-entry budget was exhausted, so this inspection is incomplete. Rerun the complete "
    "inspection one Change at a time with `delivery-diagnose inspect --project-root "
    "<PROJECT_ROOT> --change-id <CHANGE_ID>`, using the applicable project root and a valid "
    "Change ID. Do not manually edit any inspected file."
)


class _InvocationError(Exception):
    """A bounded command-line error that must not echo user input."""


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise _InvocationError


class _Inspection:
    def __init__(self, project_root: Path | None, change_id: str | None) -> None:
        self.project_root = project_root
        self.change_id = change_id
        self.total_bytes = 0
        self.records: list[dict[str, object]] = []
        self.diagnostics: list[str] = []
        self.counts = {
            "config": 0,
            "host": 0,
            "host_local": 0,
            "host_locks": 0,
            "frontier": 0,
            "change_records": 0,
            "coordination": 0,
            "snapshot": 0,
            "packages": 0,
            "pending_transactions": 0,
            "logs": 0,
        }
        self.selected_runtime_change_seen = False
        self.runtime_frontier_changes: set[str] = set()
        self.transaction_scan_unknown = False
        self.incomplete = False
        self.entries_seen = 0
        self.entry_budget_exhausted = False
        self.charged_entries: set[tuple[int, int, str]] = set()

    def diagnostic(self, code: str) -> None:
        if code not in self.diagnostics:
            self.diagnostics.append(code)

    def charge_entry(self, parent_fd: int, name: str) -> bool:
        if self.entry_budget_exhausted:
            return False
        parent = os.fstat(parent_fd)
        identity = (parent.st_dev, parent.st_ino, name)
        if identity in self.charged_entries:
            return True
        self.entries_seen += 1
        if self.entries_seen > MAX_ENTRIES:
            self.entry_budget_exhausted = True
            self.diagnostic("ENTRY_LIMIT_EXCEEDED")
            return False
        self.charged_entries.add(identity)
        return True

    def has_complete_inventory(self) -> bool:
        return not (
            self.incomplete
            or self.transaction_scan_unknown
            or any(
                code in _INCOMPLETE_DIAGNOSTIC_CODES
                or code.endswith(("_UNREADABLE", "_MISSING"))
                or code in {"ROOT_UNAVAILABLE", "DELIVERY_ROOT_UNAVAILABLE"}
                for code in self.diagnostics
            )
        )

    def record(
        self,
        kind: str,
        *,
        present: bool = True,
        size_bytes: int | None = None,
        schema: int | None = None,
        status: str = "observed",
    ) -> None:
        item: dict[str, object] = {
            "kind": kind,
            "locator": _SAFE_LOCATORS[kind],
            "present": present,
            "status": status,
        }
        if size_bytes is not None:
            item["size_bytes"] = size_bytes
        if schema is not None:
            item["schema_version"] = schema
        self.records.append(item)

    def result(self, *, status: str | None = None, complete: bool = True) -> dict[str, object]:
        if "ENTRY_LIMIT_EXCEEDED" in self.diagnostics:
            self.transaction_scan_unknown = True
        complete = complete and self.has_complete_inventory() and "CHANGE_NOT_FOUND" not in self.diagnostics
        if self.counts["pending_transactions"] and not self.transaction_scan_unknown:
            self.diagnostic("PENDING_TRANSACTIONS")
        if self.transaction_scan_unknown:
            self.diagnostic("PENDING_EFFECTS_UNKNOWN")
        truncated = any(code in _INCOMPLETE_DIAGNOSTIC_CODES for code in self.diagnostics)
        if status is None:
            status = (
                "unsupported"
                if any(code.endswith("_UNSUPPORTED") for code in self.diagnostics)
                else ("degraded" if self.diagnostics else "healthy-structure")
            )
        if status == "healthy-structure" and not complete:
            status = "degraded"
        maintenance_prompt = MAINTENANCE_PROMPT
        if "ENTRY_LIMIT_EXCEEDED" in self.diagnostics:
            maintenance_prompt += "\n\n" + _ENTRY_LIMIT_MAINTENANCE_PROMPT
        return {
            "diagnostic_schema_version": 1,
            "status": status,
            "inspection_complete": complete,
            "change_scope": "selected" if self.change_id is not None else "all",
            "truncated": truncated,
            "versions": {
                **SUPPORTED_VERSIONS,
                "python": {
                    "major": sys.version_info.major,
                    "minor": sys.version_info.minor,
                    "micro": sys.version_info.micro,
                },
                "executable": {"name": Path(sys.executable).name, "version": "unknown"},
                "owlbear_tools": "unknown",
            },
            "counts": dict(self.counts),
            "bytes_inspected": self.total_bytes,
            "diagnostic_codes": sorted(self.diagnostics),
            "pending_effects": "unknown" if self.transaction_scan_unknown else self.counts["pending_transactions"] > 0,
            "writes_performed": False,
            "records": self.records,
            "maintenance_prompt": maintenance_prompt,
        }


@dataclass
class _ChangeInventory:
    directory_fd: int
    directory_opened: os.stat_result
    change_ids: list[str]


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _same_file_state(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        _same_identity(left, right)
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
        and left.st_ctime_ns == right.st_ctime_ns
    )


def _absolute_without_following(path: Path) -> Path:
    candidate = path if path.is_absolute() else Path.cwd() / path
    return Path(os.path.normpath(os.fspath(candidate)))


def _has_project_marker(root_fd: int) -> bool:
    try:
        owlbear_fd = os.open(".owlbear", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        try:
            return True
        finally:
            os.close(owlbear_fd)
    except OSError:
        return False


def _discover_project_root(start: Path) -> Path:
    """Find the nearest fixed-marker project without scanning arbitrary ancestors."""
    for candidate in (start, *start.parents):
        opened = _open_root(candidate)
        if opened is None:
            continue
        root_fd, descriptors = opened
        try:
            if _has_project_marker(root_fd):
                return candidate
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)
    return start


def _lexical_root_is_safe(path: Path) -> bool:
    for ancestor in reversed((path, *path.parents)):
        try:
            info = os.lstat(ancestor)
        except OSError:
            return False
        if stat.S_ISLNK(info.st_mode):
            return False
    return True


def _root_descriptors_are_stable(path: Path, descriptors: list[int]) -> bool:
    for index in range(1, len(descriptors)):
        current = os.stat(path.parts[index], dir_fd=descriptors[index - 1], follow_symlinks=False)
        if not _same_identity(current, os.fstat(descriptors[index])):
            return False
    return True


def _traverse_root(path: Path) -> tuple[int, tuple[int, ...]] | None:
    descriptors: list[int] = []
    succeeded = False
    try:
        current_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(current_fd)
        for component in path.parts[1:]:
            before = os.stat(component, dir_fd=current_fd, follow_symlinks=False)
            if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
                return None
            child_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=current_fd,
            )
            descriptors.append(child_fd)
            opened = os.fstat(child_fd)
            after = os.stat(component, dir_fd=current_fd, follow_symlinks=False)
            if not _same_identity(before, opened) or not _same_identity(opened, after):
                return None
            current_fd = child_fd
        if not _root_descriptors_are_stable(path, descriptors):
            return None
    except OSError:
        return None
    else:
        succeeded = True
        return current_fd, tuple(descriptors)
    finally:
        if not succeeded:
            for descriptor in reversed(descriptors):
                os.close(descriptor)


def _open_root(path: Path) -> tuple[int, tuple[int, ...]] | None:
    """Descriptor-traverse a directory with no-follow checks on every ancestor."""
    if not _lexical_root_is_safe(path):
        return None
    return _traverse_root(path)


def _open_directory(
    parent_fd: int,
    name: str,
    inspection: _Inspection,
    code_prefix: str,
    *,
    required: bool = False,
) -> tuple[int, os.stat_result] | None:
    try:
        before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        if required or exc.errno != errno.ENOENT:
            inspection.diagnostic(f"{code_prefix}_UNREADABLE")
        return None
    if stat.S_ISLNK(before.st_mode):
        inspection.diagnostic("SYMLINK_REJECTED")
        return None
    if not stat.S_ISDIR(before.st_mode):
        inspection.diagnostic("SPECIAL_FILE_REJECTED")
        return None
    fd: int | None = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        opened = os.fstat(fd)
        if not _same_identity(before, opened):
            os.close(fd)
            fd = None
            inspection.diagnostic("REPLACED_DURING_INSPECTION")
            return None
    except OSError as exc:
        if fd is not None:
            os.close(fd)
        inspection.diagnostic("SYMLINK_REJECTED" if exc.errno == errno.ELOOP else f"{code_prefix}_UNREADABLE")
        return None
    else:
        return fd, opened


def _close_directory(
    parent_fd: int,
    name: str,
    fd: int,
    opened: os.stat_result,
    inspection: _Inspection,
) -> None:
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not _same_identity(current, opened):
            inspection.diagnostic("REPLACED_DURING_INSPECTION")
            inspection.transaction_scan_unknown = True
    except OSError:
        inspection.diagnostic("DIRECTORY_UNREADABLE")
        inspection.transaction_scan_unknown = True
    finally:
        os.close(fd)


def _directory_names(fd: int, inspection: _Inspection) -> list[str]:
    if inspection.entry_budget_exhausted:
        return []
    names: list[str] = []
    try:
        with os.scandir(fd) as entries:
            for entry in entries:
                if not inspection.charge_entry(fd, entry.name):
                    break
                names.append(entry.name)
    except OSError:
        inspection.diagnostic("DIRECTORY_UNREADABLE")
        inspection.transaction_scan_unknown = True
    return names


def _safe_read(  # noqa: C901, PLR0911, PLR0912, PLR0913, PLR0915
    parent_fd: int,
    name: str,
    inspection: _Inspection,
    kind: str,
    *,
    required: bool = False,
    limit: int = MAX_RECORD_BYTES,
) -> tuple[bytes | None, int | None]:
    """Read one regular file and verify its descriptor/path identity."""
    if inspection.entry_budget_exhausted:
        return None, None
    try:
        before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        if required and exc.errno == errno.ENOENT:
            inspection.diagnostic(f"{kind.upper()}_MISSING")
        elif exc.errno != errno.ENOENT or required:
            inspection.diagnostic(f"{kind.upper()}_UNREADABLE")
        return None, None
    if not inspection.charge_entry(parent_fd, name):
        return None, None
    if stat.S_ISLNK(before.st_mode):
        inspection.diagnostic("SYMLINK_REJECTED")
        return None, None
    if not stat.S_ISREG(before.st_mode):
        inspection.diagnostic("SPECIAL_FILE_REJECTED")
        return None, None
    size = int(before.st_size)
    inspection.record(kind, size_bytes=size, status="observed")
    if size > limit:
        inspection.diagnostic("OVERSIZED_RECORD")
        return None, size
    if size > MAX_TOTAL_BYTES - inspection.total_bytes:
        inspection.diagnostic("TOTAL_LIMIT_EXCEEDED")
        return None, size
    consumed = 0
    charged = False
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
    except OSError as exc:
        inspection.diagnostic("SYMLINK_REJECTED" if exc.errno == errno.ELOOP else f"{kind.upper()}_UNREADABLE")
        return None, size
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or not _same_identity(before, opened):
            inspection.diagnostic("REPLACED_DURING_READ")
            return None, size
        remaining = min(limit, MAX_TOTAL_BYTES - inspection.total_bytes)
        chunks: list[bytes] = []
        while consumed < remaining:
            chunk = os.read(fd, min(65_536, remaining - consumed))
            if not chunk:
                break
            chunks.append(chunk)
            consumed += len(chunk)
        after_fd = os.fstat(fd)
        inspection.total_bytes += consumed
        charged = True
        try:
            after_path = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError:
            inspection.diagnostic("REPLACED_DURING_READ")
            return None, size
        if not _same_file_state(opened, after_fd) or not _same_file_state(before, after_path):
            inspection.diagnostic("REPLACED_DURING_READ")
            return None, size
        if int(after_fd.st_size) != size or int(after_path.st_size) != size:
            inspection.diagnostic("TRUNCATED_DURING_READ" if after_fd.st_size < size else "CHANGED_DURING_READ")
            return None, size
        return b"".join(chunks), size
    except OSError:
        if not charged:
            inspection.total_bytes += consumed
        inspection.diagnostic(f"{kind.upper()}_UNREADABLE")
        return None, size
    finally:
        os.close(fd)


def _json_shape(
    content: bytes,
    *,
    kind: str,
    expected_schema: int,
    inspection: _Inspection,
    expected_change_id: str | None = None,
) -> None:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, RecursionError, ValueError):
        inspection.diagnostic(f"{kind.upper()}_MALFORMED")
        inspection.records[-1]["status"] = "malformed"
        return
    if not isinstance(value, dict):
        inspection.diagnostic(f"{kind.upper()}_MALFORMED")
        inspection.records[-1]["status"] = "malformed"
        return
    schema = value.get("schema_version", expected_schema if kind == "host_local" else None)
    if isinstance(schema, bool) or not isinstance(schema, int) or schema != expected_schema:
        inspection.diagnostic(f"{kind.upper()}_UNSUPPORTED")
        inspection.records[-1]["status"] = "unsupported"
        return
    if kind == "config":
        if any(
            not isinstance(value.get(field), str) or not value[field]
            for field in ("remote", "target_branch", "github_repository")
        ):
            inspection.diagnostic("CONFIG_MALFORMED")
            inspection.records[-1]["status"] = "malformed"
        else:
            inspection.records[-1]["schema_version"] = expected_schema
            inspection.records[-1]["status"] = "supported"
    elif kind == "frontier" and not isinstance(value.get("bindings"), list):
        inspection.diagnostic("FRONTIER_MALFORMED")
        inspection.records[-1]["status"] = "malformed"
    elif kind == "coordination" and (
        not isinstance(value.get("change_id"), str)
        or not value["change_id"]
        or (expected_change_id is not None and value["change_id"] != expected_change_id)
    ):
        inspection.diagnostic("COORDINATION_MALFORMED")
        inspection.records[-1]["status"] = "malformed"
    elif kind == "snapshot" and not isinstance(value.get("frontier"), dict):
        inspection.diagnostic("SNAPSHOT_MALFORMED")
        inspection.records[-1]["status"] = "malformed"
    elif kind in {"host", "host_local"} and (
        set(value) - {"schema_version", "execution_capacity", "claim_timeout_seconds"}
        or any(
            field in value
            and not (kind == "host_local" and value[field] is None)
            and (not isinstance(value[field], int) or isinstance(value[field], bool) or value[field] <= 0)
            for field in ("execution_capacity", "claim_timeout_seconds")
        )
    ):
        inspection.diagnostic(f"{kind.upper()}_MALFORMED")
        inspection.records[-1]["status"] = "malformed"
    else:
        inspection.records[-1]["schema_version"] = expected_schema
        inspection.records[-1]["status"] = "supported"


def _inspect_file(
    parent_fd: int,
    name: str,
    inspection: _Inspection,
    kind: str,
    *,
    required: bool = False,
) -> None:
    content, _ = _safe_read(parent_fd, name, inspection, kind, required=required)
    if content is not None:
        _json_shape(content, kind=kind, expected_schema=SUPPORTED_VERSIONS[kind], inspection=inspection)
        inspection.counts[kind] += 1
    elif kind == "frontier":
        inspection.incomplete = True


def _unrecognized_change_entry(inspection: _Inspection) -> None:
    inspection.diagnostic("UNRECOGNIZED_CHANGE_ENTRY")
    inspection.incomplete = True
    inspection.transaction_scan_unknown = True


def _change_record_child(layout: dict[str, object], name: str) -> object | None:
    for pattern, child in layout.items():
        matcher = _CHANGE_RECORD_NAME_PATTERNS.get(pattern)
        if pattern == name or (matcher is not None and matcher.fullmatch(name)):
            return child
    return None


def _change_record_sort_key(layout: dict[str, object], name: str) -> tuple[int, str]:
    for index, pattern in enumerate(layout):
        matcher = _CHANGE_RECORD_NAME_PATTERNS.get(pattern)
        if pattern == name or (matcher is not None and matcher.fullmatch(name)):
            return index, name
    return len(layout), name


def _change_record_shape(content: bytes, kind: str, inspection: _Inspection) -> None:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, RecursionError, ValueError):
        value = None
    if not isinstance(value, dict):
        inspection.diagnostic(f"{kind.upper()}_MALFORMED")
        inspection.records[-1]["status"] = "malformed"
        return
    if kind in _HISTORICAL_CHANGE_KINDS:
        inspection.records[-1]["status"] = "supported"
        return
    versions = _CHANGE_RECORD_VERSIONS[kind]
    schema = value.get("schema_version")
    if versions is None:
        if "schema_version" in value:
            inspection.diagnostic(f"{kind.upper()}_UNSUPPORTED")
            inspection.records[-1]["status"] = "unsupported"
        elif any(
            not isinstance(value.get(field), expected)
            for field, expected in _VERSIONLESS_REQUIRED_FIELDS.get(kind, {}).items()
        ):
            inspection.diagnostic(f"{kind.upper()}_MALFORMED")
            inspection.records[-1]["status"] = "malformed"
        else:
            inspection.records[-1]["status"] = "supported"
    elif isinstance(schema, bool) or not isinstance(schema, int) or schema not in versions:
        inspection.diagnostic(f"{kind.upper()}_UNSUPPORTED")
        inspection.records[-1]["status"] = "unsupported"
    else:
        inspection.records[-1]["schema_version"] = schema
        inspection.records[-1]["status"] = "supported"


def _inspect_change_record_file(parent_fd: int, name: str, kind: str, inspection: _Inspection) -> None:
    content, _ = _safe_read(parent_fd, name, inspection, kind, required=True)
    if content is None:
        inspection.transaction_scan_unknown = True
        return
    _change_record_shape(content, kind, inspection)
    inspection.counts["change_records"] += 1
    if inspection.records[-1]["status"] != "supported":
        inspection.transaction_scan_unknown = True


def _inspect_optional_change_record_file(parent_fd: int, name: str, kind: str, inspection: _Inspection) -> None:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            inspection.diagnostic(f"{kind.upper()}_UNREADABLE")
            inspection.transaction_scan_unknown = True
        return
    _inspect_change_record_file(parent_fd, name, kind, inspection)


def _inspect_opaque_change_entry(parent_fd: int, name: str, kind: str, inspection: _Inspection) -> None:
    """Classify an owner payload or interrupted temporary without opening or following it."""
    pending, symlink_allowed = _OPAQUE_CHANGE_KINDS[kind]
    try:
        info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError:
        inspection.diagnostic("CHANGE_RECORD_UNREADABLE")
        inspection.transaction_scan_unknown = True
        return
    if stat.S_ISLNK(info.st_mode) and not symlink_allowed:
        inspection.diagnostic("SYMLINK_REJECTED")
        inspection.transaction_scan_unknown = True
        return
    if not stat.S_ISLNK(info.st_mode) and not stat.S_ISREG(info.st_mode):
        inspection.diagnostic("SPECIAL_FILE_REJECTED")
        inspection.transaction_scan_unknown = True
        return
    inspection.record(kind, size_bytes=int(info.st_size), status="pending-opaque" if pending else "observed-opaque")
    inspection.counts["pending_transactions" if pending else "change_records"] += 1


def _scan_change_record_names(
    parent_fd: int,
    names: list[str],
    layout: dict[str, object],
    inspection: _Inspection,
    *,
    skip_retry_ledger_current: bool = False,
) -> None:
    for name in sorted(names, key=lambda entry: _change_record_sort_key(layout, entry)):
        if skip_retry_ledger_current and name == "current.json":
            continue
        child = "change_transient" if _TRANSIENT_CHANGE_ENTRY.fullmatch(name) else _change_record_child(layout, name)
        if isinstance(child, dict):
            opened = _open_directory(parent_fd, name, inspection, "CHANGE_RECORD", required=True)
            if opened is None:
                inspection.transaction_scan_unknown = True
                continue
            child_fd, child_opened = opened
            try:
                _scan_change_record_names(
                    child_fd,
                    _directory_names(child_fd, inspection),
                    child,
                    inspection,
                    skip_retry_ledger_current=name == "retry-ledger",
                )
            finally:
                _close_directory(parent_fd, name, child_fd, child_opened, inspection)
        elif isinstance(child, str) and child in _OPAQUE_CHANGE_KINDS:
            _inspect_opaque_change_entry(parent_fd, name, child, inspection)
        elif isinstance(child, str):
            _inspect_change_record_file(parent_fd, name, child, inspection)
        else:
            _unrecognized_change_entry(inspection)


def _inspect_coordination_file(
    parent_fd: int,
    name: str,
    inspection: _Inspection,
    expected_change_id: str,
    *,
    required: bool = True,
) -> bool:
    content, _ = _safe_read(parent_fd, name, inspection, "coordination", required=required)
    if content is None:
        return False
    _json_shape(
        content,
        kind="coordination",
        expected_schema=SUPPORTED_VERSIONS["coordination"],
        inspection=inspection,
        expected_change_id=expected_change_id,
    )
    inspection.counts["coordination"] += 1
    return inspection.records[-1]["status"] == "supported"


def _scan_change_transactions(change_fd: int, inspection: _Inspection) -> None:
    transaction = _open_optional_transactions(change_fd, inspection)
    if transaction is None:
        return
    transactions_fd, transactions_opened = transaction
    try:
        _scan_transaction_entries(
            transactions_fd,
            inspection,
            kind="transaction_legacy",
            strict_change=True,
        )
    finally:
        _close_directory(change_fd, "transactions", transactions_fd, transactions_opened, inspection)


def _scan_change_records(
    runtime_fd: int,
    inspection: _Inspection,
    *,
    selected: str | None,
) -> _ChangeInventory | None:
    changes = _open_optional_pending_directory(runtime_fd, "changes", inspection, "CHANGES")
    if changes is None:
        return None
    changes_fd, changes_opened = changes
    names = [selected] if selected is not None else _directory_names(changes_fd, inspection)
    change_ids: list[str] = []
    for name in names:
        if inspection.entry_budget_exhausted:
            break
        if not _CHANGE_ID.fullmatch(name):
            inspection.diagnostic("UNSAFE_ENTRY_NAME")
            inspection.transaction_scan_unknown = True
            continue
        if selected is not None:
            try:
                os.stat(name, dir_fd=changes_fd, follow_symlinks=False)
            except OSError as exc:
                if exc.errno != errno.ENOENT:
                    inspection.diagnostic("CHANGE_UNREADABLE")
                    inspection.transaction_scan_unknown = True
                continue
        child = _open_directory(
            changes_fd,
            name,
            inspection,
            "CHANGE",
            required=selected is not None,
        )
        if child is None:
            inspection.transaction_scan_unknown = True
            continue
        inspection.selected_runtime_change_seen = True
        change_ids.append(name)
        child_fd, child_opened = child
        try:
            frontier_record = len(inspection.records)
            _inspect_file(child_fd, "frontier.json", inspection, "frontier", required=True)
            if len(inspection.records) > frontier_record and inspection.records[-1]["status"] == "supported":
                inspection.runtime_frontier_changes.add(name)
        finally:
            _close_directory(changes_fd, name, child_fd, child_opened, inspection)
    return _ChangeInventory(changes_fd, changes_opened, change_ids)


def _open_change_scope(
    inventory: _ChangeInventory,
    change_id: str,
    inspection: _Inspection,
) -> tuple[int, os.stat_result] | None:
    opened = _open_directory(inventory.directory_fd, change_id, inspection, "CHANGE", required=True)
    if opened is None:
        inspection.transaction_scan_unknown = True
    return opened


def _scan_change_current_records(inventory: _ChangeInventory, inspection: _Inspection) -> None:
    for change_id in inventory.change_ids:
        if inspection.entry_budget_exhausted:
            break
        change = _open_change_scope(inventory, change_id, inspection)
        if change is None:
            continue
        change_fd, change_opened = change
        try:
            retry_ledger = _open_optional_pending_directory(change_fd, "retry-ledger", inspection, "CHANGE_RECORD")
            if retry_ledger is not None:
                ledger_fd, ledger_opened = retry_ledger
                try:
                    _inspect_optional_change_record_file(ledger_fd, "current.json", "retry_ledger", inspection)
                finally:
                    _close_directory(change_fd, "retry-ledger", ledger_fd, ledger_opened, inspection)
            for name, kind in (
                ("state-publication.json", "state_publication"),
                ("contract.json", "contract"),
                ("admission.json", "admission"),
            ):
                if inspection.entry_budget_exhausted:
                    break
                _inspect_optional_change_record_file(change_fd, name, kind, inspection)
        finally:
            _close_directory(inventory.directory_fd, change_id, change_fd, change_opened, inspection)


def _scan_change_pending_transactions(inventory: _ChangeInventory, inspection: _Inspection) -> None:
    for change_id in inventory.change_ids:
        change = _open_change_scope(inventory, change_id, inspection)
        if change is None:
            continue
        change_fd, change_opened = change
        try:
            _scan_change_transactions(change_fd, inspection)
        finally:
            _close_directory(inventory.directory_fd, change_id, change_fd, change_opened, inspection)


def _scan_change_receipts(inventory: _ChangeInventory, inspection: _Inspection) -> None:
    for change_id in inventory.change_ids:
        change = _open_change_scope(inventory, change_id, inspection)
        if change is None:
            continue
        change_fd, change_opened = change
        try:
            names = _directory_names(change_fd, inspection)
            _scan_change_record_names(
                change_fd,
                [name for name in names if name not in _CURRENT_CHANGE_RECORD_ENTRIES],
                _CHANGE_RECORD_LAYOUT,
                inspection,
            )
        finally:
            _close_directory(inventory.directory_fd, change_id, change_fd, change_opened, inspection)


def _scan_selected_coordination(
    changes_fd: int,
    inspection: _Inspection,
    selected: str,
    expected_changes: set[str],
) -> None:
    name = f"{selected}.json"
    try:
        os.stat(name, dir_fd=changes_fd, follow_symlinks=False)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            if selected in expected_changes:
                _record_missing_coordination(inspection, {selected})
        else:
            inspection.diagnostic("COORDINATION_UNREADABLE")
            inspection.transaction_scan_unknown = True
        return
    if not _inspect_coordination_file(changes_fd, name, inspection, selected):
        inspection.transaction_scan_unknown = True


def _scan_coordination(runtime_fd: int, inspection: _Inspection, *, selected: str | None) -> None:
    expected_changes = inspection.runtime_frontier_changes
    if selected is not None:
        expected_changes = expected_changes & {selected}
    coordination = _open_directory(runtime_fd, "coordination", inspection, "COORDINATION")
    if coordination is None:
        _record_missing_coordination_if_absent(runtime_fd, "coordination", inspection, expected_changes)
        return
    coordination_fd, coordination_opened = coordination
    try:
        changes = _open_directory(coordination_fd, "changes", inspection, "COORDINATION_CHANGES")
        if changes is None:
            _record_missing_coordination_if_absent(coordination_fd, "changes", inspection, expected_changes)
            return
        changes_fd, changes_opened = changes
        try:
            if selected is not None:
                _scan_selected_coordination(changes_fd, inspection, selected, expected_changes)
                return
            names = _directory_names(changes_fd, inspection)
            coordination_changes: set[str] = set()
            unresolved_changes: set[str] = set()
            for name in names:
                if not name.endswith(".json") or not _CHANGE_ID.fullmatch(name[:-5]):
                    inspection.diagnostic("UNSAFE_ENTRY_NAME")
                    inspection.transaction_scan_unknown = True
                    continue
                change_id = name[:-5]
                if selected is not None and change_id != selected:
                    continue
                if _inspect_coordination_file(changes_fd, name, inspection, change_id):
                    coordination_changes.add(change_id)
                else:
                    unresolved_changes.add(change_id)
                    inspection.transaction_scan_unknown = True
            listing_errors = {"DIRECTORY_UNREADABLE", "ENTRY_LIMIT_EXCEEDED"} & set(inspection.diagnostics)
            if not inspection.entry_budget_exhausted and not listing_errors:
                _record_missing_coordination(inspection, expected_changes - coordination_changes - unresolved_changes)
        finally:
            _close_directory(coordination_fd, "changes", changes_fd, changes_opened, inspection)
    finally:
        _close_directory(runtime_fd, "coordination", coordination_fd, coordination_opened, inspection)


def _record_missing_coordination_if_absent(
    parent_fd: int, name: str, inspection: _Inspection, expected_changes: set[str]
) -> None:
    if not expected_changes:
        return
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            _record_missing_coordination(inspection, expected_changes)
            return
    inspection.transaction_scan_unknown = True


def _record_missing_coordination(inspection: _Inspection, missing_changes: set[str]) -> None:
    if not missing_changes:
        return
    for _change in missing_changes:
        inspection.record("coordination", present=False, status="missing")
    inspection.diagnostic("COORDINATION_MISSING")
    inspection.transaction_scan_unknown = True


def _scan_snapshots(delivery_fd: int, inspection: _Inspection, *, selected: str | None) -> None:
    state = _open_directory(delivery_fd, "state", inspection, "STATE")
    if state is None:
        return
    state_fd, state_opened = state
    try:
        if selected is not None:
            child = _open_directory(state_fd, selected, inspection, "SNAPSHOT")
            if child is not None:
                child_fd, child_opened = child
                try:
                    _inspect_file(child_fd, "snapshot.json", inspection, "snapshot")
                finally:
                    _close_directory(state_fd, selected, child_fd, child_opened, inspection)
            return
        for name in _directory_names(state_fd, inspection):
            if not _CHANGE_ID.fullmatch(name):
                inspection.diagnostic("UNSAFE_ENTRY_NAME")
                inspection.transaction_scan_unknown = True
                continue
            if selected is not None and name != selected:
                continue
            child = _open_directory(state_fd, name, inspection, "SNAPSHOT")
            if child is None:
                inspection.transaction_scan_unknown = True
                continue
            child_fd, child_opened = child
            try:
                _inspect_file(child_fd, "snapshot.json", inspection, "snapshot")
            finally:
                _close_directory(state_fd, name, child_fd, child_opened, inspection)
    finally:
        _close_directory(delivery_fd, "state", state_fd, state_opened, inspection)


def _verify_opaque_transaction(
    transactions_fd: int,
    name: str,
    info: os.stat_result,
    inspection: _Inspection,
) -> bool:
    transaction_fd: int | None = None
    try:
        transaction_fd = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=transactions_fd,
        )
        opened = os.fstat(transaction_fd)
        after_path = os.stat(name, dir_fd=transactions_fd, follow_symlinks=False)
        if not _same_file_state(info, opened) or not _same_file_state(info, after_path):
            inspection.diagnostic("REPLACED_DURING_READ")
            inspection.transaction_scan_unknown = True
            return False
    except OSError:
        inspection.diagnostic("TRANSACTION_UNREADABLE")
        inspection.transaction_scan_unknown = True
        return False
    finally:
        if transaction_fd is not None:
            os.close(transaction_fd)
    return True


def _scan_opaque_transaction_entry(
    transactions_fd: int,
    name: str,
    inspection: _Inspection,
    kind: str,
) -> None:
    try:
        info = os.stat(name, dir_fd=transactions_fd, follow_symlinks=False)
    except OSError:
        inspection.diagnostic("TRANSACTION_UNREADABLE")
        inspection.transaction_scan_unknown = True
        return
    inspection.record(kind, size_bytes=int(info.st_size), status="pending-opaque")
    if stat.S_ISLNK(info.st_mode):
        inspection.diagnostic("SYMLINK_REJECTED")
        inspection.transaction_scan_unknown = True
        return
    if not stat.S_ISREG(info.st_mode):
        inspection.diagnostic("SPECIAL_FILE_REJECTED")
        inspection.transaction_scan_unknown = True
        return
    if not _verify_opaque_transaction(transactions_fd, name, info, inspection):
        return
    inspection.counts["pending_transactions"] += 1
    if info.st_size > MAX_RECORD_BYTES:
        inspection.diagnostic("OVERSIZED_RECORD")
    elif info.st_size > MAX_TOTAL_BYTES - inspection.total_bytes:
        inspection.diagnostic("TOTAL_LIMIT_EXCEEDED")
    else:
        inspection.total_bytes += int(info.st_size)


def _scan_transaction_entries(
    transactions_fd: int,
    inspection: _Inspection,
    *,
    kind: str = "transaction",
    strict_change: bool = False,
) -> None:
    """Inspect only opaque YAML entries in one fixed transaction directory."""
    names = _directory_names(transactions_fd, inspection)
    if inspection.entry_budget_exhausted:
        inspection.transaction_scan_unknown = True
    for name in names:
        if not name.endswith(".yaml"):
            if strict_change:
                _unrecognized_change_entry(inspection)
            continue
        _scan_opaque_transaction_entry(transactions_fd, name, inspection, kind)


def _open_optional_transactions(parent_fd: int, inspection: _Inspection) -> tuple[int, os.stat_result] | None:
    """Open a known transactions child while distinguishing absence from unreadability."""
    try:
        os.stat("transactions", dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            return None
        inspection.diagnostic("TRANSACTIONS_UNREADABLE")
        inspection.transaction_scan_unknown = True
        return None
    opened = _open_directory(parent_fd, "transactions", inspection, "TRANSACTIONS")
    if opened is None:
        inspection.transaction_scan_unknown = True
        return None
    return opened


def _open_optional_pending_directory(
    parent_fd: int,
    name: str,
    inspection: _Inspection,
    code_prefix: str,
) -> tuple[int, os.stat_result] | None:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            return None
        inspection.diagnostic(f"{code_prefix}_UNREADABLE")
        inspection.transaction_scan_unknown = True
        return None
    opened = _open_directory(parent_fd, name, inspection, code_prefix)
    if opened is None:
        inspection.transaction_scan_unknown = True
    return opened


def _scan_transactions(runtime_fd: int, inspection: _Inspection) -> None:
    transactions = _open_optional_transactions(runtime_fd, inspection)
    if transactions is None:
        return
    transactions_fd, transactions_opened = transactions
    try:
        _scan_transaction_entries(transactions_fd, inspection)
    finally:
        _close_directory(runtime_fd, "transactions", transactions_fd, transactions_opened, inspection)


def _scan_nested_transaction_families(runtime_fd: int, inspection: _Inspection) -> None:
    """Inspect known nested transaction families without traversing arbitrary runtime data."""
    for family_name in ("finalization-reports", "proof-attempts"):
        family = _open_optional_pending_directory(runtime_fd, family_name, inspection, family_name.upper())
        if family is None:
            continue
        family_fd, family_opened = family
        try:
            for name in _directory_names(family_fd, inspection):
                if not _FIXED_ENTRY_ID.fullmatch(name):
                    inspection.diagnostic("UNSAFE_ENTRY_NAME")
                    inspection.transaction_scan_unknown = True
                    continue
                entry = _open_directory(family_fd, name, inspection, "TRANSACTION_OWNER")
                if entry is None:
                    inspection.transaction_scan_unknown = True
                    continue
                entry_fd, entry_opened = entry
                try:
                    transactions = _open_optional_transactions(entry_fd, inspection)
                    if transactions is not None:
                        transactions_fd, transactions_opened = transactions
                        try:
                            _scan_transaction_entries(
                                transactions_fd,
                                inspection,
                                kind=(
                                    "transaction_finalization"
                                    if family_name == "finalization-reports"
                                    else "transaction_proof"
                                ),
                            )
                        finally:
                            _close_directory(
                                entry_fd,
                                "transactions",
                                transactions_fd,
                                transactions_opened,
                                inspection,
                            )
                finally:
                    _close_directory(family_fd, name, entry_fd, entry_opened, inspection)
        finally:
            _close_directory(runtime_fd, family_name, family_fd, family_opened, inspection)


def _scan_package_root_transactions(packages_fd: int, inspection: _Inspection) -> None:
    transactions = _open_optional_transactions(packages_fd, inspection)
    if transactions is None:
        return
    transactions_fd, transactions_opened = transactions
    try:
        _scan_transaction_entries(transactions_fd, inspection, kind="transaction_package_root")
    finally:
        _close_directory(packages_fd, "transactions", transactions_fd, transactions_opened, inspection)


def _inspect_package_storage_lock(packages_fd: int, inspection: _Inspection) -> None:
    try:
        info = os.stat(".storage.lock", dir_fd=packages_fd, follow_symlinks=False)
    except OSError:
        inspection.diagnostic("PACKAGES_UNREADABLE")
        inspection.transaction_scan_unknown = True
        return
    if stat.S_ISREG(info.st_mode):
        return
    if stat.S_ISLNK(info.st_mode):
        inspection.diagnostic("SYMLINK_REJECTED")
    else:
        inspection.diagnostic("SPECIAL_FILE_REJECTED")
    inspection.transaction_scan_unknown = True


def _package_change_names(
    packages_fd: int,
    inspection: _Inspection,
    *,
    selected: str | None,
) -> list[str]:
    if selected is not None:
        try:
            os.stat(".storage.lock", dir_fd=packages_fd, follow_symlinks=False)
        except OSError as exc:
            if exc.errno != errno.ENOENT:
                inspection.diagnostic("PACKAGES_UNREADABLE")
                inspection.transaction_scan_unknown = True
        else:
            _inspect_package_storage_lock(packages_fd, inspection)
        return [selected]
    names = _directory_names(packages_fd, inspection)
    if ".storage.lock" in names:
        _inspect_package_storage_lock(packages_fd, inspection)
    return [name for name in names if name not in {"transactions", ".storage.lock"}]


def _scan_package_change(
    packages_fd: int,
    name: str,
    inspection: _Inspection,
    *,
    required: bool,
) -> None:
    if not _CHANGE_ID.fullmatch(name):
        inspection.diagnostic("UNSAFE_ENTRY_NAME")
        inspection.transaction_scan_unknown = True
        return
    try:
        info = os.stat(name, dir_fd=packages_fd, follow_symlinks=False)
    except OSError as exc:
        if not required and exc.errno == errno.ENOENT:
            return
        inspection.diagnostic("PACKAGES_UNREADABLE")
        inspection.transaction_scan_unknown = True
        return
    if stat.S_ISLNK(info.st_mode):
        inspection.diagnostic("SYMLINK_REJECTED")
        inspection.transaction_scan_unknown = True
    elif not stat.S_ISDIR(info.st_mode):
        inspection.diagnostic("SPECIAL_FILE_REJECTED")
        inspection.transaction_scan_unknown = True
    else:
        inspection.counts["packages"] += 1
        package = _open_directory(packages_fd, name, inspection, "PACKAGE")
        if package is None:
            inspection.transaction_scan_unknown = True
            return
        package_fd, package_opened = package
        try:
            transactions = _open_optional_transactions(package_fd, inspection)
            if transactions is not None:
                transactions_fd, transactions_opened = transactions
                try:
                    _scan_transaction_entries(transactions_fd, inspection, kind="transaction_package")
                finally:
                    _close_directory(package_fd, "transactions", transactions_fd, transactions_opened, inspection)
        finally:
            _close_directory(packages_fd, name, package_fd, package_opened, inspection)


def _scan_packages(delivery_fd: int, inspection: _Inspection, *, selected: str | None) -> None:
    packages = _open_optional_pending_directory(delivery_fd, "packages", inspection, "PACKAGES")
    if packages is None:
        return
    packages_fd, packages_opened = packages
    try:
        _scan_package_root_transactions(packages_fd, inspection)
        for name in _package_change_names(packages_fd, inspection, selected=selected):
            _scan_package_change(packages_fd, name, inspection, required=selected is None)
    finally:
        _close_directory(delivery_fd, "packages", packages_fd, packages_opened, inspection)


def _scan_logs(runtime_fd: int, inspection: _Inspection) -> None:  # noqa: C901, PLR0912
    logs = _open_directory(runtime_fd, "logs", inspection, "LOGS")
    if logs is None:
        return
    logs_fd, logs_opened = logs
    try:
        for name in _directory_names(logs_fd, inspection):
            try:
                info = os.stat(name, dir_fd=logs_fd, follow_symlinks=False)
            except OSError:
                inspection.diagnostic("LOG_UNREADABLE")
                continue
            if stat.S_ISLNK(info.st_mode):
                inspection.diagnostic("SYMLINK_REJECTED")
                continue
            if not stat.S_ISREG(info.st_mode):
                inspection.diagnostic("SPECIAL_FILE_REJECTED")
                continue
            inspection.counts["logs"] += 1
            inspection.record("log", size_bytes=int(info.st_size), status="metadata-only")
            if info.st_size > MAX_LOG_BYTES:
                inspection.diagnostic("LOG_TRUNCATED")
            if info.st_size > MAX_TOTAL_BYTES - inspection.total_bytes:
                inspection.diagnostic("TOTAL_LIMIT_EXCEEDED")
                continue
            log_fd: int | None = None
            try:
                log_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=logs_fd)
                opened = os.fstat(log_fd)
                if not _same_identity(info, opened):
                    inspection.diagnostic("REPLACED_DURING_READ")
                    continue
                start = max(0, int(info.st_size) - MAX_LOG_BYTES)
                budget = MAX_TOTAL_BYTES - inspection.total_bytes
                os.lseek(log_fd, start, os.SEEK_SET)
                tail = os.read(log_fd, min(MAX_LOG_BYTES, budget))
                inspection.total_bytes += len(tail)
                after = os.fstat(log_fd)
                after_path = os.stat(name, dir_fd=logs_fd, follow_symlinks=False)
                if (
                    not _same_file_state(opened, after)
                    or not _same_file_state(info, after)
                    or not _same_file_state(info, after_path)
                ):
                    inspection.diagnostic("REPLACED_DURING_READ")
            except OSError:
                inspection.diagnostic("LOG_UNREADABLE")
            finally:
                if log_fd is not None:
                    os.close(log_fd)
    finally:
        _close_directory(runtime_fd, "logs", logs_fd, logs_opened, inspection)


def _scan_host_locks(runtime_fd: int, inspection: _Inspection) -> None:
    hosts = _open_optional_pending_directory(runtime_fd, "hosts", inspection, "HOSTS")
    if hosts is None:
        return
    hosts_fd, hosts_opened = hosts
    try:
        for name in _directory_names(hosts_fd, inspection):
            if not _HOST_LOCK_NAME.fullmatch(name):
                _unrecognized_change_entry(inspection)
                continue
            try:
                info = os.stat(name, dir_fd=hosts_fd, follow_symlinks=False)
            except OSError:
                inspection.diagnostic("HOST_LOCK_UNREADABLE")
                inspection.transaction_scan_unknown = True
                continue
            if stat.S_ISLNK(info.st_mode):
                inspection.diagnostic("SYMLINK_REJECTED")
                inspection.transaction_scan_unknown = True
            elif not stat.S_ISREG(info.st_mode):
                inspection.diagnostic("SPECIAL_FILE_REJECTED")
                inspection.transaction_scan_unknown = True
            else:
                inspection.counts["host_locks"] += 1
    finally:
        _close_directory(runtime_fd, "hosts", hosts_fd, hosts_opened, inspection)


def _scan_runtime(delivery_fd: int, inspection: _Inspection, *, selected: str | None) -> None:
    runtime = _open_directory(delivery_fd, "runtime", inspection, "RUNTIME", required=True)
    if runtime is None:
        inspection.transaction_scan_unknown = True
        _scan_snapshots(delivery_fd, inspection, selected=selected)
        _scan_packages(delivery_fd, inspection, selected=selected)
        return
    runtime_fd, runtime_opened = runtime
    try:
        _inspect_file(runtime_fd, "host.json", inspection, "host")
        _inspect_file(runtime_fd, "host.local.json", inspection, "host_local")
        inventory = _scan_change_records(runtime_fd, inspection, selected=selected)
        try:
            _scan_coordination(runtime_fd, inspection, selected=selected)
            if inventory is not None:
                _scan_change_current_records(inventory, inspection)
            _scan_host_locks(runtime_fd, inspection)
            _scan_snapshots(delivery_fd, inspection, selected=selected)
            if inventory is not None:
                _scan_change_pending_transactions(inventory, inspection)
            _scan_transactions(runtime_fd, inspection)
            _scan_nested_transaction_families(runtime_fd, inspection)
            _scan_packages(delivery_fd, inspection, selected=selected)
            if inventory is not None:
                _scan_change_receipts(inventory, inspection)
            if selected is None:
                _scan_logs(runtime_fd, inspection)
        finally:
            if inventory is not None:
                _close_directory(
                    runtime_fd,
                    "changes",
                    inventory.directory_fd,
                    inventory.directory_opened,
                    inspection,
                )
    finally:
        _close_directory(delivery_fd, "runtime", runtime_fd, runtime_opened, inspection)


def _inspect_delivery_tree(root_fd: int, inspection: _Inspection, *, selected: str | None) -> str | None:
    owlbear = _open_directory(root_fd, ".owlbear", inspection, "OWLBEAR", required=True)
    if owlbear is None:
        inspection.diagnostic("DELIVERY_ROOT_UNAVAILABLE")
        inspection.transaction_scan_unknown = True
        return "unavailable"
    owlbear_fd, owlbear_opened = owlbear
    try:
        delivery_diagnostics_before = len(inspection.diagnostics)
        delivery = _open_directory(owlbear_fd, "delivery", inspection, "DELIVERY")
        if delivery is None:
            if len(inspection.diagnostics) == delivery_diagnostics_before:
                inspection.diagnostic("DELIVERY_STATE_MISSING")
            else:
                inspection.transaction_scan_unknown = True
            return "degraded"
        delivery_fd, delivery_opened = delivery
        try:
            _inspect_file(delivery_fd, "config.json", inspection, "config", required=True)
            _scan_runtime(delivery_fd, inspection, selected=selected)
        finally:
            _close_directory(owlbear_fd, "delivery", delivery_fd, delivery_opened, inspection)
    finally:
        _close_directory(root_fd, ".owlbear", owlbear_fd, owlbear_opened, inspection)
    return None


def inspect_delivery(project_root: Path | str | None = None, change_id: str | None = None) -> dict[str, object]:
    """Inspect fixed Delivery paths without importing or initializing Delivery."""
    if change_id is not None and not _CHANGE_ID.fullmatch(change_id):
        raise ValueError(_INVALID_CHANGE_ID)
    try:
        root = (
            _discover_project_root(_absolute_without_following(Path.cwd()))
            if project_root is None
            else _absolute_without_following(Path(project_root))
        )
    except OSError:
        inspection = _Inspection(None, change_id)
        inspection.transaction_scan_unknown = True
        inspection.diagnostic("ROOT_UNAVAILABLE")
        return inspection.result(status="unavailable", complete=False)
    inspection = _Inspection(root, change_id)
    opened = _open_root(root)
    if opened is None:
        inspection.transaction_scan_unknown = True
        inspection.diagnostic("ROOT_UNAVAILABLE")
        return inspection.result(status="unavailable", complete=False)
    root_fd, root_descriptors = opened
    forced_status: str | None = None
    forced_complete = True
    try:
        forced_status = _inspect_delivery_tree(root_fd, inspection, selected=change_id)
        forced_complete = forced_status != "unavailable"
        if forced_status == "degraded":
            forced_complete = False
    finally:
        try:
            root_stable = _root_descriptors_are_stable(root, root_descriptors)
        except OSError:
            root_stable = False
        if not root_stable:
            inspection.diagnostic("REPLACED_DURING_INSPECTION")
            inspection.transaction_scan_unknown = True
            forced_complete = False
        for descriptor in reversed(root_descriptors):
            os.close(descriptor)
    if change_id is not None and not inspection.selected_runtime_change_seen and inspection.has_complete_inventory():
        inspection.diagnostic("CHANGE_NOT_FOUND")
    return inspection.result(status=forced_status, complete=forced_complete)


def _text(result: dict[str, object]) -> str:
    lines = [
        f"status: {result['status']}",
        f"inspection_complete: {str(result['inspection_complete']).lower()}",
        f"change_scope: {result['change_scope']}",
        f"truncated: {str(result['truncated']).lower()}",
        "versions: " + ", ".join(f"{key}={value}" for key, value in sorted(result["versions"].items())),
        "counts: " + ", ".join(f"{key}={value}" for key, value in sorted(result["counts"].items())),
        f"pending_effects: {str(result['pending_effects']).lower()}",
        "writes_performed: false",
        "diagnostic_codes: " + (", ".join(result["diagnostic_codes"]) or "none"),
        "observations:",
        *(
            "  "
            + str(record["locator"])
            + " status="
            + str(record["status"])
            + (f" size_bytes={record['size_bytes']}" if "size_bytes" in record else "")
            + (f" schema_version={record['schema_version']}" if "schema_version" in record else "")
            for record in result["records"]
        ),
        "maintenance_prompt:",
        str(result["maintenance_prompt"]),
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Run the fixed ``inspect`` operation and return its bounded exit code."""
    parser = _SafeArgumentParser(prog="delivery-diagnose")
    commands = parser.add_subparsers(dest="operation", required=True, parser_class=_SafeArgumentParser)
    inspect_parser = commands.add_parser("inspect")
    inspect_parser.add_argument("--project-root", type=Path)
    inspect_parser.add_argument("--change-id")
    inspect_parser.add_argument("--format", choices=("text", "json"), default="text")
    try:
        args = parser.parse_args(argv)
        result = inspect_delivery(args.project_root, args.change_id)
    except (ValueError, _InvocationError):
        print(_INVALID_INVOCATION)  # noqa: T201
        raise SystemExit(2) from None
    if args.format == "json":
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))  # noqa: T201
    else:
        print(_text(result), end="")  # noqa: T201
    if result["status"] == "healthy-structure":
        return 0
    if result["status"] == "unavailable":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
