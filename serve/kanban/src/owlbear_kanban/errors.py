"""Kanban engine domain error catalogue and exception hierarchy."""

from __future__ import annotations

from importlib import import_module

KANBAN_ERROR_CODES: frozenset[str] = frozenset(
    {
        "ERR_NOT_CLAIMED",
        "ERR_BLOCK_REASON_REQUIRED",
        "ERR_NO_OP",
        "ERR_BODY_EXCLUSIVE",
        "ERR_IDS_EXCLUSIVE",
        "ERR_SECTION_EMPTY",
        "ERR_INVALID_TITLE",
        "ERR_INVALID_STATUS",
        "ERR_CONFLICT_STATUS",
        "ERR_PATH_ESCAPE",
        "ERR_INVALID_PRIORITY",
        "ERR_INVALID_WAVE_PARAM",
        "ERR_PROOF_BUNDLE_INVALID",
        "ERR_AC_EXCLUSIVE",
        "ERR_AC_DUPLICATE",
        "ERR_AC_LIMIT",
        "ERR_AC_ITEM_TOO_LONG",
        "ERR_PARENT_NOT_FOUND",
        "ERR_DEP_NOT_FOUND",
        "ERR_ARCHIVAL_REASON_INVALID",
        "ERR_ARCHIVAL_REASON_REQUIRED",
        "ERR_ARCHIVAL_FIELDS_FORBIDDEN",
        "ERR_ARCHIVAL_REFS_REQUIRED",
        "ERR_ARCHIVAL_REFS_FORBIDDEN",
        "ERR_ARCHIVAL_REF_MISSING",
        "ERR_ARCHIVAL_REF_SELF",
        "ERR_ARCHIVAL_REF_CYCLE",
        "ERR_COMPLETED_REQUIRES_DONE",
        "ERR_INVALID_OUTCOME",
        "ERR_REJECT_REQUIRES_MOVE_TO",
        "ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK",
        "ERR_MOVE_TO_FORBIDDEN_ON_SUCCESS",
        "ERR_MOVE_TO_NOT_FORWARD",
        "ERR_MOVE_TO_INVALID_STATUS",
        "ERR_MOVE_TO_FORBIDDEN_ON_FAIL",
        "ERR_MOVE_TO_FORBIDDEN_ON_RELEASE",
        "ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS",
        "ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_FAIL",
        "ERR_PREDICATE_FAILED",
        "ERR_ENTRY_STATUS_INVALID",
        "ERR_INVALID_CLAIM_TIMEOUT",
        "ERR_TERMINAL_STATUS_INVALID",
        "ERR_DISPATCH_PRIORITY_MISMATCH",
        "ERR_DISPATCH_STATUS_MISMATCH",
        "ERR_MIGRATION_REQUIRED",
        "ERR_ALREADY_CLAIMED",
        "ERR_ARCHIVED_NOT_CLAIMABLE",
        "ERR_BLOCKED_NOT_CLAIMABLE",
        "ERR_BODY_TOO_LARGE",
        "ERR_STALE",
        "ERR_NOT_FOUND",
        "ERR_CORRUPT_DELIMITERS",
        "ERR_CORRUPT_DUPLICATE_ID",
        "ERR_CORRUPT_MISSING_FIELD",
        "ERR_CORRUPT_TYPE_MISMATCH",
        "ERR_CORRUPT_YAML_PARSE",
        "ERR_CORRUPT_ID_FILENAME_MISMATCH",
        "ERR_CORRUPT_DUPLICATE_LOCATION",
        "ERR_CORRUPT_INVALID_STATUS",
        "ERR_CORRUPT_INVALID_PRIORITY",
        "ERR_CORRUPT_ENCODING",
    }
)


class KanbanError(Exception):
    """Base exception for kanban engine domain errors."""

    def __init__(self, code: str, user_message: str) -> None:
        if code not in KANBAN_ERROR_CODES:
            msg = f"Unknown error code: {code!r}"
            raise ValueError(msg)
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message


class ValidationError(KanbanError):
    """Raised when tool input or mutation intent is invalid."""


class NotFoundError(KanbanError):
    """Raised when an addressed task or section does not exist."""


class ConcurrencyError(KanbanError):
    """Raised by write_task_if_unchanged when the on-disk version is newer."""


class ConfigError(KanbanError):
    """Raised when board configuration contains an invalid value."""


class MigrationRequiredError(KanbanError):
    """The board requires migration before it can be used.

    Raised by ``KanbanEngine.__init__`` when any active task file contains
    the legacy ``claimed_by`` field (Brief C §1.5, AC-C47).
    """


def __getattr__(name: str) -> object:
    if name == "CorruptionError":
        return import_module("owlbear_kanban.corruption").CorruptionError
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
