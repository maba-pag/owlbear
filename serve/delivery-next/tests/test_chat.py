import json
import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api, loop, setup, tools
from owlbear_delivery_next.host import HostRecord
from owlbear_delivery_next.mcp_server import NOT_RUNNING, Chat
from owlbear_delivery_next.models import Change, Exit, Option, Outcome, Profile, ProfileEntry, Question, StepKind
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.store import Store

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
BRIEF = {
    "title": "Add farewell",
    "outcome": "farewell(name) says goodbye in the app package.",
    "criteria": ["farewell('Ada') returns 'Bye, Ada!'"],
    "scope": ["packages/app"],
}


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW)  # noqa: S106 - test token

    def activity(self, _slug):
        return Activity(host_up=True)


def client(store):
    app = api.create_app(store, "t", Host())
    return TestClient(app, base_url="http://127.0.0.1", headers={"authorization": "Bearer t"})


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607
    return tmp_path


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
        store.write(lock, loop.apply(*loop.brief_review(change, loop.StepResult(exit=Exit.DONE)), NOW))
    assert c.post("/api/next/briefs", json=revised).status_code == 409


def test_plan_checks_come_from_the_profile():
    plan, _ = tools.parse(
        tools.PlanResult, {"tasks": [{"title": "t", "goal": "AC-1", "scope": ["/x"], "checks": ["make"]}]}
    )
    assert tools.check_plan(plan, tools.Worktree("a", "a"), ["npm test"]) == [
        'tasks[0].checks: "make" is not a check of the project profile - use one of "npm test"',
        "tasks[0].scope: /x is not repository-relative",
    ]


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


def test_no_tracked_write_without_consent(tmp_path):
    asked = []
    path = tmp_path / ".vscode" / "tasks.json"
    merge = lambda d: setup.with_task(d, "python")  # noqa: E731
    assert setup.consent(path, merge, "Write?", lambda q: asked.append(q) or "", yes=False).startswith("not written")
    assert asked == ["Write? [y/N] "]
    assert not path.exists()
    path.parent.mkdir()
    path.write_text(json.dumps({"version": "2.0.0", "tasks": [{"label": "build"}]}))
    assert setup.consent(path, merge, "Write?", lambda _q: "y", yes=False).startswith("written")
    tasks = json.loads(path.read_text())["tasks"]
    assert [t["label"] for t in tasks] == ["build", setup.TASK]
    assert tasks[1]["runOptions"] == {"runOn": "folderOpen"}
    jsonc = tmp_path / ".mcp.json"
    jsonc.write_text("// mine\n{}")
    assert "not plain JSON" in setup.consent(jsonc, lambda d: d, "Write?", lambda _q: "y", yes=True)
    assert jsonc.read_text() == "// mine\n{}"


def test_yes_confirms_the_profile_but_never_an_unknown_entry():
    unknown = ProfileEntry(state="unknown", evidence="HTTP 403")
    prof = Profile(version=2, entries={"github:rules": unknown})
    declined, _ = setup.confirm(prof, lambda _q: "", yes=False)
    assert declined.confirmed_at is None
    confirmed, left = setup.confirm(prof, lambda _q: "", yes=True)
    assert (left, confirmed.entries["github:rules"].state) == (["github:rules"], "unknown")
    assert confirmed.entries["setup:confirmed-by"].value == "--yes"
    assert confirmed.confirmed_at is not None
