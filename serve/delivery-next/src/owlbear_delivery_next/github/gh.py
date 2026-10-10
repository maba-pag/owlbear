# Adapted from serve/delivery-github/src/owlbear_delivery_github/github.py at ab9cfc6cb.
"""``gh`` provider: fixed REST and GraphQL operations; rules read with HTTP 403 are unknown (D4 §3.2)."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NoReturn
from urllib.parse import quote, urlencode

from pydantic import ValidationError

from owlbear_delivery_next.github.provider import (
    Check,
    Comment,
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

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from pathlib import Path

TIMEOUT = 30.0
_API_VERSION = "2026-03-10"
_MAX_CHECKS = 100
# gh prints `gh: <message> (HTTP 409)`, or `gh: HTTP 409` when the body has no top-level message.
_HTTP_STATUS = re.compile(r"^gh: (?:HTTP (\d{3})|.*\(HTTP (\d{3})\))$", re.MULTILINE)
_LOG_STAMP = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ")
_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|[\x00-\x08\x0b-\x1f\x7f]")
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

type Runner = Callable[[tuple[str, ...], bytes | None, float, Path | None], subprocess.CompletedProcess[bytes]]
type Json = Any


@dataclass(frozen=True)
class Missing:
    """A read answered with an expected error status; ``message`` is GitHub's evidence."""

    status: int
    message: str


def run(
    argv: tuple[str, ...], data: bytes | None, timeout: float, cwd: Path | None
) -> subprocess.CompletedProcess[bytes]:
    """Run one fixed ``gh`` command without a terminal."""
    return subprocess.run(  # noqa: S603 - fixed gh executable and code-owned argument vectors
        argv, input=data, capture_output=True, timeout=timeout, cwd=cwd, check=False, stdin=None
    )


def _status(stderr: bytes) -> int | None:
    found = list(_HTTP_STATUS.finditer(stderr.decode(errors="replace")))
    return int(found[-1].group(1) or found[-1].group(2)) if found else None


def _message(stderr: bytes) -> str:
    text = stderr.decode(errors="replace").strip().splitlines()
    return bounded(text[-1].removeprefix("gh: ") if text else "") or "no message"


def _repo(repository: str) -> str:
    owner, name = repository.split("/", 1)
    return f"repos/{quote(owner, safe='')}/{quote(name, safe='')}"


def _fail(operation: str, stderr: bytes, *, write: bool) -> NoReturn:
    text = stderr.decode(errors="replace").casefold()
    if "rate limit" in text or "http 429" in text:
        code, safe = FailureCode.RATE_LIMITED, True
    elif "gh auth login" in text or "http 401" in text or "bad credentials" in text:
        code, safe = FailureCode.AUTHENTICATION_REQUIRED, False
    elif "http 404" in text or "not found" in text or "could not resolve to" in text:
        code, safe = FailureCode.NOT_FOUND, False
    elif "http 409" in text or "http 422" in text or "already exists" in text:
        code, safe = FailureCode.CONFLICT, False
    elif write:
        code, safe = FailureCode.RESPONSE_UNKNOWN, False
    else:
        code, safe = FailureCode.UNAVAILABLE, True
    raise ProviderError(code, operation, _message(stderr), retry_safe=safe)


def _invalid(operation: str, detail: str, cause: Exception | None = None) -> NoReturn:
    raise ProviderError(FailureCode.INVALID_RESPONSE, operation, detail, retry_safe=True) from cause


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
        _invalid(operation, "GitHub returned an invalid pull request", exc)


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
        _invalid(operation, "GitHub returned an invalid check", exc)


