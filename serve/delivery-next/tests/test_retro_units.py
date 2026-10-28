"""Retro's units (#715): a Change's sessions and gaps, a chat's revisions, and which records each one grades."""

import gzip
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from owlbear_delivery_next.improvement import retro_store, retro_units, spotter
from owlbear_delivery_next.runtimes import chatlogs

LATER = datetime.now(UTC) + timedelta(days=2)


def _record(rid, cutoff, **more):
    line = {
        "id": rid,
        "at": "2026-01-01T00:00:00+00:00",
        "look": "handoff",
        "call": "c",
        "cutoff": cutoff,
        "category": "none",
        **more,
    }
    folder = spotter.root()
    with (folder / "records-2026-01-01.jsonl").open("a") as out:
        out.write(json.dumps(line) + "\n")
    (folder / "cards" / f"{rid}.json.gz").write_bytes(gzip.compress(b"{}"))


def _note(**line):
    chatlogs.root().mkdir(parents=True, exist_ok=True)
    with (chatlogs.root() / "manifest.jsonl").open("a") as out:
        out.write(json.dumps(line) + "\n")


def _captured(session, events, **sidecar):
    folder = retro_units.folder(session)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "log.jsonl.gz").write_bytes(gzip.compress("".join(json.dumps(e) + "\n" for e in events).encode()))
    (folder / "sidecar.json").write_text(
        json.dumps({"session": session, "provisional": False, "outputs": [], **sidecar})
    )


def _event(kind, **data):
    return {"type": kind, "data": data}


def test_a_changes_sessions_reviewers_and_replacements_are_its_own_and_each_gap_is_named(tmp_path):
    place = str(tmp_path / "data" / "repo-1111" / "fix-it")
    other = str(tmp_path / "data" / "repo-2222" / "fix-it")
    _note(event="started", session="s-build", worktree=place, role="builder")
    _note(event="started", session="s-rev", worktree=place + ".ro", role="reviewer")
    _note(event="started", session="s-new", worktree=place, replaces="s-build", role="builder")
    _note(event="started", session="s-other", worktree=other, role="builder")
    _note(event="ended", session="s-build", provisional=False)
    _captured(
        "s-build",
        [_event("skill.invoked", name="w-build"), _event("tool.execution_start", toolName="edit")],
        outputs=[{"path": str(tmp_path / "copilot-tool-output-1.txt"), "state": "missing"}],
    )
    _captured("s-new", [_event("subagent.started", agentName="explore")], provisional=True)
    _record("rec-1", 4, project="p1", change="fix-it", step="build", session="s-build")
    (spotter.place() / "cards" / "rec-1.json.gz").unlink()
    change = SimpleNamespace(finished_at=datetime.now(UTC), names=SimpleNamespace(worktree=place))
    st = SimpleNamespace(
        root=Path("/x/p1"), slugs=lambda: ["fix-it"], read=lambda _s: change, events=lambda _s: [{}] * 200
    )

    rev = retro_units.freeze({"unit": "chg:p1:fix-it", "rev": ""}, {"p1": (st, None)}, retro_units.records())

    unit = retro_store.units()["chg:p1:fix-it"]
    assert unit["sessions"] == ["s-build", "s-rev", "s-new"]
    assert unit["exposure"] == ["agent:builder", "agent:explore", "agent:reviewer", "skill:w-build", "tool:edit"]
    assert unit["gaps"] == [
        retro_units.SHAPING,
        "output copilot-tool-output-1.txt of session s-build: missing",
        "session s-rev has no capture",
        "session s-new's end was not confirmed; its capture may be incomplete",
        "the Change's activity keeps only its last 200 events",
        "record rec-1's card is missing",
    ]
    assert (rev["rev"], rev["records"], unit["family"]) == ("r1", ["rec-1"], "chg:p1:fix-it")


class _Chat:
    def __init__(self, tmp_path):
        self.folder = tmp_path / "enrolled"
        self.folder.mkdir()
        self.log = chatlogs.state() / "c1" / "events.jsonl"
        self.log.parent.mkdir(parents=True)
        (self.log.parent / "workspace.yaml").write_text(f"cwd: {self.folder}\n")
        self.log.write_text("")

    def say(self, *events):
        with self.log.open("a") as out:
            for e in events:
                out.write(json.dumps(e) + "\n")
        os.utime(self.log, (self.log.stat().st_atime, self.log.stat().st_mtime + 1))

    def due(self, **kw):
        return retro_units.due_chats([str(self.folder)], LATER, **kw)


