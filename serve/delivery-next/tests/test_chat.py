import contextlib
import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api, briefs, loop, setup, tools
from owlbear_delivery_next.codebase import CURRENT
from owlbear_delivery_next.config import Agent, Layer, resolve
from owlbear_delivery_next.host import HostRecord
from owlbear_delivery_next.mcp_server import NOT_RUNNING, Chat
from owlbear_delivery_next.models import Change, Exit, Option, Outcome, Question, StepKind
from owlbear_delivery_next.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.store import Store
from owlbear_delivery_next.vscode_contract import Outcome as Outcome_

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
BRIEF = {
    "title": "Add farewell",
    "outcome": "farewell(name) says goodbye in the app package.",
    "criteria": ["farewell('Ada') returns 'Bye, Ada!'"],
    "scope": ["packages/app"],
}


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW, code=CURRENT)  # noqa: S106 - test token

    def activity(self, _slug):
        return Activity(host_up=True)


def client(store):
    app = api.create_app(store, "t", Host())
    return TestClient(app, base_url="http://127.0.0.1", headers={"authorization": "Bearer t"})


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607
    return tmp_path


def test_an_unloadable_change_keeps_its_handle_from_a_new_brief(tmp_path):
    store = Store(tmp_path)
    path = tmp_path / "changes" / "old" / "change.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"format": 0, "slug": 5, "handle": "c1"}')
    assert client(store).post("/api/next/briefs", json=BRIEF).json()["change"] == "c2"


def test_a_handle_once_issued_is_never_issued_again(tmp_path):
    store, c = Store(tmp_path), client(Store(tmp_path))
    assert [c.post("/api/next/briefs", json=BRIEF).json()["change"] for _ in range(2)] == ["c1", "c2"]
    (tmp_path / "changes" / "add-farewell-2" / "change.json").write_text('{"handle": "c')  # truncated
    odd = tmp_path / "changes" / "odd" / "change.json"
    odd.parent.mkdir()
    odd.write_text('{"format": 0, "handle": "x999"}')  # not a handle the host issues
    assert c.post("/api/next/briefs", json=BRIEF).json()["change"] == "c3"
    for name in ("add-farewell-2", "add-farewell-3"):  # a restore or loss leaves only c1 readable
        (tmp_path / "changes" / name / "change.json").unlink()
    assert (store.issued(), c.post("/api/next/briefs", json=BRIEF).json()["change"]) == (3, "c4")


def test_brief_errors_name_each_field(tmp_path):
    c = client(Store(tmp_path))
    bad = {
        **BRIEF,
        "outcome": "short",
        "criteria": [],
        "person_checks": [{"name": "Look!", "steps": ["a"], "expect": "b"}],
    }
    r = c.post("/api/next/briefs", json=bad)
    assert r.status_code == 422
    assert [e.split(":")[0] for e in r.json()["errors"]] == ["outcome", "criteria", "person_checks[0].name"]
    r = c.post("/api/next/briefs", json={**BRIEF, "scope": ["../elsewhere"]})
    assert r.json()["errors"] == ['scope[0]: ../elsewhere is not repository-relative - e.g. "packages/app"']
    assert c.post("/api/next/briefs", json={**BRIEF, "change": "c7"}).json()["errors"][0].startswith("change: c7")


def test_a_saved_brief_waits_for_approval_of_its_exact_version(tmp_path):
    store = Store(tmp_path)
    c = client(store)
    saved = c.post("/api/next/briefs", json=BRIEF).json()
    assert (saved["change"], saved["next"].endswith("page: http://127.0.0.1:9/#token=tok")) == ("c1", True)
    assert api.link(Host.record.model_copy(update={"token": ""})) is None  # a starting host has no link yet
    slug = store.slugs()[0]
    assert loop.next_step(store.read(slug), NOW) is None
    revised = {**BRIEF, "change": "c1", "criteria": ["farewell('Ada') returns 'Bye bye, Ada!'"]}
    assert c.post("/api/next/briefs", json=revised).json()["version"] == 2
    assert store.read(slug).brief.criteria[0].version == 2
    assert c.post(f"/api/next/changes/{slug}/approve-brief", json={"version": 1}).status_code == 409
    assert c.post(f"/api/next/changes/{slug}/approve-brief", json={"version": 2}).json() == {
        "accepted": "brief-approval"
    }
    with store.lock(slug) as lock:
        change, step = store.fold(lock, slug, NOW)
        assert (change.brief.approved_version, step.kind, loop.brief_due(change)) == (2, StepKind.SHAPE, True)
        store.write(lock, loop.apply(*loop.brief_challenge(change, loop.StepResult(exit=Exit.DONE)), NOW))
    assert c.post("/api/next/briefs", json=revised).status_code == 409


