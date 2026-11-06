"""OwlBear's versions on this machine (self-update build §3, §4, §5.1): choosing, fetching, installing, checking.

Git runs on disposable local repositories; the environment step is replaced, the selfcheck runs for real once, and a
version's interpreter is a script that records how its Impeccable was installed.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.local_system import codebase, data_place, data_repo, local_home
from owlbear_delivery_next.machine_host import command, environment, impeccable, selfcheck, update_checks, versions
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.machine_host.versions import Choice
from owlbear_delivery_next.project_host import pages
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.settings.config import CONFIG_FORMAT
from owlbear_delivery_next.state_store import project_home, registry, switched_authority
from owlbear_delivery_next.state_store.database import STORE_FORMAT, StoreError


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


OUT = "OUT begins\nwhat the command printed on stdout, in the middle\nOUT ends"
URL, TOKEN = "http://127.0.0.1:4321/", "t"  # the host's address and token
FAILING = {  # a command of an update that fails: the step it fails, and what the update says before that step's line
    "sync": ("building", ""),
    "selfcheck": ("selfcheck", "v0.2 failed its selfcheck: "),
    "design-pack": ("impeccable", "v0.2's Impeccable could not be installed: "),
}


@pytest.fixture
def updating(origin, monkeypatch) -> SimpleNamespace:
    """A machine at v0.1 updating to v0.2 through the real versions and install; ``said`` is its host log."""
    runtime_at(origin, git(origin, "rev-parse", "v0.1^{commit}"))
    record = HostRecord(url=URL, token=TOKEN, pid=1, started_at=datetime.now(UTC), code="c")
    machine, said = Machine(record, paused=False), []
    monkeypatch.setattr(machine, "say", said.append)
    return SimpleNamespace(machine=machine, said=said)


def ended(machine: Machine, step: str) -> tuple[str, str, list[str]]:
    """The update's detail, *step*'s line and the lines the update's log has for it."""
    report = machine.updater.report()
    line = next(s["line"] for s in report["steps"] if s["key"] == step)
    return report["detail"], line, [e["line"] for e in report["log"] if e["step"] == step]


def streams(head: str, stderr: str) -> str:
    """A failed command's whole text: its head, then what it printed on stderr and on stdout."""
    return f"{head}\nstderr:\n{stderr}\nstdout:\n{OUT}"


def test_a_git_verb_failing_while_looking_says_its_whole_stderr_on_the_page_and_in_the_log(updating, whole_error):
    said = local_home.root() / "said.txt"
    said.write_text(whole_error + "\n")
    refusing = local_home.root() / "upload-pack"
    refusing.write_text(f"#!/bin/sh\ncat {said} >&2\nexit 1\n")
    refusing.chmod(0o755)
    git(versions.repo(), "config", "remote.origin.uploadpack", str(refusing))

    updating.machine.updater._update()  # noqa: SLF001 - the thread's work, run here

    detail, line, logged = ended(updating.machine, "looking")
    lead = "the versions could not be read: VersionError: git fetch failed: CalledProcessError: Command '["
    assert detail.startswith(lead)
    assert f"' returned non-zero exit status 128.\n{whole_error}\n" in detail
    assert (line, logged[-1]) == (detail, detail)
    assert f"update: failed: {detail}" in updating.said


