"""Add project's runs (item 15), executed: each entry against local bare remotes and a fake GitHub."""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.commands import setup, setup_profile
from owlbear_delivery_next.git.access import Access
from owlbear_delivery_next.github import branch_rules, repo_target
from owlbear_delivery_next.github.provider import MergeMethod
from owlbear_delivery_next.local_system import codebase, onboarding_git
from owlbear_delivery_next.machine_host import app, onboarding_job, onboarding_probe, onboarding_stages, project
from owlbear_delivery_next.machine_host import machine as machine_module
from owlbear_delivery_next.machine_host.machine import MachineError
from owlbear_delivery_next.machine_host.onboarding import Onboarding
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import Store

ALL = ("merge", "squash", "rebase")
LIMIT = "Upgrade to GitHub Pro or make this repository public to enable this feature."


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)  # noqa: S603, S607
    return done.stdout.strip()


class Hub:
    """GitHub as the stages see it: repositories are bare remotes the https URLs are rewritten to; calls recorded."""

    def __init__(self, remotes: Path) -> None:
        self.remotes, self.repos, self.rulesets, self.calls = remotes, {}, {}, []
        self.classic: dict[str, Any] = {}
        self.limit: dict[str, str] = {}
        self.answer: dict[str, Any] | None = None  # what a ruleset write answers instead of what was sent
        self.writer = SimpleNamespace(access=lambda *_a, **_k: Access.LOCAL)

    def add(self, repository: str, *, methods: tuple[str, ...] = ALL, commits: bool = False) -> Path:
        bare = self.remotes / f"{repository}.git"
        git(self.remotes, "init", "--bare", "-q", "-b", "main", str(bare))
        self.repos[repository.casefold()] = {"methods": methods, "visibility": "private", "id": f"R_{repository}"}
        if commits:
            seed = self.remotes / "seed"
            git(self.remotes, "clone", "-q", str(bare), str(seed))
            (seed / "README.md").write_text("# seeded\n")
            git(seed, "add", "-A")
            git(seed, "commit", "-q", "-m", "seed")
            git(seed, "push", "-q", "origin", "HEAD:main")
            shutil.rmtree(seed)
        return bare

    def view(self, _client: object, repository: str) -> repo_target.RepoState | None:
        self.calls.append(("view", repository))
        if (r := self.repos.get(repository.casefold())) is None:
            return None
        bare = self.remotes / f"{repository}.git"
        empty = not git(bare, "for-each-ref", "refs/heads")
        methods = frozenset(MergeMethod(m) for m in r["methods"])
        return repo_target.RepoState(repository, r["id"], empty, "" if empty else "main", methods, "ADMIN",
                                     r["visibility"])  # fmt: skip

    def name_free(self, _client: object, owner: str, name: str) -> bool:
        return f"{owner}/{name}".casefold() not in self.repos

    def create(self, _client: object, owner: str, name: str, visibility: str) -> repo_target.RepoState:
        self.calls.append(("create", f"{owner}/{name}", visibility))
        self.add(f"{owner}/{name}")
        self.repos[f"{owner}/{name}".casefold()]["visibility"] = visibility
        return self.view(None, f"{owner}/{name}")  # type: ignore[return-value]

    def read(self, _client: object, repository: str, _branch: str) -> branch_rules.Rules:
        found = [{**rule, "ruleset_id": i, "ruleset_source_type": "Repository"}
                 for i, body in self.rulesets.get(repository, {}).items() for rule in body["rules"]]  # fmt: skip
        return branch_rules.Rules(tuple(found), self.classic.get(repository), self.limit.get(repository, ""))

    def write(self, _client: object, repository: str, *args: Any) -> dict[str, Any]:
        ident, body = (len(self.rulesets.get(repository, {})) + 1, args[0]) if len(args) == 1 else args
        self.calls.append(("ruleset", repository, ident))
        self.rulesets.setdefault(repository, {})[ident] = body
        return {**(self.answer or body), "id": ident}


