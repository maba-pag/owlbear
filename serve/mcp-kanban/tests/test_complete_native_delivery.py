"""Assembled PROOF-013 fresh-consumer native delivery workflow."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from owlbear_kanban import JobStore
from owlbear_mcp_kanban import server

from .test_mcp_acceptance_tools import _active_accept, _identity, _rejection_payload, _start

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIVE_CARRIER = _REPO_ROOT / ".owlbear" / "kanban"


def _run(repository: Path, *command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        command,
        cwd=repository,
        check=True,
        text=True,
        capture_output=True,
    )


def _git(repository: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    assert executable is not None
    return _run(repository, executable, *arguments).stdout.strip()


async def _complete_corrective_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[object, object, str]:
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _git(consumer, "init", "--initial-branch=main")
    _git(consumer, "config", "user.name", "PROOF-013")
    _git(consumer, "config", "user.email", "proof-013@example.invalid")

    setup = _run(consumer, sys.executable, str(_REPO_ROOT / "setup" / "init.py"))

    work_root = consumer / ".owlbear" / "kanban"
    change_root = consumer / ".owlbear" / "changes"
    assert "OwlBear workspace initialised" in setup.stdout
    assert work_root.is_dir()
    assert change_root.is_dir()
    assert consumer.is_relative_to(tmp_path)
    assert not work_root.is_relative_to(_LIVE_CARRIER)
    assert not change_root.is_relative_to(_REPO_ROOT / ".owlbear" / "changes")
    assert not (consumer / ".owlbear" / "legacy").exists()

    shutil.copytree(
        _REPO_ROOT / ".owlbear" / "changes" / "replace-delivery-pipeline",
        change_root / "replace-delivery-pipeline",
    )
    _git(consumer, "add", ".")
    _git(consumer, "commit", "-m", "fixture: initialize disposable consumer")
    monkeypatch.chdir(consumer)

    runtime_root = tmp_path / "runtime"
    revision, board, context, _runtime, checkout, accept_start, base_commit = await _active_accept(runtime_root)
    rejected = await server.reject_accept(
        context,
        **_rejection_payload(revision, accept_start, base_commit),
    )
    assert rejected.diagnostic is None
    assert not checkout.root.exists()
    assert rejected.invalidation is not None
    assert tuple(job.job.kind for job in rejected.invalidation.corrective_jobs) == ("build",)
    assert rejected.replacement_accept is not None
    assert rejected.replacement_accept.job.predecessor_job_ids == (20,)

    (consumer / "README.md").write_text("# Corrected disposable consumer\n", encoding="utf-8")
    _git(consumer, "add", "README.md")
    _git(consumer, "commit", "-m", "fix: correct disposable implementation")
    corrected_commit = _git(consumer, "rev-parse", "HEAD")
    corrective_job = rejected.invalidation.corrective_jobs[0].job
    corrective_start = _start(corrective_job.job_id, 5, corrected_commit)
    started = await server.start_job(context, **corrective_start)
    assert started.diagnostic is None
    target = revision.resolve(corrective_job.target_node_id)
    proof = revision.resolve(target.proof)
    closure = {"paths": ["serve/kanban/"], "authority_targets": [target.id, target.proof]}
    corrected = await server.finish_build(
        context,
        **_identity(corrective_start),
        finished_at="2026-07-25T00:08:00Z",
        receipt_id="build-corrected",
        code_revision=corrected_commit,
        evidence={"methods": list(proof.method)},
        evidence_ids=("proof-corrected",),
        impact_closure=closure,
    )

    assert corrected.diagnostic is None
    assert corrected.receipt is not None
    assert corrected.receipt.receipt_id == "build-corrected"
    assert corrected.receipt.payload["node_plan_digest"] == corrective_job.node_plan_digest
    assert (revision.source_dir / "receipts" / "build-corrected.yaml").is_file()
    assert JobStore(board).read(corrective_job.job_id, archived=True).job.receipt_id == "build-corrected"
    return revision, context, corrected_commit


@pytest.mark.asyncio
async def test_fresh_consumer_completes_corrective_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _complete_corrective_build(tmp_path, monkeypatch)


@pytest.mark.asyncio
async def test_fresh_consumer_resumes_replacement_acceptance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision, context, corrected_commit = await _complete_corrective_build(tmp_path, monkeypatch)

    resumed = await server.pick_jobs(
        context,
        change_id=revision.change_id,
        candidate_revision=corrected_commit,
        wave_size=2,
    )
    selected = [entry for wave in resumed.waves for entry in wave]
    assert [(entry.job_id, entry.agent_profile, entry.predecessor_job_ids) for entry in selected] == [
        (21, "acceptor", (20,))
    ]
    replacement_start = _start(21, 6, corrected_commit)
    started = await server.start_job(context, **replacement_start)
    assert started["start"].diagnostic is None
    assert started["checkout"].commit == corrected_commit
