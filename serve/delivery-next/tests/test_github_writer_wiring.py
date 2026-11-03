"""Each place that makes a GitHub provider or client hands it the right account (TD-402).

Only ``gh`` is faked: each case runs a production entry to its first recorded launch and reads the token it carried.
The project names ``octo-writer``, which is neither the active account nor the repository's owner.
"""

import contextlib
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.models import Change, Exit, Names, Step, StepKind
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.commands import cli, runner, setup
from owlbear_delivery_next.github import gh_client
from owlbear_delivery_next.github.owlbear_issues import OwlbearIssues
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.impeccable import pack_git
from owlbear_delivery_next.impeccable_runs import pack_live
from owlbear_delivery_next.local_system import data_place, data_repo, git_files
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.pds_runs import job
from owlbear_delivery_next.project_host import host
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.state_store import backlog_issues, github_writer, profile_share
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import cleanup, engine, publish, queue

ACCOUNTS = {"github.com": {"maba-pag": "success", "boecht": "success", "octo-writer": "success"}}


def _git(cwd, *args) -> str:
    return subprocess.run(("git", "-C", str(cwd), *args), capture_output=True, text=True, check=True).stdout  # noqa: S603, S607


def _clone(path: Path, origin: str) -> Path:
    path.mkdir(parents=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "remote", "add", "origin", origin)
    return path


def _project(tmp_path: Path) -> tuple[Store, Path]:
    repo = _clone(tmp_path / "tools", "https://github.com/acme/tools.git")
    store = Store(tmp_path / "store")
    store.root.mkdir()
    known = {
        k: ProfileEntry(state="known", value=v) for k, v in {profile.REPO: "acme/tools", profile.QUEUE: "yes"}.items()
    }
    store.write_profile(Profile(entries=known))
    return store, repo


def _following(store: Store) -> Change:
    with store.lock("c1") as lock:
        c = Change(slug="c1", step=Step(kind=StepKind.FOLLOW), names=Names(pr=7))
        store.write(lock, c)
    return c


def _engine(tmp_path, _monkeypatch):
    store, repo = _project(tmp_path)
    c = _following(store)
    with store.lock("c1") as lock:
        runner._engine(store, lock, c, repo)  # noqa: SLF001 - the step's provider is built here


def _observe(tmp_path, _monkeypatch):
    store, repo = _project(tmp_path)
    _following(store)
    engine.observe(store, repo, "c1")


def _barrier(tmp_path, _monkeypatch):
    store, repo = _project(tmp_path)
    before = Change(slug="c1", step=Step(kind=StepKind.MERGE), names=Names(pr=7))
    queue.barrier(store, repo)(before, before.model_copy(update={"step": Step(kind=StepKind.FOLLOW)}))


def _detected(seen: list):
    def detect(_repo, gh, _prev):
        with contextlib.suppress(ProviderError):
            gh.read_repository()
        seen.append(gh)
        return Profile(version=1)

    return detect


def _setup(tmp_path, monkeypatch):
    repo = _clone(tmp_path / "tools", "https://github.com/boecht/tools.git")
    monkeypatch.setattr(readiness, "check", lambda *_a: [])
    monkeypatch.setattr(setup.profile, "detect", _detected(seen := []))
    setup.run(repo, [], yes=True, local_files="no")
    assert seen


def _cli(tmp_path, monkeypatch):
    repo = _clone(tmp_path / "tools", "https://github.com/boecht/tools.git")
    monkeypatch.setattr(cli.profile, "detect", _detected(seen := []))
    cli.show_profile(Store(tmp_path / "store"), repo, [])
    assert seen


def _profile_share(tmp_path, monkeypatch):
    repo = _clone(tmp_path / "tools", "https://github.com/boecht/tools.git")
    store = Store(tmp_path / "store")
    store.root.mkdir()
    old = ProfileEntry(state="known", value="main", evidence=f"{profile.CONFIRMED} before observations were bound")
    store.write_profile(Profile(entries={profile.DEFAULT: old}))  # unbound: detection runs again
    monkeypatch.setattr(profile_share.profile, "detect", _detected(seen := []))
    profile_share.checked(store, repo)
    assert seen


