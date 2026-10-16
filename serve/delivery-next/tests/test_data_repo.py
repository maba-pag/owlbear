import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api, change_record, cli, data_repo, local_home, profile_share, sessions, setup
from owlbear_delivery_next import host as host_module
from owlbear_delivery_next.codebase import CURRENT
from owlbear_delivery_next.config import Layer
from owlbear_delivery_next.github.provider import FailureCode, ProviderError, PullRequest
from owlbear_delivery_next.host import HostRecord
from owlbear_delivery_next.models import Brief, BriefDecision, Change, Decision, VisualState
from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.store import STORE_DIR, Store, StoreError

AUTH = {"authorization": "Bearer t"}
EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # sha256 of nothing


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def shared(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    remote, root = tmp_path / "remote.git", tmp_path / "owlbear-data"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(root))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(root, "config", key, value)
    git(root, "commit", "-q", "--allow-empty", "-m", "start")
    git(root, "push", "-q", "origin", "HEAD")
    home = tmp_path / "home"
    home.mkdir()
    (home / "data.json").write_text(json.dumps({"repository": str(root)}))
    monkeypatch.setattr(local_home, "root", lambda: home)
    return root, remote


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "shop"
    git(tmp_path, "init", "-q", "-b", "main", str(path))
    git(path, "commit", "--allow-empty", "-qm", "start")
    git(path, "remote", "add", "origin", "git@github.com:acme/shop-site.git")
    return path


def client(store: Store) -> TestClient:
    return TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers=AUTH)


def pushed(remote: Path, rel: str) -> str:
    return git(remote, "log", "--format=%s", "main", "--", rel)


def test_a_project_is_named_after_its_repository(repo: Path) -> None:
    assert data_repo.project_name(repo) == "shop-site"
    git(repo, "remote", "remove", "origin")
    assert data_repo.project_name(repo) == "shop"


def test_agents_remember_in_the_projects_folder_of_the_shared_repository(shared, repo) -> None:
    root, _ = shared
    store = Store.open(repo)
    folder = sessions.memory(store)

    assert folder == root / "shop-site" / "memory"
    assert folder.is_dir()
    (folder / "pending.md").write_text("---\ntitle: x\n---\n")  # curation commits entries, not settings saves
    assert store.shared.pending() == ""
    assert git(repo, "status", "--porcelain") == ""


def test_without_a_shared_repository_agents_have_no_memory_and_the_clone_gets_none(repo) -> None:
    assert sessions.memory(Store.open(repo)) is None
    assert not (repo / ".owlbear").exists()


def test_settings_live_in_the_shared_repository_and_each_save_is_committed_and_pushed(shared, repo) -> None:
    root, remote = shared
    store = Store.open(repo)
    assert (store.config_path, store.global_path) == (root / "shop-site" / "config.json", root / "config.json")

    project = client(store).put("/api/next/config/project", json={"rev": EMPTY, "layer": {"widths": [1440]}})
    glob = client(store).put("/api/next/config/global", json={"rev": EMPTY, "layer": {"widths": [1366]}})

    assert (project.status_code, project.json()["notice"]) == (200, "")
    assert (glob.status_code, glob.json()["notice"]) == (200, "")
    assert pushed(remote, "shop-site/config.json")
    assert pushed(remote, "config.json")
    assert git(root, "status", "--porcelain") == ""
    assert Store.open(repo).settings().widths == [1440]
    git(repo, "remote", "set-url", "origin", "https://github.com/acme/blog.git")
    assert Store.open(repo).settings().widths == [1366]  # another project sees the global layer


def test_a_failed_push_keeps_the_commit_and_says_so(shared, repo) -> None:
    root, _ = shared
    git(root, "remote", "remove", "origin")
    c = client(Store.open(repo))
    got = c.put("/api/next/config/project", json={"rev": EMPTY, "layer": {"widths": [1440]}})

    assert got.status_code == 200
    assert "push" in got.json()["notice"]
    assert git(root, "log", "--format=%s", "-1", "--", "shop-site/config.json")
    assert "not pushed" in c.get("/api/next/config").json()["notice"]  # stays visible after reload


