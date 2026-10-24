"""The watcher's SDK feed (W1a): observations from deserialised SDK events, identity, the switch and the teardown."""

from __future__ import annotations

import asyncio
import dataclasses
import json
import subprocess
import threading
import uuid
from functools import partial
from types import SimpleNamespace
from typing import Any, ClassVar

import pytest
from copilot.generated.session_events import PermissionRequestWrite, SessionEvent

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.change_contracts.watch_effects import PROGRAM
from owlbear_delivery_next.change_contracts.watch_policy import Places
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import sdk_adapter, sdk_teardown, sdk_usage, watch_feed
from owlbear_delivery_next.settings.config import Layer, SettingsUnset, resolve
from owlbear_delivery_next.state_store import project_home, watch_reports
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import sessions, watched

SHELL_UNRESOLVED = f"unresolved ({PROGRAM})"  # make: W1b-1 does not follow it
OUTSIDE = "outside write (not judged yet)"


def event(kind: str, data: dict[str, Any], *, agent: str | None = None, second: int = 0) -> SessionEvent:
    raw = {"id": str(uuid.uuid4()), "timestamp": f"2026-10-24T10:00:{second:02d}.000Z", "type": kind, "data": data}
    return SessionEvent.from_dict(raw | ({"agentId": agent} if agent else {}))


def start(cid: str, tool: str = "bash", *, parent: str | None = None, second: int = 0, **kw: Any) -> SessionEvent:
    args = {"command": f"make {cid}"} if tool == "bash" else {"path": kw.pop("path", "x.py")}
    data = {"toolCallId": cid, "toolName": tool, "arguments": args}
    data |= {"shellToolInfo": {"hasWriteFileRedirection": False, "possiblePaths": []}} if tool == "bash" else {}
    return event("tool.execution_start", data | ({"parentToolCallId": parent} if parent else {}), second=second, **kw)


def shell(cid: str, *, read_only: bool, redirect: bool = False, second: int = 0, **kw: Any) -> SessionEvent:
    request = {"kind": "shell", "toolCallId": cid, "canOfferSessionApproval": False, "fullCommandText": f"make {cid}",
               "commands": [{"identifier": "make", "readOnly": read_only}], "hasWriteFileRedirection": redirect,
               "intention": "build", "possiblePaths": [], "possibleUrls": []}  # fmt: skip
    return event("permission.requested", {"requestId": f"r-{cid}", "permissionRequest": request}, second=second, **kw)


def write(cid: str, path: str, **kw: Any) -> SessionEvent:
    request = {"kind": "write", "toolCallId": cid, "canOfferSessionApproval": False, "diff": "", "fileName": path,
               "intention": "edit"}  # fmt: skip
    return event("permission.requested", {"requestId": f"w-{cid}", "permissionRequest": request}, **kw)


def launched(launcher: str, name: str, **kw: Any) -> SessionEvent:
    data = {"toolCallId": launcher, "agentName": name, "agentDisplayName": name, "agentDescription": ""}
    return event("subagent.started", data, **kw)


@pytest.fixture
def place(tmp_path) -> SimpleNamespace:
    own, elsewhere = tmp_path / "worktrees" / "c1", tmp_path / "elsewhere"
    own.mkdir(parents=True)
    elsewhere.mkdir()
    store = Store(tmp_path / "store")
    store.db.check()
    notes: list[str] = []
    places = Places((tmp_path / "worktrees",), (), (), tmp_path / "home", None)  # pytest's own folders are exempt
    writer = partial(watch_reports.Writer, store.db, Lock("c1"), note=notes.append)
    watching = watch_feed.Watching("c1", "build", places, writer)
    return SimpleNamespace(own=own, elsewhere=elsewhere.resolve(), store=store, notes=notes, watching=watching)


def config(place, *, watch: bool = True, **kw: Any) -> sdk_adapter.Session:
    made = sdk_adapter.Session(
        StepKind.BUILD, place.own, "s1", "m", resume=False, policy=Policy(place.own),
        observe=lambda: Worktree("a", "a"), checks=(), subagents=True, model="gpt-6-luna",
        watch=place.watching if watch else None,
    )  # fmt: skip
    return dataclasses.replace(made, **kw)


