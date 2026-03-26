"""Generic append-only JSONL store with Pydantic (de)serialization.

Provides :class:`JsonlStore[T]` — a thin, reusable base class for any
append-only JSONL file backed by a Pydantic ``BaseModel``.

Concrete stores (:class:`~owlbear.memory.usage.UsageTracker`,
:class:`~owlbear.core.observability.EventStore`) inherit this base and add
domain-specific query / aggregation methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import TypeAdapter

if TYPE_CHECKING:
    from pathlib import Path


class JsonlStore[T]:
    """Append-only JSONL store for any Pydantic-serializable record type.

    Usage::

        store = JsonlStore(Path("data.jsonl"), MyModel)
        store.append(record)
        records = store.load()
    """

    def __init__(self, path: Path, record_type: type[T]) -> None:
        self._path = path
        self._adapter: TypeAdapter[T] = TypeAdapter(record_type)

    @property
    def path(self) -> Path:
        """Location of the JSONL file."""
        return self._path

    # -- write ---------------------------------------------------------------

    def append(self, record: T) -> None:
        """Serialize *record* and append it as a new JSONL line."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = self._adapter.dump_json(record).decode("utf-8")
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    # -- read ----------------------------------------------------------------

    def load(self) -> list[T]:
        """Deserialize all records from the JSONL file.

        Returns an empty list when the file doesn't exist or is empty.
        """
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").strip().splitlines()
        return [self._adapter.validate_json(line) for line in lines if line]
