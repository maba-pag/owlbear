"""Filesystem context for the native delivery control plane."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_DURATION_PATTERN = re.compile(r"^(?P<amount>[1-9]\d*)(?P<unit>[smhd])$")
_DURATION_UNITS = {
    "s": timedelta(seconds=1),
    "m": timedelta(minutes=1),
    "h": timedelta(hours=1),
    "d": timedelta(days=1),
}


def parse_claim_expiry(value: str) -> timedelta:
    """Parse one positive native claim expiry such as ``30m`` or ``2h``."""
    match = _DURATION_PATTERN.fullmatch(value.strip())
    if match is None:
        message = "claim expiry must be a positive integer followed by s, m, h, or d"
        raise ValueError(message)
    return int(match.group("amount")) * _DURATION_UNITS[match.group("unit")]


@dataclass(frozen=True, slots=True)
class NativeWorkspace:
    """Bind native authority and runtime stores without loading legacy state."""

    work_root: Path
    claim_expiry: timedelta = timedelta(hours=1)

    def __post_init__(self) -> None:
        root = self.work_root.resolve()
        if not root.is_dir():
            raise FileNotFoundError(root)
        if self.claim_expiry <= timedelta(0):
            message = "claim expiry must be positive"
            raise ValueError(message)
        object.__setattr__(self, "work_root", root)

    @property
    def ops_root(self) -> Path:
        """Return the shared operational root containing native stores."""
        return self.work_root.parent

    @property
    def changes_dir(self) -> Path:
        """Return the canonical native change-authority root."""
        return self.ops_root / "changes"

    @property
    def workspace_root(self) -> Path:
        """Return the repository root containing the operational directory."""
        return self.ops_root.parent

    @property
    def proof_root(self) -> Path:
        """Return the contained proof-checkout root."""
        return self.ops_root / "scratch" / "proof"

    @property
    def legacy_snapshot_root(self) -> Path:
        """Return the immutable legacy-inventory root."""
        return self.ops_root / "legacy" / "kanban-final"
