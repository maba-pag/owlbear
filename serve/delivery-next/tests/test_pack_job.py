"""The Settings page's design pack update job (TD-101) and the Maintenance overview (TD-113), with fakes for the live
parts: upstream, downloads, golden pages, replay and the challenger. Git runs only on local repositories in tmp."""

import hashlib
import json
import os
import shutil
import subprocess
import threading
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import dispute_tools, pack_tools, tools
from owlbear_delivery_next.change_contracts.models import Brief, Change
from owlbear_delivery_next.change_contracts.round_records import RoundFinding, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import disputes
from owlbear_delivery_next.design_packs import calibration, design_pack, pack_git, pack_update
from owlbear_delivery_next.github.provider import (
    Check,
    FailureCode,
    MergeMethod,
    MergeRequest,
    MergeResult,
    MergeStatus,
    ProviderError,
    PullRequest,
    Repository,
    Rules,
)
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.pack_runs import pack_gates, pack_job, pack_publish, pack_rounds, pack_updater
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.admission import STOPPING
from owlbear_delivery_next.project_host.host import ENDING, HostRecord
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Lock, Store

AUTH = {"authorization": "Bearer t"}
PKG = files("owlbear_delivery_next")
OLD = design_pack.manifest()
BUNDLE = OLD["bundle"]["path"]
NAMES = [name for name, _ in pack_job.STAGES]
GITHUB_URL = "https://github.com/maba-pag/owlbear.git"


class FakeGitHub:
    """OwlBear's repository on GitHub: pull requests over the bare remote, their checks, and merges into main."""

    def __init__(self, remote: Path) -> None:
        self.remote, self.prs, self.calls = remote, {}, []
        self.checks = ["success"]  # the conclusion at each look; the last one stays
        self.behind, self.labels_fail, self.refusal = 0, False, None
        self.can_push, self.lose_create = True, False

    def read_repository(self) -> Repository:
        return Repository(
            repository="maba-pag/owlbear", url="https://github.com/maba-pag/owlbear", default_branch="main",
            methods=(MergeMethod.MERGE,), can_push=self.can_push, delete_branch_on_merge=True,
        )  # fmt: skip

    def __call__(self, _root: Path) -> FakeGitHub:
        return self

    def _head(self, branch: str) -> str:
        said = git(self.remote, "for-each-ref", "--format=%(objectname)", f"refs/heads/{branch}")
        return said or self.prs[next(n for n, p in self.prs.items() if p["branch"] == branch)]["head"]

    def read_pull_request(self, repository: str, number: int) -> PullRequest:
        p = self.prs[number]
        if not p["merged"]:
            p["head"] = self._head(p["branch"])
        return PullRequest(
            repository=repository, number=number, node_id=f"N{number}", url=f"https://github.com/{repository}/pull/{number}",
            head_branch=p["branch"], head_sha=p["head"], base_branch="main", draft=p["draft"], state=p["state"],
            merged=p["merged"], merge_state="behind" if self.behind else "clean", merge_commit_sha=p["sha"] or None,
        )  # fmt: skip

    def find_pull_request(self, repository: str, head: str, base: str) -> PullRequest | None:
        found = [n for n, p in self.prs.items() if p["branch"] == head and p["state"] == "open" and base == "main"]
        return self.read_pull_request(repository, found[0]) if found else None

    def create_pull_request(self, repository: str, head: str, base: str, title: str, body: str) -> PullRequest:
        self.calls.append("create")
        number = len(self.prs) + 1
        self.prs[number] = {"branch": head, "head": "", "title": title, "body": body, "draft": True, "state": "open",
                            "merged": False, "sha": "", "labels": []}  # fmt: skip
        assert base == "main"
        if self.lose_create:
            self.lose_create = False
            raise ProviderError(FailureCode.RESPONSE_UNKNOWN, "create_pull_request", "timed out", retry_safe=False)
        return self.read_pull_request(repository, number)

    def mark_ready(self, pr: PullRequest) -> None:
        self.prs[pr.number]["draft"] = False

    def add_labels(self, _repository: str, number: int, labels: list[str]) -> None:
        if self.labels_fail:
            raise ProviderError(FailureCode.INVALID_RESPONSE, "add_labels", "no such label", retry_safe=False)
        self.prs[number]["labels"] += labels

    def read_rules(self, _repository: str, branch: str) -> Rules:
        assert branch == "main"
        return Rules(state="known", evidence="rules", required_checks=("CI",))

    def observe_checks(self, _repository: str, _number: int, _head: str) -> tuple[Check, ...]:
        said = self.checks.pop(0) if len(self.checks) > 1 else self.checks[0]
        status = "in_progress" if said == "running" else "completed"
        return (Check(name="CI", status=status, conclusion=None if said == "running" else said),)

    def update_branch(self, _repository: str, number: int, expected_head: str) -> bool:
        self.calls.append("update-branch")
        self.behind -= 1
        self._merge(self.prs[number]["branch"], into=self.prs[number]["branch"], source="main", at=expected_head)
        return True

    def request_merge(self, request: MergeRequest) -> MergeResult:
        self.calls.append("merge")
        p = self.prs[request.number]
        if self.refusal:
            return MergeResult(status=MergeStatus.REFUSED, refusal=self.refusal, message="refused")
        assert (request.method, request.expected_head_sha) == (MergeMethod.MERGE, self._head(p["branch"]))
        p["sha"] = self._merge(p["branch"], into="main", source=p["branch"])
        p["merged"], p["state"] = True, "closed"
        return MergeResult(status=MergeStatus.MERGED, sha=p["sha"])

    def delete_branch(self, _repository: str, branch: str) -> None:
        self.calls.append("delete")
        git(self.remote, "update-ref", "-d", f"refs/heads/{branch}")

    def _merge(self, _branch: str, *, into: str, source: str, at: str = "") -> str:
        work = self.remote.parent / "merge-work"
        shutil.rmtree(work, ignore_errors=True)
        git(self.remote.parent, "clone", "-q", str(self.remote), str(work))
        for key, value in (("user.name", "gh"), ("user.email", "gh@example.com")):
            git(work, "config", key, value)
        git(work, "checkout", "-q", into)
        assert not at or git(work, "rev-parse", "HEAD") == at
        git(work, "merge", "-q", "--no-ff", "-m", f"Merge {source} into {into}", f"origin/{source}")
        git(work, "push", "-q", "origin", into)
        return git(work, "rev-parse", "HEAD")


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    done = subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """Delivery's package inside a git checkout of main whose origin names OwlBear's repository, a local bare one."""
    remote, root = tmp_path / "remote.git", tmp_path / "checkout"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(root))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com"), (f"url.{remote}.insteadOf", GITHUB_URL)):
        git(root, "config", key, value)
    git(root, "remote", "set-url", "origin", GITHUB_URL)
    package = root / "src" / "pkg"
    (package / "skills").mkdir(parents=True)
    shutil.copy(str(PKG.joinpath("design_pack.json")), package / "design_pack.json")
    for name in ("NOTICE.md", "IMPECCABLE-LICENSE", *(f"{s}/SKILL.md" for s in OLD["skills"])):
        (package / "skills" / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(PKG.joinpath("skills", name)), package / "skills" / name)
    for name in ("golden/expected.json", "golden/good.html", "golden/bad.html", *pack_gates.GLUE.values()):
        (package / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(PKG.joinpath(name)), package / name)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "start")
    git(root, "push", "-q", "-u", "origin", "main")
    return package


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """Upstream with the pinned tag and one newer skill release: a new rule, skill text and engine version."""
    root = tmp_path / "impeccable"
    git(tmp_path, "init", "-q", "-b", "main", str(root))
    licence = PKG.joinpath("skills", "IMPECCABLE-LICENSE").read_bytes()
    for tag, rules, engine in (
        ("skill-v4.5.2", ["side-tab"], "0.1.14"),
        ("skill-v4.6.0", ["side-tab", "glow"], "0.2.0"),
    ):
        entries = "".join(
            f'    Antipattern {{\n        id: "{r}",\n        name: "{r.title()}",\n        description: "d",\n'
            "    },\n"
            for r in rules
        )
        for path, data in (
            (pack_update.REGISTRY, f"pub static ANTIPATTERNS: &[Antipattern] = &[\n{entries}];\n".encode()),
            ("skill/SKILL.md", f"# Impeccable {tag}\n".encode()),
            ("ENGINE_VERSION", f"{engine}\n".encode()),
            ("LICENSE", licence),
            (BUNDLE, f"bundle {tag}".encode()),
        ):
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_bytes(data)
        git(root, "add", "-A")
        git(root, "commit", "-qm", tag)
        git(root, "tag", tag)
    return root


def engine(platform: str) -> bytes:
    return f"engine 0.2.0 {platform}".encode()


