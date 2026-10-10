# Adapted from serve/delivery-github/src/owlbear_delivery_github/github.py at ab9cfc6cb.
"""``gh`` provider: fixed REST and GraphQL operations; rules read with HTTP 403 are unknown (D4 §3.2)."""

from __future__ import annotations

import json
import subprocess
from urllib.parse import quote, urlencode

from pydantic import ValidationError

from owlbear_delivery_next.github import gh_client
from owlbear_delivery_next.github.gh_checks import Checks
from owlbear_delivery_next.github.gh_client import API_VERSION, Json, Missing, invalid, repo
from owlbear_delivery_next.github.gh_conversation import Conversation
from owlbear_delivery_next.github.provider import (
    FailureCode,
    MergeMethod,
    MergeRequest,
    MergeResult,
    MergeStatus,
    ProviderError,
    PullRequest,
    Refusal,
    Repository,
    Rules,
    bounded,
    merge_request_body,
)

_FORBIDDEN, _NOT_FOUND, _CONFLICT = 403, 404, 409
_MERGE_REFUSALS = {
    400: Refusal.CLOSED_OR_DRAFT,
    403: Refusal.FORBIDDEN,
    405: Refusal.NOT_MERGEABLE,
    409: Refusal.HEAD_CHANGED,
    422: Refusal.VALIDATION,
}
_PUSH = frozenset({"ADMIN", "MAINTAIN", "WRITE"})
_READY = """mutation Ready($id: ID!) {
  markPullRequestReadyForReview(input: {pullRequestId: $id}) { pullRequest { id isDraft } }
}"""
_MERGED = """query Merged($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) { pullRequest(number: $number) { mergeCommit { oid } } }
}"""


def _pull(repository: str, p: Json, operation: str) -> PullRequest:
    try:
        return PullRequest(
            repository=repository,
            number=p["number"],
            node_id=p["node_id"],
            url=p["html_url"],
            head_branch=p["head"]["ref"],
            head_sha=p["head"]["sha"],
            base_branch=p["base"]["ref"],
            draft=p["draft"],
            state=p["state"],
            merged=p["merged"],
            mergeable=p.get("mergeable"),
            merge_state=p.get("mergeable_state"),
            merge_commit_sha=p.get("merge_commit_sha") if p["merged"] else None,
        )
    except (KeyError, TypeError, ValidationError) as exc:
        invalid(operation, "GitHub returned an invalid pull request", exc)


