from __future__ import annotations

import multiprocessing
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from owlbear_memory import MemoryCategory, MemoryEngine, MemoryEntry

from owlbear_memory_mcp.git import commit_batch, format_git_failure


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_bytes(repository: Path, *args: str) -> bytes:
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repository,
        check=True,
        capture_output=True,
    )
    return result.stdout


def _blob_id(repository: Path, raw: bytes) -> str:
    result = subprocess.run(
        ["git", "hash-object", "--stdin"],  # noqa: S607
        cwd=repository,
        check=True,
        capture_output=True,
        input=raw,
    )
    return result.stdout.decode("ascii").strip()


def _init_repository(repository: Path) -> tuple[Path, MemoryEngine, MemoryEntry]:
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "OwlBear Test")
    _git(repository, "config", "user.email", "test@example.invalid")
    memory_dir = repository / ".owlbear/memory"
    memory_dir.mkdir(parents=True)

    engine = MemoryEngine(memory_dir)
    pending = engine.save(
        title="Batch entry",
        content="Initial memory content.",
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        source_agent="test-agent",
        scope_agents=[],
    )
    curated = engine.edit(pending.id, {"scope_agents": ["test-agent"]}, expected_updated_at=pending.updated_at)
    approved = engine.approve(curated.id, expected_updated_at=curated.updated_at)
    relative_path = f".owlbear/memory/{approved.id}.md"
    _git(repository, "add", "--", relative_path)
    _git(repository, "commit", "-m", "initial memory")
    return memory_dir, engine, approved


