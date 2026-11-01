"""#777: the Updates page's PDS update run on a local remote, with fakes for npm, the sessions and the browser tests.

A checkout pins PDS 4.9.0 and has a page with a planted deprecated value; npm offers 4.10.1. Git runs only on local
repositories in tmp, and GitHub is the Impeccable tests' fake over the bare remote.
"""

import importlib.util
import json
import os
import re
import subprocess
import threading
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.audit_tools import AuditResult
from owlbear_delivery_next.impeccable_runs import machine_lock, pack_job, pack_repair
from owlbear_delivery_next.impeccable_runs.pack_state import MACHINE_LOCK
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.pds_runs import audit, browser, pin, sessions, tree
from owlbear_delivery_next.pds_runs import job as pds_job
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store import pds_run_record
from owlbear_delivery_next.state_store.store import Store


def _sibling(name: str) -> ModuleType:
    """A sibling test module, loaded for its fakes: the tests are no package, so they cannot import each other."""
    spec = importlib.util.spec_from_file_location(f"pds_run_{name}", Path(__file__).with_name(f"{name}.py"))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PACK = _sibling("test_pack_job")  # FakeGitHub and git
PINS = _sibling("test_pds_pin")  # the release's entries, its tarball and integrity
AUDITED = _sibling("test_pds_audit")  # a report the release's schema accepts
git, GITHUB_URL = PACK.git, PACK.GITHUB_URL
OLD, NEW = "4.9.0", "4.10.1"
DEPRECATIONS = "skills/pds-knowledge-js/references/deprecations.md"
SCHEMA = {str(audit.SCHEMA): (pin.package() / pin.TREE / audit.SCHEMA).read_bytes()}
RELEASES = {
    OLD: PINS.BASE | SCHEMA | {
        "CHANGELOG.md": b"# Changelog\n\n## [4.9.0] - 2026-09-01\n- p-tag gains a variant\n",
        DEPRECATIONS: b"[button](references/components/button.md)\n",
        "meta/old.mjs": b"only the old release has it",
    },
    NEW: PINS.BASE | SCHEMA | {
        "CHANGELOG.md": b"# Changelog\n\n## [4.10.1] - 2026-10-01\n- p-text: size x-small is deprecated, use xs\n\n"
                        b"## [4.9.0] - 2026-09-01\n- p-tag gains a variant\n",
        DEPRECATIONS: b"[button](references/components/button.md)\n- p-text size x-small: use xs\n",
    },
}  # fmt: skip
TARBALLS = {v: PINS.tarball(e) for v, e in RELEASES.items()}
PAGE = "web/pages/demo.mjs"  # in the package folder
PLANT = 'size="x-small"'
DEMO = f'import {{ html }} from "/assets/lit.js";\nexport const t = html`<p-text {PLANT}>Hi</p-text>`;\n'
REPO = pin.PREFIX  # a package path as a repository path
PASS = browser.Result(tests=5, failures=0, errors=0, skipped=0, failed=(), code=0, output="5 passed")


def failing(*ids: str) -> browser.Result:
    said = "\n".join(f"FAILED {i} - assert" for i in ids)
    return browser.Result(tests=5, failures=len(ids), errors=0, skipped=0, failed=ids, code=1, output=said)


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """OwlBear's package inside a checkout of main pinning PDS 4.9.0, whose origin is a local bare remote."""
    remote, root = tmp_path / "remote.git", tmp_path / "checkout"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(root))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com"), (f"url.{remote}.insteadOf", GITHUB_URL)):
        git(root, "config", key, value)
    git(root, "remote", "set-url", "origin", GITHUB_URL)
    data = TARBALLS[OLD]
    tree.lay(root, pin.unpack(OLD, PINS.integrity(data), data).files(None))
    package = root / REPO
    for path, text in ((PAGE, DEMO), ("web/vendor/lit.mjs", "export {};\n"), ("project_host/pages.py", "PAGES = 1\n")):
        (package / path).parent.mkdir(parents=True, exist_ok=True)
        (package / path).write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "start")
    git(root, "push", "-q", "-u", "origin", "main")
    return package