def stepped(place, *events: SessionEvent, close: bool = True, **kw: Any) -> sdk_adapter._Step:
    """A step's event handler with its watcher, opened as ``sdk_adapter.run`` opens it."""
    cfg = config(place, **kw)
    st = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    st.feed = watch_feed.opened(cfg.watch, cfg.worktree, lambda: st.run.session_id, st.watch)
    for ev in events:
        st.on_event(ev)
    if close and st.feed is not None:
        st.feed.close()
    return st


def rows(place) -> dict[str, dict[str, Any]]:
    return {r["call_id"]: r for r in watch_reports.reports(place.store.db, "c1")}


def threads() -> list[threading.Thread]:
    """The writer threads alive that this test started."""
    return [t for t in threading.enumerate() if t.name.startswith("watch-") and t not in BEFORE]


BEFORE: set[threading.Thread] = set()


@pytest.fixture(autouse=True)
def _baseline() -> None:
    BEFORE.clear()
    BEFORE.update(threading.enumerate())


def test_a_call_is_one_observation_whichever_comes_first_its_start_or_its_permission_request(place) -> None:
    stepped(
        place,
        start("c1", second=1), shell("c1", read_only=True, second=2),  # proven read-only: its row goes again
        shell("c2", read_only=True, second=3), start("c2", second=4),
        start("c3", second=5), shell("c3", read_only=False, second=6),
        shell("c4", read_only=False, second=7), start("c4", second=8),
        start("c5", second=9),  # no permission request ever: judged on its start alone
    )  # fmt: skip
    found = rows(place)
    assert sorted(found) == ["c3", "c4", "c5"]
    assert [found[c]["at"] for c in ("c3", "c4", "c5")] == [f"2026-10-24T10:00:0{s}.000+00:00" for s in (5, 8, 9)]
    assert [found[c]["source"] for c in ("c3", "c4", "c5")] == ["enriched", "enriched", "start"]
    assert {r["verdict"] for r in found.values()} == {SHELL_UNRESOLVED}
    assert found["c3"]["command"] == "ran make c3"
    assert watch_reports.counts(place.store.db, "c1") == {"outside": 0, "unresolved": 3}
    assert not threads()


def test_repeated_enrichment_reclassifies_the_one_row_and_read_only_evidence_covers_only_the_shell(place) -> None:
    outside = str(place.elsewhere / "out.txt")
    stepped(place, start("c1"), shell("c1", read_only=True), write("c1", outside), shell("c2", read_only=False),
            write("c2", outside), start("c2"))  # fmt: skip
    found = rows(place)
    assert (found["c1"]["targets"], found["c1"]["unresolved"], found["c1"]["verdict"]) == ([outside], "", OUTSIDE)
    assert (found["c2"]["targets"], found["c2"]["unresolved"]) == ([outside], PROGRAM)
    assert watch_reports.counts(place.store.db, "c1") == {"outside": 2, "unresolved": 1}


def test_a_file_tools_writes_are_reported_by_their_canonical_path_and_its_own_folder_is_not(place) -> None:
    stepped(place, start("e1", "edit", path="src/a.py"), start("e2", "edit", path="../../elsewhere/b.py"),
            start("v1", "view", path="/etc/hosts"))  # fmt: skip
    assert list(rows(place)) == ["e2"]
    assert rows(place)["e2"]["targets"] == [str(place.elsewhere / "b.py")]
    assert rows(place)["e2"]["tool"] == "edit"


def test_the_agent_is_the_events_else_the_subagent_its_parent_call_launched_else_the_steps_own(place) -> None:
    stepped(
        place,
        start("m1"),  # the main agent's events carry no ids and no parent call: the step's own agent (TD-94)
        launched("t1", "explore"), start("s1", parent="t1"),  # launched by the main agent's task call
        launched("t2", "general-purpose", agent="a-explore"), start("s2", parent="t2", agent="a-general"),
        start("s3", parent="t2"),  # nested: launched by the explore subagent's own task call
        start("s4", agent="t1"),  # an agent id that names a launcher
        start("s5", parent="t9"), launched("t9", "rubber-duck"),  # its launch announced after its first call
        shell("s5", read_only=False),
        start("s6", parent="gone"),
    )  # fmt: skip
    found = {c: r["agent"] for c, r in rows(place).items()}
    assert found == {"m1": "main", "s1": "explore", "s2": "a-general", "s3": "general-purpose", "s4": "explore",
                     "s5": "rubber-duck", "s6": "unknown"}  # fmt: skip


