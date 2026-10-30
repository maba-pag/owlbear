"""The unpatched public prepare/finish flow, driven through both real CLI surfaces.

Only the boot-session reader and the verifier's binding are replaced: the binding is a clean checkout of the
candidate bytes behind a launcher. Gaps and compatibility are never patched, so the verifier decides every case.
"""

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.machine_host import command
from owlbear_delivery_next.state_store import legacy_family, offline_protocol, project_home
from owlbear_delivery_next.state_store.database import MARKER
from owlbear_delivery_next.state_store.store import Store, StoreError

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"
REFUSED = "legacy producers are not proven fenced"

Surface = Callable[[Path, str], int]


def via_argparse(repo: Path, name: str) -> int:
    return cli.main(["--repo", str(repo), name])


def via_forwarder(repo: Path, name: str) -> int:
    return command.forward([name, "--repo", str(repo)])


@pytest.fixture(params=[via_argparse, via_forwarder], ids=["argparse", "forwarder"])
def run(request) -> Surface:
    return request.param


# The forwarder only moves --repo before the command and calls cli.main. Both surfaces run the prepare and finish
# proofs and one refusal (its exit code); the other scenarios run through argparse alone.
ARGPARSE_ONLY = pytest.mark.parametrize("run", [via_argparse], ids=["argparse"])


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "shop"
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True)  # noqa: S603, S607
    folder = project_home.clone_dir(path)  # a legacy clone: its own store, format 7, still in the clone
    folder.mkdir(parents=True)
    (folder / MARKER).write_text("7")
    (folder / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    return path


@pytest.fixture
def boot(monkeypatch) -> dict:
    state = {"id": BEFORE}
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: state["id"])
    return state


def source_marker(repo: Path) -> str:
    return (project_home.clone_dir(repo) / MARKER).read_text().strip()


def prepared(repo: Path) -> dict:
    return json.loads((project_home.clone_dir(repo) / offline_protocol.PREPARED).read_text())


@pytest.mark.usefixtures("current_binding", "boot")
def test_prepare_records_the_prior_format_and_boot_then_fences_the_source(run, repo) -> None:
    assert source_marker(repo) == "7"

    assert run(repo, "prepare") == 0

    record = prepared(repo)
    assert set(record) == {"boot", "folder", "marker"}
    assert (record["boot"], record["marker"].strip()) == (BEFORE, "7")
    assert source_marker(repo) == "999"


@pytest.mark.usefixtures("current_binding", "boot")
@ARGPARSE_ONLY
def test_a_repeated_prepare_keeps_the_valid_prior_format(run, repo) -> None:
    assert run(repo, "prepare") == 0
    assert run(repo, "prepare") == 0

    assert prepared(repo)["marker"].strip() == "7"  # never the fence 999 saved as the prior format
    assert source_marker(repo) == "999"


@pytest.mark.usefixtures("current_binding")
@ARGPARSE_ONLY
def test_an_ordinary_open_refuses_after_prepare_even_when_only_the_boot_changed(run, repo, boot) -> None:
    assert run(repo, "prepare") == 0
    with pytest.raises(StoreError):
        Store.open(repo)

    boot["id"] = AFTER
    with pytest.raises(StoreError):
        Store.open(repo)
    assert source_marker(repo) == "999"


@pytest.mark.usefixtures("current_binding")
@pytest.mark.usefixtures("boot")
@ARGPARSE_ONLY
def test_finish_refuses_on_the_same_boot_and_on_an_unreadable_boot(run, repo, monkeypatch, capsys) -> None:
    assert run(repo, "prepare") == 0

    assert run(repo, "finish") == 1
    assert "still the boot session" in capsys.readouterr().err

    def unreadable() -> str:
        msg = "boot-session UUID is unreadable (no sysctl): refusing the offline move"
        raise StoreError(msg)

    monkeypatch.setattr(offline_protocol, "boot_session", unreadable)
    assert run(repo, "finish") == 1
    assert "refusing the offline move" in capsys.readouterr().err
    assert source_marker(repo) == "999"
    assert (project_home.clone_dir(repo) / offline_protocol.PREPARED).exists()


def rewrite_record(repo: Path, **changes: object) -> None:
    record = prepared(repo) | changes
    (project_home.clone_dir(repo) / offline_protocol.PREPARED).write_text(json.dumps(record) + "\n")


@pytest.mark.usefixtures("current_binding")
@ARGPARSE_ONLY
@pytest.mark.parametrize("stored", [None, "not-a-boot-uuid", 7])
def test_a_malformed_stored_boot_is_never_a_new_boot(run, repo, boot, capsys, stored) -> None:
    assert run(repo, "prepare") == 0
    rewrite_record(repo, boot=stored)
    boot["id"] = AFTER  # a genuinely different current boot must not make a malformed witness proof

    assert run(repo, "finish") == 1
    assert "not a preparation record OwlBear wrote" in capsys.readouterr().err
    assert source_marker(repo) == "999"
    assert (project_home.clone_dir(repo) / offline_protocol.PREPARED).exists()


@pytest.mark.usefixtures("current_binding", "boot")
@ARGPARSE_ONLY
def test_a_lowercase_stored_boot_is_the_same_boot_as_the_current_one(run, repo, capsys) -> None:
    assert run(repo, "prepare") == 0
    rewrite_record(repo, boot=BEFORE.lower())

    assert run(repo, "finish") == 1
    assert "still the boot session" in capsys.readouterr().err
    assert source_marker(repo) == "999"


