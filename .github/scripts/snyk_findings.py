"""Snyk Code findings on a pull request, and the owner's tick that ignores one (TD-363).

``comment`` runs in the Security job after ``snyk code test`` failed: it comments each open high finding of the
SARIF file on the pull request once, with a box and an empty reason. ``ignore`` runs when such a comment is edited
by the owner's account (the workflow checks it): when the comment's box is ticked under a written reason, it sets
the finding "Not vulnerable" in Snyk, marks the comment and re-runs the pull request's failed CI.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

MARK = re.compile(r"<!-- snyk-finding: ([A-Za-z0-9-]+) -->")
RECEIPT = re.compile(r"<!-- snyk-ignored: ([A-Za-z0-9-]+) policy=([A-Za-z0-9-]+) -->")
BOX = "- [ ] **Not vulnerable**: tick to ignore this finding in Snyk; only the owner's tick counts (TD-363)"
TICKED = BOX.replace("[ ]", "[x]", 1)
DONE = "- [x] **Not vulnerable**: ignored in Snyk as policy"
REASON = "Reason:"
EMPTY = "the reason under the finding is empty"
FINDING = "snyk/asset/finding/v1"
SNYK_VERSION = "2024-10-15"
ORG = "porsche-ag-fdi3-scanners"
CI = ".github/workflows/ci.yml"
BOT = "github-actions[bot]"


class Http:
    """JSON over HTTPS with one authorization header."""

    def __init__(self, base: str, auth: str, accept: str, content: str) -> None:
        self.base, self.auth, self.accept, self.content = base, auth, accept, content

    def call(self, method: str, path: str, body: object | None = None) -> object:
        """Send one request and return its JSON answer, or ``None`` for an empty one."""
        request = urllib.request.Request(  # noqa: S310 - the API's own https URL
            f"{self.base}/{path}",
            data=None if body is None else json.dumps(body).encode(),
            method=method,
            headers={"Authorization": self.auth, "Accept": self.accept, "Content-Type": self.content},
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            raw = response.read()
        return json.loads(raw) if raw else None


class GitHub:
    """The pull request's comments and CI runs, with the workflow's token."""

    def __init__(self, http: Http, repo: str) -> None:
        self.http, self.repo = http, repo

    def comments(self, pr: int) -> list[dict]:
        """Every comment on the pull request's conversation."""
        found, page = [], 1
        while batch := self.http.call("GET", f"repos/{self.repo}/issues/{pr}/comments?per_page=100&page={page}"):
            found += batch
            page += 1
        return found

    def create(self, pr: int, body: str) -> None:
        """Comment on the pull request."""
        self.http.call("POST", f"repos/{self.repo}/issues/{pr}/comments", {"body": body})

    def update(self, comment: int, body: str) -> None:
        """Rewrite one comment; an edit with the workflow's token starts no workflow."""
        self.http.call("PATCH", f"repos/{self.repo}/issues/comments/{comment}", {"body": body})

    def current(self, comment: int) -> str:
        """One comment's body as it is now, not as the event saw it."""
        return self.http.call("GET", f"repos/{self.repo}/issues/comments/{comment}")["body"]

    def rerun(self, pr: int, *, tries: int = 40, sleep: Callable[[float], None] = time.sleep) -> str:
        """Once the newest CI run of the pull request's head has completed, re-run its failed jobs."""
        sha = self.http.call("GET", f"repos/{self.repo}/pulls/{pr}")["head"]["sha"]
        for attempt in range(tries):
            found = self.http.call(
                "GET", f"repos/{self.repo}/actions/runs?head_sha={sha}&event=pull_request&per_page=100"
            )
            runs = [r for r in found["workflow_runs"] if r.get("path") == CI]
            if not runs:
                return "no CI run to re-run"
            run = max(runs, key=lambda r: r["id"])
            if run["status"] == "completed":
                break
            if attempt < tries - 1:
                sleep(30)
        else:
            return f"CI run {run['id']} is still running; re-run its failed jobs once it ends"
        if run["conclusion"] == "success":
            return f"CI run {run['id']} passed already"
        self.http.call("POST", f"repos/{self.repo}/actions/runs/{run['id']}/rerun-failed-jobs")
        return f"re-ran the failed jobs of CI run {run['id']}"


class Snyk:
    """Snyk's REST API with the CI service account's token."""

    def __init__(self, http: Http) -> None:
        self.http = http

    def ignore(self, finding: str, reason: str, name: str) -> str:
        """Set one Snyk Code finding "Not vulnerable" without expiry; return the new policy's ID."""
        orgs = self.http.call("GET", f"rest/orgs?slug={ORG}&version={SNYK_VERSION}")["data"]
        if not orgs:
            msg = f"the token cannot see the org {ORG}"
            raise RuntimeError(msg)
        policy = {
            "data": {
                "type": "policy",
                "attributes": {
                    "name": name[:255],
                    "action_type": "ignore",
                    "action": {"data": {"ignore_type": "not-vulnerable", "reason": reason[:10000]}},
                    "conditions_group": {
                        "logical_operator": "and",
                        "conditions": [{"field": FINDING, "operator": "includes", "value": finding}],
                    },
                },
            }
        }
        made = self.http.call("POST", f"rest/orgs/{orgs[0]['id']}/policies?version={SNYK_VERSION}", policy)
        return made["data"]["id"]