def test_plan_checks_come_from_the_profile():
    plan, _ = tools.parse(
        tools.PlanResult, {"tasks": [{"title": "t", "goal": "AC-1", "scope": ["/x"], "checks": ["make"]}]}
    )
    assert tools.check_plan(plan, tools.Worktree("a", "a"), ["npm test"]) == [
        'tasks[0].checks: "make" is not a check of the project profile - use one of "npm test"',
        "tasks[0].scope: /x is not repository-relative",
    ]


def test_plan_scopes_stay_within_the_approved_brief():
    tasks = [{"title": "t", "goal": "AC-1", "scope": s, "checks": ["make"]} for s in ([".", "packages/app/src"],)]
    tasks += [{"title": "t", "goal": "AC-1", "scope": [s], "checks": ["make"]} for s in ("packages", ".github/ci.yml")]
    plan, _ = tools.parse(tools.PlanResult, {"tasks": tasks})
    outside = "is outside the approved brief scope packages/app; keep to the brief or report_wrong_premise to widen it"
    assert tools.check_plan(plan, tools.Worktree("a", "a"), ["make"], ["packages/app"]) == [
        f"tasks[0].scope: . {outside}",
        f"tasks[1].scope: packages {outside}",
        f"tasks[2].scope: .github/ci.yml {outside}",
    ]
    assert tools.check_plan(plan, tools.Worktree("a", "a"), ["make"], []) == []


def test_chat_refuses_recovery_decisions(repo):
    store = Store.open(repo)
    closed = [Option(id="abandon", label="Abandon", next="abandon"), Option(id="reopen", label="Reopen")]
    change = Change(
        slug="greet",
        handle="c1",
        questions=[
            Question(id="q1", step=StepKind.BUILD, text="Which language?", options=[Option(id="o1", label="German")]),
            Question(id="q2", step=StepKind.MERGE, text="The PR was closed", cause=loop.PR_CLOSED, options=closed),
        ],
        outcome=Outcome(exit=Exit.ASK, question="q2", reason="The PR was closed", who="you", at=NOW),
    )
    with store.lock("greet") as lock:
        store.write(lock, change)
    chat = Chat(repo)
    refused = chat.answer_question("c1.q2", "abandon", "")
    assert (refused["answered"], refused["error"].startswith(api.T6)) == (False, True)
    assert chat.answer_question("c1.q1", "o1", "") == {"answered": False, "error": NOT_RUNNING.format(repo=repo)}
    assert not list((store.root / "changes" / "greet" / "inbox").glob("*.json"))
    status = chat.show_status("c1")
    assert (status["running"], status["changes"][0]["question"]["answer_in"]) == (False, "changes-page")
    c = client(store)
    body = {"question": "q2", "option": "abandon", "channel": "chat"}
    assert c.post("/api/next/changes/greet/answers", json=body).status_code == 403
    assert c.post("/api/next/changes/greet/answers", json=body | {"channel": "status-view"}).status_code == 200


READY = {
    "gh --version": (0, "gh version 2.102.0"),
    "gh repo view --json nameWithOwner,viewerPermission": (0, '{"nameWithOwner": "o/r", "viewerPermission": "ADMIN"}'),
    "copilot --version": (0, "1.0.95"),
    "git config user.name": (0, "Ada"),
    "git config user.email": (0, "ada@example.com"),
    "git config --bool commit.gpgsign": (1, ""),
}
GPG = "gpg --batch --yes --pinentry-mode error -u ABC --clearsign -o /dev/null /dev/null"


def failed(table, network=None):
    checks = setup.readiness("github.com", lambda argv: table.get(" ".join(argv), (0, "")), network, "copilot")
    return [(c.name, c.fix) for c in checks if not c.ok]