class Fakes:
    """npm, the auditor, the updater, the challenger and the browser tests, recording the order they were called in."""

    def __init__(self, package: Path) -> None:
        self.calls: list[str] = []
        self.github = Moving(package.parents[4] / "remote.git")
        self.offline, self.ending = False, "result"  # npm unreachable; how the auditor ends
        self.follow_ups: list[dict] = []  # each audit's manual follow-ups
        self.edits: list[dict[str, str | None]] = []  # per updater session: copy path -> text, None deletes
        self.browsers: list = []  # per browser run: a Result, or an exception it raises; then PASS
        self.browsed: list[tuple[str, tuple[str, ...]]] = []  # each run's tree (its folder's name) and ids
        self.verdicts: list[str] = []  # per challenger session; then pass
        self.sessions: list = []  # every session's config
        self.copies: list[list[str]] = []  # each updater copy's files
        self.repairs: list[dict[str, str]] = []  # per CI repair session: repository path -> text
        self.hold: threading.Event | None = None  # set: the first session waits for it, its run holding the lock
        self.holding = threading.Event()

    def fetch(self, url: str, _seconds: float) -> bytes:
        if self.offline:
            msg = "no route to host"
            raise OSError(msg)
        if url == f"{pin.REGISTRY}/latest":
            return json.dumps({"version": NEW}).encode()
        if url == f"{pin.REGISTRY}/{NEW}":
            tarball = f"{pin.TARBALLS}components-js-{NEW}.tgz"
            return json.dumps({"dist": {"tarball": tarball, "integrity": PINS.integrity(TARBALLS[NEW])}}).encode()
        assert url == f"{pin.TARBALLS}components-js-{NEW}.tgz", url
        return TARBALLS[NEW]

    def session(self, _store: Store, cfg) -> Run:
        self.sessions.append(cfg)
        if self.hold is not None:
            self.holding.set()
            assert self.hold.wait(30)
        done = Termination(confirmed=True)
        if cfg.job == sessions.AUDIT:
            self.calls.append("audit")
            if self.ending != "result":
                return Run(cfg.session_id, self.ending, detail="the model stopped", termination=done)
            said = AuditResult(report=json.dumps(report(cfg.worktree, self.follow_ups)), markdown="# Audit\n")
            return Run(cfg.session_id, "result", payload=said, termination=done)
        if cfg.submit is pack_repair.SUBMIT:  # the agent repairing the pull request's CI in a copy of its head
            self.calls.append("repair")
            for path, text in (self.repairs.pop(0) if self.repairs else {}).items():
                (cfg.worktree / path).parent.mkdir(parents=True, exist_ok=True)
                (cfg.worktree / path).write_text(text, encoding="utf-8")
            said = pack_repair.RepairResult(summary=f"repair {self.calls.count('repair')}")
            return Run(cfg.session_id, "result", payload=said, termination=done)
        if cfg.role == "updater":
            self.calls.append("update")
            self.copies.append(sorted(p.relative_to(cfg.worktree).as_posix() for p in cfg.worktree.rglob("*.*js")))
            planned = self.edits.pop(0) if self.edits else {PAGE: "fix"}
            for path, text in planned.items():
                at = cfg.worktree / path
                if text is None:
                    at.unlink()
                else:
                    at.parent.mkdir(parents=True, exist_ok=True)
                    now = at.read_text(encoding="utf-8") if at.is_file() else ""
                    at.write_text(now.replace(PLANT, 'size="xs"') if text == "fix" else text, encoding="utf-8")
            said = sessions.UpdateResult(summary=f"web/pages/demo.mjs: x-small to xs ({len(self.calls)})")
            return Run(cfg.session_id, "result", payload=said, termination=done)
        assert cfg.role == "challenger"
        self.calls.append("challenger")
        verdict = self.verdicts.pop(0) if self.verdicts else "pass"
        found = [] if verdict == "pass" else [tools.Finding(place=f"{PAGE}:2", problem="xs is too small", fix="s")]
        result = tools.ReviewResult(verdict=verdict, findings=found)
        return Run(cfg.session_id, "result", payload=result, termination=done)

    def browser(self, at: Path, ids: tuple[str, ...]) -> browser.Result:
        self.calls.append("browser")
        self.browsed.append((at.name, ids))
        planned = self.browsers.pop(0) if self.browsers else PASS
        if isinstance(planned, Exception):
            raise planned
        return planned

    def live(self, package: Path) -> pds_job.Live:
        return pds_job.Live(
            package=package, fetch=self.fetch, browser=self.browser, session=self.session, github=self.github,
            sleep=lambda _s: None, poll=1.0, ci_wait=5.0,
        )  # fmt: skip


class Moving(PACK.FakeGitHub):
    """GitHub, where someone may push to the update's pull request once it is open, before its merge."""

    def __init__(self, remote: Path) -> None:
        super().__init__(remote)
        self.push: dict[str, str | None] = {}  # repository path -> text, None deletes; pushed once

    def read_rules(self, repository: str, branch: str):
        if self.push and self.prs:
            pushed(self.remote, next(iter(self.prs.values()))["branch"], self.push)
            self.push = {}
        return super().read_rules(repository, branch)


def pushed(remote: Path, branch: str, files: dict[str, str | None]) -> None:
    """Someone's commit of *files* on *branch* of *remote*."""
    work = remote.parent / "someone"
    git(remote.parent, "clone", "-q", "-b", branch, str(remote), str(work))
    for path, text in files.items():
        if text is None:
            (work / path).unlink()
        else:
            (work / path).parent.mkdir(parents=True, exist_ok=True)
            (work / path).write_text(text, encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "someone's change")
    git(work, "push", "-q", "origin", branch)


