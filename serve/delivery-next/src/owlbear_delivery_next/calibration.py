"""Decided visual review rounds kept for calibration (TD-78, design skill research §3.5).

They live in the shared repository's project folder, outside every project: each round's verdicts and the owner's
decision are committed in ``<project>/visual/<change>-<round>/round.json``. Its screenshots stay beside it on this
machine only, excluded from git, and only for the last ``ROUNDS`` decided rounds; older rounds keep their verdicts.
"""

from __future__ import annotations

import re
import shutil
from collections import Counter
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.storage_io import atomic_write
from owlbear_delivery_next.visual_records import VisualRound

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from owlbear_delivery_next.common import Common

FOLDER, RECORD = "visual", "round.json"
ROUNDS = 50  # decided rounds whose screenshots are kept
PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")  # one path component: a project, a Change or a screenshot


def folder(shared: Common, name: str) -> Path:
    """The project's calibration folder in the shared repository."""
    return shared.root / _part(name) / FOLDER


def keep(shared: Common, name: str, slug: str, decided: VisualRound, images: Mapping[str, Path]) -> str:
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


def cases(shared: Common, name: str, wait: float | None = None) -> list[tuple[VisualRound, list[Path]]]:
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


def _cases(shared: Common, name: str) -> list[tuple[VisualRound, list[Path]]]:
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
