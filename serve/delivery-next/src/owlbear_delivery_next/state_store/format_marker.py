"""The store format marker: which formats a runtime opens, and how a published target keeps its marker.

The marker is an ASCII integer. A target that holds no marker is written with the format it had before its move,
or with STORE_FORMAT; a marker that is present is kept only when it is a supported format.
"""

from owlbear_delivery_next.state_store import fd_tree
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT, StoreError


def supported_format(text: object) -> int:
    """A format marker this runtime opens: an ASCII integer from 1 through STORE_FORMAT; anything else is refused."""
    digits = text.strip() if isinstance(text, str) else ""
    if not (digits.isascii() and digits.isdigit()):
        msg = f"format marker {text!r} is not a supported store format: refusing it; nothing was changed"
        raise StoreError(msg)
    value = int(digits)
    if not 1 <= value <= STORE_FORMAT:
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
    """Keep the target's own marker when it is a supported format; write *previous* (or STORE_FORMAT) when it has none.

    Read through the descriptor already validated: a FIFO, a link or another special entry is refused without
    blocking, and nothing is written over it.
    """
    try:
        text = fd_tree.read_at(tfd, MARKER)
    except OSError as exc:
        msg = "the target's format marker is not a regular file: refusing it; nothing was changed"
        raise StoreError(msg) from exc
    if text is None:
        fd_tree.write_at(tfd, MARKER, f"{previous or STORE_FORMAT}\n")  # keeps the format it was written in
        return
    supported_format(text)


def written_format(tfd: int, previous: int) -> None:
    """Refuse unless the target's marker is still present and holds the format ensure_target wrote for *previous*.

    Called after the target is synced, so a marker removed or changed while it was made durable stops the switch.
    """
    try:
        text = fd_tree.read_at(tfd, MARKER)
    except OSError as exc:
        msg = "the target's format marker is not a regular file: nothing was switched"
        raise StoreError(msg) from exc
    if text is None or supported_format(text) != (previous or STORE_FORMAT):
        msg = "the target's format marker changed while it was published: nothing was switched; start again"
        raise StoreError(msg)