def test_a_permission_request_without_a_call_id_is_a_call_of_its_own(place) -> None:
    outside = str(place.elsewhere / "x.txt")
    request = {"kind": "write", "canOfferSessionApproval": False, "diff": "", "fileName": outside, "intention": "e"}
    stepped(place, event("permission.requested", {"requestId": "w9", "permissionRequest": request}))
    assert [(c, r["targets"], r["source"]) for c, r in rows(place).items()] == [("request w9", [outside], "permission")]


def test_events_after_the_intake_closed_are_counted_never_written(place) -> None:
    st = stepped(place, start("c1"))
    st.on_event(shell("c1", read_only=True))
    st.on_event(start("c2"))
    assert (list(rows(place)), st.feed.writer.dropped) == (["c1"], 2)


def test_with_the_master_switch_off_there_is_no_watcher_and_nothing_is_recorded(place, change_repo) -> None:
    st = stepped(place, start("c1"), write("c1", str(place.elsewhere / "x")), watch=False)
    assert (st.feed, rows(place), threads()) == (None, {}, [])
    store, lock = place.store, Lock("c1")
    assert watched.watching(store, lock, "build", resolve(None, Layer(watcher=False)), change_repo, print) is None
    unset = resolve(None, Layer())
    unset.missing.append("watcher")
    with pytest.raises(SettingsUnset, match="watcher"):
        watched.watching(store, lock, "build", unset, change_repo, print)
    on = watched.watching(store, lock, "plan", resolve(None, Layer(watcher=True)), change_repo, print)
    assert (on.slug, on.step, on.places.mine) == ("c1", "plan", (store.root / "changes" / "c1",))
    assert on.places.guarded[:2] == (worktree.data_root(), store.root / "changes")
    assert on.places.guarded[-2:] == (change_repo, change_repo / ".git")
    assert store.root in on.places.exempt


def test_a_run_closes_its_watcher_after_the_teardown_and_its_outcome_and_guard_are_unchanged(
    place, monkeypatch
) -> None:
    outside = str(place.elsewhere / "secret.txt")

    class Session:
        def __init__(self, opts: dict[str, Any]) -> None:
            self.opts = opts
            self.rpc = SimpleNamespace(usage=SimpleNamespace(get_metrics=self.metrics))

        async def metrics(self) -> None:
            raise RuntimeError

        async def send(self, *_a, **_k) -> None:
            self.opts["on_event"](start("c1", "edit", path=outside))
            request = PermissionRequestWrite.from_dict(write("c1", outside).to_dict()["data"]["permissionRequest"])
            Client.decided.append(type(self.opts["on_permission_request"](request, None)).__name__)
            self.opts["on_event"](write("c1", outside))

    class Client:
        decided: ClassVar[list[str]] = []
        sessions: ClassVar[list[Session]] = []

        def __init__(self, **_k) -> None:
            pass

        async def start(self) -> None:
            pass

        async def create_session(self, **opts) -> Session:
            Client.sessions.append(Session(opts))
            return Client.sessions[-1]

    async def teardown(_client, session, _st) -> Termination:
        session.opts["on_event"](start("c2"))  # a call the runtime reports while it is stopped
        return Termination(confirmed=True)

    monkeypatch.setattr(sdk_adapter, "CopilotClient", Client)
    monkeypatch.setattr(sdk_adapter, "cli_path", lambda: "copilot")
    monkeypatch.setattr(sdk_teardown, "teardown", teardown)
    monkeypatch.setattr(sdk_usage, "USAGE_PAUSE", 0)
    read_only = Policy(place.own, write=False)
    ran = [asyncio.run(sdk_adapter.run(config(place, watch=w, limit=0.2, policy=read_only))) for w in (True, False)]
    assert not threads()  # no writer outlives its run
    assert [(r.ending, r.denials, r.termination) for r in ran[:1]] == [(r.ending, r.denials, r.termination)
                                                                       for r in ran[1:]]  # fmt: skip
    assert Client.decided == ["PermissionDecisionReject", "PermissionDecisionReject"]
    found = rows(place)
    assert (found["c1"]["targets"], found["c1"]["source"], found["c1"]["step"]) == ([outside], "enriched", "build")
    assert found["c2"]["verdict"] == SHELL_UNRESOLVED
    refused = asyncio.run(sdk_adapter.run(dataclasses.replace(config(place), model=None)))
    assert (refused.ending, threads()) == ("error", [])