@pytest.fixture
def hub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Hub:
    remotes = tmp_path / "remotes"
    remotes.mkdir()
    Path(os.environ["HOME"], ".gitconfig").write_text(
        f'[url "{remotes}/"]\n\tinsteadOf = https://github.com/\n[user]\n\tname = Ada\n\temail = ada@example.com\n'
    )
    for name in [n for n in os.environ if n.startswith("GIT_CONFIG_")]:
        monkeypatch.delenv(name)
    h = Hub(remotes)
    monkeypatch.setattr(repo_target, "view", h.view)
    monkeypatch.setattr(repo_target, "name_free", h.name_free)
    monkeypatch.setattr(repo_target, "create", h.create)
    monkeypatch.setattr(repo_target, "ci_status", lambda *_a: "success")
    monkeypatch.setattr(branch_rules, "read", h.read)
    monkeypatch.setattr(branch_rules, "create", h.write)
    monkeypatch.setattr(branch_rules, "replace", h.write)
    monkeypatch.setattr(branch_rules, "read_ruleset", lambda _c, repo, ident: h.rulesets[repo][ident])
    monkeypatch.setattr(onboarding_probe, "account", lambda *_a, **_k: "repository-owner")
    monkeypatch.setattr(onboarding_probe, "client", lambda *_a, **_k: h)
    monkeypatch.setattr(onboarding_git, "push_urls_name", lambda *_a, **_k: [])
    monkeypatch.setattr(readiness, "check", lambda *_a: [])
    monkeypatch.setattr(readiness, "reach", lambda _host: None)
    monkeypatch.setattr(setup_profile.profile, "detect", lambda *_a: Profile(version=1))
    return h


class Machine:
    """What the stages use of the machine: registration and each project's row."""

    def __init__(self) -> None:
        self.projects: dict[str, Any] = {}
        self.updating, self.stopping, self.said = "", threading.Event(), []

    def say(self, text: str) -> None:
        self.said.append(text)

    def register(self, path: Path) -> Any:
        project = SimpleNamespace(entry=SimpleNamespace(id=f"p{len(self.projects) + 1}", path=str(path)), readied=0)
        project._ready = lambda: setattr(project, "readied", project.readied + 1)  # noqa: SLF001
        project.info = lambda: {"ready": [], "blocked": "", "setup": "" if setup.registered(path) else "setup"}
        self.projects[project.entry.id] = project
        return project

    def get(self, pid: str) -> Any:
        return self.projects[pid]


@pytest.fixture
def jobs() -> Onboarding:
    return Onboarding(Machine())  # type: ignore[arg-type]


def plan_for(found: dict[str, Any], **choices: Any) -> dict[str, Any]:
    """The dialog's plan: the probe's facts and the Choices' defaults, overridden by *choices*."""
    rules = found.get("rules") or {}
    plan = {
        "folder": found["folder"], "name": found["name"], "repository": found["repository"],
        "github": found["on_github"], "entry": found["entry"], "stages": found["stages"], "visibility": "private",
        "ci": True, "protect": True, "advice": [], "needs": [], "method": "merge", "labels": [],
        "consents": {"task": True, "server": True, "memory": True, "harness": True}, "files_warned": True,
        "rules_items": rules.get("items"),
    }  # fmt: skip
    return plan | choices


def run(jobs: Onboarding, plan: dict[str, Any], *, profile: bool = True) -> dict[str, Any]:
    """Start the run and answer the profile when it asks; the run's last state."""
    info = settle(jobs, jobs.start(plan)["id"])
    if profile and info["waiting"] and info["waiting"]["kind"] == "profile":
        info = settle(jobs, jobs.answer(info["id"], "profile", {})["id"])
    return info


def settle(jobs: Onboarding, ident: str) -> dict[str, Any]:
    job = jobs.get(ident)
    if job.thread:
        job.thread.join(60)
    return job.info()


def stage(info: dict[str, Any], name: str) -> dict[str, Any]:
    return next(s for s in info["stages"] if s["name"] == name)


def facts(info: dict[str, Any]) -> dict[str, Any]:
    return {k: stage(info, "end")["result"][k] for k in ("registered", "profile", "ready")}


