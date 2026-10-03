"""Release-gated effect entry: fake-gh ordering tests and the real-gh EOF falsifier (G12, D16).

The falsifier runs the installed ``gh`` against a local HTTP recorder only: ``GH_HOST`` is
``github.localhost`` (plain HTTP to ``api.github.localhost``) and ``HTTP_PROXY`` routes that host to
the recorder; the token is a dummy and the configuration directory is temporary. A missing ``gh``
fails these tests; it never skips them.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear_delivery.publication_provider import (
    PublicationMergeMethod,
    PublicationMergeRequestStatus,
    RequestPublicationMerge,
)
from owlbear_delivery_github import GitHubCliPublicationProvider
from owlbear_delivery_github.effect_launcher import (
    LAUNCHER_UNSENT_EXIT,
    TOKEN_SIZE,
    freeze_body,
    read_process_start_time,
    run_release_gated,
    spawn_effect,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_HEAD = "a" * 40
_UUID = "4b1d2c3e-0000-4000-8000-000000000001"
_GROUP_DEADLINE_SECONDS = 20.0
_CONTROLLER = r"""
import json
import os
import sys
from pathlib import Path

from owlbear_delivery_github.effect_launcher import release_token, spawn_effect

scenario, body_path, record_dir, arguments = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), json.loads(sys.argv[4])
launched = spawn_effect(tuple(arguments), body_path)
(record_dir / "observer-pid").write_text(str(launched.group_id))
if scenario == "after-spawn":
    os._exit(0)
from owlbear_delivery_github.effect_launcher import read_process_start_time

(record_dir / "group.json").write_text(
    json.dumps({"group_id": launched.group_id, "start_time": read_process_start_time(launched.group_id)})
)
if scenario == "after-group":
    os._exit(0)