class Fakes:
    """Each live part, recording the order it was called in."""

    def __init__(self, clone: Path, *, wrong: dict | None = None, replay_ok: bool = True, verdict: str = "pass"):
        self.calls, self.sessions, self.updates, self.clone = [], [], [], clone
        self.wrong, self.replay_ok, self.verdict = wrong or {}, replay_ok, verdict
        self.wrong_after: dict = {}  # the golden check on the candidate's own pages, after each updater session
        self.folders: list[Path | None] = []  # the golden folder of each check: None for the package's
        self.needed: dict[str, str] = {}  # the full rounds' judgement of a changed file; yes for the rest
        self.evidence = ""  # the updater's reason for changed golden evidence
        self.verdicts: list[str] = []  # per challenger round; then `verdict`
        self.edits: list[dict[str, str]] = []  # per updater round: worktree path -> new text
        self.rejects: list[list[str]] = []  # per updater round: finding keys it rejects
        self.upheld, self.premise, self.confirmed = False, False, True
        self.found, self.reconsider = 1, "withdrawn"  # findings per fix verdict; a reconsideration's verdict
        self.replays: list[tuple[str, str]] = []  # what each replay judged: the pack identity and the edited skill
        self.during = lambda: None  # something else that happens while the challenger runs
        self.at_golden = lambda: None  # something else that happens while the golden pages run
        self.hold: threading.Event | None = None
        self.waiting = threading.Event()
        self.tags = ["skill-v4.5.2", "skill-v4.6.0"]

    def releases(self, url: str) -> bytes:
        self.calls.append("releases")
        assert url == pack_update.RELEASES.format(repo="pbakaus/impeccable")
        return json.dumps([{"tag_name": t} for t in self.tags]).encode()

    def sync(self, clone: Path, repository: str) -> None:
        self.calls.append("sync")
        assert (clone, repository) == (self.clone, "pbakaus/impeccable")

    def download(self, url: str) -> bytes:
        platform = url.removesuffix(".sha256").rsplit("impeccable-", 1)[1]
        assert "/engine-v0.2.0/" in url, url
        if url.endswith(".sha256"):
            return f"{hashlib.sha256(engine(platform)).hexdigest()}  impeccable-{platform}\n".encode()
        self.calls.append(f"engine {platform}")
        return engine(platform)

    def golden(self, installed: design_pack.Installed, folder: Path | None = None) -> dict:
        self.calls.append("golden")
        self.folders.append(folder)
        assert installed.bundle == "bundle skill-v4.6.0"  # the candidate's detector, not the active one
        self.at_golden()
        return self.wrong if folder is None else self.wrong_after

    def replay(self, _store: Store, candidate) -> calibration.Replay:
        self.calls.append("replay")
        self.replayed = candidate
        skill = (candidate.skills / "owlbear-design-review" / "SKILL.md").read_text()
        self.replays.append((design_pack.identity(candidate.manifest, candidate.skills), skill))
        return calibration.Replay(40, 40, 40 if self.replay_ok else 0)

    def challenge(self, _store: Store, cfg) -> Run:
        self.calls.append("challenger")
        self.sessions.append(cfg)
        self.during()
        if self.hold:
            self.waiting.set()
            self.hold.wait(10)
        done = Termination(confirmed=self.confirmed)
        if cfg.submit is dispute_tools.SUBMIT:
            said = [{"finding": k, "verdict": self.reconsider, "text": "narrower - fix: g", "reason": "r"}
                    for k in cfg.rechecks]  # fmt: skip
            return Run(
                cfg.session_id, "result", payload=dispute_tools.ReconsiderResult(reconsidered=said), termination=done
            )
        verdict = self.verdicts.pop(0) if self.verdicts else self.verdict
        problems = ["p", *(f"p{i}" for i in range(2, self.found + 1))]
        findings = (
            []
            if verdict == "pass"
            else [tools.Finding(place="owlbear-design-review", problem=p, fix="f") for p in problems]
        )
        rechecked = [{"finding": k, "upheld": self.upheld, "reason": "r"} for k in cfg.rechecks]
        if cfg.submit is pack_tools.REVIEW:  # a full round judges each changed file (TD-194)
            changes = [{"path": p, "needed": self.needed.get(p, "yes"), "what": f"w {p}", "suspicious": "s"}
                       for p in cfg.changed]  # fmt: skip
            result = pack_tools.PackReview(verdict=verdict, findings=findings, rechecked=rechecked, changes=changes)
        else:
            result = tools.ReviewResult(verdict=verdict, findings=findings, rechecked=rechecked)
        return Run(cfg.session_id, "result", payload=result, termination=done)

    def update(self, _store: Store, cfg) -> Run:
        """The writing updater: each planned edit lands in its worktree, then it submits (or reports a premise)."""
        self.calls.append("update")
        self.updates.append(cfg)
        edit = self.edits.pop(0) if self.edits else {}
        for path, text in edit.items():
            if isinstance(text, Path):  # a link the updater made
                (cfg.worktree / path).symlink_to(text)
            elif text is None:
                (cfg.worktree / path).unlink()
            else:
                (cfg.worktree / path).parent.mkdir(parents=True, exist_ok=True)
                (cfg.worktree / path).write_text(text)
        if self.premise:
            premise = tools.WrongPremise(stage="brief", reason="golden page glow.html must change", evidence=["g"])
            return Run(cfg.session_id, "premise", payload=premise, termination=Termination(confirmed=True))
        reject = [{"finding": k, "reason": "it already holds"} for k in (self.rejects.pop(0) if self.rejects else [])]
        result = pack_updater.UpdateResult(
            summary=f"round {len(self.updates)}", rejected=reject, evidence=self.evidence
        )
        return Run(cfg.session_id, "result", payload=result, termination=Termination(confirmed=True))

    def live(self, package: Path) -> pack_job.Live:
        self.github = getattr(self, "github", None) or FakeGitHub(package.parents[2] / "remote.git")
        return pack_job.Live(
            package=package, clone=self.clone, releases=self.releases, sync=self.sync, download=self.download,
            golden=self.golden, replay=self.replay, challenge=self.challenge, update=self.update, github=self.github,
            sleep=lambda _s: None, poll=1.0, ci_wait=5.0,
        )  # fmt: skip


def run(job: pack_job.Job) -> dict:
    job.start()
    return settled(job)


def settled(job: pack_job.Job) -> dict:
    assert job.thread is not None
    job.thread.join(30)
    return job.read()


def rounds(store: Store, **values: int) -> Store:
    """The project's settings give the updater's loops these round values (TD-209)."""
    store.root.mkdir(parents=True, exist_ok=True)
    (store.root / "config.json").write_text(json.dumps({"format": 4, "agents": {"updater": values}}))
    return store


def answered(job: pack_job.Job, option: str, note: str = "", at: int = 0) -> dict:
    """Answer the waiting run's *at*-th question; when that resumes it, wait for it to settle again."""
    q = job.read()["questions"][at]
    state = job.answer(q["id"], option, note)
    return settled(job) if state["state"] == "running" else state


def snapshot(package: Path) -> tuple[bytes, bytes, str, str]:
    root = package.parents[1]
    notice = (package / "skills" / "NOTICE.md").read_bytes()
    remote = git(root, "ls-remote", "origin", "refs/heads/main").split()[0]
    return (package / "design_pack.json").read_bytes(), notice, git(root, "rev-parse", "HEAD"), remote


def results(state: dict) -> dict[str, str]:
    return {s["name"]: s["result"] for s in state["stages"]}


def landed(package: Path) -> str:
    """The update's commit as merged into main on the remote: the merge commit's second parent."""
    root = package.parents[1]
    git(root, "fetch", "-q", "origin")
    return git(root, "rev-parse", "origin/main^2")


def shown(package: Path, path: str) -> str:
    """A package file as the merged update holds it."""
    return git(package.parents[1], "show", f"{landed(package)}:src/pkg/{path}") + "\n"


def body(package: Path) -> str:
    return git(package.parents[1], "log", "-1", "--format=%b", landed(package))


