"""What the compaction reader takes from a session's log where no Metrics row would show it."""

import gzip
import json
from pathlib import Path

from owlbear_delivery_next.improvement import chatlogs
from owlbear_delivery_next.runtimes import compaction_logs
from owlbear_delivery_next.runtimes.compaction_logs import Actor, Log


def line(kind: str, **data: object) -> str:
    return json.dumps({"type": kind, "data": data, "id": "e", "timestamp": "2026-10-28T14:40:17.428Z"}) + "\n"


def compacted(attempt: str) -> list[str]:
    return [
        line("session.compaction_start", compactionAttemptId=attempt, trigger="threshold"),
        line("session.compaction_complete", success=True, outcome="applied", compactionAttemptId=attempt),
    ]


def test_the_live_log_wins_over_retros_copy() -> None:
    live = chatlogs.state() / "s1" / "events.jsonl"
    live.parent.mkdir(parents=True)
    live.write_text("".join([line("assistant.turn_start"), *compacted("a"), line("assistant.turn_start")]))
    copy = chatlogs.root() / "chatlogs" / "s1" / "log.jsonl.gz"
    copy.parent.mkdir(parents=True)
    with gzip.open(copy, "wt") as f:
        f.write(line("assistant.turn_start") * 5)
    assert compaction_logs.read("s1") == Log("found", Actor(calls=2, compactions=1, before=1))


def test_a_line_still_being_written_is_skipped_and_an_unchanged_log_is_not_read_again(monkeypatch) -> None:
    log = chatlogs.state() / "s2" / "events.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text("".join([line("assistant.turn_start"), *compacted("a"), '{"type":"assistant.turn_start","da']))
    opened = []
    real = Path.open
    with monkeypatch.context() as m:
        m.setattr(Path, "open", lambda self, *a, **k: opened.append(self) or real(self, *a, **k))
        first, again = compaction_logs.read("s2"), compaction_logs.read("s2")
    assert first == again == Log("found", Actor(calls=1, compactions=1, before=1))
    assert opened == [log]


def test_a_log_that_cannot_be_reached_is_unreadable_not_missing() -> None:
    folder = chatlogs.state() / "s3"
    folder.mkdir(parents=True)
    folder.chmod(0)
    try:
        found = compaction_logs.read("s3")
    finally:
        folder.chmod(0o700)
    assert found.state == "error"
    assert f"{folder / 'events.jsonl'}: PermissionError" in found.error
