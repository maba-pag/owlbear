"""OwlBear's versions on this machine (self-update build §3, §4, §5.1): choosing, fetching, installing, checking.

Git runs on disposable local repositories; the environment step is replaced, the selfcheck runs for real once, and a
version's interpreter is a script that records how its Impeccable was installed.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.local_system import codebase, data_place, data_repo, local_home
from owlbear_delivery_next.machine_host import impeccable, selfcheck, versions
from owlbear_delivery_next.machine_host.versions import Choice
from owlbear_delivery_next.project_host import pages
from owlbear_delivery_next.settings.config import CONFIG_FORMAT
from owlbear_delivery_next.state_store import project_home, registry
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
    if (cwd / "HEAD").is_file():  # a bare repository: safe.bareRepository=explicit wants it named
        args = ("--git-dir=.", *args)
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
    monkeypatch.setattr(codebase, "URL", str(root))
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
    """Installs whose environment is an interpreter recording the pack it installs, and whose selfcheck says as set.

    The interpreter writes its folder, its arguments and the manifest it finds there to ``packs.log``, and exits as
    ``pack-exit`` says.
    """
    log, code = local_home.root() / "packs.log", local_home.root() / "pack-exit"
    said = SimpleNamespace(check="", synced=[], packs=lambda: log.read_text().splitlines() if log.exists() else [])

    def sync(folder: Path) -> None:
        said.synced.append(folder)
        python = folder / ".venv" / "bin" / "python"
        python.parent.mkdir(parents=True)
        python.write_text(f'#!/bin/sh\necho "$(pwd -P)|$*|$(cat {versions.MANIFEST})" >> {log}\n'
                          f"exit $(cat {code} 2>/dev/null || echo 0)\n")  # fmt: skip
        python.chmod(0o755)

    monkeypatch.setattr(versions, "_sync", sync)
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


def released(origin: Path, tag: str, manifest: str | None, name: str = versions.MANIFEST) -> str:
    """A commit on main whose manifest at *name* is *manifest* (None: it has none), tagged *tag* unless empty."""
    for each in (versions.MANIFEST, versions.OLD_MANIFEST):
        (origin / each).unlink(missing_ok=True)
    path = origin / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if manifest is not None:
        path.write_text(manifest)
    (origin / "f.txt").write_text(f"{tag or 'untagged'}\n")
    git(origin, "add", "-A")
    git(origin, "commit", "-qm", tag or "untagged")
    if tag:
        git(origin, "tag", "-a", tag, "-m", tag)
    return git(origin, "rev-parse", "HEAD")


def test_a_version_is_ready_only_once_its_own_pack_is_installed_by_its_own_interpreter(origin, installing):
    commit = released(origin, "v0.3", '{"pack": "p-new"}')
    versions.fetch(versions.repo())

    folder = versions.install(Choice("v0.3", commit))
    versions.install(Choice("v0.3", commit))  # installed and checked before: its pack is installed again

    made = f'{folder.resolve()}|-m owlbear_delivery_next impeccable --install|{{"pack": "p-new"}}'
    assert installing.packs() == [made, made]
    assert len(installing.synced) == 1


def test_a_version_from_before_the_impeccable_rename_is_read_and_installed_by_its_old_names(origin, installing):
    commit = released(origin, "v0.3", '{"pack": "p-old"}', versions.OLD_MANIFEST)
    versions.fetch(versions.repo())

    assert versions.pins(commit) == {"pack": "p-old"}
    folder = versions.install(Choice("v0.3", commit))

    assert installing.packs() == [f"{folder.resolve()}|-m owlbear_delivery_next design-pack --install|"]


def test_a_version_whose_pack_fails_is_kept_unready_and_only_its_pack_is_tried_again(origin, installing):
    commit = git(origin, "rev-parse", "v0.2^{commit}")
    (local_home.root() / "pack-exit").write_text("1")

    with pytest.raises(versions.PackInstallError, match=r"v0\.2's Impeccable could not be installed"):
        versions.install(Choice("v0.2", commit))

    (local_home.root() / "pack-exit").write_text("0")
    assert versions.install(Choice("v0.2", commit)) == local_home.root() / local_home.VERSIONS / "v0.2"
    assert (len(installing.synced), len(installing.packs())) == (1, 2)


def at_v0_2(origin: Path) -> Path:
    """A runtime at v0.2, the highest version ever active, with updating by itself off."""
    runtime = runtime_at(origin, git(origin, "rev-parse", "v0.2^{commit}"))
    with registry.locked():
        saved = registry.load()
        saved.active, saved.settings = "v0.2", saved.settings.model_copy(update={"update_when_idle": False})
        registry.save(saved)
    return runtime


def test_upstream_ahead_without_an_owlbear_release_shows_no_newer_pack(origin):
    at_v0_2(origin)
    released(origin, "", '{"pack": "p-new"}')

    assert impeccable.look()["state"] == "none"


def test_a_release_pinning_another_pack_is_newer_with_updating_by_itself_off_and_starts_nothing(origin, monkeypatch):
    runtime = at_v0_2(origin)
    head = git(runtime, "rev-parse", "HEAD")
    released(origin, "v0.3", '{"pack": "p-new"}')
    fetched, target = [], versions.target
    monkeypatch.setattr(versions, "target", lambda: fetched.append(1) or target())

    said = impeccable.look()

    assert (said["state"], said["version"], said["pack"]) == ("newer", "v0.3", "p-new")
    assert said["running_pack"] == pack_files.manifest()["pack"]
    assert impeccable.look() == impeccable.release() == said  # within the day: what was kept, nothing fetched
    assert fetched == [1]
    assert impeccable.look(force=True)["checked_at"] is not None
    assert fetched == [1, 1]
    assert not (local_home.root() / local_home.VERSIONS).exists()  # nothing installed
    assert git(runtime, "rev-parse", "HEAD") == head


def test_a_release_pinning_the_same_pack_shows_nothing_and_an_unreadable_one_stays_unknown(origin):
    at_v0_2(origin)
    released(origin, "v0.3", json.dumps(pack_files.manifest()))

    assert impeccable.look()["state"] == "same"

    released(origin, "v0.4", None)
    said = impeccable.look(force=True)
    assert (said["state"], said["version"]) == ("unknown", "v0.4")
    assert "Impeccable is unreadable" in said["detail"]


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


def test_the_selfcheck_reads_settings_in_format_17_and_refuses_the_next_one(tmp_path):
    clone = registered(tmp_path)
    folder = project_home.clone_dir(clone)
    folder.mkdir(exist_ok=True)
    switched = {"format": 17, "load_user_instructions": True, "load_user_skills": False}
    (folder / "config.json").write_text(json.dumps(switched))
    assert selfcheck.problems() == []

    (folder / "config.json").write_text(json.dumps(switched | {"format": 18}))
    said = f"its settings in {folder / 'config.json'} have format 18, newer than this version's 17"
    assert selfcheck.problems() == [f"{clone}: {said}"]


def test_the_selfcheck_reads_the_default_shared_checkout_with_no_pointer(tmp_path):
    clone = registered(tmp_path)
    shared = data_repo.DataRepo(data_place.default())
    git(tmp_path, "init", "-q", str(shared.root))
    shared.global_path.parent.mkdir(parents=True, exist_ok=True)
    shared.global_path.write_text(json.dumps({"format": 99}))

    said = f"its settings in {shared.global_path} have format 99, newer than this version's {CONFIG_FORMAT}"
    assert selfcheck.problems() == [f"{clone}: {said}"]
    assert not (local_home.root() / "data.json").exists()  # read, never written


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
