"""The store format marker: which formats a runtime opens, and how a published target keeps its marker.

The marker is an ASCII integer. A target that holds no marker is created exclusively with the format it had before
its move, or with STORE_FORMAT. An existing or collided marker is kept only when supported, then made durable.
"""

import contextlib
import os

from owlbear_delivery_next.state_store import fd_tree
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT, FormatTooNewError, StoreError


def supported_format(text: object) -> int:
    """A format marker this runtime opens: an ASCII integer from 1 through STORE_FORMAT; anything else is refused.

    A newer format raises FormatTooNewError, so the stop tells the owner to upgrade rather than to restore.
    """
    digits = text.strip() if isinstance(text, str) else ""
    if not (digits.isascii() and digits.isdigit()):
        msg = f"format marker {text!r} is not a supported store format: refusing it; nothing was changed"
        raise StoreError(msg)
    try:
        value = int(digits)
    except ValueError as exc:
        msg = "format marker is not a readable integer: refusing it; nothing was changed"
        raise StoreError(msg) from exc
    if value > STORE_FORMAT:
        msg = f"store format {value} is newer than {STORE_FORMAT}"
        raise FormatTooNewError(msg)
    if value < 1:
        msg = f"format {value} is not a supported store format (1 to {STORE_FORMAT}): refusing it"
        raise StoreError(msg)
    return value


def prior_format(text: object) -> int:
    """A format the store held before its offline move: 0 when it had no marker, else a supported format.

    Only the exact empty string (how an absent marker is recorded) or None is 0; any other text, including
    whitespace, must be a supported format. The fence itself is never a prior format, and nothing above
    STORE_FORMAT is one.
    """
    if text is None or text == "":
        return 0
    return supported_format(text)


def ensure_target(tfd: int, previous: int) -> None:
    """Keep and sync a supported marker; exclusively create *previous* (or STORE_FORMAT) when it has none.

    A collision adopts only a supported regular file, never replacing or unlinking the entry. Reads are no-follow
    and non-blocking; the file and folder are synced before admission, then the marker is checked again.
    """
    try:
        text = fd_tree.read_at(tfd, MARKER)
    except (OSError, UnicodeError) as exc:
        msg = "the target's format marker is not a regular file: refusing it; nothing was changed"
        raise StoreError(msg) from exc
    if text is None:
        with contextlib.suppress(FileExistsError):
            fd_tree.create_at(tfd, MARKER, f"{previous or STORE_FORMAT}\n")
    else:
        supported_format(text)
    _durable_target(tfd)


def _durable_target(tfd: int) -> None:
    """Sync the supported regular marker actually read, then refuse if its name or bytes changed during the sync.

    The raw descriptor stays owned until finally, including when its file-object handover fails.
    """
    try:
        fd = fd_tree.open_file(tfd, MARKER)
        try:
            with os.fdopen(fd, "rb", closefd=False) as marker:
                held = fd_tree.ident(os.fstat(marker.fileno()))
                text = marker.read().decode()
                supported_format(text)
                os.fsync(marker.fileno())
                os.fsync(tfd)
                current = fd_tree.read_at(tfd, MARKER)
                if current is not None:
                    supported_format(current)
                now = fd_tree.stat_at(tfd, MARKER)
                if current != text or now is None or fd_tree.ident(now) != held:
                    msg = (
                        "the target's format marker changed while it was made durable: "
                        "nothing was switched; start again"
                    )
                    raise StoreError(msg)
        finally:
            os.close(fd)
    except (OSError, UnicodeError) as exc:
        msg = f"the target's format marker could not be made durable ({exc}): nothing was switched; it is kept"
        raise StoreError(msg) from exc


def written_format(tfd: int, previous: int) -> None:
    """Refuse unless the target's marker is still present and holds the format ensure_target wrote for *previous*.

    Called after the target is synced, so a marker removed or changed while it was made durable stops the switch.
    """
    try:
        text = fd_tree.read_at(tfd, MARKER)
    except (OSError, UnicodeError) as exc:
        msg = "the target's format marker is not a regular file: nothing was switched"
        raise StoreError(msg) from exc
    if text is None or supported_format(text) != (previous or STORE_FORMAT):
        msg = "the target's format marker changed while it was published: nothing was switched; start again"
        raise StoreError(msg)
