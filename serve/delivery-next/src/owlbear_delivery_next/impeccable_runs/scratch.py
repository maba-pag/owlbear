"""A temporary repository an Impeccable session works in; it stays while the maintenance ledger holds the session."""

from __future__ import annotations

import contextlib
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


@contextlib.contextmanager
def scratch(prefix: str, keep: Callable[[Path], bool] | None = None) -> Iterator[Path]:
    """Yield a new directory and remove it on exit, unless *keep* says its session is unproven.

    The ledger records a session's outcome before the session's call returns or raises, so *keep* is read after that.
    """
    at = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield at
    finally:
        if not (keep and keep(at)):
            shutil.rmtree(at, ignore_errors=True)
