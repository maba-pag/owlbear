# Adapted from serve/delivery-github/src/owlbear_delivery_github/github.py at ab9cfc6cb.
"""``gh`` checks: check rollups, review requests and Actions job logs."""

from __future__ import annotations

import re

from pydantic import ValidationError

from owlbear_delivery_next.github.gh_client import GhClient, Json, invalid, repo
from owlbear_delivery_next.github.provider import Check, FailureCode, ProviderError

_MAX_CHECKS = 100
_LOG_STAMP = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ")
_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|[\x00-\x08\x0b-\x1f\x7f]")
_CHECKS = """query Checks($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) { pullRequest(number: $number) { headRefOid
    commits(last: 1) { nodes { commit { oid statusCheckRollup { contexts(first: 100) {
      pageInfo { hasNextPage }
      nodes { __typename
        ... on CheckRun { name status conclusion detailsUrl completedAt databaseId
                          isRequired(pullRequestNumber: $number) }
        ... on StatusContext { context state targetUrl isRequired(pullRequestNumber: $number) }
      } } } } } } } }
}"""
_COMMIT_CHECKS = """query CommitChecks($owner: String!, $name: String!, $oid: GitObjectID!) {
  repository(owner: $owner, name: $name) { object(oid: $oid) { ... on Commit { oid
    statusCheckRollup { contexts(first: 100) {
      pageInfo { hasNextPage }
      nodes { __typename
        ... on CheckRun { name status conclusion detailsUrl completedAt databaseId }
        ... on StatusContext { context state targetUrl }
      } } } } } }
}"""
_REVIEWS = """query Reviews($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) { pullRequest(number: $number) { reviewDecision
    reviewRequests(first: 20) { nodes { requestedReviewer {
      __typename ... on User { login } ... on Team { slug } } } } } }
}"""


def _check(node: Json, operation: str) -> Check:
    try:
        if node["__typename"] == "CheckRun":
            return Check(
                name=node["name"],
                status=node["status"].casefold(),
                conclusion=node["conclusion"].casefold() if node["conclusion"] else None,
                required=node["isRequired"],
                url=node["detailsUrl"],
                job_id=node["databaseId"],
                completed_at=node["completedAt"],
            )
        state = node["state"].casefold()
        done = state in {"success", "failure", "error"}
        return Check(
            name=node["context"],
            status="completed" if done else state,
            conclusion=state if done else None,
            required=node["isRequired"],
            url=node["targetUrl"],
        )
    except (KeyError, TypeError, AttributeError, ValidationError) as exc:
        invalid(operation, "GitHub returned an invalid check", exc)


class Checks(GhClient):
    """Read check rollups, review requests and job logs."""

    def observe_commit_checks(self, repository: str, sha: str) -> tuple[Check, ...]:
        """Observe check runs and commit statuses on one commit; outside a PR no check is marked required."""
        op, (owner, name) = "observe_commit_checks", repository.split("/", 1)
        result = self._graphql(op, _COMMIT_CHECKS, {"owner": owner, "name": name, "oid": sha})
        try:
            rollup = result["data"]["repository"]["object"]["statusCheckRollup"]
        except (KeyError, TypeError) as exc:
            invalid(op, "GitHub returned an invalid check rollup", exc)
        if rollup is None:
            return ()
        if rollup["contexts"]["pageInfo"]["hasNextPage"]:
            invalid(op, f"more than {_MAX_CHECKS} checks")
        return tuple(_check({**n, "isRequired": False}, op) for n in rollup["contexts"]["nodes"])

    def review_request(self, repository: str, number: int) -> tuple[str | None, tuple[str, ...]]:
        """Read GitHub's review decision and the requested reviewers (users by login, teams by slug)."""
        op, (owner, name) = "review_request", repository.split("/", 1)
        result = self._graphql(op, _REVIEWS, {"owner": owner, "name": name, "number": number})
        try:
            pr = result["data"]["repository"]["pullRequest"]
            who = [n["requestedReviewer"] or {} for n in pr["reviewRequests"]["nodes"]]
            names = tuple(r.get("login") or r.get("slug") for r in who if r.get("login") or r.get("slug"))
            return pr["reviewDecision"], names
        except (KeyError, TypeError, AttributeError) as exc:
            invalid(op, "GitHub returned an invalid review request", exc)

    def observe_checks(self, repository: str, number: int, head: str) -> tuple[Check, ...]:
        """Observe check runs and commit statuses at one exact head; a moved head is a conflict."""
        op, (owner, name) = "observe_checks", repository.split("/", 1)
        body = {"query": _CHECKS, "variables": {"owner": owner, "name": name, "number": number}}
        result = self._gh(op, ("api", "--hostname", self.host, "graphql", "--input", "-"), body=body)
        try:
            pr = result["data"]["repository"]["pullRequest"]
            commit = pr["commits"]["nodes"][0]["commit"]
            rollup = commit["statusCheckRollup"]
        except (KeyError, TypeError, IndexError) as exc:
            invalid(op, "GitHub returned an invalid check rollup", exc)
        if pr["headRefOid"] != head or commit["oid"] != head:
            raise ProviderError(FailureCode.CONFLICT, op, f"head moved to {pr['headRefOid'][:7]}", retry_safe=True)
        if rollup is None:
            return ()
        if rollup["contexts"]["pageInfo"]["hasNextPage"]:
            invalid(op, f"more than {_MAX_CHECKS} checks")
        return tuple(_check(n, op) for n in rollup["contexts"]["nodes"])

    def job_log(self, repository: str, job_id: int, lines: int = 40) -> str:
        """Return the tail of one Actions job log without timestamps or escapes; empty when it cannot be read."""
        endpoint = f"{repo(repository)}/actions/jobs/{job_id}/logs"
        try:  # escapes are removed below, so gh may pass them through
            text = self._gh("job_log", ("api", "--hostname", self.host, "--allow-escape-sequences", endpoint), raw=True)
        except ProviderError:
            return ""
        all_lines = str(text).splitlines()
        end = next((i for i in range(len(all_lines) - 1, -1, -1) if "##[error]" in all_lines[i]), len(all_lines) - 1)
        tail = all_lines[max(0, end + 1 - lines) : end + 1]  # the lines up to the last error
        return "\n".join(_ESCAPE.sub("", _LOG_STAMP.sub("", line)) for line in tail)
