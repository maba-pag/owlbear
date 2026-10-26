import contextlib
import json
import os
import shlex
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import chat_contract, tool_schema, tools
from owlbear_delivery_next.change_contracts.models import Change, Exit, Option, Outcome, Question, StepKind
from owlbear_delivery_next.change_contracts.preparation import Preparation
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import chat_client, setup
from owlbear_delivery_next.commands.chat_client import NOT_RUNNING, NOT_SERVED, OWLBEAR_DOWN, Chat, OwlBear
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import answers, api, pages
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import copilot_cli, readiness, step_input
from owlbear_delivery_next.runtimes.vscode_contract import Outcome as Outcome_
from owlbear_delivery_next.settings import carried
from owlbear_delivery_next.settings.config import Agent, Layer
from owlbear_delivery_next.state_store import briefs
from owlbear_delivery_next.state_store.database import put_record
from owlbear_delivery_next.state_store.store import Store

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
BRIEF = {
    "title": "Add farewell",
    "outcome": "farewell(name) says goodbye in the app package.",
    "criteria": ["farewell('Ada') returns 'Bye, Ada!'"],
    "scope": ["packages/app"],
}


class Host:
    wake = SimpleNamespace(set=lambda: None)
    draining = staticmethod(lambda: False)
    closed = staticmethod(lambda: False)
    updating = staticmethod(lambda: "")
    launching = threading.Lock()
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


def raw(store: Store, slug: str, text: str) -> None:
    """A Change record as stored, damaged or of an older format."""
    with store.db.write() as db:
        put_record(db, slug, text)


def test_an_unloadable_change_keeps_its_handle_from_a_new_brief(tmp_path):
    store = Store(tmp_path)
    raw(store, "old", '{"format": 0, "slug": 5, "handle": "c1"}')
    assert client(store).post("/api/next/briefs", json=BRIEF).json()["change"] == "c2"


def test_a_handle_once_issued_is_never_issued_again(tmp_path):
    store, c = Store(tmp_path), client(Store(tmp_path))
    assert [c.post("/api/next/briefs", json=BRIEF).json()["change"] for _ in range(2)] == ["c1", "c2"]
    raw(store, "add-farewell-2", '{"handle": "c')  # truncated
    raw(store, "odd", '{"format": 0, "handle": "x999"}')  # not a handle the host issues
    assert c.post("/api/next/briefs", json=BRIEF).json()["change"] == "c3"
    with store.db.write() as db:  # a restore or loss leaves only c1 readable
        db.execute("DELETE FROM changes WHERE slug IN ('add-farewell-2', 'add-farewell-3')")
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
    assert (saved["change"], saved["next"].endswith("after: http://127.0.0.1:9/#token=tok")) == ("c1", True)
    assert "challenge_brief (change c1, version 1)" in saved["next"]
    assert api.link(Host.record.model_copy(update={"token": ""})) is None  # a starting host has no link yet
    slug = store.slugs()[0]
    assert loop.next_step(store.read(slug), NOW) is None
    revised = {**BRIEF, "change": "c1", "criteria": ["farewell('Ada') returns 'Bye bye, Ada!'"]}
    assert c.post("/api/next/briefs", json=revised).json()["version"] == 2
    assert store.read(slug).brief.criteria[0].version == 2
    assert c.post(f"/api/next/changes/{slug}/approve-brief", json={"version": 1}).status_code == 409
    unchallenged = c.post(f"/api/next/changes/{slug}/approve-brief", json={"version": 2})
    assert (unchallenged.status_code, "has not been challenged" in unchallenged.json()["detail"]) == (409, True)
    with store.lock(slug) as lock:
        change = store.read(slug)
        change.brief.challenged = 2  # its challenge loop ended on v2 (TD-249)
        store.write(lock, change)
    assert c.post(f"/api/next/changes/{slug}/approve-brief", json={"version": 2}).json() == {
        "accepted": "brief-approval"
    }
    with store.lock(slug) as lock:
        change, step = store.fold(lock, slug, NOW)
        assert (change.brief.approved_version, step.kind) == (2, StepKind.PLAN)
        store.write(lock, change)
    assert c.post("/api/next/briefs", json=revised).status_code == 409


DECIDED = [
    {"question": "Which wording?", "answer": "'Bye, Ada!'", "origin": "decided", "reason": ""},
    {"question": "Where does it live?", "answer": "packages/app/farewell.ts", "origin": "autonomous", "reason": "Near"},
]


