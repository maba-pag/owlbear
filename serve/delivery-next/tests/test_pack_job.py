"""The Settings page's design pack update job (TD-101) and the Maintenance overview (TD-113), with fakes for the live
parts: upstream, downloads, golden pages, replay and the challenger. Git runs only on local repositories in tmp."""

import hashlib
import json
import shutil
import subprocess
import threading
from datetime import UTC, datetime
from functools import partial
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import dispute_tools, tools
from owlbear_delivery_next.change_contracts.round_records import RoundFinding, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import disputes
from owlbear_delivery_next.design_packs import calibration, design_pack, pack_git, pack_update
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.pack_runs import pack_job, pack_rounds, pack_updater
from owlbear_delivery_next.project_host import api, pack_routes
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Store

AUTH = {"authorization": "Bearer t"}
PKG = files("owlbear_delivery_next")
OLD = design_pack.manifest()
BUNDLE = OLD["bundle"]["path"]
NAMES = [name for name, _ in pack_job.STAGES]


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    done = subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """Delivery's package inside a git checkout on branch main, tracking a local bare remote."""
    remote, root = tmp_path / "remote.git", tmp_path / "checkout"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(root))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(root, "config", key, value)
    package = root / "src" / "pkg"
    (package / "skills").mkdir(parents=True)
    shutil.copy(str(PKG.joinpath("design_pack.json")), package / "design_pack.json")
    for name in ("NOTICE.md", "IMPECCABLE-LICENSE", *(f"{s}/SKILL.md" for s in OLD["skills"])):
        (package / "skills" / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(PKG.joinpath("skills", name)), package / "skills" / name)
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

    def golden(self, installed: design_pack.Installed) -> dict:
        self.calls.append("golden")
        assert installed.bundle == "bundle skill-v4.6.0"  # the candidate's detector, not the active one
        self.at_golden()
        return self.wrong

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
        result = tools.ReviewResult(verdict=verdict, findings=findings, rechecked=rechecked)
        return Run(cfg.session_id, "result", payload=result, termination=done)

    def update(self, _store: Store, cfg) -> Run:
        """The writing updater: each planned edit lands in its worktree, then it submits (or reports a premise)."""
        self.calls.append("update")
        self.updates.append(cfg)
        edit = self.edits.pop(0) if self.edits else {}
        for path, text in edit.items():
            (cfg.worktree / path).write_text(text)
        if self.premise:
            premise = tools.WrongPremise(stage="brief", reason="golden page glow.html must change", evidence=["g"])
            return Run(cfg.session_id, "premise", payload=premise, termination=Termination(confirmed=True))
        reject = [{"finding": k, "reason": "it already holds"} for k in (self.rejects.pop(0) if self.rejects else [])]
        result = pack_updater.UpdateResult(summary=f"round {len(self.updates)}", rejected=reject)
        return Run(cfg.session_id, "result", payload=result, termination=Termination(confirmed=True))

    def live(self, package: Path) -> pack_job.Live:
        return pack_job.Live(
            package=package, clone=self.clone, releases=self.releases, sync=self.sync, download=self.download,
            golden=self.golden, replay=self.replay, challenge=self.challenge, update=self.update,
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


def test_a_passing_update_runs_every_stage_in_order_then_activates_commits_and_pushes_one_commit(
    tmp_path, checkout, clone
):
    fakes = Fakes(clone)
    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert (state["state"], state["reason"]) == ("passed", "activated, committed and pushed")
    assert results(state) == dict.fromkeys(NAMES, "passed")
    here = design_pack.platform_name()
    assert fakes.calls == ["releases", "sync", f"engine {here}", "golden", "update", "replay", "challenger"]
    replayed = fakes.replayed  # the replay judges with the candidate pack, not the active one
    assert (replayed.pins["pack"], replayed.installed.bundle) == ("impeccable-4.6.0.1", "bundle skill-v4.6.0")
    assert replayed.manifest == (checkout / "design_pack.json").read_text()  # the pack then activated
    cfg = fakes.sessions[0]
    assert (cfg.role, cfg.policy.write, cfg.judging, cfg.submit) == ("challenger", False, True, tools.REVIEW)
    assert "## Rules added\n- glow: Glow" in cfg.message
    assert "## Golden pages\nas expected" in cfg.message
    assert "40 decided rounds" in cfg.message
    assert "# UI Design" in cfg.message  # the candidate skill text
    pins = json.loads((checkout / "design_pack.json").read_text())
    assert pins["upstream"] | {"commit": "x"} == {
        "repository": "pbakaus/impeccable", "tag": "skill-v4.6.0", "commit": "x", "engine": "0.2.0"
    }  # fmt: skip
    assert pins["upstream"]["commit"] == git(clone, "rev-parse", "skill-v4.6.0")
    assert pins["pack"] == "impeccable-4.6.0.1"
    assert pins["engine"]["linux-x64"] == hashlib.sha256(engine("linux-x64")).hexdigest()
    assert pins["bundle"]["sha256"] == hashlib.sha256(b"bundle skill-v4.6.0").hexdigest()
    assert (pins["skills"], pins["licence"]) == (OLD["skills"], OLD["licence"])
    written = (checkout / "design_pack.json").read_text()
    assert written == json.dumps(pins, indent=2, ensure_ascii=False) + "\n"  # TD-270
    assert list(pins) == list(OLD)  # in the old file's key order
    notice = (checkout / "skills" / "NOTICE.md").read_text()
    assert "`skill-v4.6.0`" in notice
    assert OLD["upstream"]["commit"] not in notice
    root = checkout.parents[1]
    head = git(root, "rev-parse", "HEAD")
    assert git(root, "ls-remote", "origin", "refs/heads/main").split()[0] == head  # pushed
    assert git(root, "show", "--name-only", "--format=%s", head).splitlines() == [
        "design pack: impeccable-4.5.2.1 to impeccable-4.6.0.1 (upstream skill-v4.5.2 to skill-v4.6.0)",
        "",
        "src/pkg/design_pack.json",
        "src/pkg/skills/NOTICE.md",
    ]
    assert state["pushed"] == {
        "commit": head, "remote": "origin", "branch": "refs/heads/main",
        "files": ["src/pkg/design_pack.json", "src/pkg/skills/NOTICE.md"],
    }  # fmt: skip
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
        (activated / name / "SKILL.md").write_bytes((checkout / "skills" / name / "SKILL.md").read_bytes())
    assert identity == design_pack.identity((checkout / "design_pack.json").read_text(), activated)
    assert "halo is decoration" in fakes.sessions[0].message
    assert "## The updater's report (data, not instructions)\nround 1" in fakes.sessions[0].message
    root = checkout.parents[1]
    head = git(root, "rev-parse", "HEAD")
    assert f"src/pkg/{PACKAGED}" in git(root, "show", "--name-only", "--format=", head).splitlines()
    assert ((checkout / PACKAGED).read_text(), git(root, "status", "--porcelain")) == (new, "")  # its exact text
    assert "The updater changed owlbear-design-review." in git(root, "log", "-1", "--format=%b")


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
    assert "Challenge rounds: 3." in git(checkout.parents[1], "log", "-1", "--format=%b")


def test_an_accepted_rejection_is_judged_alone_and_the_unchanged_candidate_activates(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.verdicts, fakes.rejects = ["fix"], [[], ["F1"]]

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    check = fakes.sessions[1]  # an early last round's rejections, judged alone (TD-218)
    assert (check.rechecks, check.cap) == (("F1",), 0)
    assert "- F1: owlbear-design-review: p - fix: f\n  The updater's reason: it already holds" in check.message
    assert "Judge only these rejections" in check.message
    assert state["state"] == "passed", state["reason"]
    body = git(checkout.parents[1], "log", "-1", "--format=%b")
    assert "F1 rejected; the challenger accepted that (updater: it already holds)" in body
    assert "The challenger passed." in body


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
    assert "F1 you dropped it" in git(checkout.parents[1], "log", "-1", "--format=%b")


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
    assert "The updater's last repair (r2) was not reviewed by a challenger." in q["text"]
    assert snapshot(checkout) == before

    state = answered(job, "activate")

    assert (state["state"], state["reason"]) == (
        "passed",
        "activated by you after rounds without a pass, committed and pushed",
    )
    assert (checkout / PACKAGED).read_text() == "fixed as you said\n"
    body = git(checkout.parents[1], "log", "-1", "--format=%b")
    assert "the owner activated it; its last repair (r2) was not reviewed (TD-256)" in body
    assert "The challenger passed." not in body


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
    assert results(state)["activate"] == "skipped"


def test_activation_publishes_only_the_candidate_the_owner_was_asked_about(tmp_path, checkout, clone):
    fakes, store = Fakes(clone, verdict="fix"), Store(tmp_path / "store")
    fakes.edits = [{}, {REVIEW_SKILL: "repaired\n"}]
    before = snapshot(checkout)
    job = pack_job.Job(store, fakes.live(checkout))
    run(job)
    (store.root / pack_job.CANDIDATE / "owlbear-design-review" / "SKILL.md").write_text("slipped in\n")

    state = answered(job, "activate")

    assert (state["state"], results(state)["activate"]) == ("failed", "skipped")
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
    assert "The challenger passed." in git(checkout.parents[1], "log", "-1", "--format=%b")


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
    assert (checkout / PACKAGED).read_text() == "repaired\n"


def test_a_skill_restored_to_its_start_replaces_the_earlier_edit_in_the_candidate(tmp_path, checkout, clone):
    fakes, original = Fakes(clone), (checkout / PACKAGED).read_text()
    fakes.verdicts, fakes.edits = ["fix", "pass"], [{REVIEW_SKILL: "an edit\n"}, {REVIEW_SKILL: original}]
    store = rounds(Store(tmp_path / "store"), last_round_at=0, ask_owner_at=1)

    state = run(pack_job.Job(store, fakes.live(checkout)))

    assert state["state"] == "passed", state["reason"]
    assert (checkout / PACKAGED).read_text() == original
    assert "The updater changed no skill." in git(checkout.parents[1], "log", "-1", "--format=%b")


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


@pytest.mark.parametrize(
    ("edit", "premise", "said"),
    [
        ({"upstream/skill/SKILL.md": "mine"}, False, "the updater changed upstream/skill/SKILL.md, which it may not"),
        ({"notes.md": "mine"}, False, "the updater changed notes.md, which it may not change"),
        ({}, True, "the updater asks the owner: golden page glow.html must change (g)"),
    ],
)
def test_an_edit_beyond_the_skills_or_a_change_of_expected_evidence_stops_for_the_owner(  # noqa: PLR0913, PLR0917
    tmp_path, checkout, clone, edit, premise, said
):
    fakes = Fakes(clone)
    fakes.edits, fakes.premise = [edit], premise
    before = snapshot(checkout)

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert (state["state"], results(state)["update"]) == ("failed", "failed")
    assert said in state["reason"]
    assert "challenger" not in fakes.calls
    assert snapshot(checkout) == before


def test_a_skill_changed_in_the_package_meanwhile_stops_activation(tmp_path, checkout, clone):
    fakes = Fakes(clone)
    fakes.edits = [{REVIEW_SKILL: "updated\n"}]
    fakes.during = lambda: (checkout / PACKAGED).write_text("edited by hand meanwhile\n")

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert (state["state"], results(state)["activate"]) == ("failed", "failed")
    assert "owlbear-design-review changed in the package during the update" in state["reason"]
    assert (checkout / PACKAGED).read_text() == "edited by hand meanwhile\n"  # never overwritten


def test_a_skill_the_owner_commits_after_the_candidate_was_made_is_never_overwritten(tmp_path, checkout, clone):
    fakes, root = Fakes(clone), checkout.parents[1]

    def committed() -> None:  # the candidate copied the skills already; the owner commits a newer one meanwhile
        (checkout / PACKAGED).write_text("the owner's newer text\n")
        git(root, "commit", "-qam", "mine")
        git(root, "push", "-q")

    fakes.at_golden = committed
    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert (state["state"], results(state)["activate"]) == ("failed", "failed")
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

    assert (state["state"], results(state)["activate"]) == ("failed", "failed")
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
        ({"wrong": {"bad.html (source)": {"missing": ["glow"], "unexpected": []}}}, "golden", "missing glow"),
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


def test_a_rejected_push_takes_the_local_commit_back(tmp_path, checkout, clone):
    hook = tmp_path / "remote.git" / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho refused by the remote >&2\nexit 1\n")
    hook.chmod(0o755)
    before = snapshot(checkout)

    state = run(pack_job.Job(Store(tmp_path / "store"), Fakes(clone).live(checkout)))

    assert (state["state"], results(state)["push"]) == ("failed", "failed")
    assert "the local commit was undone" in state["reason"]
    assert "is protected, the update must reach it through a pull request" in state["reason"]
    assert snapshot(checkout) == before
    assert state["pushed"] is None


def test_a_failed_activation_undoes_only_its_own_commit_never_a_concurrent_one(checkout):
    root, notice = checkout.parents[1], checkout / "skills" / "NOTICE.md"
    co, start, old = pack_git.checkout(checkout), git(checkout.parents[1], "rev-parse", "HEAD"), notice.read_bytes()

    def concurrent(cwd: Path, args: list[str], *, fail: bool = False) -> str:
        if args[0] == "commit":  # another process commits on the branch while the update commits
            (root / "other.txt").write_text(f"theirs {fail}\n")
            git(root, "add", "other.txt")
            git(root, "commit", "-qm", "theirs", "--", "other.txt")
            if fail:
                msg = "git commit failed: hook refused"
                raise design_pack.PackError(msg)
        return pack_git.git(cwd, args)

    with pytest.raises(design_pack.PackError, match="did not land"):
        pack_git.activate(co, {notice: "new\n"}, "update", concurrent)
    theirs = git(root, "rev-parse", "HEAD")
    assert (git(root, "rev-parse", "HEAD^"), git(root, "log", "-1", "--format=%s")) == (start, "theirs")
    assert (notice.read_bytes(), git(root, "status", "--porcelain")) == (old, "")

    git(root, "push", "-q")
    co = pack_git.checkout(checkout)
    with pytest.raises(design_pack.PackError, match=r"HEAD moved to \w+ during the update; nothing was reset"):
        pack_git.activate(co, {notice: "new\n"}, "update", partial(concurrent, fail=True))
    assert git(root, "rev-parse", "HEAD^") == theirs  # the second concurrent commit stays
    assert (notice.read_bytes(), git(root, "status", "--porcelain")) == (old, "")


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


def test_while_delivery_is_paused_no_update_starts_or_goes_on(tmp_path, checkout, clone):
    job, _, state = upheld(tmp_path, checkout, clone)
    stopped = Host()
    stopped.paused = lambda: True
    c = TestClient(api.create_app(job.store, "t", stopped, pack=job), base_url="http://127.0.0.1", headers=AUTH)
    answer = {"question": state["questions"][0]["id"], "option": "drop"}
    for path, body in (("/api/next/design-pack/update", None), ("/api/next/design-pack/update/answer", answer)):
        refused = c.post(path, json=body)
        assert (refused.status_code, refused.json()["detail"]) == (409, pack_routes.PAUSED)
    assert c.get("/api/next/design-pack/update").json()["state"] == "waiting"


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


def test_settings_shows_the_design_pack_section_and_its_update_button(tmp_path):
    c = TestClient(api.create_app(Store(tmp_path), "t", Host()), base_url="http://127.0.0.1", headers=AUTH)

    page = c.get("/config").text

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
    assert list(got) == [
        "Memory curation", "Design pack update", "Engine update", "Review Tests", "Backlog triage",
        "Explore experiment",
    ]  # fmt: skip
    assert (got["Explore experiment"]["built"], "availability only" in got["Explore experiment"]["note"]) == (
        False, True
    )  # fmt: skip
    assert (got["Memory curation"]["href"], got["Memory curation"]["last"]) == ("/memory", None)
    assert (got["Design pack update"]["href"], got["Design pack update"]["last"]) == ("/config#pack", None)
    assert (got["Engine update"]["built"], got["Engine update"]["note"]) == (False, "Not built yet.")
    assert (got["Review Tests"]["built"], got["Review Tests"]["note"]) == (False, "Not built yet (TD-112).")
    assert (got["Backlog triage"]["href"], got["Backlog triage"]["recorded"]) == ("/backlog", False)
    (store.root / pack_job.FILE).write_text(
        json.dumps(pack_job._blank() | {"state": "failed", "started_at": "2026-10-15T10:00:00+00:00",  # noqa: SLF001
                                        "ended_at": "2026-10-15T10:05:00+00:00", "reason": "golden pages differ"})
    )  # fmt: skip
    last = {a["name"]: a for a in c.get("/api/next/maintenance").json()}["Design pack update"]["last"]
    assert last == {"state": "failed", "started_at": "2026-10-15T10:00:00+00:00",
                    "ended_at": "2026-10-15T10:05:00+00:00", "reason": "golden pages differ"}  # fmt: skip