def report(at: Path, follow_ups: list[dict]) -> dict:
    """The auditor's report on its copy at *at*: one finding for each planted value, as the schema wants it."""
    places = [
        (p.relative_to(at).as_posix(), n, line)
        for p in sorted((at / "web").rglob("*.mjs"))
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if PLANT in line
    ]
    found = [
        {"id": f"f{i}", "ruleId": "propValue/p-text/size/x-small", "usageKind": "propValue",
         "title": "Deprecated value x-small of prop size on p-text", "confidence": "high", "baselineEffort": "trivial",
         "remediation": {"replacement": {"from": PLANT, "to": 'size="xs"'}, "instruction": "Use xs."},
         "evidence": [{"path": path, "line": n, "snippet": line, "detection": "direct", "valueResolution": "literal"}],
         "sources": [{"reference": "references/deprecations.md", "pdsVersion": NEW}]}
        for i, (path, n, line) in enumerate(places, 1)
    ]  # fmt: skip
    return AUDITED.report(version=NEW, findings=found, follow_ups=follow_ups)


def store(tmp_path: Path, **updater: int) -> Store:
    """The project's store; *updater* gives the updater's loop these round values (TD-209)."""
    s = Store(tmp_path / "store")
    s.root.mkdir(parents=True, exist_ok=True)
    agents = {"agents": {"updater": updater}} if updater else {}
    (s.root / "config.json").write_text(json.dumps({"format": 4, "pr_labels": ["release:minor"]} | agents))
    return s


def run(job: pds_job.Job) -> dict:
    job.start()
    return PACK.settled(job)


def started(tmp_path: Path, checkout: Path, *, updater: dict | None = None, **plan) -> tuple[Fakes, pds_job.Job, dict]:
    """A PDS update run with the fakes' *plan* (attribute -> value) and *updater*'s round values, settled."""
    fakes = Fakes(checkout)
    for key, value in plan.items():
        setattr(fakes, key, value)
    job = pds_job.Job(store(tmp_path, **(updater or {})), fakes.live(checkout))
    return fakes, job, run(job)


def landed(package: Path, path: str = "") -> str:
    """The update's commit as merged into main on the remote, or a file of it."""
    root = package.parents[3]
    git(root, "fetch", "-q", "origin")
    made = git(root, "rev-parse", "origin/main^2")
    return git(root, "show", f"{made}:{REPO}{path}") if path else made


def results(state: dict) -> dict[str, str]:
    return {s["name"]: s["result"] for s in state["stages"]}


def test_an_update_audits_fixes_tests_and_challenges_the_pages_then_merges_one_commit(tmp_path, checkout):
    """The plant is found, the updater fixes it in its copy, both gates pass the fix and one pull request merges it."""
    root = checkout.parents[3]
    before = (git(root, "rev-parse", "HEAD"), (checkout / PAGE).read_text(), (checkout / pin.PIN).read_bytes())
    fakes, job, state = started(tmp_path, checkout)

    pub = state["published"]
    assert (state["state"], state["reason"]) == (
        "passed", f"updated to PDS {NEW}: merged into main as {pub['merged'][:12]} through {pub['url']}"
    )  # fmt: skip
    kept = pds_run_record.read_only(job.store.root)  # what Updates reads: the ended run's context is gone
    assert (kept["release"], kept["context"]) == (NEW, None)
    assert fakes.calls == ["audit", "update", "audit", "browser", "challenger"]
    assert fakes.browsed == [("candidate", ())]
    assert results(state) == dict.fromkeys(results(state), "passed") | {"update": "completed"}
    assert fakes.copies == [["web/pages/demo.mjs"]]  # the pages only: never the vendored folders
    updater, challenger = fakes.sessions[1], fakes.sessions[-1]
    assert f"{PAGE}:2:" in updater.message  # the finding, at its copy path
    assert "Use xs." in updater.message
    assert "p-text: size x-small is deprecated, use xs" in updater.message  # the release's changelog
    assert '+export const t = html`<p-text size="xs">Hi</p-text>`;' in challenger.message  # the page edit
    assert f"removed: {pin.TREE}/meta/old.mjs" in challenger.message  # the vendored change
    assert (challenger.policy.write, challenger.pds.name) == (False, sessions.KNOWLEDGE)

    made = landed(checkout)
    assert json.loads(landed(checkout, pin.PIN))["version"] == NEW
    assert 'size="xs"' in landed(checkout, PAGE)
    assert landed(checkout, f"{pin.WEB}/load.mjs").startswith(f"/* {pin.NAME} {NEW} esm/index.mjs;")
    files = git(root, "show", "--name-only", "--format=%s", made).splitlines()
    assert files[:2] == [f"PDS: {OLD} to {NEW}", ""]
    assert f"{REPO}{PAGE}" in files  # edited
    assert f"{REPO}{pin.TREE}/meta/old.mjs" in files  # removed
    assert f"{REPO}project_host/pages.py" not in files
    assert f"{REPO}web/vendor/lit.mjs" not in files
    assert git(root, "rev-parse", f"{made}^") == before[0]
    (pr,) = fakes.github.prs.values()
    assert (pr["branch"], pr["labels"]) == (pub["branch"], ["release:minor"])
    assert pr["branch"].startswith("pds/")
    assert pr["body"].endswith("Opened by OwlBear Delivery for a PDS update.")
    assert "The challenger passed it." in pr["body"]
    assert fakes.github.calls == ["create", "merge", "delete"]
    now = (git(root, "rev-parse", "HEAD"), (checkout / PAGE).read_text(), (checkout / pin.PIN).read_bytes())
    assert now == before  # the running checkout never changed
    assert git(root, "status", "--porcelain") == ""


