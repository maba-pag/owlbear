"""#921: a failed command's whole text keeps its type, its message and both streams it printed."""

import subprocess

import pytest

from owlbear_delivery_next.git.command_failure import failed, failure

OUT = "OUT begins\nthe command's own answer, in the middle\nOUT ends"


@pytest.mark.parametrize("as_bytes", [False, True])
def test_a_failed_command_says_both_streams_whole(whole_error, as_bytes):
    stderr, stdout = (whole_error.encode(), OUT.encode()) if as_bytes else (whole_error, OUT)
    exc = subprocess.CalledProcessError(1, ["git", "push"], stdout, stderr)
    assert failure(exc) == f"CalledProcessError: {exc}\nstderr:\n{whole_error}\nstdout:\n{OUT}"


def test_a_timed_out_command_says_what_it_printed_before_it_was_stopped(whole_error):
    exc = subprocess.TimeoutExpired(["gh", "api"], 30, output=OUT.encode(), stderr=whole_error.encode())
    assert failure(exc) == f"TimeoutExpired: {exc}\nstderr:\n{whole_error}\nstdout:\n{OUT}"


def test_a_command_that_exited_without_raising_reads_as_any_failed_command(whole_error):
    done = subprocess.CompletedProcess(["uv", "sync"], 2, OUT, whole_error)
    exc = subprocess.CalledProcessError(2, ["uv", "sync"])
    assert failed(done) == f"CalledProcessError: {exc}\nstderr:\n{whole_error}\nstdout:\n{OUT}"