def _pack(tmp_path, _monkeypatch):
    with contextlib.suppress(ProviderError):
        pack_live.Live().github(_clone(tmp_path / "pack", "https://github.com/acme/pack.git")).read_repository()


def _pds(tmp_path, _monkeypatch):
    with contextlib.suppress(ProviderError):
        job.Live(package=tmp_path).github(_clone(tmp_path / "pds", "https://github.com/acme/pds.git")).read_repository()


def _backlog(tmp_path, monkeypatch):
    monkeypatch.setattr(backlog_issues, "RUNNER", gh_client.run)
    shared = DataRepo(_clone(tmp_path / "data", "https://github.com/acme/owlbear-data.git"))
    with contextlib.suppress(ProviderError):
        backlog_issues.Issues(shared).comment(7, "seen")


def _owlbear_issues(tmp_path, _monkeypatch):
    with contextlib.suppress(ProviderError):
        OwlbearIssues("acme/owlbear", tmp_path).find("<!-- marker -->")


CASES = {  # entry, the project's setting, the active account, whose token the launch carries
    "the engine's steps": (_engine, "octo-writer", "maba-pag", "octo-writer"),
    "observe": (_observe, "octo-writer", "maba-pag", "octo-writer"),
    "the queue barrier": (_barrier, "octo-writer", "maba-pag", "octo-writer"),
    "setup's detection, setting unset": (_setup, None, "maba-pag", "boecht"),
    "the CLI's detection, setting unset": (_cli, None, "maba-pag", "boecht"),
    "the profile's detection, setting unset": (_profile_share, None, "maba-pag", "boecht"),
    "the design pack": (_pack, "boecht", "boecht", "maba-pag"),
    "the PDS update": (_pds, "boecht", "boecht", "maba-pag"),
    "a backlog issue": (_backlog, "octo-writer", "boecht", "maba-pag"),
    "an OwlBear issue": (_owlbear_issues, "octo-writer", "boecht", "maba-pag"),
}


@pytest.mark.parametrize("case", CASES)
def test_each_construction_site_launches_gh_as_its_account(case, fake_gh, tmp_path, monkeypatch):
    entry, setting, active, login = CASES[case]
    fake_gh.set(ACCOUNTS, {"github.com": active})
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"github_account": setting}))
    entry(tmp_path, monkeypatch)
    launches = [c for c in fake_gh.calls() if c["argv"][0] != "auth"]
    assert launches
    assert {c["GH_TOKEN"] for c in launches} == {f"tok-{login}"}


def test_an_unset_setting_observes_nothing_and_asks_the_owner_at_the_step(fake_gh, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"github_account": None}))
    store, repo = _project(tmp_path)
    c = _following(store)
    assert engine.observe(store, repo, "c1") == (None, False)
    before = Change(slug="c1", step=Step(kind=StepKind.MERGE), names=Names(pr=7))
    assert queue.barrier(store, repo)(before, before.model_copy(update={"step": Step(kind=StepKind.FOLLOW)})) is None
    with store.lock("c1") as lock:
        runner._run(store, lock, c, c.step, repo)  # noqa: SLF001 - the manual runner's handler
    (question,) = store.read("c1").questions
    assert "github_account" in question.text
    assert fake_gh.calls() == []


NOW = datetime(2026, 11, 1, tzinfo=UTC)


def _hosted(tmp_path: Path) -> tuple[Store, Path, str]:
    """The project's clone: its origin names acme/tools on GitHub, and its Git traffic reaches a local bare copy."""
    store, repo = _project(tmp_path)
    bare = tmp_path / "tools.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    _git(repo, "config", f"url.{bare}.insteadOf", "https://github.com/acme/tools.git")  # outranks the offline rule
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
    _git(repo, "push", "-q", "origin", "HEAD:refs/heads/main")
    head = _git(repo, "rev-parse", "HEAD").strip()
    return store, repo, head


def _change(repo: Path, kind: StepKind = StepKind.PUBLISH, **fields) -> Change:
    names = Names(branch="owlbear/c1", target="main", worktree=str(repo), pr=7)
    return Change(slug="c1", step=Step(kind=kind), names=names, **fields)


