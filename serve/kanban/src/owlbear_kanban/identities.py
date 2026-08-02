"""Constrained identities shared by target delivery modules."""

from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

ChangeId = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