(record_dir / "release.json").write_text(json.dumps({"group_id": launched.group_id}))
token = release_token(launched.launch_id, launched.digest)
pipe = launched.process.stdin.fileno()
if scenario == "partial-token":
    os.write(pipe, token[: len(token) // 2])
elif scenario == "truncated-body":
    body_path.chmod(0o644)
    body_path.write_bytes(body_path.read_bytes()[:20])
    os.write(pipe, token)
elif scenario == "missing-body":
    body_path.chmod(0o644)
    body_path.unlink()
    os.write(pipe, token)
elif scenario == "full-token":
    os.write(pipe, token)
os._exit(0)
"""


@dataclass
class _Recorder:
    requests: list[dict[str, object]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def snapshot(self) -> list[dict[str, object]]:
        with self.lock:
            return list(self.requests)


def _handler(recorder: _Recorder) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _body(self) -> bytes:
            if self.headers.get("Transfer-Encoding", "").casefold() == "chunked":
                chunks: list[bytes] = []
                while True:
                    size = int(self.rfile.readline().split(b";")[0].strip() or b"0", 16)
                    if size == 0:
                        self.rfile.readline()
                        return b"".join(chunks)
                    chunks.append(self.rfile.read(size))
                    self.rfile.readline()
            length = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(length) if length else b""

        def _record(self) -> None:
            body = self._body()
            with recorder.lock:
                recorder.requests.append(
                    {
                        "method": self.command,
                        "target": self.path,
                        "host": self.headers.get("Host"),
                        "content_length": self.headers.get("Content-Length"),
                        "chunked": self.headers.get("Transfer-Encoding") is not None,
                        "body": body,
                    }
                )
            payload = json.dumps(
                {
                    "status": "pending",
                    "details": {
                        "message": "Merge request accepted",
                        "uuid": _UUID,
                        "merge_method": "merge",
                        "merge_action": "direct_merge",
                        "expected_head_sha": _HEAD,
                        "bypass_rules": False,
                    },
                }
            ).encode()
            self.send_response(202 if self.command != "CONNECT" else 405)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = do_PUT = do_POST = do_PATCH = do_CONNECT = _record  # noqa: N815 - stdlib dispatch names.

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature.
            del format, args

    return Handler


@pytest.fixture
def recorder() -> Iterator[tuple[_Recorder, int]]:
    state = _Recorder()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state, server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def real_gh() -> str:
    executable = shutil.which("gh")
    if executable is None:
        pytest.fail("the EOF falsifier requires a real gh executable on PATH; a skip would fail the gate")
    return executable


def _gh_environment(tmp_path: Path, port: int, gh: str) -> dict[str, str]:
    config = tmp_path / "gh-config"
    config.mkdir(exist_ok=True)
    proxy = f"http://127.0.0.1:{port}"
    return {
        "PATH": os.pathsep.join((str(Path(gh).parent), "/usr/bin", "/bin")),
        "HOME": str(config),
        "GH_CONFIG_DIR": str(config),
        "GH_HOST": "github.localhost",
        "GH_TOKEN": "owlbear-falsifier-dummy-token",
        "GH_ENTERPRISE_TOKEN": "owlbear-falsifier-dummy-token",
        "HTTP_PROXY": proxy,
        "http_proxy": proxy,
        "HTTPS_PROXY": proxy,
        "https_proxy": proxy,
        "NO_PROXY": "",
        "no_proxy": "",
        "GH_PROMPT_DISABLED": "1",
        "GH_NO_UPDATE_NOTIFIER": "1",
        "GH_NO_EXTENSION_UPDATE_NOTIFIER": "1",
        "GH_TELEMETRY": "false",
        "DO_NOT_TRACK": "1",
        "LC_ALL": "C",
    }


def _request() -> RequestPublicationMerge:
    return RequestPublicationMerge(
        repository="example/project",
        number=7,
        node_id="PR_node_7",
        expected_head_sha=_HEAD,
        merge_method=PublicationMergeMethod.MERGE,
    )


def _frozen(tmp_path: Path) -> tuple[Path, bytes]:
    body = freeze_body(_request())
    directory = tmp_path / "request-bodies"
    directory.mkdir(exist_ok=True)
    path = directory / f"{hashlib.sha256(body).hexdigest()}.json"
    path.write_bytes(body)
    path.chmod(0o444)
    return path, body


def _production_arguments(body_path: Path) -> tuple[str, ...]:
    captured: list[tuple[str, ...]] = []

    def capture(
        arguments: tuple[str, ...],
        _body_path: Path,
        _release: Callable[[int, str], None],
        _timeout: float,
    ) -> subprocess.CompletedProcess[bytes]:
        captured.append(arguments)
        message = "argument capture only"
        raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="argument capture only"):
        GitHubCliPublicationProvider(effect_runner=capture).request_merge(
            _request(),
            body_path=body_path,
            release=lambda _group, _start: None,
        )
    return captured[0]


def _group_gone(group_id: int) -> bool:
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    stat = Path(f"/proc/{group_id}/stat")
    with contextlib.suppress(OSError, IndexError):
        return stat.read_text(encoding="ascii").rsplit(")", maxsplit=1)[1].split()[0] == "Z"
    return False


def _wait_for_group_exit(group_id: int) -> None:
    deadline = time.monotonic() + _GROUP_DEADLINE_SECONDS
    while not _group_gone(group_id):
        if time.monotonic() > deadline:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(group_id, signal.SIGKILL)
            pytest.fail(f"launcher group {group_id} did not exit after controller death")
        time.sleep(0.05)


def _put_requests(recorder: _Recorder) -> list[dict[str, object]]:
    return [request for request in recorder.snapshot() if request["method"] == "PUT"]


def _run_controller(
    tmp_path: Path,
    scenario: str,
    gh_environment: dict[str, str],
) -> tuple[Path, bytes, dict[str, object] | None]:
    body_path, body = _frozen(tmp_path)
    arguments = _production_arguments(body_path)
    controller = tmp_path / "controller.py"
    controller.write_text(_CONTROLLER, encoding="utf-8")
    records = tmp_path / "records"
    records.mkdir()
    completed = subprocess.run(  # noqa: S603 - fixed test interpreter and controller script.
        (sys.executable, str(controller), scenario, str(body_path), str(records), json.dumps(arguments)),
        check=False,
        capture_output=True,
        env={**gh_environment, "PYTHONPATH": os.pathsep.join(sys.path)},
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    group_record = records / "group.json"
    group = json.loads(group_record.read_text()) if group_record.exists() else None
    return body_path, body, group


# Fake gh on PATH: ordering and argument shape without any network.

_FAKE_GH = """#!/bin/sh
for last; do :; done
printf '%s\\n' "$@" > "$FAKE_GH_RECORD/argv"
cat > "$FAKE_GH_RECORD/stdin"
cat "$last" > "$FAKE_GH_RECORD/body"
printf '%s' "$FAKE_GH_RESPONSE"
"""


@pytest.fixture
def fake_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    script = bin_dir / "gh"
    script.write_text(_FAKE_GH, encoding="utf-8")
    script.chmod(0o755)
    record = tmp_path / "fake-gh-record"
    record.mkdir()
    monkeypatch.setenv("PATH", os.pathsep.join((str(bin_dir), os.environ.get("PATH", ""))))
    monkeypatch.setenv("FAKE_GH_RECORD", str(record))
    monkeypatch.setenv(
        "FAKE_GH_RESPONSE",
        json.dumps(
            {
                "status": "pending",
                "details": {
                    "uuid": _UUID,
                    "merge_method": "merge",
                    "merge_action": "direct_merge",
                    "expected_head_sha": _HEAD,
                    "bypass_rules": False,
                },
            }
        ),
    )
    return record


def test_release_runs_with_a_live_recorded_group_before_gh_and_gh_reads_only_the_file(
    tmp_path: Path,
    fake_gh: Path,
) -> None:
    body_path, body = _frozen(tmp_path)
    observed: list[tuple[int, str, bool, str | None]] = []

    def release(group_id: int, start_time: str) -> None:
        observed.append(
            (group_id, start_time, (fake_gh / "argv").exists(), read_process_start_time(group_id)),
        )
        assert os.getpgid(group_id) == group_id

    result = GitHubCliPublicationProvider().request_merge(_request(), body_path=body_path, release=release)

    group_id, start_time, gh_started_before_release, live_start_time = observed[0]
    assert gh_started_before_release is False
    assert start_time == live_start_time
    assert group_id != os.getpgid(0)
    argv = (fake_gh / "argv").read_text().splitlines()
    assert argv[-2:] == ["--input", str(body_path)]
    assert "-" not in argv
    assert (fake_gh / "stdin").read_bytes() == b""
    assert (fake_gh / "body").read_bytes() == body
    assert result.status is PublicationMergeRequestStatus.PENDING


def test_raised_release_closes_the_pipe_and_gh_never_runs(tmp_path: Path, fake_gh: Path) -> None:
    body_path, _ = _frozen(tmp_path)
    groups: list[int] = []

    def release(group_id: int, _start_time: str) -> None:
        groups.append(group_id)
        message = "release record write failed"
        raise OSError(message)

    with pytest.raises(OSError, match="release record write failed"):
        GitHubCliPublicationProvider().request_merge(_request(), body_path=body_path, release=release)

    _wait_for_group_exit(groups[0])
    assert not (fake_gh / "argv").exists()


@pytest.mark.parametrize(
    "token",
    [b"", b"0" * (TOKEN_SIZE - 1), b"f" * TOKEN_SIZE],
)
def test_launcher_exits_unsent_on_eof_short_or_wrong_token(tmp_path: Path, fake_gh: Path, token: bytes) -> None:
    body_path, _ = _frozen(tmp_path)
    launched = spawn_effect(_production_arguments(body_path), body_path)
    assert launched.process.stdin is not None
    launched.process.stdin.write(token)
    launched.process.stdin.close()

    completed = launched.finish(30.0)

    assert completed.returncode == LAUNCHER_UNSENT_EXIT
    assert b"unsent" in completed.stderr
    assert not (fake_gh / "argv").exists()


def test_launcher_refuses_stdin_input_and_foreign_commands(tmp_path: Path) -> None:
    body_path, _ = _frozen(tmp_path)
    arguments = _production_arguments(body_path)

    for invalid in (
        (*arguments[:-1], "-"),
        ("sh", *arguments[1:]),
        (*arguments, "--input", str(body_path)),
        arguments[:-2],
    ):
        with pytest.raises(ValueError, match="effect launcher"):
            spawn_effect(invalid, body_path)


def test_effect_timeout_kills_the_group_and_reraises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "slow-bin"
    bin_dir.mkdir()
    script = bin_dir / "gh"
    script.write_text("#!/bin/sh\nexec sleep 30\n", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", os.pathsep.join((str(bin_dir), os.environ.get("PATH", ""))))
    body_path, _ = _frozen(tmp_path)
    groups: list[int] = []

    with pytest.raises(subprocess.TimeoutExpired):
        run_release_gated(
            _production_arguments(body_path),
            body_path,
            lambda group_id, _start: groups.append(group_id),
            1.0,
        )

    assert _group_gone(groups[0])


# Real gh against a local HTTP recorder: the G12 EOF falsifier.


def test_recorder_detects_the_stdin_eof_empty_put_hazard(
    tmp_path: Path,
    recorder: tuple[_Recorder, int],
    real_gh: str,
) -> None:
    state, port = recorder
    body_path, _ = _frozen(tmp_path)
    arguments = (*_production_arguments(body_path)[:-1], "-")

    completed = subprocess.run(  # noqa: S603 - real gh pointed at the local recorder only.
        arguments,
        check=False,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        env=_gh_environment(tmp_path, port, real_gh),
        timeout=60,
    )

    puts = _put_requests(state)
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    assert len(puts) == 1
    assert puts[0]["body"] == b""


def test_released_provider_request_sends_exactly_the_frozen_body_once(
    tmp_path: Path,
    recorder: tuple[_Recorder, int],
    real_gh: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, port = recorder
    for name, value in _gh_environment(tmp_path, port, real_gh).items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    body_path, body = _frozen(tmp_path)
    releases: list[int] = []

    result = GitHubCliPublicationProvider().request_merge(
        _request(),
        body_path=body_path,
        release=lambda group_id, _start: releases.append(group_id),
    )

    puts = _put_requests(state)
    assert len(releases) == 1
    assert result.status is PublicationMergeRequestStatus.PENDING
    assert result.pending is not None
    assert result.pending.matches(_request())
    assert state.snapshot() == puts
    assert len(puts) == 1
    assert puts[0]["host"] == "api.github.localhost"
    assert str(puts[0]["target"]).endswith("/repos/example/project/pulls/7/merge-async")
    assert puts[0]["body"] == body
    assert puts[0]["content_length"] == str(len(body))
    assert puts[0]["chunked"] is False


@pytest.mark.parametrize("scenario", ["after-spawn", "after-group"])
def test_controller_death_before_the_release_record_sends_no_request(
    tmp_path: Path,
    recorder: tuple[_Recorder, int],
    real_gh: str,
    scenario: str,
) -> None:
    state, port = recorder

    _, _, group = _run_controller(tmp_path, scenario, _gh_environment(tmp_path, port, real_gh))

    assert (tmp_path / "records" / "release.json").exists() is False
    assert (group is None) is (scenario == "after-spawn")
    if group is not None:
        assert group["start_time"]
    _wait_for_group_exit(int((tmp_path / "records" / "observer-pid").read_text()))
    assert state.snapshot() == []


@pytest.mark.parametrize("scenario", ["after-release", "partial-token", "truncated-body", "missing-body"])
def test_controller_death_after_release_without_a_complete_token_or_body_sends_nothing(
    tmp_path: Path,
    recorder: tuple[_Recorder, int],
    real_gh: str,
    scenario: str,
) -> None:
    state, port = recorder

    _, body, group = _run_controller(tmp_path, scenario, _gh_environment(tmp_path, port, real_gh))

    assert group is not None
    assert (tmp_path / "records" / "release.json").exists()
    _wait_for_group_exit(int(group["group_id"]))
    requests = state.snapshot()
    assert len(requests) <= 1
    assert all(request["body"] == body for request in requests)
    assert requests == []


def test_controller_death_right_after_the_full_token_sends_exactly_the_frozen_body(
    tmp_path: Path,
    recorder: tuple[_Recorder, int],
    real_gh: str,
) -> None:
    state, port = recorder

    _, body, group = _run_controller(tmp_path, "full-token", _gh_environment(tmp_path, port, real_gh))

    assert group is not None
    _wait_for_group_exit(int(group["group_id"]))
    requests = state.snapshot()
    assert len(requests) == 1
    assert requests[0]["method"] == "PUT"
    assert requests[0]["body"] == body
    assert requests[0]["body"] != b""
    assert requests[0]["content_length"] == str(len(body))