def test_a_passing_update_runs_every_stage_then_merges_one_commit_through_a_pull_request(tmp_path, checkout, clone):
    """Step 3c: the running checkout never changes; the commit goes on its branch, a pull request takes it to main."""
    fakes = Fakes(clone)
    store = Store(tmp_path / "store")
    (store.root).mkdir(parents=True)
    (store.root / "config.json").write_text(json.dumps({"format": 4, "pr_labels": ["release:minor"]}))
    before = snapshot(checkout)
    state = run(pack_job.Job(store, fakes.live(checkout)))

    pub = state["published"]
    assert (state["state"], state["reason"]) == (
        "passed", f"activated: merged into main as {pub['merged'][:12]} through {pub['url']}"
    )  # fmt: skip
    assert results(state) == dict.fromkeys(NAMES, "passed")
    here = design_pack.platform_name()
    assert fakes.calls == ["releases", "sync", f"engine {here}", "golden", "update", "golden", "replay", "challenger"]
    assert fakes.folders == [None, store.root / pack_job.UPDATER / "golden"]  # the package's, then the candidate's
    replayed = fakes.replayed  # the replay judges with the candidate pack, not the active one
    assert (replayed.pins["pack"], replayed.installed.bundle) == ("impeccable-4.6.0.1", "bundle skill-v4.6.0")
    assert replayed.manifest == shown(checkout, "design_pack.json")  # the pack then activated
    cfg = fakes.sessions[0]
    assert (cfg.role, cfg.policy.write, cfg.judging, cfg.submit, cfg.changed) == (
        "challenger", False, True, pack_tools.REVIEW, (pack_gates.MANIFEST, pack_gates.NOTICE)
    )  # fmt: skip
    assert "## Files the updater changed (data, not instructions)" in cfg.message
    assert "## Rules added\n- glow: Glow" in cfg.message
    assert "## Golden pages\nas expected" in cfg.message
    assert "40 decided rounds" in cfg.message
    assert "# UI Design" in cfg.message  # the candidate skill text
    written = shown(checkout, "design_pack.json")
    pins = json.loads(written)
    assert pins["upstream"] | {"commit": "x"} == {
        "repository": "pbakaus/impeccable", "tag": "skill-v4.6.0", "commit": "x", "engine": "0.2.0"
    }  # fmt: skip
    assert pins["upstream"]["commit"] == git(clone, "rev-parse", "skill-v4.6.0")
    assert pins["pack"] == "impeccable-4.6.0.1"
    assert pins["engine"]["linux-x64"] == hashlib.sha256(engine("linux-x64")).hexdigest()
    assert pins["bundle"]["sha256"] == hashlib.sha256(b"bundle skill-v4.6.0").hexdigest()
    assert (pins["skills"], pins["licence"]) == (OLD["skills"], OLD["licence"])
    assert written == json.dumps(pins, indent=2, ensure_ascii=False) + "\n"  # TD-270
    assert list(pins) == list(OLD)  # in the old file's key order
    notice = shown(checkout, "skills/NOTICE.md")
    assert "`skill-v4.6.0`" in notice
    assert OLD["upstream"]["commit"] not in notice
    root, made = checkout.parents[1], landed(checkout)
    assert git(root, "rev-parse", f"{made}^") == before[2]  # on the base pinned when the candidate was made
    assert git(root, "show", "--name-only", "--format=%s", made).splitlines() == [
        "design pack: impeccable-4.5.2.1 to impeccable-4.6.0.1 (upstream skill-v4.5.2 to skill-v4.6.0)",
        "",
        "src/pkg/design_pack.json",
        "src/pkg/skills/NOTICE.md",
    ]
    (pr,) = fakes.github.prs.values()
    assert (pr["branch"], pr["draft"], pr["labels"], pr["title"]) == (
        pub["branch"], False, ["release:minor"],
        "design pack: impeccable-4.5.2.1 to impeccable-4.6.0.1 (upstream skill-v4.5.2 to skill-v4.6.0)"
    )  # fmt: skip
    assert pr["body"].endswith(pack_publish.MARKER)
    assert "The challenger passed." in pr["body"]
    assert pub == {"repository": "maba-pag/owlbear", "base": before[2], "branch": pr["branch"], "commit": made,
                   "number": 1, "url": "https://github.com/maba-pag/owlbear/pull/1", "merged": pr["sha"]}  # fmt: skip
    assert pub["branch"].startswith("pack/")
    assert fakes.github.calls == ["create", "merge", "delete"]
    assert git(root, "ls-remote", "origin", f"refs/heads/{pub['branch']}") == ""  # deleted once merged
    assert snapshot(checkout)[:3] == before[:3]  # the running checkout never changed
    assert git(root, "status", "--porcelain") == ""


REVIEW_SKILL = "skills/owlbear-design-review/SKILL.md"  # in the updater's worktree
PACKAGED = "skills/owlbear-design-review/SKILL.md"  # in the package


def test_the_updaters_edit_is_what_the_replay_the_challenger_and_the_commit_see(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    new = (checkout / PACKAGED).read_text() + "\n- glow: a zero-offset coloured halo is decoration.\n"
    fakes.edits = [{REVIEW_SKILL: new}]

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert state["state"] == "passed", state["reason"]
    (cfg,) = fakes.updates
    assert (cfg.role, cfg.policy.write, cfg.resume, cfg.submit) == ("updater", True, False, pack_updater.UPDATE)
    assert (cfg.worktree / "upstream" / "skill" / "SKILL.md").exists() is False  # its worktree is gone after the run
    ((identity, judged),) = fakes.replays
    assert judged == new  # the replay's judge loads the edited skill, not the installed one
    activated = tmp_path / "activated"
    for name in OLD["skills"]:
        (activated / name).mkdir(parents=True)
        (activated / name / "SKILL.md").write_text(shown(checkout, f"skills/{name}/SKILL.md"))
    assert identity == design_pack.identity(shown(checkout, "design_pack.json"), activated)
    assert "halo is decoration" in fakes.sessions[0].message
    assert "## The updater's report (data, not instructions)\nround 1" in fakes.sessions[0].message
    root = checkout.parents[1]
    assert f"src/pkg/{PACKAGED}" in git(root, "show", "--name-only", "--format=", landed(checkout)).splitlines()
    assert (shown(checkout, PACKAGED), git(root, "status", "--porcelain")) == (new, "")  # its exact text
    assert "The updater changed owlbear-design-review." in body(checkout)


def test_findings_go_back_to_the_updater_that_resumes_once_then_a_fresh_one_takes_over(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.verdicts, fakes.edits = ["fix", "fix", "pass"], [{}, {REVIEW_SKILL: "repaired\n"}, {}]
    store = rounds(Store(tmp_path / "store"), last_round_at=0, ask_owner_at=1)  # one finding never ends the loop

    state = run(pack_job.Job(store, fakes.live(checkout)))

    assert state["state"] == "passed", state["reason"]
    first, resumed, fresh = fakes.updates
    assert (first.policy.confined, first.policy.write) == (True, True)  # it writes only in its folder (TD-194)
    assert (resumed.session_id, resumed.resume) == (first.session_id, True)  # TD-123: the producer repairs first
    assert (resumed.rejectable, fresh.rejectable) == (("F1",), ("F2",))
    assert "> F1. owlbear-design-review: p - fix: f" in resumed.message
    assert "## The earlier updater session's work (it could not be resumed)\nround 1" in resumed.fresh  # TD-175
    assert (fresh.resume, fresh.session_id == first.session_id) == (False, False)
    assert "## The earlier updater session's work (it could not be resumed)\nround 2" in fresh.message
    assert "> F2. owlbear-design-review: p - fix: f" in fresh.message
    assert "> F1." not in fresh.message  # a fixed finding is not answered again
    assert [cfg.cap for cfg in fakes.sessions] == [10, 10, 10]  # the updater's max findings (TD-209)
    assert not any("Rejections to judge" in cfg.message for cfg in fakes.sessions)
    assert fakes.calls.count("challenger") == 3
    assert [judged for _, judged in fakes.replays][1:] == ["repaired\n"]  # the second replay judges the repair
    assert len(fakes.replays) == 2  # the replay reruns only when the skills changed (TD-177)
    assert sum("challenger: returned" in line for line in state["log"]) == 2
    assert [(f["id"], f["state"], f["repair"]) for f in state["loop"]["findings"]] == [
        ("F1", "fixed", "r1"), ("F2", "fixed", "r2")
    ]  # fmt: skip
    assert "Challenge rounds: 3." in body(checkout)


def test_an_accepted_rejection_is_judged_alone_and_the_unchanged_candidate_activates(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.verdicts, fakes.rejects = ["fix"], [[], ["F1"]]

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    check = fakes.sessions[1]  # a last round's rejections, judged alone (TD-330)
    assert (check.rechecks, check.cap) == (("F1",), 0)
    assert "- F1: owlbear-design-review: p - fix: f\n  The updater's reason: it already holds" in check.message
    assert "Judge only these rejections" in check.message
    assert state["state"] == "passed", state["reason"]
    said = body(checkout)
    assert "F1 rejected; the challenger accepted that (updater: it already holds)" in said
    assert "The challenger passed." in said


def test_a_fix_beside_an_accepted_rejection_still_waits_for_the_owner(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.verdicts, fakes.found, fakes.rejects = ["fix"], 2, [[], ["F2"]]
    fakes.edits = [{}, {REVIEW_SKILL: "fixed F1\n"}]
    before = snapshot(checkout)

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert fakes.sessions[1].rechecks == ("F2",)  # the check judged the rejection, never the fix beside it
    assert state["state"] == "waiting"
    assert "The updater's last repair (r1) was not reviewed by a challenger." in state["questions"][0]["text"]
    assert snapshot(checkout) == before


def test_an_unchanged_resubmission_is_no_repair_but_still_ends_without_a_pass(tmp_path, checkout, clone):
    fakes = Fakes(clone, verdict="fix")

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert state["state"] == "waiting"
    assert "The candidate is what the last round judged." in state["questions"][0]["text"]
    assert state["loop"]["unreviewed"] == []


def test_a_waiting_run_whose_candidate_is_no_longer_installed_stops(tmp_path, checkout, clone):
    fakes = Fakes(clone, verdict="fix")
    fakes.edits = [{}, {REVIEW_SKILL: "repaired\n"}]
    before = snapshot(checkout)
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))
    run(job)
    shutil.rmtree(design_pack.folder({"pack": "impeccable-4.6.0.1"}))

    state = answered(job, "activate")

    assert state["state"] == "failed"
    assert "impeccable-4.6.0.1 is no longer installed on this machine" in state["reason"]
    assert snapshot(checkout) == before


def upheld(tmp_path: Path, checkout: Path, clone: Path) -> tuple[pack_job.Job, Fakes, dict]:
    """A run waiting for the owner: the updater rejected F1 and the rejections-only check upheld it."""
    fakes = Fakes(clone)
    fakes.verdicts, fakes.rejects, fakes.upheld = ["fix"], [[], ["F1"]], True
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))
    return job, fakes, run(job)