def test_a_new_private_project_from_zero_is_published_protected_and_set_up(hub, jobs, tmp_path):
    found = jobs.probe({"kind": "new", "name": "demo", "folder": str(tmp_path / "demo")})
    assert (found["entry"], found["refusal"]) == ("E5", "")
    plan = plan_for(found, repository="ada/demo")
    assert jobs.preflight(plan) == []
    info = run(jobs, plan)
    assert [s["state"] for s in info["stages"]] == ["done"] * len(info["stages"]), info
    folder = Path(found["folder"])
    pushed = git(hub.remotes / "ada/demo.git", "ls-tree", "-r", "--name-only", "main").split("\n")
    assert pushed == [".github/workflows/ci.yml", "README.md"]
    assert git(folder, "rev-parse", "--abbrev-ref", "@{upstream}") == "origin/main"
    assert ("create", "ada/demo", "private") in hub.calls
    rules = {r["type"]: r.get("parameters") for r in hub.rulesets["ada/demo"][1]["rules"]}
    assert rules["pull_request"]["allowed_merge_methods"] == ["merge"]
    assert rules["required_status_checks"]["required_status_checks"] == [{"context": "CI"}]
    store = Store.open(folder)
    assert store.read_config().prefs.merge_method == MergeMethod.MERGE
    assert store.read_profile().confirmed_at is not None
    assert setup.registered(folder)
    assert facts(info) == {"registered": True, "profile": True, "ready": True}


def test_a_local_only_project_makes_no_github_effect_registers_nothing_and_stays_listed(hub, jobs, tmp_path):
    found = jobs.probe({"kind": "new", "name": "notes", "github": False, "folder": str(tmp_path / "notes")})
    info = run(jobs, plan_for(found, repository=""))
    assert found["stages"] == ["folder", "git", "commit", "files", "end"]
    assert info["ended"] == "local"
    assert hub.calls == []
    assert onboarding_git.folder_state(Path(found["folder"])).git == "commits"
    assert jobs.machine.projects == {}
    assert [j["id"] for j in jobs.listed()] == [info["id"]]
    again = jobs.probe({"kind": "folder", "folder": found["folder"], "github": True})
    assert again["entry"] == "E3b"
    assert "repository" in again["stages"]


def test_an_ignored_file_staged_before_it_was_ignored_stays_unpublished(hub, jobs, tmp_path):
    folder = tmp_path / "keep"
    folder.mkdir()
    (folder / "app.py").write_text("print(1)\n")
    (folder / "secret.txt").write_text("token\n")
    git(folder, "init", "-q", "-b", "main")
    git(folder, "add", "secret.txt")
    (folder / ".gitignore").write_text("secret.txt\n")
    found = jobs.probe({"kind": "folder", "folder": str(folder)})
    assert found["entry"] == "E3"
    run(jobs, plan_for(found, repository="ada/keep"))
    pushed = git(hub.remotes / "ada/keep.git", "ls-tree", "-r", "--name-only", "main").split("\n")
    assert pushed == [".github/workflows/ci.yml", ".gitignore", "app.py"]
    assert (folder / "secret.txt").exists()


def test_an_empty_repository_with_an_unborn_clone_gets_a_first_commit_and_merge_without_protection(hub, jobs, tmp_path):
    hub.add("ada/ledger")
    hub.limit["ada/ledger"] = LIMIT
    folder = tmp_path / "ledger"
    folder.mkdir()
    git(folder, "init", "-q", "-b", "main")
    git(folder, "remote", "add", "origin", "https://github.com/ada/ledger.git")
    found = jobs.probe({"kind": "folder", "folder": str(folder)})
    assert found["entry"] == "E4a"
    assert "repository" not in found["stages"]
    info = run(jobs, plan_for(found))
    assert stage(info, "protection")["result"] == {"applied": False, "why": LIMIT}
    assert git(hub.remotes / "ada/ledger.git", "rev-parse", "main")
    assert Store.open(folder).read_config().prefs.merge_method == MergeMethod.MERGE
    assert facts(info)["profile"] is True


