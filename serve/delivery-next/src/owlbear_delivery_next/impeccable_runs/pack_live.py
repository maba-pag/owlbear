"""What an Impeccable update reaches outside (``pack_job``): upstream, downloads, the browser, sessions and git.

Each is a field of ``Live``, so tests replace each without the network.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from owlbear_delivery_next.github.gh import GhProvider
from owlbear_delivery_next.impeccable import pack_files, pack_git, pack_update
from owlbear_delivery_next.impeccable_runs import pack_candidate, pack_replay
from owlbear_delivery_next.workflow_steps import sessions

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.github.provider import Provider
    from owlbear_delivery_next.impeccable.calibration import Replay
    from owlbear_delivery_next.runtimes.sdk_adapter import Session
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Store

__all__ = ["Live"]


def _upstream() -> Path:
    return pack_files.folder().parent / "upstream"  # beside the packs, outside every project


class Replays(Protocol):
    """The calibration replay: its candidate's session runs under *run*, and *keep* holds its scratch directory."""

    def __call__(
        self,
        store: Store,
        candidate: pack_candidate.Candidate | None,
        run: Callable[[Session], Run] | None = None,
        *,
        keep: Callable[[Path], bool] | None = None,
    ) -> Replay: ...


@dataclass
class Live:
    """What reaches outside: upstream, downloads, the browser, model sessions and git. Tests replace each."""

    package: Path = field(default_factory=lambda: Path(str(files("owlbear_delivery_next"))))
    clone: Path = field(default_factory=_upstream)
    releases: Callable[[str], bytes] | None = None  # the notice's release list; None reads GitHub
    sync: Callable[[Path, str], None] = pack_candidate.sync
    download: Callable[[str], bytes] = pack_files.fetch
    golden: Callable[..., dict[str, dict[str, list[str]]]] = pack_update.golden  # (installed, folder=None)
    replay: Replays = pack_replay.replay
    challenge: Callable[[Store, Session], Run] = sessions.run
    update: Callable[[Store, Session], Run] = sessions.run  # the writing updater (TD-125)
    git: pack_git.Git = pack_git.git
    github: Callable[[Path], Provider] = GhProvider
    sleep: Callable[[float], None] = time.sleep
    poll: float = 30.0  # seconds between looks at the pull request's checks
    ci_wait: float = 3600.0  # seconds CI may take at one head before the owner is asked
