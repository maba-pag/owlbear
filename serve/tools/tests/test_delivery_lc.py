"""``delivery-lc`` contracts (N02-B): copy, isolation proof, container command, compare, full form."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from serve.delivery.tests.test_portfolio_application import (
    _seed_loader_composed_completed_change,
    _startup_config,
)

from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.state_formats import FORMAT_MARKER, SUPPORTED_FORMAT, format_marker_bytes
from owlbear_tools import delivery_lc
from owlbear_tools.delivery_lc import Mount, isolation_failures

if TYPE_CHECKING:
    from collections.abc import Callable

_GIT = resolve_git_executable()
_LIVE = "/Users/example/Projects/owlbear-dev"
_STAGE = "/private/tmp/lc/root"
_N02A_GATE = Path(__file__).parents[2] / "delivery/tests/fixtures/state_formats/n02a_state_formats.py.txt"
_LAUNCH_POINTS = frozenset({_LIVE, "/lc", "/root/.cache/uv"})
_EXPOSED = "the real checkout, an ancestor or a descendant of it is mounted at "
# A real `docker inspect` of a container created by `docker_command` on a dummy stage (Docker Desktop 29.4.0).
_PROBE = json.loads((Path(__file__).parent / "fixtures/delivery_lc/docker_create_inspect.json").read_text())


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
        "launch_points": _LAUNCH_POINTS,
    }
    return isolation_failures(**{**arguments, **overrides})  # type: ignore[arg-type]


def test_isolation_proof_accepts_only_the_stage_copy_at_the_live_path() -> None:
    assert _isolated() == []
    assert _isolated(mounts=[Mount("/host_mnt/private/tmp/lc/root", _LIVE)]) == []
    shared = Mount("/example/stage/root", _LIVE, "fakeowner", "/run/host_mark/Users")
    assert _isolated(mounts=[shared], stage_source="/Users/example/stage/root") == []


# An ordinary Docker Desktop container: overlay root, kernel and runtime pseudo mounts, Docker's
# /etc files, masked /proc paths, the uv cache volume, the stage at the live path and the control mount.
_CONTAINER_MOUNTINFO = f"""\
1090 931 0:233 / / rw,relatime master:400 - overlay overlay rw,lowerdir=/var/lib/docker/overlay2/l/A
1091 1090 0:236 / /proc rw,nosuid,nodev,noexec,relatime - proc proc rw
1092 1090 0:237 / /dev rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755
1093 1092 0:238 / /dev/pts rw,nosuid,noexec,relatime - devpts devpts rw,gid=5,mode=620,ptmxmode=666
1094 1090 0:239 / /sys ro,nosuid,nodev,noexec,relatime - sysfs sysfs ro
1095 1094 0:30 / /sys/fs/cgroup ro,nosuid,nodev,noexec,relatime - cgroup2 cgroup rw
1096 1092 0:235 / /dev/mqueue rw,nosuid,nodev,noexec,relatime - mqueue mqueue rw
1097 1092 0:240 / /dev/shm rw,nosuid,nodev,noexec,relatime - tmpfs shm rw,size=65536k
1098 1090 0:58 /tmp/lc/root {_LIVE} rw,nosuid,nodev,relatime - fakeowner /run/host_mark/private rw
1099 1090 0:58 /tmp/lc/control /lc rw,nosuid,nodev,relatime - fakeowner /run/host_mark/private rw
1100 1090 254:1 /docker/volumes/n00a-uv-cache/_data /root/.cache/uv rw,relatime - ext4 /dev/vda1 rw
1101 1090 254:1 /docker/containers/abc/resolv.conf /etc/resolv.conf rw,relatime - ext4 /dev/vda1 rw
1102 1090 254:1 /docker/containers/abc/hostname /etc/hostname rw,relatime - ext4 /dev/vda1 rw
1103 1090 254:1 /docker/containers/abc/hosts /etc/hosts rw,relatime - ext4 /dev/vda1 rw
1104 1091 0:236 /bus /proc/bus ro,nosuid,nodev,noexec,relatime - proc proc rw
1105 1091 0:241 / /proc/acpi ro,relatime - tmpfs tmpfs ro
1106 1091 0:237 /null /proc/kcore rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755
1107 1094 0:242 / /sys/firmware ro,relatime - tmpfs tmpfs ro
"""


def _container(*extra: Mount, **overrides: object) -> list[str]:
    mounts = [*delivery_lc.parse_mountinfo(_CONTAINER_MOUNTINFO), *extra]
    return _isolated(mounts=mounts, stage_source="/private/tmp/lc/root", **overrides)


def test_isolation_proof_accepts_an_ordinary_container_mount_table() -> None:
    assert _container() == []


def test_runtime_tmpfs_is_exempt_only_with_validated_launch_provenance_showing_no_mount_there() -> None:
    runtime_tmpfs = ["/dev", "/dev/shm", "/proc/acpi", "/sys/firmware"]  # noqa: S108 - mount points.
    shm = runtime_tmpfs[1]

    assert _container(launch_points=None) == [
        "no validated host-side launch provenance",
        *(f"{_EXPOSED}{point}" for point in runtime_tmpfs),
    ]
    assert _container(launch_points=_LAUNCH_POINTS | {shm}) == [f"{_EXPOSED}{shm}"]


@pytest.mark.parametrize(
    "mount",
    [
        Mount("/Users/example/Projects/owlbear-dev/.owlbear/delivery", "/mnt/cache", "ext4", "/dev/vda1"),
        Mount("/example/Projects/owlbear-dev/.owlbear", "/mnt/cache", "fakeowner", "/run/host_mark/Users"),
        Mount("/owlbear-dev/.git", "/mnt/cache", "ext4", "/dev/vda1"),
    ],
    ids=["delivery-descendant", "docker-desktop-share-descendant", "unknown-prefix-descendant"],
)
def test_isolation_proof_rejects_a_checkout_descendant_mounted_anywhere(mount: Mount) -> None:
    assert _container(mount) == [f"{_EXPOSED}/mnt/cache"]


@pytest.mark.parametrize(
    "mount",
    [
        Mount("/Users/example", "/host-work", "overlay", "overlay"),
        Mount("/Users", "/host-work", "tmpfs", "tmpfs"),
        Mount("/", "/host-work", "overlay", "overlay"),
        Mount("/Users/example/Projects/owlbear-dev", "/dev/shm", "tmpfs", "shm"),  # noqa: S108 - mount table row.
        Mount("/Users", "/run", "tmpfs", "tmpfs"),
        Mount("/", "/run", "tmpfs", "tmpfs"),
        Mount("/", "/dev/shm", "tmpfs", "tmpfs"),  # noqa: S108 - mount table row.
    ],
    ids=[
        "overlay-alias",
        "tmpfs-alias",
        "overlay-root-alias",
        "tmpfs-bind-at-pseudo-path",
        "tmpfs-bind-at-run",
        "tmpfs-root-at-run",
        "tmpfs-stacked-on-runtime-point",
    ],
)
def test_isolation_proof_inspects_overlay_and_tmpfs_binds_like_any_other_mount(mount: Mount) -> None:
    # A mount stacked on a runtime point leaves both instances ambiguous, so each is reported.
    assert set(_container(mount)) == {f"{_EXPOSED}{mount.mount_point}"}


# An ordinary Docker Engine container on a Linux host (root filesystem /dev/sda1): overlay2 root, runc's
# /dev and /dev/shm tmpfs, kernel mounts, Docker's /etc files and masked /proc and /sys paths, a named
# volume, the stage copy at the live /home path and the control mount.
_LINUX_LIVE = "/home/user/repo"
_LINUX_MOUNTINFO = f"""\
600 520 0:52 / / rw,relatime master:300 - overlay overlay rw,lowerdir=/var/lib/docker/overlay2/l/A
601 600 0:55 / /proc rw,nosuid,nodev,noexec,relatime - proc proc rw
602 600 0:56 / /dev rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
603 602 0:57 / /dev/pts rw,nosuid,noexec,relatime - devpts devpts rw,gid=5,mode=620,ptmxmode=666
604 600 0:58 / /sys ro,nosuid,nodev,noexec,relatime - sysfs sysfs ro
605 604 0:29 / /sys/fs/cgroup ro,nosuid,nodev,noexec,relatime - cgroup2 cgroup rw,nsdelegate
606 602 0:54 / /dev/mqueue rw,nosuid,nodev,noexec,relatime - mqueue mqueue rw
607 602 0:59 / /dev/shm rw,nosuid,nodev,noexec,relatime - tmpfs shm rw,size=65536k,inode64
608 600 8:1 /var/lib/docker/containers/abc/resolv.conf /etc/resolv.conf rw,relatime - ext4 /dev/sda1 rw
609 600 8:1 /var/lib/docker/containers/abc/hostname /etc/hostname rw,relatime - ext4 /dev/sda1 rw
610 600 8:1 /var/lib/docker/containers/abc/hosts /etc/hosts rw,relatime - ext4 /dev/sda1 rw
611 600 8:1 /var/lib/docker/volumes/n00a-uv-cache/_data /root/.cache/uv rw,relatime master:1 - ext4 /dev/sda1 rw
612 600 8:1 /tmp/lc/root {_LINUX_LIVE} rw,relatime - ext4 /dev/sda1 rw
613 600 8:1 /tmp/lc/control /lc rw,relatime - ext4 /dev/sda1 rw
614 601 0:55 /bus /proc/bus ro,nosuid,nodev,noexec,relatime - proc proc rw
615 601 0:55 /sysrq-trigger /proc/sysrq-trigger ro,nosuid,nodev,noexec,relatime - proc proc rw
616 601 0:60 / /proc/asound ro,relatime - tmpfs tmpfs ro,inode64
617 601 0:61 / /proc/acpi ro,relatime - tmpfs tmpfs ro,inode64
618 601 0:56 /null /proc/kcore rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
619 601 0:56 /null /proc/timer_list rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
620 601 0:62 / /proc/scsi ro,relatime - tmpfs tmpfs ro,inode64
621 604 0:63 / /sys/firmware ro,relatime - tmpfs tmpfs ro,inode64
622 604 0:64 / /sys/devices/virtual/powercap ro,relatime - tmpfs tmpfs ro,inode64
"""


def _linux(*extra: Mount) -> list[str]:
    mounts = [*delivery_lc.parse_mountinfo(_LINUX_MOUNTINFO), *extra]
    return _isolated(
        mounts=mounts,
        live=_LINUX_LIVE,
        stage_source="/tmp/lc/root",  # noqa: S108 - host stage path in a mount table.
        common_dirs={"copy": f"{_LINUX_LIVE}/.git"},
    )


def test_isolation_proof_accepts_an_ordinary_linux_docker_mount_table() -> None:
    assert _linux() == []


@pytest.mark.parametrize(
    "mount",
    [
        Mount("/", "/run/host-home", "tmpfs", "tmpfs"),
        Mount("/user", "/run/user-home", "tmpfs", "tmpfs"),
        Mount("/", "/sys/devices/virtual/powercap", "tmpfs", "home"),
        Mount("/", "/dev/shm", "tmpfs", "shm"),  # noqa: S108 - mount table row.
    ],
    ids=["host-tmpfs-home-root", "host-tmpfs-home-subdirectory", "named-tmpfs-at-runtime-point", "second-shm"],
)
def test_isolation_proof_rejects_a_host_tmpfs_ancestor_that_looks_like_a_fresh_instance(mount: Mount) -> None:
    assert set(_linux(mount)) == {f"{_EXPOSED}{mount.mount_point}"}


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

    assert failures == [f"{_EXPOSED}{mount.mount_point}"]


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


def _live(tmp_path: Path, *, marked: bool = False) -> Path:
    repository, _runtime_root = _seed_loader_composed_completed_change(tmp_path, marked=marked)
    (repository / ".owlbear/delivery/config.json").write_text(_startup_config().model_dump_json(), encoding="utf-8")
    return repository


_FRONTIER = "runtime/changes/change-a/frontier.json"


def _pretty_frontier(live: Path, *, schema_version: int | None = None) -> bytes:
    frontier = live / ".owlbear/delivery" / _FRONTIER
    payload = json.loads(frontier.read_bytes())
    if schema_version is not None:
        payload["schema_version"] = schema_version
    frontier.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return frontier.read_bytes()


def test_load_form_reads_without_canonicalizing_and_fails_when_a_load_rewrites_a_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    live = _live(tmp_path, marked=True)
    pretty = _pretty_frontier(live)

    report = delivery_lc.load_form(live)

    assert report["passed"] is True, json.dumps(report, indent=1)
    assert report["records_changed"] == {}
    assert (live / ".owlbear/delivery" / _FRONTIER).read_bytes() == pretty
    # The normal composition canonicalizes the frontier; the guard fails the form on that write.
    monkeypatch.setattr(delivery_lc, "_read_only_load", delivery_lc._load_every_change)  # noqa: SLF001

    rewritten = delivery_lc.load_form(live)

    assert rewritten["load"]["loaded"] is True  # type: ignore[index]
    assert (live / ".owlbear/delivery" / _FRONTIER).read_bytes() != pretty
    assert rewritten["records_changed"] == {"load": [_FRONTIER]}
    assert rewritten["passed"] is False


def _add(delivery: Path) -> None:
    (delivery / "runtime/stray.json").write_bytes(b"{}\n")


def _delete(delivery: Path) -> None:
    (delivery / "runtime/changes/change-a/admission.json").unlink()


def _lock_files(delivery: Path) -> None:
    (delivery / "runtime/controller.lock").write_bytes(b"")
    (delivery / "runtime/changes/change-a/.storage.lock").write_bytes(b"")
    (delivery / "runtime/claims").mkdir(exist_ok=True)
    (delivery / "runtime/claims/lc-probe").write_bytes(b"claim\n")


@pytest.mark.parametrize(
    ("mutate", "changed"),
    [
        (_add, {"load": ["runtime/stray.json"]}),
        (_delete, {"load": ["runtime/changes/change-a/admission.json"]}),
        (_lock_files, {}),
    ],
    ids=["addition", "deletion", "lock-files-ignored"],
)
def test_load_form_fails_on_any_record_addition_or_deletion_but_ignores_lock_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutate: Callable[[Path], None], changed: dict[str, list[str]]
) -> None:
    live = _live(tmp_path, marked=True)
    read_only_load = delivery_lc._read_only_load  # noqa: SLF001

    def mutating_load(path: Path) -> dict[str, object]:
        result = read_only_load(path)
        mutate(path / ".owlbear/delivery")
        return result

    monkeypatch.setattr(delivery_lc, "_read_only_load", mutating_load)

    report = delivery_lc.load_form(live)

    assert report["load"]["loaded"] is True  # type: ignore[index]
    assert report["records_changed"] == changed
    assert report["passed"] is (not changed)


def test_full_form_fails_when_the_migrated_load_rewrites_a_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    live, previous = _live_with_previous_gate(tmp_path, _N02A_GATE)
    # A stored schema-18 frontier is never rewritten by a read (N03 section 1.7); a non-canonical 19 one is.
    pretty = _pretty_frontier(live, schema_version=19)
    monkeypatch.setattr(delivery_lc, "_read_only_load", delivery_lc._load_every_change)  # noqa: SLF001

    report = delivery_lc.full_form(live, previous, previous_load=_unexpected_previous_load)

    assert report["unmigrated"]["records_changed"] == {}  # type: ignore[index]
    assert report["migrated"]["records_changed"] == {"load": [_FRONTIER]}  # type: ignore[index]
    assert sorted(report["changed_records"]) == sorted([FORMAT_MARKER, _COORDINATION])  # type: ignore[arg-type]
    assert (live / ".owlbear/delivery" / _FRONTIER).read_bytes() != pretty
    assert report["passed"] is False


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
    assert command[:2] == ["docker", "create"]  # type: ignore[index]
    assert "--rm" not in command  # type: ignore[operator]
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
    assert "--launch /lc/launch.json" in inside


_PROBE_STAGE = Path(_PROBE["probe"]["stage"])
_PROBE_LIVE = Path(_PROBE["probe"]["live"])
_PROBE_CACHE = _PROBE["probe"]["uv_cache_volume"]


def _probe(mutate: Callable[[dict[str, Any]], object] | None = None) -> dict[str, Any]:
    container = json.loads(json.dumps(_PROBE["container"]))
    if mutate is not None:
        mutate(container)
    return container


def _launch(container: dict[str, Any], volume: dict[str, Any] | None = None, **overrides: Any) -> dict[str, Any]:
    arguments = {"stage": _PROBE_STAGE, "live": _PROBE_LIVE, "uv_cache_volume": _PROBE_CACHE, **overrides}
    return delivery_lc.launch_report(container, volume or _PROBE["volume"], **arguments)


def test_launch_provenance_accepts_the_recorded_docker_create_inspect() -> None:
    report = _launch(_probe())

    assert report["failures"] == []
    assert report["validated"] is True
    assert report["mount_points"] == sorted([str(_PROBE_LIVE), "/lc", "/root/.cache/uv"])
    assert report["host_config"]["Binds"] == _PROBE["container"]["HostConfig"]["Binds"]
    assert report["volume"] == _PROBE["volume"]


def _host(key: str, value: object) -> Callable[[dict[str, Any]], object]:
    return lambda container: container["HostConfig"].__setitem__(key, value)


_HOME_SHM = {"Type": "bind", "Source": "/home", "Destination": "/dev/shm", "RW": True}  # noqa: S108


def _home_bound_at_shm(container: dict[str, Any]) -> None:
    container["HostConfig"]["Binds"].append("/home:/dev/shm")
    container["Mounts"].append(_HOME_SHM)


def _anonymous_volume(container: dict[str, Any]) -> None:
    container["Mounts"].append({"Type": "volume", "Name": "f" * 64, "Destination": "/data", "Driver": "local"})


def _foreign_cache_driver(container: dict[str, Any]) -> None:
    container["Mounts"][2]["Driver"] = "sshfs"


def _live_checkout_as_stage(container: dict[str, Any]) -> None:
    container["Mounts"][0]["Source"] = str(_PROBE_LIVE)


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (_home_bound_at_shm, "HostConfig.Binds"),
        (_host("Tmpfs", {"/dev/shm": ""}), "HostConfig.Tmpfs"),  # noqa: S108 - inspect field.
        (_host("Mounts", [{"Type": "tmpfs", "Target": "/dev/shm"}]), "HostConfig.Mounts"),  # noqa: S108
        (_host("Privileged", True), "privileged"),  # noqa: FBT003 - inspect field value.
        (_host("CapAdd", ["SYS_ADMIN"]), "HostConfig.CapAdd"),
        (_host("VolumesFrom", ["other"]), "HostConfig.VolumesFrom"),
        (_host("Devices", [{"PathOnHost": "/dev/sda"}]), "HostConfig.Devices"),
        (_host("PidMode", "host"), "HostConfig.PidMode"),
        (_host("IpcMode", "host"), "HostConfig.IpcMode"),
        (_anonymous_volume, "mounts at /data"),
        (_foreign_cache_driver, "mounts at /root/.cache/uv"),
        (_live_checkout_as_stage, f"mounts at {_PROBE_LIVE}"),
    ],
    ids=[
        "host-home-bound-at-shm",
        "tmpfs",
        "mount-api",
        "privileged",
        "capability",
        "volumes-from",
        "device",
        "host-pid",
        "host-ipc",
        "anonymous-volume",
        "foreign-cache-driver",
        "live-checkout-at-live-path",
    ],
)
def test_launch_provenance_rejects_any_other_host_access(
    mutate: Callable[[dict[str, Any]], object], reason: str
) -> None:
    report = _launch(_probe(mutate))

    assert report["validated"] is False
    assert any(reason in failure for failure in report["failures"]), report["failures"]


def test_launch_provenance_rejects_a_stage_inside_the_checkout() -> None:
    report = _launch(_probe(), live=_PROBE_STAGE.parent)

    assert report["validated"] is False
    assert any("overlaps the real checkout" in failure for failure in report["failures"])


_BIND_VOLUME = _PROBE["bind_volume"]
_BIND_DEVICE = _BIND_VOLUME["Options"]["device"]


@pytest.mark.parametrize(
    ("volume", "live", "refused"),
    [
        (_PROBE["volume"], str(_PROBE_LIVE), None),
        (_BIND_VOLUME, "/Users/example/Projects/owlbear-dev", None),
        (_BIND_VOLUME, str(Path(_BIND_DEVICE).parents[1]), "overlapping the real checkout"),
        (_BIND_VOLUME, f"{_BIND_DEVICE}/inner", "overlapping the real checkout"),
        (_BIND_VOLUME, _BIND_DEVICE.removeprefix("/private"), "overlapping the real checkout"),
        ({**_PROBE["volume"], "Driver": "rclone"}, str(_PROBE_LIVE), "not local"),
        ({**_PROBE["volume"], "Options": {"type": "nfs", "device": ":/x"}}, str(_PROBE_LIVE), "unsupported"),
        ({**_BIND_VOLUME, "Name": "other"}, str(_PROBE_LIVE), "not an inspected named volume"),
    ],
    ids=[
        "plain-named-volume",
        "bind-elsewhere",
        "bind-to-live-descendant",
        "bind-to-live-ancestor",
        "bind-to-live-alias",
        "foreign-driver",
        "nfs-options",
        "other-volume",
    ],
)
def test_uv_cache_volume_must_be_local_and_clear_of_the_checkout(
    volume: dict[str, Any], live: str, refused: str | None
) -> None:
    expected_name = _BIND_VOLUME["Name"] if volume["Name"] == "other" else volume["Name"]

    failures = delivery_lc.volume_failures(volume, name=expected_name, live=live)

    assert (failures == []) if refused is None else any(refused in failure for failure in failures), failures


@pytest.mark.parametrize(
    "cache",
    ["/Users/example/Projects/owlbear-dev/.owlbear/delivery", "./cache", "cache/uv", "~", "c"],
)
def test_path_like_uv_cache_is_refused_before_any_docker_call(tmp_path: Path, cache: str) -> None:
    stage = tmp_path / "stage"
    (stage / "control").mkdir(parents=True)

    with pytest.raises(ValueError, match="must name a Docker volume"):
        delivery_lc.run(stage, Path(_LIVE), "a" * 40, "load", "", uv_cache_volume=cache, dry_run=True)
    arguments = ["run", "--stage", str(stage), "--live", _LIVE, "--candidate", "a" * 40, "--form", "load"]
    assert delivery_lc.main([*arguments, "--uv-cache-volume", cache, "--dry-run"]) == 2


class _FakeDocker:
    """Stands in for the Docker CLI with the recorded inspect output rebased onto a temporary stage."""

    def __init__(self, stage: Path, container: dict[str, Any], volume: dict[str, Any]) -> None:
        rebased = json.dumps(container).replace(str(_PROBE_STAGE), str(stage.resolve()))
        self.container, self.volume = json.loads(rebased), volume
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        del check
        self.calls.append(arguments)
        outputs = {"create": "cid\n", "inspect": json.dumps([self.container])}
        stdout = json.dumps([self.volume]) if arguments[:2] == ("volume", "inspect") else outputs.get(arguments[0], "")
        return subprocess.CompletedProcess(arguments, 0, stdout=stdout, stderr="")


def _run_with(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, container: dict[str, Any], volume: dict[str, Any]
) -> tuple[dict[str, Any], _FakeDocker, list[str]]:
    stage = tmp_path / "stage"
    (stage / "control").mkdir(parents=True)
    docker, started = _FakeDocker(stage, container, volume), []

    def start(container_id: str, _log: Path) -> int:
        started.append(container_id)
        (stage / "control/report.json").write_text('{"passed": true}', encoding="utf-8")
        return 0

    monkeypatch.setattr(delivery_lc, "_docker", docker)
    monkeypatch.setattr(delivery_lc, "_start", start)
    result = delivery_lc.run(stage, _PROBE_LIVE, "a" * 40, "load", "", uv_cache_volume=_PROBE_CACHE)
    return result, docker, started


def test_run_starts_only_a_container_whose_inspect_provenance_validates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    result, docker, started = _run_with(monkeypatch, tmp_path, _probe(), _PROBE["volume"])

    assert (result["exit"], result["report"], started) == (0, {"passed": True}, ["cid"])
    assert docker.calls[0] == ("volume", "create", _PROBE_CACHE)
    assert docker.calls[-1] == ("rm", "-f", "cid")
    recorded = json.loads((tmp_path / "stage/control/launch.json").read_text(encoding="utf-8"))
    assert recorded == result["launch"]
    assert recorded["validated"] is True


def test_run_never_starts_a_container_with_an_extra_mount(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    result, docker, started = _run_with(monkeypatch, tmp_path, _probe(_home_bound_at_shm), _PROBE["volume"])

    assert (result["exit"], started) == (None, [])
    assert result["launch"]["validated"] is False
    assert docker.calls[-1] == ("rm", "-f", "cid")
    assert json.loads((tmp_path / "stage/control/launch.json").read_text(encoding="utf-8"))["validated"] is False


def test_run_refuses_a_cache_volume_bound_into_the_checkout_before_creating_a_container(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    delivery = {**_BIND_VOLUME, "Name": _PROBE_CACHE, "Options": {**_BIND_VOLUME["Options"]}}
    delivery["Options"]["device"] = f"{_PROBE_LIVE}/.owlbear/delivery"

    result, docker, started = _run_with(monkeypatch, tmp_path, _probe(), delivery)

    assert (result["exit"], started) == (None, [])
    assert "overlapping the real checkout" in result["launch"]["failures"][0]
    assert [call[0] for call in docker.calls] == ["volume", "volume"]


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
    _downgrade_coordination(live)
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


_COORDINATION = "runtime/coordination/changes/change-a.json"


def _downgrade_coordination(live: Path) -> None:
    """Write the coordination record as live holds it before N09-A2: schema 1, no Pause request."""
    path = live / ".owlbear/delivery" / _COORDINATION
    payload = json.loads(path.read_bytes())
    payload.pop("pause_request", None)
    payload["schema_version"] = 1
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def _unexpected_previous_load(_live: Path, _previous: str) -> dict[str, object]:
    raise AssertionError


def test_full_form_migrates_the_copy_and_meets_the_rollback_downgrade_oracle(tmp_path: Path) -> None:
    live, previous = _live_with_previous_gate(tmp_path, _N02A_GATE)

    report = delivery_lc.full_form(live, previous, previous_load=_unexpected_previous_load)

    assert report["passed"] is True, json.dumps(report, indent=1)
    assert report["unmigrated"]["load"]["code"] == "state-migration-required"  # type: ignore[index]
    assert report["unmigrated"]["inspector"]["diagnostic_codes"] == [  # type: ignore[index]
        "COORDINATION_MIGRATION_REQUIRED",
        "FORMAT_MIGRATION_REQUIRED",
    ]
    assert report["migrated"]["inspector"]["status"] == "healthy-structure"  # type: ignore[index]
    assert report["migrated"]["inspector"]["diagnostic_codes"] == []  # type: ignore[index]
    assert sorted(report["changed_records"]) == sorted([FORMAT_MARKER, _COORDINATION])  # type: ignore[arg-type]
    assert sorted(entry["locator"] for entry in report["proposal"]["entries"]) == sorted(  # type: ignore[index]
        [FORMAT_MARKER, _COORDINATION]
    )
    assert report["proposal"]["source_format"] == 0  # type: ignore[index]
    assert report["proposal"]["steps"] == ["format-0-to-1", "format-1-to-2", "format-2-to-3"]  # type: ignore[index]
    assert report["previous_gate_before"]["refusals"] == []  # type: ignore[index]
    assert ["state-newer-than-controller", FORMAT_MARKER] in report["previous_gate_after"]["refusals"]  # type: ignore[index]
    assert "previous_load" not in report
    assert report["migrated"]["load"]["unavailable"] == []  # type: ignore[index]
    assert ["state-newer-than-controller", FORMAT_MARKER] in report["synthetic_newer"]  # type: ignore[operator]


def test_full_form_from_an_older_format_ignores_the_journals_of_earlier_migrations(tmp_path: Path) -> None:
    live, previous = _live_with_previous_gate(tmp_path, _N02A_GATE)
    assert delivery_lc.full_form(live, previous, previous_load=_unexpected_previous_load)["passed"] is True
    (live / ".owlbear/delivery" / FORMAT_MARKER).write_bytes(format_marker_bytes(SUPPORTED_FORMAT - 1))

    report = delivery_lc.full_form(live, previous, previous_load=_unexpected_previous_load)

    assert report["passed"] is True, json.dumps(report, indent=1)
    assert report["changed_records"] == [FORMAT_MARKER]
    assert report["unmigrated"]["inspector"]["diagnostic_codes"] == ["FORMAT_MIGRATION_REQUIRED"]  # type: ignore[index]


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


def test_full_form_downgrade_refuses_exactly_the_records_of_a_family_version_the_previous_release_lacks(
    tmp_path: Path,
) -> None:
    candidate = Path(delivery_lc.__file__).parents[3] / "delivery/src/owlbear_delivery/state_formats.py"
    source = candidate.read_text(encoding="utf-8")
    coordination_2 = (
        '"M",\n        2,\n        rewrites=((1, "owlbear_delivery.state_migration:coordination_1_to_2"),),'
    )
    assert source.count(coordination_2) == 1
    gate = tmp_path / "previous-gate/state_formats.py"
    gate.parent.mkdir()
    gate.write_text(source.replace(coordination_2, '"M",\n        1,'), encoding="utf-8")
    live, previous = _live_with_previous_gate(tmp_path, gate)

    report = delivery_lc.full_form(live, previous, previous_load=_unexpected_previous_load)

    assert report["passed"] is True, json.dumps(report, indent=1)
    assert report["previous_gate_after"]["supported_format"] == report["target_format"]  # type: ignore[index]
    assert report["previous_gate_after"]["refusals"] == [["state-newer-than-controller", _COORDINATION]]  # type: ignore[index]
    assert report["previous_beyond"] == [_COORDINATION]
    assert "previous_load" not in report


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
_BUMPED = ["state-newer-than-controller", _COORDINATION]


def _bumped_report(refusals: list[list[str]], **extra: object) -> dict[str, Any]:
    """Format 1 in both releases; the candidate moved coordination to 2, the previous registry reads only 1."""
    versions = [["config", "config.json", 2], ["coordination", _COORDINATION, 2]]
    report: dict[str, Any] = _oracle_report(1, refusals, migrated_versions=versions, **extra)
    report["previous_gate_after"]["read_versions"] = {"config": [2], "coordination": [1]}
    return report


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
        (_bumped_report([_BUMPED], previous_gate_hashes_unchanged=True), True),
        (
            _bumped_report(
                [["state-newer-than-controller", "runtime/changes/change-a/frontier.json"]],
                previous_gate_hashes_unchanged=True,
            ),
            False,
        ),
        (_bumped_report([_BUMPED, _INCOMPLETE], previous_gate_hashes_unchanged=True), False),
        (_bumped_report([["state-version-unknown", _COORDINATION]], previous_gate_hashes_unchanged=True), False),
        (_bumped_report([], previous_gate_hashes_unchanged=True, previous_load=_LOADED), False),
        (_bumped_report([_BUMPED], previous_gate_hashes_unchanged=False), False),
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
        "family-bump-typed-refusal-at-bumped-records",
        "family-bump-refusal-at-unrelated-record",
        "family-bump-extra-refusal",
        "family-bump-untyped-refusal",
        "family-bump-previous-loads",
        "family-bump-hashes-changed",
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


# ---------------------------------------------------------------------------
# N02-D: pin-state capture and the upgrade rehearsal verdict
# ---------------------------------------------------------------------------


def _pinned(live: Path) -> None:
    controller = live / ".owlbear/controller"
    (controller / "bin").mkdir(parents=True)
    (controller / "pin.json").write_text('{"schema_version": 1, "commit": "' + "a" * 40 + '"}\n', encoding="utf-8")
    (controller / "bin/delivery-mcp").write_text("#!/bin/sh\nexec release\n", encoding="utf-8")
    release = controller / "releases" / ("a" * 40)
    (release / ".venv").mkdir(parents=True)
    (release / "RELEASE.json").write_text('{"commit": "' + "a" * 40 + '"}\n', encoding="utf-8")
    (live / ".vscode").mkdir()
    (live / ".vscode/mcp.json").write_text('{"servers": {}}\n', encoding="utf-8")


def test_prepare_copies_pin_state_without_release_trees_and_compare_covers_it(tmp_path: Path) -> None:
    live = _live(tmp_path)
    _pinned(live)
    stage = tmp_path / "stage"

    delivery_lc.prepare(live, stage)

    root, control = stage / "root/.owlbear/controller", stage / "control"
    assert (root / "pin.json").read_bytes() == (live / ".owlbear/controller/pin.json").read_bytes()
    assert (root / "bin/delivery-mcp").is_file()
    assert not (root / "releases").exists()
    assert (control / "controller/releases" / ("a" * 40) / "RELEASE.json").is_file()
    assert (control / "mcp.json").is_file()
    assert {"controller/pin.json", "controller/bin/delivery-mcp"} <= set(delivery_lc.record_hashes(live))
    (live / ".owlbear/controller/pin.json").write_text("{}\n", encoding="utf-8")
    assert delivery_lc.compare(live, stage)["changed"] == ["controller/pin.json"]


def test_upgrade_form_needs_a_previous_release_and_prebuilt_bundles(tmp_path: Path) -> None:
    base = ["run", "--stage", str(tmp_path), "--live", str(tmp_path), "--candidate", "c" * 40, "--form", "upgrade"]

    assert delivery_lc._run_command(delivery_lc._parser().parse_args(base), tmp_path)[0] == 2  # noqa: SLF001
    with_previous = delivery_lc._parser().parse_args([*base, "--previous", "p" * 40])  # noqa: SLF001
    assert delivery_lc._run_command(with_previous, tmp_path) == (  # noqa: SLF001
        2,
        {"error": "the upgrade form needs --bundles with the candidate's (and a gated previous) bundle"},
    )


def test_readiness_blockers_name_running_and_interrupted_custody_only() -> None:
    views = {
        "a": {"kind": "change", "outcomes": [{"readiness": {"state": "running", "reason_code": "claim-active"}}]},
        "b": {"finalization": {"readiness": {"state": "blocked", "reason_code": "engine-action-interrupted"}}},
        "c": {"readiness": {"state": "ready", "reason_code": "plan-ready"}},
        "d": [{"readiness": {"state": "attention", "reason_code": "engine-action-failed"}}],
    }

    assert delivery_lc.readiness_blockers(views) == ["claim-active", "engine-action-interrupted"]


def _session(**overrides: object) -> dict[str, object]:
    return {"started": True, "health_status": "healthy", "unavailable": [], "blockers": [], **overrides}


def _upgrade_report(*, gated: bool, **overrides: object) -> dict[str, Any]:
    report: dict[str, Any] = {
        "previous_controller": {"gated": gated, "online": _session(), "release": {"supported_format": 2}},
        "candidate_release": {"installed": True, "supported_format": 2},
        "offline_preflight": {"exit": 0, "ready": True, "blockers": []},
        "backup": {"exit": 0},
        "migration": {"required": True, "verified": True, "proposal": {"entries": [{"locator": FORMAT_MARKER}]}},
        "changed_records": [FORMAT_MARKER],
        "switch": {"exit": 0},
        "mcp_json_names_launcher": True,
        "first_start": _session(),
        "second_start": _session(),
        "round_trip_unchanged": True,
        "cockpit": {"work_items_status": 200, "index_matches_release": True},
        "checkout_controller": {"loaded": False, "code": "controller-not-pinned"},
        "verify": {"exit": 0},
        "rollback": {"exit": 0} if gated else {"exit": 1, "code": "release-invalid"},
    }
    if gated:
        report["rollback_start"] = _session()
    return {**report, **overrides}


# A gated previous release whose format is older than the migrated state's must refuse the switch back (D3).
_older_previous = {"gated": True, "online": _session(), "release": {"supported_format": 1}}
_refused = {"exit": 1, "code": "release-refuses-state"}


@pytest.mark.parametrize(
    ("report", "passed"),
    [
        (_upgrade_report(gated=False), True),
        (_upgrade_report(gated=True), True),
        (_upgrade_report(gated=True, migration={"required": False, "proposal": {}}, changed_records=[]), True),
        (_upgrade_report(gated=False, previous_controller={"gated": False, "online": _session(blockers=["x"])}), False),
        (_upgrade_report(gated=False, offline_preflight={"exit": 1, "blockers": [{"code": "claim-running"}]}), False),
        (_upgrade_report(gated=False, changed_records=[FORMAT_MARKER, "runtime/changes/a/frontier.json"]), False),
        (_upgrade_report(gated=False, first_start=_session(unavailable=["a"])), False),
        (_upgrade_report(gated=False, round_trip_unchanged=False), False),
        (_upgrade_report(gated=False, cockpit={"work_items_status": 200, "index_matches_release": False}), False),
        (_upgrade_report(gated=False, checkout_controller={"loaded": True}), False),
        (_upgrade_report(gated=False, rollback={"exit": 0}), False),
        (_upgrade_report(gated=True, rollback={"exit": 1, "code": "release-refuses-state"}), False),
        (_upgrade_report(gated=True, previous_controller=_older_previous, rollback=_refused), True),
        (_upgrade_report(gated=True, previous_controller=_older_previous), False),
        (_upgrade_report(gated=True, rollback_start=_session(unavailable=["a"])), False),
        (_upgrade_report(gated=False, first_start=_session(health_status="degraded")), False),
        (_upgrade_report(gated=False, second_start=_session(health_status="degraded")), False),
        (_upgrade_report(gated=False, first_start=_session(health_status=None)), False),
        (_upgrade_report(gated=True, rollback_start=_session(health_status="degraded")), False),
        (
            _upgrade_report(gated=False, previous_controller={"gated": False, "online": _session(health_status="x")}),
            False,
        ),
    ],
    ids=[
        "first-upgrade",
        "gated-rollback",
        "no-migration-needed",
        "online-blocker",
        "offline-blocker",
        "unproposed-record-changed",
        "change-unavailable",
        "round-trip-changed",
        "foreign-bundle",
        "checkout-code-started",
        "ungated-switch-back",
        "gated-rollback-refused",
        "older-format-rollback-refused",
        "older-format-rollback-accepted",
        "rollback-loses-change",
        "candidate-unhealthy",
        "restart-unhealthy",
        "candidate-health-missing",
        "rollback-unhealthy",
        "previous-unhealthy",
    ],
)
def test_upgrade_verdict_requires_every_procedure_step(report: dict[str, Any], *, passed: bool) -> None:
    assert delivery_lc.upgrade_passed(report) is passed