def test_decisions_and_non_goals_stay_on_the_brief_version_reach_the_workers_and_are_read_back(repo, chat_replied):
    store = Store.open(repo)
    c = client(store)
    body = {**BRIEF, "non_goals": ["No translations"], "decisions": DECIDED}
    assert c.post("/api/next/briefs", json=body).status_code == 200
    states = [{"name": "home", "path": "/", "expect": "Bye"}]
    assert c.post("/api/next/briefs/visual", json={"change": "c1", "ui": True, "states": states}).status_code == 200
    change = store.read(store.slugs()[0])
    brief = change.brief
    assert (brief.version, brief.non_goals) == (2, ["No translations"])
    assert [d.model_dump(include={"question", "answer", "origin", "reason"}) for d in brief.decisions] == DECIDED
    shown = [step_input.plan(change, Profile(), Path("/w"), {}), step_input.brief_challenge(change, Path("/w"))]
    for text in [*shown, "\n".join(step_input.brief(change))]:  # planner, challenger, reviewers
        assert "Non-goals:\n- No translations" in text
        assert "- Which wording? -> 'Bye, Ada!' (decided)\n- Where does it live?" in text
    read_back = hosted(store, chat_replied).show_status("c1")["brief"]
    assert read_back["decisions"] == [{**d, "scope": "change"} for d in DECIDED]  # what the shaper sends again
    assert (read_back["non_goals"], read_back["version"]) == (["No translations"], 2)
    bad = {**body, "decisions": [{"question": "Which?", "answer": "this", "origin": "guessed"}]}
    assert c.post("/api/next/briefs", json=bad).json()["errors"][0].startswith("decisions")
    unreasoned = {**body, "decisions": [{**DECIDED[1], "reason": " "}]}
    errors = c.post("/api/next/briefs", json=unreasoned).json()["errors"]
    assert [e.split(":", 1)[0] for e in errors] == ["decisions[0].reason"]  # an autonomous choice says why


def test_a_saved_decision_reaches_the_workers_whole(repo):
    store = Store.open(repo)
    question = "Which states may the greeting show? " + "q" * 240 + " end of question"
    answer = "Home and checkout. " + "x" * 400 + " Never on the payment page."
    decided = [{"question": question, "answer": answer, "origin": "decided"}]
    assert answer.index("Never") > 400  # past the old cut
    assert client(store).post("/api/next/briefs", json={**BRIEF, "decisions": decided}).status_code == 200
    change = store.read(store.slugs()[0])

    for text in (step_input.plan(change, Profile(), Path("/w"), {}), "\n".join(step_input.brief(change))):
        assert f"- {' '.join(question.split())} -> {answer} (decided)" in text


def test_what_the_owner_stated_himself_is_recorded_and_survives_a_visual_save_and_a_revision(repo):
    store = Store.open(repo)
    c = client(store)
    checks = [
        {"name": "feel", "steps": ["Flip five times"], "expect": "No stutter", "owner": True},
        {"name": "copy", "steps": ["Read the label"], "expect": "It says Flip"},
    ]
    body = {**BRIEF, "criteria": [*BRIEF["criteria"], "farewell('') returns 'Bye!'"], "specified": ["AC-2"]}
    body |= {"person_checks": checks}
    assert c.post("/api/next/briefs", json=body).status_code == 200
    states = [
        {"name": "home", "path": "/", "expect": "Bye", "owner": True},
        {"name": "copy", "path": "/", "expect": "!"},  # named like a check the owner did not state
    ]
    assert c.post("/api/next/briefs/visual", json={"change": "c1", "ui": True, "states": states}).status_code == 200
    slug, owned = store.slugs()[0], ["AC-2", "screen:home", "check:feel"]
    assert store.read(slug).brief.specified == owned
    assert c.get(f"/api/next/changes/{slug}").json()["brief"]["specified"] == owned
    assert c.post("/api/next/briefs", json={**body, "change": "c1"}).status_code == 200  # keeps the visual check
    assert store.read(slug).brief.specified == owned
    read_back = hosted(Store.open(repo)).show_status("c1")["brief"]  # what a resumed chat resaves
    assert read_back["specified"] == ["AC-2"]
    assert read_back["states"] == [{"name": "home", "owner": True}, {"name": "copy", "owner": False}]
    assert read_back["person_checks"] == [{"name": "feel", "owner": True}, {"name": "copy", "owner": False}]
    unknown = c.post("/api/next/briefs", json={**body, "specified": ["AC-3"]}).json()["errors"]
    assert unknown == ["specified[0]: AC-3 names no criterion of this brief - use one of AC-1, AC-2"]