def test_a_rejection_the_challenger_upholds_waits_for_the_owner_who_drops_it(tmp_path, checkout, clone):
    before = snapshot(checkout)
    job, fakes, state = upheld(tmp_path, checkout, clone)

    assert (state["state"], results(state)["challenger"]) == ("waiting", "waiting")
    (q,) = state["questions"]
    assert (q["kind"], q["finding"], [o["id"] for o in q["options"]]) == (
        "dispute",
        "F1",
        ["fix", "reconsider", "drop"],
    )
    assert "Updater: it already holds Challenger: r" in q["text"]
    assert "context" not in state  # the page never gets the run's context
    assert snapshot(checkout) == before

    state = answered(job, "drop", "upstream says so")

    assert state["state"] == "passed", state["reason"]
    assert len(fakes.updates) == 2  # nothing left to fix: no updater session
    assert "F1 you dropped it" in body(checkout)


def test_the_owners_fix_goes_to_the_updater_and_its_unreviewed_repair_waits_for_activation(tmp_path, checkout, clone):
    job, fakes, _ = upheld(tmp_path, checkout, clone)
    fakes.edits = [{REVIEW_SKILL: "fixed as you said\n"}]
    before = snapshot(checkout)

    state = answered(job, "fix", "use the halo rule")

    cfg = fakes.updates[-1]
    assert "> F1. owlbear-design-review: p - fix: f [the owner's]" in cfg.message
    assert "> F1: use the halo rule" in cfg.message
    assert (cfg.rejectable, cfg.settled) == ((), ("F1",))  # the owner's finding is never rejected
    assert state["state"] == "waiting"  # TD-256: the last repair is unreviewed
    (q,) = state["questions"]
    assert (q["kind"], [o["id"] for o in q["options"]]) == ("end", ["activate", "discard"])
    assert "The updater's last repair (r1) was not reviewed by a challenger." in q["text"]  # after round 1 (TD-330)
    assert snapshot(checkout) == before

    state = answered(job, "activate")

    pub = state["published"]
    assert (state["state"], state["reason"]) == (
        "passed",
        f"activated by you after rounds without a pass: merged into main as {pub['merged'][:12]} through {pub['url']}",
    )
    assert shown(checkout, PACKAGED) == "fixed as you said\n"
    said = body(checkout)
    assert "the owner activated it; its last repair (r1) was not reviewed (TD-256)" in said
    assert "The challenger passed." not in said


@pytest.mark.parametrize(
    ("verdict", "ends"), [("withdrawn", "passed"), ("unsure", "waiting"), ("clarified", "waiting")]
)
def test_a_reconsideration_needs_the_owners_note_and_a_fresh_challenger_settles_it(
    tmp_path, checkout, clone, verdict, ends
):
    job, fakes, state = upheld(tmp_path, checkout, clone)
    fakes.reconsider = verdict
    with pytest.raises(pack_job.Refused, match="needs your note"):
        job.answer(state["questions"][0]["id"], "reconsider", " ")

    state = answered(job, "reconsider", "the halo is upstream's own example")

    cfg = fakes.sessions[-1]
    assert (cfg.submit, cfg.rechecks, cfg.session_id.startswith("pack-reconsider-")) == (
        dispute_tools.SUBMIT, ("F1",), True
    )  # fmt: skip
    assert "The owner's note: the halo is upstream's own example" in cfg.message
    assert "Earlier recheck: r" in cfg.message
    assert state["state"] == ends, state["reason"]
    if verdict == "unsure":  # asked again, without a second reconsideration (TD-193: once per finding)
        assert [o["id"] for o in state["questions"][0]["options"]] == ["fix", "drop"]
    if verdict == "clarified":  # the narrower finding is the owner's for the updater
        assert "> F1. narrower - fix: g [the owner's]" in fakes.updates[-1].message
        assert state["questions"][0]["kind"] == "end"


def test_rounds_ending_without_a_pass_wait_and_a_discard_changes_nothing(tmp_path, checkout, clone):
    fakes, store = Fakes(clone, verdict="fix"), Store(tmp_path / "store")
    fakes.edits = [{}, {REVIEW_SKILL: "repaired\n"}]
    before = snapshot(checkout)
    job = pack_job.Job(store, fakes.live(checkout))

    state = run(job)

    assert (state["state"], fakes.calls.count("challenger")) == ("waiting", 1)  # 1 finding: the last round (TD-208)
    assert results(state)["challenger"] == "waiting"
    assert [o["id"] for o in state["questions"][0]["options"]] == ["activate", "discard"]
    assert (store.root / "design-pack-updater").is_dir()
    with pytest.raises(pack_job.Busy, match="waits for your answers"):
        job.start()

    state = answered(job, "discard")

    assert (state["state"], state["reason"]) == ("discarded", "discarded by you; nothing changed")
    assert (state["questions"], snapshot(checkout)) == ([], before)
    assert not (store.root / "design-pack-updater").exists()
    assert results(state)["commit"] == "skipped"


def test_activation_publishes_only_the_candidate_the_owner_was_asked_about(tmp_path, checkout, clone):
    fakes, store = Fakes(clone, verdict="fix"), Store(tmp_path / "store")
    fakes.edits = [{}, {REVIEW_SKILL: "repaired\n"}]
    before = snapshot(checkout)
    job = pack_job.Job(store, fakes.live(checkout))
    run(job)
    (store.root / pack_job.CANDIDATE / "owlbear-design-review" / "SKILL.md").write_text("slipped in\n")

    state = answered(job, "activate")

    assert (state["state"], results(state)["commit"]) == ("failed", "skipped")
    assert "is not what the challenger passed or you accepted" in state["reason"]
    assert snapshot(checkout) == before