def _judged(rev, *graded):
    retro_store.add_grades([{"id": f"rg-{r}", "record": r, "grade": "worth-it"} for r in graded])
    retro_units.settle("chat:c1", rev["rev"], "judged", run="run-x")


def test_a_chat_revision_takes_only_new_events_and_records_and_a_late_record_makes_a_grade_only_run(tmp_path):
    retro_store.watermark()
    chat = _Chat(tmp_path)
    chat.say(
        _event("user.message", content="go"),
        _event("assistant.message", content="ok"),
        _event("tool.execution_start", toolName="bash"),
    )
    _record("a", 2, step="chat", session="c1")
    [item] = chat.due()
    r1 = retro_units.freeze(item, {}, retro_units.records())
    chat.say(
        {"type": "tool.execution_start", "agentId": "sub", "data": {"toolName": "grep"}},
        _event("assistant.message", content="done"),
    )
    _record("c", 4, step="chat", session="c1")  # beyond r1's cutoff: the next revision's
    _record("d", 3, step="chat", session="c1")  # r1's, written after r1 was taken
    _record("g", 0, step="chat", session="c1", skipped="the log was replaced")
    assert (r1["from_events"], r1["cutoff_events"], r1["records"]) == (0, 3, ["a"])
    assert chat.due() == []  # r1's run has not ended
    _judged(r1, "a")
    known, found, graded = retro_store.units(), retro_units.records(), retro_store.graded()
    assert retro_units.late(found, known, graded) == [
        {"unit": "chat:c1", "rev": "r1", "mode": "grade-only", "records": ["d"]}
    ]
    [gap] = retro_units.gap_grades(found, known, graded)
    assert (gap["id"], gap["grade"], gap["reason"]) == ("rg-g", "not-assessable", "the log was replaced")
    [item] = chat.due()
    r2 = retro_units.freeze(item, {}, found)
    assert (r2["rev"], r2["from_events"], r2["cutoff_events"], r2["records"]) == ("r2", 3, 5, ["c"])
    assert retro_store.units()["chat:c1"]["family"] == "chat:c1"


def test_a_new_gap_record_alone_is_graded_without_a_run(tmp_path):
    retro_store.watermark()
    chat = _Chat(tmp_path)
    chat.say(_event("user.message", content="go"))
    [item] = chat.due()
    _judged(retro_units.freeze(item, {}, []))
    _record("g", 0, step="chat", session="c1", skipped="not followed")
    assert chat.due() == []
    known, found = retro_store.units(), retro_units.records()
    assert [g["id"] for g in retro_units.gap_grades(found, known, retro_store.graded())] == ["rg-g"]
    assert retro_units.late(found, known, retro_store.graded()) == []


def test_a_chat_quiet_since_before_the_watermark_waits_for_the_button(tmp_path):
    chat = _Chat(tmp_path)
    chat.say(_event("user.message", content="go"))
    os.utime(chat.log, (0, 0))
    retro_store.watermark()
    assert chat.due() == []
    assert not retro_units.folder("c1").exists()
    assert chat.due(chat="c1") == [{"unit": "chat:c1", "rev": "", "mode": "judge"}]


def test_eligibility_refuses_owlbears_own_sessions_unenrolled_chats_and_unfinished_changes(tmp_path):
    chat = _Chat(tmp_path)
    assert retro_units.eligible("chat:c1", [str(chat.folder)], {}) == ""
    assert retro_units.eligible("chat:c1", [], {}) == "it is not an enrolled chat"
    _note(event="started", session="c1", worktree="/w")
    assert retro_units.eligible("chat:c1", [str(chat.folder)], {}) == "it is one of OwlBear's own sessions"
    st = SimpleNamespace(read=lambda _s: SimpleNamespace(finished_at=None))
    assert retro_units.eligible("chg:p1:x", [], {"p1": (st, None)}) == "it is not finished"