class GhProvider(Checks, Conversation):
    """Execute only Delivery's fixed GitHub operations through ``gh``; GitHub Enterprise via ``host``."""

    def read_repository(self) -> Repository:
        """Read the working directory's repository, default branch, merge methods and push permission."""
        fields = "nameWithOwner,url,defaultBranchRef,squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed"
        r = self._gh("read_repository", ("repo", "view", "--json", f"{fields},deleteBranchOnMerge,viewerPermission"))
        allowed = (
            (MergeMethod.SQUASH, r.get("squashMergeAllowed")),
            (MergeMethod.MERGE, r.get("mergeCommitAllowed")),
            (MergeMethod.REBASE, r.get("rebaseMergeAllowed")),
        )
        try:
            return Repository(
                repository=r["nameWithOwner"],
                url=r["url"],
                default_branch=r["defaultBranchRef"]["name"],
                methods=tuple(m for m, on in allowed if on is True),
                can_push=r.get("viewerPermission") in _PUSH,
                delete_branch_on_merge=bool(r.get("deleteBranchOnMerge")),
            )
        except (KeyError, TypeError, ValidationError) as exc:
            invalid("read_repository", "gh returned an invalid repository", exc)

    def read_rules(self, repository: str, branch: str) -> Rules:
        """Read rulesets and classic protection; any HTTP 403 makes the rules unknown with GitHub's message."""
        op, b = "read_rules", quote(branch, safe="")
        rules = self._api(op, "GET", f"{repo(repository)}/rules/branches/{b}?per_page=100", absent={_FORBIDDEN})
        classic = self._api(op, "GET", f"{repo(repository)}/branches/{b}/protection", absent={_FORBIDDEN, _NOT_FOUND})
        for found in (rules, classic):
            if isinstance(found, Missing) and found.status == _FORBIDDEN:
                return Rules(state="unknown", evidence=f"HTTP 403: {found.message}")
        try:
            types = tuple(sorted({r["type"] for r in rules}))
            params = [r.get("parameters") or {} for r in rules if r["type"] == "required_status_checks"]
            contexts = [c["context"] for p in params for c in p.get("required_status_checks", [])]
            strict = any(p.get("strict_required_status_checks_policy") for p in params)
            resolution = any(
                (r.get("parameters") or {}).get("required_review_thread_resolution")
                for r in rules
                if r["type"] == "pull_request"
            )
            if isinstance(classic, dict) and (rsc := classic.get("required_status_checks")):
                contexts += rsc.get("contexts") or []
                strict = strict or bool(rsc.get("strict"))
            if isinstance(classic, dict):
                resolution = resolution or bool((classic.get("required_conversation_resolution") or {}).get("enabled"))
        except (KeyError, TypeError, AttributeError) as exc:
            invalid(op, "GitHub returned invalid branch rules", exc)
        protection = "none" if isinstance(classic, Missing) else "set"
        evidence = f"rules {', '.join(types) or 'none'}; classic protection {protection}"
        return Rules(
            state="known",
            evidence=evidence,
            types=types,
            required_checks=tuple(sorted(set(contexts))),
            queue_required="merge_queue" in types,
            strict=strict,
            conversation_resolution=resolution,
        )

    def find_pull_request(self, repository: str, head: str, base: str) -> PullRequest | None:
        """Return the unique open pull request for one head and base branch."""
        owner = repository.split("/", 1)[0]
        query = urlencode({"state": "open", "head": f"{owner}:{head}", "base": base, "per_page": 100})
        found = self._api("find_pull_request", "GET", f"{repo(repository)}/pulls?{query}")
        if not isinstance(found, list) or len(found) > 1:
            raise ProviderError(FailureCode.CONFLICT, "find_pull_request", "several open PRs match", retry_safe=False)
        return self.read_pull_request(repository, int(found[0]["number"])) if found else None

    def read_pull_request(self, repository: str, number: int) -> PullRequest:
        """Read one exact pull request; a merged one gets its merge commit, which this REST version omits."""
        pr = _pull(repository, self._api("read_pull_request", "GET", f"{repo(repository)}/pulls/{number}"), "read")
        if pr.merged and pr.merge_commit_sha is None:
            owner, name = repository.split("/", 1)
            body = {"query": _MERGED, "variables": {"owner": owner, "name": name, "number": number}}
            found = self._gh(
                "read_pull_request", ("api", "--hostname", self.host, "graphql", "--input", "-"), body=body
            )
            try:
                sha = found["data"]["repository"]["pullRequest"]["mergeCommit"]["oid"]
            except (KeyError, TypeError) as exc:
                invalid("read_pull_request", "GitHub omitted the merge commit", exc)
            pr = pr.model_copy(update={"merge_commit_sha": sha})
        return pr

    def create_pull_request(self, repository: str, head: str, base: str, title: str, body: str) -> PullRequest:
        """Create one draft pull request; an unknown outcome is read back by the caller."""
        payload = {"title": title, "body": body, "head": head, "base": base, "draft": True}
        p = self._api("create_pull_request", "POST", f"{repo(repository)}/pulls", body=payload, write=True)
        return _pull(repository, p, "create_pull_request")

    def mark_ready(self, pr: PullRequest) -> None:
        """Mark one draft pull request ready for review."""
        body = {"query": _READY, "variables": {"id": pr.node_id}}
        result = self._gh(
            "mark_ready", ("api", "--hostname", self.host, "graphql", "--input", "-"), body=body, write=True
        )
        if not isinstance(result, dict) or result.get("errors"):
            raise ProviderError(FailureCode.RESPONSE_UNKNOWN, "mark_ready", str(result)[:200], retry_safe=False)

    def close_pull_request(self, repository: str, number: int) -> None:
        """Close one pull request without merging it."""
        endpoint = f"{repo(repository)}/pulls/{number}"
        self._api("close_pull_request", "PATCH", endpoint, body={"state": "closed"}, write=True)

    def reopen_pull_request(self, repository: str, number: int) -> None:
        """Reopen one closed pull request."""
        endpoint = f"{repo(repository)}/pulls/{number}"
        self._api("reopen_pull_request", "PATCH", endpoint, body={"state": "open"}, write=True)

    def compare(self, repository: str, base: str, head: str) -> str:
        """Return a short delta from *base* to *head*: commit subjects and changed files."""
        c = self._api("compare", "GET", f"{repo(repository)}/compare/{base}...{head}")
        try:
            subjects = [x["commit"]["message"].splitlines()[0] for x in c["commits"]][:5]
            files = [f["filename"] for f in c.get("files", [])][:8]
            return bounded(f"{c['ahead_by']} commit(s): {'; '.join(subjects)} · files: {', '.join(files)}") or ""
        except (KeyError, TypeError, IndexError) as exc:
            invalid("compare", "GitHub returned an invalid comparison", exc)

    def request_merge(self, request: MergeRequest) -> MergeResult:
        """Merge directly with ``sha`` set to the gated head."""
        endpoint = f"{repo(request.repository)}/pulls/{request.number}/merge"
        args = ("api", "--method", "PUT", "--hostname", self.host, "-H", f"X-GitHub-Api-Version: {API_VERSION}")
        try:
            done = self.runner(
                ("gh", *args, endpoint, "--input", "-"), merge_request_body(request), self.timeout, self.cwd
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return MergeResult(status=MergeStatus.UNKNOWN, message=bounded(type(exc).__name__))
        try:
            payload = json.loads(done.stdout) if done.stdout.strip() else {}
        except UnicodeDecodeError, json.JSONDecodeError:
            payload = {}
        message = bounded(payload.get("message") if isinstance(payload, dict) else None)
        if done.returncode != 0:
            status = gh_client.status(done.stderr)
            reason = _MERGE_REFUSALS.get(status or 0)
            if reason is None:
                return MergeResult(status=MergeStatus.UNKNOWN, message=message or gh_client.message(done.stderr))
            return MergeResult(status=MergeStatus.REFUSED, refusal=reason, message=message)
        return self._merged(payload, message)

    @staticmethod
    def _merged(payload: Json, message: str | None) -> MergeResult:
        if not isinstance(payload, dict):
            return MergeResult(status=MergeStatus.UNKNOWN, message="no merge response")
        if payload.get("merged") is True and isinstance(payload.get("sha"), str):
            return MergeResult(status=MergeStatus.MERGED, sha=payload["sha"], message=message)
        return MergeResult(status=MergeStatus.UNKNOWN, message=message)

    def delete_branch(self, repository: str, branch: str) -> None:
        """Delete one remote branch; an already absent branch is fine."""
        endpoint = f"{repo(repository)}/git/refs/heads/{quote(branch, safe='/')}"
        self._api("delete_branch", "DELETE", endpoint, write=True, absent={_NOT_FOUND, 422}, raw=True)
