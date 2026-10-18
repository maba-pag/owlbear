"""The Snyk Code finding comments and the owner's tick that ignores one (TD-363), against faked APIs."""

from __future__ import annotations

import importlib.util
import sys
import urllib.error
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
_SPEC = importlib.util.spec_from_file_location("snyk_findings", ROOT / ".github/scripts/snyk_findings.py")
snyk_findings = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = snyk_findings
_SPEC.loader.exec_module(snyk_findings)

PATH = "serve/delivery-next/src/owlbear_delivery_next/project_host/api.py"


def result(identity: str, *, level: str = "error", suppressed: bool = False) -> dict:
    return {
        "ruleId": "python/PT",
        "level": level,
        "message": {"text": "Unsanitized input flows into FileResponse."},
        "locations": [{"physicalLocation": {"artifactLocation": {"uri": PATH}, "region": {"startLine": 402}}}],
        "fingerprints": {"snyk/asset/finding/v1": identity},
        "suppressions": [{"kind": "external"}] if suppressed else [],
    }


def sarif(*results: dict) -> dict:
    rules = [{"id": "python/PT", "shortDescription": {"text": "Path Traversal"}}]
    return {"runs": [{"tool": {"driver": {"rules": rules}}, "results": list(results)}]}


class Seq(list):
    """Answers given one per call, the last one repeating."""


class Fake:
    """One API: answers by method and path prefix, and records every call."""

    def __init__(self, answers: dict[tuple[str, str], object]) -> None:
        self.answers, self.calls = answers, []

    def call(self, method: str, path: str, body: object | None = None) -> object:
        self.calls.append((method, path, body))
        for (verb, prefix), answer in self.answers.items():
            if verb == method and path.startswith(prefix):
                given = (answer.pop(0) if len(answer) > 1 else answer[0]) if isinstance(answer, Seq) else answer
                if isinstance(given, Exception):
                    raise given
                return given
        return None


def ci_run(status: str = "completed", conclusion: str | None = "failure") -> dict:
    run = {"id": 7, "path": ".github/workflows/ci.yml", "status": status, "conclusion": conclusion}
    return {"workflow_runs": [run]}


def github(comments: list[dict], *, current: str = "", runs: object = None) -> tuple[object, Fake]:
    fake = Fake({
        ("GET", "repos/o/r/issues/5/comments?per_page=100&page=1"): comments,
        ("GET", "repos/o/r/issues/comments/11"): {"body": current},
        ("GET", "repos/o/r/pulls/5"): {"head": {"sha": "abc"}},
        ("GET", "repos/o/r/actions/runs?head_sha=abc"): runs or ci_run(),
    })  # fmt: skip
    return snyk_findings.GitHub(fake, "o/r"), fake


def snyk(policy: object = None) -> tuple[object, Fake]:
    fake = Fake({
        ("GET", "rest/orgs?slug=porsche-ag-fdi3-scanners"): {"data": [{"id": "org-1"}]},
        ("POST", "rest/orgs/org-1/policies"): policy if policy is not None else {"data": {"id": "pol-1"}},
    })  # fmt: skip
    return snyk_findings.Snyk(fake), fake


def test_only_open_high_findings_with_snyk_s_identity_are_commented() -> None:
    found = snyk_findings.findings(
        sarif(result("f-1"), result("f-2", level="warning"), result("f-3", suppressed=True), result(""))
    )
    assert [(f["id"], f["rule"], f["path"], f["line"]) for f in found] == [("f-1", "Path Traversal", PATH, 402)]
    text = snyk_findings.body(found[0])
    assert text.startswith("<!-- snyk-finding: f-1 -->\n**Snyk Code: Path Traversal** (high)")
    assert f"\n\n{snyk_findings.BOX}\n\nReason: " in text


