"""Behavioral coverage for receipt-gated target cutover."""

from __future__ import annotations

from pathlib import Path
from threading import Event, Thread

import pytest

from owlbear_kanban.snapshot import LegacyDisposition
from owlbear_kanban.snapshot import inventory_legacy_source
from owlbear_kanban.target_authority import Commitment, CommitmentClass, Outcome, TargetAuthority
from owlbear_kanban.target_cutover import (
    TargetAdapterRef,
    TargetCutoverClassification,
    TargetCutoverPublicationError,
    TargetCutoverReadiness,
    TargetCutoverReadinessError,
    TargetCutoverRequest,
    TargetCutoverSource,
    TargetCutoverSubjectKind,
    TargetMutationAuthority,
    TargetMutationGateError,
    authorize_target_mutation,
    cut_over_target_runtime,
    query_target_snapshot,
    target_authority_digest,
    validate_target_cutover_readiness,
)

_DIGEST = "a" * 64


def _authority() -> TargetAuthority:
    commitments = tuple(
        Commitment(
            commitment_id=f"COM-{index:03d}",
            commitment_class=commitment_class,
            provenance="accepted design",
            statement=f"Commitment {index}",
        )
        for index, commitment_class in enumerate(
            (
                CommitmentClass.DEALBREAKER,
                CommitmentClass.PROTECTED_REQUEST,
                CommitmentClass.IMPORTANT_REVIEWED,
            ),
            start=1,
        )
    )
    return TargetAuthority(
        change_id="change-one",
        title="Change one",
        commitments=commitments,
        outcomes=(
            Outcome(
                outcome_id="OUT-001",
                title="Outcome",
                promise="Deliver outcome",
                acceptance=("Outcome is visible",),
                commitment_ids=tuple(item.commitment_id for item in commitments),
            ),
        ),
    )


def _classifications(authority: TargetAuthority) -> tuple[TargetCutoverClassification, ...]:
    subjects = (
        (TargetCutoverSubjectKind.CHANGE, authority.change_id),
        (TargetCutoverSubjectKind.OUTCOME, "OUT-001"),
        *((TargetCutoverSubjectKind.COMMITMENT, item.commitment_id) for item in authority.commitments),
    )
    return tuple(
        TargetCutoverClassification(
            change_id=authority.change_id,
            subject_kind=kind,
            subject_id=identity,
            disposition=LegacyDisposition.REINTRODUCE_NATIVE,
        )
        for kind, identity in subjects
    )


def _request(*, readiness: TargetCutoverReadiness | None = None) -> TargetCutoverRequest:
    authority = _authority()
    return TargetCutoverRequest(
        sources=(
            TargetCutoverSource(source_path=".owlbear/kanban", snapshot_name="runtime", expected_source_digest=_DIGEST),
        ),
        snapshot_path=".owlbear/legacy/target-cutover",
        target_path=".owlbear/target",
        receipt_path=".owlbear/target-cutover.json",
        adapter_refs=(TargetAdapterRef(relative_path=".owlbear/adapters/delivery", target="target"),),
        authorities=(authority,),
        classifications=_classifications(authority),
        expected_authority_digest=target_authority_digest((authority,)),
        actual_code_revision=_DIGEST,
        expected_code_revision=_DIGEST,
        readiness=readiness or TargetCutoverReadiness(),
        approval="ACTIVATE_TARGET_RUNTIME",
    )


def _workspace_request(tmp_path: Path) -> tuple[TargetCutoverRequest, Path, Path]:
    source = tmp_path / ".owlbear/kanban"
    (source / "jobs").mkdir(parents=True)
    (source / "jobs/1-plan.md").write_text("current-schema job\n", encoding="utf-8")
    (source / "receipts").mkdir()
    (source / "receipts/proof.yaml").write_text("accepted: true\n", encoding="utf-8")
    adapter = tmp_path / ".owlbear/adapters/delivery"
    adapter.parent.mkdir(parents=True)
    adapter.write_bytes(b"bootstrap\n")
    digest = inventory_legacy_source(source, (), {}).source_digest
    specification = TargetCutoverSource(
        source_path=".owlbear/kanban",
        snapshot_name="runtime",
        expected_source_digest=digest,
    )
    return _request().model_copy(update={"sources": (specification,)}), source, adapter


def _source_files(source: Path) -> dict[str, bytes]:
    return {str(path.relative_to(source)): path.read_bytes() for path in sorted(source.rglob("*")) if path.is_file()}


def _smoke(_workspace_root: Path, _request: TargetCutoverRequest) -> None:
    pass


