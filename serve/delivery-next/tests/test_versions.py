"""OwlBear's versions on this machine (self-update build §3, §4, §5.1): choosing, fetching, installing, checking.

Git runs on disposable local repositories; the environment step is replaced, the selfcheck runs for real once.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import registry, selfcheck, versions
from owlbear_delivery_next.machine_host.versions import Choice
from owlbear_delivery_next.project_host import pages
from owlbear_delivery_next.settings.config import CONFIG_FORMAT
from owlbear_delivery_next.state_store import project_home
from owlbear_delivery_next.state_store.database import STORE_FORMAT


def always(_older: str, _newer: str) -> bool:
    return True


def never(_older: str, _newer: str) -> bool:
    return False


TAGS = {"v0.1": "a", "v0.2": "b", "v0.10": "c", "notes": "x", "v1.2.3": "y"}


def test_a_minor_machine_takes_the_newest_version_numerically():
    assert versions.choose(TAGS, "minor", None, "", always) == Choice("v0.10", "c")
    assert versions.choose(TAGS, "minor", (0, 2), "a", always) == Choice("v0.10", "c")


def test_never_backwards_a_version_at_or_below_the_mark_is_never_taken():
    assert versions.choose(TAGS, "minor", (0, 10), "c", always) is None
    assert versions.choose(TAGS, "minor", (0, 11), "z", always) is None  # a mark above every tag


def test_a_version_that_does_not_descend_from_the_running_commit_waits_for_a_later_one():
    choice = versions.choose(TAGS, "minor", None, "ahead", never)
    assert choice is not None
    said = "v0.10 does not descend from the running commit ahead; a later version is taken"
    assert (choice.tag, choice.notes) == ("", (said,))


def test_a_major_machine_takes_only_major_versions_and_v0_1_until_v1_exists():
    """TD-300, TD-369."""
    assert versions.choose(TAGS, "major", None, "", always) == Choice("v0.1", "a")
    with_major = TAGS | {"v1": "d", "v1.0": "d", "v1.1": "e"}
    assert versions.choose(with_major, "major", None, "", always) == Choice("v1", "d")
    assert versions.choose(with_major, "minor", None, "", always) == Choice("v1.1", "e")


def test_a_major_and_its_dot_zero_on_different_commits_are_neither_taken_and_said():
    choice = versions.choose({"v0.1": "a", "v1": "d", "v1.0": "e"}, "minor", None, "", always)
    assert choice == Choice("v0.1", "a", ("v1 and v1.0 name different commits; neither is taken",))


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    done = subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture
def origin(tmp_path, monkeypatch) -> Path:
    """OwlBear's repository: three commits on main, the first two tagged annotated, one lightweight tag."""
    root = tmp_path / "origin"
    git(tmp_path, "init", "-q", "-b", "main", str(root))
    for n in range(3):
        (root / "f.txt").write_text(f"{n}\n")
        git(root, "add", "-A")
        git(root, "commit", "-qm", f"c{n}")
        if n < 2:
            git(root, "tag", "-a", f"v0.{n + 1}", "-m", f"v0.{n + 1}")
    git(root, "tag", "v0.9")  # lightweight: no version
    monkeypatch.setattr(versions, "URL", str(root))
    return root


def runtime_at(origin: Path, commit: str) -> Path:
    """A legacy runtime: a clone of the repository at *commit*."""
    runtime = local_home.root() / local_home.RUNTIME
    git(origin.parent, "clone", "-q", str(origin), str(runtime))
    git(runtime, "checkout", "-q", "--detach", commit)
    return runtime


def test_repo_git_fetches_only_annotated_tags_and_the_legacy_runtime_takes_the_newest_descendant(origin):
    runtime_at(origin, git(origin, "rev-parse", "v0.1^{commit}"))

    choice = versions.target()

    assert (local_home.root() / versions.REPO / "HEAD").is_file()
    assert choice == Choice("v0.2", git(origin, "rev-parse", "v0.2^{commit}"))
    assert set(versions.fetch(local_home.root() / versions.REPO)) == {"v0.1", "v0.2"}


def test_a_legacy_runtime_ahead_of_the_newest_version_waits(origin):
    runtime_at(origin, git(origin, "rev-parse", "main"))

    choice = versions.target()

    assert choice is not None
    assert choice.tag == ""
    assert "does not descend from the running commit" in choice.notes[0]


def test_the_mark_in_machine_json_keeps_a_lower_version_from_being_taken(origin):
    runtime_at(origin, git(origin, "rev-parse", "v0.1^{commit}"))
    with registry.locked():
        saved = registry.load()
        saved.active = "v0.2"
        registry.save(saved)

    assert versions.target() is None


@pytest.fixture
def installing(origin, monkeypatch) -> SimpleNamespace:  # noqa: ARG001 - the repository it installs from
    """Installs whose environment step only makes the folder, and whose selfcheck says what the test sets."""
    said = SimpleNamespace(check="", synced=[])
    monkeypatch.setattr(versions, "_sync", lambda folder: (said.synced.append(folder), (folder / ".venv").mkdir()))
    monkeypatch.setattr(versions, "selfcheck", lambda _folder: said.check)
    versions.repo()
    versions.fetch(local_home.root() / versions.REPO)
    return said


def test_a_version_installs_beside_the_others_as_a_detached_worktree_at_its_commit(origin, installing):
    commit = git(origin, "rev-parse", "v0.2^{commit}")

    folder = versions.install(Choice("v0.2", commit))

    assert folder == local_home.root() / local_home.VERSIONS / "v0.2"
    assert git(folder, "rev-parse", "HEAD") == commit
    assert (folder / "f.txt").read_text() == "1\n"
    assert versions.install(Choice("v0.2", commit)) == folder  # installed and checked before: not again
    assert len(installing.synced) == 1


