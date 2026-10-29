"""Visual review slice 4: the design detector in the visual check, as evidence that never fails it (TD-77)."""

import asyncio
import dataclasses
import functools
import http.server
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import Change, Names, StepKind, VisualState, VisualStep
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.visual_records import DetectorFinding, DetectorScan, VisualResult
from owlbear_delivery_next.impeccable import design_tools, detector, pack_files
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.results import Gate
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.workflow_steps import design, visual

NOW = datetime(2026, 10, 14, 12, tzinfo=UTC)
PACK = pack_files.Installed(Path("/nowhere/impeccable"), "0" * 64, "")
HOME = VisualState(name="home", path="/", expect="e")
FORM = VisualState(name="form", path="/f", expect="e", steps=[VisualStep(do="click", target="Open")])


def found(rule: str, where: str) -> detector.Finding:
    return detector.Finding(rule=rule, category="quality", advisory=False, name=rule, where=where, detail="d")


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@t"]
    done = subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


def test_a_rendered_state_is_scanned_in_its_page_and_a_refused_static_state_by_the_engine(monkeypatch, tmp_path):
    def scan(state, width=1280, url="http://127.0.0.1:1/", browser="", pack=PACK):
        return design.rendered(object(), pack, state, width=width, url=url, browser=browser, cwd=tmp_path)

    monkeypatch.setattr(detector, "scan_page", lambda *_a: [])
    scanned = scan(HOME)
    assert (scanned.kind, scanned.scanned, scanned.findings) == ("page", True, [])
    monkeypatch.setattr(detector, "scan_page", lambda *_a: [found("side-tab", ".card")])
    assert [(f.rule, f.where, f.freshness) for f in scan(HOME).findings] == [("side-tab", ".card", "unknown")]

    def refused(*_a):
        msg = "the page refused the design detector: CSP"
        raise detector.DetectorError(msg)

    urls = []
    monkeypatch.setattr(detector, "scan_page", refused)
    monkeypatch.setattr(detector, "scan_url", lambda _p, url, width, *_a: urls.append((url, width)) or [])
    scanned = scan(HOME, 1920, browser="/chromium")
    assert (scanned.kind, scanned.scanned, urls) == ("url", True, [("http://127.0.0.1:1/", 1920)])
    stepped = scan(FORM, url="http://127.0.0.1:1/f")
    assert (stepped.scanned, urls[1:]) == (False, [])  # its steps run only in Delivery's own page
    assert "CSP" in stepped.reason
    assert "not installed" in scan(HOME, pack=None).reason


def test_a_page_finding_is_new_or_existing_only_against_a_before_scan_of_the_same_state_version() -> None:
    def scan(state: str, *rules: str, kind: str = "page") -> DetectorScan:
        found = [DetectorFinding(rule=r, category="quality", advisory=False, where=".x") for r in rules]
        return DetectorScan(state=state, width=1280, kind=kind, scanned=True, findings=found)

    after = [scan("home", "old", "fresh"), scan("about", "x")]
    before = VisualResult(head="b", tree="t", states={"home": 1, "about": 1}, at=NOW, design=[scan("home", "old")])
    marked = design.marked(after, before, {"home": 1, "about": 1})
    assert [[f.freshness for f in s.findings] for s in marked] == [["existing", "new"], ["unknown"]]
    revised = design.marked(after, before, {"home": 2, "about": 1})  # the state changed since "before"
    assert [f.freshness for f in revised[0].findings] == ["unknown", "unknown"]
    assert [f.freshness for f in design.marked(after, None, {"home": 1})[0].findings] == ["unknown", "unknown"]
    by_engine = design.marked([scan("home", "old", kind="url")], before, {"home": 1})  # other rules ran
    assert [f.freshness for f in by_engine[0].findings] == ["unknown"]