@pytest.mark.usefixtures("current_binding")
def test_finish_after_the_reboot_selects_the_proved_target_and_keeps_the_source_fenced(run, repo, boot) -> None:
    assert run(repo, "prepare") == 0
    boot["id"] = AFTER

    assert run(repo, "finish") == 0

    target = Store.open(repo).root
    assert target != project_home.clone_dir(repo)
    assert Store.open(repo).root == target  # a fresh startup selects the same target
    assert source_marker(repo) == "999"


@pytest.mark.usefixtures("current_binding")
@ARGPARSE_ONLY
@pytest.mark.parametrize("kind", ["missing", "replaced"])
def test_a_missing_or_replaced_target_refuses_and_keeps_the_source(kind, run, repo, boot) -> None:
    assert run(repo, "prepare") == 0
    boot["id"] = AFTER
    assert run(repo, "finish") == 0
    target = Store.open(repo).root

    if kind == "missing":
        shutil.rmtree(target)
    else:
        target.rename(target.with_name(target.name + "-moved"))
        target.mkdir()
    with pytest.raises(StoreError):
        Store.open(repo)
    assert source_marker(repo) == "999"


@pytest.mark.usefixtures("boot")
@pytest.mark.parametrize(
    ("kind", "run"),
    [
        *(
            pytest.param(kind, via_argparse, id=f"{kind}-argparse")
            for kind in ("no-launcher", "split-interpreter", "dirty-checkout", "changed-constant")
        ),
        pytest.param("no-launcher", via_forwarder, id="no-launcher-forwarder"),  # the forwarder keeps the refusal
    ],
)
def test_an_unproven_binding_refuses_prepare_without_cutover(  # noqa: PLR0913, PLR0917
    kind, run, repo, current_binding, current_package, monkeypatch, capsys
) -> None:
    if kind == "no-launcher":
        unknown = legacy_family.Binding(None, current_binding.interpreter, current_binding.package)
        monkeypatch.setattr(legacy_family, "live_binding", lambda: unknown)
    elif kind == "split-interpreter":
        split = legacy_family.Binding(current_binding.launcher, Path("/nonexistent/python"), current_binding.package)
        monkeypatch.setattr(legacy_family, "live_binding", lambda: split)
    elif kind == "dirty-checkout":
        project_home_src = current_package / "state_store" / "project_home.py"
        project_home_src.write_text(project_home_src.read_text() + "\n# uncommitted edit\n")
    else:
        move_src = current_package / "state_store" / "project_move.py"
        move_src.write_text(move_src.read_text().replace('FENCE = "999"', 'FENCE = "998"'))
        who = ["-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(["git", *who, "-C", str(current_package), "commit", "-qam", "altered"], check=True)  # noqa: S603, S607

    assert run(repo, "prepare") == 1
    assert REFUSED in capsys.readouterr().err
    assert not (project_home.clone_dir(repo) / offline_protocol.PREPARED).exists()
    assert source_marker(repo) == "7"


@pytest.mark.usefixtures("current_binding", "boot")
@ARGPARSE_ONLY
def test_a_no_op_quarantine_refusal_helper_refuses_public_prepare(run, repo, current_package, capsys) -> None:
    helper = current_package / "state_store" / "fd_tree.py"
    old = "    kept = sorted(n for n in os.listdir(dfd) if n.startswith(QUARANTINE))"
    assert helper.read_text().count(old) == 1
    helper.write_text(helper.read_text().replace(old, "    kept = []"))
    who = ["-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", *who, "-C", str(current_package), "commit", "-qam", "no-op helper"], check=True)  # noqa: S603, S607

    assert run(repo, "prepare") == 1
    assert REFUSED in capsys.readouterr().err
    assert not (project_home.clone_dir(repo) / offline_protocol.PREPARED).exists()
    assert source_marker(repo) == "7"


def tree(root: Path) -> dict[str, bytes | None]:
    """Every entry under *root* except git metadata: directories map to None, files to their bytes."""
    found: dict[str, bytes | None] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if rel != ".git" and not rel.startswith(".git/"):
            found[rel] = None if path.is_dir() else path.read_bytes()
    return found


@pytest.mark.usefixtures("current_binding", "boot")
@ARGPARSE_ONLY
def test_a_committed_storage_io_guard_removal_refuses_default_public_prepare_before_any_write(
    run, repo, current_package, capsys
) -> None:
    storage = current_package / "local_system" / "storage_io.py"
    guard = (
        "    if not stat.S_ISREG(os.fstat(lock_fd).st_mode):\n"
        "        os.close(lock_fd)\n"
        '        msg = "storage lock must be a regular file"\n'
        "        raise ValueError(msg)\n"
    )
    text = storage.read_text(encoding="utf-8")
    assert text.count(guard) == 1
    storage.write_text(text.replace(guard, ""), encoding="utf-8")
    who = ["-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", *who, "-C", str(current_package), "commit", "-qam", "drop lock guard"], check=True)  # noqa: S603, S607
    before = tree(repo)

    assert run(repo, "prepare") == 1
    assert REFUSED in capsys.readouterr().err
    assert tree(repo) == before
    assert source_marker(repo) == "7"
