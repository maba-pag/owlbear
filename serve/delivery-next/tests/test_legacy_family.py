import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

from owlbear_delivery_next.state_store import legacy_family
from owlbear_delivery_next.state_store.legacy_family import Binding

GIT_IDENTITY = ("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid")
RELEASE_9074 = "9074ec727eddf99dbadc457529bd2819b449e73a"
RELEASE_V151 = "28ef7dade41b744e53294bf8fc8515e2b7e90a3d"
RELEASE_V150 = "cf9f9981f4cbb7f2996b3fa17845fa1e5beaa5f9"


def _commit(package: Path) -> None:
    subprocess.run(["git", "-C", str(package), "add", "-A"], check=True, capture_output=True)  # noqa: S603, S607
    commit = ["git", "-C", str(package), *GIT_IDENTITY, "commit", "-q", "-m", "change"]
    subprocess.run(commit, check=True, capture_output=True)  # noqa: S603


def _edit(package: Path, rel: str, old: str, new: str, *, commit: bool = True) -> None:
    path = package / rel
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1
    path.write_text(text.replace(old, new), encoding="utf-8")
    if commit:
        _commit(package)


def _reasons(binding: Binding) -> list[str]:
    return [gap.reason for gap in legacy_family.open_gaps(binding)]


def test_the_audited_checkout_is_a_proven_binding(audited_binding: Binding) -> None:
    assert legacy_family.open_gaps(audited_binding) == ()


def test_the_family_aggregate_is_the_digest_of_the_function_table() -> None:
    text = "\n".join(f"{key} {digest}" for key, digest in sorted(legacy_family.FUNCTIONS))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == legacy_family.FAMILY_AGGREGATE


def test_the_current_candidate_is_a_proven_binding(current_binding: Binding) -> None:
    assert legacy_family.open_gaps(current_binding) == ()


def test_the_current_family_aggregate_is_the_digest_of_its_table() -> None:
    text = "\n".join(f"{key} {digest}" for key, digest in sorted(legacy_family.CURRENT_FUNCTIONS))
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == legacy_family.CURRENT_FAMILY_AGGREGATE


def test_a_current_function_change_is_an_unknown_build(current_binding: Binding) -> None:
    _edit(
        current_binding.package,
        "state_store/project_home.py",
        "return git_common_dir(cwd) / STORE_DIR\n",
        'return git_common_dir(cwd) / STORE_DIR / "x"\n',
    )
    reasons = _reasons(current_binding)
    assert len(reasons) == 1
    assert "current family modules differ from the candidate: state_store/project_home.py" in reasons[0]


def test_a_current_lock_guard_change_is_an_unknown_build(current_binding: Binding) -> None:
    _edit(
        current_binding.package,
        "local_system/storage_io.py",
        'name: str = ".storage.lock")',
        'name: str = ".storage.lock2")',
    )
    reasons = _reasons(current_binding)
    assert len(reasons) == 1
    assert "current family modules differ from the candidate: local_system/storage_io.py" in reasons[0]


def test_a_current_constant_change_is_an_unknown_build(current_binding: Binding) -> None:
    _edit(current_binding.package, "state_store/database.py", "STORE_FORMAT = 7", "STORE_FORMAT = 8")
    reasons = _reasons(current_binding)
    assert "current family constant STORE_FORMAT in state_store/database.py is not the expected value" in reasons[0]


def test_a_changed_function_is_an_unknown_build(audited_binding: Binding) -> None:
    _edit(
        audited_binding.package,
        "state_store/project_home.py",
        "return git_common_dir(cwd) / STORE_DIR\n",
        'return git_common_dir(cwd) / STORE_DIR / "x"\n',
    )
    reasons = _reasons(audited_binding)
    assert len(reasons) == 1
    assert "functions differ from the audited family: state_store/project_home.py:clone_dir" in reasons[0]


def test_a_changed_constant_is_an_unknown_build(audited_binding: Binding) -> None:
    _edit(audited_binding.package, "state_store/database.py", "STORE_FORMAT = 7", "STORE_FORMAT = 8")
    assert "constant STORE_FORMAT in state_store/database.py is not the audited value" in _reasons(audited_binding)[0]