def test_a_finding_is_commented_once_and_only_the_security_job_s_comment_counts() -> None:
    mine = {"user": {"login": "github-actions[bot]"}, "body": "<!-- snyk-finding: f-1 -->"}
    forged = {"user": {"login": "maba-pag"}, "body": "<!-- snyk-finding: f-2 -->"}
    gh, fake = github([mine, forged])
    assert snyk_findings.comment(gh, sarif(result("f-1"), result("f-2")), 5) == ["f-2"]
    assert [(m, p) for m, p, _ in fake.calls if m == "POST"] == [("POST", "repos/o/r/issues/5/comments")]


def finding_comment(reason: str = "", *, box: str = snyk_findings.BOX) -> str:
    text = snyk_findings.body({"id": "f-1", "rule": "Path Traversal", "path": PATH, "line": 402, "text": "t"})
    return text.replace(snyk_findings.BOX, box) + reason


TICKED = snyk_findings.TICKED


@pytest.mark.parametrize(
    ("now", "why"),
    [
        (finding_comment("why"), "the box is not ticked"),
        ("plain words", "not a finding's comment"),
        (finding_comment("why", box=f"{snyk_findings.DONE} `pol-1` (TD-363)"), "the finding is ignored already"),
    ],
)
def test_the_live_comment_sets_nothing_unless_its_box_is_ticked_once_under_a_reason(now: str, why: str) -> None:
    """GitHub may reorder or replace queued runs, so whatever edit started the run, the live comment decides."""
    gh, gh_calls = github([], current=now)
    api, snyk_calls = snyk()
    assert snyk_findings.ignore(gh, api, 5, 11) == f"nothing set: {why}"
    assert not any(method != "GET" for method, _, _ in gh_calls.calls)
    assert not snyk_calls.calls


def test_a_tick_over_an_empty_reason_is_unticked_with_a_note() -> None:
    gh, gh_calls = github([], current=finding_comment(box=TICKED))
    api, snyk_calls = snyk()
    assert snyk_findings.ignore(gh, api, 5, 11) == f"nothing set: {snyk_findings.EMPTY}; unticked"
    edit = next(body for method, _, body in gh_calls.calls if method == "PATCH")["body"]
    assert snyk_findings.BOX in edit
    assert "Write the reason below first, then tick." in edit
    assert not snyk_calls.calls


def test_the_owner_s_tick_sets_not_vulnerable_marks_the_comment_and_reruns_the_failed_ci() -> None:
    reason = "Only stored names reach the path."
    gh, gh_calls = github([], current=finding_comment(reason, box=TICKED))
    api, snyk_calls = snyk()

    report = snyk_findings.ignore(gh, api, 5, 11)

    assert report == "ignored f-1 as policy pol-1; re-ran the failed jobs of CI run 7"
    _, path, policy = snyk_calls.calls[-1]
    assert path == "rest/orgs/org-1/policies?version=2024-10-15"
    attributes = policy["data"]["attributes"]
    assert attributes["action"] == {"data": {"ignore_type": "not-vulnerable", "reason": reason}}
    assert attributes["conditions_group"]["conditions"] == [
        {"field": "snyk/asset/finding/v1", "operator": "includes", "value": "f-1"}
    ]
    assert "expires" not in attributes["action"]["data"]
    edit = next(body for method, path, body in gh_calls.calls if method == "PATCH")
    assert f"{snyk_findings.DONE} `pol-1` (TD-363)" in edit["body"]
    receipt = next(body for method, path, body in gh_calls.calls if method == "POST" and path.endswith("/comments"))
    assert receipt["body"].startswith("<!-- snyk-ignored: f-1 policy=pol-1 -->")
    assert ("POST", "repos/o/r/actions/runs/7/rerun-failed-jobs", None) in gh_calls.calls