def _publish_push(store, repo, head, lock):
    hook = repo / ".git" / "hooks" / "pre-push"
    hook.write_text("#!/bin/sh\nexit 1\n")  # the refused push is read back: both ls-remotes run
    hook.chmod(0o755)
    ctx = engine.Ctx(store, lock, repo, store.read_profile(), None, NOW)
    assert publish.push(repo, _change(repo), head, ctx.writer.access()).exit == Exit.BACK


def _cleanup_fetch(store, repo, _head, lock):
    ctx = engine.Ctx(store, lock, repo, store.read_profile(), None, NOW)
    assert cleanup._keep(ctx, repo, _change(repo, StepKind.CLEANUP), None) == ["origin/main"]  # noqa: SLF001


def _needs_target(store, repo, _head, _lock):
    c = _change(repo, StepKind.BUILD)
    assert engine.needs_target(c, repo, "the API", NOW, github_writer.of(store, repo)).exit == Exit.BACK


def _owners_pull(store, repo, _head, lock):
    said: list[str] = []
    found = SimpleNamespace(store=store, repo=repo, say=said.append)
    c = host.Host._pull(found, lock, _change(repo, StepKind.CLEANUP, pull_requested=NOW), NOW)  # noqa: SLF001
    assert c.pullback is not None, said


GIT_CASES = {
    "the publish push and both reads of its ref": (_publish_push, ["ls-remote", "push", "ls-remote"]),
    "a cleanup fetch": (_cleanup_fetch, ["fetch"]),
    "a Builder task that needs the target": (_needs_target, ["fetch"]),
    "the owner's Pull": (_owners_pull, ["fetch"]),
}


@pytest.mark.parametrize("case", GIT_CASES)
def test_each_project_git_launch_carries_the_projects_account(case, fake_gh, git_launches, tmp_path, monkeypatch):
    (entry, verbs), login = GIT_CASES[case], "octo-writer"
    fake_gh.set(ACCOUNTS, {"github.com": "maba-pag"})
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"github_account": login}))
    store, repo, head = _hosted(tmp_path)
    with store.lock("c1") as lock:
        entry(store, repo, head, lock)
    assert git_launches.verbs() == verbs
    for argv, environment in git_launches.seen:
        assert git_launches.options(argv)[:2] == ("-c", "credential.helper=")
        assert environment["GH_TOKEN"] == f"tok-{login}"


@pytest.mark.parametrize(
    ("setting", "cause", "says"),
    [("octo-writer", "gate:publish:ssh", "over SSH"), ("nobody", "auth:publish:gh", "nobody")],
)
def test_an_ssh_push_or_a_missing_account_asks_the_owner_and_pushes_nothing(  # noqa: PLR0913, PLR0917 - one case
    setting, cause, says, fake_gh, git_launches, tmp_path, monkeypatch
):
    fake_gh.set(ACCOUNTS, {"github.com": "maba-pag"})
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"github_account": setting}))
    store, repo, head = _hosted(tmp_path)
    _git(repo, "remote", "set-url", "--push", "origin", "git@github.com:acme/tools.git")
    with store.lock("c1") as lock:
        ctx = engine.Ctx(store, lock, repo, store.read_profile(), None, NOW)
        _, result = engine.run(lambda x, c: (c, publish.push(repo, c, head, x.writer.access())), ctx, _change(repo))
    assert (result.exit, result.cause) == (Exit.ASK, cause)
    assert says in result.question.text
    assert "push" not in git_launches.verbs()


def _mirrored(tmp_path: Path, name: str, url: str) -> Path:
    """A checkout whose origin is *url* on GitHub and whose Git traffic reaches a local bare copy holding ``main``."""
    bare, root = tmp_path / f"{name}.git", tmp_path / name
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    _clone(root, url)
    _git(root, "config", f"url.{bare}.insteadOf", url)  # outranks the offline rule
    for key, value in (("user.name", "t"), ("user.email", "t@t")):
        _git(root, "config", key, value)
    _git(root, "commit", "-q", "--allow-empty", "-m", "i")
    _git(root, "push", "-q", "-u", "origin", "main")
    return root


def _data_push(tmp_path):
    shared = DataRepo(_mirrored(tmp_path, "owlbear-data", "https://github.com/maba-pag/owlbear-data.git"))
    (shared.root / "note.md").write_text("n\n")
    with shared.locked():
        assert shared.publish(shared.root / "note.md", "a note") == ""