def test_a_challenger_finding_goes_to_a_fresh_updater_and_both_gates_and_the_challenger_run_again(tmp_path, checkout):
    """Plan d8 step 7: the challenger's findings send the run back; the next updater is told them.

    With no round made the last by its few findings, the repair gets the full checks and a challenger round of its own.
    """
    answer = {PAGE: f"{FIXED}export const s = 1;\n"}
    fakes, _job, state = started(tmp_path, checkout, updater={"last_round_at": 0}, verdicts=["fix"],
                                 edits=[{PAGE: "fix"}, answer])  # fmt: skip

    assert state["state"] == "passed", state["reason"]
    assert fakes.calls == ["audit", "update", "audit", "browser", "challenger", "update", "audit", "browser",
                           "challenger"]  # fmt: skip
    first, second = (s.message for s in fakes.sessions if s.role == "updater")
    assert "xs is too small" not in first
    assert "xs is too small" in second


def test_an_up_to_date_pin_ends_up_to_date_with_nothing_downloaded(tmp_path, checkout):
    fakes = Fakes(checkout)
    fetch = fakes.fetch
    fakes.fetch = lambda url, s: json.dumps({"version": OLD}).encode() if url.endswith("/latest") else fetch(url, s)
    state = run(pds_job.Job(store(tmp_path), fakes.live(checkout)))
    assert (state["state"], state["reason"]) == ("up-to-date", f"up to date: PDS {OLD} is npm's latest release")
    assert (fakes.calls, fakes.github.calls) == ([], [])


@pytest.mark.parametrize(
    ("plan", "said", "calls"),
    [
        ({"offline": True}, "npm was not reached for @porsche-design-system/components-js", []),
        ({"ending": "error"}, "audit: the auditor submitted no report: ended error", ["audit"]),
        ({"browsers": [browser.Unrunnable("the PDS CDN did not answer, so the browser tests prove nothing")]},
         "the PDS CDN did not answer", ["audit", "update", "audit", "browser"]),
        ({"browsers": [browser.Result(0, 0, 0, 0, (), 5, "no tests ran")]},
         "browser tests: 0 browser test(s) ran, 0 failed, 0 errored, 0 skipped (exit 5)",
         ["audit", "update", "audit", "browser"]),
        ({"browsers": [failing("tests/test_x.py::t"), failing("tests/test_x.py::t")]},
         "browser tests fail on main as well: tests/test_x.py::t", ["audit", "update", "audit", "browser", "browser"]),
    ],
    ids=["npm-unreachable", "no-audit-result", "cdn-unrunnable", "zero-tests", "failing-on-main-too"],
)  # fmt: skip
def test_a_gate_that_cannot_judge_stops_the_update_with_its_reason_and_opens_nothing(tmp_path, checkout, plan, said,
                                                                                     calls):  # fmt: skip
    fakes, _job, state = started(tmp_path, checkout, **plan)
    assert state["state"] == "failed"
    assert said in state["reason"]
    assert fakes.calls == calls
    assert (fakes.github.prs, fakes.github.calls) == ({}, [])


def test_a_failure_the_update_caused_goes_to_a_fresh_updater_and_both_gates_run_again(tmp_path, checkout):
    """A test failing on the candidate but passing on main is the update's: the updater gets it, never a waiver."""
    broken = replace(failing("tests/test_machine_pages.py::test_menu"), told="test_menu\nAssertionError: no dot")
    fakes, _job, state = started(tmp_path, checkout, browsers=[broken, PASS, broken])

    assert state["state"] == "passed", state["reason"]
    assert fakes.calls == [
        "audit", "update", "audit", "browser", "browser", "browser", "update", "audit", "browser", "challenger"
    ]  # fmt: skip
    rerun = [("base", broken.failed), ("candidate", broken.failed)]
    assert fakes.browsed == [("candidate", ()), *rerun, ("candidate", ())]
    second = [c for c in fakes.sessions if c.role == "updater"][1]
    assert "tests/test_machine_pages.py::test_menu" in second.message
    assert "AssertionError: no dot" in second.message  # what the report said, not the output's tail
    assert second.session_id != fakes.sessions[1].session_id  # a fresh session


def test_a_failure_passing_its_rerun_on_main_and_the_candidate_is_a_named_flake(tmp_path, checkout):
    """D-01M6BFK5YF5GYYN7QCDDPBEZH2: no updater round for a test that passes again on both trees."""
    flaky = failing("tests/test_visual.py::test_a_real_capture_of_a_local_page")
    fakes, _job, state = started(tmp_path, checkout, browsers=[flaky, PASS, PASS])

    assert state["state"] == "passed", state["reason"]
    assert fakes.calls == ["audit", "update", "audit", "browser", "browser", "browser", "challenger"]
    assert fakes.browsed == [("candidate", ()), ("base", flaky.failed), ("candidate", flaky.failed)]
    gate = next(s for s in state["stages"] if s["name"] == "browser")
    assert gate["result"] == "passed"
    assert gate["detail"].endswith("passed on a rerun on the candidate and on main: " + flaky.failed[0])


