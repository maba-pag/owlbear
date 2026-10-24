"""The watcher's shell effects over a corpus of commands agents run (W1b-1): exact effects and the unresolved budget."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts import watch_effects
from owlbear_delivery_next.change_contracts.watch_policy import Places, reported

CORPUS = json.loads((Path(__file__).parent / "fixtures" / "watch_corpus.json").read_text(encoding="utf-8"))
FOLDERS = ("src", "tests", "docs", "dist", "build", "packages/app", "templates")


@pytest.fixture(scope="module")
def machine(tmp_path_factory):
    """A fake worktree with the corpus's folders, a home with its caches, and a temporary folder."""
    root = tmp_path_factory.mktemp("corpus")
    own, home, tmp = root / "wt", root / "home", root / "T"
    for folder in [*(own / f for f in FOLDERS), home / ".cache", tmp]:
        folder.mkdir(parents=True)
    places = Places((), (), (tmp, home / ".cache"), home, tmp).resolved()
    return own.resolve(), home, tmp, places


def expected(path: str, own: Path, home: Path) -> str:
    if path.startswith("~/"):
        return str(home.resolve() / path[2:])
    return os.path.realpath(path) if path.startswith("/") else str(own / path)


def found(command: str, own: Path, home: Path, tmp: Path) -> watch_effects.Effects:
    return watch_effects.effects(command, watch_effects.Shell(own, home, tmp))


@pytest.mark.parametrize("entry", CORPUS["commands"], ids=lambda e: e["command"][:60])
def test_each_corpus_command_has_exactly_its_expected_effects(machine, entry) -> None:
    own, home, tmp, places = machine
    effects = found(entry["command"], own, home, tmp)
    targets = [[t.kind, str(t.path)] for t in effects.targets]
    assert targets == [[kind, expected(p, own, home)] for kind, p in entry["targets"]]
    assert list(effects.unresolved) == [getattr(watch_effects, r) for r in entry["unresolved"]]
    if entry.get("inside", True):  # work in the worktree identifies nothing outside it
        assert all(t.path.is_relative_to(own) for t in effects.targets)
        assert not any(reported(t.path, own, places) for t in effects.targets)


def test_the_unresolved_reasons_stay_within_the_recorded_budget(machine) -> None:
    own, home, tmp, _ = machine
    names = {getattr(watch_effects, n): n for n in CORPUS["budget"]}
    counts = Counter(
        names.get(r, r) for e in CORPUS["commands"] for r in found(e["command"], own, home, tmp).unresolved
    )
    sys.stdout.write(f"\nwatch corpus: {len(CORPUS['commands'])} commands, unresolved per reason {dict(counts)}\n")
    over = {r: n for r, n in counts.items() if n > CORPUS["budget"].get(r, 0)}
    assert not over, f"unresolved reasons over the budget {CORPUS['budget']}: {over}"
    assert len(CORPUS["commands"]) >= 80