class _MadeError(Exception):
    pass


def test_a_judges_session_is_watched_in_the_folder_it_runs_in(place, tmp_path, monkeypatch) -> None:
    built: list[sdk_adapter.Session] = []

    def isolated(_store, _lock, _change, _source, make, _go, **_kw):
        built.extend(make(tmp_path / "read-only"))
        raise _MadeError

    monkeypatch.setattr(sessions, "isolated", isolated)
    with pytest.raises(_MadeError):
        sessions.judges(place.store, Lock("c1"), None, place.own, lambda _at: [("review", config(place, watch=False))])
    (cfg,) = built
    assert (cfg.worktree, cfg.watch.slug, cfg.watch.step) == (tmp_path / "read-only", "c1", "review")


def test_a_call_seen_only_in_a_permission_request_is_its_owners_or_unknown_never_main(place) -> None:
    outside = str(place.elsewhere / "x")
    owned = write("p1", outside)
    owned.data.owner_agent_id = "subagent-7"
    stepped(place, owned, write("p2", outside))
    assert {c: r["agent"] for c, r in rows(place).items()} == {"p1": "subagent-7", "p2": "unknown"}


def test_a_cancelled_run_waits_until_its_watcher_closed_then_is_cancelled() -> None:
    release, closed = threading.Event(), threading.Event()
    feed = SimpleNamespace(close=lambda: (release.wait(5), closed.set()))

    async def work() -> str:
        return "done"

    async def main() -> None:
        task = asyncio.ensure_future(watch_feed.around(feed, work()))
        await asyncio.sleep(0.05)  # the work returned; the watcher is closing
        for _ in range(2):  # cancelled twice while it closes
            task.cancel()
            await asyncio.sleep(0.05)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert closed.is_set()

    asyncio.run(main())


def test_a_checkout_whose_git_folder_lives_elsewhere_is_guarded_with_it(place, tmp_path) -> None:
    checkout, meta = tmp_path / "tmp" / "project", tmp_path / "metadata" / "project.git"
    meta.parent.mkdir()
    subprocess.run(["git", "init", "-q", f"--separate-git-dir={meta}", str(checkout)], check=True)  # noqa: S603, S607
    listed = {"projects": [{"id": place.store.root.name, "path": str(checkout), "added_at": "2026-10-24"}]}
    (local_home.root() / project_home.MACHINE).write_text(json.dumps(listed))  # Git cannot name such a checkout
    on = watched.watching(place.store, Lock("c1"), "build", resolve(None, Layer(watcher=True)), checkout, print)
    assert {checkout.resolve(), meta.resolve()} <= {p.resolve() for p in on.places.guarded}


def test_a_call_reported_before_its_launcher_was_announced_gets_its_subagent_without_another_event(place) -> None:
    outside = str(place.elsewhere / "y.py")
    stepped(place, start("e7", "edit", parent="t8", path=outside), launched("t8", "explore"))
    assert rows(place)["e7"]["agent"] == "explore"


def test_a_shell_call_seen_only_in_its_permission_request_shows_its_whole_command(place) -> None:
    stepped(place, shell("p3", read_only=False))
    assert rows(place)["p3"]["command"] == "ran make p3"


def ran(cid: str, command: str, *, second: int = 0, shell_id: str | None = None) -> SessionEvent:
    args = {"command": command, "description": "x"} | ({"shellId": shell_id} if shell_id else {})
    data = {"toolCallId": cid, "toolName": "bash", "arguments": args,
            "shellToolInfo": {"hasWriteFileRedirection": ">" in command, "possiblePaths": []}}  # fmt: skip
    return event("tool.execution_start", data, second=second)


def asking(
    cid: str, text: str, *, cwd: str | None = None, read_only: tuple[str, ...] = (), second: int = 0
) -> SessionEvent:
    segments = [{"identifier": " ".join(s.split()[:2]), "fullCommandText": s} for s in text.split(" && ")]
    commands = [{"identifier": s["identifier"], "readOnly": s["identifier"] in read_only} for s in segments]
    request = {"kind": "shell", "toolCallId": cid, "canOfferSessionApproval": False, "fullCommandText": text,
               "commands": commands, "commandSegments": segments, "hasWriteFileRedirection": ">" in text,
               "intention": "work", "possiblePaths": ["out.txt"], "possibleUrls": [],
               "resolvedPaths": {"out.txt": "/abs/out.txt"}}  # fmt: skip
    request |= {"resolvedWorkingDirectory": cwd} if cwd else {}
    return event("permission.requested", {"requestId": f"r-{cid}", "permissionRequest": request}, second=second)