@pytest.mark.parametrize(("where", "state_", "calls"), [
    ("candidate", "passed", ["audit", "update", "audit", "browser", "browser", "browser", "update", "audit", "browser",
                             "challenger"]),
    ("base", "failed", ["audit", "update", "audit", "browser", "browser"]),
])  # fmt: skip
def test_a_rerun_that_skips_a_failing_test_proves_no_flake(tmp_path, checkout, where, state_, calls):
    two = failing("tests/test_a.py::t", "tests/test_b.py::t")
    half = browser.Result(tests=2, failures=0, errors=0, skipped=1, failed=(), code=0, output="1 passed, 1 skipped")
    plan = [two, half] if where == "base" else [two, PASS, half]
    fakes, _job, state = started(tmp_path, checkout, browsers=plan)

    assert state["state"] == state_, state["reason"]
    assert fakes.calls == calls
    if where == "base":
        assert "browser tests fail on main as well" in state["reason"]


def test_an_update_whose_updater_sessions_are_spent_stops_with_what_is_still_open(tmp_path, checkout):
    broken = failing("tests/test_machine_pages.py::test_menu")
    fakes, _job, state = started(tmp_path, checkout, updater={"max_rounds": 1}, browsers=[broken, PASS, broken])

    assert state["state"] == "failed"
    assert "spent its 1 updater session(s)" in state["reason"]
    assert "tests/test_machine_pages.py::test_menu" in state["reason"]
    assert fakes.calls.count("update") == 1


@pytest.mark.parametrize("added", [False, True], ids=["same-set", "new-follow-up"])
def test_a_continue_covers_the_follow_ups_shown_and_a_new_one_asks_again(tmp_path, checkout, added):
    """D-01M69VVX2N0F938Y0NSHQYP40S: never the updater's; the owner's continue covers exactly the set he saw."""
    one, two = AUDITED.follow_up("the size the theme picks"), AUDITED.follow_up("the weight the theme picks")
    broken = failing("tests/test_machine_pages.py::test_menu")
    fakes, job, state = started(tmp_path, checkout, follow_ups=[one], browsers=[broken, PASS, broken])
    [q] = state["questions"]
    assert (state["state"], q["kind"], fakes.calls) == ("waiting", "follow-ups", ["audit", "update", "audit"])
    if added:
        fakes.follow_ups = [one, two]

    state = PACK.answered(job, "continue")  # the browser failure sends the run back to the updater and the audit

    assert fakes.calls[3:7] == ["browser", "browser", "browser", "update"]
    assert all("the theme picks" not in s.message for s in fakes.sessions if s.role == "updater")
    if added:
        [q] = state["questions"]
        assert (state["state"], q["kind"]) == ("waiting", "follow-ups")
        assert "the weight the theme picks" in q["text"]
        return
    assert state["state"] == "passed", state["reason"]
    assert fakes.calls[7:] == ["audit", "browser", "challenger"]


@pytest.mark.parametrize(
    ("edit", "named"),
    [
        ({"web/pages/new.mjs": "export {};\n"}, "web/pages/new.mjs"),
        ({PAGE: None}, PAGE),
        ({"web/pages/data.json": "{}\n"}, "web/pages/data.json"),
    ],
    ids=["creates", "deletes", "edits-json"],
)
def test_an_updater_that_changes_what_it_may_not_stops_the_update(tmp_path, checkout, edit, named):
    fakes, _job, state = started(tmp_path, checkout, edits=[{PAGE: "fix", **edit}])
    assert state["state"] == "failed"
    assert f"the updater changed files it may not ({named}); nothing it did was taken" in state["reason"]
    assert (fakes.calls, fakes.github.calls) == (["audit", "update"], [])


def test_nothing_an_updater_did_is_taken_when_one_change_is_outside_its_pages(tmp_path):
    candidate, copy = tmp_path / "candidate", tmp_path / "copy"
    (candidate / tree.WEB / "pages").mkdir(parents=True)
    (candidate / REPO / PAGE).write_text(DEMO)

    start = tree.copy(candidate, copy, lambda at, args: git(at, *args))
    (copy / PAGE).write_text("fixed\n")
    (copy / "web/pages/new.mjs").write_text("export {};\n")
    with pytest.raises(tree.Outside, match=r"web/pages/new\.mjs"):
        tree.taken(copy, start, candidate)
    assert (candidate / REPO / PAGE).read_text() == DEMO


def test_a_publication_stop_waits_and_a_retry_merges_the_one_pull_request(tmp_path, checkout):
    fakes = Fakes(checkout)
    fakes.github.checks = ["failure"]
    job = pds_job.Job(store(tmp_path), fakes.live(checkout))
    state = run(job)
    (q,) = state["questions"]
    assert (state["state"], q["kind"]) == ("waiting", "publish")
    assert "CI failed" in state["reason"]
    fakes.github.checks = ["success"]

    state = PACK.answered(job, "retry")

    assert state["state"] == "passed", state["reason"]
    assert fakes.github.calls.count("create") == 1
    assert fakes.calls == ["audit", "update", "audit", "browser", "challenger"]  # nothing judged again