def test_a_brief_with_clicks_waits_for_a_declared_test_preparation_before_approval(tmp_path):
    store = Store(tmp_path)
    c = client(store)
    states = [{"name": "dark", "path": "/", "expect": "Dark"}]
    steps = [{"state": "dark", "do": "click", "target": "Dark mode"}]
    assert c.post("/api/next/briefs", json={**BRIEF, "ui": True, "visual": states, "steps": steps}).status_code == 200
    slug = store.slugs()[0]
    with store.lock(slug) as lock:
        change = store.read(slug)
        change.brief.challenged = 1
        store.write(lock, change)
    refused = c.post(f"/api/next/changes/{slug}/approve-brief", json={"version": 1})
    assert (refused.status_code, "dark" in refused.json()["detail"]) == (409, True)
    option = Preparation(id="fixtures", kind="data-only", seed="npm run seed", cleanup="npm run drop")
    assert (
        store.save(
            store.config_path,
            Layer,
            lambda layer: layer.model_copy(update={"preparations": [option]}),
            "setup",
            owner=True,
        )
        == ""
    )
    assert c.post(f"/api/next/changes/{slug}/approve-brief", json={"version": 1}).status_code == 200


def test_plan_checks_come_from_the_profile():
    plan, _ = tool_schema.parse(
        tools.PlanResult, {"tasks": [{"title": "t", "goal": "AC-1", "scope": ["/x"], "checks": ["make"]}]}
    )
    assert tools.check_plan(plan, tools.Worktree("a", "a"), ["npm test"]) == [
        'tasks[0].checks: "make" is not a check of the project profile - use one of "npm test"',
        "tasks[0].scope: /x is not repository-relative",
    ]


def test_plan_scopes_stay_within_the_approved_brief():
    tasks = [{"title": "t", "goal": "AC-1", "scope": s, "checks": ["make"]} for s in ([".", "packages/app/src"],)]
    tasks += [{"title": "t", "goal": "AC-1", "scope": [s], "checks": ["make"]} for s in ("packages", ".github/ci.yml")]
    plan, _ = tool_schema.parse(tools.PlanResult, {"tasks": tasks})
    outside = "is outside the approved brief scope packages/app; keep to the brief or report_wrong_premise to widen it"
    assert tools.check_plan(plan, tools.Worktree("a", "a"), ["make"], ["packages/app"]) == [
        f"tasks[0].scope: . {outside}",
        f"tasks[1].scope: packages {outside}",
        f"tasks[2].scope: .github/ci.yml {outside}",
    ]
    assert tools.check_plan(plan, tools.Worktree("a", "a"), ["make"], []) == []


def hosted(store: Store, replied=lambda *_a: None) -> Chat:
    """The chat tools of the clone of *store*, calling its host in-process as a chat does (chat contract 1)."""
    http, chat = client(store), Chat(Path(), store.root)

    def call(method: str, path: str, body: object = None) -> tuple[int, object]:
        r = http.request(method, f"/api/next{path}", json=body, headers={chat_contract.HEADER: str(chat_contract.CHAT)})
        if r.status_code == 200:
            replied(method, path, r.json())
        return r.status_code, r.json()

    chat.call = call
    return chat


def test_chat_refuses_recovery_decisions(repo, chat_replied):
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
    chat = hosted(store, chat_replied)
    refused = chat.answer_question("c1.q2", "abandon", "", {"kind": "event"})
    assert (refused["answered"], refused["error"].startswith(answers.T6)) == (False, True)
    down = {"answered": False, "error": NOT_RUNNING.format(repo=repo)}
    assert Chat(repo, store.root).answer_question("c1.q1", "o1", "", {"kind": "event"}) == down
    unknown = chat.answer_question("c9.q1", "o1", "", {"kind": "event"})
    assert unknown == {"answered": False, "error": "question: c9.q1 is not a question id; show_status gives them"}
    with store.db.read() as db:
        assert db.execute("SELECT count(*) FROM inbox").fetchone() == (0,)
    status = chat.show_status("c1")
    assert (status["running"], status["changes"][0]["question"]["answer_in"]) == (True, "changes-page")
    assert {"progress", "spend", "tool_use"} <= set(status["changes"][0])
    [listed] = chat.show_status()["changes"]  # every Change: the page's details stay out
    assert (listed["question"]["id"], {"progress", "spend", "tool_use", "pullback"} & set(listed)) == ("c1.q2", set())
    c = client(store)
    body = {"question": "q2", "option": "abandon", "channel": "chat"}
    assert c.post("/api/next/changes/greet/answers", json=body).status_code == 403
    assert c.post("/api/next/changes/greet/answers", json=body | {"channel": "status-view"}).status_code == 200