def test_the_v1_checkout_is_a_proven_binding(legacy_v1_binding: Binding) -> None:
    assert legacy_family.open_gaps(legacy_v1_binding) == ()


@pytest.mark.parametrize("commit", [RELEASE_9074, RELEASE_V151, RELEASE_V150], ids=["9074", "v1.51", "v1.50"])
def test_a_shipped_release_build_is_a_proven_binding(commit: str, release_binding) -> None:
    assert legacy_family.open_gaps(release_binding(commit)) == ()


def test_a_release_runner_mixed_into_the_audited_build_is_an_unknown_build(audited_binding: Binding) -> None:
    blob = subprocess.run(  # noqa: S603 - fixed argv reading a committed blob, no shell
        [  # noqa: S607
            "git",
            "-C",
            str(Path(__file__).parent),
            "show",
            f"{RELEASE_V151}:serve/delivery-next/src/owlbear_delivery_next/commands/runner.py",
        ],
        capture_output=True,
        check=True,
    ).stdout
    (audited_binding.package / "commands/runner.py").write_bytes(blob)
    _commit(audited_binding.package)
    reasons = _reasons(audited_binding)
    assert len(reasons) == 1
    assert "module imports differ" in reasons[0]


def test_a_no_op_current_open_switched_is_an_unknown_build(current_binding: Binding) -> None:
    _edit(
        current_binding.package,
        "state_store/project_home.py",
        "project_move.check_switched(target, pfd, rec)",
        "None",
        commit=False,
    )
    _edit(
        current_binding.package,
        "state_store/project_home.py",
        "_publish_markers(folder_fd, pfd, target, previous, moved=True)",
        "None",
    )
    reasons = _reasons(current_binding)
    assert len(reasons) == 1
    assert "current family modules differ from the candidate: state_store/project_home.py" in reasons[0]


def test_a_no_op_quarantine_refusal_helper_is_an_unknown_build(current_binding: Binding) -> None:
    _edit(
        current_binding.package,
        "state_store/fd_tree.py",
        "    kept = sorted(n for n in os.listdir(dfd) if n.startswith(QUARANTINE))",
        "    kept = []",
    )
    reasons = _reasons(current_binding)
    assert len(reasons) == 1
    assert "current family modules differ from the candidate: state_store/fd_tree.py" in reasons[0]


def test_a_direct_store_construction_in_the_v1_chat_is_an_unknown_build(legacy_v1_binding: Binding) -> None:
    _edit(legacy_v1_binding.package, "commands/mcp_server.py", "Store.open(repo)", "Store(repo)")
    reasons = _reasons(legacy_v1_binding)
    assert len(reasons) == 1
    assert "v1.0 family functions differ: commands/mcp_server.py:Chat.__init__" in reasons[0]


def test_a_v1_located_prefix_change_is_an_unknown_build(legacy_v1_binding: Binding) -> None:
    _edit(
        legacy_v1_binding.package,
        "state_store/project_home.py",
        "    if found > STORE_FORMAT:\n",
        "    if found >= STORE_FORMAT:\n",
    )
    reasons = _reasons(legacy_v1_binding)
    assert len(reasons) == 1
    assert "v1.0 family functions differ: state_store/project_home.py:located" in reasons[0]


def test_a_v1_import_change_is_an_unknown_build(legacy_v1_binding: Binding) -> None:
    _edit(
        legacy_v1_binding.package,
        "state_store/project_home.py",
        "from owlbear_delivery_next.local_system import local_home\n",
        "from owlbear_delivery_next.local_system import local_home as local_home\n",
    )
    reasons = _reasons(legacy_v1_binding)
    assert len(reasons) == 1
    assert (
        "v1.0 family imports differ: state_store/project_home.py imports owlbear_delivery_next.local_system"
        in reasons[0]
    )