def test_a_clones_own_settings_move_into_the_shared_repository_once(shared, repo) -> None:
    root, remote = shared
    local = repo / ".git" / STORE_DIR / "config.json"
    local.parent.mkdir(parents=True)
    local.write_text(json.dumps({"format": 1, "widths": [1600]}))

    assert Store.open(repo).settings().widths == [1600]
    assert json.loads((root / "shop-site" / "config.json").read_text())["widths"] == [1600]
    assert not local.exists()
    assert local.with_name("config.json.moved").exists()  # the recovery copy stays
    assert pushed(remote, "shop-site/config.json")


@pytest.mark.usefixtures("shared")
def test_another_repository_of_the_same_name_is_refused(repo) -> None:
    Store.open(repo)
    git(repo, "remote", "set-url", "origin", "https://gitlab.com/other/shop-site.git")
    with pytest.raises(StoreError, match=r"belongs to github\.com/acme/shop-site"):
        Store.open(repo)
    git(repo, "remote", "set-url", "origin", "https://github.com/acme/shop-site.git")  # same repository by https
    assert Store.open(repo).name == "shop-site"


def test_an_unchanged_save_pushes_what_an_earlier_save_could_not(shared, repo) -> None:
    root, remote = shared
    url = git(root, "remote", "get-url", "origin")
    git(root, "remote", "set-url", "origin", str(root.parent / "gone.git"))
    c = client(Store.open(repo))
    first = c.put("/api/next/config/project", json={"rev": EMPTY, "layer": {"widths": [1440]}})
    assert "push" in first.json()["notice"]
    git(root, "remote", "set-url", "origin", url)
    again = c.put("/api/next/config/project", json={"rev": first.json()["project_rev"], "layer": {"widths": [1440]}})
    assert again.json()["notice"] == ""
    assert pushed(remote, "shop-site/config.json")


def test_old_role_overrides_reach_the_shared_layer_without_replacing_its_values(shared, repo) -> None:
    root, _ = shared
    Store.open(repo).update_config(lambda cur: cur.model_copy(update={"widths": [1440]}))
    old = repo / ".git" / STORE_DIR / "profile.json"
    old.write_text(json.dumps({"format": 1, "roles": {"builder": {"model": "m-old", "effort": "low"}}}))

    layer = json.loads((root / "shop-site" / "config.json").read_text())
    assert Store.open(repo).settings().agents["builder"].model == "m-old"
    assert json.loads((root / "shop-site" / "config.json").read_text())["widths"] == layer["widths"] == [1440]


def test_the_profile_lives_in_the_shared_folder_and_a_clones_own_moves_there_once(shared, repo) -> None:
    root, remote = shared
    old = Store.open(repo).root / "profile.json"
    old.write_text(Profile(version=3).model_dump_json())
    store = Store.open(repo)
    assert (store.read_profile().version, old.exists(), old.with_name("profile.json.moved").exists()) == (
        3,
        False,
        True,
    )
    assert pushed(remote, "shop-site/profile.json") == "settings: shop-site: project profile moved from its clone"
    assert store.write_profile(Profile(version=4)) == ""
    assert json.loads((root / "shop-site" / "profile.json").read_text())["version"] == 4
    assert pushed(remote, "shop-site/profile.json").splitlines()[0] == "settings: shop-site: project profile"


@pytest.mark.usefixtures("shared")
def test_a_shared_profile_is_detected_once_in_each_clone_and_again_after_a_failure(repo, monkeypatch) -> None:
    store, seen = Store.open(repo), []
    store.write_profile(Profile(version=2))

    def detect(_repo, _gh, prev):
        seen.append(prev.version)
        if len(seen) == 1:
            raise ProviderError(FailureCode.UNAVAILABLE, "repo view", "offline", retry_safe=True)
        if len(seen) == 2:
            store.write_profile(Profile(version=5))  # another clone saves meanwhile: its profile stays
        return prev.model_copy(update={"version": prev.version + 1})

    monkeypatch.setattr(profile_share.profile, "detect", detect)
    monkeypatch.setattr(profile_share.profile, "provider", lambda *_a: None)
    assert [profile_share.checked(store, repo).version for _ in range(2)] == [2, 2]
    assert [profile_share.checked(store, repo).version for _ in range(2)] == [6, 6]
    assert (seen, Store.open(repo).read_profile().version) == ([2, 2, 5], 6)