def test_the_changes_ui_sources_are_marked_against_the_same_paths_in_the_before_checkout(tmp_path, monkeypatch):
    base, work = tmp_path / "base", tmp_path / "work"
    for root, files in (
        (base, {"app.css": "BAD-a\nok\n"}),
        (work, {"app.css": "ok\nBAD-a\nBAD-b\n", "new.html": "BAD-a"}),
    ):
        (root / "web").mkdir(parents=True)
        for name, text in files.items():
            (root / "web" / name).write_text(text)

    def scan_source(_pack, paths, cwd):
        assert all(p.is_absolute() and p.is_relative_to(cwd) for p in paths)
        return [
            found(text, f"{p}:{n}")
            for p in paths
            for n, text in enumerate(p.read_text().splitlines(), 1)
            if text.startswith("BAD")
        ]

    monkeypatch.setattr(detector, "scan_source", scan_source)
    paths = ["web/app.css", "web/new.html", "web/gone.css", "web/logo.png"]
    old = design.sources(base, paths, PACK)
    assert (old.covered, [f.where for f in old.findings]) == (
        ["web/app.css", "web/gone.css", "web/new.html"],
        ["web/app.css:1"],
    )
    scan = design.sources(work, paths, PACK)
    before = VisualResult(head="b", tree="t", at=NOW, design=[old])
    [marked] = design.marked([scan], before, {})
    assert [(f.rule, f.where, f.freshness) for f in marked.findings] == [
        ("BAD-a", "web/app.css:2", "existing"),  # the same rule in the same file, whatever its line
        ("BAD-b", "web/app.css:3", "new"),
        ("BAD-a", "web/new.html:1", "new"),  # "before" asked about it and the merge-base had none
    ]
    narrower = old.model_copy(update={"covered": ["web/app.css"]})  # a path changed after "before" was taken
    [later] = design.marked([scan], before.model_copy(update={"design": [narrower]}), {})
    assert [f.freshness for f in later.findings] == ["existing", "new", "unknown"]
    assert design.sources(work, ["web/logo.png"], PACK) is None  # nothing the engine reads
    assert "not installed" in design.sources(work, paths, None).reason
    monkeypatch.setattr(detector, "scan_source", lambda *_a: (_ for _ in ()).throw(detector.DetectorError("exit 1")))
    assert (design.sources(work, paths, PACK).scanned, design.sources(work, paths, PACK).reason) == (False, "exit 1")


def test_engine_failures_of_every_kind_are_detector_errors(tmp_path) -> None:
    with pytest.raises(detector.DetectorError, match="cannot be verified"):  # the engine file is missing
        detector.scan_source(PACK, [tmp_path / "a.html"], tmp_path)
    malformed = SimpleNamespace(
        evaluate=lambda *_a: [{"selector": "h1", "findings": "x"}], add_script_tag=lambda **_k: None
    )
    with pytest.raises(detector.DetectorError, match="not a list of findings"):
        detector.scan_page(malformed, PACK)


def test_the_diff_names_unusual_ui_paths_and_both_ends_of_a_rename(tmp_path) -> None:
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(work))
    (work / "web").mkdir()
    (work / "web" / "old.css").write_text("a{color:red}\n" * 20)
    git(work, "add", ".")
    git(work, "commit", "-q", "-m", "base")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/main")
    git(work, "mv", "web/old.css", "web/new.css")
    (work / "web" / "café tab\t.css").write_text("b{}\n")
    (work / "web" / "cr\r\n.css").write_text("c{}\n")
    git(work, "add", ".")
    git(work, "commit", "-q", "-m", "change")
    c = Change(slug="c1", names=Names(branch="main", target="main", worktree=str(work)))
    assert visual.ui_paths(c, git(work, "rev-parse", "HEAD")) == [
        "web/café tab\t.css",
        "web/cr\r\n.css",
        "web/new.css",
        "web/old.css",
    ]
    assert visual.digest(["a.css", "b.css"]) != visual.digest(["a.css\nb.css"])


