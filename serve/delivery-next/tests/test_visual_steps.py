"""Item 8c (TD-49, TD-96): click and type steps before a state's screenshot, on a prepared test copy only."""

import functools
import http.server
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next import brief_tools, briefs, loop
from owlbear_delivery_next.inbox import BriefApproval
from owlbear_delivery_next.models import Change, Exit, StepKind, VisualState, VisualStep
from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.steps import before, browse, prepare, visual
from owlbear_delivery_next.store import Store

NOW = datetime(2026, 10, 13, 6, tzinfo=UTC)
SEARCH = {"name": "search", "path": "/", "expect": "The results list shows Ada"}
TYPE = {"state": "search", "do": "type", "target": "Name", "text": "Ada"}
CLICK = {"state": "search", "do": "click", "target": "Show"}


def draft(visual=(SEARCH,), steps=(TYPE, CLICK), **fields) -> brief_tools.BriefDraft:
    base = {"title": "Search", "outcome": "The page finds people by name.", "criteria": ["Searching Ada lists Ada"]}
    return brief_tools.BriefDraft(
        **(base | {"scope": ["web"], "ui": True, "visual": list(visual), "steps": list(steps)} | fields)
    )


def approve(c: Change) -> Change:
    return loop.fold(c, [BriefApproval(at=NOW, version=c.brief.version)], NOW)


def test_steps_are_stored_in_order_with_their_state_and_version_it():
    c = briefs.drafted(None, draft(), "c1", "c1", Profile())
    (state,) = c.brief.visual
    assert [(s.do, s.target, s.text) for s in state.steps] == [("type", "Name", "Ada"), ("click", "Show", "")]
    assert state.version == 1
    same = briefs.drafted(c, draft(), "c1", "c1", Profile())
    assert same.brief.visual[0].version == 1
    moved = briefs.drafted(same, draft(steps=(CLICK, TYPE)), "c1", "c1", Profile())
    assert moved.brief.visual[0].version == 3  # another order is another state: the brief version it changed in


def test_a_state_removed_and_added_again_never_gets_a_version_an_earlier_draft_had():
    c = approve(briefs.drafted(None, draft(), "c1", "c1", Profile()))
    c = briefs.drafted(c, draft(steps=(TYPE,)), "c1", "c1", Profile())  # never approved
    assert c.brief.visual[0].version == 2
    gone = briefs.drafted(c, draft(visual=(), steps=(), ui=False), "c1", "c1", Profile())
    back = briefs.drafted(gone, draft(steps=(TYPE,)), "c1", "c1", Profile())  # the unapproved v2 content again
    assert back.brief.visual[0].version == 4


@pytest.mark.parametrize(
    ("steps", "error"),
    [
        ([TYPE | {"state": "home"}], "steps[0].state: home is not a state of this brief"),
        ([TYPE | {"text": ""}], 'steps[0].text: empty - say what to type into "Name"'),
        ([CLICK] * 11, "steps: state search has 11 steps, over 10"),
    ],
)
def test_a_step_names_a_state_and_typing_has_text(steps, error):
    assert any(e.startswith(error) for e in brief_tools.check_brief(draft(steps=steps)))


def test_the_visual_check_is_saved_apart_and_a_brief_revision_keeps_it(tmp_path):
    store = Store(tmp_path / "store")
    code, out = briefs.save_brief(store, draft(visual=(), steps=(), ui=False).model_dump())
    assert code == 200
    handle = out["change"]
    code, out = briefs.save_visual(store, {"change": handle, "ui": True, "states": [SEARCH], "steps": [TYPE, CLICK]})
    assert (code, out["version"]) == (200, 2)
    c = store.read(out["slug"])
    assert (c.brief.title, c.brief.ui, [len(s.steps) for s in c.brief.visual]) == ("Search", True, [2])
    revised = draft(title="Search people").model_dump(exclude={"ui", "visual", "steps"}) | {"change": handle}
    code, out = briefs.save_brief(store, revised)  # what the chat's brief tool sends: no visual check
    c = store.read(out["slug"])
    assert (code, c.brief.title, c.brief.ui, [len(s.steps) for s in c.brief.visual]) == (
        200,
        "Search people",
        True,
        [2],
    )
    code, out = briefs.save_visual(store, {"change": "c99", "ui": False})
    assert (code, out["errors"]) == (422, ["change: c99 is not a Change here - use a handle from show_status"])


def stepped(*steps: VisualStep) -> Change:
    state = VisualState(name="search", path="/", expect="Ada", steps=list(steps))
    c = briefs.drafted(None, draft(), "c1", "c1", Profile())
    c.brief.visual = [state]
    return c


def test_steps_run_only_on_a_prepared_test_copy():
    c = stepped(VisualStep(do="click", target="Show"))
    with pytest.raises(prepare.PrepareError) as unprepared:
        prepare.stepped(c, prepared=False)
    asked = unprepared.value.result
    assert (asked.exit, asked.cause, [o.next for o in asked.question.options]) == (
        Exit.ASK,
        "project-env:check:preparation",
        [StepKind.CHECK, StepKind.SHAPE, "pause"],
    )
    prepare.stepped(c, prepared=True)
    prepare.stepped(stepped(), prepared=False)  # static states need no test copy