def test_a_format_one_profile_moves_to_the_shared_folder_only_after_its_roles_did(shared, repo) -> None:
    root, _ = shared
    old = Store.open(repo).root / "profile.json"
    old.write_text(json.dumps({"format": 1, "roles": {"builder": {"model": "m-old", "effort": "low"}}}))
    (root / "shop-site" / "config.json").write_text("{damaged")
    Store.open(repo)
    assert (old.exists(), (root / "shop-site" / "profile.json").exists()) == (True, False)
    (root / "shop-site" / "config.json").write_text(Layer().model_dump_json())
    assert Store.open(repo).settings().agents["builder"].model == "m-old"
    assert (old.exists(), (root / "shop-site" / "profile.json").exists()) == (False, True)


def test_a_finished_change_leaves_its_record_in_the_shared_folder_once(shared, repo) -> None:
    root, remote = shared
    store, at = Store.open(repo), datetime(2026, 10, 15, 9, tzinfo=UTC)
    decided = BriefDecision(question="Limit the notes?", answer="yes", origin="decided")
    state = VisualState(name="full", path="/notes", expect="a counter shows 800")
    approved = Brief(version=2, title="Notes", outcome="Owners keep notes", decisions=[decided], visual=[state])
    c = Change(slug="notes", handle="c4", brief=Brief(version=2, approved_at=at, approved=[approved]))
    c.decisions.append(Decision(text="keep 800 characters", origin="decided", at=at))
    c.spend = c.spend.plus({"credits": 3.5}, "s1")
    pr = PullRequest(
        repository="acme/shop-site", number=7, node_id="n", url="https://x/pull/7", head_branch="owlbear/notes",
        head_sha="a" * 40, base_branch="main", draft=False, state="closed", merged=True, merge_commit_sha="b" * 40,
    )  # fmt: skip
    assert change_record.save(store, c, pr, at) == ""
    assert change_record.save(store, c, pr, at + timedelta(days=1)) == ""  # a cleanup run again rewrites it
    folder = root / "shop-site" / "changes"
    assert [p.name for p in folder.iterdir()] == ["20261015-090000-notes.json"]
    record = json.loads((folder / "20261015-090000-notes.json").read_text())
    assert (record["outcome"], record["pr"]["number"], record["brief"]["title"]) == ("merged", 7, "Notes")
    assert (record["brief"]["decisions"][0]["answer"], record["decisions"][0]["text"]) == ("yes", "keep 800 characters")
    assert (record["brief"]["visual"][0]["expect"], record["spend"]["credits"]) == ("a counter shows 800", 3.5)
    assert pushed(remote, "shop-site/changes/20261015-090000-notes.json").splitlines()[-1] == (
        "changes: shop-site: notes merged"
    )
    assert change_record.save(store, Change(slug="never"), None, at) == ""  # never approved: no record
    assert not (folder / "20261015-090000-never.json").exists()


def test_without_a_pointer_the_settings_stay_in_the_clone(repo) -> None:
    store = Store.open(repo)
    assert (store.config_path, store.global_path) == (store.root / "config.json", None)
    got = client(store).put("/api/next/config/global", json={"rev": EMPTY, "layer": {"widths": [1366]}})
    assert got.status_code == 409


def test_a_pointer_to_no_repository_stops_delivery(tmp_path: Path, repo, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "data.json").write_text(json.dumps({"repository": str(tmp_path / "missing")}))
    monkeypatch.setattr(local_home, "root", lambda: home)
    with pytest.raises(StoreError, match="not a git repository"):
        Store.open(repo)