BAD = (
    "<!doctype html><html><head><title>t</title><style>"
    "body{font-family:Inter,sans-serif}.card{border-left:4px solid #6366f1;border-radius:12px;padding:4px}"
    "</style></head><body><h1>Hallo</h1><div class=card><p>One</p></div><div class=card><p>Two</p></div>"
    "<button onclick=\"console.log('opened')\">Open</button></body></html>"
)


class _Csp(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'")
        super().end_headers()

    def log_message(self, *_a):
        pass


@pytest.mark.browser
def test_a_real_capture_scans_each_state_in_its_page_and_falls_back_where_csp_refuses(
    tmp_path, monkeypatch, machine_home
):
    monkeypatch.setattr(local_home, "root", lambda: machine_home / ".owlbear")  # this machine's pack, read only
    pack = pack_files.installed()
    if pack is None:
        pytest.skip("Impeccable is not installed (owlbear-next impeccable --install)")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(BAD)
    (site / "f").mkdir()
    (site / "f" / "index.html").write_text(BAD)
    servers = []
    for handler in (http.server.SimpleHTTPRequestHandler, _Csp):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(handler, directory=str(site)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
    plain, strict = (f"http://127.0.0.1:{s.server_port}" for s in servers)
    try:
        open_ = visual.capture(plain, [HOME, FORM], tmp_path / "open", (1280,), timeout_ms=5000, pack=pack)
        csp = visual.capture(strict, [HOME, FORM], tmp_path / "csp", (1280,), timeout_ms=5000, pack=pack)
    except visual.BrowserMissingError as exc:
        pytest.skip(f"no Chrome, Edge or Playwright Chromium: {exc}")
    finally:
        for server in servers:
            server.shutdown()
    assert [(s.design.kind, s.design.scanned) for s in open_] == [("page", True), ("page", True)]
    assert all(s.design.findings for s in open_), [s.design for s in open_]
    assert [(s.design.kind, s.design.scanned) for s in csp] == [("url", True), ("page", False)]
    assert {f.rule for f in csp[0].design.findings} == {f.rule for f in open_[0].design.findings}
    assert [s.errors for s in (*open_, *csp)] == [()] * 4  # the scan's own refusals are not the page's errors


@pytest.mark.browser
@pytest.mark.timeout(90)  # a real browser starts and two pages hang; a loaded CI runner needs more than 30 s
def test_a_scan_that_hangs_its_page_is_ended_and_the_screenshot_kept(tmp_path, monkeypatch):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(BAD)
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    hang = pack_files.Installed(Path("/nowhere"), "0" * 64, "window.impeccableDetectAsync = () => { for (;;) {} };")
    monkeypatch.setattr(design, "PAGE_SECONDS", 2)
    start = time.monotonic()
    again = VisualState(name="again", path="/", expect="e")
    try:
        shots = visual.capture(
            f"http://127.0.0.1:{server.server_port}",
            [HOME, again],
            tmp_path / "out",
            (1280,),
            timeout_ms=5000,
            pack=hang,
        )
    except visual.BrowserMissingError as exc:
        pytest.skip(f"no Chrome, Edge or Playwright Chromium: {exc}")
    finally:
        server.shutdown()
    # The deadline, not the 60 s in-page timer: one page on that timer alone passes 60 s. The headroom is the browser's
    # start under a loaded CI runner, which took 35 s on 2026-10-22.
    assert time.monotonic() - start < detector.PAGE_MS / 1000 - 5
    assert [(bool(s.file), s.design.scanned, s.errors) for s in shots] == [(True, False, ())] * 2  # the next page too
    assert all("refused" in s.design.reason for s in shots)


def scan_args(**fields):
    return design_tools.ScanDesign(**fields)


def test_the_builders_scan_reads_only_ui_sources_of_its_worktree(tmp_path, monkeypatch) -> None:
    root = tmp_path / "work"
    (root / "web").mkdir(parents=True)
    (root / "web" / "app.css").write_text(".card{border-left:4px solid red}")
    (tmp_path / "outside.css").write_text("x")
    (root / "web" / "link.css").symlink_to(tmp_path / "outside.css")
    assert "not installed" in design.builder_scan(root, scan_args(paths=["web/app.css"]))
    monkeypatch.setattr(design, "pack", lambda: PACK)
    asked = []
    monkeypatch.setattr(
        detector, "scan_source", lambda _p, paths, _cwd: asked.append(paths) or [found("side-tab", f"{paths[0]}:1")]
    )
    reply = design.builder_scan(root, scan_args(paths=["web/app.css"]))
    assert reply.splitlines() == [
        "1 design detector findings (hints to weigh, never a verdict):",
        "- side-tab at web/app.css:1: d",
    ]
    assert asked == [[root.resolve() / "web/app.css"]]
    for bad in (["../outside.css"], ["/etc/hosts"], ["web/missing.css"], ["web/app.py"], ["web/link.css"]):
        assert "is not a UI file of the worktree" in design.builder_scan(root, scan_args(paths=bad))
    assert "name the UI files to scan" in design.builder_scan(root, scan_args(paths=[]))
    with pytest.raises(ValidationError):
        scan_args(
            paths=["web/app.css"], url="http://127.0.0.1:4173/"
        )  # no page scan: the engine's browser is unguarded
    assert len(asked) == 1  # nothing outside the worktree was scanned


def test_the_scan_answers_without_ending_the_builders_step(tmp_path) -> None:
    calls = []
    helper = (design_tools.SCAN, lambda args: calls.append(args) or "No design detector findings.")
    cfg = sdk_adapter.Session(
        kind=StepKind.BUILD, worktree=tmp_path, session_id="s", message="m", resume=False,
        policy=Policy(tmp_path), observe=lambda: tools.Worktree("h", "h"), checks=(), helpers=(helper,),
    )  # fmt: skip
    run = Run("s")
    gate = Gate(cfg, run, lambda **_e: None, lambda: None)
    assert design_tools.SCAN in gate.specs
    for _ in range(tools.INVALID_LIMIT + 1):  # a wrong scan call is never counted toward ending the step
        assert gate.call(design_tools.SCAN, {"width": 5})[1] is False
    assert gate.call(design_tools.SCAN, {"paths": ["web/app.css"]}) == ("No design detector findings.", True)
    assert (gate.done, run.invalid, len(calls)) == (False, 0, 1)
    st = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    assert {t.name: t.is_terminal for t in st.tools()}[tools.SCAN_DESIGN] is False
    loop_thread, ran = threading.get_ident(), []
    st.cfg = dataclasses.replace(
        cfg, helpers=((design_tools.SCAN, lambda _a: ran.append(threading.get_ident()) or "ok"),)
    )
    st.gate = Gate(st.cfg, Run("s"), lambda **_e: None, lambda: None)
    answer = asyncio.run(st._helped(design_tools.SCAN, SimpleNamespace(arguments={"paths": ["a.css"]})))  # noqa: SLF001
    assert (answer.text_result_for_llm, ran[0] != loop_thread) == ("ok", True)
    assert tools.SCAN_DESIGN in sdk_adapter.agent(StepKind.BUILD, ui=True)["tools"]
    assert tools.SCAN_DESIGN not in sdk_adapter.agent(StepKind.BUILD)["tools"]


def test_a_real_scan_of_a_builders_page(tmp_path, monkeypatch, machine_home) -> None:
    monkeypatch.setattr(local_home, "root", lambda: machine_home / ".owlbear")  # this machine's pack, read only
    if pack_files.installed() is None:
        pytest.skip("Impeccable is not installed (owlbear-next impeccable --install)")
    (tmp_path / "index.html").write_text(BAD)
    reply = design.builder_scan(tmp_path, scan_args(paths=["index.html"]))
    assert "design detector findings" in reply, reply
    assert "at index.html" in reply  # relative to the worktree, never the absolute path