def test_a_look_whose_git_fetch_fails_says_the_whole_failure_on_the_page_and_in_the_log(
    updating, whole_error, monkeypatch
):
    """#971: the failed look's detail, its step's line and the host's log carry the error's type, streams and notes."""
    run, seen = subprocess.run, []

    def failing(command: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess:
        if "fetch" in command:
            seen.append(command)
            error = subprocess.CalledProcessError(128, command, OUT, whole_error)
            error.add_note("a note on the failure")
            raise error
        return run(command, *args, **kwargs)

    monkeypatch.setattr(versions.subprocess, "run", failing)

    updating.machine.updater._update()  # noqa: SLF001 - the thread's work, run here

    [command] = seen
    failed = streams(f"CalledProcessError: Command '{command}' returned non-zero exit status 128.", whole_error)
    whole = f"the versions could not be read: VersionError: git fetch failed: {failed}\na note on the failure"
    assert ended(updating.machine, "looking") == (whole, whole, ["fetching the versions", whole])
    assert updating.said[-1] == f"update: failed: {whole}"


@pytest.mark.parametrize("word", FAILING)
def test_a_failing_build_step_says_both_its_streams_whole_on_the_page_and_in_the_log(
    updating, word, whole_error, tmp_path, monkeypatch
):
    """uv, the version's selfcheck and its pack install, each failing with output on stdout and stderr."""
    (tmp_path / "out").write_text(OUT)
    (tmp_path / "err").write_text(whole_error)
    tool = tmp_path / "bin" / "uv"  # uv, and the interpreter it makes
    tool.parent.mkdir()
    failing = f'case " $* " in *" {word} "*) cat {tmp_path}/out; cat {tmp_path}/err >&2; exit 3;; esac'
    tool.write_text(f"#!/bin/sh\nmkdir -p .venv/bin && cp {tool} .venv/bin/python\n{failing}\n")
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tool.parent}{os.pathsep}{os.environ['PATH']}")
    python = str(local_home.root() / local_home.VERSIONS / "v0.2" / ".venv" / "bin" / "python")
    command = {"sync": [str(tool), "sync", "--locked", "--quiet"],
               "selfcheck": [python, "-m", "owlbear_delivery_next", "selfcheck"],
               "design-pack": [python, "-m", "owlbear_delivery_next", "design-pack", "--install"]}[word]  # fmt: skip
    step, lead = FAILING[word]
    whole = streams(f"CalledProcessError: Command '{command}' returned non-zero exit status 3.", whole_error)
    if word == "sync":
        whole = f"its environment could not be made: {whole}"

    updating.machine.updater._update()  # noqa: SLF001

    detail, line, logged = ended(updating.machine, step)
    kind = "PackInstallError" if word == "design-pack" else "VersionError"
    assert (detail, line, logged[-1]) == (f"{kind}: {lead}{whole}", whole, whole)
    assert f"update: failed v0.2: {detail}" in updating.said
    if word == "design-pack":
        assert updating.machine.impeccable.read()["install"]["detail"] == detail  # every page's banner


def test_a_switch_that_fails_says_the_whole_failure_on_the_page_and_in_the_log(updating, whole_error, monkeypatch):
    """#971: a version that could not take over: the update's detail and the host's log carry the error's notes."""
    error = versions.VersionError(whole_error)
    error.add_note("a note on the failure")

    def failing(_folder: Path, _tag: str) -> bool:
        raise error

    updater = updating.machine.updater
    monkeypatch.setattr(updater, "_prepared", lambda _choice: local_home.root() / local_home.VERSIONS / "v0.2")
    monkeypatch.setattr(updater, "_switch", failing)

    updater._update()  # noqa: SLF001 - the thread's work, run here

    whole = f"VersionError: {whole_error}\na note on the failure"
    assert (updater.read()["phase"], updater.read()["detail"]) == ("failed", whole)
    assert updating.said[-1] == f"update: failed v0.2: {whole}"


