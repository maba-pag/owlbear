"""``delivery-lc`` contracts (N02-B): copy, isolation proof, container command, compare, full form."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from serve.delivery.tests.test_portfolio_application import (
    _seed_loader_composed_completed_change,
    _startup_config,
)

from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.state_formats import FORMAT_MARKER
from owlbear_tools import delivery_lc
from owlbear_tools.delivery_lc import Mount, isolation_failures

_GIT = resolve_git_executable()
_LIVE = "/Users/example/Projects/owlbear-dev"
_STAGE = "/private/tmp/lc/root"
_N02A_GATE = Path(__file__).parents[2] / "delivery/tests/fixtures/state_formats/n02a_state_formats.py.txt"


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        (_GIT, "-C", str(repository), *arguments), check=True, capture_output=True, text=True
    ).stdout.strip()


def _isolated(**overrides: object) -> list[str]:
    arguments: dict[str, object] = {
        "mounts": [
            Mount("/", "/", "overlay", "overlay"),
            Mount("/", "/proc", "proc", "proc"),
            Mount("/", "/dev", "tmpfs", "tmpfs"),
            Mount("/docker/containers/a/hosts", "/etc/hosts", "ext4", "/dev/vda1"),
            Mount(_STAGE, _LIVE),
            Mount("/private/tmp/lc/control", "/lc"),
        ],
        "live": _LIVE,
        "stage_source": _STAGE,
        "marker_present": True,
        "common_dirs": {"copy": f"{_LIVE}/.git", "change-a": f"{_LIVE}/.git"},
    }
    return isolation_failures(**{**arguments, **overrides})  # type: ignore[arg-type]


def test_isolation_proof_accepts_only_the_stage_copy_at_the_live_path() -> None:
    assert _isolated() == []
    assert _isolated(mounts=[Mount("/host_mnt/private/tmp/lc/root", _LIVE)]) == []
    shared = Mount("/example/stage/root", _LIVE, "fakeowner", "/run/host_mark/Users")
    assert _isolated(mounts=[shared], stage_source="/Users/example/stage/root") == []


@pytest.mark.parametrize(
    "mount",
    [
        Mount("/Users", "/host-users", "ext4", "/dev/sda1"),
        Mount("/", "/host-users", "fakeowner", "/run/host_mark/Users"),
        Mount("/host_mnt/Users/example", "/mnt/home", "fuse.grpcfuse", "grpcfuse"),
        Mount("/example/Projects/owlbear-dev", "/checkout", "fakeowner", "/run/host_mark/Users"),
    ],
    ids=["users-at-alias", "docker-desktop-share", "home-at-alias", "checkout-at-alias"],
)
def test_isolation_proof_rejects_the_checkout_or_an_ancestor_mounted_at_any_other_path(mount: Mount) -> None:
    failures = _isolated(mounts=[Mount("/", "/", "overlay", "overlay"), Mount(_STAGE, _LIVE), mount])

    assert failures == [f"the real checkout or an ancestor of it is mounted at {mount.mount_point}"]


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"mounts": [Mount(_LIVE, _LIVE)]}, "not the stage copy"),
        ({"mounts": [Mount(_STAGE, _LIVE), Mount("/x", f"{_LIVE}/.owlbear")]}, "exactly one mount"),
        ({"mounts": [Mount(_STAGE, _LIVE), Mount(_LIVE, "/Users/elsewhere")]}, "unexpected mounts"),
        ({"mounts": [Mount("/", "/")]}, "exactly one mount"),
        ({"marker_present": False}, "copy marker"),
        ({"common_dirs": {"change-a": "/Users/example/Projects/owlbear-dev-lane-a/.git"}}, "outside the copy"),
    ],
    ids=["real-checkout", "nested-mount", "other-users-mount", "unmounted", "no-marker", "worktree-escape"],
)
def test_isolation_proof_rejects_every_non_isolated_shape(overrides: dict[str, object], reason: str) -> None:
    failures = _isolated(**overrides)

    assert any(reason in failure for failure in failures), failures


def test_mountinfo_parser_decodes_escaped_paths_and_keeps_the_mount_source() -> None:
    text = (
        "36 35 98:0 /private/tmp/l\\040c/root /Users/a\\040b rw,noatime master:1 - ext3 /dev/root rw\n"
        "40 35 0:50 / /host-users rw,relatime - fakeowner /run/host_mark/Users rw\n"
    )

    assert delivery_lc.parse_mountinfo(text) == [
        Mount("/private/tmp/l c/root", "/Users/a b", "ext3", "/dev/root"),
        Mount("/", "/host-users", "fakeowner", "/run/host_mark/Users"),
    ]


def _live(tmp_path: Path) -> Path:
    repository, _runtime_root = _seed_loader_composed_completed_change(tmp_path, marked=False)
    (repository / ".owlbear/delivery/config.json").write_text(_startup_config().model_dump_json(), encoding="utf-8")
    return repository


def test_prepare_copies_git_and_delivery_state_and_compare_detects_live_changes(tmp_path: Path) -> None:
    live = _live(tmp_path)
    (live / ".owlbear/delivery/.venv").mkdir()
    (live / ".owlbear/delivery/.venv/bin").write_text("ignored\n", encoding="utf-8")
    stage = tmp_path / "stage"

    summary = delivery_lc.prepare(live, stage)

    root = stage / "root"
    assert summary["records"] == len(delivery_lc.record_hashes(live))
    assert (root / ".git/HEAD").is_file()
    assert not (root / ".owlbear/delivery/.venv").exists()
    assert delivery_lc.record_hashes(root) == delivery_lc.record_hashes(live)
    assert (root / delivery_lc.COPY_MARKER).read_text(encoding="utf-8").startswith(f"copy-of-{live.resolve()} ")
    worktree = next((root / ".owlbear/delivery/worktrees").iterdir())
    live_worktree = live / ".owlbear/delivery/worktrees" / worktree.name
    assert (worktree / ".git").read_bytes() == (live_worktree / ".git").read_bytes()
    assert delivery_lc.compare(live, stage)["live_unchanged"] is True
    (live / ".owlbear/delivery/runtime/changes/change-a/frontier.json").write_bytes(b"{}\n")
    assert delivery_lc.compare(live, stage) == {
        "live_unchanged": False,
        "changed": ["runtime/changes/change-a/frontier.json"],
        "records": summary["records"],
    }


def test_container_command_binds_only_the_stage_copy_at_the_live_path(tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    (stage / "control").mkdir(parents=True)
    (stage / "root").mkdir()
    live = Path(_LIVE)

    result = delivery_lc.run(stage, live, "a" * 40, "full", "b" * 40, uv_cache_volume="n00a-uv-cache", dry_run=True)

    command = result["command"]
    mounts = [command[index + 1] for index, item in enumerate(command) if item == "-v"]  # type: ignore[union-attr]
    assert mounts == [
        f"{(stage / 'root').resolve()}:{_LIVE}",
        f"{(stage / 'control').resolve()}:/lc",
        "n00a-uv-cache:/root/.cache/uv",
    ]
    assert command[-5:] == ["/lc/inside.sh", _LIVE, "a" * 40, "full", "b" * 40]  # type: ignore[index]
    inside = (stage / "control/inside.sh").read_text(encoding="utf-8")
    assert "prove-isolation" in inside
    assert (stage / "control/delivery_lc.py").read_bytes() == Path(delivery_lc.__file__).read_bytes()
    assert not (stage / "control" / delivery_lc.CA_BUNDLE).exists()
    # uv and curl trust the system store, extended by an optional bundle before the first download.
    trust = inside.index("export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt UV_NATIVE_TLS=1")
    assert inside.index("/lc/ca-bundle.crt") < trust < inside.index("curl -LsSf") < inside.index("uv run")
    bundle = tmp_path / "corporate.pem"
    bundle.write_text("-----BEGIN CERTIFICATE-----\n", encoding="utf-8")
    delivery_lc.run(stage, live, "a" * 40, "load", "", ca_bundle=bundle, dry_run=True)
    assert (stage / "control" / delivery_lc.CA_BUNDLE).read_bytes() == bundle.read_bytes()


def test_module_is_stdlib_only_at_import_for_the_container_isolation_proof(tmp_path: Path) -> None:
    script = tmp_path / "delivery_lc.py"
    shutil.copyfile(delivery_lc.__file__, script)
    blocked_runner = (
        "import importlib.abc,runpy,sys\n"
        "class Blocker(importlib.abc.MetaPathFinder):\n"
        " def find_spec(self,fullname,path=None,target=None):\n"
        "  if fullname.split('.')[0] in {'owlbear_delivery','owlbear_tools','pydantic','yaml'}:\n"
        "   raise ImportError('blocked')\n"
        "sys.meta_path.insert(0,Blocker())\n"
        "sys.argv=[sys.argv[1],'--help']\n"
        "runpy.run_path(sys.argv[0],run_name='__main__')\n"
    )
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and argument vector.
        (sys.executable, "-I", "-c", blocked_runner, str(script)),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "prove-isolation" in completed.stdout


def _live_with_previous_gate(tmp_path: Path, gate_source: Path) -> tuple[Path, str]:
    """A live copy whose origin is a local bare remote and a previous-release commit carrying ``gate_source``."""
    live = _live(tmp_path)
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    _git(live, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    _git(live, "push", "origin", "HEAD:refs/heads/main")
    gate = live / "serve/delivery/src/owlbear_delivery/state_formats.py"
    gate.parent.mkdir(parents=True)
    shutil.copyfile(gate_source, gate)
    _git(live, "add", str(gate))
    _git(live, "commit", "-m", "previous release gate")
    previous = _git(live, "rev-parse", "HEAD")
    _git(live, "reset", "--soft", "HEAD~1")
    return live, previous


def _unexpected_previous_load(_live: Path, _previous: str) -> dict[str, object]:
    raise AssertionError


def test_full_form_migrates_the_copy_and_meets_the_rollback_downgrade_oracle(tmp_path: Path) -> None:
    live, previous = _live_with_previous_gate(tmp_path, _N02A_GATE)

    report = delivery_lc.full_form(live, previous, previous_load=_unexpected_previous_load)

    assert report["passed"] is True, json.dumps(report, indent=1)
    assert report["unmigrated"]["load"]["code"] == "state-migration-required"  # type: ignore[index]
    assert report["unmigrated"]["inspector"]["diagnostic_codes"] == ["FORMAT_MIGRATION_REQUIRED"]  # type: ignore[index]
    assert report["migrated"]["inspector"]["status"] == "healthy-structure"  # type: ignore[index]
    assert report["migrated"]["inspector"]["diagnostic_codes"] == []  # type: ignore[index]
    assert report["changed_records"] == [FORMAT_MARKER]
    assert [entry["locator"] for entry in report["proposal"]["entries"]] == [FORMAT_MARKER]  # type: ignore[index]
    assert report["previous_gate_before"]["refusals"] == []  # type: ignore[index]
    assert ["state-newer-than-controller", FORMAT_MARKER] in report["previous_gate_after"]["refusals"]  # type: ignore[index]
    assert "previous_load" not in report
    assert report["migrated"]["load"]["unavailable"] == []  # type: ignore[index]
    assert ["state-newer-than-controller", FORMAT_MARKER] in report["synthetic_newer"]  # type: ignore[operator]


def test_full_form_rollback_needs_the_previous_release_to_load_every_change(tmp_path: Path) -> None:
    candidate_gate = Path(delivery_lc.__file__).parents[3] / "delivery/src/owlbear_delivery/state_formats.py"
    live, previous = _live_with_previous_gate(tmp_path, candidate_gate)
    loads: list[str] = []

    def previous_load(path: Path, commit: str) -> dict[str, object]:
        loads.append(commit)
        return delivery_lc._load_every_change(path)  # noqa: SLF001 - the candidate loader stands in for it.

    report = delivery_lc.full_form(live, previous, previous_load=previous_load)

    assert report["passed"] is True, json.dumps(report, indent=1)
    assert loads == [previous]
    assert report["previous_gate_after"]["refusals"] == []  # type: ignore[index]
    assert report["previous_load"]["changes"] == report["migrated"]["load"]["changes"]  # type: ignore[index]
    assert delivery_lc.previous_release_oracle({**report, "previous_load": {}}) is False


def _oracle_report(supported_format: int, refusals: list[list[str]], **extra: object) -> dict[str, object]:
    return {
        "target_format": 1,
        "previous_gate_after": {"supported_format": supported_format, "refusals": refusals},
        "migrated": {"load": {"loaded": True, "changes": ["change-a"], "unavailable": []}},
        **extra,
    }


_NEWER = ["state-newer-than-controller", FORMAT_MARKER]
_INCOMPLETE = ["state-migration-incomplete", "runtime/migrations/" + "a" * 64 + "/journal.json"]
_LOADED = {"loaded": True, "changes": ["change-a"], "unavailable": []}


@pytest.mark.parametrize(
    ("report", "accepted"),
    [
        (_oracle_report(0, [_INCOMPLETE], previous_gate_hashes_unchanged=True), False),
        (_oracle_report(0, [_NEWER, _INCOMPLETE], previous_gate_hashes_unchanged=False), False),
        (_oracle_report(0, [_NEWER, _INCOMPLETE], previous_gate_hashes_unchanged=True), True),
        (_oracle_report(1, []), False),
        (_oracle_report(1, [], previous_load={"loaded": False, "code": "previous-load-failed"}), False),
        (_oracle_report(1, [], previous_load={**_LOADED, "unavailable": ["change-a"]}), False),
        (_oracle_report(1, [], previous_load={**_LOADED, "changes": []}), False),
        (_oracle_report(1, [_INCOMPLETE], previous_load=_LOADED), False),
        (_oracle_report(1, [], previous_load=_LOADED), True),
    ],
    ids=[
        "downgrade-incomplete-only",
        "downgrade-hashes-changed",
        "downgrade-typed-refusal",
        "rollback-empty-gate-without-load",
        "rollback-load-refused",
        "rollback-change-unavailable",
        "rollback-changes-missing",
        "rollback-gate-refuses",
        "rollback-loads-every-change",
    ],
)
def test_previous_release_oracle_requires_d3_evidence(report: dict[str, object], *, accepted: bool) -> None:
    assert delivery_lc.previous_release_oracle(report) is accepted


@pytest.mark.parametrize(
    ("inspection", "gate", "load", "agrees"),
    [
        ({"status": "healthy-structure", "inspection_complete": True, "diagnostic_codes": []}, [], _LOADED, True),
        (
            {"status": "degraded", "inspection_complete": True, "diagnostic_codes": ["COORDINATION_MISSING"]},
            [],
            _LOADED,
            False,
        ),
        ({"status": "healthy-structure", "inspection_complete": False, "diagnostic_codes": []}, [], _LOADED, False),
        (
            {"status": "degraded", "diagnostic_codes": ["FORMAT_MIGRATION_REQUIRED"]},
            [["state-migration-required", FORMAT_MARKER]],
            {},
            True,
        ),
        (
            {"status": "degraded", "diagnostic_codes": ["FORMAT_MIGRATION_REQUIRED", "PENDING_TRANSACTIONS"]},
            [["state-migration-required", FORMAT_MARKER]],
            {},
            False,
        ),
        (
            {"status": "healthy-structure", "diagnostic_codes": []},
            [["state-migration-required", FORMAT_MARKER]],
            {},
            False,
        ),
        ({"status": "healthy-structure", "diagnostic_codes": []}, [_NEWER], {}, False),
        ({"status": "unsupported", "diagnostic_codes": ["FORMAT_UNSUPPORTED"]}, [_NEWER], {}, True),
    ],
    ids=[
        "healthy",
        "unexpected-diagnostic",
        "incomplete",
        "migration",
        "migration-plus-other",
        "migration-missed",
        "newer-missed",
        "newer",
    ],
)
def test_inspector_must_agree_with_the_gate_and_the_load(
    inspection: dict[str, object], gate: list[list[str]], load: dict[str, object], *, agrees: bool
) -> None:
    assert delivery_lc.inspector_agrees(inspection, gate, load) is agrees