def test_a_shell_request_keeps_the_runtimes_command_text_segments_paths_and_working_directory() -> None:
    request = asking("c1", "cd sub && git status --short", cwd="/w", read_only=("git status",)).data.permission_request
    found = watch_feed.asked(request)
    assert (found.kind, found.full_command_text, found.resolved_working_directory) == (
        "shell", "cd sub && git status --short", "/w",
    )  # fmt: skip
    assert found.command_segments == (("cd sub", "cd sub"), ("git status --short", "git status"))
    assert found.commands == (("cd sub", False), ("git status", True))
    assert (found.read_only, found.redirect) == (False, False)
    assert (found.possible_paths, found.resolved_paths) == (("out.txt",), (("out.txt", "/abs/out.txt"),))
    write_request = write("c2", "/x.py").data.permission_request
    assert watch_feed.asked(write_request).full_command_text == ""


def test_a_shell_call_is_read_from_its_requests_working_directory_whichever_comes_first(place) -> None:
    there = str(place.elsewhere / "out.txt")
    stepped(
        place,
        ran("s1", "touch out.txt", second=1),  # start only: from the session's folder, inside
        ran("s2", "touch ../../elsewhere/out.txt", second=2),  # start only, relative and outside
        asking("p1", "touch out.txt", cwd=str(place.elsewhere), second=3),  # permission only
        ran("b1", "touch out.txt", second=4), asking("b1", "touch out.txt", cwd=str(place.elsewhere), second=5),
        asking("b2", "touch out.txt", cwd=str(place.elsewhere), second=6), ran("b2", "touch out.txt", second=7),
        ran("b3", "touch out.txt", second=8), asking("b3", "touch out.txt", cwd=str(place.own), second=9),
        asking("b4", "echo x > out.txt", second=10), ran("b4", "echo x > out.txt", second=11),  # no directory named
    )  # fmt: skip
    found = rows(place)
    assert sorted(found) == ["b1", "b2", "p1", "s2"]
    assert {c: (r["targets"], r["verdict"], r["source"]) for c, r in found.items()} == {
        "s2": ([there], OUTSIDE, "start"), "p1": ([there], OUTSIDE, "permission"),
        "b1": ([there], OUTSIDE, "enriched"), "b2": ([there], OUTSIDE, "enriched"),
    }  # fmt: skip
    assert found["p1"]["command"] == "ran touch out.txt"


def test_a_shell_calls_read_only_commands_clear_only_their_own_unresolved_effect(place) -> None:
    stepped(
        place,
        ran("r1", "git status --short"), asking("r1", "git status --short", read_only=("git status",)),
        ran("r2", "git status && git push"), asking("r2", "git status && git push", read_only=("git status",)),
        asking("r3", "git status > ../../elsewhere/s.txt", read_only=("git status",)),
    )  # fmt: skip
    found = rows(place)
    assert sorted(found) == ["r2", "r3"]
    assert (found["r2"]["targets"], found["r2"]["verdict"]) == ([], SHELL_UNRESOLVED)
    assert (found["r3"]["targets"], found["r3"]["verdict"]) == ([str(place.elsewhere / "s.txt")], OUTSIDE)


def test_a_call_after_one_that_may_have_moved_its_shell_has_its_relative_targets_unresolved(place) -> None:
    drift = "unresolved (an earlier command changed the shell's directory)"
    elsewhere = place.elsewhere
    stepped(
        place,
        ran("b0", "touch early", second=1),  # before any cd: from the session's folder
        ran("m1", f"cd {elsewhere}", second=2), ran("m2", "touch note", second=3),
        ran("m3", f"touch {elsewhere}/abs.txt", second=4),  # absolute: still identified
        asking("m4", "touch named", cwd=str(place.own), second=5),  # the runtime names its directory
        asking("m1", f"cd {elsewhere}", second=7),  # judged again: its change counts once
    )  # fmt: skip
    found = rows(place)
    assert sorted(found) == ["m2", "m3"]
    assert (found["m2"]["targets"], found["m2"]["verdict"]) == ([], drift)
    assert (found["m3"]["targets"], found["m3"]["unresolved"]) == ([str(elsewhere / "abs.txt")], "")


