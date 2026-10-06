"""Entry point for ``python -m owlbear_delivery_mcp``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from owlbear_delivery_mcp.server import mcp
from owlbear_delivery_mcp.target_models import DeliveryStartupDiagnostic

if TYPE_CHECKING:
    from collections.abc import Iterator


def main() -> None:
    """Run the server; a typed startup refusal prints one line per diagnostic and exits 1."""
    try:
        mcp.run()
    except DeliveryStartupDiagnostic as diagnostic:
        _refuse((diagnostic,))
    except BaseExceptionGroup as group:
        matched, rest = group.split(DeliveryStartupDiagnostic)
        if matched is None or rest is not None:
            raise
        _refuse(tuple(_leaves(matched)))


def _leaves(group: BaseExceptionGroup) -> Iterator[DeliveryStartupDiagnostic]:
    for exc in group.exceptions:
        if isinstance(exc, BaseExceptionGroup):
            yield from _leaves(exc)
        elif isinstance(exc, DeliveryStartupDiagnostic):
            yield exc


def _refuse(diagnostics: tuple[DeliveryStartupDiagnostic, ...]) -> None:
    for diagnostic in diagnostics:
        retry_safe = str(diagnostic.retry_safe).lower()
        sys.stderr.write(
            f"Delivery MCP refused to start: {diagnostic.code}: {diagnostic.detail} "
            f"(field={diagnostic.field}, retry_safe={retry_safe})\n"
        )
    sys.exit(1)


if __name__ == "__main__":
    main()