def test_the_old_common_pointer_moves_to_data_once_and_a_data_pointer_wins(shared, repo, caplog) -> None:
    root, _ = shared
    home = data_repo.pointer().parent
    (home / "data.json").rename(home / "common.json")
    said = (home / "common.json").read_text()

    with caplog.at_level("WARNING", logger=data_repo.__name__):
        assert Store.open(repo).shared == data_repo.DataRepo(root)
        assert Store.open(repo).shared == data_repo.DataRepo(root)
    assert ((home / "data.json").read_text(), (home / "common.json").exists()) == (said, False)
    assert sorted(p.name for p in home.iterdir()) == ["data.json"]  # no temporary file left
    assert [r.getMessage() for r in caplog.records] == [
        f"moved the shared repository's pointer {home / 'common.json'} to {home / 'data.json'}"
    ]
    (home / "common.json").write_text(json.dumps({"repository": "/elsewhere"}))  # the new pointer wins; old kept
    assert (data_repo.locate(), (home / "common.json").exists()) == (data_repo.DataRepo(root), True)


def test_recording_a_repository_moves_the_old_pointer_away(tmp_path: Path) -> None:
    home, local = data_repo.pointer().parent, tmp_path / "local-data"
    git(tmp_path, "init", "-q", "-b", "main", str(local))
    (home / "common.json").write_text(json.dumps({"repository": str(tmp_path / "gone")}))
    assert str(local) in cli.show_data(local)
    assert sorted(p.name for p in home.iterdir()) == ["data.json"]
    assert data_repo.locate() == data_repo.DataRepo(local.resolve())


def test_the_cli_records_the_shared_repository_and_refuses_a_plain_folder(tmp_path: Path, repo) -> None:
    plain, local = tmp_path / "plain", tmp_path / "local-data"
    plain.mkdir()
    git(tmp_path, "init", "-q", "-b", "main", str(local))
    assert "No shared settings repository" in cli.show_data(None)
    assert "not a git repository" in cli.show_data(plain)
    assert str(local) in cli.show_data(local)
    assert Store.open(repo).global_path == local / "config.json"
    assert (local / "shop-site" / "repository").read_text() == "github.com/acme/shop-site\n"


def test_the_hosts_runners_read_the_hosts_shared_repository(shared, repo, monkeypatch) -> None:
    root, _ = shared
    seen: list[dict] = []

    class Proc:
        pid = 1

        def wait(self) -> None:
            return None

    def popen(*_a: object, env: dict, **_k: object) -> Proc:
        seen.append(env)
        return Proc()

    store = Store.open(repo)
    (store.root / "changes" / "c1").mkdir(parents=True)
    monkeypatch.setattr(host_module.subprocess, "Popen", popen)
    host_module.Host(store, repo).spawn("c1")
    assert seen[0][data_repo.VIEW] == str(root)
    assert data_repo.VIEW not in os.environ  # the host's own environment is untouched


def test_a_save_waits_for_the_shared_lock_only_so_long(shared, repo, monkeypatch) -> None:
    root, _ = shared
    store = Store.open(repo)
    monkeypatch.setattr(data_repo, "LOCK_SECONDS", 0.2)
    with data_repo.DataRepo(root).locked(), pytest.raises(StoreError, match="another settings save"):
        store.update_config(lambda cur: cur)


def claimed_by_another(root: Path, name: str = "shop-site") -> None:
    (root / name).mkdir()
    (root / name / "repository").write_text("github.com/other/shop-site\n")
    git(root, "add", name)
    git(root, "commit", "-qm", "other")


def renamer(store: Store, repo: Path, **kw: object) -> TestClient:
    found = host_module.Host(store, repo, **kw)
    return TestClient(api.create_app(store, "t", found), base_url="http://127.0.0.1", headers=AUTH)


def test_a_taken_folder_name_is_asked_for_at_setup_and_kept_for_the_repository(shared, repo) -> None:
    root, remote = shared
    claimed_by_another(root)
    answers, said = iter(["bad name", "shop-site", "acme-shop"]), []

    assert setup.project_folder(repo, "", lambda _q: next(answers), said.append)
    assert any("belongs to github.com/other/shop-site" in s for s in said)
    assert any("no folder name" in s for s in said)
    assert pushed(remote, "acme-shop/repository")
    store = Store.open(repo)
    assert (store.name, store.config_path) == ("acme-shop", root / "acme-shop" / "config.json")
    assert setup.project_folder(repo, "", lambda _q: pytest.fail("asked again"), said.append)


