"""Each place that makes a GitHub provider or client hands it the right account (TD-402).

Only ``gh`` is faked: each case runs a production entry to its first recorded launch and reads the token it carried.
The project names ``octo-writer``, which is neither the active account nor the repository's owner.
"""

import contextlib
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.models import Change, Names, Step, StepKind
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.commands import cli, runner, setup
from owlbear_delivery_next.github import gh_client
from owlbear_delivery_next.github.owlbear_issues import OwlbearIssues
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.impeccable_runs import pack_live
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.pds_runs import job
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.state_store import backlog_issues, profile_share
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import engine, queue

ACCOUNTS = {"github.com": {"maba-pag": "success", "boecht": "success", "octo-writer": "success"}}


def _git(cwd, *args):
    subprocess.run(("git", "-C", str(cwd), *args), capture_output=True, check=True)  # noqa: S603, S607


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
