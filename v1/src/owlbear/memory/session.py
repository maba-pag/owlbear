"""JSONL-based session persistence for PydanticAI message histories."""

from __future__ import annotations

import json
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
        self._last_consolidated: int | None = None

    @property
    def path(self) -> Path:
        """Location of the JSONL file."""
        return self._path

    @property
    def last_consolidated(self) -> int | None:
        """Index into the message list up to which consolidation has run."""
        return self._last_consolidated

    @last_consolidated.setter
    def last_consolidated(self, value: int | None) -> None:
        self._last_consolidated = value

    # -- read ----------------------------------------------------------------

    def load(self) -> list[ModelMessage]:
        """Deserialize all messages from the JSONL file.

        Returns an empty list when the file doesn't exist or is empty.
        """
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").strip().splitlines()
        self._load_meta()
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
        self._save_meta()

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

    # -- metadata ------------------------------------------------------------

    @property
    def _meta_path(self) -> Path:
        """Path to the companion ``.meta`` JSON file."""
        return self._path.with_suffix(".meta")

    def _load_meta(self) -> None:
        """Restore ``last_consolidated`` from the ``.meta`` file."""
        if not self._meta_path.exists():
            return
        data = json.loads(self._meta_path.read_text(encoding="utf-8"))
        self._last_consolidated = data.get("last_consolidated")

    def _save_meta(self) -> None:
        """Persist ``last_consolidated`` to the ``.meta`` file."""
        self._meta_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"last_consolidated": self._last_consolidated}
        self._meta_path.write_text(json.dumps(data), encoding="utf-8")