def test_a_failed_selfcheck_removes_the_install(origin, installing):
    installing.check = "its store has format 9, newer than this version's 7"

    with pytest.raises(versions.VersionError, match=r"v0\.2 failed its selfcheck: its store has format 9"):
        versions.install(Choice("v0.2", git(origin, "rev-parse", "v0.2^{commit}")))

    assert not (local_home.root() / local_home.VERSIONS / "v0.2").exists()
    assert "v0.2" not in git(local_home.root() / versions.REPO, "worktree", "list")


def test_an_install_waits_while_the_disk_is_nearly_full(origin, installing, monkeypatch):
    monkeypatch.setattr(versions.shutil, "disk_usage", lambda _p: SimpleNamespace(free=versions.FREE - 1))

    with pytest.raises(versions.VersionError, match=r"needs 2 GB free"):
        versions.install(Choice("v0.2", git(origin, "rev-parse", "v0.2^{commit}")))

    assert installing.synced == []


def test_the_versions_command_says_what_runs_and_what_comes_next(origin):
    runtime_at(origin, git(origin, "rev-parse", "v0.1^{commit}"))
    lines: list[str] = []

    assert versions.report(lines.append) == 0

    assert lines[0].startswith("running: no installed version at ")
    assert lines[1].startswith("next: v0.2 at ")


def registered(tmp_path: Path, marker: int | None = None, config: int | None = None) -> Path:
    clone = tmp_path / "clone"
    git(tmp_path, "init", "-q", str(clone))
    entry = registry.register(clone)
    store = local_home.root() / "projects" / entry.id
    store.mkdir(parents=True, exist_ok=True)
    if marker is not None:
        (store / "format").write_text(f"{marker}\n")
    if config is not None:
        (store / "config.json").write_text(json.dumps({"format": config}))
    return clone


def test_the_selfcheck_passes_on_projects_whose_formats_it_reads(tmp_path):
    registered(tmp_path, marker=STORE_FORMAT)

    assert selfcheck.problems() == []


def test_the_selfcheck_refuses_a_store_or_settings_newer_than_it_reads(tmp_path):
    clone = registered(tmp_path, marker=99, config=99)

    found = selfcheck.problems()

    assert f"{clone}: its store has format 99, newer than this version's {STORE_FORMAT}" in found
    assert any("have format 99, newer" in line for line in found)


def test_the_selfcheck_runs_as_its_own_process_and_says_it_passed():
    done = subprocess.run(
        [sys.executable, "-m", "owlbear_delivery_next", "selfcheck"], capture_output=True, text=True, check=False
    )
    assert (done.returncode, done.stdout) == (0, "selfcheck passed\n")


def test_the_selfcheck_creates_nothing_on_a_machine_without_owlbear():
    home = local_home.root()
    shutil.rmtree(home)

    assert selfcheck.problems() == []
    assert not home.exists()


def test_the_selfcheck_refuses_a_missing_page_asset(monkeypatch):
    monkeypatch.setattr(pages, "lit_files", lambda: {"lit-html.js": "x", "gone.js": "y"})

    assert selfcheck.problems() == ["the pages' assets are missing: vendor/lit-html/gone.js"]


def test_the_selfcheck_refuses_a_page_module_a_page_names_but_the_version_lacks(monkeypatch):
    own = pages.page_files()
    monkeypatch.setattr(pages, "page_files", lambda: {k: v for k, v in own.items() if k != ("changes", "main.mjs")})

    assert selfcheck.problems() == ["the pages' assets are missing: pages/changes/main.mjs"]


def test_the_selfcheck_refuses_a_module_only_another_module_imports(monkeypatch):
    own = pages.page_files()
    monkeypatch.setattr(pages, "page_files", lambda: {k: v for k, v in own.items() if k != ("changes", "list.mjs")})

    assert selfcheck.problems() == ["the pages' assets are missing: pages/changes/list.mjs"]


def test_the_selfcheck_refuses_a_clones_unmoved_settings_newer_than_it_reads(tmp_path):
    clone = registered(tmp_path)
    folder = project_home.clone_dir(clone)
    folder.mkdir(exist_ok=True)
    (folder / "config.json").write_text(json.dumps({"format": 99}))

    found = selfcheck.problems()

    said = f"its settings in {folder / 'config.json'} have format 99, newer than this version's {CONFIG_FORMAT}"
    assert found == [f"{clone}: {said}"]


@pytest.mark.usefixtures("origin")
def test_a_runtime_whose_commit_cannot_be_read_takes_nothing():
    (local_home.root() / local_home.RUNTIME).mkdir()

    with pytest.raises(versions.VersionError, match="rev-parse"):
        versions.target()


def test_a_tag_of_a_tag_is_peeled_to_its_commit(origin):
    git(origin, "tag", "-a", "v0.3", "v0.2", "-m", "v0.3 names v0.2's tag")

    tags = versions.fetch(versions.repo())

    assert tags["v0.3"] == git(origin, "rev-parse", "v0.2^{commit}")


def test_an_install_at_another_commit_is_made_again(origin, installing):
    old, new = git(origin, "rev-parse", "v0.1^{commit}"), git(origin, "rev-parse", "v0.2^{commit}")
    folder = versions.install(Choice("v0.2", old))

    assert versions.install(Choice("v0.2", new)) == folder
    assert git(folder, "rev-parse", "HEAD") == new
    assert len(installing.synced) == 2


def test_a_format_3_machine_json_reads_with_no_version_ever_active():
    (local_home.root() / registry.MACHINE).write_text(json.dumps({"format": 3, "projects": []}))

    assert registry.load().active == ""
