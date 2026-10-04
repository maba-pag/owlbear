"""Behavioral tests for the merge transport of both publication providers."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from owlbear_delivery import (
    PublicationProvider,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    PublicationRepository,
)
from owlbear_delivery.publication_provider import (
    PendingMergeRequest,
    PublicationMergeEvidence,
    PublicationMergeMethod,
    PublicationMergeProvider,
    PublicationMergeRefusal,
    PublicationMergeRefusalReason,
    PublicationMergeRequestResult,
    PublicationMergeRequestStatus,
    PublicationMergeSettings,
    PublicationMergeStack,
    RequestPublicationMerge,
    merge_request_body,
)
from owlbear_delivery_github import GitHubCliPublicationProvider, InMemoryPublicationProvider
from owlbear_delivery_github.effect_launcher import FrozenBodyMismatchError, freeze_body

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_REPOSITORY = "example/project"
_HEAD = "a" * 40
_OTHER_HEAD = "b" * 40
_TARGET = "c" * 40
_ADVANCED_TARGET = "d" * 40
_MERGE_OID = "e" * 40
_UUID = "0f3c2a5e-1111-4222-8333-944455556666"
_MERGED_AT = "2026-08-11T10:02:00Z"
_HEADERS = ("--header", "Accept: application/vnd.github+json", "--header", "X-GitHub-Api-Version: 2026-03-10")


def _request(
    *, head: str = _HEAD, method: PublicationMergeMethod = PublicationMergeMethod.MERGE
) -> RequestPublicationMerge:
    return RequestPublicationMerge(
        repository=_REPOSITORY,
        number=7,
        node_id="PR_node_7",
        expected_head_sha=head,
        merge_method=method,
    )


def _frozen(tmp_path: Path, request: RequestPublicationMerge | None = None) -> Path:
    body = freeze_body(request or _request())
    path = tmp_path / "request-bodies" / f"{hashlib.sha256(body).hexdigest()}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        path.chmod(0o444)
    return path


def _completed(payload: object, *, returncode: int = 0, stderr: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    stdout = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return subprocess.CompletedProcess(args=(), returncode=returncode, stdout=stdout, stderr=stderr)


def _pending_payload(**overrides: object) -> dict[str, object]:
    details: dict[str, object] = {
        "message": "Merge request accepted",
        "uuid": _UUID,
        "merge_method": "merge",
        "merge_action": "direct_merge",
        "expected_head_sha": _HEAD,
        "bypass_rules": False,
    }
    details.update(overrides)
    return {"status": "pending", "details": {key: value for key, value in details.items() if value is not None}}


def _pull_payload(*, merged: bool = False, stack: object = None, head: str = _HEAD) -> dict[str, object]:
    payload: dict[str, object] = {
        "number": 7,
        "node_id": "PR_node_7",
        "head": {"ref": "owlbear/change/example", "sha": head},
        "base": {"ref": "main", "sha": _TARGET},
        "title": "Example change",
        "body": "Generated summary",
        "draft": False,
        "state": "closed" if merged else "open",
        "merged": merged,
        "merged_at": _MERGED_AT if merged else None,
        "merged_by": {"login": "octocat"} if merged else None,
    }
    if stack is not None:
        payload["stack"] = stack
    return payload


def _merge_commit_payload(
    *, parents: tuple[str, ...] = (_TARGET, _HEAD), total: int | None = None
) -> dict[str, object]:
    return {
        "data": {
            "repository": {
                "nameWithOwner": _REPOSITORY,
                "pullRequest": {
                    "number": 7,
                    "headRefOid": _HEAD,
                    "baseRefName": "main",
                    "merged": True,
                    "mergedAt": _MERGED_AT,
                    "mergeCommit": {
                        "oid": _MERGE_OID,
                        "parents": {
                            "totalCount": len(parents) if total is None else total,
                            "nodes": [{"oid": parent} for parent in parents],
                        },
                    },
                },
            }
        }
    }


@dataclass
class _QueuedRunner:
    results: deque[subprocess.CompletedProcess[bytes] | BaseException]
    calls: list[tuple[tuple[str, ...], bytes | None]] = field(default_factory=list)

    def __call__(
        self,
        arguments: tuple[str, ...],
        input_bytes: bytes | None,
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[bytes]:
        del timeout_seconds
        self.calls.append((arguments, input_bytes))
        result = self.results.popleft()
        if isinstance(result, BaseException):
            raise result
        return result


@dataclass
class _EffectRecorder:
    results: deque[subprocess.CompletedProcess[bytes] | BaseException]
    events: list[str] = field(default_factory=list)
    calls: list[tuple[tuple[str, ...], bytes, float]] = field(default_factory=list)

    def __call__(
        self,
        arguments: tuple[str, ...],
        body_path: Path,
        release: Callable[[int, str], None],
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[bytes]:
        self.events.append("spawn")
        release(4242, "fake-start")
        self.events.append("token")
        self.calls.append((arguments, body_path.read_bytes(), timeout_seconds))
        result = self.results.popleft()
        if isinstance(result, BaseException):
            raise result
        return result


def _github(
    *results: subprocess.CompletedProcess[bytes] | BaseException,
    effects: tuple[subprocess.CompletedProcess[bytes] | BaseException, ...] = (),
) -> tuple[GitHubCliPublicationProvider, _QueuedRunner, _EffectRecorder]:
    runner = _QueuedRunner(deque(results))
    recorder = _EffectRecorder(deque(effects))
    provider = GitHubCliPublicationProvider(timeout_seconds=9.0, runner=runner, effect_runner=recorder)
    return provider, runner, recorder


def _released(events: list[str]) -> Callable[[int, str], None]:
    def release(group_id: int, start_time: str) -> None:
        events.append(f"release:{group_id}:{start_time}")

    return release


def _get(endpoint: str) -> tuple[str, ...]:
    return ("gh", "api", "--method", "GET", *_HEADERS, endpoint)


# GitHub CLI provider: exact vectors and positive mappings.


def test_both_providers_implement_the_merge_protocol_beside_the_publication_protocol() -> None:
    github, _, _ = _github()
    memory = InMemoryPublicationProvider()

    for provider in (github, memory):
        assert isinstance(provider, PublicationMergeProvider)
        assert isinstance(provider, PublicationProvider)


def test_merge_settings_read_methods_push_queue_and_strict_rules_through_fixed_gets() -> None:
    provider, runner, _ = _github(
        _completed(
            {
                "full_name": _REPOSITORY,
                "allow_merge_commit": True,
                "allow_squash_merge": False,
                "allow_rebase_merge": True,
                "allow_auto_merge": True,
                "permissions": {"admin": False, "push": True, "pull": True},
            }
        ),
        _completed(
            [
                {"type": "merge_queue", "parameters": {"merge_method": "MERGE"}},
                {"type": "required_status_checks", "parameters": {"strict_required_status_checks_policy": True}},
                {"type": "deletion"},
            ]
        ),
    )

    settings = provider.read_merge_settings(_REPOSITORY, "release/2026")

    assert [call[0] for call in runner.calls] == [
        _get("repos/example/project"),
        _get("repos/example/project/rules/branches/release%2F2026?per_page=100"),
    ]
    assert all(call[1] is None for call in runner.calls)
    assert settings == PublicationMergeSettings(
        repository=_REPOSITORY,
        branch="release/2026",
        allowed_methods=(PublicationMergeMethod.MERGE, PublicationMergeMethod.REBASE),
        viewer_can_push=True,
        rule_types=("deletion", "merge_queue", "required_status_checks"),
        queue_required=True,
        strict_up_to_date_required=True,
        execution_scope_enforced=False,
    )


def test_merge_settings_fail_closed_without_permissions_or_method_fields() -> None:
    provider, _, _ = _github(
        _completed({"full_name": _REPOSITORY}),
        _completed([{"type": "required_status_checks", "parameters": {"strict_required_status_checks_policy": False}}]),
    )

    settings = provider.read_merge_settings(_REPOSITORY, "main")

    assert settings.allowed_methods == ()
    assert settings.viewer_can_push is False
    assert settings.queue_required is False
    assert settings.strict_up_to_date_required is False
    assert settings.execution_scope_enforced is False


def test_branch_head_reads_one_encoded_branch() -> None:
    provider, runner, _ = _github(_completed({"name": "release/2026", "commit": {"sha": _TARGET}}))

    head = provider.read_branch_head(_REPOSITORY, "release/2026")

    assert runner.calls[0][0] == _get("repos/example/project/branches/release%2F2026")
    assert head.head_sha == _TARGET


def test_request_merge_releases_before_token_and_sends_the_frozen_file_never_stdin(tmp_path: Path) -> None:
    provider, runner, recorder = _github(effects=(_completed(_pending_payload(), stderr=b""),))
    body_path = _frozen(tmp_path)

    result = provider.request_merge(_request(), body_path=body_path, release=_released(recorder.events))

    arguments, body, timeout = recorder.calls[0]
    assert recorder.events == ["spawn", "release:4242:fake-start", "token"]
    assert arguments == (
        "gh",
        "api",
        "--method",
        "PUT",
        *_HEADERS,
        "repos/example/project/pulls/7/merge-async",
        "--input",
        str(body_path),
    )
    assert "-" not in arguments
    assert timeout == 9.0
    assert (
        body
        == b'{"bypass_rules":false,"merge_action":"direct_merge","merge_method":"merge","sha":"'
        + _HEAD.encode()
        + b'"}'
    )
    assert runner.calls == []
    assert result.status is PublicationMergeRequestStatus.PENDING
    assert result.pending == PendingMergeRequest(
        request_id=_UUID,
        expected_head_sha=_HEAD,
        merge_method="merge",
        merge_action="direct_merge",
        bypass_rules=False,
    )
    assert result.pending.matches(_request())
    assert result.existing_request is False


def test_repeated_request_adopts_the_pending_request_reported_with_409(tmp_path: Path) -> None:
    provider, _, recorder = _github(
        effects=(_completed(_pending_payload(), returncode=1, stderr=b"gh: Conflict (HTTP 409)\n"),),
    )

    result = provider.request_merge(_request(), body_path=_frozen(tmp_path), release=_released(recorder.events))

    assert result.status is PublicationMergeRequestStatus.PENDING
    assert result.existing_request is True
    assert result.pending is not None
    assert result.pending.request_id == _UUID
    assert result.pending.matches(_request())


@pytest.mark.parametrize("stderr", [b"gh: HTTP 409\n", b"gh: Conflict (HTTP 409)\n", b"warning\ngh: HTTP 409"])
def test_both_gh_status_forms_identify_the_409_pending_request(tmp_path: Path, stderr: bytes) -> None:
    provider, _, recorder = _github(effects=(_completed(_pending_payload(), returncode=1, stderr=stderr),))

    result = provider.request_merge(_request(), body_path=_frozen(tmp_path), release=_released(recorder.events))

    assert result.existing_request is True
    assert result.pending is not None
    assert result.pending.matches(_request())


@pytest.mark.parametrize(
    "stderr",
    [b"HTTP 409\n", b"proxy said (HTTP 409) earlier\n", b"gh: HTTP 4090\n", b"gh: HTTP 409 trailing\n"],
)
def test_status_outside_a_gh_status_line_is_response_unknown(tmp_path: Path, stderr: bytes) -> None:
    provider, _, recorder = _github(effects=(_completed(_pending_payload(), returncode=1, stderr=stderr),))

    with pytest.raises(PublicationProviderError) as raised:
        provider.request_merge(_request(), body_path=_frozen(tmp_path), release=_released(recorder.events))

    assert raised.value.code is PublicationProviderFailureCode.RESPONSE_UNKNOWN
    assert raised.value.retry_safe is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"expected_head_sha": _OTHER_HEAD},
        {"merge_action": "merge_queue"},
        {"bypass_rules": True},
        {"merge_method": "squash"},
    ],
)
def test_foreign_409_options_are_reported_and_never_match(tmp_path: Path, overrides: dict[str, object]) -> None:
    provider, _, recorder = _github(
        effects=(_completed(_pending_payload(**overrides), returncode=1, stderr=b"gh: Conflict (HTTP 409)\n"),),
    )

    result = provider.request_merge(_request(), body_path=_frozen(tmp_path), release=_released(recorder.events))

    assert result.pending is not None
    assert result.pending.matches(_request()) is False


@pytest.mark.parametrize("missing", ["merge_method", "merge_action", "expected_head_sha", "bypass_rules", "uuid"])
def test_409_without_complete_options_is_unknown_never_the_request_own(tmp_path: Path, missing: str) -> None:
    provider, _, recorder = _github(
        effects=(_completed(_pending_payload(**{missing: None}), returncode=1, stderr=b"gh: Conflict (HTTP 409)\n"),),
    )

    with pytest.raises(PublicationProviderError) as raised:
        provider.request_merge(_request(), body_path=_frozen(tmp_path), release=_released(recorder.events))

    assert raised.value.code is PublicationProviderFailureCode.RESPONSE_UNKNOWN
    assert raised.value.retry_safe is False


def test_already_merged_pull_request_reports_merged_with_its_commit(tmp_path: Path) -> None:
    provider, _, recorder = _github(
        effects=(_completed({"status": "merged", "details": {"message": "Already merged", "sha": _MERGE_OID}}),),
    )

    result = provider.request_merge(_request(), body_path=_frozen(tmp_path), release=_released(recorder.events))

    assert result == PublicationMergeRequestResult(
        status=PublicationMergeRequestStatus.MERGED,
        merge_commit_sha=_MERGE_OID,
        message="Already merged",
    )


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (400, PublicationMergeRefusalReason.CLOSED_OR_DRAFT),
        (403, PublicationMergeRefusalReason.FORBIDDEN),
        (405, PublicationMergeRefusalReason.NOT_MERGEABLE),
        (422, PublicationMergeRefusalReason.VALIDATION),
    ],
)
def test_complete_http_refusals_map_to_typed_refusals(
    tmp_path: Path,
    status: int,
    reason: PublicationMergeRefusalReason,
) -> None:
    error_body = {"message": "Pull request\n is not\tmergeable " + "x" * 600, "status": str(status)}
    provider, _, recorder = _github(
        effects=(_completed(error_body, returncode=1, stderr=f"gh: refused (HTTP {status})\n".encode()),),
    )

    result = provider.request_merge(_request(), body_path=_frozen(tmp_path), release=_released(recorder.events))

    assert result.status is PublicationMergeRequestStatus.REFUSED
    assert result.refusal is not None
    assert result.refusal.reason is reason
    assert result.refusal.http_status == status
    assert result.refusal.message is not None
    assert result.refusal.message.startswith("Pull request is not mergeable x")
    assert len(result.refusal.message) == 500


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ({"status": "failed", "details": {"message": "Required status check failed"}}, "rules-failed"),
        ({"status": "enqueued", "details": {"message": "Added to merge queue"}}, "queue-required"),
    ],
)
def test_final_failed_or_enqueued_results_are_refusals(tmp_path: Path, payload: object, reason: str) -> None:
    provider, _, recorder = _github(effects=(_completed(payload),))

    result = provider.request_merge(_request(), body_path=_frozen(tmp_path), release=_released(recorder.events))

    assert result.refusal is not None
    assert result.refusal.reason == reason
    assert result.refusal.message is not None


@pytest.mark.parametrize(
    "effect",
    [
        subprocess.TimeoutExpired(cmd="gh", timeout=9.0),
        _completed(b"not json"),
        _completed(b"", returncode=1, stderr=b"gh: Server Error (HTTP 502)\n"),
        _completed(b"", returncode=1, stderr=b"gh: Not Found (HTTP 404)\n"),
        _completed(b"", returncode=86, stderr=b"owlbear-effect-launcher: unsent: release token missing\n"),
        _completed({"status": "merged", "details": {"message": "no sha"}}),
        _completed({"status": "surprising"}),
    ],
)
def test_unknown_write_outcomes_are_response_unknown_and_not_retry_safe(
    tmp_path: Path,
    effect: subprocess.CompletedProcess[bytes] | BaseException,
) -> None:
    provider, _, recorder = _github(effects=(effect,))

    with pytest.raises(PublicationProviderError) as raised:
        provider.request_merge(_request(), body_path=_frozen(tmp_path), release=_released(recorder.events))

    assert raised.value.code is PublicationProviderFailureCode.RESPONSE_UNKNOWN
    assert raised.value.retry_safe is False


def test_frozen_body_mismatch_is_refused_before_spawn(tmp_path: Path) -> None:
    provider, _, recorder = _github(effects=(_completed(_pending_payload()),))
    body_path = _frozen(tmp_path, _request(head=_OTHER_HEAD))

    with pytest.raises(FrozenBodyMismatchError):
        provider.request_merge(_request(), body_path=body_path, release=_released(recorder.events))

    assert recorder.events == []
    assert recorder.calls == []


def test_read_merge_request_reads_pending_and_merged_by_uuid() -> None:
    provider, runner, _ = _github(
        _completed(_pending_payload()),
        _completed({"status": "merged", "details": {"message": "Merged", "sha": _MERGE_OID}}),
    )

    pending = provider.read_merge_request(_REPOSITORY, 7, _UUID)
    merged = provider.read_merge_request(_REPOSITORY, 7, _UUID)

    assert runner.calls[0][0] == _get(f"repos/example/project/pulls/7/merge-async/{_UUID}")
    assert pending.status is PublicationMergeRequestStatus.PENDING
    assert merged.status is PublicationMergeRequestStatus.MERGED
    assert merged.merge_commit_sha == _MERGE_OID


def test_expired_merge_request_is_unavailable_never_refused() -> None:
    provider, _, _ = _github(_completed({"message": "Not Found"}, returncode=1, stderr=b"gh: Not Found (HTTP 404)\n"))

    result = provider.read_merge_request(_REPOSITORY, 7, _UUID)

    assert result == PublicationMergeRequestResult(status=PublicationMergeRequestStatus.UNAVAILABLE)
    assert result.refusal is None


def test_read_merge_request_failures_stay_read_failures() -> None:
    provider, _, _ = _github(
        _completed(b"", returncode=1, stderr=b"gh: Server Error (HTTP 503)\n"),
        _completed(_pending_payload(uuid="another")),
        _completed(_pending_payload(bypass_rules=None)),
    )

    for _ in range(3):
        with pytest.raises(PublicationProviderError) as raised:
            provider.read_merge_request(_REPOSITORY, 7, _UUID)
        assert raised.value.code is not PublicationProviderFailureCode.RESPONSE_UNKNOWN
        assert raised.value.retry_safe is True


def test_merge_evidence_reads_stack_and_its_absence() -> None:
    stack = {"base": {"ref": "main", "sha": _TARGET}, "size": 2, "position": 2, "id": 9, "number": 3}
    provider, runner, _ = _github(_completed(_pull_payload(stack=stack)), _completed(_pull_payload()))

    stacked = provider.read_merge_evidence(_REPOSITORY, 7)
    single = provider.read_merge_evidence(_REPOSITORY, 7)

    assert runner.calls[0][0] == _get("repos/example/project/pulls/7")
    assert len(runner.calls) == 2
    assert stacked.stack == PublicationMergeStack(size=2, position=2, base_branch="main", base_sha=_TARGET)
    assert single.stack is None
    assert single.merged is False
    assert single.merge_commit_parents == ()


def test_merged_evidence_reads_the_merge_commit_and_its_parents() -> None:
    provider, runner, _ = _github(_completed(_pull_payload(merged=True)), _completed(_merge_commit_payload()))

    evidence = provider.read_merge_evidence(_REPOSITORY, 7)

    graphql = json.loads(runner.calls[1][1] or b"{}")
    assert runner.calls[1][0] == ("gh", "api", "graphql", "--method", "POST", "--input", "-")
    assert graphql["operationName"] == "ReadMergeCommit"
    assert graphql["variables"] == {"owner": "example", "name": "project", "number": 7}
    assert evidence.merged is True
    assert evidence.merge_commit_sha == _MERGE_OID
    assert evidence.merge_commit_parents == (_TARGET, _HEAD)
    assert evidence.merged_at == datetime(2026, 8, 11, 10, 2, tzinfo=UTC)


def test_incomplete_merge_commit_parents_are_invalid() -> None:
    provider, _, _ = _github(_completed(_pull_payload(merged=True)), _completed(_merge_commit_payload(total=3)))

    with pytest.raises(PublicationProviderError) as raised:
        provider.read_merge_evidence(_REPOSITORY, 7)

    assert raised.value.code is PublicationProviderFailureCode.INVALID_RESPONSE


# Transport-free contract.


@pytest.mark.parametrize(
    "extra",
    [{"bypass_rules": True}, {"merge_action": "merge_queue"}, {"auto_merge": True}, {"merge_queue": True}],
)
def test_merge_request_model_has_no_bypass_queue_or_auto_merge_field(extra: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        RequestPublicationMerge.model_validate({**_request().model_dump(), **extra})


def test_merge_request_method_rejects_queue_actions() -> None:
    with pytest.raises(ValidationError):
        RequestPublicationMerge.model_validate({**_request().model_dump(), "merge_method": "merge_queue"})


def test_frozen_body_is_canonical_and_carries_every_fence_field() -> None:
    body = merge_request_body(_request(method=PublicationMergeMethod.SQUASH))

    assert json.loads(body) == {
        "bypass_rules": False,
        "merge_action": "direct_merge",
        "merge_method": "squash",
        "sha": _HEAD,
    }
    assert freeze_body(_request(method=PublicationMergeMethod.SQUASH)) == body


def test_existing_pull_request_observation_dump_bytes_are_unchanged() -> None:
    observation = PublicationPullRequest(
        repository=_REPOSITORY,
        number=7,
        node_id="PR_node_7",
        head_branch="owlbear/change/example",
        head_sha=_HEAD,
        base_branch="main",
        title="Example change",
        body="Generated summary",
        draft=False,
        state="open",
        merged=False,
        mergeable=True,
        merge_state_status="clean",
    )

    assert observation.model_dump_json().encode() == (
        b'{"repository":"example/project","number":7,"node_id":"PR_node_7",'
        b'"head_branch":"owlbear/change/example","head_sha":"' + _HEAD.encode() + b'","base_branch":"main",'
        b'"title":"Example change","body":"Generated summary","draft":false,"state":"open","merged":false,'
        b'"merge_commit_sha":null,"merged_at":null,"merged_by_login":null}'
    )


def test_merge_evidence_model_rejects_partial_merge_facts() -> None:
    base = {
        "repository": _REPOSITORY,
        "number": 7,
        "node_id": "PR_node_7",
        "state": "closed",
        "draft": False,
        "head_sha": _HEAD,
        "base_branch": "main",
    }
    with pytest.raises(ValidationError):
        PublicationMergeEvidence.model_validate({**base, "merged": True, "merge_commit_sha": _MERGE_OID})
    with pytest.raises(ValidationError):
        PublicationMergeEvidence.model_validate({**base, "merged": False, "merge_commit_parents": (_TARGET,)})


# In-memory merge fake.


def _memory(*, settings: PublicationMergeSettings | None = None) -> InMemoryPublicationProvider:
    provider = InMemoryPublicationProvider()
    provider.add_repository(PublicationRepository(repository=_REPOSITORY, default_branch="main"))
    provider.set_branch_head(_REPOSITORY, "main", _TARGET)
    provider.pull_requests[(_REPOSITORY, 7)] = PublicationPullRequest(
        repository=_REPOSITORY,
        number=7,
        node_id="PR_node_7",
        head_branch="owlbear/change/example",
        head_sha=_HEAD,
        base_branch="main",
        title="Example change",
        body="Generated summary",
        draft=False,
        state="open",
        merged=False,
    )
    if settings is not None:
        provider.set_merge_settings(settings)
    return provider


def _settings(**overrides: object) -> PublicationMergeSettings:
    values: dict[str, object] = {
        "repository": _REPOSITORY,
        "branch": "main",
        "allowed_methods": (PublicationMergeMethod.MERGE,),
        "viewer_can_push": True,
        "rule_types": (),
        "queue_required": False,
        "strict_up_to_date_required": False,
        "execution_scope_enforced": False,
    }
    values.update(overrides)
    return PublicationMergeSettings.model_validate(values)


def _memory_merge(provider: InMemoryPublicationProvider, tmp_path: Path) -> PublicationMergeRequestResult:
    return provider.request_merge(_request(), body_path=_frozen(tmp_path), release=lambda _group, _start: None)


def test_memory_pending_request_merges_in_the_background_and_reads_back_merged(tmp_path: Path) -> None:
    provider = _memory()

    pending = _memory_merge(provider, tmp_path)
    assert pending.pending is not None
    request_id = pending.pending.request_id
    assert provider.read_merge_request(_REPOSITORY, 7, request_id).status is PublicationMergeRequestStatus.PENDING

    assert provider.execute_pending_merges() == (request_id,)
    merged = provider.read_merge_request(_REPOSITORY, 7, request_id)
    evidence = provider.read_merge_evidence(_REPOSITORY, 7)

    assert merged.status is PublicationMergeRequestStatus.MERGED
    assert evidence.merged is True
    assert evidence.merge_commit_sha == merged.merge_commit_sha
    assert evidence.merge_commit_parents == (_TARGET, _HEAD)
    assert provider.read_branch_head(_REPOSITORY, "main").head_sha == merged.merge_commit_sha
    assert provider.merge_request_bodies == [freeze_body(_request())]


def test_memory_lost_response_applies_the_effect_and_readback_finds_it(tmp_path: Path) -> None:
    provider = _memory()
    provider.lose_next_merge_response = True

    with pytest.raises(PublicationProviderError) as raised:
        _memory_merge(provider, tmp_path)
    repeated = _memory_merge(provider, tmp_path)

    assert raised.value.code is PublicationProviderFailureCode.RESPONSE_UNKNOWN
    assert repeated.existing_request is True
    assert repeated.pending is not None
    assert repeated.pending.matches(_request())
    assert len(provider.merge_requests) == 1
    assert len(provider.merge_request_bodies) == 2


def test_memory_foreign_pending_request_is_reported_and_never_matches(tmp_path: Path) -> None:
    provider = _memory()
    provider.add_foreign_merge_request(
        _REPOSITORY,
        7,
        PendingMergeRequest(
            request_id="foreign",
            expected_head_sha=_HEAD,
            merge_method="merge",
            merge_action="merge_queue",
            bypass_rules=False,
        ),
    )

    result = _memory_merge(provider, tmp_path)

    assert result.existing_request is True
    assert result.pending is not None
    assert result.pending.request_id == "foreign"
    assert result.pending.matches(_request()) is False


def test_memory_merged_pull_request_returns_merged_without_a_new_request(tmp_path: Path) -> None:
    provider = _memory()
    merge_commit = provider.merge_manually(_REPOSITORY, 7)

    result = _memory_merge(provider, tmp_path)

    assert result.status is PublicationMergeRequestStatus.MERGED
    assert result.merge_commit_sha == merge_commit
    assert provider.merge_requests == {}
    assert provider.read_merge_evidence(_REPOSITORY, 7).merged is True
    assert provider.pull_requests[(_REPOSITORY, 7)].merged_by_login == "user"


@pytest.mark.parametrize("change", ["draft", "closed"])
def test_memory_draft_or_closed_pull_request_is_refused(tmp_path: Path, change: str) -> None:
    provider = _memory()
    current = provider.pull_requests[(_REPOSITORY, 7)]
    provider.pull_requests[(_REPOSITORY, 7)] = current.model_copy(
        update={"draft": True} if change == "draft" else {"state": "closed"}
    )

    result = _memory_merge(provider, tmp_path)

    assert result.refusal is not None
    assert result.refusal.reason is PublicationMergeRefusalReason.CLOSED_OR_DRAFT
    assert provider.merge_requests == {}


def test_memory_head_fence_fails_a_request_after_a_push(tmp_path: Path) -> None:
    provider = _memory()
    request_id = _pending_id(_memory_merge(provider, tmp_path))
    current = provider.pull_requests[(_REPOSITORY, 7)]
    provider.pull_requests[(_REPOSITORY, 7)] = current.model_copy(update={"head_sha": _OTHER_HEAD})

    provider.execute_pending_merges()

    result = provider.read_merge_request(_REPOSITORY, 7, request_id)
    assert result.refusal is not None
    assert result.refusal.reason is PublicationMergeRefusalReason.HEAD_CHANGED
    assert provider.read_merge_evidence(_REPOSITORY, 7).merged is False


def test_memory_rules_failure_and_strict_target_advance_fail_without_merging(tmp_path: Path) -> None:
    rules = _memory()
    rules.rules_failures[(_REPOSITORY, 7)] = "Required review is missing"
    strict = _memory(settings=_settings(strict_up_to_date_required=True))

    rules_id = _pending_id(_memory_merge(rules, tmp_path / "rules"))
    strict_id = _pending_id(_memory_merge(strict, tmp_path / "strict"))
    strict.set_branch_head(_REPOSITORY, "main", _ADVANCED_TARGET)
    rules.execute_pending_merges()
    strict.execute_pending_merges()

    for provider, request_id in ((rules, rules_id), (strict, strict_id)):
        result = provider.read_merge_request(_REPOSITORY, 7, request_id)
        assert result.refusal is not None
        assert result.refusal.reason is PublicationMergeRefusalReason.RULES_FAILED
        assert provider.read_merge_evidence(_REPOSITORY, 7).merged is False


def test_memory_unenforced_target_advance_merges_on_the_new_target(tmp_path: Path) -> None:
    provider = _memory()
    _memory_merge(provider, tmp_path)
    provider.set_branch_head(_REPOSITORY, "main", _ADVANCED_TARGET)

    provider.execute_pending_merges()

    evidence = provider.read_merge_evidence(_REPOSITORY, 7)
    assert evidence.merged is True
    assert evidence.merge_commit_parents[0] == _ADVANCED_TARGET


@pytest.mark.parametrize("enforced", [False, True])
def test_memory_base_retarget_after_the_final_read(tmp_path: Path, *, enforced: bool) -> None:
    provider = _memory(settings=_settings(execution_scope_enforced=enforced))
    provider.set_branch_head(_REPOSITORY, "other", _ADVANCED_TARGET)
    _memory_merge(provider, tmp_path)
    current = provider.pull_requests[(_REPOSITORY, 7)]
    provider.pull_requests[(_REPOSITORY, 7)] = current.model_copy(update={"base_branch": "other"})

    provider.execute_pending_merges()

    evidence = provider.read_merge_evidence(_REPOSITORY, 7)
    assert evidence.merged is not enforced
    if not enforced:
        assert evidence.base_branch == "other"
        assert evidence.merge_commit_parents[0] == _ADVANCED_TARGET


@pytest.mark.parametrize("enforced", [False, True])
def test_memory_stack_join_after_the_final_read(tmp_path: Path, *, enforced: bool) -> None:
    provider = _memory(settings=_settings(execution_scope_enforced=enforced))
    downstack = provider.pull_requests[(_REPOSITORY, 7)].model_copy(
        update={"number": 3, "node_id": "PR_node_3", "head_branch": "downstack", "head_sha": _OTHER_HEAD}
    )
    provider.pull_requests[(_REPOSITORY, 3)] = downstack
    _memory_merge(provider, tmp_path)
    provider.set_stack(
        _REPOSITORY,
        7,
        PublicationMergeStack(size=2, position=2, base_branch="main", base_sha=_TARGET),
        downstack=(3,),
    )

    provider.execute_pending_merges()

    assert provider.read_merge_evidence(_REPOSITORY, 7).stack is not None
    assert provider.read_merge_evidence(_REPOSITORY, 7).merged is not enforced
    assert provider.read_merge_evidence(_REPOSITORY, 3).merged is not enforced


def test_memory_expired_request_is_unavailable_and_a_repeated_request_adopts_it(tmp_path: Path) -> None:
    provider = _memory()
    request_id = _pending_id(_memory_merge(provider, tmp_path))
    provider.expire_merge_request(request_id)

    unavailable = provider.read_merge_request(_REPOSITORY, 7, request_id)
    repeated = _memory_merge(provider, tmp_path)
    provider.execute_pending_merges()

    assert unavailable.status is PublicationMergeRequestStatus.UNAVAILABLE
    assert repeated.pending is not None
    assert repeated.pending.request_id == request_id
    assert provider.read_merge_evidence(_REPOSITORY, 7).merged is True
    assert provider.read_merge_request(_REPOSITORY, 7, request_id).status is PublicationMergeRequestStatus.UNAVAILABLE


def test_memory_complete_refusal_and_raised_release_send_nothing(tmp_path: Path) -> None:
    provider = _memory()
    provider.next_merge_refusal = PublicationMergeRefusal(
        reason=PublicationMergeRefusalReason.FORBIDDEN,
        http_status=403,
    )
    refused = _memory_merge(provider, tmp_path)

    def failing_release(_group: int, _start: str) -> None:
        message = "release record could not be written"
        raise OSError(message)

    with pytest.raises(OSError, match="release record"):
        provider.request_merge(_request(), body_path=_frozen(tmp_path), release=failing_release)

    assert refused.refusal is not None
    assert refused.refusal.reason is PublicationMergeRefusalReason.FORBIDDEN
    assert provider.merge_requests == {}
    assert len(provider.merge_request_bodies) == 1


def test_memory_frozen_body_mismatch_is_refused_before_release(tmp_path: Path) -> None:
    provider = _memory()
    released: list[int] = []

    with pytest.raises(FrozenBodyMismatchError):
        provider.request_merge(
            _request(),
            body_path=_frozen(tmp_path, _request(head=_OTHER_HEAD)),
            release=lambda group, _start: released.append(group),
        )

    assert released == []
    assert provider.merge_request_bodies == []


def test_memory_settings_default_and_configured() -> None:
    provider = _memory(settings=_settings(branch="release", queue_required=True, execution_scope_enforced=True))

    default = provider.read_merge_settings(_REPOSITORY, "main")
    configured = provider.read_merge_settings(_REPOSITORY, "release")

    assert default.allowed_methods == tuple(PublicationMergeMethod)
    assert default.execution_scope_enforced is False
    assert configured.queue_required is True
    assert configured.execution_scope_enforced is True


def _pending_id(result: PublicationMergeRequestResult) -> str:
    assert result.pending is not None
    return result.pending.request_id
