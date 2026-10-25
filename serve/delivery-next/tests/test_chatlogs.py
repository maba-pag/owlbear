"""Retro chatlogs (Improvement design §5): manifest, capture, saved outputs, enrolled chats and pruning."""

import asyncio
import gzip
import json
import os
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import chatlogs, host_record, vscode_adapter
from owlbear_delivery_next.runtimes.session_result import Run


def _records(tmp_path: Path, session: str, lines: list[dict], cwd: str = "/work") -> Path:
    folder = tmp_path / "records" / session
    folder.mkdir(parents=True)
    (folder / "events.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    (folder / "workspace.yaml").write_text(f"id: {session}\ncwd: {cwd}\n")
    return tmp_path / "records"


def _saved(path: str) -> dict:
    text = f"Output too large to read at once (19.1 KB). Saved to: {path}\nConsider using tools like grep"
    return {"type": "tool.execution_complete", "data": {"result": {"content": text}}}


def _manifest() -> list[dict]:
    return [json.loads(x) for x in (chatlogs.root() / "manifest.jsonl").read_text().splitlines()]


def test_a_capture_keeps_the_log_gzipped_and_the_runtime_s_own_saved_outputs_only(tmp_path):
    temp = Path(tempfile.gettempdir())
    own = temp / f"{os.getpid()}-copilot-tool-output-abc.txt"
    own.write_text("the full output")
    elsewhere = tmp_path / "1-copilot-tool-output-x.txt"  # outside the temp folder: never copied
    elsewhere.write_text("private")
    linked = temp / f"{os.getpid()}-copilot-tool-output-link.txt"
    linked.unlink(missing_ok=True)
    linked.symlink_to(elsewhere)
    gone = temp / f"{os.getpid()}-copilot-tool-output-gone.txt"
    lines = [
        {"type": "session.start"},
        _saved(str(own)),
        _saved(str(elsewhere)),
        _saved(str(linked)),
        _saved(str(gone)),
    ]
    records = _records(tmp_path, "s1", lines)
    try:
        said = chatlogs.capture("s1", provisional=False, records=records)
    finally:
        own.unlink()
        linked.unlink()
    folder = chatlogs.root() / "chatlogs"
    with gzip.open(folder / "s1.jsonl.gz", "rt") as log:
        assert log.read() == (records / "s1" / "events.jsonl").read_text()
    assert [o["state"] for o in said["outputs"]] == ["kept", "refused", "refused", "missing"]
    with gzip.open(folder / "s1.outputs" / f"{own.name}.gz", "rt") as out:
        assert out.read() == "the full output"
    assert json.loads((folder / "s1.json").read_text()) == said
    modes = {p.name: p.stat().st_mode & 0o777 for p in (folder, folder / "s1.jsonl.gz", folder / "s1.json")}
    assert modes == {"chatlogs": 0o700, "s1.jsonl.gz": 0o600, "s1.json": 0o600}


def test_a_capture_is_a_snapshot_refreshed_when_the_log_grows_or_was_provisional(tmp_path):
    records = _records(tmp_path, "s2", [{"type": "session.start"}])
    first = chatlogs.capture("s2", provisional=True, records=records)
    again = chatlogs.capture("s2", provisional=False, records=records)  # provisional before: copied again
    assert (first["provisional"], again["provisional"]) == (True, False)
    assert chatlogs.capture("s2", provisional=False, records=records) == again  # final and unchanged: kept
    assert chatlogs.capture("s2", provisional=True, records=records)["provisional"]  # asked provisional: taken again
    again = chatlogs.capture("s2", provisional=False, records=records)
    with (records / "s2" / "events.jsonl").open("a") as log:
        log.write(json.dumps({"type": "session.resume"}) + "\n")  # the session resumed and wrote on
    grown = chatlogs.capture("s2", provisional=False, records=records)
    assert grown["size"] > again["size"]
    with gzip.open(chatlogs.root() / "chatlogs" / "s2.jsonl.gz", "rt") as log:
        assert "session.resume" in log.read()


def test_a_stopped_capture_leaves_no_partial_copy_and_a_later_one_takes_it_again(tmp_path, capsys, monkeypatch):
    records = _records(tmp_path, "s6", [{"type": "session.start"}])
    stop = threading.Event()
    stop.set()  # the step was cancelled, or the capture ran past its time
    with pytest.raises(chatlogs.Stopped):
        chatlogs.capture("s6", provisional=False, records=records, stop=stop)
    folder = chatlogs.root() / "chatlogs"
    assert sorted(p.name for p in folder.iterdir() if not p.name.startswith(".")) == []
    monkeypatch.setattr(chatlogs, "state", lambda: records)
    chatlogs.kept("s6", "finished", provisional=False, stop=stop)
    assert "s6 not captured (Stopped" in capsys.readouterr().err
    assert chatlogs.capture("s6", provisional=False, records=records)["size"] > 0


def test_a_saved_output_that_is_a_fifo_is_refused_without_blocking(tmp_path):
    fifo = Path(tempfile.gettempdir()) / f"{os.getpid()}-copilot-tool-output-fifo.txt"
    fifo.unlink(missing_ok=True)
    os.mkfifo(fifo)
    try:
        said = chatlogs.capture("s7", provisional=False, records=_records(tmp_path, "s7", [_saved(str(fifo))]))
    finally:
        fifo.unlink()
    assert [o["state"] for o in said["outputs"]] == ["refused"]


def test_a_capture_stopped_while_copying_outputs_publishes_nothing(tmp_path, monkeypatch):
    own = Path(tempfile.gettempdir()) / f"{os.getpid()}-copilot-tool-output-late.txt"
    own.write_text("x")
    stop, records = threading.Event(), _records(tmp_path, "s8", [_saved(str(own))])
    real = chatlogs._copy  # noqa: SLF001

    def stopping(src, target, limit, *rest):
        if limit is not None:  # an output, after the log: the step is cancelled now
            stop.set()
        return real(src, target, limit, *rest)

    monkeypatch.setattr(chatlogs, "_copy", stopping)
    try:
        with pytest.raises(chatlogs.Stopped):
            chatlogs.capture("s8", provisional=False, records=records, stop=stop)
    finally:
        own.unlink()
    assert not (chatlogs.root() / "chatlogs" / "s8.json").exists()  # no final snapshot to keep: taken again later
    assert not [p for p in (chatlogs.root() / "chatlogs").iterdir() if p.name.startswith(".stage")]


def test_a_stopped_refresh_keeps_the_previous_snapshot_whole(tmp_path, monkeypatch):
    own = Path(tempfile.gettempdir()) / f"{os.getpid()}-copilot-tool-output-refresh.txt"
    own.write_text("first")
    records = _records(tmp_path, "s9", [_saved(str(own))])
    try:
        first = chatlogs.capture("s9", provisional=True, records=records)
        with (records / "s9" / "events.jsonl").open("a") as log:
            log.write(json.dumps({"type": "session.resume"}) + "\n")
        own.write_text("second")
        stop, real = threading.Event(), chatlogs._copy  # noqa: SLF001

        def stopping(src, target, limit, *rest):
            if limit is not None:
                stop.set()
            return real(src, target, limit, *rest)

        monkeypatch.setattr(chatlogs, "_copy", stopping)
        with pytest.raises(chatlogs.Stopped):
            chatlogs.capture("s9", provisional=False, records=records, stop=stop)
    finally:
        own.unlink()
    folder = chatlogs.root() / "chatlogs"
    assert json.loads((folder / "s9.json").read_text()) == first
    with gzip.open(folder / "s9.jsonl.gz", "rt") as log:
        assert "session.resume" not in log.read()  # the log, too, as the sidecar says
    with gzip.open(folder / "s9.outputs" / f"{own.name}.gz", "rt") as out:
        assert out.read() == "first"


def test_a_session_without_a_record_is_said_missing(tmp_path):
    said = chatlogs.capture("nowhere", provisional=False, records=tmp_path)
    assert (said["missing"], (chatlogs.root() / "chatlogs" / "nowhere.json").exists()) == (True, True)


def _run(ending: str = "finished", *, confirmed: bool = True) -> Run:
    return Run("s3", ending, termination=Termination(confirmed=confirmed))


def test_a_session_runs_between_its_manifest_lines_and_is_captured_at_its_end(monkeypatch):
    taken = []
    monkeypatch.setattr(chatlogs, "capture", lambda s, *, provisional, **_k: taken.append((s, provisional)))

    async def step():
        return _run(confirmed=False)

    cfg = SimpleNamespace(
        session_id="s3", kind=SimpleNamespace(value="build"), role="builder", job="", worktree="/w/shop/c1"
    )
    done = asyncio.run(chatlogs.around(cfg, step()))
    events = _manifest()
    assert (done.ending, taken) == ("finished", [("s3", True)])  # unconfirmed termination: a provisional copy
    assert [(e["event"], e["session"]) for e in events] == [("started", "s3"), ("ended", "s3")]
    assert (events[0]["worktree"], events[0]["role"], events[1]["ending"]) == ("/w/shop/c1", "builder", "finished")
    assert chatlogs.sessions() == {"s3"}


def test_a_replacement_session_gets_its_own_owner_line(monkeypatch):
    monkeypatch.setattr(chatlogs, "capture", lambda *_a, **_k: None)

    async def step():
        return Run("s3-new", "finished", termination=Termination(confirmed=True))

    cfg = SimpleNamespace(session_id="s3", kind=SimpleNamespace(value="build"), role="builder", job="", worktree="/w")
    asyncio.run(chatlogs.around(cfg, step()))
    started = [e for e in _manifest() if e["event"] == "started"]
    assert [(e["session"], e.get("replaces")) for e in started] == [("s3", None), ("s3-new", "s3")]


@pytest.mark.parametrize("raised", [RuntimeError("runtime gone"), asyncio.CancelledError()])
def test_an_interrupted_session_gets_its_line_and_its_error_goes_on(monkeypatch, raised):
    monkeypatch.setattr(chatlogs, "capture", lambda *_a, **_k: pytest.fail("no capture while interrupted"))

    async def step():
        raise raised

    cfg = SimpleNamespace(session_id="s4", kind=SimpleNamespace(value="review"), role="", job="", worktree="/w")
    with pytest.raises(type(raised)):
        asyncio.run(chatlogs.around(cfg, step()))
    assert [(e["event"], e.get("ending")) for e in _manifest()] == [("started", None), ("ended", "interrupted")]


def test_an_interrupted_replacement_gets_its_owner_line_and_the_interruption(monkeypatch):
    monkeypatch.setattr(chatlogs, "capture", lambda *_a, **_k: pytest.fail("no capture while interrupted"))

    async def step():
        raise asyncio.CancelledError

    cfg = SimpleNamespace(session_id="s4", kind=SimpleNamespace(value="build"), role="builder", job="", worktree="/w")
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(chatlogs.around(cfg, step(), lambda: "s4-new"))
    assert [(e["event"], e["session"], e.get("replaces")) for e in _manifest()] == [
        ("started", "s4", None), ("started", "s4-new", "s4"), ("ended", "s4-new", None)]  # fmt: skip


def test_a_failing_capture_never_fails_the_step(monkeypatch, capsys):
    def broken(*_a, **_k):
        raise OSError(28, "disk full")

    monkeypatch.setattr(chatlogs, "capture", broken)
    chatlogs.kept("s5", "finished", provisional=False)
    assert "s5 not captured (OSError: [Errno 28] disk full)" in capsys.readouterr().err
    assert _manifest()[-1]["session"] == "s5"


def test_a_window_step_maps_its_session_to_the_host_s_record(monkeypatch):
    taken = []
    monkeypatch.setattr(chatlogs, "capture", lambda s, *, provisional, **_k: taken.append((s, provisional)))
    found = host_record.Record(found=True, tools=[], session="host-7")
    vscode_adapter._kept("step-1", found, _run())  # noqa: SLF001
    unmatched = host_record.Record(found=False, why="2 host records match the step")
    vscode_adapter._kept("step-2", unmatched, _run())  # noqa: SLF001
    events = _manifest()
    assert (taken, events[0], events[2]["why"]) == (
        [("host-7", False)], events[0] | {"event": "mapped", "session": "step-1", "record": "host-7"},
        "2 host records match the step")  # fmt: skip


def test_the_host_record_names_its_own_session(tmp_path):
    start = datetime.now(UTC) - timedelta(seconds=1)
    began = {"context": {"cwd": str(tmp_path)}, "startTime": datetime.now(UTC).isoformat()}
    events = [{"type": "session.start", "data": began},
              {"type": "subagent.selected", "data": {"agentName": "owlbear-builder", "tools": ["edit"]}}]  # fmt: skip
    records = _records(tmp_path, "host-9", events)
    assert host_record.read(tmp_path, start, "owlbear-builder", records).session == "host-9"


def test_only_chats_in_an_enrolled_folder_are_read(tmp_path):
    work = tmp_path / "work"
    (work / "sub").mkdir(parents=True)
    (tmp_path / "workshop").mkdir()
    link = tmp_path / "link"
    link.symlink_to(work)
    assert chatlogs.enrolled(str(work / "sub"), [str(work)])
    assert chatlogs.enrolled(str(work), [str(link)])  # a linked folder is the folder itself
    assert not chatlogs.enrolled(str(tmp_path / "workshop"), [str(work)])  # a prefix is not a folder
    assert not chatlogs.enrolled(str(work), [])
    assert not chatlogs.enrolled("", [str(Path.cwd())])  # unreadable metadata never enrols, even here
    assert not chatlogs.enrolled("work", [str(Path.cwd())])


def test_finished_chats_are_quiet_for_a_day_enrolled_and_never_owlbear_s_own(tmp_path):
    work, now = tmp_path / "work", datetime.now(UTC)
    work.mkdir()
    records = None
    for sid, cwd in (("old", work), ("new", work), ("other", tmp_path / "elsewhere"), ("ours", work)):
        records = _records(tmp_path, sid, [{"type": "session.start"}], str(cwd))
    day_ago = (now - timedelta(days=2)).timestamp()
    for sid in ("old", "other", "ours"):
        os.utime(records / sid / "events.jsonl", (day_ago, day_ago))
    chatlogs.note({"event": "started", "session": "ours"})  # a Delivery or curation session, not a chat
    assert list(chatlogs.finished_chats([str(work)], now, records)) == ["old"]
    assert list(chatlogs.finished_chats([], now, records)) == []  # none enrolled: none read


def test_only_judged_unpinned_sessions_a_month_old_are_pruned(tmp_path):
    records = _records(tmp_path, "a", [{"type": "session.start"}])
    for sid in ("a", "b", "c", "d"):
        (records / sid).mkdir(exist_ok=True)
        (records / sid / "events.jsonl").write_text("{}\n")
        chatlogs.capture(sid, provisional=False, records=records)
    now = datetime.now(UTC)
    judged = {"a": now - timedelta(days=31), "b": now - timedelta(days=31), "c": now - timedelta(days=2)}
    assert chatlogs.prune(now, judged, pinned={"b"}) == ["a"]
    left = sorted(p.name for p in (chatlogs.root() / "chatlogs").iterdir() if not p.name.startswith("."))
    assert left == ["b.json", "b.jsonl.gz", "c.json", "c.jsonl.gz", "d.json", "d.jsonl.gz"]  # d: never judged