def findings(sarif: dict) -> list[dict]:
    """The open high findings: SARIF level ``error``, not suppressed, with Snyk's finding identity."""
    run = sarif["runs"][0]
    rules = {rule["id"]: rule for rule in run["tool"]["driver"].get("rules", [])}
    found = []
    for result in run.get("results", []):
        identity = result.get("fingerprints", {}).get(FINDING)
        if result.get("level") != "error" or result.get("suppressions") or not identity:
            continue
        where = result["locations"][0]["physicalLocation"]
        rule = rules.get(result["ruleId"], {})
        found.append({
            "id": identity,
            "rule": rule.get("shortDescription", {}).get("text") or rule.get("name") or result["ruleId"],
            "path": where["artifactLocation"]["uri"],
            "line": where["region"]["startLine"],
            "text": result["message"]["text"],
        })  # fmt: skip
    return found


def body(finding: dict) -> str:
    """One finding's comment: its marker, where it is, the box and the reason to fill in."""
    return (
        f"<!-- snyk-finding: {finding['id']} -->\n"
        f"**Snyk Code: {finding['rule']}** (high) in `{finding['path']}`, line {finding['line']}\n\n"
        f"{finding['text']}\n\n{BOX}\n\n{REASON} "
    )


def comment(gh: GitHub, sarif: dict, pr: int) -> list[str]:
    """Comment each finding the Security job has not commented on yet; return the new findings."""
    seen = {m[1] for c in gh.comments(pr) if c["user"]["login"] == BOT and (m := MARK.search(c["body"]))}
    new = [f for f in findings(sarif) if f["id"] not in seen]
    for finding in new:
        gh.create(pr, body(finding))
    return [f["id"] for f in new]


def pending(now: str) -> tuple[str, str] | str:
    """The finding and reason a comment's ticked box asks to ignore, or why it asks for nothing."""
    mark = MARK.search(now)
    if not mark:
        return "not a finding's comment"
    if DONE in now:
        return "the finding is ignored already"
    if TICKED not in now:
        return "the box is not ticked"
    reason = now.split(REASON, 1)[1].strip() if REASON in now else ""
    return (mark[1], reason) if reason else EMPTY


def ignore(gh: GitHub, snyk: Snyk, pr: int, comment_id: int) -> str:
    """Reconcile one finding's comment as it is now; a refused or reasonless tick is unticked with why.

    Any edit by the owner's account starts this, and GitHub may reorder queued runs or replace a pending one,
    so the comment's live state decides, never the edit that started the run.
    """
    now = gh.current(comment_id)
    if (state := pending(now)) == EMPTY:
        gh.update(comment_id, now.replace(TICKED, f"{BOX}\n\nWrite the reason below first, then tick.", 1))
        return f"nothing set: {EMPTY}; unticked"
    if isinstance(state, str):
        return f"nothing set: {state}"
    finding, reason = state
    receipts = {m[1]: m[2] for c in gh.comments(pr) if c["user"]["login"] == BOT and (m := RECEIPT.search(c["body"]))}
    if policy := receipts.get(finding):  # an editor's stale copy may have saved over the mark
        gh.update(comment_id, now.replace(TICKED, f"{DONE} `{policy}` (TD-363)", 1))
        return f"nothing set: {finding} is ignored already as policy {policy}"
    try:
        policy = snyk.ignore(finding, reason, f"OwlBear #{pr}: {finding}")
    except (urllib.error.URLError, RuntimeError, KeyError) as exc:
        gh.update(comment_id, now.replace(TICKED, f"{BOX}\n\nSnyk refused the ignore ({exc}); tick to retry.", 1))
        return f"Snyk refused the ignore: {exc}"
    gh.create(pr, f"<!-- snyk-ignored: {finding} policy={policy} -->\nSnyk Code finding `{finding}` is ignored as "
              f'"Not vulnerable" by policy `{policy}`, after the owner\'s tick (TD-363).')  # fmt: skip
    gh.update(comment_id, now.replace(TICKED, f"{DONE} `{policy}` (TD-363)", 1))
    return f"ignored {finding} as policy {policy}; {gh.rerun(pr)}"


def main(argv: list[str]) -> int:
    """``comment <sarif>`` from the Security job, or ``ignore`` from the Snyk ignore workflow."""
    env = os.environ
    api = env.get("GITHUB_API_URL") or "https://api.github.com"
    http = Http(api, f"Bearer {env['GH_TOKEN']}", "application/vnd.github+json", "application/json")
    gh, pr = GitHub(http, env["GITHUB_REPOSITORY"]), int(env["PR"])
    if argv[0] == "comment":
        new = comment(gh, json.loads(Path(argv[1]).read_text(encoding="utf-8")), pr)
        report = f"commented {len(new)} new Snyk Code finding(s) on #{pr}"
    else:
        vnd = "application/vnd.api+json"
        snyk = Snyk(Http(env["SNYK_API"], f"token {env['SNYK_TOKEN']}", vnd, vnd))
        report = ignore(gh, snyk, pr, int(env["COMMENT"]))
    sys.stdout.write(report + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