def test_a_stale_copy_saved_over_the_mark_finds_the_receipt_and_sets_nothing_twice() -> None:
    """The owner's editor may save a ticked copy from before the mark; the bot's receipt still knows the policy."""
    receipt = {"user": {"login": "github-actions[bot]"}, "body": "<!-- snyk-ignored: f-1 policy=pol-1 -->\nIgnored."}
    gh, gh_calls = github([receipt], current=finding_comment("a better reason", box=TICKED))
    api, snyk_calls = snyk()

    assert snyk_findings.ignore(gh, api, 5, 11) == "nothing set: f-1 is ignored already as policy pol-1"

    assert not snyk_calls.calls
    edit = next(body for method, _, body in gh_calls.calls if method == "PATCH")["body"]
    assert f"{snyk_findings.DONE} `pol-1` (TD-363)" in edit


def test_a_refused_ignore_unticks_the_box_with_the_error_and_runs_nothing() -> None:
    gh, gh_calls = github([], current=finding_comment("why", box=TICKED))
    error = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
    api, _ = snyk(policy=error)

    report = snyk_findings.ignore(gh, api, 5, 11)

    assert report.startswith("Snyk refused the ignore: HTTP Error 403")
    edit = next(body for method, path, body in gh_calls.calls if method == "PATCH")["body"]
    assert snyk_findings.BOX in edit
    assert snyk_findings.TICKED not in edit
    assert not any("rerun" in path for _, path, _ in gh_calls.calls)


def test_a_tick_while_ci_still_runs_waits_for_it_to_end_then_reruns_it() -> None:
    waits = []
    gh, fake = github([], runs=Seq([ci_run("in_progress", None), ci_run("in_progress", None), ci_run()]))
    assert gh.rerun(5, sleep=waits.append) == "re-ran the failed jobs of CI run 7"
    assert waits == [30, 30]
    assert ("POST", "repos/o/r/actions/runs/7/rerun-failed-jobs", None) in fake.calls


@pytest.mark.parametrize(
    ("status", "conclusion", "said"),
    [("in_progress", None, "is still running"), ("completed", "success", "passed already")],
)
def test_a_ci_still_running_after_the_wait_or_passed_is_not_rerun(
    status: str, conclusion: str | None, said: str
) -> None:
    gh, fake = github([], runs=ci_run(status, conclusion))
    assert said in gh.rerun(5, tries=2, sleep=lambda _: None)
    assert not any(method == "POST" for method, _, _ in fake.calls)


def test_only_the_owner_s_edit_of_a_finding_comment_in_owlbear_runs_the_ignore_from_main() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/snyk-ignore.yml").read_text(encoding="utf-8"))
    assert workflow["on"] == {"issue_comment": {"types": ["edited"]}}
    assert workflow["permissions"] == {}
    job = workflow["jobs"]["ignore"]
    for guard in (
        "github.repository == 'maba-pag/owlbear'",
        "github.event.sender.id == 238680231",
        "github.event.comment.user.login == 'github-actions[bot]'",
    ):
        assert guard in job["if"]
    assert job["permissions"] == {"contents": "read", "actions": "write", "pull-requests": "write"}
    checkout, run = job["steps"]
    assert checkout["with"] == {"ref": "main", "persist-credentials": False}
    assert "${{" not in run["run"]  # event text reaches the script only through the environment


def test_the_security_job_comments_code_findings_only_on_pull_requests() -> None:
    security = yaml.safe_load((ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8"))
    steps = {s.get("id") or s["name"]: s for s in security["jobs"]["snyk"]["steps"]}
    assert "--sarif-file-output=snyk-code.sarif" in steps["code"]["run"]
    step = next(s for s in steps.values() if "snyk_findings.py comment" in s.get("run", ""))
    assert "steps.code.outcome == 'failure'" in step["if"]
    assert "github.event_name == 'pull_request'" in step["if"]
    assert security["jobs"]["snyk"]["permissions"]["pull-requests"] == "write"
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    assert ci["jobs"]["security"]["permissions"] == {"contents": "read", "pull-requests": "write"}
