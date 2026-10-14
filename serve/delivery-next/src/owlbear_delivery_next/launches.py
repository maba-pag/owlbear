"""New Change launches: the shaping chat opens on a background thread, one at a time per project (TD-83).

The page gets a launch id at once and polls its state; a launch can take minutes when VS Code must start.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

KEPT = 16  # ended launches whose state the page can still read


class Refused(Exception):  # noqa: N818 - the route's answer, not a fault
    """A launch is opening or one ended less than the gap ago."""

    def __init__(self, status: int, text: str) -> None:
        """Keep the HTTP status and the owner's reason."""
        super().__init__(text)
        self.status, self.text = status, text


@dataclass
class Launch:
    """One New Change launch as the page sees it."""

    state: Literal["opening", "open", "failed"] = "opening"
    reason: str = ""
    warning: str = ""  # what Delivery could not undo in the owner's settings


class Launches:
    """The project's launches; the gap between two starts when the earlier one ends."""

    def __init__(self, gap: float, clock: Callable[[], float]) -> None:
        """Start with no launch and no gap to wait."""
        self.gap, self.clock = gap, clock
        self.lock = threading.Lock()
        self.ended = -gap
        self.opening: str | None = None
        self.kept: dict[str, Launch] = {}

    def start(self, work: Callable[[], dict[str, str]]) -> str:
        """Run ``work`` on its own thread and return the launch id; ``work`` gives the ending state."""
        with self.lock:
            if self.opening:
                raise Refused(409, "a shaping chat is already opening")
            if self.clock() - self.ended < self.gap:
                raise Refused(429, "A new Change chat was just opened; wait a few seconds")
            self.opening = launch = uuid.uuid4().hex[:12]
            self.kept[launch] = Launch()
            while len(self.kept) > KEPT:
                del self.kept[next(iter(self.kept))]
        threading.Thread(target=self._run, args=(launch, work), name=f"new-change-{launch}", daemon=True).start()
        return launch

    def _run(self, launch: str, work: Callable[[], dict[str, str]]) -> None:
        try:
            out = work()
        except Exception as exc:  # noqa: BLE001 - the page must learn how its launch ended
            out = {"state": "failed", "reason": f"{type(exc).__name__}: {exc}"[:300]}
        with self.lock:
            if (kept := self.kept.get(launch)) is not None:
                kept.state, kept.reason, kept.warning = out["state"], out.get("reason", ""), out.get("warning", "")
            self.opening, self.ended = None, self.clock()

    def state(self, launch: str) -> dict[str, Any] | None:
        """The launch's state, reason and warning, the empty ones left out; None for an unknown id."""
        with self.lock:
            kept = self.kept.get(launch)
            return None if kept is None else {k: v for k, v in asdict(kept).items() if v}
