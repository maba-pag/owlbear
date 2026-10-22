"""Pydantic models for decisions: one record per lasting decision of OwlBear, a project or a Change."""

from __future__ import annotations

import enum
import hashlib
import json
import secrets
from datetime import UTC, date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, computed_field, field_validator, model_validator

STATEMENT_LIMIT = 240
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ID_PATTERN = r"^D-[0-7][0-9A-HJKMNP-TV-Z]{25}$"
ALIAS_PATTERN = r"^[A-Z][A-Z0-9]*-[0-9]+$"
FOLDER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
CHANGE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$"  # Delivery's record stem: approval second plus a 64-char slug

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Alias = Annotated[str, StringConstraints(pattern=ALIAS_PATTERN)]


class Origin(enum.StrEnum):
    """Who made the decision ("Prior decisions by origin")."""

    DECIDED = "decided"
    APPROVED = "approved"
    AUTONOMOUS = "autonomous"


class Scope(enum.StrEnum):
    """Where a decision applies (TD-426)."""

    GLOBAL = "global"
    PROJECT = "project"
    CHANGE = "change"


class State(enum.StrEnum):
    """Lifecycle state (TD-430); nothing is deleted."""

    DRAFT = "draft"
    IN_FORCE = "in_force"
    REPLACED = "replaced"
    WITHDRAWN = "withdrawn"
    SPENT = "spent"


class LinkType(enum.StrEnum):
    """The fixed link set (TD-429)."""

    REPLACES = "replaces"
    REFINES = "refines"
    EXCEPTION_TO = "exception_to"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    PROMOTED_FROM = "promoted_from"


class ReadBackKind(enum.StrEnum):
    """Why a read-back waits, most urgent first: the queue's order (TD-427, §8)."""

    SAFETY = "safety"  # imminent safety or irreversible effects
    BLOCKED = "blocked"  # blocked work
    UNCERTAIN = "uncertain"  # consequential uncertainty
    IMPROVEMENT = "improvement"  # deferred improvement


READ_BACK_EXTRAS = ("read_back_why", "read_back_kind")  # left out of a decision's content while empty
OMITTED_WHEN_EMPTY = (*READ_BACK_EXTRAS, "inherited")
# files hashed empty `owner_words` and selectors before TD-449 and TD-460 removed them; hashing them keeps revisions
_LEGACY_HASHED = {"owner_words": [], "applies_to": {"paths": [], "roles": [], "steps": []}}


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Link(_Frozen):
    """A typed link to another decision by id."""

    type: LinkType
    target: Annotated[str, StringConstraints(pattern=ID_PATTERN)]


class Decision(_Frozen):
    """One decision; `revision` is the sha256 of its canonical content.

    Statement length is a validator finding, not a construction error, so a faulty file still loads and is
    reported (see `validate`). The owner's words are never stored (TD-449) and decisions carry no paths, roles or
    steps selectors (TD-460); an older file's are dropped on reading. `read_back` is the date the owner last
    confirmed the statement; `inherited` marks a decision brought over from the old record and never read back
    (TD-454).
    """

    id: Annotated[str, StringConstraints(pattern=ID_PATTERN)]
    aliases: tuple[Alias, ...] = ()
    title: NonBlank
    topic: str = ""
    statement: NonBlank
    rationale: str = ""
    consequences: str = ""
    scope: Scope
    project: Annotated[str, StringConstraints(pattern=f"{FOLDER_PATTERN}|^$")] = ""
    change: Annotated[str, StringConstraints(pattern=f"{CHANGE_PATTERN}|^$")] = ""
    origin: Origin
    actor: NonBlank
    source: str = ""
    inherited: bool = False
    state: State = State.DRAFT
    links: tuple[Link, ...] = ()
    conflict: bool = False
    read_back: str = Field(default="none", pattern=r"^(none|pending|\d{4}-\d{2}-\d{2})$")
    read_back_why: str = ""
    read_back_kind: ReadBackKind | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _drop_retired(cls, data: object) -> object:
        if isinstance(data, dict) and _LEGACY_HASHED.keys() & data.keys():
            return {k: v for k, v in data.items() if k not in _LEGACY_HASHED}
        return data

    @field_validator("rationale", "read_back_why")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("read_back", mode="before")
    @classmethod
    def _read_back_date(cls, value: object) -> object:
        return value.isoformat() if isinstance(value, date) else value

    @field_validator("created_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            msg = "created_at needs a time zone"
            raise ValueError(msg)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _scope_fields(self) -> Decision:
        wanted = {Scope.GLOBAL: (False, False), Scope.PROJECT: (True, False), Scope.CHANGE: (True, True)}
        if (bool(self.project), bool(self.change)) != wanted[self.scope]:
            msg = f"a {self.scope} decision needs project {'set' if wanted[self.scope][0] else 'empty'}"
            msg += f" and change {'set' if wanted[self.scope][1] else 'empty'}"
            raise ValueError(msg)
        if self.read_back not in {"none", "pending"}:
            date.fromisoformat(self.read_back)
        return self._read_back_reason()

    def _read_back_reason(self) -> Decision:
        pending = self.read_back == "pending"
        if pending and not (self.read_back_why and self.read_back_kind):
            msg = "a pending read-back needs read_back_why and read_back_kind"
            raise ValueError(msg)
        if self.read_back == "none" and (self.read_back_why or self.read_back_kind):
            msg = "read_back_why and read_back_kind belong to a read-back: pending, or the one answered on its date"
            raise ValueError(msg)
        return self

    def content(self) -> dict[str, object]:
        """The canonical content: every field in declaration order, JSON-typed, without `revision`.

        An empty read-back reason and `inherited` false are left out, so files written before they existed keep
        their revision.
        """
        found = self.model_dump(mode="json", exclude={"revision"})
        return {k: v for k, v in found.items() if k not in OMITTED_WHEN_EMPTY or v}

    @computed_field
    @property
    def revision(self) -> str:
        """Sha256 of the canonical JSON of `content()`."""
        return _digest(self.content())

    @property
    def rule_revision(self) -> str:
        """Sha256 of the content but its read-back and `inherited`: what a Change pins; confirming changes no rule."""
        return _digest({k: v for k, v in self.content().items()
                        if k not in {"read_back", "inherited", *READ_BACK_EXTRAS}})  # fmt: skip


def _digest(content: dict[str, object]) -> str:
    canonical = json.dumps(content | _LEGACY_HASHED, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def new_id(at: datetime | None = None, seed: str | None = None) -> str:
    """A ULID-style id: `D-` plus 26 Crockford base32 characters (48-bit milliseconds, 80 bits of tail).

    The tail is random, or derived from `seed` so a migration preview mints the same ids on every run.
    """
    millis = int((at or datetime.now(UTC)).timestamp() * 1000)
    tail = hashlib.sha256(seed.encode()).digest()[:10] if seed is not None else secrets.token_bytes(10)
    value = (millis << 80) | int.from_bytes(tail)
    return "D-" + "".join(_CROCKFORD[(value >> (5 * shift)) & 31] for shift in reversed(range(26)))
