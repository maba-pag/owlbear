"""JSONL-based session persistence for PydanticAI message histories."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from pydantic import TypeAdapter
from pydantic_ai.messages import ModelMessage

if TYPE_CHECKING:
    from pathlib import Path

_message_adapter: TypeAdapter[ModelMessage] = TypeAdapter(ModelMessage)


class SessionStore:
    """Append-only JSONL store for :class:`~pydantic_ai.messages.ModelMessage`.

    Each message is serialized as a single JSON line.  The file can be loaded
    back to reconstruct the full conversation history that PydanticAI expects
    via ``Agent.run(message_history=...)``.

    Usage::

        store = SessionStore(Path("sessions/abc.jsonl"))
        store.append(request_msg)
        store.append(response_msg)
        history = store.load()
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        """Location of the JSONL file."""
        return self._path

    # -- read ----------------------------------------------------------------

    def load(self) -> list[ModelMessage]:
        """Deserialize all messages from the JSONL file.

        Returns an empty list when the file doesn't exist or is empty.
        """
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").strip().splitlines()
        return [_message_adapter.validate_json(line) for line in lines if line]

    # -- write ---------------------------------------------------------------

    def append(self, message: ModelMessage) -> None:
        """Serialize *message* and append it as a new line."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = _message_adapter.dump_json(message).decode("utf-8")
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def save(self, messages: list[ModelMessage]) -> None:
        """Overwrite the file with *messages* (bulk rewrite)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as fh:
            for msg in messages:
                fh.write(_message_adapter.dump_json(msg).decode("utf-8") + "\n")

    # -- maintenance ---------------------------------------------------------

    def backup(self) -> Path | None:
        """Copy the JSONL file to ``<name>.bak``.

        Returns the backup path, or ``None`` if the source doesn't exist.
        """
        if not self._path.exists():
            return None
        bak = self._path.with_suffix(".bak")
        shutil.copy2(self._path, bak)
        return bak