def test_many_findings_in_the_last_allowed_round_offer_another_round(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.verdicts, fakes.edits = ["fix", "pass"], [{}, {REVIEW_SKILL: "repaired\n"}]
    store = rounds(Store(tmp_path / "store"), max_rounds=1, last_round_at=0, ask_owner_at=1)
    job = pack_job.Job(store, fakes.live(checkout))

    state = run(job)

    assert [o["id"] for o in state["questions"][0]["options"]] == ["another", "activate", "discard"]
    state = answered(job, "another")

    assert state["state"] == "passed", state["reason"]
    assert fakes.calls.count("challenger") == 2  # the extra round reviewed the repair: no question at its end
    assert "The challenger passed." in body(checkout)


def test_few_findings_in_the_last_allowed_round_offer_no_other_round(tmp_path, checkout, clone):
    fakes = Fakes(clone, verdict="fix")
    fakes.edits = [{}, {REVIEW_SKILL: "repaired\n"}]
    store = rounds(Store(tmp_path / "store"), max_rounds=1)  # 1 finding, below `ask owner at` 7

    state = run(pack_job.Job(store, fakes.live(checkout)))

    assert [o["id"] for o in state["questions"][0]["options"]] == ["activate", "discard"]


def test_the_owners_fix_is_fixed_even_if_the_updater_lists_it_as_rejected():
    found = [
        RoundFinding(id="F1", text="a", raised=1, state="owner-fix"),
        RoundFinding(id="F2", text="b", raised=1),
    ]
    lp = RoundLoop(subject="pack", policy=RoundPolicy(), round=1, found=2, last=False, findings=found)

    assert pack_rounds.revised(lp, {"F1": "no", "F2": "no"}, "x") == "challenge"
    assert [(f.id, f.state) for f in lp.findings] == [("F1", "fixed"), ("F2", "rejected")]


def test_a_waiting_run_survives_a_host_restart_and_goes_on_from_its_answer(tmp_path, checkout, clone):
    store = Store(tmp_path / "store")
    fakes = Fakes(clone, verdict="fix")
    fakes.edits = [{}, {REVIEW_SKILL: "repaired\n"}]
    waiting = run(pack_job.Job(store, fakes.live(checkout)))

    again = pack_job.Job(store, fakes.live(checkout))

    assert again.read() == waiting
    assert answered(again, "activate")["state"] == "passed"
    assert shown(checkout, PACKAGED) == "repaired\n"


def test_a_skill_restored_to_its_start_replaces_the_earlier_edit_in_the_candidate(tmp_path, checkout, clone):
    fakes, original = Fakes(clone), (checkout / PACKAGED).read_text()
    fakes.verdicts, fakes.edits = ["fix", "pass"], [{REVIEW_SKILL: "an edit\n"}, {REVIEW_SKILL: original}]
    store = rounds(Store(tmp_path / "store"), last_round_at=0, ask_owner_at=1)

    state = run(pack_job.Job(store, fakes.live(checkout)))

    assert state["state"] == "passed", state["reason"]
    assert (checkout / PACKAGED).read_text() == original
    assert "The updater changed nothing." in body(checkout)


def test_a_challenger_judges_open_rejections_and_sees_what_the_owner_dropped():
    found = [
        RoundFinding(id="F1", text="a: b - fix: c", raised=1, state="rejected", reason="it holds"),
        RoundFinding(id="F2", text="d: e - fix: f", raised=1, state="owner-drop", note="upstream's choice"),
        RoundFinding(id="F3", text="g: h - fix: i", raised=1, state="fixed", repair="r1"),
    ]
    lp = RoundLoop(subject="pack", policy=RoundPolicy(), round=1, findings=found)

    full, check = pack_rounds.challenge_lines(lp, recheck=False), pack_rounds.challenge_lines(lp, recheck=True)

    assert full[:4] == ["", "## Rejections to judge", pack_rounds.RECHECK, "- F1: a: b - fix: c"]
    assert "  The updater's reason: it holds" in full
    assert pack_rounds.ONLY in check
    assert pack_rounds.ONLY not in full
    assert "- F2: d: e - fix: f The owner's reason: upstream's choice" in full  # TD-193: raised again only anew
    assert not any("F3" in line for line in full)  # a fixed finding never reaches the challenger


def test_the_updaters_rejections_are_checked_at_its_result_tool():
    def errors(rejected: list[str], allowed: tuple[str, ...], settled: tuple[str, ...] = ()) -> list[str]:
        said = pack_updater.UpdateResult(summary="s", rejected=[{"finding": k, "reason": "r"} for k in rejected])
        return disputes.check(said, tools.Worktree("", ""), allowed, (), settled=settled)

    assert errors(["F1"], ("F1", "F2")) == []
    assert errors(["F9"], ("F1",)) == ["rejected: F9 is no finding key of this task - use F1"]
    assert errors(["F1", "F1"], ("F1",)) == ["rejected: F1 listed twice - one entry per finding"]
    assert "is the owner's decision" in errors(["F2"], ("F1",), ("F2",))[0]


def test_a_premise_the_updater_reports_stops_for_the_owner(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.premise = True
    before = snapshot(checkout)

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert (state["state"], results(state)["update"]) == ("failed", "failed")
    assert "the updater asks the owner: golden page glow.html must change (g)" in state["reason"]
    assert "challenger" not in fakes.calls
    assert snapshot(checkout) == before


@pytest.mark.parametrize(
    "edit",
    [
        {"upstream/skill/SKILL.md": "mine"},
        {"notes.md": "mine"},
        {"golden/deep/page.html": "mine"},
        {"code/other.py": "mine"},
    ],
)
def test_an_edit_beyond_the_pack_asks_the_owner_and_an_undo_restores_it_for_a_repair(tmp_path, checkout, clone, edit):
    """TD-194: only the pack's files may change; the owner has the rest undone (Delivery restores it) or discards."""
    fakes = Fakes(clone)
    fakes.edits = [edit]
    before = snapshot(checkout)
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))

    state = run(job)

    assert (state["state"], results(state)["update"]) == ("waiting", "waiting")
    (q,) = state["questions"]
    (path,) = edit
    assert (q["kind"], q["bad"], [o["id"] for o in q["options"]]) == ("scope", [path], ["undo", "discard"])
    assert "challenger" not in fakes.calls
    state = answered(job, "undo")
    assert state["state"] == "passed", state["reason"]
    second = fakes.updates[1].message
    assert f"{path}: Delivery restored the package's version" in second  # the owner's finding, never rejectable
    assert fakes.updates[1].settled == ("F1",)
    assert snapshot(checkout)[:3] == before[:3]


WRONG = {"bad.html (source)": {"missing": ["glow"], "unexpected": []}}
EXPECTED = "golden/expected.json"


def test_golden_pages_that_differ_go_to_the_updater_and_still_differing_after_its_session_stops(
    tmp_path, checkout, clone
):
    """TD-177: the first golden mismatch is the updater's evidence; on its candidate the check must hold."""
    fakes = Fakes(clone, wrong=WRONG)
    fakes.wrong_after = WRONG
    before = snapshot(checkout)

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert (state["state"], results(state)["golden"], results(state)["update"]) == ("failed", "failed", "passed")
    assert "golden pages differ: bad.html (source): missing glow" in state["reason"]
    assert "## Golden pages with the package's expectations\ngolden pages differ" in fakes.updates[0].message
    assert fakes.calls[-2:] == ["update", "golden"]
    assert snapshot(checkout) == before


def changed_expectations(checkout: Path) -> str:
    kept = json.loads((checkout / EXPECTED).read_text())
    kept["source"]["bad.html"] = [*kept["source"]["bad.html"], "glow"]
    return json.dumps(kept, indent=2) + "\n"


def test_changed_evidence_waits_for_the_owner_and_once_accepted_lands_with_the_pack(tmp_path, checkout, clone):
    """TD-177: a golden change is asked about with its diff before the replay; accepted, it is published."""
    fakes = Fakes(clone, wrong=WRONG)
    new = changed_expectations(checkout)
    fakes.edits, fakes.evidence = [{EXPECTED: new, "golden/glow.html": "<div>glow</div>\n"}], "glow is a new rule"
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))

    state = run(job)

    assert (state["state"], results(state)["golden"]) == ("waiting", "waiting")
    (q,) = state["questions"]
    assert (q["kind"], [o["id"] for o in q["options"]]) == ("evidence", ["accept", "undo", "discard"])
    assert "Its reason: glow is a new rule." in q["text"]
    assert any(line.startswith("+ ") and '"glow"' in line for line in q["diff"].splitlines())
    assert "+++ candidate/golden/glow.html" in q["diff"]
    assert "replay" not in fakes.calls
    state = answered(job, "accept")
    assert state["state"] == "passed", state["reason"]
    assert fakes.sessions[0].changed == (pack_gates.MANIFEST, pack_gates.NOTICE, EXPECTED, "golden/glow.html")
    assert shown(checkout, EXPECTED) == new
    assert shown(checkout, "golden/glow.html") == "<div>glow</div>\n"
    assert "You accepted the changed golden evidence." in body(checkout)
    assert f"- {EXPECTED}: needed yes; w {EXPECTED}; suspicious: s" in body(checkout)


def test_changed_evidence_the_owner_has_undone_is_restored_and_repaired_without_a_round(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.edits = [{EXPECTED: changed_expectations(checkout), "golden/good.html": None}]
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))
    run(job)

    state = answered(job, "undo")

    assert state["state"] == "passed", state["reason"]
    assert "golden: Delivery restored the package's version" in fakes.updates[1].message
    assert state["loop"]["round"] == 1  # the owner's undo counts no round
    names = git(checkout.parents[1], "show", "--name-only", "--format=", landed(checkout)).splitlines()
    assert names == ["src/pkg/design_pack.json", "src/pkg/skills/NOTICE.md"]


def test_a_removed_golden_page_is_removed_by_the_pull_request(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    kept = json.loads((checkout / EXPECTED).read_text())
    for mode in kept.values():
        mode.pop("good.html")
    fakes.edits = [{EXPECTED: json.dumps(kept) + "\n", "golden/good.html": None}]
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))
    run(job)

    state = answered(job, "accept")

    assert state["state"] == "passed", state["reason"]
    names = git(checkout.parents[1], "show", "--name-only", "--format=", landed(checkout)).splitlines()
    assert "src/pkg/golden/good.html" in names
    git(checkout.parents[1], "fetch", "-q", "origin")
    assert "good.html" not in git(checkout.parents[1], "ls-tree", "--name-only", "origin/main", "src/pkg/golden/")


GLUE = "code/detector.py"


def test_a_glue_change_is_judged_then_waits_for_the_owners_approval_before_the_pull_request(tmp_path, checkout, clone):
    """TD-194, TD-414: the run never loads it; the owner approves its diff, then it joins the one commit."""
    fakes = Fakes(clone)
    glue = (checkout / "design_packs/detector.py").read_text() + "\n# reads the new engine's field\n"
    fakes.edits = [{GLUE: glue}]
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))

    state = run(job)

    assert (state["state"], results(state)["challenger"], results(state)["commit"]) == ("waiting", "passed", "waiting")
    assert fakes.sessions[0].changed == (pack_gates.MANIFEST, pack_gates.NOTICE, GLUE)
    assert "+++ candidate/code/detector.py" in fakes.sessions[0].message
    (q,) = state["questions"]
    assert (q["kind"], [o["id"] for o in q["options"]]) == ("code", ["approve", "discard"])
    assert "+# reads the new engine's field" in q["diff"]
    assert fakes.github.prs == {}
    state = answered(job, "approve")
    assert state["state"] == "passed", state["reason"]
    assert shown(checkout, "design_packs/detector.py") == glue
    assert "You approved the glue's diff, checked with the running code (TD-414)." in body(checkout)