def test_without_an_answer_setup_names_the_folder_flag_and_stops(shared, repo, capsys) -> None:
    root, _ = shared
    claimed_by_another(root)
    assert cli.main(["--repo", str(repo), "setup"]) == 1  # no terminal under pytest: nothing is asked
    assert "--folder NAME" in capsys.readouterr().out
    said: list[str] = []
    assert not setup.project_folder(repo, "", lambda _q: "", said.append)
    assert "--folder NAME" in said[-1]
    assert not setup.project_folder(repo, "shop-site", lambda _q: pytest.fail("asked"), said.append)
    assert setup.project_folder(repo, "acme-shop", lambda _q: pytest.fail("asked"), said.append)
    assert Store.open(repo).name == "acme-shop"


def test_renaming_moves_the_whole_folder_commits_pushes_and_is_used_from_then_on(shared, repo) -> None:
    root, remote = shared
    store = Store.open(repo)
    store.update_config(lambda cur: cur.model_copy(update={"widths": [1440]}))
    memory = sessions.memory(store)
    (memory / "kept.md").write_text("kept\n")
    git(root, "add", "shop-site/memory/kept.md")
    git(root, "commit", "-qm", "memory")
    (memory / "pending.md").write_text("not curated\n")

    got = renamer(store, repo).put("/api/next/config/folder", json={"name": "acme-shop"})

    assert (got.status_code, got.json()["folder"], got.json()["notice"]) == (200, "acme-shop", "")
    assert not (root / "shop-site").exists()
    assert (root / "acme-shop" / "memory" / "pending.md").exists()
    assert git(root, "status", "--porcelain") == "?? acme-shop/memory/pending.md"  # uncurated memory stays so
    move = "settings: the folder shop-site is now acme-shop"
    assert pushed(remote, "acme-shop/memory/kept.md").splitlines()[0] == move
    assert git(remote, "ls-tree", "-r", "--name-only", "main").split() == [
        "acme-shop/config.json", "acme-shop/memory/kept.md", "acme-shop/repository"
    ]  # fmt: skip
    assert store.config_path == root / "acme-shop" / "config.json"
    reopened = Store.open(repo)
    assert (reopened.name, reopened.settings().widths) == ("acme-shop", [1440])


def test_a_rename_to_a_taken_or_unsafe_name_is_refused(shared, repo) -> None:
    root, _ = shared
    store = Store.open(repo)
    claimed_by_another(root, "other")
    c = renamer(store, repo)
    taken = c.put("/api/next/config/folder", json={"name": "other"})
    unsafe = c.put("/api/next/config/folder", json={"name": "../x"})

    assert (taken.status_code, unsafe.status_code) == (409, 409)
    assert "belongs to github.com/other/shop-site" in taken.json()["detail"]
    assert "no folder name" in unsafe.json()["detail"]
    assert (store.name, Store.open(repo).name) == ("shop-site", "shop-site")


def test_a_rename_waits_for_running_steps_and_a_host_picks_up_a_rename_made_elsewhere(shared, repo) -> None:
    root, _ = shared
    store = Store.open(repo)
    (store.root / "changes" / "c1").mkdir(parents=True)
    record = host_module.RunnerRecord(pid=4242, created=None, started_at=datetime.now(UTC))
    (store.root / "changes" / "c1" / "runner.json").write_text(record.model_dump_json())
    (store.root / "changes" / "c1" / "change.json").write_text("{}")  # listed; the host reports it unloadable

    got = renamer(store, repo, alive=lambda _p, _c: True).put("/api/next/config/folder", json={"name": "acme-shop"})

    assert got.status_code == 409
    assert "steps of c1 are running" in got.json()["detail"]
    assert (root / "shop-site").is_dir()
    with data_repo.DataRepo(root).locked():
        data_repo.DataRepo(root).rename("shop-site", "acme-shop")  # as a pull of another machine's rename leaves it
    host = host_module.Host(store, repo, alive=lambda _p, _c: True)
    host.tick()
    assert store.name == "acme-shop"