def _data_clone(_tmp_path):
    with pytest.raises(data_repo.DataRepoError, match="cloning"):  # the tests' offline rewrite leaves nothing to clone
        data_place.provision("https://github.com/maba-pag/owlbear-data.git")


def _pack_push(tmp_path):
    root = _mirrored(tmp_path, "owlbear", "https://github.com/maba-pag/owlbear.git")
    made = _git(root, "commit-tree", "-m", "update", "HEAD^{tree}", "-p", "HEAD").strip()
    pack_git.push(pack_git.Source(root, "maba-pag/owlbear", made), made, "owlbear/pack-update")


NOT_A_PROJECTS = {  # each reaches its own repository's account by TD-402's rule, never the project's or the active one
    "a data push": (_data_push, {"push"}),
    "the data clone": (_data_clone, {"clone"}),
    "a pack push": (_pack_push, {"ls-remote", "push"}),
}


@pytest.mark.parametrize("case", NOT_A_PROJECTS)
def test_each_write_that_is_not_a_projects_runs_as_its_own_repositorys_account(
    case, fake_gh, git_runs, tmp_path, monkeypatch
):
    (entry, verbs), owner = NOT_A_PROJECTS[case], "maba-pag"  # owns the data and pack repositories
    fake_gh.set(ACCOUNTS, {"github.com": "boecht"})
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"github_account": "octo-writer"}))
    entry(tmp_path)
    assert verbs <= set(git_runs.verbs())
    for argv, environment, _ in git_runs.seen:
        assert argv[1:3] == ("-c", "credential.helper=")
        assert environment["GH_TOKEN"] == f"tok-{owner}"


REPO_VIEW = ["repo", "view", "--json", "nameWithOwner,viewerPermission"]


@pytest.mark.parametrize(("pushes", "ok"), [("maba-pag", False), ("octo-writer", True)])
def test_readiness_asks_whether_the_projects_account_can_push_not_the_active_one(
    pushes, ok, fake_gh, tmp_path, monkeypatch
):
    """Only the account the push answers for counts: maba-pag is active, the project names octo-writer."""
    can = {f"tok-{x}": {"nameWithOwner": "acme/tools", "viewerPermission": "ADMIN" if x == pushes else "READ"}
           for x in ("maba-pag", "octo-writer")}  # fmt: skip
    fake_gh.set(ACCOUNTS, {"github.com": "maba-pag"}, [{"has": REPO_VIEW, "out": "{}", "by_token": can}])
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"github_account": "octo-writer"}))
    store, repo = _project(tmp_path)
    checks = readiness.publishing("github.com", git_files.probe_in(repo), None, github_writer.of(store, repo))
    said = {c.name: c for c in checks}
    assert said["github sign-in"].detail == "writes as octo-writer (the setting names it)"
    assert (said["repository"].ok, said["repository"].detail) == (ok, f"acme/tools: {'ADMIN' if ok else 'READ'}")
    assert not [c for c in fake_gh.calls() if c["argv"][:2] == ["auth", "status"] and "--json" not in c["argv"]]


@pytest.mark.parametrize(("host", "token"), [("github.com", "GH_TOKEN"), ("ghe.acme.test", "GH_ENTERPRISE_TOKEN")])
def test_setups_readiness_checks_the_origins_host_as_td_402s_rule_while_the_setting_is_unset(
    host, token, fake_gh, tmp_path, monkeypatch
):
    both = {"maba-pag": "success", "boecht": "success"}
    fake_gh.set({"github.com": both, host: both}, {"github.com": "maba-pag", host: "maba-pag"})
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"github_account": None}))
    store = Store(tmp_path / "store")
    store.root.mkdir()
    repo = _clone(tmp_path / "tools", f"https://{host}/boecht/tools.git")
    reached: list[str] = []
    monkeypatch.setattr(readiness, "reach", reached.append)
    checks = readiness.check(repo, None, github_writer.of(store, repo, detecting=True))
    sign_in = next(c for c in checks if c.name == "github sign-in")
    assert sign_in.detail == (
        "writes as boecht (the repository owner); the GitHub account setting is unset, so TD-402's rule picked it"
    )
    assert reached == [host]
    (view,) = [c for c in fake_gh.calls() if c["argv"][:2] == ["repo", "view"]]
    assert view[token] == "tok-boecht"
