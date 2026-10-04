"""Single-use consent generations for questions asked through the confirmation boundary (D13, I11).

Each question renders one server-owned generation that exists before it is asked. The first answer
consumes it atomically with every write the answer causes; later answers return the recorded
disposition. Generations are local replay protection, never confirmation authority, and are not
part of snapshots.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

CONSENT_GENERATION_DIRECTORY = "consent-generations"
_SEQUENCE_WIDTH = 8
_SEQUENCE_FILE = re.compile(r"[0-9]{8}\.json")
_MAX_CREATE_ATTEMPTS = 8


class _ConsentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryConsentDisposition(_ConsentModel):
    """The recorded outcome of the first answer to one generation."""

    outcome: Literal["accepted", "declined", "cancelled", "refused"]
    code: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    confirmation_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    record_id: str | None = Field(default=None, min_length=1, max_length=256)

    @model_validator(mode="after")
    def _validate_disposition(self) -> DeliveryConsentDisposition:
        if (self.outcome == "accepted") != (self.confirmation_id is not None):
            message = "only an accepted consent disposition names its confirmation"
            raise ValueError(message)
        if (self.outcome == "refused") != (self.code is not None):
            message = "only a refused consent disposition carries a refusal code"
            raise ValueError(message)
        return self


class DeliveryConsentGeneration(_ConsentModel):
    """One single-use question identity, mutable only by the CAS transition ``open`` -> ``answered``."""

    schema_version: Literal[1] = 1
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    use: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    subject_id: str = Field(min_length=1, max_length=256)
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    sequence: int = Field(ge=1, lt=10**_SEQUENCE_WIDTH)
    generation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    state: Literal["open", "answered"] = "open"
    disposition: DeliveryConsentDisposition | None = None

    @model_validator(mode="after")
    def _validate_generation(self) -> DeliveryConsentGeneration:
        if (self.state == "answered") != (self.disposition is not None):
            message = "an answered consent generation records exactly one disposition"
            raise ValueError(message)
        if self.created_at.tzinfo is None:
            message = "consent generation timestamp must include a timezone"
            raise ValueError(message)
        return self

    def answered(self, disposition: DeliveryConsentDisposition) -> DeliveryConsentGeneration:
        """Return this open generation consumed by its first answer."""
        if self.state != "open":
            message = "consent generation is already answered"
            raise ValueError(message)
        return self.model_copy(update={"state": "answered", "disposition": disposition})


def consent_binding_digest(binding: Mapping[str, object]) -> str:
    """Return the digest of one use's canonical binding."""
    encoded = json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _content(generation: DeliveryConsentGeneration) -> bytes:
    payload = generation.model_dump(mode="json")
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


class ConsentGenerationStore:
    """Per-Change generation records under ``runtime/changes/<change>/consent-generations``."""

    def __init__(self, runtime_root: Path, change_id: str) -> None:
        self._root = runtime_root.resolve()
        self._change_id = change_id
        self._relative = Path("changes") / change_id / CONSENT_GENERATION_DIRECTORY

    def _path(self, sequence: int) -> Path:
        return self._relative / f"{sequence:0{_SEQUENCE_WIDTH}d}.json"

    def _entries(self) -> list[tuple[int, Path]]:
        directory = self._root / self._relative
        if directory.is_symlink():
            message = "consent generation directory is unsafe"
            raise ValueError(message)
        if not directory.is_dir():
            return []
        entries = []
        for path in directory.iterdir():
            if _SEQUENCE_FILE.fullmatch(path.name) is None:
                continue
            entries.append((int(path.name.removesuffix(".json")), self._relative / path.name))
        return sorted(entries)

    def read(self, sequence: int) -> tuple[DeliveryConsentGeneration, bytes]:
        """Read one generation strictly; its bytes must be canonical and name this Change."""
        path = self._root / self._path(sequence)
        if path.is_symlink():
            message = "consent generation record is unsafe"
            raise ValueError(message)
        content = path.read_bytes()
        generation = DeliveryConsentGeneration.model_validate_json(content, strict=True)
        if (
            content != _content(generation)
            or generation.change_id != self._change_id
            or generation.sequence != sequence
        ):
            message = "consent generation record is invalid"
            raise ValueError(message)
        return generation, content

    def latest(self, use: str, subject_id: str) -> tuple[DeliveryConsentGeneration, bytes] | None:
        """Return the subject's most recent generation, whatever its state."""
        for sequence, _path in reversed(self._entries()):
            generation, content = self.read(sequence)
            if generation.use == use and generation.subject_id == subject_id:
                return generation, content
        return None

    def create(
        self,
        *,
        use: str,
        subject_id: str,
        binding_digest: str,
        created_at: datetime,
    ) -> tuple[DeliveryConsentGeneration, bytes]:
        """Durably create the next generation by exclusive create before it is asked."""
        for _attempt in range(_MAX_CREATE_ATTEMPTS):
            entries = self._entries()
            sequence = entries[-1][0] + 1 if entries else 1
            generation = DeliveryConsentGeneration(
                change_id=self._change_id,
                use=use,
                subject_id=subject_id,
                binding_digest=binding_digest,
                sequence=sequence,
                generation_id=secrets.token_hex(32),
                created_at=created_at,
            )
            content = _content(generation)
            participant = TransactionParticipant(self._root, self._path(sequence), content)
            try:
                RuntimeTransaction(
                    self._root,
                    f"consent-generation-{self._change_id}-{generation.generation_id}",
                    (participant,),
                ).commit()
            except TransactionConflictError:
                continue
            return generation, content
        message = "consent generation sequence is contended"
        raise TransactionConflictError(message)

    def answer_participant(
        self,
        generation: DeliveryConsentGeneration,
        content: bytes,
        disposition: DeliveryConsentDisposition,
    ) -> ReplacementTransactionParticipant:
        """Return the CAS participant that consumes one open generation inside the answer's transaction."""
        return ReplacementTransactionParticipant(
            self._root,
            self._path(generation.sequence),
            content,
            _content(generation.answered(disposition)),
        )

    def record_answer(
        self,
        generation: DeliveryConsentGeneration,
        content: bytes,
        disposition: DeliveryConsentDisposition,
    ) -> None:
        """Consume one open generation when the answer causes no other write."""
        participant = self.answer_participant(generation, content, disposition)
        RuntimeTransaction(
            self._root,
            f"consent-answer-{self._change_id}-{generation.generation_id}",
            (participant,),
        ).commit()


__all__ = [
    "CONSENT_GENERATION_DIRECTORY",
    "ConsentGenerationStore",
    "DeliveryConsentDisposition",
    "DeliveryConsentGeneration",
    "consent_binding_digest",
]
