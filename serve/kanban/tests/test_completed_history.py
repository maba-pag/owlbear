from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from owlbear_kanban.completed_history import (
    CompletedHistoryCatalog,
    CompletedHistoryDiagnosticCode,
    CompletedHistoryError,
)
from owlbear_kanban.delivery_runtime import (
    DeliveryFrontier,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    OutcomeAuthorityBinding,
)
from owlbear_kanban.design_package import CompletionPackageManifest, DesignPackageManifest
from owlbear_kanban.target_contract import (
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContract,
    DeliveryOutcome,
    DeliveryPlanScope,
)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _canonical(value: object) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return f"{json.dumps(value, sort_keys=True, separators=(',', ':'))}\n".encode()


def _contract(change_id: str, title: str, intent: bytes, design: bytes) -> DeliveryContract:
    return DeliveryContract(
        change_id=change_id,
        title=title,
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.AGREED_PATH,
                provenance="accepted design",
                statement="Keep completed history bounded.",
            ),
        ),
        outcomes=(
            DeliveryOutcome(
                outcome_id="OUT-001",
                title=f"Ship {title}",
                promise="Return a verified semantic record.",
                acceptance=("Completed history is queryable.",),
                commitment_ids=("COM-001",),
                dependency_ids=(),
            ),
        ),
        plan_scopes=(DeliveryPlanScope(scope_id="SCOPE-001", outcome_id="OUT-001"),),
        source_bindings=(
            {"source_name": "intent.md", "sha256": hashlib.sha256(intent).hexdigest()},
            {"source_name": "design.md", "sha256": hashlib.sha256(design).hexdigest()},
        ),
    )


def _capture_content(change_id: str, title: str, reviewed_head: str) -> dict[str, bytes]:
    intent = f"intent body sentinel {change_id}\n".encode()
    design = f"design body sentinel {change_id}\n".encode()
    contract = _contract(change_id, title, intent, design)
    authority = _canonical(contract)
    authority_digest = hashlib.sha256(authority).hexdigest()
    task = _task()
    result = DeliveryTaskResult(
        result_id=f"result-{change_id}",
        change_id=change_id,
        authority_digest=authority_digest,
        task_id=task.task_id,
        task_digest=task.digest,
        completed_commit=reviewed_head,
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.COMPLETED,
                tasks=(task,),
                results=(result,),
            ),
        )
    )
    authored = {"authority.json": authority, "design.md": design, "intent.md": intent}
    return _completion_files(change_id, authored, frontier, (result,), reviewed_head)


def _task() -> DeliveryTaskDefinition:
    return DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Build bounded history",
        result="A Git-backed semantic catalog.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Completed record",),
        maintained_surfaces=("completed_history.py",),
        constraints=("Do not expose bodies.",),
        exclusions=("No active package query.",),
        acceptance_observations=("History is bounded.",),
        proof_boundaries=("CompletedHistoryCatalog",),
    )


def _completion_files(
    change_id: str,
    authored: dict[str, bytes],
    frontier: DeliveryFrontier,
    results: tuple[DeliveryTaskResult, ...],
    reviewed_head: str,
) -> dict[str, bytes]:
    authority = authored["authority.json"]
    runtime = _canonical(frontier)
    result_history = _canonical([result.model_dump(mode="json") for result in results])
    package = DesignPackageManifest.from_content(
        change_id,
        authored["intent.md"],
        authored["design.md"],
        authority,
    )
    completion = CompletionPackageManifest(
        change_id=change_id,
        package_id=hashlib.sha256(package.canonical_bytes()).hexdigest(),
        authority_digest=hashlib.sha256(authority).hexdigest(),
        runtime_sha256=hashlib.sha256(runtime).hexdigest(),
        result_history_sha256=hashlib.sha256(result_history).hexdigest(),
        reviewed_change_head=reviewed_head,
        integration_target="main",
        completion_path=f".owlbear/completed/{change_id}",
    )
    return {
        **authored,
        "completion.json": completion.canonical_bytes(),
        "manifest.json": package.canonical_bytes(),
        "results.json": result_history,
        "runtime.json": runtime,
    }