def test_a_glue_change_the_owner_does_not_approve_is_discarded(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.edits = [{GLUE: "mine\n"}]
    before = snapshot(checkout)
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))
    run(job)

    state = answered(job, "discard")

    assert state["state"] == "discarded"
    assert (snapshot(checkout), fakes.github.prs) == (before, {})


def test_a_change_the_challenger_is_unsure_about_goes_to_the_owner_who_keeps_it_once(tmp_path, checkout, clone):
    """TD-194: an unsure change is the owner's; a kept one is not asked about again while it stays the same."""
    fakes = Fakes(clone)
    new = (checkout / PACKAGED).read_text() + "\n- an extra line\n"
    fakes.edits, fakes.needed = [{REVIEW_SKILL: new}], {REVIEW_SKILL: "unsure"}
    fakes.verdicts = ["fix", "pass"]
    job = pack_job.Job(rounds(Store(tmp_path / "store"), last_round_at=0, ask_owner_at=1), fakes.live(checkout))

    state = run(job)

    (q,) = state["questions"]
    assert (q["kind"], q["path"], [o["id"] for o in q["options"]]) == ("unsure", REVIEW_SKILL, ["keep", "undo"])
    assert f"w {REVIEW_SKILL}; suspicious: s" in q["text"]
    assert "+- an extra line" in q["diff"]
    assert fakes.calls.count("update") == 1  # asked before the repair
    state = answered(job, "keep")
    assert state["state"] == "passed", state["reason"]  # the next round is unsure again: kept, not asked
    assert fakes.calls.count("challenger") == 2
    assert shown(checkout, PACKAGED) == new


def test_a_change_the_owner_has_undone_is_restored_and_the_updater_adjusts_the_rest(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    original = (checkout / PACKAGED).read_text()
    fakes.edits, fakes.needed = [{REVIEW_SKILL: original + "\n- an extra line\n"}], {REVIEW_SKILL: "unsure"}
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))
    run(job)

    state = answered(job, "undo")

    assert state["state"] == "waiting"  # the undo was the last round's repair, reviewed by no round (TD-256)
    assert f"{REVIEW_SKILL}: Delivery restored the package's version" in fakes.updates[1].message
    assert [q["kind"] for q in state["questions"]] == ["end"]
    state = answered(job, "activate")
    assert state["state"] == "passed", state["reason"]
    assert "The updater changed nothing." in body(checkout)


def test_the_challengers_file_judgements_are_checked_at_its_result_tool():
    def errors(paths: list[str], changed: tuple[str, ...]) -> list[str]:
        said = [{"path": p, "needed": "yes", "what": "w", "suspicious": "none"} for p in paths]
        return pack_tools.check(pack_tools.PackReview(verdict="pass", changes=said), changed)

    assert errors(["a", "b"], ("a", "b")) == []
    assert errors(["a"], ("a", "b")) == ["changes: no entry for b"]
    assert errors(["a", "c"], ("a",)) == ["changes: c is not listed as changed"]
    assert errors(["a", "a"], ("a",)) == ["changes: a answered more than once"]
    unneeded = [{"path": "a", "needed": "no", "what": "w", "suspicious": "not in upstream"}]
    said = pack_tools.check(pack_tools.PackReview(verdict="pass", changes=unneeded), ("a",))
    assert said == ["changes: a judged not needed - raise a finding to undo it, verdict fix"]


def test_a_generated_file_the_challenger_is_unsure_about_is_kept_or_the_update_discarded():
    q = pack_gates.unsure("run", pack_gates.MANIFEST, "w", "diff", "d")
    assert [o["id"] for o in q["options"]] == ["keep", "discard"]  # Delivery writes it: there is nothing to undo


def test_a_link_the_updater_makes_is_never_followed_and_an_undo_removes_only_the_link(tmp_path, checkout, clone):
    """TD-194: a link in its folder is outside the pack; restoring never writes through it."""
    secret = tmp_path / "secret.html"
    secret.write_text("mine\n")
    fakes = Fakes(clone)
    fakes.edits = [{"golden/evil.html": secret}]
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))

    state = run(job)

    (q,) = state["questions"]
    assert (q["kind"], q["bad"]) == ("scope", ["golden/evil.html"])
    state = answered(job, "undo")
    assert state["state"] == "passed", state["reason"]
    assert secret.read_text() == "mine\n"
    names = git(checkout.parents[1], "show", "--name-only", "--format=", landed(checkout)).splitlines()
    assert names == ["src/pkg/design_pack.json", "src/pkg/skills/NOTICE.md"]


def test_a_skill_changed_in_the_package_meanwhile_stops_activation(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.edits = [{REVIEW_SKILL: "updated\n"}]
    fakes.during = lambda: (checkout / PACKAGED).write_text("edited by hand meanwhile\n")

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert (state["state"], results(state)["commit"]) == ("failed", "failed")
    assert "owlbear-design-review changed in the package during the update" in state["reason"]
    assert (checkout / PACKAGED).read_text() == "edited by hand meanwhile\n"  # never overwritten


def test_a_skill_the_owner_commits_after_the_candidate_was_made_is_never_overwritten(tmp_path, checkout, clone):
    fakes, root = Fakes(clone), checkout.parents[1]

    def committed() -> None:  # the candidate copied the skills already; the owner commits a newer one meanwhile
        if (checkout / PACKAGED).read_text() == "the owner's newer text\n":
            return
        (checkout / PACKAGED).write_text("the owner's newer text\n")
        git(root, "commit", "-qam", "mine")
        git(root, "push", "-q")

    fakes.at_golden = committed
    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert (state["state"], results(state)["commit"]) == ("failed", "failed")
    assert "owlbear-design-review changed in the package during the update" in state["reason"]
    assert (checkout / PACKAGED).read_text() == "the owner's newer text\n"


def test_a_skill_the_updater_left_alone_but_committed_meanwhile_stops_activation_too(tmp_path, checkout, clone):
    fakes, root, design = Fakes(clone), checkout.parents[1], checkout / "skills/owlbear-interface-design/SKILL.md"

    def committed() -> None:  # the owner commits and pushes another skill while the challenger runs
        design.write_text("theirs\n")
        git(root, "commit", "-qam", "theirs")
        git(root, "push", "-q")

    fakes.during = committed
    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert (state["state"], results(state)["commit"]) == ("failed", "failed")
    assert "owlbear-interface-design changed in the package during the update" in state["reason"]


def test_a_passing_challenger_whose_processes_are_not_confirmed_gone_never_passes_the_pack(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.confirmed = False
    before = snapshot(checkout)

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert (state["state"], results(state)["challenger"]) == ("failed", "failed")
    assert "may still be running" in state["reason"]
    assert snapshot(checkout) == before


def test_when_upstream_is_not_ahead_the_run_is_up_to_date_and_does_nothing_else(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.tags = ["skill-v4.5.2", "skill-v4.0.0"]
    before = snapshot(checkout)

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert state["state"] == "up-to-date"
    assert "no skill release newer than skill-v4.5.2" in state["reason"]
    assert results(state) == {"notice": "passed"} | dict.fromkeys(NAMES[1:], "skipped")
    assert fakes.calls == ["releases"]
    assert snapshot(checkout) == before


@pytest.mark.parametrize(
    ("fakes_kw", "stage", "said"),
    [
        ({"replay_ok": False}, "replay", "below the margin"),
    ],
)
def test_a_failing_stage_stops_before_activation_and_changes_nothing(  # noqa: PLR0913, PLR0917 - one case per stage
    tmp_path, checkout, clone, fakes_kw, stage, said
):
    fakes = Fakes(clone, **fakes_kw)
    before = snapshot(checkout)

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert state["state"] == "failed"
    assert said in state["reason"]
    at = NAMES.index(stage)
    assert results(state) == dict.fromkeys(NAMES[:at], "passed") | {stage: "failed"} | dict.fromkeys(
        NAMES[at + 1 :], "skipped"
    )
    assert fakes.calls[-1] == stage
    assert snapshot(checkout) == before


def test_a_refused_push_waits_for_the_owner_and_trying_again_reconciles_with_github(tmp_path, checkout, clone):
    """TD-368: what stops publication asks the owner; trying again neither commits nor opens anything twice."""
    hook = tmp_path / "remote.git" / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho refused by the remote >&2\nexit 1\n")
    hook.chmod(0o755)
    before = snapshot(checkout)
    fakes = Fakes(clone)
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))

    state = run(job)

    assert (state["state"], results(state)["commit"], results(state)["push"]) == ("waiting", "passed", "waiting")
    (q,) = state["questions"]
    assert (q["kind"], [o["id"] for o in q["options"]]) == ("publish", ["retry", "discard"])
    assert "refused by the remote" in q["text"]
    assert (snapshot(checkout), fakes.github.prs) == (before, {})
    made = state["published"]["commit"]
    hook.unlink()
    state = answered(job, "retry")
    assert (state["state"], state["published"]["commit"], landed(checkout)) == ("passed", made, made)
    assert fakes.github.calls == ["create", "merge", "delete"]


def test_a_failed_check_waits_and_a_branch_behind_main_is_brought_up_to_date_first(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))
    fakes.live(checkout)
    fakes.github.checks = ["running", "failure"]

    state = run(job)

    (q,) = state["questions"]
    assert (state["state"], results(state)["merge"], q["kind"]) == ("waiting", "waiting", "publish")
    assert "CI failed at" in q["text"]
    assert "https://github.com/maba-pag/owlbear/pull/1" in q["text"]
    root = checkout.parents[1]
    (root / "other.txt").write_text("someone else's\n")
    git(root, "add", "other.txt")
    git(root, "commit", "-qm", "other")
    git(root, "push", "-q", "origin", "HEAD:main")  # main moved on meanwhile
    fakes.github.checks, fakes.github.behind = ["success"], 1
    state = answered(job, "retry")
    assert state["state"] == "passed", state["reason"]
    assert fakes.github.calls == ["create", "update-branch", "merge", "delete"]
    git(root, "fetch", "-q", "origin")
    assert git(root, "show", "-s", "--format=%s", "origin/main^1") == "other"  # merged on top of it