def test_readiness_gives_one_concrete_fix_per_failure():
    assert failed(READY) == []
    assert failed(READY | {"gh auth status --hostname github.com": (1, "not logged in")}) == [
        ("github sign-in", "Run `gh auth login --hostname github.com`")
    ]
    tls = failed(READY, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
    assert [n for n, _ in tls] == ["network"]
    assert "SSL_CERT_FILE" in tls[0][1]
    read_only = '{"nameWithOwner": "o/r", "viewerPermission": "READ"}'
    assert [n for n, _ in failed(READY | {"gh repo view --json nameWithOwner,viewerPermission": (0, read_only)})] == [
        "repository"
    ]
    locked = {"git config --bool commit.gpgsign": (0, "true"), "git config user.signingkey": (0, "ABC"), GPG: (2, "")}
    assert [n for n, _ in failed(READY | locked)] == ["commit signing"]
    assert failed(READY | locked | {GPG: (0, "")}) == []


def test_a_failed_sign_in_names_the_failed_account_not_the_last_one_listed():
    status = (
        "github.com\n  X Failed to log in to github.com using token (GH_TOKEN)\n  - Active account: true\n"
        "  - The token in GH_TOKEN is invalid.\n\n  ✓ Logged in to github.com account ada (keyring)\n"
        "  - Active account: false\n  - Token scopes: 'repo'"
    )
    probe = READY | {"gh auth status --hostname github.com": (1, status)}
    *_, sign_in = setup.publishing("github.com", lambda argv: probe.get(" ".join(argv), (0, "")), None)
    assert (sign_in.name, sign_in.ok) == ("github sign-in", False)
    assert sign_in.detail.endswith("The token in GH_TOKEN is invalid.")
    assert sign_in.fix.startswith("Unset GH_TOKEN")


def test_an_unusable_ssh_signing_key_is_a_failed_check_with_one_fix(tmp_path):
    ssh = {"git config --bool commit.gpgsign": (0, "true"), "git config gpg.format": (0, "ssh")}
    ssh |= {"ssh-add -L": (0, "ssh-ed25519 AAAAkey ada")}
    (tmp_path / "bad.pub").write_text("not a key")
    for key in (tmp_path / "missing", tmp_path / "bad.pub"):
        [(name, fix)] = failed(READY | ssh | {"git config user.signingkey": (0, str(key))})
        assert (name, fix.startswith("Set `git config user.signingkey`")) == ("commit signing", True)
    assert failed(READY | ssh | {"git config user.signingkey": (0, "key::ssh-ed25519 AAAAkey")}) == []


def test_the_chat_skill_installs_user_locally_and_never_over_another_skill(tmp_path):
    assert setup.install_skill(tmp_path).startswith("chat skill installed for you only (not tracked)")
    path = tmp_path / ".copilot" / "skills" / "delivery" / "SKILL.md"
    assert "save_brief" in path.read_text()
    path.write_text("---\nname: delivery\n---\nsomeone else's")
    assert "holds another skill" in setup.install_skill(tmp_path)
    assert path.read_text().endswith("someone else's")


def test_no_local_write_without_consent(repo):
    asked = []
    path = repo / ".vscode" / "tasks.json"
    merge = lambda d: setup.with_task(d, "python")  # noqa: E731
    no = setup.consent(repo, path, merge, "Write?", lambda q: asked.append(q) or "", yes=False)
    assert no.startswith("not written")
    assert asked == ["Write? [y/N] "]
    assert not path.exists()
    path.parent.mkdir()
    path.write_text(json.dumps({"version": "2.0.0", "tasks": [{"label": "build"}]}))
    assert setup.consent(repo, path, merge, "Write?", lambda _q: "y", yes=False).startswith("written")
    tasks = json.loads(path.read_text())["tasks"]
    assert [t["label"] for t in tasks] == ["build", setup.TASK]
    assert tasks[1]["runOptions"] == {"runOn": "folderOpen"}
    jsonc = repo / ".mcp.json"
    jsonc.write_text("// mine\n{}")
    assert "not plain JSON" in setup.consent(repo, jsonc, lambda d: d, "Write?", lambda _q: "y", yes=True)
    assert jsonc.read_text() == "// mine\n{}"


def test_an_untracked_write_is_excluded_once_and_the_exclude_file_is_created(repo):
    exclude = repo / ".git" / "info" / "exclude"
    exclude.unlink(missing_ok=True)
    path = repo / ".mcp.json"
    for _ in range(2):
        said = setup.consent(repo, path, lambda d: d | {"a": 1}, "Write?", lambda _q: "", yes=True)
        assert said.startswith("written")
    assert exclude.read_text() == "/.mcp.json\n"
    exclude.write_text("# mine\n*.log\n/.mcp.json\n")
    setup.consent(repo, repo / ".vscode" / "tasks.json", lambda d: d, "Write?", lambda _q: "", yes=True)
    assert exclude.read_text() == "# mine\n*.log\n/.mcp.json\n/.vscode/tasks.json\n"
    git = ["git", "status", "--porcelain"]
    status = subprocess.run(git, cwd=repo, capture_output=True, text=True, check=True)  # noqa: S603
    assert status.stdout == ""


def test_a_tracked_file_is_left_untouched_with_the_manual_alternative(repo):
    path = repo / ".mcp.json"
    path.write_text("{}\n")
    subprocess.run(["git", "add", ".mcp.json"], cwd=repo, check=True)  # noqa: S607
    said = setup.consent(repo, path, lambda d: d | {"a": 1}, "Write?", lambda _q: "y", yes=True)
    assert said.startswith("not written")
    assert "tracked" in said
    assert path.read_text() == "{}\n"
    assert ".mcp.json" not in (repo / ".git" / "info" / "exclude").read_text()


def test_an_untracked_link_to_a_tracked_file_is_refused_and_its_target_untouched(repo, tmp_path):
    (repo / "real.json").write_text("{}\n")
    subprocess.run(["git", "add", "real.json"], cwd=repo, check=True)  # noqa: S607
    (repo / ".mcp.json").symlink_to("real.json")
    said = setup.consent(repo, repo / ".mcp.json", lambda d: d | {"a": 1}, "Write?", lambda _q: "y", yes=True)
    assert said.startswith("not written")
    assert "symbolic link" in said
    assert (repo / "real.json").read_text() == "{}\n"
    (tmp_path / "elsewhere").mkdir()
    (repo / ".vscode").symlink_to(tmp_path / "elsewhere")
    linked = setup.consent(repo, repo / ".vscode" / "tasks.json", lambda d: d, "Write?", lambda _q: "y", yes=True)
    assert "symbolic link" in linked
    assert not (tmp_path / "elsewhere" / "tasks.json").exists()


def test_a_file_tracked_while_the_owner_answers_is_not_written(repo):
    path = repo / ".mcp.json"
    path.write_text("{}\n")

    def answer(_q):
        subprocess.run(["git", "add", ".mcp.json"], cwd=repo, check=True)  # noqa: S607
        return "y"

    said = setup.consent(repo, path, lambda d: d | {"a": 1}, "Write?", answer, yes=False)
    assert (said.startswith("not written"), "tracked" in said) == (True, True)
    assert path.read_text() == "{}\n"


COMMAND = f"code chat -m agent '{api.START_PROMPT}'"
SHAPER = resolve(None, Layer()).agents["shaper"]


@pytest.mark.parametrize(
    ("ending", "warning", "state"),
    [
        (Outcome_("started", session="copilotcli:/s0"), "", {"state": "open"}),
        (Outcome_("started"), "could not remove it", {"state": "open", "warning": "could not remove it"}),
        (Outcome_("model-unavailable", "the agent host does not list m"), "", {"state": "failed"}),
    ],
)
def test_new_chat_opens_the_shaping_chat_on_the_shaper_role_and_reports_how_it_went(tmp_path, ending, warning, state):
    asked = []
    out = api.new_chat(tmp_path, SHAPER, start=lambda *a: asked.append(a) or (ending, warning))
    assert asked == [(tmp_path, SHAPER, api.START_PROMPT)]
    assert (SHAPER.model, SHAPER.effort, SHAPER.context) == ("claude-opus-5.5", "high", "default")
    assert {k: v for k, v in out.items() if k != "reason"} == state
    if state["state"] == "failed":
        why = f"the Copilot chat did not start (model-unavailable: {ending.detail})"
        assert out["reason"] == f"{why}; run this in {tmp_path}"


class Opening:
    """A launch that stays opening until released, then ends as ``ending`` says."""

    def __init__(self, ending=None):
        self.release, self.calls, self.ending = threading.Event(), [], ending or {"state": "open"}

    def __call__(self, repo, role):
        self.calls.append((repo, role))
        assert self.release.wait(5)
        if isinstance(self.ending, Exception):
            raise self.ending
        return self.ending


def launcher(store, launch, which=lambda _n: "/bin/code", auth="Bearer t"):
    host = Host()
    host.repo = store.root
    app = api.create_app(store, "t", host, launch=launch, which=which)
    return TestClient(app, base_url="http://127.0.0.1", headers={"authorization": auth})


def settled(c, launch):
    end = time.monotonic() + 5
    while (state := c.get(f"/api/next/new-change/{launch}").json())["state"] == "opening" and time.monotonic() < end:
        time.sleep(0.01)
    return state


def test_new_change_returns_at_once_and_the_page_polls_the_launch_on_the_projects_shaper(tmp_path):
    store = Store(tmp_path)
    store.update_config(lambda _layer: Layer(agents={"shaper": Agent(model="gpt-6-luna", effort="max")}))
    opening = Opening({"state": "open", "warning": "could not remove it"})
    c = launcher(store, opening)
    started = c.post("/api/next/new-change").json()
    assert (started["started"], set(started)) == (True, {"started", "launch"})
    assert c.get(f"/api/next/new-change/{started['launch']}").json() == {"state": "opening", "command": COMMAND}
    opening.release.set()
    assert settled(c, started["launch"]) == {"state": "open", "warning": "could not remove it", "command": COMMAND}
    [(repo, role)] = opening.calls
    assert (repo, role.model, role.effort) == (store.root, "gpt-6-luna", "max")


@pytest.mark.parametrize(
    ("ending", "reason"),
    [
        ({"state": "failed", "reason": "the Copilot chat did not start (unbound: x)"}, "did not start (unbound: x)"),
        (OSError("no window"), "OSError: no window"),
    ],
)
def test_a_failed_launch_gives_its_reason_and_the_command(tmp_path, ending, reason):
    opening = Opening(ending)
    opening.release.set()
    c = launcher(Store(tmp_path), opening)
    state = settled(c, c.post("/api/next/new-change").json()["launch"])
    assert (state["state"], state["command"], reason in state["reason"]) == ("failed", COMMAND, True)


def test_a_new_change_while_one_opens_is_refused_and_the_gap_starts_when_it_ends(tmp_path, monkeypatch):
    now = [100.0]
    monkeypatch.setattr(api, "time", SimpleNamespace(monotonic=lambda: now[0]))
    opening = Opening()
    c = launcher(Store(tmp_path), opening)
    first = c.post("/api/next/new-change").json()["launch"]
    now[0] += 60  # VS Code had to start
    refused = c.post("/api/next/new-change")
    assert (refused.status_code, refused.json()["detail"]) == (409, "a shaping chat is already opening")
    opening.release.set()
    assert settled(c, first)["state"] == "open"
    assert c.post("/api/next/new-change").status_code == 429
    now[0] += api.LAUNCH_GAP
    assert c.post("/api/next/new-change").json()["started"] is True
    assert len(opening.calls) == 2


def test_new_change_needs_the_token_and_without_code_or_settings_returns_the_command(tmp_path):
    store, opening = Store(tmp_path), Opening()
    anonymous = launcher(store, opening, auth="")
    codes = [anonymous.post("/api/next/new-change").status_code, anonymous.get("/api/next/new-change/x").status_code]
    assert codes == [401, 401]
    out = launcher(store, opening, which=lambda _n: None).post("/api/next/new-change").json()
    assert (out["started"], out["command"], out["reason"]) == (
        False,
        COMMAND,
        f"`code` is not on PATH; run this in {store.root}",
    )
    store.config_path.write_text("{")
    c = launcher(store, opening)
    out = c.post("/api/next/new-change").json()
    assert (out["started"], out["command"], "settings" in out["reason"]) == (False, COMMAND, True)
    assert (c.get("/api/next/new-change/nope").status_code, opening.calls) == (404, [])


def test_two_concurrent_new_change_calls_launch_once(tmp_path, monkeypatch):
    meet = threading.Barrier(2)

    def monotonic():
        with contextlib.suppress(threading.BrokenBarrierError):  # both meet here only without the lock
            meet.wait(timeout=0.3)
        return time.monotonic()

    monkeypatch.setattr(api, "time", SimpleNamespace(monotonic=monotonic))
    opening = Opening()
    c = launcher(Store(tmp_path), opening)
    with ThreadPoolExecutor(2) as pool:
        codes = sorted(pool.map(lambda _i: c.post("/api/next/new-change").status_code, range(2)))
    opening.release.set()
    assert (codes, len(opening.calls)) == ([200, 409], 1)


def test_the_page_loads_the_vendored_design_system_without_the_token(tmp_path):
    c = TestClient(api.create_app(Store(tmp_path), "t", Host()), base_url="http://127.0.0.1")
    page = c.get("/").text
    assert all(f"/assets/pds/{n}" in page for n in api.PDS)
    css, js = c.get("/assets/pds/index.css"), c.get("/assets/pds/load.mjs")
    assert (css.headers["content-type"].split(";")[0], js.headers["content-type"].split(";")[0]) == (
        "text/css",
        "text/javascript",
    )
    assert "--p-color-canvas" in css.text
    assert "export" in js.text
    assert [c.get(f"/assets/pds/{n}").status_code for n in ("x.js", "..%2Fchanges.html")] == [404, 404]


def test_yes_confirms_the_profile_but_never_an_unknown_entry():
    unknown = ProfileEntry(state="unknown", evidence="HTTP 403")
    prof = Profile(version=2, entries={"github:rules": unknown})
    declined, _ = setup.confirm(prof, lambda _q: "", yes=False)
    assert declined.confirmed_at is None
    confirmed, left = setup.confirm(prof, lambda _q: "", yes=True)
    assert (left, confirmed.entries["github:rules"].state) == (["github:rules"], "unknown")
    assert confirmed.entries["setup:confirmed-by"].value == "--yes"
    assert confirmed.confirmed_at is not None


def test_yes_confirms_only_the_profile_and_local_files_and_the_skill_need_their_own_consent(
    repo, tmp_path_factory, monkeypatch
):
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(setup, "check", lambda *_a: [])
    monkeypatch.setattr(setup.profile, "detect", lambda *_a: Profile(version=1))
    written = [repo / ".vscode" / "tasks.json", repo / ".mcp.json", home / ".copilot" / "skills" / "delivery"]
    asked = []
    assert setup.run(repo, [], yes=True, ask=lambda q: asked.append(q) or "") == 0
    assert [p.exists() for p in written] == [False, False, False]
    assert len(asked) == 3  # both local files and the skill were asked, never assumed
    assert "Install the Delivery chat skill" in asked[2]
    asked.clear()
    assert setup.run(repo, [], yes=True, local_files="no", skill="no", ask=lambda q: asked.append(q) or "y") == 0
    assert (asked, [p.exists() for p in written]) == ([], [False, False, False])
    assert setup.run(repo, [], yes=True, local_files="yes", skill="yes", ask=pytest.fail) == 0
    assert [p.exists() for p in written] == [True, True, True]


def test_setup_replaces_a_saved_profile_it_cannot_read(repo, tmp_path_factory, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))
    monkeypatch.setattr(setup, "check", lambda *_a: [])
    monkeypatch.setattr(setup.profile, "detect", lambda *_a: Profile(version=1))
    store = Store.open(repo)
    store.root.mkdir(parents=True, exist_ok=True)
    (store.root / "profile.json").write_text('{"format": 1, "models": {}}')
    assert setup.run(repo, [], yes=True, local_files="no", skill="no") == 0
    assert "cannot be read" in capsys.readouterr().out
    assert store.read_profile().confirmed_at is not None


@pytest.mark.parametrize(
    ("title", "slug"),
    [
        ("Add a Notes textarea with an 800-character counter", "add-a-notes-textarea-with-an-800"),
        ("Add greet(name)", "add-greet-name"),
        ("Supercalifragilisticexpialidocious-and-more-words-beyond-forty", "supercalifragilisticexpialidocious-and"),
        ("x" * 50, "x" * 40),
        ("!!!", "change"),
    ],
)
def test_a_slug_ends_on_a_whole_word_within_forty_characters(title, slug):
    assert briefs.new_slug(title, []) == slug
    assert briefs.new_slug(title, [slug]) == f"{slug}-2"