def test_a_v1_constant_change_is_an_unknown_build(legacy_v1_binding: Binding) -> None:
    _edit(legacy_v1_binding.package, "state_store/database.py", "STORE_FORMAT = 7", "STORE_FORMAT = 8")
    reasons = _reasons(legacy_v1_binding)
    assert len(reasons) == 1
    assert "v1.0 family constant STORE_FORMAT in state_store/database.py is not the audited value" in reasons[0]


def test_a_v1_kept_set_change_is_an_unknown_build(legacy_v1_binding: Binding) -> None:
    _edit(
        legacy_v1_binding.package,
        "state_store/project_home.py",
        "KEPT = frozenset({CLONE_ID, MARKER, MOVE_LOCK})",
        "KEPT = frozenset({CLONE_ID, MARKER})",
    )
    reasons = _reasons(legacy_v1_binding)
    assert len(reasons) == 1
    assert "v1.0 family constant KEPT in state_store/project_home.py is not the audited value" in reasons[0]


def test_a_v1_split_launcher_is_a_split_binding(legacy_v1_binding: Binding) -> None:
    legacy_v1_binding.launcher.write_text("#!/bin/sh\n")
    reasons = _reasons(legacy_v1_binding)
    assert len(reasons) == 1
    assert "split binding" in reasons[0]


def test_an_uncommitted_edit_is_a_dirty_checkout(audited_binding: Binding) -> None:
    _edit(
        audited_binding.package,
        "state_store/project_home.py",
        "return git_common_dir(cwd) / STORE_DIR\n",
        'return git_common_dir(cwd) / STORE_DIR / "x"\n',
        commit=False,
    )
    reasons = _reasons(audited_binding)
    assert len(reasons) == 1
    assert "dirty" in reasons[0]


def test_a_launcher_running_another_interpreter_is_a_split_binding(audited_binding: Binding) -> None:
    audited_binding.launcher.write_text("#!/bin/sh\n")
    reasons = _reasons(audited_binding)
    assert len(reasons) == 1
    assert "split binding" in reasons[0]


def test_a_launcher_through_env_has_an_unknown_interpreter(audited_binding: Binding) -> None:
    audited_binding.launcher.write_text("#!/usr/bin/env python3\n")
    assert _reasons(audited_binding) == ["the owlbear launcher starts through env, so its interpreter is unknown"]


def test_a_missing_launcher_is_an_unknown_binding(audited_binding: Binding) -> None:
    unlaunched = Binding(None, Path(sys.executable), audited_binding.package)
    assert _reasons(unlaunched) == ["no owlbear launcher is on PATH: unknown binding"]


def _venv(root: Path, name: str) -> Path:
    """A venv-shaped interpreter path: its own directory and pyvenv.cfg, a symlink to the shared base interpreter."""
    bin_dir = root / name / "bin"
    bin_dir.mkdir(parents=True)
    (root / name / "pyvenv.cfg").write_text(f"home = {Path(sys.executable).parent}\n")
    (bin_dir / "python").symlink_to(Path(sys.executable).resolve())
    return bin_dir / "python"


def test_two_venvs_sharing_one_base_interpreter_are_a_split_binding(audited_binding: Binding, tmp_path: Path) -> None:
    venv_a = _venv(tmp_path, "a")
    venv_b = _venv(tmp_path, "b")
    audited_binding.launcher.write_text(f"#!{venv_b}\n")  # the launcher runs venv B
    loaded_by_a = Binding(audited_binding.launcher, venv_a, audited_binding.package)

    reasons = _reasons(loaded_by_a)
    assert len(reasons) == 1
    assert "split binding" in reasons[0]


def test_a_launcher_running_the_loading_venv_is_proven(audited_binding: Binding, tmp_path: Path) -> None:
    venv_a = _venv(tmp_path, "a")
    audited_binding.launcher.write_text(f"#!{venv_a}\n")
    assert _reasons(Binding(audited_binding.launcher, venv_a, audited_binding.package)) == []


def test_an_unimportable_package_is_an_unknown_binding(audited_binding: Binding) -> None:
    unloaded = Binding(audited_binding.launcher, Path(sys.executable), None)
    assert _reasons(unloaded) == ["the owlbear_delivery_next package is not importable: unknown binding"]