def test_an_existing_clone_left_unprotected_gets_no_rule_and_no_merge_method(hub, jobs, tmp_path):
    hub.add("ada/patch", commits=True)
    folder = Path(onboarding_git.clone(tmp_path, "https://github.com/ada/patch.git", "patch", Access.LOCAL))
    found = jobs.probe({"kind": "folder", "folder": str(folder)})
    assert found["entry"] == "E2"
    assert found["stages"][0] == "protection"
    head = git(folder, "rev-parse", "HEAD")
    info = run(jobs, plan_for(found, protect=False, method=None))
    assert [c for c in hub.calls if c[0] in {"ruleset", "create"}] == []
    assert Store.open(folder).read_config().prefs is None
    assert git(folder, "rev-parse", "HEAD") == head
    assert stage(info, "end")["state"] == "done"


@pytest.mark.parametrize("entry", ["E1", "E4b", "E4c", "E3b"])
def test_each_remaining_entry_ends_with_the_local_and_remote_tips_equal(hub, jobs, tmp_path, entry):
    folder = tmp_path / "proj"
    if entry in {"E1", "E4b"}:
        hub.add("ada/proj", commits=True)
    if entry == "E4b":
        folder.mkdir()
        git(folder, "init", "-q", "-b", "main")
        git(folder, "remote", "add", "origin", "https://github.com/ada/proj.git")
    if entry in {"E4c", "E3b"}:
        folder.mkdir()
        (folder / "a.txt").write_text("a\n")
        git(folder, "init", "-q", "-b", "main")
        git(folder, "add", "-A")
        git(folder, "commit", "-q", "-m", "mine")
    if entry == "E4c":
        hub.add("ada/proj")
        git(folder, "remote", "add", "origin", "https://github.com/ada/proj.git")
    start = {"kind": "github", "repository": "ada/proj", "folder": str(folder)} if entry == "E1" else {
        "kind": "folder", "folder": str(folder)}  # fmt: skip
    found = jobs.probe(start)
    assert found["entry"] == entry, found
    run(jobs, plan_for(found, repository="ada/proj"))
    assert git(folder, "rev-parse", "HEAD") == git(hub.remotes / "ada/proj.git", "rev-parse", "main")


def test_nothing_is_created_when_signing_fails_or_the_name_is_taken(hub, jobs, tmp_path, monkeypatch):
    found = jobs.probe({"kind": "new", "name": "demo", "folder": str(tmp_path / "demo")})
    locked = readiness.Check("commit signing", ok=False, detail="gpg key K locked", fix="Unlock")
    with monkeypatch.context() as m:
        m.setattr(readiness, "signing", lambda _p: locked)
        assert jobs.preflight(plan_for(found, repository="ada/demo")) == ["commit signing: gpg key K locked. Unlock"]
    hub.add("ada/taken")
    taken = jobs.preflight(plan_for(found, repository="ada/taken"))
    assert any("ada/taken already exists" in p for p in taken)
    assert not (tmp_path / "demo").exists()
    assert [c for c in hub.calls if c[0] == "create"] == []


