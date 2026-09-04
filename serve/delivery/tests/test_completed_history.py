from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery.acceptance import (
    CompletionDisplayMetadata,
    CompletionEvidence,
    CompletionPullRequestIdentity,
    CompletionReceipt,
    CompletionReceiptStore,
)
from owlbear_delivery.completed_history import (
    CompletedHistoryCatalog,
    CompletedHistoryDiagnosticCode,
    CompletedHistoryError,
    CompletedHistoryReceiptSetAdvancedError,
    LegacyCompletedChangeRecord,
    ReceiptCompletedChangeRecord,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryChangeAbandonment,
    DeliveryChangeStage,
    DeliveryFrontier,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    OutcomeAuthorityBinding,
)
from owlbear_delivery.design_package import CompletionPackageManifest, DesignPackageManifest
from owlbear_delivery.target_contract import (
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContract,
    DeliveryOutcome,
    DeliveryPlanScope,
)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        ("git", "-C", str(repository), *arguments),  # noqa: S607
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


def _task_result(
    result_id: str,
    change_id: str,
    authority_digest: str,
    task: DeliveryTaskDefinition,
    completed_commit: str,
) -> DeliveryTaskResult:
    observed_at = datetime(2026, 8, 11, 12, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=task.task_id,
            exact_commit=completed_commit,
            observation_kind="pytest",
            command_or_procedure="completed-history fixture validation",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=completed_commit,
            author_id="Completed history test author",
            reviewer_id="Completed history test reviewer",
            evidence=("The exact fixture commit satisfies task authority.",),
            reviewed_at=observed_at,
        )
    )
    return DeliveryTaskResult(
        result_id=result_id,
        change_id=change_id,
        authority_digest=authority_digest,
        task_id=task.task_id,
        task_digest=task.digest,
        completed_commit=completed_commit,
        observations=(observation,),
        review=review,
    )