FIXED = DEMO.replace(PLANT, 'size="xs"')  # the page as the update left it


def ci_failed(tmp_path: Path, checkout: Path, *repairs: dict[str, str]) -> tuple[Fakes, pds_job.Job, dict, list[str]]:
    """An update whose pull request's CI failed, waiting; its repair sessions make *repairs*. The last item is the pull
    request's head on the remote at each browser run, to show what a repair's check saw pushed."""
    fakes, heads = Fakes(checkout), []
    fakes.github.checks, fakes.repairs = ["failure"], list(repairs)
    browse = fakes.browser

    def watched(at: Path, ids: tuple[str, ...]) -> browser.Result:
        heads.append(pr_head(checkout, fakes))
        return browse(at, ids)

    fakes.browser = watched
    job = pds_job.Job(store(tmp_path), fakes.live(checkout))
    state = run(job)
    (q,) = state["questions"]
    assert (state["state"], q["kind"], [o["id"] for o in q["options"]]) == (
        "waiting", "publish", ["retry", "repair", "discard"]
    )  # fmt: skip
    return fakes, job, state, heads


def pr_head(checkout: Path, fakes: Fakes) -> str:
    """The update's pull request's branch on the remote; empty before it is open."""
    if not fakes.github.prs:
        return ""
    ref = f"refs/heads/{next(iter(fakes.github.prs.values()))['branch']}"
    return git(checkout.parents[3], "ls-remote", "origin", ref).split()[0]


def test_a_ci_repair_of_a_page_is_checked_as_one_more_round_before_it_is_pushed_and_merges_once_approved(
    tmp_path, checkout
):
    """The repaired page passes the audit, the browser tests and the challenger before the remote has it; then CI, then
    the owner's approval of the changed pages, then the merge."""
    repaired = FIXED + "export const u = 1;\n"
    fakes, job, _state, heads = ci_failed(tmp_path, checkout, {f"{REPO}{PAGE}": repaired})
    calls, before = len(fakes.calls), pr_head(checkout, fakes)
    fakes.github.checks = ["success"]

    state = PACK.answered(job, "repair")

    assert fakes.calls[calls:] == ["repair", "audit", "browser", "challenger"]
    assert heads[-1] == before  # checked before it was pushed
    assert "export const u = 1;" in fakes.sessions[-1].message  # the challenger saw the repair
    (q,) = state["questions"]
    assert (state["state"], q["kind"], q["paths"]) == ("waiting", "repair-approval", [f"{REPO}{PAGE}"])
    assert "+export const u = 1;" in q["diff"]
    assert pr_head(checkout, fakes) != before
    assert (state["repair"]["attempts"], fakes.github.calls) == (1, ["create"])  # never merged without him
    rounds = [i["round"] for i in state["invocations"] if i["operation"] == "pds-challenge"]
    assert rounds == [1, 2]  # one more counted round

    state = PACK.answered(job, "approve-repair")

    assert state["state"] == "passed", state["reason"]
    assert landed(checkout, PAGE) == repaired.rstrip("\n")
    assert fakes.github.calls == ["create", "merge", "delete"]


def test_a_ci_repair_whose_page_the_audit_flags_is_dropped_unpushed_and_another_is_offered(tmp_path, checkout):
    fakes, job, _state, _heads = ci_failed(tmp_path, checkout, {f"{REPO}{PAGE}": DEMO})  # the plant back
    calls, before = len(fakes.calls), pr_head(checkout, fakes)

    state = PACK.answered(job, "repair")

    assert fakes.calls[calls:] == ["repair", "audit"]
    (q,) = state["questions"]
    assert (state["state"], q["kind"], [o["id"] for o in q["options"]]) == (
        "waiting", "publish", ["retry", "repair", "discard"]
    )  # fmt: skip
    assert "failed its check and was not pushed" in state["reason"]
    assert (pr_head(checkout, fakes), fakes.github.calls, state["repair"]["attempts"]) == (before, ["create"], 1)


@pytest.mark.parametrize(
    "path",
    [f"{REPO}{pin.PIN}", f"{REPO}{pin.TREE}/CHANGELOG.md", f"{REPO}{pin.WEB}/load.mjs"],
    ids=["pin", "vendored", "served"],
)
def test_a_ci_repair_of_what_only_an_update_may_change_is_never_pushed(tmp_path, checkout, path):
    fakes, job, _state, _heads = ci_failed(tmp_path, checkout, {path: "edited\n"})
    calls, before = len(fakes.calls), pr_head(checkout, fakes)

    state = PACK.answered(job, "repair")

    (q,) = state["questions"]
    assert (q["kind"], q["paths"], [o["id"] for o in q["options"]]) == (
        "repair-config", [f"{path} (PDS files only an update may change)"], ["retry", "discard"]
    )  # fmt: skip
    with pytest.raises(pack_job.Refused):
        job.answer(q["id"], "push-config")
    assert (fakes.calls[calls:], pr_head(checkout, fakes), fakes.github.calls) == (["repair"], before, ["create"])


