"""Bounded, noninteractive remote Git runner proofs against real local transports."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any

import pytest

from owlbear_delivery import remote_git
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.remote_git import (
    RemoteGitFailed,
    RemoteGitTimeout,
    RemoteGitWriteUnknown,
    classify_write_readback,
    read_remote_ref,
    remote_git_environment,
    run_remote_git,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_BOUND = 1.0
_SLACK = 4.0


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        (resolve_git_executable(), "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, Path, str]:
    bare = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(bare))
    repository = tmp_path / "repository"
    _git(tmp_path, "init", "-b", "main", str(repository))
    _git(repository, "config", "user.name", "Remote Git Test")
    _git(repository, "config", "user.email", "remote-git@example.invalid")
    (repository / "product.txt").write_text("base\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "base")
    _git(repository, "remote", "add", "origin", str(bare))
    _git(repository, "push", "origin", "HEAD:refs/heads/main")
    return repository, bare, _git(repository, "rev-parse", "HEAD")


def _commit(repository: Path, message: str) -> str:
    (repository / "product.txt").write_text(f"{message}\n", encoding="utf-8")
    _git(repository, "commit", "-am", message)
    return _git(repository, "rev-parse", "HEAD")


def _recording_script(path: Path, record: Path, body: str) -> Path:
    path.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" >> "{record}"\n{body}', encoding="utf-8")
    path.chmod(0o755)
    return path


def test_environment_disables_every_prompt_and_clears_repository_overrides() -> None:
    environment = remote_git_environment(
        {
            "PATH": "/bin",
            "GIT_DIR": "/elsewhere/.git",
            "GIT_WORK_TREE": "/elsewhere",
            "GIT_INDEX_FILE": "/elsewhere/index",
            "GIT_ASKPASS": "/usr/bin/askpass",
            "SSH_ASKPASS": "/usr/bin/ssh-askpass",
            "GIT_TERMINAL_PROMPT": "1",
        }
    )

    assert {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"}.isdisjoint(environment)
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert environment["GCM_INTERACTIVE"] == "never"
    assert environment["GIT_ASKPASS"] == ""
    assert environment["SSH_ASKPASS"] == ""
    assert environment["SSH_ASKPASS_REQUIRE"] == "never"
    assert environment["GIT_SSH_COMMAND"] == "ssh -o BatchMode=yes"
    assert environment["PATH"] == "/bin"


@pytest.mark.parametrize("variable", ["GIT_SSH_COMMAND", "GIT_SSH"])
def test_environment_keeps_a_user_ssh_command(variable: str) -> None:
    environment = remote_git_environment({variable: "custom-ssh"})

    assert environment[variable] == "custom-ssh"
    assert environment.get("GIT_SSH_COMMAND", "custom-ssh") == "custom-ssh"


def test_hung_read_raises_typed_timeout_within_bound_and_kills_the_transport(
    tmp_path: Path,
    ext_remote: Callable[[Path], Any],
) -> None:
    repository, bare, _base = _repository(tmp_path)
    transport = ext_remote(bare)
    transport.use(repository)
    transport.modes("upload-pack", "hang")

    started = time.monotonic()
    with pytest.raises(RemoteGitTimeout) as raised:
        run_remote_git(repository, ("fetch", "origin", "refs/heads/main"), kind="read", timeout=_BOUND)

    assert time.monotonic() - started < _BOUND + _SLACK
    assert raised.value.retry_safe
    assert len(transport.pids("upload-pack")) == 1
    transport.assert_exited("upload-pack")


def test_timeout_returns_even_when_a_detached_descendant_holds_the_output_pipes(
    tmp_path: Path,
    ext_remote: Callable[[Path], Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, bare, _base = _repository(tmp_path)
    transport = ext_remote(bare)
    transport.use(repository)
    transport.modes("upload-pack", "orphan")
    monkeypatch.setattr(remote_git, "REAP_TIMEOUT_SECONDS", 0.5)

    started = time.monotonic()
    try:
        with pytest.raises(RemoteGitTimeout):
            run_remote_git(repository, ("ls-remote", "origin"), kind="read", timeout=_BOUND)
        assert time.monotonic() - started < _BOUND + 0.5 + _SLACK
    finally:
        for pid in transport.pids("upload-pack"):
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)


def test_hung_write_is_unknown_never_retried_and_kills_the_transport(
    tmp_path: Path,
    ext_remote: Callable[[Path], Any],
) -> None:
    repository, bare, base = _repository(tmp_path)
    transport = ext_remote(bare)
    transport.use(repository)
    transport.modes("receive-pack", "hang")
    advanced = _commit(repository, "advanced")

    started = time.monotonic()
    with pytest.raises(RemoteGitWriteUnknown) as raised:
        run_remote_git(repository, ("push", "origin", "HEAD:refs/heads/main"), kind="write", timeout=_BOUND)

    assert time.monotonic() - started < _BOUND + _SLACK
    assert raised.value.timed_out
    assert not raised.value.retry_safe
    assert len(transport.pids("receive-pack")) == 1
    transport.assert_exited("receive-pack")
    observed = read_remote_ref(repository, "origin", "refs/heads/main", timeout=10)
    assert classify_write_readback(observed, intended=advanced, expected_old=base) == "not-applied"


def test_rejected_write_is_unknown_and_keeps_its_result_for_classification(tmp_path: Path) -> None:
    repository, bare, base = _repository(tmp_path)
    hook = bare / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\ncat >/dev/null\necho declined >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    advanced = _commit(repository, "advanced")

    with pytest.raises(RemoteGitWriteUnknown) as raised:
        run_remote_git(repository, ("push", "origin", "HEAD:refs/heads/main"), kind="write", timeout=30)

    assert not raised.value.timed_out
    assert raised.value.result is not None
    assert raised.value.result.returncode != 0
    assert b"declined" in raised.value.result.stderr
    observed = read_remote_ref(repository, "origin", "refs/heads/main", timeout=10)
    assert classify_write_readback(observed, intended=advanced, expected_old=base) == "not-applied"


def test_read_returns_nonzero_exit_and_ref_reader_distinguishes_absent_refs(tmp_path: Path) -> None:
    repository, _bare, base = _repository(tmp_path)

    missing = run_remote_git(repository, ("ls-remote", "--exit-code", "origin", "refs/heads/absent"), kind="read")

    assert missing.returncode == 2
    assert read_remote_ref(repository, "origin", "refs/heads/main") == base
    assert read_remote_ref(repository, "origin", "refs/heads/absent") is None


def test_unavailable_git_is_a_typed_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(remote_git, "resolve_git_executable", lambda: str(tmp_path / "missing-git"))

    with pytest.raises(RemoteGitFailed) as raised:
        run_remote_git(tmp_path, ("ls-remote", "origin"), kind="read")

    assert not raised.value.retry_safe


class _Unauthorized(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="owlbear"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *_arguments: object) -> None:
        return


def test_prompt_requiring_remote_fails_instead_of_waiting_for_any_prompt(tmp_path: Path) -> None:
    repository, _bare, _base = _repository(tmp_path)
    record = tmp_path / "askpass.log"
    askpass = _recording_script(tmp_path / "askpass", record, "sleep 30\necho secret\n")
    _git(repository, "config", "core.askPass", str(askpass))
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Unauthorized)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        _git(repository, "remote", "set-url", "origin", f"http://127.0.0.1:{server.server_address[1]}/repo.git")
        environment = {
            **os.environ,
            "GIT_ASKPASS": str(askpass),
            "SSH_ASKPASS": str(askpass),
            "NO_PROXY": "127.0.0.1",
            "no_proxy": "127.0.0.1",
        }
        started = time.monotonic()
        result = run_remote_git(repository, ("ls-remote", "origin"), kind="read", timeout=20, environment=environment)
        elapsed = time.monotonic() - started
    finally:
        server.shutdown()
        server.server_close()

    assert result.returncode != 0
    assert b"terminal prompts disabled" in result.stderr
    assert elapsed < _SLACK
    assert not record.exists()


def test_ssh_remote_runs_in_batch_mode_unless_the_user_chose_a_command(tmp_path: Path) -> None:
    repository, _bare, _base = _repository(tmp_path)
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    record = tmp_path / "ssh.log"
    fake_ssh = _recording_script(bin_directory / "ssh", record, "exit 255\n")
    _git(repository, "remote", "set-url", "origin", "ssh://git@example.invalid/repo.git")
    environment = {key: value for key, value in os.environ.items() if key not in {"GIT_SSH", "GIT_SSH_COMMAND"}}
    environment["PATH"] = f"{bin_directory}{os.pathsep}{environment.get('PATH', '')}"

    default = run_remote_git(repository, ("ls-remote", "origin"), kind="read", timeout=20, environment=environment)
    default_arguments = record.read_text(encoding="utf-8").splitlines()
    record.unlink()
    custom = run_remote_git(
        repository,
        ("ls-remote", "origin"),
        kind="read",
        timeout=20,
        environment={**environment, "GIT_SSH_COMMAND": f"{fake_ssh} -o UserChosen=yes"},
    )
    custom_arguments = record.read_text(encoding="utf-8").splitlines()

    assert default.returncode != 0
    assert "BatchMode=yes" in default_arguments
    assert custom.returncode != 0
    assert "UserChosen=yes" in custom_arguments
    assert "BatchMode=yes" not in custom_arguments


@pytest.mark.parametrize(
    ("observed", "expected"),
    [("a" * 40, "applied"), ("b" * 40, "not-applied"), (None, "conflict"), ("c" * 40, "conflict")],
)
def test_write_readback_classification(observed: str | None, expected: str) -> None:
    assert classify_write_readback(observed, intended="a" * 40, expected_old="b" * 40) == expected


def test_write_readback_treats_absent_ref_as_unchanged_when_it_was_absent() -> None:
    assert classify_write_readback(None, intended="a" * 40, expected_old=None) == "not-applied"