def _capture_content(change_id: str, title: str, reviewed_head: str) -> dict[str, bytes]:
    intent = f"intent body sentinel {change_id}\n".encode()
    design = f"design body sentinel {change_id}\n".encode()
    contract = _contract(change_id, title, intent, design)
    authority = _canonical(contract)
    authority_digest = hashlib.sha256(authority).hexdigest()
    task = _task()
    result = _task_result(
        f"result-{change_id}",
        change_id,
        authority_digest,
        task,
        reviewed_head,
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
    legacy_root = root / ".owlbear/legacy"
    legacy_root.mkdir()
    (root / ".owlbear/completed").rename(legacy_root / "completed")
    _git(root, "add", "-A", ".owlbear/completed", ".owlbear/legacy/completed")
    _git(root, "commit", "-m", "move completed packages to legacy history")
    return root, {"baseline": baseline, "first": first, "second": second}


def _publish(repository: Path, change_id: str, title: str, reviewed_head: str) -> str:
    package_root = repository / ".owlbear/completed" / change_id
    package_root.mkdir(parents=True)
    for name, content in _capture_content(change_id, title, reviewed_head).items():
        (package_root / name).write_bytes(content)
    _git(repository, "add", str(package_root.relative_to(repository)))
    _git(repository, "commit", "-m", f"complete {change_id}")
    return _git(repository, "rev-parse", "HEAD")


def _receipt_digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _receipt_commit(value: str) -> str:
    return _receipt_digest(value)[:40]


def _publish_receipt(
    runtime_root: Path,
    change_id: str,
    title: str,
    *,
    pull_request_number: int,
) -> CompletionReceipt:
    merged_at = datetime(2026, 8, 11, 12, tzinfo=UTC)
    receipt = CompletionReceipt.create(
        CompletionEvidence(
            change_id=change_id,
            finalization_receipt_id=_receipt_digest(f"finalization:{change_id}"),
            finalized_change_head=_receipt_commit(f"finalized:{change_id}"),
            repository_identity="example/project",
            pull_request_identity=CompletionPullRequestIdentity(
                number=pull_request_number,
                node_id=f"PR_node_{pull_request_number}",
            ),
            accepted_target_ref="main",
            accepted_merge_commit=_receipt_commit(f"accepted:{change_id}"),
            merged_at=merged_at,
            acceptance_observation_id=_receipt_digest(f"acceptance:{change_id}"),
            check_observation_ids=(_receipt_digest(f"checks:{change_id}"),),
            review_receipt_ids=(_receipt_digest(f"review:{change_id}"),),
            completed_at=datetime(2026, 8, 11, 13, tzinfo=UTC),
        )
    )
    display = CompletionDisplayMetadata.create(
        change_id=change_id,
        completion_id=receipt.completion_id,
        title=title,
        outcome_titles=(f"Ship {title}",),
        outcome_promises=(f"Deliver the purpose of {title}.",),
    )
    store = CompletionReceiptStore(runtime_root)
    for participant in (store.participant(receipt), store.display_participant(display)):
        destination = participant.destination()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(participant.content)
    return receipt


def _stale_target_binding(path: Path) -> int:
    manifest = CompletionPackageManifest.model_validate_json(path.read_bytes())
    stale = manifest.model_copy(update={"integration_target": "other-target"})
    return path.write_bytes(stale.canonical_bytes())


def test_catalog_pages_searches_and_shows_verified_sibling_history(tmp_path: Path) -> None:
    repository, commits = _repository(tmp_path / "repository")
    catalog = CompletedHistoryCatalog(repository, "main", "main", tmp_path / "runtime")
    target_before = _git(repository, "rev-parse", "main")

    first_page = catalog.list(limit=1)
    second_page = catalog.list(cursor=first_page.next_cursor, limit=1)
    search = catalog.search("ship beta", limit=10)
    shown = catalog.show("change-b", search.records[0].completion_id)

    assert tuple(record.change_id for record in (*first_page.records, *second_page.records)) == (
        "change-a",
        "change-b",
    )
    assert first_page.total_count == second_page.total_count == 2
    assert first_page.next_cursor is not None
    assert second_page.next_cursor is None
    assert search.records == (shown,)
    assert search.total_count == 1
    assert isinstance(shown, LegacyCompletedChangeRecord)
    assert shown.semantic_summary == "Ship Beta search"
    assert shown.outcome_titles == ("Ship Beta search",)
    assert shown.outcome_promises == ("Return a verified semantic record.",)
    assert shown.introducing_target_commit == commits["second"]
    assert shown.source_target_commit == commits["first"]
    assert shown.completion_path == ".owlbear/legacy/completed/change-b"
    assert shown.historical_completion_locator == ".owlbear/completed/change-b"
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
    completion = repository / ".owlbear/legacy/completed/change-a/completion.json"
    corrupt(completion)
    _git(repository, "add", ".owlbear/legacy/completed/change-a")
    _git(repository, "commit", "-m", "corrupt completed history")
    target_before = _git(repository, "rev-parse", "main")

    with pytest.raises(CompletedHistoryError) as raised:
        CompletedHistoryCatalog(repository, "main", "main", tmp_path / "runtime").list()

    assert raised.value.diagnostic.code == expected
    assert _git(repository, "rev-parse", "main") == target_before


def test_catalog_reports_missing_and_stale_queries_without_mutating_target(tmp_path: Path) -> None:
    repository, _commits = _repository(tmp_path / "repository")
    catalog = CompletedHistoryCatalog(repository, "main", "main", tmp_path / "runtime")
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


def test_catalog_combines_legacy_and_receipt_history_without_false_graph_claims(tmp_path: Path) -> None:
    repository, _commits = _repository(tmp_path / "repository")
    runtime_root = tmp_path / "runtime"
    replacement = _publish_receipt(runtime_root, "change-b", "Beta accepted", pull_request_number=7)
    added = _publish_receipt(runtime_root, "change-c", "Gamma accepted", pull_request_number=8)
    catalog = CompletedHistoryCatalog(repository, "main", "main", runtime_root)

    page = catalog.list()
    search = catalog.search("beta accepted")
    shown = catalog.show("change-c", added.completion_id)

    assert tuple((record.change_id, record.record_kind) for record in page.records) == (
        ("change-a", "legacy-package"),
        ("change-b", "completion-receipt"),
        ("change-c", "completion-receipt"),
    )
    assert page.records[1].semantic_summary == "Ship Beta accepted"
    assert page.records[1].outcome_promises == ("Deliver the purpose of Beta accepted.",)
    assert search.records[0].completion_id == replacement.completion_id
    assert search.records[0].semantic_summary == "Ship Beta accepted"
    assert isinstance(shown, ReceiptCompletedChangeRecord)
    assert shown.finalized_change_head == added.finalized_change_head
    assert shown.accepted_merge_commit == added.accepted_merge_commit
    assert shown.finalized_change_head != shown.accepted_merge_commit
    projection = shown.model_dump(mode="json")
    assert "merge_method" not in projection
    assert "source_target_commit" not in projection
    assert "introducing_target_commit" not in projection
    assert "completion_path" not in projection


def test_catalog_reports_receipt_growth_separately_from_target_staleness(tmp_path: Path) -> None:
    repository, _commits = _repository(tmp_path / "repository")
    runtime_root = tmp_path / "runtime"
    catalog = CompletedHistoryCatalog(repository, "main", "main", runtime_root)
    cursor = catalog.list(limit=1).next_cursor
    assert cursor is not None
    _publish_receipt(runtime_root, "change-c", "Gamma accepted", pull_request_number=8)

    with pytest.raises(CompletedHistoryReceiptSetAdvancedError) as advanced:
        catalog.list(cursor=cursor, limit=1)

    assert advanced.value.diagnostic.code == CompletedHistoryDiagnosticCode.RECEIPT_SET_ADVANCED


def test_catalog_fails_closed_for_malformed_receipt_display_metadata(tmp_path: Path) -> None:
    repository, _commits = _repository(tmp_path / "repository")
    runtime_root = tmp_path / "runtime"
    _publish_receipt(runtime_root, "change-c", "Gamma accepted", pull_request_number=8)
    (runtime_root / "completions/change-c/display.json").write_bytes(b"not-json\n")

    with pytest.raises(CompletedHistoryError) as malformed:
        CompletedHistoryCatalog(repository, "main", "main", runtime_root).list()

    assert malformed.value.diagnostic.code == CompletedHistoryDiagnosticCode.MALFORMED


def test_catalog_ignores_stray_runtime_entries_but_rejects_recognized_corruption(tmp_path: Path) -> None:
    repository, _commits = _repository(tmp_path / "repository")
    runtime_root = tmp_path / "runtime"
    changes_root = runtime_root / "changes"
    changes_root.mkdir(parents=True)
    (changes_root / "README.txt").write_text("unrelated runtime note\n", encoding="utf-8")
    (changes_root / "not_a_change").mkdir()
    (changes_root / "not_a_change" / "frontier.json").write_text("not a Change\n", encoding="utf-8")
    (changes_root / "stray-link").symlink_to(changes_root / "README.txt")

    abandoned_id = "abandoned-change"
    abandoned_root = changes_root / abandoned_id
    abandoned_root.mkdir()
    contract = _contract(abandoned_id, "Abandoned delivery", b"intent", b"design")
    abandonment = DeliveryChangeAbandonment.create(
        change_id=abandoned_id,
        prior_stage=DeliveryChangeStage.BUILDING,
        abandoned_at=datetime(2026, 8, 11, 14, tzinfo=UTC),
        reason="User stopped the Change.",
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.IMPLEMENTATION,
            ),
        ),
        change_abandonment=abandonment,
    )
    (abandoned_root / "contract.json").write_bytes(_canonical(contract))
    (abandoned_root / "frontier.json").write_bytes(_canonical(frontier))

    catalog = CompletedHistoryCatalog(repository, "main", "main", runtime_root)
    page = catalog.list()

    assert tuple(record.change_id for record in page.records) == (abandoned_id, "change-a", "change-b")
    assert page.records[0].record_kind == "abandoned-change"

    corrupt_root = changes_root / "recognized-corruption"
    corrupt_root.mkdir()
    (corrupt_root / "frontier.json").write_text("not-json\n", encoding="utf-8")

    with pytest.raises(CompletedHistoryError) as malformed:
        catalog.list()

    assert malformed.value.diagnostic.code == CompletedHistoryDiagnosticCode.MALFORMED
    assert malformed.value.diagnostic.change_id == "recognized-corruption"