def test_a_host_running_without_this_project_says_so_and_owlbears_clone_is_never_told_to_add_itself(repo, monkeypatch):
    machine = HostRecord(url="http://127.0.0.1:9/", token="t", pid=9, started_at=NOW, code=CURRENT)  # noqa: S106
    found = {local_home.root(): machine}
    monkeypatch.setattr(chat_client.host, "running_at", lambda root, _m=None: found.get(root))
    chat, served = Chat(repo, repo / "home"), NOT_SERVED.format(repo=repo)
    assert chat.find_decisions("x", "all", include_retired=False) == {"found": False, "error": served}
    assert chat.show_status()["message"] == served
    monkeypatch.setattr(chat_client.host, "running_at", lambda _root, _m=None: None)
    assert chat.show_status()["message"] == NOT_RUNNING.format(repo=repo)
    own = OwlBear(repo).find_decisions("x", "all", include_retired=False)
    assert (own["error"], "add this project" in own["error"]) == (OWLBEAR_DOWN, False)


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
    checks = readiness.readiness("github.com", lambda argv: table.get(" ".join(argv), (0, "")), network, "copilot")
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


def test_copilot_cli_skips_vscode_shim_and_names_it_when_alone(tmp_path, monkeypatch):
    shim, real = tmp_path / copilot_cli.SHIM, tmp_path / "bin"
    for folder in (shim, real):
        folder.mkdir()
        (folder / "copilot").write_text("#!/bin/sh\n", encoding="utf-8")
        (folder / "copilot").chmod(0o755)
    monkeypatch.delenv("COPILOT_CLI_PATH", raising=False)
    monkeypatch.setenv("PATH", f"{shim}{os.pathsep}{real}")
    assert copilot_cli.cli_path() == str(real / "copilot")
    monkeypatch.setenv("PATH", str(shim))
    with pytest.raises(FileNotFoundError, match=r"only VS Code's shim .*brew install --cask copilot-cli"):
        copilot_cli.cli_path()
    checks = readiness.readiness("github.com", lambda argv: READY.get(" ".join(argv), (0, "")), None, None)
    [check] = [c for c in checks if c.name == "copilot cli"]
    assert not check.ok
    assert check.detail == f"not found: only VS Code's shim {shim / 'copilot'}, which is not the CLI"


def test_a_failed_sign_in_names_the_failed_account_not_the_last_one_listed():
    status = (
        "github.com\n  X Failed to log in to github.com using token (GH_TOKEN)\n  - Active account: true\n"
        "  - The token in GH_TOKEN is invalid.\n\n  ✓ Logged in to github.com account ada (keyring)\n"
        "  - Active account: false\n  - Token scopes: 'repo'"
    )
    probe = READY | {"gh auth status --hostname github.com": (1, status)}
    *_, sign_in = readiness.publishing("github.com", lambda argv: probe.get(" ".join(argv), (0, "")), None)
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


def test_no_local_write_without_consent(repo):
    asked = []
    path = repo / ".vscode" / "tasks.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"version": "2.0.0", "tasks": [{"label": "build"}, {"label": setup.TASK}]}))
    no = setup.consent(repo, path, setup.without_task, "Remove?", lambda q: asked.append(q) or "", yes=False)
    assert (no.startswith("not written"), asked, setup.has_task(path)) == (True, ["Remove? [y/N] "], True)
    assert setup.consent(repo, path, setup.without_task, "Remove?", lambda _q: "y", yes=False).startswith("written")
    assert (json.loads(path.read_text())["tasks"], setup.has_task(path)) == ([{"label": "build"}], False)
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


def command(prompt: str) -> str:
    return shlex.join(["code", "chat", "-m", "owlbear-shaper", prompt])


PROMPT = api.START_PROMPT + api.PICKER_NOTE.format(model="claude-opus-5.5", effort="medium")
COMMAND = command(PROMPT)
SHAPER = carried.layer().agents["shaper"]  # module level runs before the carried-settings fixture


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
    assert "owlbear-change-shaping skill" in api.START_PROMPT
    assert (SHAPER.model, SHAPER.effort, SHAPER.context) == ("claude-opus-5.5", "medium", "default")
    assert {k: v for k, v in out.items() if k != "reason"} == state
    if state["state"] == "failed":
        why = f"the Copilot chat did not start (model-unavailable: {ending.detail})"
        assert out["reason"] == f"{why}; run this in {tmp_path}"