PAGE = """<!doctype html><title>t</title>
<label>Name <input id="n"></label><button onclick="o.textContent='Hello, '+n.value">Show</button>
<p id="o"></p>{extra}"""


@pytest.fixture
def site(tmp_path):
    root = tmp_path / "site"
    root.mkdir()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield root, f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def capture(url: str, out: Path, *states: VisualState) -> list[visual.Shot]:
    try:
        return visual.capture(url, states, out, (1280,), timeout_ms=5000)
    except visual.BrowserMissingError as exc:
        pytest.skip(f"no Chrome, Edge or Playwright Chromium: {exc}")


@pytest.mark.browser
def test_a_real_capture_types_and_clicks_before_its_screenshot(site, tmp_path):
    root, url = site
    (root / "index.html").write_text(PAGE.format(extra=""))
    (root / "twice.html").write_text(PAGE.format(extra="<button>Show</button>"))
    steps = [VisualStep(do="type", target="Name", text="Ada"), VisualStep(do="click", target="Show")]
    wrong = [VisualStep(do="type", target="Show", text="Ada")]  # a button is no field to type into
    shot, twice, field = capture(  # one browser launch, a page per state
        url,
        tmp_path / "out",
        VisualState(name="search", path="/", expect="Hello, Ada", steps=steps),
        VisualState(name="twice", path="/twice.html", expect="x", steps=steps),
        VisualState(name="field", path="/", expect="x", steps=wrong),
    )
    assert (shot.file, shot.error) == ("search-1280.png", "")
    assert twice.error == "state twice step 2 (click 'Show'): 2 controls are named 'Show'; name exactly one"
    assert field.error == "state field step 1 (type 'Show'): no control named it"


@pytest.mark.browser
def test_a_field_named_like_a_button_takes_the_typing_and_a_step_never_reaches_outside(site, tmp_path):
    root, url = site
    other = http.server.ThreadingHTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    threading.Thread(target=other.serve_forever, daemon=True).start()
    live = f"http://127.0.0.1:{other.server_port}"
    send = f"fetch('{live}/orders', {{method: 'POST', body: n.value}})"
    page = f'<input id="n" placeholder="Search"><button aria-label="Search" onclick="{send}">go</button>'
    (root / "index.html").write_text(f"<!doctype html><title>t</title>{page}")
    steps = [VisualStep(do="type", target="Search", text="Ada"), VisualStep(do="click", target="Search")]
    try:
        (shot,) = capture(url, tmp_path / "out", VisualState(name="search", path="/", expect="x", steps=steps))
    finally:
        other.shutdown()
    assert shot.error == f"state search left the preview ({live})"  # typed into the field, the POST stopped


def test_a_stepped_shot_stops_off_origin_sockets_and_a_framed_less_popup():
    from playwright.sync_api import Error  # noqa: PLC0415 - the optional browser runtime's error

    handlers: dict[str, object] = {}
    context = SimpleNamespace(
        route=lambda _p, h: handlers.update(route=h), route_web_socket=lambda _m, h: handlers.update(socket=h)
    )
    page = SimpleNamespace(context=context, main_frame=object())
    left: list[str] = []
    browse.confine(page, "http://127.0.0.1:4173", left, stepped=True)
    done: list[str] = []
    for url in ("ws://127.0.0.1:4173/live", "wss://api.example.com/orders"):
        ws = SimpleNamespace(
            url=url, connect_to_server=lambda: done.append("connect"), close=lambda: done.append("close")
        )
        handlers["socket"](ws)
    assert (done, left) == (["connect", "close"], ["wss://api.example.com"])

    class Popup:  # a popup's first request: its frame is not available yet
        url, method, resource_type = "https://example.com/", "GET", "document"

        def is_navigation_request(self) -> bool:
            return True

        @property
        def frame(self) -> object:
            msg = "Frame for this navigation request is not available"
            raise Error(msg)

    route = SimpleNamespace(request=Popup(), abort=lambda: done.append("abort"), continue_=lambda: done.append("go"))
    handlers["route"](route)
    assert (done[-1], left[-1]) == ("abort", "https://example.com")


def test_the_before_capture_renders_only_static_states_without_a_test_copy(monkeypatch, tmp_path):
    c = stepped(VisualStep(do="click", target="Show"))
    c.brief.visual.append(VisualState(name="home", path="/", expect="Hallo"))
    rendered: list[str] = []
    monkeypatch.setattr(before.check, "answers", lambda _u: False)
    monkeypatch.setattr(before.check, "start", lambda *_a: subprocess.Popen([sys.executable, "-c", "pass"]))
    monkeypatch.setattr(before.check, "ready", lambda *_a: {})
    monkeypatch.setattr(before.check, "dispose", lambda _e: {})
    monkeypatch.setattr(
        before.visual, "CAPTURE", lambda _u, states, *_a, **_k: rendered.extend(s.name for s in states) or []
    )
    c.env = c.env or before.Environment(check="visual", command="serve", directory=".", ready_url="http://127.0.0.1:1/")
    notes: list[str] = []
    before._serve(c, tmp_path, tmp_path, lambda _e: None, notes, widths=[1280])  # noqa: SLF001
    assert (rendered, notes) == (["home"], ["search: its steps need a test preparation"])
