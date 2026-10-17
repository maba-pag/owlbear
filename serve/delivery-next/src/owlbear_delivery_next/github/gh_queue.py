"""``gh`` merge queue: membership and queue events of a pull request, enqueue, dequeue and merge-group runs."""

from __future__ import annotations

import json
import subprocess
from urllib.parse import urlencode

from pydantic import ValidationError

from owlbear_delivery_next.github.gh_checks import Checks
from owlbear_delivery_next.github.gh_client import Json, invalid, repo
from owlbear_delivery_next.github.provider import (
    EnqueueResult,
    EnqueueStatus,
    FailureCode,
    GroupRun,
    ProviderError,
    PullRequest,
    QueueEntry,
    QueueEvent,
    QueueState,
    bounded,
)

GROUP_PREFIX = "gh-readonly-queue/"
_QUEUE = """query Queue($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) { pullRequest(number: $number) { state merged headRefOid
    mergeQueueEntry { state position enqueuedAt headCommit { oid } }
    timelineItems(last: 50, itemTypes: [ADDED_TO_MERGE_QUEUE_EVENT, REMOVED_FROM_MERGE_QUEUE_EVENT]) {
      nodes { __typename
        ... on AddedToMergeQueueEvent { id createdAt actor { login } }
        ... on RemovedFromMergeQueueEvent { id createdAt reason actor { login } beforeCommit { oid } }
      } } } }
}"""
_ENQUEUE = """mutation Enqueue($id: ID!, $head: GitObjectID!) {
  enqueuePullRequest(input: {pullRequestId: $id, expectedHeadOid: $head}) { mergeQueueEntry { state } }
}"""
_DEQUEUE = """mutation Dequeue($id: ID!) {
  dequeuePullRequest(input: {id: $id}) { mergeQueueEntry { state } }
}"""


def _event(node: Json) -> QueueEvent:
    kind = "added" if node["__typename"] == "AddedToMergeQueueEvent" else "removed"
    before = (node.get("beforeCommit") or {}).get("oid")
    actor = (node.get("actor") or {}).get("login") or ""
    reason = node.get("reason") or ""
    return QueueEvent(id=node["id"], kind=kind, at=node["createdAt"], actor=actor, reason=reason, before=before)


def _state(pr: Json) -> QueueState:
    e = pr["mergeQueueEntry"]
    entry = None
    if e:  # headCommit is the merge group's commit; GitHub leaves it empty until the group is built
        group = (e.get("headCommit") or {}).get("oid")
        entry = QueueEntry(state=e["state"], position=e["position"], group_sha=group, enqueued_at=e["enqueuedAt"])
    events = [_event(n) for n in pr["timelineItems"]["nodes"]]
    last = {k: next((v for v in reversed(events) if v.kind == k), None) for k in ("added", "removed")}
    is_open, head = pr["state"] == "OPEN", pr["headRefOid"]
    return QueueState(
        merged=pr["merged"], open=is_open, head_sha=head, entry=entry, added=last["added"], removed=last["removed"]
    )


class Queue(Checks):
    """Read and change one pull request's place in its merge queue."""

    def read_queue(self, repository: str, number: int) -> QueueState:
        """Read the pull request, its queue entry and its latest added and removed queue events in one query."""
        op, (owner, name) = "read_queue", repository.split("/", 1)
        result = self._graphql(op, _QUEUE, {"owner": owner, "name": name, "number": number})
        try:
            return _state(result["data"]["repository"]["pullRequest"])
        except (KeyError, TypeError, AttributeError, ValidationError) as exc:
            invalid(op, "GitHub returned an invalid merge-queue state", exc)

    def enqueue(self, pr: PullRequest, expected_head: str) -> EnqueueResult:
        """Add the pull request to its queue at *expected_head*; GraphQL errors are refusals, a lost answer unknown."""
        body = {"query": _ENQUEUE, "variables": {"id": pr.node_id, "head": expected_head}}
        data = json.dumps(body, separators=(",", ":")).encode()
        argv = ("gh", "api", "--hostname", self.host, "graphql", "--input", "-")
        try:
            done = self.runner(argv, data, self.timeout, self.cwd)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return EnqueueResult(status=EnqueueStatus.UNKNOWN, message=bounded(type(exc).__name__))
        try:
            payload = json.loads(done.stdout) if done.stdout.strip() else {}
        except UnicodeDecodeError, json.JSONDecodeError:
            payload = {}
        errors = payload.get("errors") if isinstance(payload, dict) else None
        if errors:  # GitHub answered and changed nothing
            text = "; ".join(str(e.get("message", e)) for e in errors if isinstance(e, dict)) or str(errors)
            return EnqueueResult(status=EnqueueStatus.REFUSED, message=bounded(text))
        entry = ((payload.get("data") or {}).get("enqueuePullRequest") or {}).get("mergeQueueEntry")
        if done.returncode == 0 and entry:
            return EnqueueResult(status=EnqueueStatus.ENQUEUED, message=bounded(entry.get("state")))
        return EnqueueResult(status=EnqueueStatus.UNKNOWN, message=bounded(done.stderr.decode(errors="replace")))

    def dequeue(self, pr: PullRequest) -> None:
        """Take the pull request out of its queue; a PR that is not queued raises, and the caller reads back."""
        result = self._graphql("dequeue", _DEQUEUE, {"id": pr.node_id}, write=True)
        if not isinstance(result, dict) or result.get("errors"):
            raise ProviderError(FailureCode.CONFLICT, "dequeue", str(result)[:200], retry_safe=True)

    def group_runs(self, repository: str, group_sha: str) -> tuple[GroupRun, ...]:
        """Actions runs on ``merge_group`` at the group's commit (a removal's ``before``), newest first."""
        query = urlencode({"event": "merge_group", "head_sha": group_sha, "per_page": 100})
        found = self._api("group_runs", "GET", f"{repo(repository)}/actions/runs?{query}")
        try:
            mine = [
                GroupRun(
                    id=r["id"],
                    name=r.get("name") or "",
                    head_sha=r["head_sha"],
                    branch=r["head_branch"],
                    status=r["status"],
                    conclusion=r["conclusion"],
                    updated_at=r["updated_at"],
                )
                for r in found["workflow_runs"]
                if str(r["head_branch"]).startswith(GROUP_PREFIX) and r["head_sha"] == group_sha
            ]
        except (KeyError, TypeError, ValidationError) as exc:
            invalid("group_runs", "GitHub returned invalid workflow runs", exc)
        return tuple(sorted(mine, key=lambda r: r.updated_at, reverse=True))

    def group_log(self, repository: str, run_id: int, lines: int = 40) -> str:
        """The log tail of the run's first failed job; empty when no job failed or the log cannot be read."""
        try:
            jobs = self._api("group_log", "GET", f"{repo(repository)}/actions/runs/{run_id}/jobs?per_page=100")
            failed = next(j["id"] for j in jobs["jobs"] if j.get("conclusion") not in {None, "success", "skipped"})
        except ProviderError, KeyError, TypeError, StopIteration:
            return ""
        return self.job_log(repository, failed, lines)