def _write_waiting_hook(
    repository: Path,
    signal_path: Path,
    release_path: Path,
    *,
    exit_code: int = 0,
    stderr_line: str | None = None,
) -> None:
    hook = repository / ".git/hooks/pre-commit"
    hook.write_text(
        f"#!{sys.executable}\n"
        "from pathlib import Path\n"
        "import sys\n"
        "import time\n"
        f"signal_path = Path({str(signal_path)!r})\n"
        f"release_path = Path({str(release_path)!r})\n"
        "signal_path.write_text('ready', encoding='utf-8')\n"
        "deadline = time.monotonic() + 15\n"
        "while not release_path.exists():\n"
        "    if time.monotonic() >= deadline:\n"
        "        sys.exit(96)\n"
        "    time.sleep(0.01)\n"
        f"if {stderr_line!r}:\n"
        f"    sys.stderr.write({stderr_line!r} + '\\n')\n"
        f"sys.exit({exit_code})\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)


def _write_rewriting_hook(repository: Path, relative_path: str) -> None:
    hook = repository / ".git/hooks/pre-commit"
    hook.write_text(
        f"#!{sys.executable}\n"
        "from pathlib import Path\n"
        "import subprocess\n"
        f"target = Path({relative_path!r})\n"
        "raw = target.read_bytes()\n"
        "target.write_bytes(raw.replace(b'Validated batch content.', b'Hook replacement content.', 1))\n"
        f"subprocess.run(['git', 'add', '--', {relative_path!r}], check=True)\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)


def _write_add_all_hook(repository: Path) -> None:
    hook = repository / ".git/hooks/pre-commit"
    hook.write_text(
        f"#!{sys.executable}\nimport subprocess\nsubprocess.run(['git', 'add', '-A'], check=True)\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)


def _commit_worker(memory_dir: str, results: Any) -> None:
    engine = MemoryEngine(memory_dir)
    engine.get_entries()
    try:
        result = commit_batch(Path(memory_dir), session_type="curation")
    except subprocess.CalledProcessError as error:
        results.put(("git-error", error.returncode, format_git_failure(error)))
    except ValueError as error:
        results.put(("error", type(error).__name__, str(error)))
    else:
        results.put(("committed", result.commit_sha, result.deferred_deletions))


def _edit_worker(
    memory_dir: str,
    edit: tuple[str, str],
    started: Any,
    finished: Any,
    results: Any,
) -> None:
    entry_id, expected_updated_at = edit
    engine = MemoryEngine(memory_dir)
    started.set()
    try:
        updated = engine.edit(
            entry_id,
            {"content": "Concurrent writer content."},
            expected_updated_at=expected_updated_at,
        )
        results.put(("edited", updated.content))
    finally:
        finished.set()


def _wait_for_file(path: Path, timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert path.exists(), f"timed out waiting for {path.name}"


def _join_processes(processes: list[multiprocessing.Process]) -> None:
    for process in processes:
        process.join(timeout=20)
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join()
    assert all(process.exitcode == 0 for process in processes)


def test_commit_batch_holds_writer_lock_through_precommit_hook(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    memory_dir, engine, entry = _init_repository(tmp_path)
    updated = engine.edit(
        entry.id,
        {"content": "Validated batch content."},
        expected_updated_at=entry.updated_at,
    )
    relative_path = f".owlbear/memory/{entry.id}.md"
    memory_path = memory_dir / f"{entry.id}.md"
    validated_bytes = memory_path.read_bytes()
    initial_head = _git(tmp_path, "rev-parse", "HEAD")
    hook_ready = tmp_path / "hook-ready"
    hook_release = tmp_path / "hook-release"
    _write_waiting_hook(tmp_path, hook_ready, hook_release)

    results = context.Queue()
    writer_started = context.Event()
    writer_finished = context.Event()
    commit_process = context.Process(target=_commit_worker, args=(str(memory_dir), results))
    writer_process = context.Process(
        target=_edit_worker,
        args=(str(memory_dir), (entry.id, updated.updated_at), writer_started, writer_finished, results),
    )
    processes: list[multiprocessing.Process] = []

    try:
        commit_process.start()
        processes.append(commit_process)
        _wait_for_file(hook_ready)
        assert memory_path.read_bytes() == validated_bytes

        writer_process.start()
        processes.append(writer_process)
        assert writer_started.wait(timeout=5)
        assert not writer_finished.wait(timeout=0.25)
        assert memory_path.read_bytes() == validated_bytes

        hook_release.touch()
        _join_processes(processes)
        outcomes = [results.get(timeout=5) for _ in processes]
    finally:
        hook_release.touch()
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join()
        results.close()
        results.join_thread()

    committed = next(outcome for outcome in outcomes if outcome[0] == "committed")
    edited = next(outcome for outcome in outcomes if outcome[0] == "edited")
    assert committed[1] is not None
    assert committed[0] == "committed"
    assert edited[1] == "Concurrent writer content."
    assert _git(tmp_path, "rev-parse", "HEAD") != initial_head
    assert _git_bytes(tmp_path, "show", f"{committed[1]}:{relative_path}") == validated_bytes
    assert memory_path.read_bytes() != validated_bytes
    assert MemoryEngine(memory_dir).get_entry(entry.id).content == "Concurrent writer content."


def test_failing_precommit_hook_releases_writer_lock_and_preserves_diagnostics(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    memory_dir, engine, entry = _init_repository(tmp_path)
    updated = engine.edit(
        entry.id,
        {"content": "Validated batch content."},
        expected_updated_at=entry.updated_at,
    )
    relative_path = f".owlbear/memory/{entry.id}.md"
    initial_head = _git(tmp_path, "rev-parse", "HEAD")
    hook_ready = tmp_path / "hook-ready"
    hook_release = tmp_path / "hook-release"
    _write_waiting_hook(
        tmp_path,
        hook_ready,
        hook_release,
        exit_code=1,
        stderr_line="HOOKFAIL: batch rejected",
    )

    results = context.Queue()
    commit_process = context.Process(target=_commit_worker, args=(str(memory_dir), results))
    commit_process.start()
    try:
        _wait_for_file(hook_ready)
        hook_release.touch()
        _join_processes([commit_process])
        failure = results.get(timeout=5)
    finally:
        hook_release.touch()
        if commit_process.is_alive():
            commit_process.terminate()
            commit_process.join()

    assert failure[0] == "git-error"
    assert failure[1] == 1
    assert "captured command output" in failure[2]
    assert "<<<" in failure[2]
    assert ">>>" in failure[2]
    assert "HOOKFAIL: batch rejected" in failure[2]
    assert _git(tmp_path, "rev-parse", "HEAD") == initial_head
    assert _git(tmp_path, "diff", "--cached", "--name-only") == relative_path

    edit_results = context.Queue()
    edit_started = context.Event()
    edit_finished = context.Event()
    edit_process = context.Process(
        target=_edit_worker,
        args=(str(memory_dir), (entry.id, updated.updated_at), edit_started, edit_finished, edit_results),
    )
    edit_process.start()
    try:
        _join_processes([edit_process])
        edited = edit_results.get(timeout=5)
    finally:
        if edit_process.is_alive():
            edit_process.terminate()
            edit_process.join()
        results.close()
        results.join_thread()
        edit_results.close()
        edit_results.join_thread()

    assert edited == ("edited", "Concurrent writer content.")
    assert edit_started.is_set()
    assert edit_finished.is_set()


def test_rewriting_hook_cannot_commit_unvalidated_memory_bytes(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    memory_dir, engine, entry = _init_repository(tmp_path)
    engine.edit(
        entry.id,
        {"content": "Validated batch content."},
        expected_updated_at=entry.updated_at,
    )
    relative_path = f".owlbear/memory/{entry.id}.md"
    validated_bytes = (memory_dir / f"{entry.id}.md").read_bytes()
    initial_head = _git(tmp_path, "rev-parse", "HEAD")
    _write_rewriting_hook(tmp_path, relative_path)

    results = context.Queue()
    process = context.Process(target=_commit_worker, args=(str(memory_dir), results))
    process.start()
    try:
        _join_processes([process])
        outcome = results.get(timeout=5)
    finally:
        if process.is_alive():
            process.terminate()
            process.join()
        results.close()
        results.join_thread()

    assert outcome[:2] == ("error", "ValueError")
    assert "HEAD contains unvalidated changes" in outcome[2]
    assert relative_path in outcome[2]
    new_head = _git(tmp_path, "rev-parse", "HEAD")
    committed_bytes = _git_bytes(tmp_path, "show", f"{new_head}:{relative_path}")
    assert new_head != initial_head
    assert committed_bytes != validated_bytes
    assert b"Hook replacement content." in committed_bytes
    assert _git(tmp_path, "rev-parse", f":{relative_path}") == _blob_id(tmp_path, validated_bytes)


def test_add_all_hook_cannot_commit_unrelated_or_pending_paths(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    memory_dir, engine, entry = _init_repository(tmp_path)
    engine.edit(
        entry.id,
        {"content": "Validated batch content."},
        expected_updated_at=entry.updated_at,
    )
    pending = engine.save(
        title="Pending batch entry",
        content="Must remain pending.",
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        source_agent="test-agent",
        scope_agents=[],
    )
    pending_relative = f".owlbear/memory/{pending.id}.md"
    (tmp_path / "notes.txt").write_text("Unrelated hook addition.\n", encoding="utf-8")
    initial_head = _git(tmp_path, "rev-parse", "HEAD")
    _write_add_all_hook(tmp_path)

    results = context.Queue()
    process = context.Process(target=_commit_worker, args=(str(memory_dir), results))
    process.start()
    try:
        _join_processes([process])
        outcome = results.get(timeout=5)
    finally:
        if process.is_alive():
            process.terminate()
            process.join()
        results.close()
        results.join_thread()

    assert outcome[:2] == ("error", "ValueError")
    assert "HEAD contains unvalidated changes" in outcome[2]
    assert "notes.txt" in outcome[2]
    assert pending_relative in outcome[2]
    new_head = _git(tmp_path, "rev-parse", "HEAD")
    assert new_head != initial_head
    assert "notes.txt" in _git(tmp_path, "ls-tree", "-r", "--name-only", "HEAD")
    assert pending_relative in _git(tmp_path, "ls-tree", "-r", "--name-only", "HEAD")