@pytest.mark.usefixtures("hub")
def test_a_folder_inside_another_repository_is_refused_naming_it(jobs, tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    found = jobs.probe({"kind": "new", "name": "inner", "folder": str(tmp_path / "inner")})
    assert found["enclosing"] == str(tmp_path)
    assert "inside the repository" in found["refusal"]


@pytest.mark.usefixtures("hub")
def test_a_save_that_returns_a_notice_fails_the_stage_and_resume_saves_again(jobs, tmp_path, monkeypatch):
    found = jobs.probe({"kind": "new", "name": "demo", "folder": str(tmp_path / "demo")})
    notices = ["the shared repository could not be reached: offline"]
    real = Store.save
    monkeypatch.setattr(Store, "save", lambda self, *a, **k: notices.pop() if notices else real(self, *a, **k))
    info = run(jobs, plan_for(found, repository="ada/demo"))
    failed = {"state": "failed", "detail": "StageError: the shared repository could not be reached: offline"}
    assert stage(info, "merge_method") == {"name": "merge_method", "result": {}, **failed}
    info = settle(jobs, jobs.resume(info["id"])["id"])
    if info["waiting"]:
        info = settle(jobs, jobs.answer(info["id"], "profile", {})["id"])
    assert stage(info, "merge_method")["result"] == {"written": "merge", "clean": True}


def test_a_run_rebuilt_from_its_receipt_resumes_without_repeating_an_effect(hub, jobs, tmp_path):
    found = jobs.probe({"kind": "new", "name": "demo", "folder": str(tmp_path / "demo")})
    info = settle(jobs, jobs.start(plan_for(found, repository="ada/demo"))["id"])
    assert info["waiting"]["kind"] == "profile"
    restarted = Onboarding(jobs.machine)
    assert stage(restarted.get(info["id"]).info(), "push")["state"] == "done"
    info = settle(restarted, restarted.resume(info["id"])["id"])
    info = settle(restarted, restarted.answer(info["id"], "profile", {})["id"])
    assert [c[0] for c in hub.calls].count("create") == 1
    assert facts(info)["registered"] is True


def test_a_lost_create_answer_adopts_only_the_matching_empty_repository(hub, jobs, tmp_path, monkeypatch):
    found = jobs.probe({"kind": "new", "name": "demo", "folder": str(tmp_path / "demo")})
    real = hub.create

    def lost(*args: Any) -> None:
        real(*args)
        msg = "gh timed out"
        raise TimeoutError(msg)

    monkeypatch.setattr(repo_target, "create", lost)
    info = run(jobs, plan_for(found, repository="ada/demo"))
    assert stage(info, "repository")["state"] == "failed"
    info = run(jobs, plan_for(found, repository="ada/demo"))
    info = settle(jobs, jobs.resume(info["id"])["id"])
    assert stage(info, "repository")["result"]["adopted"] is True


@pytest.mark.usefixtures("hub")
def test_a_running_stage_counts_as_busy(jobs, tmp_path, monkeypatch):
    held, gone = threading.Event(), threading.Event()
    monkeypatch.setitem(onboarding_stages.STAGES, "git", lambda _job: held.set() or (gone.wait(30) and {}))
    found = jobs.probe({"kind": "new", "name": "demo", "github": False, "folder": str(tmp_path / "demo")})
    ident = jobs.start(plan_for(found, repository=""))["id"]
    held.wait(30)
    assert jobs.working() == ["Add project demo: git"]
    gone.set()
    settle(jobs, ident)  # its later stages write under this test's home, never the next one's
    assert jobs.working() == []


def test_one_ruleset_without_merge_gets_merge_added_and_its_answer_is_checked(hub, jobs, tmp_path):
    hub.add("ada/proj", commits=True, methods=("merge", "squash"))
    body = branch_rules.new_ruleset("main", require_ci=False)
    body["rules"][2]["parameters"]["allowed_merge_methods"] = ["squash"]
    hub.rulesets["ada/proj"] = {7: body}
    folder = Path(onboarding_git.clone(tmp_path, "https://github.com/ada/proj.git", "proj", Access.LOCAL))
    found = jobs.probe({"kind": "folder", "folder": str(folder)})
    assert "merge_method" in [i["key"] for i in found["rules"]["items"] if not i["holds"]]
    hub.answer = {**body, "bypass_actors": [{"actor_id": 1, "actor_type": "Integration", "bypass_mode": "always"}]}
    info = run(jobs, plan_for(found, needs=["merge_method"]))
    assert stage(info, "protection")["state"] == "failed"
    assert "bypass_actors" in stage(info, "protection")["detail"]
    hub.answer = None
    info = settle(jobs, jobs.resume(info["id"])["id"])
    sent = hub.rulesets["ada/proj"][7]["rules"][2]["parameters"]["allowed_merge_methods"]
    assert sorted(sent) == ["merge", "squash"]


def test_classic_protection_is_listed_for_github_and_never_written(hub, jobs, tmp_path):
    hub.add("ada/proj", commits=True)
    hub.classic["ada/proj"] = {"required_linear_history": {"enabled": True}}
    folder = Path(onboarding_git.clone(tmp_path, "https://github.com/ada/proj.git", "proj", Access.LOCAL))
    found = jobs.probe({"kind": "folder", "folder": str(folder)})
    assert found["rules"]["links"] == {"classic": "https://github.com/ada/proj/settings/branches"}
    info = run(jobs, plan_for(found, method="squash"))
    assert stage(info, "protection")["result"] == {"applied": False, "listed": True}
    assert [c for c in hub.calls if c[0] == "ruleset"] == []


@pytest.mark.usefixtures("hub")
def test_the_receipt_holds_the_inputs_and_results_but_no_token(jobs, tmp_path):
    found = jobs.probe({"kind": "new", "name": "demo", "folder": str(tmp_path / "demo")})
    info = run(jobs, plan_for(found, repository="ada/demo"))
    text = (onboarding_job.receipts() / f"{info['id']}.json").read_text()
    assert '"repository": "ada/demo"' in text
    assert "token" not in text.lower()


def test_a_refused_registration_fails_its_stage_with_the_refusal_whole(hub, jobs, tmp_path, monkeypatch, whole_error):
    found = jobs.probe({"kind": "new", "name": "demo", "folder": str(tmp_path / "demo")})
    refused = MachineError(409, f"RegistryError: {whole_error}\na note on the refusal")

    def refuse(_path: Path) -> None:
        raise refused

    monkeypatch.setattr(jobs.machine, "register", refuse)
    info = run(jobs, plan_for(found, repository="ada/demo"))
    assert stage(info, "register")["detail"] == f"MachineError: RegistryError: {whole_error}\na note on the refusal"
    assert hub.repos  # what ran before it stays: no Undo


@contextmanager
def served(monkeypatch: pytest.MonkeyPatch, pds: Any) -> Iterator[tuple[Any, str, machine_module.Machine]]:
    """A browser page on a machine host served in this process, so the fake GitHub's patches reach its jobs."""
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    monkeypatch.setattr(project.readiness, "ready", lambda *_a, **_k: [])
    monkeypatch.setattr(Host, "_launch", lambda _self, _slug: False)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    record = HostRecord(url=f"{base}/", token="t", pid=1, started_at=datetime.now(UTC), code=codebase.CURRENT)  # noqa: S106
    machine = machine_module.Machine(record)
    machine.load_all()
    server = uvicorn.Server(uvicorn.Config(app.create(machine), log_level="warning", timeout_keep_alive=60))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            pds.only(page, base)
            yield page, base, machine
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


@pytest.mark.browser
@pytest.mark.usefixtures("hub")
def test_the_dialog_takes_a_new_project_from_zero_to_new_change(tmp_path, monkeypatch, pds):
    """A failed stage shows whole with Retry; the profile is confirmed in the dialog and saved; the ending's three
    facts hold and New Change opens the shaping chat for this project; closing gives focus back to its opener."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    real, failed = onboarding_git.push_first, []

    def first_push_fails(path: Path, access: Access) -> None:
        if not failed:
            failed.append(path)
            said = "git push failed: the network went away"
            raise onboarding_git.LocalGitError(said)
        real(path, access)

    monkeypatch.setattr(onboarding_git, "push_first", first_push_fails)
    folder = tmp_path / "demo"
    with served(monkeypatch, pds) as (page, base, machine):
        opened = []
        page.route("**/new-change", lambda r: opened.append(r.request.url) or r.fulfill(
            json={"started": True, "launch": "L1"}))  # fmt: skip
        page.route("**/new-change/L1", lambda r: r.fulfill(json={"state": "open"}))
        page.goto(f"{base}/projects#token=t")
        opener = page.get_by_role("button", name="Add a project")
        opener.click()
        modal = pds.modal(page)
        modal.get_by_role("textbox", name="Name").fill("demo")
        modal.get_by_role("textbox", name="Folder").fill(str(folder))
        modal.get_by_role("button", name="Look").click()
        expect(modal).to_contain_text("Found nothing yet")
        modal.get_by_role("button", name="Continue").click()
        modal.get_by_role("textbox", name="Owner").fill("ada")
        modal.get_by_role("button", name="Check and continue").click()
        expect(modal).to_contain_text("save the merge method merge for this project")
        modal.get_by_role("button", name="Create and set up demo").click()
        expect(modal.locator("pre")).to_have_text("LocalGitError: git push failed: the network went away")
        modal.get_by_role("button", name="Retry").click()
        modal.get_by_role("button", name="Confirm profile").click()
        expect(modal.locator(".facts")).to_contain_text("Registered: yes")
        expect(modal.locator(".facts")).to_contain_text("Profile confirmed: yes")
        expect(modal.locator(".facts")).to_contain_text("Ready for Delivery: yes")
        assert Store.open(folder).read_profile().confirmed_at is not None
        pid = next(p for p in machine.projects.values() if Path(p.entry.path) == folder).entry.id
        modal.get_by_role("button", name="New Change").click()
        pds.answer(page, "Open the chat")
        expect(modal).to_contain_text("The shaping chat opened in VS Code.")
        assert opened == [f"{base}/p/{pid}/api/next/new-change"]
        modal.get_by_role("button", name="Close").click()
        expect(page.get_by_role("dialog")).to_have_count(0)
        expect(opener).to_be_focused()


@pytest.mark.browser
def test_finish_setup_on_a_registered_clone_changes_its_ruleset_and_says_what_is_missing(hub, tmp_path, monkeypatch,
                                                                                           pds):  # fmt: skip
    """A registered row's Finish setup opens the dialog on its folder; the rules list shows the conflict and the
    advice, ticked changes reach the ruleset; with the chat server declined the ending says it isn't ready and offers
    no New Change; Tab stays inside the dialog."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    hub.add("ada/proj", commits=True, methods=("merge", "squash"))
    body = branch_rules.new_ruleset("main", require_ci=False)
    body["rules"][2]["parameters"].update(allowed_merge_methods=["squash"], required_approving_review_count=1)
    hub.rulesets["ada/proj"] = {7: body}
    folder = Path(onboarding_git.clone(tmp_path, "https://github.com/ada/proj.git", "proj", Access.LOCAL))
    registry.register(folder)
    with served(monkeypatch, pds) as (page, base, _machine):
        page.goto(f"{base}/projects#token=t")
        page.get_by_role("listitem", name="proj").get_by_role("button", name="Finish setup").click()
        modal = pds.modal(page)
        expect(modal).to_contain_text("registered here")
        modal.get_by_role("button", name="Continue").click()
        for _ in range(12):  # past the last control focus goes to the browser (body), never to the page behind
            page.keyboard.press("Tab")
            assert modal.evaluate("m => m.contains(document.activeElement) || document.activeElement === document.body")
        modal.get_by_role("checkbox", name="Protect the default branch (opt-in: it has history)").check()
        rules = modal.locator(".rules")
        expect(rules).to_contain_text("conflicts: Delivery needs")
        rules.get_by_role("checkbox", name=re.compile("approv")).check()
        modal.get_by_role("checkbox", name="Register Delivery's chat server in .mcp.json").uncheck()
        modal.get_by_role("button", name="Check and continue").click()
        expect(modal).to_contain_text("change the ruleset: merge_method, no_approvals")
        modal.get_by_role("button", name="Create and set up proj").click()
        modal.get_by_role("button", name="Confirm profile").click()
        expect(modal.locator(".facts")).to_contain_text("Ready for Delivery: no")
        expect(modal).to_contain_text("chats can't reach Delivery")
        expect(modal.get_by_role("button", name="New Change")).to_have_count(0)
    pull = hub.rulesets["ada/proj"][7]["rules"][2]["parameters"]
    assert (sorted(pull["allowed_merge_methods"]), pull["required_approving_review_count"]) == (["merge", "squash"], 0)
