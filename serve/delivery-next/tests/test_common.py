import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api, cli, common, runner
from owlbear_delivery_next import host as host_module
from owlbear_delivery_next.host import HostRecord
from owlbear_delivery_next.store import STORE_DIR, Store, StoreError

AUTH = {"authorization": "Bearer t"}
EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # sha256 of nothing


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC))  # noqa: S106


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def shared(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    remote, root = tmp_path / "remote.git", tmp_path / "owlbear-common"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(root))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(root, "config", key, value)
    git(root, "commit", "-q", "--allow-empty", "-m", "start")
    git(root, "push", "-q", "origin", "HEAD")
    home = tmp_path / "home"
    home.mkdir()
    (home / "common.json").write_text(json.dumps({"repository": str(root)}))
    monkeypatch.setenv("OWLBEAR_HOME", str(home))
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
    assert common.project_name(repo) == "shop-site"
    git(repo, "remote", "remove", "origin")
    assert common.project_name(repo) == "shop"


def test_agents_remember_in_the_projects_folder_of_the_shared_repository(shared, repo) -> None:
    root, _ = shared
    store = Store.open(repo)
    folder = runner._memory(store)  # noqa: SLF001

    assert folder == root / "shop-site" / "memory"
    assert folder.is_dir()
    (folder / "pending.md").write_text("---\ntitle: x\n---\n")  # curation commits entries, not settings saves
    assert store.shared.pending() == ""
    assert git(repo, "status", "--porcelain") == ""


def test_without_a_shared_repository_agents_have_no_memory_and_the_clone_gets_none(repo) -> None:
    assert runner._memory(Store.open(repo)) is None  # noqa: SLF001
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


def test_without_a_pointer_the_settings_stay_in_the_clone(repo) -> None:
    store = Store.open(repo)
    assert (store.config_path, store.global_path) == (store.root / "config.json", None)
    got = client(store).put("/api/next/config/global", json={"rev": EMPTY, "layer": {"widths": [1366]}})
    assert got.status_code == 409


def test_a_pointer_to_no_repository_stops_delivery(tmp_path: Path, repo, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "common.json").write_text(json.dumps({"repository": str(tmp_path / "missing")}))
    monkeypatch.setenv("OWLBEAR_HOME", str(home))
    with pytest.raises(StoreError, match="not a git repository"):
        Store.open(repo)


def test_the_cli_records_the_shared_repository_and_refuses_a_plain_folder(tmp_path: Path, repo) -> None:
    plain, local = tmp_path / "plain", tmp_path / "local-common"
    plain.mkdir()
    git(tmp_path, "init", "-q", "-b", "main", str(local))
    assert "No shared settings repository" in cli.show_common(None)
    assert "not a git repository" in cli.show_common(plain)
    assert str(local) in cli.show_common(local)
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
    assert seen[0][common.VIEW] == str(root)
    assert common.VIEW not in os.environ  # the host's own environment is untouched


def test_a_save_waits_for_the_shared_lock_only_so_long(shared, repo, monkeypatch) -> None:
    root, _ = shared
    store = Store.open(repo)
    monkeypatch.setattr(common, "LOCK_SECONDS", 0.2)
    with common.Common(root).locked(), pytest.raises(StoreError, match="another settings save"):
        store.update_config(lambda cur: cur)