class GhProvider:
    """Execute only Delivery's fixed GitHub operations through ``gh``; GitHub Enterprise via ``host``."""

    def __init__(self, cwd: Path, *, host: str = "github.com", timeout: float = TIMEOUT, runner: Runner = run) -> None:
        self.cwd, self.host, self.timeout, self.runner = cwd, host, timeout, runner

    def _gh(  # noqa: PLR0913 - one runner for reads, writes, absent statuses and raw logs
        self,
        operation: str,
        args: tuple[str, ...],
        *,
        body: Json = None,
        write: bool = False,
        absent: Collection[int] = (),
        raw: bool = False,
    ) -> Json:
        data = None if body is None else json.dumps(body, separators=(",", ":")).encode()
        try:
            done = self.runner(("gh", *args), data, self.timeout, self.cwd)
        except FileNotFoundError as exc:
            raise ProviderError(FailureCode.UNAVAILABLE, operation, "gh is not installed", retry_safe=False) from exc
        except subprocess.TimeoutExpired as exc:
            code = FailureCode.RESPONSE_UNKNOWN if write else FailureCode.TIMEOUT
            raise ProviderError(code, operation, "gh timed out", retry_safe=not write) from exc
        if done.returncode != 0:
            if (status := _status(done.stderr)) in absent:
                return Missing(status or 0, _message(done.stderr))
            _fail(operation, done.stderr, write=write)
        if raw:
            return done.stdout.decode(errors="replace")
        try:
            return json.loads(done.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            code = FailureCode.RESPONSE_UNKNOWN if write else FailureCode.INVALID_RESPONSE
            raise ProviderError(code, operation, "gh returned invalid JSON", retry_safe=not write) from exc

    def _api(self, operation: str, method: str, endpoint: str, **kw: Any) -> Json:  # noqa: ANN401 - JSON
        args = ("api", "--method", method, "--hostname", self.host, "-H", "Accept: application/vnd.github+json")
        args += ("-H", f"X-GitHub-Api-Version: {_API_VERSION}", endpoint)
        return self._gh(operation, (*args, "--input", "-") if kw.get("body") is not None else args, **kw)

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
            _invalid("read_repository", "gh returned an invalid repository", exc)

    def read_rules(self, repository: str, branch: str) -> Rules:
        """Read rulesets and classic protection; any HTTP 403 makes the rules unknown with GitHub's message."""
        op, b = "read_rules", quote(branch, safe="")
        rules = self._api(op, "GET", f"{_repo(repository)}/rules/branches/{b}?per_page=100", absent={_FORBIDDEN})
        classic = self._api(op, "GET", f"{_repo(repository)}/branches/{b}/protection", absent={_FORBIDDEN, _NOT_FOUND})
        for found in (rules, classic):
            if isinstance(found, Missing) and found.status == _FORBIDDEN:
                return Rules(state="unknown", evidence=f"HTTP 403: {found.message}")
        try:
            types = tuple(sorted({r["type"] for r in rules}))
            params = [r.get("parameters") or {} for r in rules if r["type"] == "required_status_checks"]
            contexts = [c["context"] for p in params for c in p.get("required_status_checks", [])]
            strict = any(p.get("strict_required_status_checks_policy") for p in params)
            if isinstance(classic, dict) and (rsc := classic.get("required_status_checks")):
                contexts += rsc.get("contexts") or []
                strict = strict or bool(rsc.get("strict"))
        except (KeyError, TypeError, AttributeError) as exc:
            _invalid(op, "GitHub returned invalid branch rules", exc)
        protection = "none" if isinstance(classic, Missing) else "set"
        evidence = f"rules {', '.join(types) or 'none'}; classic protection {protection}"
        return Rules(
            state="known",
            evidence=evidence,
            types=types,
            required_checks=tuple(sorted(set(contexts))),
            queue_required="merge_queue" in types,
            strict=strict,
        )

    def find_pull_request(self, repository: str, head: str, base: str) -> PullRequest | None:
        """Return the unique open pull request for one head and base branch."""
        owner = repository.split("/", 1)[0]
        query = urlencode({"state": "open", "head": f"{owner}:{head}", "base": base, "per_page": 100})
        found = self._api("find_pull_request", "GET", f"{_repo(repository)}/pulls?{query}")
        if not isinstance(found, list) or len(found) > 1:
            raise ProviderError(FailureCode.CONFLICT, "find_pull_request", "several open PRs match", retry_safe=False)
        return self.read_pull_request(repository, int(found[0]["number"])) if found else None

    def read_pull_request(self, repository: str, number: int) -> PullRequest:
        """Read one exact pull request; a merged one gets its merge commit, which this REST version omits."""
        pr = _pull(repository, self._api("read_pull_request", "GET", f"{_repo(repository)}/pulls/{number}"), "read")
        if pr.merged and pr.merge_commit_sha is None:
            owner, name = repository.split("/", 1)
            body = {"query": _MERGED, "variables": {"owner": owner, "name": name, "number": number}}
            found = self._gh(
                "read_pull_request", ("api", "--hostname", self.host, "graphql", "--input", "-"), body=body
            )
            try:
                sha = found["data"]["repository"]["pullRequest"]["mergeCommit"]["oid"]
            except (KeyError, TypeError) as exc:
                _invalid("read_pull_request", "GitHub omitted the merge commit", exc)
            pr = pr.model_copy(update={"merge_commit_sha": sha})
        return pr

    def create_pull_request(self, repository: str, head: str, base: str, title: str, body: str) -> PullRequest:
        """Create one draft pull request; an unknown outcome is read back by the caller."""
        payload = {"title": title, "body": body, "head": head, "base": base, "draft": True}
        p = self._api("create_pull_request", "POST", f"{_repo(repository)}/pulls", body=payload, write=True)
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
        endpoint = f"{_repo(repository)}/pulls/{number}"
        self._api("close_pull_request", "PATCH", endpoint, body={"state": "closed"}, write=True)

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
            _invalid(op, "GitHub returned an invalid check rollup", exc)
        if pr["headRefOid"] != head or commit["oid"] != head:
            raise ProviderError(FailureCode.CONFLICT, op, f"head moved to {pr['headRefOid'][:7]}", retry_safe=True)
        if rollup is None:
            return ()
        if rollup["contexts"]["pageInfo"]["hasNextPage"]:
            _invalid(op, f"more than {_MAX_CHECKS} checks")
        return tuple(_check(n, op) for n in rollup["contexts"]["nodes"])

    def read_comments(self, repository: str, number: int) -> tuple[Comment, ...]:
        """Read inline review threads (replies joined to their root) and review bodies asking for changes."""
        op, base = "read_comments", f"{_repo(repository)}/pulls/{number}"
        threads: dict[str, Comment] = {}
        try:
            for c in self._api(op, "GET", f"{base}/comments?per_page=100"):
                key = f"c{c.get('in_reply_to_id') or c['id']}"
                text = f"{c['user']['login']}: {c['body']}"
                old = threads.get(key)
                body = f"{old.body}\n{text}" if old else text
                threads[key] = Comment(
                    id=key, author=c["user"]["login"], body=body, path=c.get("path"), url=c["html_url"]
                )
            for r in self._api(op, "GET", f"{base}/reviews?per_page=100"):
                if r["state"] in {"CHANGES_REQUESTED", "COMMENTED"} and (r.get("body") or "").strip():
                    key = f"r{r['id']}"
                    threads[key] = Comment(id=key, author=r["user"]["login"], body=r["body"], url=r["html_url"])
        except (KeyError, TypeError, ValidationError) as exc:
            _invalid(op, "GitHub returned invalid review comments", exc)
        return tuple(threads.values())

    def job_log(self, repository: str, job_id: int, lines: int = 40) -> str:
        """Return the tail of one Actions job log without timestamps or escapes; empty when it cannot be read."""
        endpoint = f"{_repo(repository)}/actions/jobs/{job_id}/logs"
        try:  # escapes are removed below, so gh may pass them through
            text = self._gh("job_log", ("api", "--hostname", self.host, "--allow-escape-sequences", endpoint), raw=True)
        except ProviderError:
            return ""
        all_lines = str(text).splitlines()
        end = next((i for i in range(len(all_lines) - 1, -1, -1) if "##[error]" in all_lines[i]), len(all_lines) - 1)
        tail = all_lines[max(0, end + 1 - lines) : end + 1]  # the lines up to the last error
        return "\n".join(_ESCAPE.sub("", _LOG_STAMP.sub("", line)) for line in tail)

    def compare(self, repository: str, base: str, head: str) -> str:
        """Return a short delta from *base* to *head*: commit subjects and changed files."""
        c = self._api("compare", "GET", f"{_repo(repository)}/compare/{base}...{head}")
        try:
            subjects = [x["commit"]["message"].splitlines()[0] for x in c["commits"]][:5]
            files = [f["filename"] for f in c.get("files", [])][:8]
            return bounded(f"{c['ahead_by']} commit(s): {'; '.join(subjects)} · files: {', '.join(files)}") or ""
        except (KeyError, TypeError, IndexError) as exc:
            _invalid("compare", "GitHub returned an invalid comparison", exc)

    def request_merge(self, request: MergeRequest) -> MergeResult:
        """Merge with ``sha`` set to the consented head; a queued submission maps ``enqueued`` to pending."""
        endpoint = f"{_repo(request.repository)}/pulls/{request.number}/{'merge-async' if request.queue else 'merge'}"
        args = ("api", "--method", "PUT", "--hostname", self.host, "-H", f"X-GitHub-Api-Version: {_API_VERSION}")
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
            status = _status(done.stderr)
            if request.queue and status == _CONFLICT:
                return MergeResult(status=MergeStatus.PENDING, message=message)
            reason = _MERGE_REFUSALS.get(status or 0)
            if reason is None:
                return MergeResult(status=MergeStatus.UNKNOWN, message=message or _message(done.stderr))
            return MergeResult(status=MergeStatus.REFUSED, refusal=reason, message=message)
        return self._merged(payload, request, message)

    @staticmethod
    def _merged(payload: Json, request: MergeRequest, message: str | None) -> MergeResult:  # noqa: PLR0911 - per status
        if not isinstance(payload, dict):
            return MergeResult(status=MergeStatus.UNKNOWN, message="no merge response")
        if not request.queue:
            if payload.get("merged") is True and isinstance(payload.get("sha"), str):
                return MergeResult(status=MergeStatus.MERGED, sha=payload["sha"], message=message)
            return MergeResult(status=MergeStatus.UNKNOWN, message=message)
        details = payload.get("details") or {}
        match payload.get("status"):
            case "merged" if isinstance(details.get("sha"), str):
                return MergeResult(status=MergeStatus.MERGED, sha=details["sha"], message=message)
            case "enqueued":
                return MergeResult(status=MergeStatus.ENQUEUED, message=message)
            case "pending":
                return MergeResult(status=MergeStatus.PENDING, message=message)
            case "failed":
                return MergeResult(status=MergeStatus.REFUSED, refusal=Refusal.RULES_FAILED, message=message)
            case _:
                return MergeResult(status=MergeStatus.UNKNOWN, message=message)

    def delete_branch(self, repository: str, branch: str) -> None:
        """Delete one remote branch; an already absent branch is fine."""
        endpoint = f"{_repo(repository)}/git/refs/heads/{quote(branch, safe='/')}"
        self._api("delete_branch", "DELETE", endpoint, write=True, absent={_NOT_FOUND, 422}, raw=True)
