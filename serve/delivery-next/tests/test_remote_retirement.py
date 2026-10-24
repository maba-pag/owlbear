"""Guarded GitHub ref retirement over a synthetic Git ref; no live provider writes."""

import json
import subprocess

import pytest

from owlbear_delivery_next.github.gh import GhProvider
from owlbear_delivery_next.github.provider import BranchState, FailureCode, ProviderError

REF = "refs/heads/owlbear/work"


def git(root, *args):
    who = ("-c", "user.name=t", "-c", "user.email=t@example.com")
    return subprocess.run(  # noqa: S603 - synthetic Git fixture
        ("git", *who, *args),  # noqa: S607 - existing test toolchain
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def history(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "commit", "-q", "--allow-empty", "-m", "merged")
    merged = git(tmp_path, "rev-parse", "HEAD")
    git(tmp_path, "commit", "-q", "--allow-empty", "-m", "new work")
    newer = git(tmp_path, "rev-parse", "HEAD")
    git(tmp_path, "update-ref", REF, merged)
    return tmp_path, merged, newer


class RefServer:
    """Model GitHub's documented beforeOid CAS with a real local `update-ref`, including a concurrent writer."""

    def __init__(self, history, mode="normal"):
        self.root, self.merged, self.newer = history
        self.mode, self.writes, self.reads = mode, [], 0
        self.ack = {}

    def head(self):
        return git(self.root, "for-each-ref", "--format=%(objectname)", REF)

    def __call__(self, argv, data, timeout, _cwd):
        assert "graphql" in argv
        body = json.loads(data)
        if "query Branch(" in body["query"]:
            self.reads += 1
            assert body["variables"] == {"owner": "o", "name": "r", "ref": REF}
            ref = {"target": {"oid": self.head()}} if self.head() else None
            repository = {"id": "R", "ref": ref}
            if self.mode == "missing-repository":
                repository = None
            result = {"data": {"repository": repository}}
            if self.mode == "invalid-read":
                result = self.ack
        else:
            assert "mutation Retire(" in body["query"]
            expected = {
                "repositoryId": "R",
                "refUpdates": [{"name": REF, "beforeOid": self.merged, "afterOid": "0" * 40, "force": False}],
            }
            assert body["variables"] == {"input": expected}
            self.writes.append(body)
            if self.mode == "invalid-ack":
                result = self.ack
            else:
                if self.mode == "race":
                    git(self.root, "update-ref", REF, self.newer, self.merged)
                deleted = subprocess.run(  # noqa: S603 - synthetic Git fixture
                    ("git", "update-ref", "-d", REF, self.merged),  # noqa: S607
                    cwd=self.root,
                    capture_output=True,
                    check=False,
                )
                if self.mode in {"lost-ack", "recreated"}:
                    if self.mode == "recreated":
                        git(self.root, "update-ref", REF, self.newer)
                    raise subprocess.TimeoutExpired(argv, timeout)
                result = (
                    {"errors": [{"message": "beforeOid did not match"}]}
                    if deleted.returncode
                    else {"data": {"updateRefs": {"__typename": "UpdateRefsPayload"}}}
                )
        return subprocess.CompletedProcess(argv, 0, json.dumps(result).encode(), b"")


def test_atomic_retirement_uses_the_exact_merged_head_and_no_force(history):
    server = RefServer(history)
    result = GhProvider(server.root, runner=server).delete_branch("o/r", "owlbear/work", server.merged)
    assert result.state is BranchState.DELETED
    assert server.head() == ""
    assert len(server.writes) == server.reads == 1


def test_a_head_moved_between_read_and_mutation_survives_real_compare_and_swap(history):
    server = RefServer(history, "race")
    result = GhProvider(server.root, runner=server).delete_branch("o/r", "owlbear/work", server.merged)
    assert (result.state, result.head) == (BranchState.MOVED, server.newer)
    assert server.head() == server.newer
    assert len(server.writes) == 1
    assert server.reads == 2


def test_an_already_advanced_branch_is_not_mutated(history):
    server = RefServer(history)
    git(server.root, "update-ref", REF, server.newer)
    result = GhProvider(server.root, runner=server).delete_branch("o/r", "owlbear/work", server.merged)
    assert (result.state, result.head) == (BranchState.MOVED, server.newer)
    assert server.head() == server.newer
    assert server.writes == []


def test_an_absent_branch_is_not_confused_with_an_unreadable_repository(history):
    server = RefServer(history)
    git(server.root, "update-ref", "-d", REF)
    gh = GhProvider(server.root, runner=server)
    assert gh.delete_branch("o/r", "owlbear/work", server.merged).state is BranchState.GONE
    server.mode = "missing-repository"
    with pytest.raises(ProviderError) as failed:
        gh.delete_branch("o/r", "owlbear/work", server.merged)
    assert failed.value.code is FailureCode.NOT_FOUND
    assert server.writes == []


@pytest.mark.parametrize(
    ("mode", "state"),
    [("lost-ack", BranchState.GONE), ("recreated", BranchState.MOVED)],
)
def test_a_lost_mutation_answer_is_reconciled_without_repeating_the_write(history, mode, state):
    server = RefServer(history, mode)
    result = GhProvider(server.root, runner=server).delete_branch("o/r", "owlbear/work", server.merged)
    assert result.state is state
    assert server.head() == (server.newer if state is BranchState.MOVED else "")
    assert len(server.writes) == 1


@pytest.mark.parametrize("mode", ["normal", "lost-ack"])
def test_a_fresh_provider_replay_retains_a_branch_recreated_after_the_first_retirement(history, mode):
    first = RefServer(history, mode)
    assert GhProvider(first.root, runner=first).delete_branch(
        "o/r",
        "owlbear/work",
        first.merged,
    ).state in {BranchState.DELETED, BranchState.GONE}
    git(first.root, "update-ref", REF, first.newer)
    restarted = RefServer(history)

    result = GhProvider(restarted.root, runner=restarted).delete_branch("o/r", "owlbear/work", restarted.merged)

    assert (result.state, result.head) == (BranchState.MOVED, first.newer)
    assert restarted.head() == first.newer
    assert restarted.writes == []


@pytest.mark.parametrize(
    "reply",
    [
        {},
        {"data": None},
        {"data": {"repository": {"id": "R"}}},
        {"data": {"repository": {"id": "", "ref": None}}},
        {"data": {"repository": {"id": "R", "ref": {"target": {"oid": "not-a-sha"}}}}},
        {"errors": [{"message": "access refused"}], "data": {"repository": {"id": "R", "ref": None}}},
    ],
)
def test_invalid_or_failed_read_is_never_acknowledged_as_an_absent_branch(history, reply):
    server = RefServer(history, "invalid-read")
    server.ack = reply
    with pytest.raises(ProviderError) as failed:
        GhProvider(server.root, runner=server).delete_branch("o/r", "owlbear/work", server.merged)
    assert failed.value.code is FailureCode.INVALID_RESPONSE
    assert server.head() == server.merged
    assert server.writes == []


@pytest.mark.parametrize(
    "ack",
    [
        {},
        {"data": None},
        {"data": {"updateRefs": {}}},
        {"data": {"updateRefs": None}},
        {"data": {"updateRefs": {"__typename": "OtherPayload"}}},
        {"data": {"updateRefs": {"__typename": "UpdateRefsPayload"}}, "errors": [{"message": "refused"}]},
    ],
)
def test_malformed_or_rejected_mutation_is_not_success_and_a_guarded_retry_is_safe(history, ack):
    server = RefServer(history, "invalid-ack")
    server.ack = ack
    with pytest.raises(ProviderError) as failed:
        GhProvider(server.root, runner=server).delete_branch("o/r", "owlbear/work", server.merged)
    assert failed.value.code is FailureCode.RESPONSE_UNKNOWN
    assert failed.value.retry_safe
    assert server.head() == server.merged
    assert len(server.writes) == 1