def test_a_ci_repair_of_a_workflow_asks_the_owner_with_its_diff_before_it_is_pushed(tmp_path, checkout):
    fakes, job, _state, _heads = ci_failed(tmp_path, checkout, {".github/workflows/ci.yml": "on: push\n"})
    before = pr_head(checkout, fakes)

    state = PACK.answered(job, "repair")
    (q,) = state["questions"]
    assert (q["kind"], q["paths"], [o["id"] for o in q["options"]]) == (
        "repair-config", [".github/workflows/ci.yml"], ["push-config", "retry", "discard"]
    )  # fmt: skip
    assert "+on: push" in q["diff"]
    assert (pr_head(checkout, fakes), fakes.github.calls) == (before, ["create"])
    fakes.github.checks = ["success"]

    state = PACK.answered(job, "push-config")

    assert state["state"] == "passed", state["reason"]
    root = checkout.parents[3]
    assert git(root, "show", f"{landed(checkout)}:.github/workflows/ci.yml") == "on: push"


def test_one_update_runs_at_a_time_on_this_machine_whichever_kind_holds_the_lock(tmp_path, checkout):
    held = machine_lock.take(local_home.root() / MACHINE_LOCK, "garage", lambda: None)  # an Impeccable update's holder
    try:
        with pytest.raises(pack_job.Busy, match="an update runs for garage; one update runs at a time"):
            pds_job.Job(store(tmp_path), Fakes(checkout).live(checkout)).start()
    finally:
        os.close(held)
    fakes = Fakes(checkout)
    fakes.hold = threading.Event()  # the PDS run holds the lock in its audit
    job = pds_job.Job(store(tmp_path), fakes.live(checkout))
    job.start()
    try:
        assert fakes.holding.wait(30)
        with pytest.raises(pack_job.Busy, match=r"an Impeccable update runs for .+ \(PDS update\)"):
            pack_job.Job(Store(tmp_path / "other" / "store"), pack_job.Live()).start()
    finally:
        fakes.hold.set()
    assert job.thread is not None
    job.thread.join(60)
    assert job.read()["state"] == "passed"


@pytest.mark.parametrize(
    ("push", "held", "rerun"),
    [
        ({}, "", False),
        ({f"{REPO}{PAGE}": DEMO.replace(PLANT, 'size="xs"') + "export const u = 1;\n"}, "", True),
        ({f"{REPO}project_host/pages.py": "PAGES = 2\n"}, "", True),
        ({f"{REPO}{PAGE}": DEMO}, "changed pages, and the deprecation audit found", False),
        ({f"{REPO}{pin.PIN}": "{}\n"}, "holds release files other than the candidate's", False),
        ({f"{REPO}{pin.TREE}/CHANGELOG.md": "# edited\n"}, "holds release files other than the candidate's", False),
        ({f"{REPO}{pin.WEB}/index.css": "html{}\n"}, "holds release files other than the candidate's", False),
        ({f"{REPO}{pin.TREE}/extra.md": "added\n"}, "holds release files other than the candidate's", False),
    ],
    ids=["unchanged", "page", "pages-module", "page-with-finding", "pin", "vendored", "served", "added-vendored"],
)
def test_the_merge_gate_judges_the_pull_requests_head_again_when_its_pages_changed(tmp_path, checkout, push, held,
                                                                                   rerun):  # fmt: skip
    fakes = Fakes(checkout)
    fakes.github.push = dict(push)
    state = run(pds_job.Job(store(tmp_path), fakes.live(checkout)))

    judged = ["audit", "update", "audit", "browser", "challenger"]
    if held:
        assert (state["state"], state["questions"][0]["kind"]) == ("waiting", "publish")
        assert held in state["reason"]
        assert "merge" not in fakes.github.calls
        assert fakes.calls[: len(judged)] == judged
        return
    assert state["state"] == "passed", state["reason"]
    assert fakes.calls == judged + (["audit", "browser", "challenger"] if rerun else [])
    if rerun:
        assert fakes.browsed[-1][0] == "head"
        notes = [(i["operation"], i["result"]) for i in state["invocations"] if i.get("stage") == "merge"]
        assert {"audit", "browser", "pds-challenge"} <= {op for op, _ in notes}


FLAKY = "tests/test_visual.py::test_a_real_capture_of_a_local_page"


@pytest.mark.parametrize(("reruns", "held"), [
    ([PASS, PASS], ""),
    ([failing(FLAKY)], "the merge gate could not judge the head"),
    ([PASS, failing(FLAKY)], "changed pages, and the browser tests found"),
], ids=["flake", "fails-on-main", "head-caused"])  # fmt: skip
def test_the_merge_gate_reruns_a_failing_browser_test_as_the_candidate_s_gate_does(tmp_path, checkout, reruns, held):
    fakes = Fakes(checkout)
    fakes.github.push = {f"{REPO}{PAGE}": DEMO.replace(PLANT, 'size="xs"') + "export const u = 1;\n"}
    fakes.browsers = [PASS, failing(FLAKY), *reruns]
    state = run(pds_job.Job(store(tmp_path), fakes.live(checkout)))

    assert [n for n, _ids in fakes.browsed][1:] == ["head", "base", "head"][: 1 + len(reruns)]
    if held:
        assert (state["state"], state["questions"][0]["kind"]) == ("waiting", "publish")
        assert held in state["reason"]
        assert "merge" not in fakes.github.calls
        return
    assert state["state"] == "passed", state["reason"]
    [note] = [i for i in state["invocations"] if i.get("stage") == "merge" and i["operation"] == "browser"]
    assert note["result"] == "passed"
    assert note["detail"].endswith("passed on a rerun on the candidate and on main: " + FLAKY)