def test_a_host_stop_during_publication_waits_for_the_owner_instead_of_failing(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    store = Store(tmp_path / "store")
    job = pack_job.Job(store, fakes.live(checkout))
    fakes.github.checks = ["failure"]
    assert run(job)["state"] == "waiting"
    kept = json.loads((store.root / pack_job.FILE).read_text())
    kept["state"], kept["questions"] = "running", []  # as if the host stopped while CI ran
    (store.root / pack_job.FILE).write_text(json.dumps(kept))

    again = pack_job.Job(store, fakes.live(checkout))

    state = again.read()
    (q,) = state["questions"]
    assert (state["state"], q["kind"]) == ("waiting", "publish")
    assert "the host stopped while the update was being published" in q["text"]
    fakes.github.checks = ["success"]
    assert answered(again, "retry")["state"] == "passed"
    assert fakes.github.calls == ["create", "merge", "delete"]  # the open pull request was found again


def test_a_retry_after_update_branch_goes_on_and_a_lost_create_answer_still_gets_its_labels(tmp_path, checkout, clone):
    """Sol: the branch GitHub updated still holds the commit; a pull request found again gets the labels too."""
    fakes = Fakes(clone)
    store = Store(tmp_path / "store")
    store.root.mkdir(parents=True)
    (store.root / "config.json").write_text(json.dumps({"format": 4, "pr_labels": ["release:minor"]}))
    job = pack_job.Job(store, fakes.live(checkout))
    fakes.github.lose_create = True
    state = run(job)
    assert (state["state"], results(state)["pull-request"]) == ("waiting", "waiting")
    fakes.github.behind, fakes.github.checks = 1, ["success", "failure"]
    state = answered(job, "retry")
    assert (state["state"], fakes.github.calls) == ("waiting", ["create", "update-branch"])
    assert fakes.github.prs[1]["labels"] == ["release:minor"]  # found again, labelled all the same
    fakes.github.checks = ["success"]
    state = answered(job, "retry")
    assert state["state"] == "passed", state["reason"]
    assert fakes.github.calls == ["create", "update-branch", "merge", "delete"]


def test_a_merge_that_landed_before_the_retry_is_read_back_and_nothing_is_pushed_again(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))
    fakes.github.checks = ["failure"]
    assert run(job)["state"] == "waiting"
    pr = fakes.github.read_pull_request("maba-pag/owlbear", 1)
    fakes.github.refusal = None
    fakes.github.request_merge(MergeRequest(repository="maba-pag/owlbear", number=1, expected_head_sha=pr.head_sha,
                                            method=MergeMethod.MERGE))  # fmt: skip
    fakes.github.delete_branch("maba-pag/owlbear", pr.head_branch)  # GitHub deletes it after the merge
    (checkout / "skills" / "NOTICE.md").write_text("the merged version, deployed meanwhile\n")  # never re-checked

    state = answered(job, "retry")

    assert state["state"] == "passed", state["reason"]
    assert state["published"]["merged"] == fakes.github.prs[1]["sha"]
    assert git(checkout.parents[1], "ls-remote", "origin", f"refs/heads/{pr.head_branch}") == ""  # not pushed again


def test_gh_that_cannot_push_stops_the_run_before_any_download(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    live = fakes.live(checkout)
    fakes.github.can_push = False

    state = run(pack_job.Job(Store(tmp_path / "store"), live))

    assert (state["state"], results(state)["candidate"]) == ("failed", "failed")
    assert "cannot push to maba-pag/owlbear" in state["reason"]
    assert fakes.calls == ["releases"]


def test_the_source_must_be_owlbears_repository_on_main(checkout):
    root = checkout.parents[1]
    src = pack_git.source(checkout)
    assert (src.repository, src.base) == ("maba-pag/owlbear", git(root, "rev-parse", "HEAD"))
    git(root, "checkout", "-q", "-b", "side")
    (root / "side.txt").write_text("side\n")
    git(root, "add", "side.txt")
    git(root, "commit", "-qm", "side")
    with pytest.raises(design_pack.PackError, match="not on main"):
        pack_git.source(checkout)
    git(root, "checkout", "-q", "main")
    git(root, "remote", "set-url", "origin", "https://github.com/someone/fork.git")
    with pytest.raises(design_pack.PackError, match=r"origin https://github\.com/someone/fork\.git"):
        pack_git.source(checkout)


def test_it_refuses_a_dirty_checkout_and_a_package_outside_git_before_any_download(tmp_path, checkout, clone):
    (checkout / "skills" / "NOTICE.md").write_text("edited by hand\n")
    fakes = Fakes(clone)

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert (state["state"], results(state)["candidate"]) == ("failed", "failed")
    assert "uncommitted changes" in state["reason"]
    assert fakes.calls == ["releases"]
    assert (checkout / "skills" / "NOTICE.md").read_text() == "edited by hand\n"

    loose = tmp_path / "loose"
    shutil.copytree(checkout, loose)
    state = run(pack_job.Job(Store(tmp_path / "store2"), Fakes(clone).live(loose)))
    assert "is not a git checkout" in state["reason"]
    assert (loose / "design_pack.json").read_bytes() == (checkout / "design_pack.json").read_bytes()


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106
    paused = staticmethod(lambda: False)
    draining = staticmethod(lambda: False)
    closed = staticmethod(lambda: False)
    updating = staticmethod(lambda: "")
    launching = threading.Lock()

    def __init__(self) -> None:  # the session slots its pack sessions take (TD-336)
        self.slots, self.stopped = Slots(lambda: 4), threading.Event()
        self.store = SimpleNamespace(root=Path("/project"), settings=lambda: SimpleNamespace(sessions=2))


def test_a_pause_holds_no_update_but_a_stop_holds_its_start_and_answers(tmp_path, checkout, clone):
    job, _, state = upheld(tmp_path, checkout, clone)
    stopped = Host()
    stopped.paused = lambda: True  # TD-287: the owner's update runs while paused
    c = TestClient(api.create_app(job.store, "t", stopped, pack=job), base_url="http://127.0.0.1", headers=AUTH)
    assert "waits for your answers" in c.post("/api/next/design-pack/update").json()["detail"]
    answer = {"question": state["questions"][0]["id"], "option": "drop"}
    for flag, code, said in (("draining", 409, ENDING), ("closed", 503, STOPPING)):
        setattr(stopped, flag, lambda: True)
        for path, body in (("/api/next/design-pack/update", None), ("/api/next/design-pack/update/answer", answer)):
            refused = c.post(path, json=body)
            assert (refused.status_code, refused.json()["detail"]) == (code, said)
    assert c.get("/api/next/design-pack/update").json()["state"] == "waiting"


def test_every_project_sees_an_update_running_on_the_machine_and_for_whom(tmp_path):
    """TD-290: the lock's holder names its project; the pack section of every project reads it."""
    store = Store(tmp_path / "store")
    store.name = "shop"
    job = pack_job.Job(store)
    assert pack_job.running_for() is None
    job._claim()  # noqa: SLF001 - what a starting run takes
    try:
        c = TestClient(api.create_app(Store(tmp_path / "other"), "t", Host()), base_url="http://127.0.0.1")
        assert (pack_job.running_for(), c.get("/api/next/design-pack", headers=AUTH).json()["machine"]) == (
            "shop", "shop"
        )  # fmt: skip
    finally:
        os.close(job.held)
    assert pack_job.running_for() is None


def test_one_run_at_a_time_and_the_api_refuses_a_second(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.hold = threading.Event()
    job = pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout))
    c = TestClient(api.create_app(Store(tmp_path / "store"), "t", Host(), pack=job), base_url="http://127.0.0.1")
    assert c.post("/api/next/design-pack/update").status_code == 401  # guarded like every route

    started = c.post("/api/next/design-pack/update", headers=AUTH)
    assert (started.status_code, started.json()["state"]) == (200, "running")
    assert fakes.waiting.wait(10)
    second = c.post("/api/next/design-pack/update", headers=AUTH)
    assert (second.status_code, second.json()["detail"]) == (409, "a design pack update is already running")
    with pytest.raises(pack_job.Busy):
        job.start()
    now = c.get("/api/next/design-pack/update", headers=AUTH).json()
    assert (now["state"], now["stage"], results(now)["challenger"]) == ("running", "challenger", "running")
    fakes.hold.set()
    assert job.thread is not None
    job.thread.join(30)
    assert c.get("/api/next/design-pack", headers=AUTH).json()["update"]["state"] == "passed"
    assert fakes.calls.count("challenger") == 1