@pytest.mark.parametrize(
    ("mutation", "code", "identity"),
    [
        ("classification", "ERR_TARGET_CUTOVER_UNCLASSIFIED", "change-one:commitment:COM-001"),
        ("request", "ERR_TARGET_CUTOVER_CURRENT_REQUEST", "request-one"),
        ("claim", "ERR_TARGET_CUTOVER_ACTIVE_CLAIM", "claim-one"),
        ("writer", "ERR_TARGET_CUTOVER_ACTIVE_WRITER", "writer-one"),
        ("authority", "ERR_TARGET_CUTOVER_AUTHORITY_STALE", None),
        ("code", "ERR_TARGET_CUTOVER_CODE_STALE", "b" * 64),
    ],
)
def test_readiness_names_blocker_before_mutation(
    tmp_path: Path,
    mutation: str,
    code: str,
    identity: str | None,
) -> None:
    request = _request()
    if mutation == "classification":
        classifications = tuple(item for item in request.classifications if item.subject_id != "COM-001")
        request = request.model_copy(update={"classifications": classifications})
    elif mutation == "request":
        request = request.model_copy(update={"readiness": TargetCutoverReadiness(current_request_ids=("request-one",))})
    elif mutation == "claim":
        request = request.model_copy(update={"readiness": TargetCutoverReadiness(active_claim_ids=("claim-one",))})
    elif mutation == "writer":
        request = request.model_copy(update={"readiness": TargetCutoverReadiness(active_writer_ids=("writer-one",))})
    elif mutation == "authority":
        request = request.model_copy(update={"expected_authority_digest": "b" * 64})
        identity = target_authority_digest(request.authorities)
    else:
        request = request.model_copy(update={"actual_code_revision": "b" * 64})

    with pytest.raises(TargetCutoverReadinessError) as raised:
        validate_target_cutover_readiness(request)

    assert raised.value.code == code
    assert raised.value.blocking_identity == identity
    assert not (tmp_path / ".owlbear").exists()


def test_cutover_publishes_gate_and_retains_queryable_snapshot(tmp_path: Path) -> None:
    request, source, adapter = _workspace_request(tmp_path)
    smoke_calls: list[Path] = []

    def smoke(workspace_root: Path, _request: TargetCutoverRequest) -> None:
        smoke_calls.append(workspace_root)

    result = cut_over_target_runtime(tmp_path, request, smoke=smoke)
    replay = cut_over_target_runtime(tmp_path, request, smoke=smoke)
    authority = authorize_target_mutation(tmp_path, request)
    snapshot = query_target_snapshot(tmp_path, request, "runtime")

    assert result.replayed is False
    assert replay.replayed is True
    assert replay.receipt == result.receipt
    assert authority.authorities == request.authorities
    assert authority.receipt == result.receipt
    assert smoke_calls == [tmp_path.resolve()]
    assert not source.exists()
    assert adapter.read_bytes() == b"target\n"
    assert snapshot.manifest.source_digest == request.sources[0].expected_source_digest
    preserved_job = snapshot.destination / "content/jobs/1-plan.md"
    assert preserved_job.read_text(encoding="utf-8") == "current-schema job\n"


@pytest.mark.parametrize(
    "interruption_stage",
    [
        "snapshot",
        "initialization",
        "adapter-staging",
        "smoke-verification",
        "receipt-publication",
        "receipt-publication-linked",
    ],
)
def test_cutover_rolls_back_every_pre_receipt_interruption(
    tmp_path: Path,
    interruption_stage: str,
) -> None:
    request, source, adapter = _workspace_request(tmp_path)
    source_before = _source_files(source)

    def interrupt(stage: str, _path: Path) -> None:
        if stage == interruption_stage:
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(TargetCutoverPublicationError):
        cut_over_target_runtime(tmp_path, request, smoke=_smoke, failure=interrupt)

    assert _source_files(source) == source_before
    assert adapter.read_bytes() == b"bootstrap\n"
    assert not (tmp_path / request.target_path).exists()
    assert not (tmp_path / request.snapshot_path).exists()
    assert not (tmp_path / request.receipt_path).exists()
    assert not (tmp_path / ".owlbear/target-cutover.pending").exists()


def test_cutover_rejects_stale_source_before_durable_intent(tmp_path: Path) -> None:
    request, source, adapter = _workspace_request(tmp_path)
    request = request.model_copy(
        update={"sources": (request.sources[0].model_copy(update={"expected_source_digest": "b" * 64}),)}
    )

    with pytest.raises(TargetCutoverReadinessError) as raised:
        cut_over_target_runtime(tmp_path, request, smoke=_smoke)

    assert raised.value.code == "ERR_TARGET_CUTOVER_SOURCE_STALE"
    assert source.is_dir()
    assert adapter.read_bytes() == b"bootstrap\n"
    assert not (tmp_path / request.snapshot_path).exists()
    assert not (tmp_path / request.target_path).exists()
    assert not (tmp_path / ".owlbear/target-cutover.pending").exists()