class Runner:
    """``subprocess.run`` for the browser tests: what it was given, and the report and output it leaves."""

    def __init__(self, xml: str | None, code: int = 0, output: str = "") -> None:
        self.xml, self.code, self.output, self.given = xml, code, output, {}

    def __call__(self, args, **kw) -> subprocess.CompletedProcess[str]:
        self.given = {"args": args, **kw}
        if self.xml is not None:
            Path(next(a for a in args if a.startswith("--junitxml=")).partition("=")[2]).write_text(self.xml)
        return subprocess.CompletedProcess(args, self.code, self.output, "")


def suite(tests: int, failures: int = 0, errors: int = 0, skipped: int = 0) -> str:
    counts = f'tests="{tests}" failures="{failures}" errors="{errors}" skipped="{skipped}"'
    return f"<testsuites><testsuite {counts}/></testsuites>"


@pytest.fixture
def browsers(tmp_path, monkeypatch) -> Path:
    where = tmp_path / "browsers"
    (where / "chromium-1").mkdir(parents=True)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(where))
    monkeypatch.setenv("OWLBEAR_SECRET_FOR_TEST", "kept out")
    monkeypatch.setenv("NODE_EXTRA_CA_CERTS", "/ca/interception.pem")
    monkeypatch.setenv("https_proxy", "http://proxy:3128")
    return where


def test_the_browser_tests_run_on_the_trees_own_code_with_a_narrow_environment(tmp_path, browsers):
    at, runner = tmp_path / "candidate", Runner(suite(4))
    at.mkdir()
    r = browser.run(at, ("tests/test_a.py::t",), runner=runner)
    assert (r.passed, r.said()) == (True, "4 browser test(s) ran, 0 failed, 0 errored, 0 skipped")
    env = runner.given["env"]
    assert (runner.given["cwd"], env["PYTHONPATH"], env["PLAYWRIGHT_BROWSERS_PATH"]) == (
        at, str(at / browser.SOURCE), str(browsers)
    )  # fmt: skip
    assert "OWLBEAR_SECRET_FOR_TEST" not in env
    assert (env["NODE_EXTRA_CA_CERTS"], env["https_proxy"]) == ("/ca/interception.pem", "http://proxy:3128")
    assert runner.given["args"][3:6] == ["tests/test_a.py::t", "-m", "browser"]


@pytest.mark.parametrize(
    ("runner", "failed"),
    [
        (Runner(suite(4, errors=1), 1, "ERROR tests/test_a.py::t - fixture failed"), ("tests/test_a.py::t",)),
        (Runner(suite(4), 1, "INTERNALERROR"), ()),
        (Runner(suite(3, skipped=3)), ()),
    ],
    ids=["setup-error", "nonzero-exit", "all-skipped"],
)
def test_a_browser_run_is_no_pass_unless_tests_ran_cleanly(tmp_path, browsers, runner, failed):  # noqa: ARG001
    r = browser.run(tmp_path, runner=runner)
    assert (r.passed, r.failed) == (False, failed)


def test_a_failing_browser_run_tells_what_its_report_says_not_the_output_tail(tmp_path, browsers):  # noqa: ARG001
    case = '<testcase classname="tests.test_v" name="t"><failure message="TimeoutError: 30000ms">trace</failure>'
    xml = f'<testsuites><testsuite tests="2" failures="1">{case}</testcase></testsuite></testsuites>'
    r = browser.run(tmp_path, runner=Runner(xml, 1, "FAILED tests/test_v.py::t\n" + "DeprecationWarning\n" * 400))
    assert r.failed == ("tests/test_v.py::t",)
    assert r.told == "tests.test_v::t\nTimeoutError: 30000ms\ntrace"


@pytest.mark.parametrize(
    ("runner", "said"),
    [
        (Runner(suite(4), 1, "E   PDS CDN fetch of https://cdn.ui.porsche.com/x failed"), "the PDS CDN did not answer"),
        (Runner(None, 2, "collection error"), "the browser tests left no report (exit 2)"),
    ],
    ids=["cdn", "no-report"],
)
def test_a_browser_run_that_proves_nothing_cannot_judge(tmp_path, browsers, runner, said):  # noqa: ARG001
    with pytest.raises(browser.Unrunnable, match=re.escape(said)):
        browser.run(tmp_path, runner=runner)


def test_without_playwrights_browsers_the_tests_cannot_run(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "none"))
    with pytest.raises(browser.Unrunnable, match="Playwright's browsers are not installed"):
        browser.run(tmp_path, runner=Runner(suite(1)))