@pytest.mark.parametrize("word", ["--detach", *FAILING])  # --detach: git worktree add
def test_a_command_of_an_update_timing_out_says_what_it_printed_whole(updating, word, whole_error, monkeypatch):
    run, which, seen = subprocess.run, shutil.which, []

    def timing_out(command: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess:
        if word in command:
            seen.append((command, kwargs["timeout"]))
            raise subprocess.TimeoutExpired(command, kwargs["timeout"], OUT.encode(), whole_error.encode())
        if Path(command[0]).name != "git":  # uv and the version's interpreter pass
            return subprocess.CompletedProcess(command, 0, "", "")
        return run(command, *args, **kwargs)

    monkeypatch.setattr(versions.subprocess, "run", timing_out)
    monkeypatch.setattr(versions.shutil, "which", lambda name: f"/bin/{name}" if name == "uv" else which(name))
    step, lead = FAILING.get(word, ("getting", ""))

    updating.machine.updater._update()  # noqa: SLF001

    [(command, seconds)] = seen
    whole = streams(f"TimeoutExpired: Command '{command}' timed out after {seconds} seconds", whole_error)
    whole = {"--detach": f"git worktree failed: {whole}", "sync": f"its environment could not be made: {whole}"}.get(
        word, f"it could not run: {whole}"
    )
    detail, line, logged = ended(updating.machine, step)
    kind = "PackInstallError" if word == "design-pack" else "VersionError"
    assert (detail, line, logged[-1]) == (f"{kind}: {lead}{whole}", whole, whole)
    assert f"update: failed v0.2: {detail}" in updating.said


def test_a_release_whose_manifest_is_no_json_says_the_parsers_whole_error(origin):
    commit = released(origin, "v0.3", "{not json")
    versions.fetch(versions.repo())

    with pytest.raises(versions.VersionError) as raised:
        versions.pins(commit)

    expected = "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"
    assert str(raised.value) == f"{versions.MANIFEST} at {commit[:12]} is no JSON: JSONDecodeError: {expected}"


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
    monkeypatch.setattr(versions, "target", lambda channel=None: fetched.append(1) or target(channel))

    said = impeccable.look()

    assert (said["state"], said["version"], said["pack"]) == ("newer", "v0.3", "p-new")
    assert said["running_pack"] == pack_files.manifest()["pack"]
    assert impeccable.release() == said  # kept for the pages, which never fetch
    assert fetched == [1]
    assert impeccable.look()["checked_at"] is not None  # each look fetches; the update checks say when
    assert fetched == [1, 1]
    assert not (local_home.root() / local_home.VERSIONS).exists()  # nothing installed
    assert git(runtime, "rev-parse", "HEAD") == head


def test_the_owlbear_update_check_finds_a_release_with_the_same_pack_while_off_and_busy_and_starts_nothing(origin):
    """D-01M63CCVRK8ZKFENY9F4A2K11A: newer whatever Impeccable it pins, whether updating by itself is on or busy."""
    runtime = at_v0_2(origin)  # updating by itself off
    head = git(runtime, "rev-parse", "HEAD")
    released(origin, "v0.3", json.dumps(pack_files.manifest()))  # the same pack: the banner says nothing
    busy = SimpleNamespace(say=print, stopping=threading.Event(), busy=lambda: ["a running step"])
    checks = update_checks.Checks(busy, spawn=lambda work: work())

    checks.start("owlbear")

    said = next(u for u in checks.read()["updates"] if u["name"] == "owlbear")
    assert (said["state"], said["latest"], checks.read()["available"]) == ("newer", "v0.3", 1)
    assert impeccable.release()["state"] == "same"
    assert not (local_home.root() / local_home.VERSIONS).exists()  # nothing installed
    assert git(runtime, "rev-parse", "HEAD") == head


def test_a_release_found_on_another_channel_is_unknown_to_the_banner_and_the_update_check_until_looked_at_again(
    origin,
):
    """A channel change can withdraw the version found; with the check's interval unset it would stay offered."""
    at_v0_2(origin)
    released(origin, "v0.3", '{"pack": "p-new"}')
    checks = update_checks.Checks(SimpleNamespace(say=print, stopping=threading.Event()), spawn=lambda work: work())
    checks.start("owlbear")

    def owlbear() -> dict:
        return next(u for u in checks.read()["updates"] if u["name"] == "owlbear")

    assert (impeccable.release()["state"], owlbear()["state"], owlbear()["latest"]) == ("newer", "newer", "v0.3")

    with registry.locked():
        saved = registry.load()
        saved.settings = saved.settings.model_copy(update={"channel": "major"})  # v0.1 until v1: v0.3 is not taken
        registry.save(saved)

    said, row = impeccable.release(), owlbear()
    assert (said["state"], said["detail"]) == ("unknown", impeccable.MOVED)
    assert (row["state"], row["detail"], checks.read()["available"]) == ("unknown", impeccable.MOVED, 0)
    checks.start("owlbear")
    assert (impeccable.release()["state"], owlbear()["state"]) == ("none", "current")


def test_a_release_pinning_the_same_pack_shows_nothing_and_an_unreadable_one_stays_unknown(origin):
    at_v0_2(origin)
    released(origin, "v0.3", json.dumps(pack_files.manifest()))

    assert impeccable.look()["state"] == "same"

    released(origin, "v0.4", None)
    said = impeccable.look()
    assert (said["state"], said["version"]) == ("unknown", "v0.4")
    assert "Impeccable is unreadable" in said["detail"]
    checks = update_checks.Checks(SimpleNamespace(say=print, stopping=threading.Event()), spawn=lambda work: work())
    checks.start("owlbear")
    row = next(u for u in checks.read()["updates"] if u["name"] == "owlbear")
    assert (row["state"], row["latest"], "Impeccable is unreadable" in row["detail"]) == ("newer", "v0.4", True)


def test_a_runtime_from_before_the_rename_sees_a_renamed_release_as_unknown_not_failed(origin, monkeypatch):
    """D-01M63CB9WFXBV3TDXGG295QCST: a reader that knows only design_pack.json shows unknown until it updates once."""
    at_v0_2(origin)
    released(origin, "v0.3", '{"pack": "p-new"}')  # the renamed tree: impeccable.json only
    monkeypatch.setattr(versions, "MANIFEST", versions.OLD_MANIFEST)  # the older runtime's one manifest path

    said = impeccable.look()

    assert (said["state"], said["version"]) == ("unknown", "v0.3")
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


@pytest.mark.parametrize("prepare", [False, True])
def test_the_versions_command_says_versions_it_could_not_read_or_install_whole(
    origin, monkeypatch, capsys, whole_error, prepare
):
    """#971: ``owlbear versions`` says a failed look, and with ``--prepare`` a failed install, whole."""
    runtime_at(origin, git(origin, "rev-parse", "v0.1^{commit}"))
    error = versions.VersionError(whole_error)
    error.add_note("a note on the failure")

    def failing(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(sys, "platform", "darwin")  # CI runs on Linux, which the command refuses
    monkeypatch.setattr(versions, "install" if prepare else "target", failing)
    tag, commit = versions.active()
    running = f"running: {tag or 'no installed version'} at {commit[:12]}\n"
    whole = f"VersionError: {whole_error}\na note on the failure"

    assert command.main(["versions", "--prepare"] if prepare else ["versions"]) == 1

    if prepare:
        nxt = f"next: v0.2 at {git(origin, 'rev-parse', 'v0.2^{commit}')[:12]}\n"
        assert capsys.readouterr().out == f"{running}{nxt}{whole}\n"
    else:
        assert capsys.readouterr().out == f"{running}the versions could not be read: {whole}\n"


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


@pytest.mark.parametrize("fails", ["import", "machine", "marker", "receipt", "settings"])
def test_the_selfcheck_says_each_failure_whole(tmp_path, monkeypatch, capsys, whole_error, fails):
    """#971: a module that does not import, an unreadable ``machine.json``, store marker or settings layer, and an
    unsound move receipt: each said with its type and notes, as the update's step line reads them."""
    clone = registered(tmp_path, marker=STORE_FORMAT)
    pid = registry.load().projects[0].id
    marker, layer = project_home.home(pid) / "format", project_home.home(pid) / "config.json"
    layer.write_text(json.dumps({"format": CONFIG_FORMAT}))
    error = {"import": RuntimeError, "machine": ValueError, "marker": OSError, "receipt": StoreError,
             "settings": OSError}[fails](whole_error)  # fmt: skip
    error.add_note("a note on the failure")
    whole = f"{type(error).__name__}: {whole_error}\na note on the failure"

    def failing(*_args, **_kwargs):
        raise error

    importing, reading, read_text = selfcheck.import_module, selfcheck.read_regular, Path.read_text
    if fails == "import":
        monkeypatch.setattr(
            selfcheck, "import_module", lambda name: failing() if name.endswith(".commands.runner") else importing(name)
        )
        said = f"commands.runner does not import: {whole}"
    elif fails == "machine":
        monkeypatch.setattr(registry.Machine, "model_validate_json", failing)
        said = f"{local_home.root() / registry.MACHINE} is unreadable: {whole}"
    elif fails == "marker":
        monkeypatch.setattr(selfcheck, "read_regular", lambda path: failing() if path == marker else reading(path))
        said = f"{clone}: {marker} is unreadable: {whole}"
    elif fails == "receipt":
        monkeypatch.setattr(switched_authority, "retained_target", failing)
        said = f"{clone}: {whole}"
    else:
        monkeypatch.setattr(Path, "read_text", lambda path, **kw: failing() if path == layer else read_text(path, **kw))
        said = f"{clone}: {layer} is unreadable: {whole}"

    assert selfcheck.main() == 1

    assert capsys.readouterr().out == f"{said}\n"


def test_the_selfcheck_names_every_missing_page_asset(monkeypatch):
    """#971: the list the owner reads is never cut to its first five."""
    gone = [f"gone{n}.js" for n in range(7)]
    monkeypatch.setattr(pages, "lit_files", lambda: {"lit-html.js": "x"} | dict.fromkeys(gone, "y"))

    named = ", ".join(f"vendor/lit-html/{name}" for name in gone)
    assert selfcheck.problems() == [f"the pages' assets are missing: {named}"]


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


def test_the_selfcheck_reads_settings_in_format_23_and_refuses_the_next_one(tmp_path):
    clone = registered(tmp_path)
    folder = project_home.clone_dir(clone)
    folder.mkdir(exist_ok=True)
    switched = {
        "format": 23, "load_user_instructions": True, "load_user_skills": False, "load_user_memory": False,
        "guard_level": "strict", "github_account": "boecht", "agents": {"shaper": {"challenge_wait": 15}},
    }  # fmt: skip
    (folder / "config.json").write_text(json.dumps(switched))
    assert selfcheck.problems() == []

    (folder / "config.json").write_text(json.dumps(switched | {"format": 24}))
    said = f"its settings in {folder / 'config.json'} have format 24, newer than this version's 23"
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


@pytest.mark.parametrize(
    "route", ["the host's start scrubbed git's settings", "a fixture's own global git config", "a test's undo()"]
)
def test_a_tests_git_never_reaches_github(route, tmp_path, monkeypatch):
    """#804: no route a test takes around the offline rule (the host start dropping GIT_CONFIG_*, a fixture's own
    global config, a test's monkeypatch.undo() putting the real HOME back) lets git reach GitHub."""
    if route.startswith("the host"):
        for name in environment.scrub(dict(os.environ)):
            monkeypatch.delenv(name)
    elif route.startswith("a fixture"):
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
        monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    else:
        monkeypatch.undo()
        monkeypatch.setenv("HOME", str(tmp_path))  # one with no .gitconfig, never the machine's
        monkeypatch.setattr(local_home, "root", lambda: tmp_path / ".owlbear")
    url = ["git", "ls-remote", "--get-url", codebase.URL]  # resolves the URL offline
    resolved = subprocess.run(url, capture_output=True, text=True, check=True).stdout  # noqa: S603 - fixed arguments
    assert resolved.startswith("/nonexistent/offline-in-tests/"), resolved
    began = time.monotonic()
    with pytest.raises(versions.VersionError, match="/nonexistent/offline-in-tests/"):
        versions.repo()  # codebase.URL, OwlBear's GitHub repository
    assert time.monotonic() - began < 5


AFTER_TEARDOWN = """
import json, os, pytest

@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_teardown(item):
    yield
    names = ("GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0")
    with open(os.environ["AFTER_TEARDOWN"], "a") as out:
        out.write(json.dumps({name: os.environ.get(name) for name in names}) + "\\n")
"""


@pytest.mark.timeout(120)  # a child pytest starts with this package's conftest; a loaded runner needs more than 30 s
@pytest.mark.parametrize(
    "parent", [{"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.fsmonitor", "GIT_CONFIG_VALUE_0": "false"}, {}]
)
def test_the_offline_rule_ends_with_the_test_that_changed_it(parent, tmp_path):
    """#804: once each route of the probe above has ended, git's settings are the ones it started with, set or not;
    checked after teardown, where a check inside the test passes falsely."""
    (tmp_path / "after_teardown.py").write_text(AFTER_TEARDOWN)
    seen = tmp_path / "seen.jsonl"
    names = ("GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0")
    skip = {*names, "OWLBEAR_FLAKY_REPORT"}  # the CI job's re-run report and summary are the outer run's
    env = {k: v for k, v in os.environ.items() if k not in skip} | parent
    env |= {"AFTER_TEARDOWN": str(seen), "PYTHONPATH": os.pathsep.join([str(tmp_path), env.get("PYTHONPATH", "")])}
    probe = f"{Path(__file__).resolve()}::test_a_tests_git_never_reaches_github"
    run = [sys.executable, "-m", "pytest", "-q", "-n", "0", "-p", "no:cacheprovider", "-p", "after_teardown", probe]
    root = Path(__file__).resolve().parents[3]
    done = subprocess.run(run, cwd=root, env=env, capture_output=True, text=True, check=False)  # noqa: S603
    assert done.returncode == 0, done.stdout[-2000:]
    after = [json.loads(line) for line in seen.read_text().splitlines()]
    assert after == [{name: parent.get(name) for name in names}] * 3