def test_a_cd_chain_or_an_environment_change_reaches_later_calls_of_its_shell_only(place) -> None:
    stepped(
        place,
        ran("c1", "cd sub && make", second=1), ran("c2", "touch a", second=2),
        ran("s1", f"cd {place.elsewhere}", shell_id="one", second=3), ran("s2", "touch b", shell_id="two", second=4),
        ran("s3", "touch c", shell_id="one", second=5),
        ran("e1", "export HOME=/elsewhere", shell_id="env", second=6), ran("e2", "touch ~/d", shell_id="env", second=7),
    )  # fmt: skip
    found = rows(place)
    assert sorted(found) == ["c1", "c2", "e2", "s3"]  # shell "two" never moved
    assert found["c2"]["unresolved"] == "an earlier command changed the shell's directory"
    assert found["s3"]["unresolved"] == "an earlier command changed the shell's directory"
    assert found["e2"]["unresolved"] == "an earlier command changed the shell's environment"


DRIFT, ENVIRONMENT = (
    "an earlier command changed the shell's directory",
    "an earlier command changed the shell's environment",
)


@pytest.mark.parametrize(
    "first",
    [
        'V=TMPDIR; printf -v "$V" /outside',
        'V=TMPDIR; export "$V=/outside"',
        'V=TMPDIR; unset "$V"',
        "TMPDIR=/outside :",
        'eval "TMPDIR=/outside"',
        'CMD=export; "$CMD" TMPDIR=/outside',
        "for v in TMPDIR; do export $v=/outside; done",
    ],
)
def test_a_later_call_of_the_same_shell_sees_what_an_unnamed_or_builtin_change_did(place, first) -> None:
    stepped(place, ran("f1", first, second=1), ran("f2", 'touch "$TMPDIR/out"', second=2))
    assert ENVIRONMENT in rows(place)["f2"]["unresolved"]


@pytest.mark.parametrize(
    "first", ["HOME=/etc cd", 'eval "cd /etc"', 'CMD=cd; "$CMD" /etc', "'cd' /etc; if :; then :; fi"]
)
def test_a_later_call_of_the_same_shell_sees_a_move_it_cannot_name(place, first) -> None:
    marked = {"identifier": "eval", "readOnly": True}
    request = {"kind": "shell", "toolCallId": "g1", "canOfferSessionApproval": False, "fullCommandText": first,
               "commands": [marked], "hasWriteFileRedirection": False, "intention": "x", "possiblePaths": [],
               "possibleUrls": []}  # fmt: skip
    eval_ro = event("permission.requested", {"requestId": "r-g1", "permissionRequest": request}, second=1)
    stepped(place, ran("g1", first, second=1), eval_ro, ran("g2", "touch note", second=2))
    assert rows(place)["g2"]["unresolved"] == DRIFT


def test_read_only_evidence_for_a_top_level_command_does_not_clear_its_nested_twin(place) -> None:
    text = "git diff && sh -c 'git diff --output=/outside/log'"
    stepped(place, ran("n1", text), asking("n1", text, read_only=("git diff",)))
    assert rows(place)["n1"]["verdict"] == SHELL_UNRESOLVED


def test_a_call_delivered_before_an_earlier_cd_is_judged_again_by_start_time(place) -> None:
    elsewhere = place.elsewhere
    events = [
        ran("o2", "touch note", second=5), ran("o1", f"cd {elsewhere}", second=2),  # delivered later, ran before
        ran("p2", "touch later", second=8, shell_id="p"),
        asking("p1", f"cd {elsewhere}", second=9),  # seen only as a request: not before p2 yet
        ran("q1", "touch same", second=20), ran("q2", f"cd {elsewhere}", second=20),  # equal times: cannot tell
    ]  # fmt: skip
    st = stepped(place, *events, close=False)
    assert st.feed.calls[("s1", "p2")].reported is False  # judged inside so far
    st.on_event(ran("p1", f"cd {elsewhere}", second=7, shell_id="p"))  # its start arrives: before p2 after all
    st.feed.close()
    found = rows(place)
    assert (found["o2"]["unresolved"], found["q1"]["unresolved"], found["p2"]["unresolved"]) == (DRIFT,) * 3