def _repository(root: Path) -> tuple[Path, dict[str, str]]:
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Completed History Test")
    _git(root, "config", "user.email", "completed-history@example.invalid")
    (root / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(root, "add", "product.txt")
    _git(root, "commit", "-m", "baseline")
    baseline = _git(root, "rev-parse", "HEAD")
    first = _publish(root, "change-a", "Alpha delivery", baseline)
    second = _publish(root, "change-b", "Beta search", first)
    return root, {"baseline": baseline, "first": first, "second": second}


def _publish(repository: Path, change_id: str, title: str, reviewed_head: str) -> str:
    package_root = repository / ".owlbear/completed" / change_id
    package_root.mkdir(parents=True)
    for name, content in _capture_content(change_id, title, reviewed_head).items():
        (package_root / name).write_bytes(content)
    _git(repository, "add", str(package_root.relative_to(repository)))
    _git(repository, "commit", "-m", f"complete {change_id}")
    return _git(repository, "rev-parse", "HEAD")


def _stale_target_binding(path: Path) -> int:
    manifest = CompletionPackageManifest.model_validate_json(path.read_bytes())
    stale = manifest.model_copy(update={"integration_target": "other-target"})
    return path.write_bytes(stale.canonical_bytes())


def test_catalog_pages_searches_and_shows_verified_sibling_history(tmp_path: Path) -> None:
    repository, commits = _repository(tmp_path / "repository")
    catalog = CompletedHistoryCatalog(repository, "main")
    target_before = _git(repository, "rev-parse", "main")

    first_page = catalog.list(limit=1)
    second_page = catalog.list(cursor=first_page.next_cursor, limit=1)
    search = catalog.search("ship beta", limit=10)
    shown = catalog.show("change-b", search.records[0].completion_id)

    assert tuple(record.change_id for record in (*first_page.records, *second_page.records)) == (
        "change-a",
        "change-b",
    )
    assert first_page.next_cursor is not None
    assert second_page.next_cursor is None
    assert search.records == (shown,)
    assert shown.introducing_target_commit == commits["second"]
    assert shown.source_target_commit == commits["first"]
    assert shown.completion_path == ".owlbear/completed/change-b"
    projection = shown.model_dump_json()
    assert "intent body sentinel" not in projection
    assert "design body sentinel" not in projection
    assert _git(repository, "rev-parse", "main") == target_before


@pytest.mark.parametrize(
    ("corrupt", "expected"),
    [
        (lambda path: path.write_bytes(b"not-json\n"), CompletedHistoryDiagnosticCode.MALFORMED),
        (
            lambda path: path.with_name("intent.md").write_bytes(b"changed\n"),
            CompletedHistoryDiagnosticCode.DIGEST_MISMATCH,
        ),
        (_stale_target_binding, CompletedHistoryDiagnosticCode.STALE),
    ],
)
def test_catalog_reports_corrupt_history_without_mutating_target(
    tmp_path: Path,
    corrupt: Callable[[Path], object],
    expected: CompletedHistoryDiagnosticCode,
) -> None:
    repository, _commits = _repository(tmp_path / "repository")
    completion = repository / ".owlbear/completed/change-a/completion.json"
    corrupt(completion)
    _git(repository, "add", ".owlbear/completed/change-a")
    _git(repository, "commit", "-m", "corrupt completed history")
    target_before = _git(repository, "rev-parse", "main")

    with pytest.raises(CompletedHistoryError) as raised:
        CompletedHistoryCatalog(repository, "main").list()

    assert raised.value.diagnostic.code == expected
    assert _git(repository, "rev-parse", "main") == target_before


def test_catalog_reports_missing_and_stale_queries_without_mutating_target(tmp_path: Path) -> None:
    repository, _commits = _repository(tmp_path / "repository")
    catalog = CompletedHistoryCatalog(repository, "main")
    cursor = catalog.list(limit=1).next_cursor
    (repository / "product.txt").write_text("new target state\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "advance target")
    target_before = _git(repository, "rev-parse", "main")

    with pytest.raises(CompletedHistoryError) as missing:
        catalog.show("missing-change")
    with pytest.raises(CompletedHistoryError) as exact_missing:
        catalog.show("change-a", "0" * 64)
    with pytest.raises(CompletedHistoryError) as stale:
        catalog.list(cursor=cursor, limit=1)

    assert missing.value.diagnostic.code == CompletedHistoryDiagnosticCode.MISSING
    assert exact_missing.value.diagnostic.code == CompletedHistoryDiagnosticCode.MISSING
    assert stale.value.diagnostic.code == CompletedHistoryDiagnosticCode.STALE
    assert _git(repository, "rev-parse", "main") == target_before
