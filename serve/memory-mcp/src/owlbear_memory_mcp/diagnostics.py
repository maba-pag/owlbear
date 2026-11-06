"""Request-local diagnostics alongside healthy memory tool results."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from owlbear_memory import MemoryEngine


class ReadDiagnostics(TypedDict, total=False):
    """Optional internal collectors, never agent-facing tool arguments."""

    read_errors: dict[str, str]


def collect(engine: MemoryEngine, read_errors: dict[str, str] | None, where: str = "project") -> None:
    """Keep the loaded snapshot's safe errors, including the folder's reading context."""
    if read_errors is not None:
        read_errors.update({path: f"{where}: {detail}" for path, detail in engine.read_errors.items()})


def with_read_errors(data: dict[str, Any], read_errors: dict[str, str]) -> dict[str, Any]:
    """Leave healthy result shapes unchanged."""
    return data | {"read_errors": dict(read_errors)} if read_errors else data
