"""Decided visual review rounds kept for calibration (TD-78, design skill research §3.5).

They live in the shared repository's project folder, outside every project: each round's verdicts and the owner's
decision are committed in ``<project>/visual/<change>-<round>/round.json``. Its screenshots stay beside it on this
machine only, excluded from git, and only for the last ``ROUNDS`` decided rounds; older rounds keep their verdicts.
"""

from __future__ import annotations

import re
import shutil
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.visual_records import Verdict, VisualRound
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo

FOLDER, RECORD = "visual", "round.json"
ROUNDS = 50  # decided rounds whose screenshots are kept
LEAST = 20  # replayed rounds below which a replay only informs the owner's choice
MARGIN = 10  # percentage points a new pack's design judge may agree with the owner less often than the old one did
PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")  # one path component: a project, a Change or a screenshot


def folder(shared: DataRepo, name: str) -> Path:
    """The project's calibration folder in the shared repository."""
    return shared.root / _part(name) / FOLDER


def keep(shared: DataRepo, name: str, slug: str, decided: VisualRound, images: Mapping[str, Path]) -> str:
    """Record one decided round and its screenshots, each under the name given, such as ``after-home-1280.png``.

    Returns what the owner should know if publishing failed.
    """
    if decided.decision is None:
        msg = "only a round the owner decided is kept for calibration"
        raise ValueError(msg)
    for image in images:
        if not image.endswith(".png") or _part(image) != image:
            msg = f"a screenshot is kept under a plain .png name, not {image!r}"
            raise ValueError(msg)
    target = folder(shared, name) / f"{_part(slug)}-{decided.number}"
    with shared.locked():
        target.mkdir(parents=True, exist_ok=True)
        atomic_write(target / RECORD, decided.model_dump_json(indent=2) + "\n")
        for image, source in images.items():
            shutil.copy2(source, target / image)
        for _old, kept in _cases(shared, name)[ROUNDS:]:
            for image in kept:
                image.unlink(missing_ok=True)
        return shared.publish(target / RECORD, f"visual: {slug} round {decided.number} decided")


def cases(shared: DataRepo, name: str, wait: float | None = None) -> list[tuple[VisualRound, list[Path]]]:
    """Every decided round of the project, newest decision first, with the screenshots still kept for it."""
    with shared.locked(wait):
        return _cases(shared, name)


def agreement(decided: Sequence[VisualRound]) -> list[dict[str, Any]]:
    """How often each judge, by lens and model, agreed with the owner's Pass or Fail (J6).

    The design judge counts twice: its final verdict, and its verdict before the detector's findings reached it.
    """
    rows: dict[tuple[str, str], Counter[str]] = {}
    for r in decided:
        owner = r.decision.outcome if r.decision else None
        for v in r.verdicts:
            said = [(v.lens, v.verdict), *([(f"{v.lens} before the detector", v.unanchored)] if v.unanchored else [])]
            for judge, verdict in said:
                counted = rows.setdefault((judge, v.model), Counter())
                counted["agreed" if verdict == owner else "unsure" if verdict == "unsure" else "disagreed"] += 1
    return [
        {"judge": judge, "model": model, "decided": c.total(), **{k: c[k] for k in ("agreed", "disagreed", "unsure")}}
        for (judge, model), c in sorted(rows.items())
    ]


@dataclass(frozen=True)
class Replay:
    """The design judge with a candidate pack, on decided rounds, against the verdicts recorded then (§3.5)."""

    rounds: int
    agreed_before: int  # recorded design verdicts that matched the owner's decision
    agreed_after: int  # replayed ones that did; a replay without a verified verdict did not
    left_out: int = 0  # kept rounds that could not be replayed: no screenshots, or inputs that do not match them
    pack: str = ""  # the identity of the pack the judge replayed with, as ``pack_files.identity`` names it

    @property
    def before(self) -> float:
        """The share of recorded design verdicts that agreed with the owner."""
        return self.agreed_before / self.rounds if self.rounds else 0.0

    @property
    def after(self) -> float:
        """The share of replayed design verdicts that agreed with the owner."""
        return self.agreed_after / self.rounds if self.rounds else 0.0

    @property
    def advisory(self) -> bool:
        """Too few rounds to hold an update back."""
        return self.rounds < LEAST

    @property
    def ok(self) -> bool:
        """The candidate may be activated as far as calibration goes."""
        return self.advisory or 100 * self.agreed_after >= 100 * self.agreed_before - MARGIN * self.rounds


def replayed(pairs: Sequence[tuple[VisualRound, Verdict | None]]) -> Replay:
    """Compare each decided round's replayed design verdict with the one it recorded."""
    decided = [(r.decision.outcome, r, v) for r, v in pairs if r.decision]
    recorded = [next((v.verdict for v in r.verdicts if v.lens == "design"), None) for _, r, _ in decided]
    before = sum(old == owner for old, (owner, _, _) in zip(recorded, decided, strict=True))
    return Replay(len(decided), before, sum(new == owner for owner, _, new in decided))


def _cases(shared: DataRepo, name: str) -> list[tuple[VisualRound, list[Path]]]:
    found = []
    for record in folder(shared, name).glob(f"*/{RECORD}"):
        decided = VisualRound.model_validate_json(record.read_text(encoding="utf-8"))
        found.append((decided, sorted(record.parent.glob("*.png"))))
    return sorted(found, key=lambda c: c[0].decision.at if c[0].decision else c[0].at, reverse=True)


def _part(text: str) -> str:
    if not PART.fullmatch(text) or text in {".", ".."}:
        msg = f"not a plain name: {text!r}"
        raise ValueError(msg)
    return text