def test_one_update_runs_at_a_time_on_the_machine_whichever_project_starts_it(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.hold = threading.Event()
    first = pack_job.Job(Store(tmp_path / "a", None, "alpha"), fakes.live(checkout))
    second = pack_job.Job(Store(tmp_path / "b", None, "beta"), fakes.live(checkout))
    first.start()
    assert fakes.waiting.wait(10)
    with pytest.raises(pack_job.Busy, match="runs for alpha; one runs at a time on this machine"):
        second.start()
    assert second.read()["state"] == "idle"
    fakes.hold.set()
    first.thread.join(30)
    assert second.start()["state"] == "running"  # the lock went with the first run's thread
    second.thread.join(30)


def test_the_answer_routes_take_only_an_open_questions_options(tmp_path, checkout, clone):
    job, _, state = upheld(tmp_path, checkout, clone)
    c = TestClient(api.create_app(job.store, "t", Host(), pack=job), base_url="http://127.0.0.1", headers=AUTH)
    qid, url = state["questions"][0]["id"], "/api/next/design-pack/update/answer"

    stale = c.post(url, json={"question": "old:dispute:F1", "option": "drop"})
    assert (stale.status_code, stale.json()["detail"]) == (409, "this question is no longer open; reload the page")
    wrong = c.post(url, json={"question": qid, "option": "activate"})
    assert (wrong.status_code, wrong.json()["detail"]) == (422, "'activate' is no answer to this question")
    bare = c.post(url, json={"question": qid, "option": "reconsider", "note": "  "})
    assert (bare.status_code, bare.json()["detail"]) == (422, "asking the challenger to reconsider needs your note")
    assert c.post(url, json={"question": qid, "option": "drop", "extra": 1}).status_code == 422
    bare_client = TestClient(c.app, base_url="http://127.0.0.1")
    assert bare_client.post("/api/next/design-pack/update/discard").status_code == 401  # guarded like every route
    assert c.get("/api/next/design-pack/update").json()["state"] == "waiting"  # nothing above changed it

    assert c.post("/api/next/design-pack/update/discard").json()["state"] == "discarded"
    gone = c.post("/api/next/design-pack/update/discard")
    assert (gone.status_code, gone.json()["detail"]) == (409, "no design pack update waits for you")


def test_the_last_run_survives_a_host_restart_and_a_run_cut_short_reads_failed(tmp_path, checkout, clone):
    store = Store(tmp_path / "store")
    fakes = Fakes(clone)
    fakes.tags = ["skill-v4.5.2"]
    ended = run(pack_job.Job(store, fakes.live(checkout)))

    again = pack_job.Job(store, fakes.live(checkout)).read()
    assert again == ended
    assert "up to date" in again["log"][-1]
    assert pack_job.last(store) == {k: ended[k] for k in ("state", "started_at", "ended_at", "reason")}

    cut = json.loads((store.root / pack_job.FILE).read_text()) | {
        "state": "running",
        "stage": "golden",
        "ended_at": None,
    }
    cut["stages"][3]["result"] = "running"
    (store.root / pack_job.FILE).write_text(json.dumps(cut))
    after = pack_job.Job(store, fakes.live(checkout)).read()
    assert after["state"] == "failed"
    assert "the host stopped during this run" in after["reason"]
    assert results(after)["golden"] == "failed"
    assert json.loads((store.root / pack_job.FILE).read_text())["state"] == "failed"  # kept on disk


def test_settings_shows_the_design_pack_section_and_its_update_button(tmp_path, page_source):
    c = TestClient(api.create_app(Store(tmp_path), "t", Host()), base_url="http://127.0.0.1", headers=AUTH)

    page = page_source(c, "/config")

    assert '<section id="pack" class="panel" aria-labelledby="pack-title">' in page
    assert '<h2 id="pack-title">Design pack</h2>' in page
    assert 'button("Update design pack", startUpdate, { id: "pack-update", icon: "refresh"' in page  # lit-html
    assert '<p-text id="pack-state" size="sm" role="status" aria-live="polite">${packLine(u)}</p-text>' in page
    assert '<ol id="pack-stages" aria-label="Update stages">' in page
    assert "commits design_pack.json, skills/NOTICE.md and " in page  # the Update dialog says what it commits
    got = c.get("/api/next/design-pack").json()
    assert (got["pack"], got["upstream"]) == (OLD["pack"], OLD["upstream"]["tag"])
    assert got["identity"] == design_pack.identity()
    assert got["notice"] == "design pack impeccable-4.5.2.1: releases upstream unknown"  # never online
    assert got["update"]["state"] == "idle"
    assert [s["name"] for s in got["update"]["stages"]] == NAMES


def test_the_maintenance_page_links_each_action_and_shows_what_is_not_built(tmp_path):
    store = Store(tmp_path)
    c = TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers=AUTH)

    page = c.get("/maintenance")
    assert page.status_code == 200
    assert "<h1>Maintenance</h1>" in page.text
    assert '<div id="page"></div>' in page.text  # lit-html renders the actions from the API (TD-264)
    assert 'from "/assets/lit-html/3.3.3/lit-html.js"' in page.text

    got = {a["name"]: a for a in c.get("/api/next/maintenance").json()}
    assert list(got) == ["Memory curation", "Design pack update", "Engine update", "Review Tests", "Backlog triage"]
    assert (got["Memory curation"]["href"], got["Memory curation"]["last"]) == ("/memory", None)
    assert (got["Design pack update"]["href"], got["Design pack update"]["last"]) == ("/config#pack", None)
    assert (got["Engine update"]["built"], got["Engine update"]["href"]) == (True, "/config#machine-title")
    assert (got["Review Tests"]["built"], got["Review Tests"]["href"]) == (True, "#tests")  # started on this page
    assert (got["Backlog triage"]["href"], got["Backlog triage"]["recorded"]) == ("/backlog", False)
    (store.root / pack_job.FILE).write_text(
        json.dumps(pack_job._blank() | {"state": "failed", "started_at": "2026-10-15T10:00:00+00:00",  # noqa: SLF001
                                        "ended_at": "2026-10-15T10:05:00+00:00", "reason": "golden pages differ"})
    )  # fmt: skip
    last = {a["name"]: a for a in c.get("/api/next/maintenance").json()}["Design pack update"]["last"]
    assert last == {"state": "failed", "started_at": "2026-10-15T10:00:00+00:00",
                    "ended_at": "2026-10-15T10:05:00+00:00", "reason": "golden pages differ"}  # fmt: skip


def test_maintenance_sums_each_role_s_subagents_once_per_step(tmp_path):
    store = Store(tmp_path)
    c = TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers=AUTH)
    assert c.get("/api/next/maintenance/subagents").json() == []
    for slug in ("a", "b"):
        store.write(Lock(slug), Change(slug=slug, brief=Brief(version=1)))
    explore = {"agent": "explore", "credits": 1.5, "credits_known": True}
    unknown = {"agent": "code-review", "credits": 0.0, "credits_known": False}
    odd = [explore, unknown, None, {"agent": "research", "credits": "1"}]  # a None and text credits
    for slug, event in [
        ("a", {"event": "step", "session": "s1", "kind": "plan", "subagents": [explore]}),
        ("a", {"event": "step", "session": "s2", "kind": "brief-challenge", "exit": "held", "subagents": [explore]}),
        ("a", {"event": "step", "session": "s2", "kind": "brief-challenge"}),  # decided: logged again without them
        ("b", {"event": "step", "session": "s3", "kind": "plan", "subagents": "odd"}),  # never a list: none
        ("b", {"event": "step", "session": "s4", "kind": "plan-challenge", "subagents": odd}),
        ("b", {"event": "subagent", "agent": "explore"}),  # its own event; the step carries the record
        ("b", {"event": "step", "kind": "merge"}),  # no agent's step
        ("b", {"event": "step", "session": "s5", "kind": "plan-review"}),  # a kind since renamed
    ]:
        store.log(Lock(slug), slug, event)
    got = {u["role"]: u for u in c.get("/api/next/maintenance/subagents").json()}
    assert set(got) == {"planner", "challenger"}
    assert got["planner"] == {"role": "planner", "steps": 2, "with": 1, "runs": 1, "credits": 1.5, "unknown": 0,
                              "agents": {"explore": 1}}  # fmt: skip
    assert got["challenger"] == {"role": "challenger", "steps": 2, "with": 2, "runs": 4, "credits": 3.0,
                                 "unknown": 2, "agents": {"explore": 2, "code-review": 1, "research": 1}}  # fmt: skip