def test_concurrent_cutovers_serialize_without_losing_source_or_snapshot(tmp_path: Path) -> None:
    request, source, _adapter = _workspace_request(tmp_path)
    source_retired = Event()
    release_first = Event()
    second_done = Event()
    results: list[object] = []

    def pause_after_retirement(stage: str, _path: Path) -> None:
        if stage == "source-retirement":
            source_retired.set()
            assert release_first.wait(timeout=2)

    def run(failure: object | None) -> None:
        try:
            result = cut_over_target_runtime(tmp_path, request, smoke=_smoke, failure=failure)  # type: ignore[arg-type]
            results.append(result)
        except BaseException as exc:  # noqa: BLE001 - retain thread failure for assertion.
            results.append(exc)
        finally:
            if failure is None:
                second_done.set()

    first = Thread(target=run, args=(pause_after_retirement,))
    second = Thread(target=run, args=(None,))
    first.start()
    assert source_retired.wait(timeout=2)
    second.start()
    assert not second_done.wait(timeout=0.1)
    release_first.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert not any(isinstance(item, BaseException) for item in results)
    assert sorted(item.replayed for item in results) == [False, True]  # type: ignore[union-attr]
    assert not source.exists()
    assert query_target_snapshot(tmp_path, request, "runtime").manifest.source_digest


def test_mutation_authorization_waits_for_cutover_receipt(tmp_path: Path) -> None:
    request, _source, _adapter = _workspace_request(tmp_path)
    source_retired = Event()
    release_cutover = Event()
    authorization_done = Event()
    results: list[object] = []

    def pause_after_retirement(stage: str, _path: Path) -> None:
        if stage == "source-retirement":
            source_retired.set()
            assert release_cutover.wait(timeout=2)

    def activate() -> None:
        results.append(cut_over_target_runtime(tmp_path, request, smoke=_smoke, failure=pause_after_retirement))

    def authorize() -> None:
        try:
            results.append(authorize_target_mutation(tmp_path, request))
        finally:
            authorization_done.set()

    activation = Thread(target=activate)
    authorization = Thread(target=authorize)
    activation.start()
    assert source_retired.wait(timeout=2)
    authorization.start()
    assert not authorization_done.wait(timeout=0.1)
    release_cutover.set()
    activation.join(timeout=2)
    authorization.join(timeout=2)

    assert not activation.is_alive()
    assert not authorization.is_alive()
    assert len(results) == 2
    assert any(isinstance(item, TargetMutationAuthority) for item in results)


def test_cutover_recovers_durable_pending_intent_after_process_death(tmp_path: Path) -> None:
    request, source, adapter = _workspace_request(tmp_path)

    def terminate(stage: str, _path: Path) -> None:
        if stage == "adapter-staging":
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        cut_over_target_runtime(tmp_path, request, smoke=_smoke, failure=terminate)

    assert adapter.read_bytes() == b"target\n"
    assert (tmp_path / ".owlbear/target-cutover.pending").is_file()
    result = cut_over_target_runtime(tmp_path, request, smoke=_smoke)
    assert result.replayed is False
    assert not source.exists()
    assert adapter.read_bytes() == b"target\n"


def test_mutation_rejects_reappearing_current_schema_jobs(tmp_path: Path) -> None:
    request, source, _adapter = _workspace_request(tmp_path)
    cut_over_target_runtime(tmp_path, request, smoke=_smoke)
    (source / "jobs").mkdir(parents=True)
    (source / "jobs/99-build.md").write_text("obsolete\n", encoding="utf-8")

    with pytest.raises(TargetMutationGateError) as raised:
        authorize_target_mutation(tmp_path, request)

    assert raised.value.code == "ERR_TARGET_CUTOVER_LEGACY_ACTIVE_WORK"
    assert "jobs/99-build.md" in str(raised.value)


def test_consumer_store_without_receipt_names_required_actions(tmp_path: Path) -> None:
    request, _source, _adapter = _workspace_request(tmp_path)

    with pytest.raises(TargetMutationGateError) as raised:
        authorize_target_mutation(tmp_path, request)

    assert raised.value.code == "ERR_TARGET_CUTOVER_REQUIRED"
    assert raised.value.required_actions == (
        "snapshot current authority and runtime stores",
        "classify unfinished changes, outcomes, and C1-C3 commitments",
    )
    assert "snapshot and classification are required" in str(raised.value)