def test_a_chat_that_opened_local_tells_the_owner_to_reload_the_window(tmp_path):
    unbound = Outcome_("unbound", "no single session matched nonce and folder")
    out = api.new_chat(tmp_path, SHAPER, start=lambda *_a: (unbound, ""))
    assert out["state"] == "failed"
    hint = "set chat.defaultToCopilotHarness to true in .vscode/settings.json (`owlbear-next setup` offers it), "
    assert f"if a Local chat opened, {hint}reload the window (Developer: Reload Window) and try again" in out["reason"]


class Opening:
    """A launch that stays opening until released, then ends as ``ending`` says."""

    def __init__(self, ending=None):
        self.release, self.calls, self.ending = threading.Event(), [], ending or {"state": "open"}

    def __call__(self, repo, role, prompt):
        self.calls.append((repo, role, prompt))
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
    setup = Layer(agents={"shaper": Agent(model="gpt-6-luna", effort="max")})
    assert store.save(store.config_path, Layer, lambda _layer: setup, "setup", owner=True) == ""
    opening = Opening({"state": "open", "warning": "could not remove it"})
    c = launcher(store, opening)
    started = c.post("/api/next/new-change").json()
    luna = command(api.START_PROMPT + api.PICKER_NOTE.format(model="gpt-6-luna", effort="max"))
    assert (started["started"], set(started)) == (True, {"started", "launch"})
    assert c.get(f"/api/next/new-change/{started['launch']}").json() == {"state": "opening", "command": luna}
    opening.release.set()
    assert settled(c, started["launch"]) == {"state": "open", "warning": "could not remove it", "command": luna}
    [(repo, role, prompt)] = opening.calls
    assert (repo, role.model, role.effort) == (store.root, "gpt-6-luna", "max")
    assert luna == command(prompt)  # the command by hand carries the same note as the launch (TD-277)
    assert prompt.endswith('model picker: set it to gpt-6-luna at max effort."')


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
    assert (out["started"], out["command"], "settings" in out["reason"]) == (False, command(api.START_PROMPT), True)
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
    assert all(f"/assets/pds/{n}" in page for n in pages.PDS)
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


def test_yes_confirms_only_the_profile_and_local_files_need_their_own_consent(
    repo, tmp_path_factory, monkeypatch, capsys
):
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(readiness, "check", lambda *_a: [])
    monkeypatch.setattr(setup.profile, "detect", lambda *_a: Profile(version=1))
    written = [repo / ".mcp.json", repo / ".vscode" / "settings.json"]
    asked = []
    assert setup.run(repo, [], yes=True, ask=lambda q: asked.append(q) or "") == 0
    assert [p.exists() for p in written] == [False] * 2
    assert len(asked) == 2  # the two local files were asked, never assumed; no folder-open task
    assert "chat.defaultToCopilotHarness" in asked[1]
    assert "run `owlbear install` and let it link the shaper" in capsys.readouterr().out  # TD-335: never copied
    asked.clear()
    assert setup.run(repo, [], yes=True, local_files="no", ask=lambda q: asked.append(q) or "y") == 0
    assert (asked, [p.exists() for p in written]) == ([], [False] * 2)
    assert setup.run(repo, [], yes=True, local_files="yes", ask=pytest.fail) == 0
    assert [p.exists() for p in written] == [True] * 2
    assert not (home / ".copilot").exists()
    assert not (repo / ".vscode" / "tasks.json").exists()  # TD-281: opening a window never starts Delivery
    assert json.loads(written[1].read_text()) == {"chat.defaultToCopilotHarness": True}  # TD-275: read at window start


def test_setup_replaces_a_saved_profile_it_cannot_read(repo, tmp_path_factory, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))
    monkeypatch.setattr(readiness, "check", lambda *_a: [])
    monkeypatch.setattr(setup.profile, "detect", lambda *_a: Profile(version=1))
    store = Store.open(repo)
    store.root.mkdir(parents=True, exist_ok=True)
    (store.root / "profile.json").write_text('{"format": 1, "models": {}}')
    assert setup.run(repo, [], yes=True, local_files="no") == 0
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
