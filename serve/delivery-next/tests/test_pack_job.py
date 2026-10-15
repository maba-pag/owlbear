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

from owlbear_delivery_next import api, calibration, design_pack, pack_git, pack_job, pack_update, tools
from owlbear_delivery_next.codebase import CURRENT
from owlbear_delivery_next.host import HostRecord
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.store import Store

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
    (package / "worker_skills").mkdir(parents=True)
    shutil.copy(str(PKG.joinpath("design_pack.json")), package / "design_pack.json")
    for name in ("NOTICE.md", "IMPECCABLE-LICENSE", *(f"{s}/SKILL.md" for s in OLD["skills"])):
        (package / "worker_skills" / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(PKG.joinpath("worker_skills", name)), package / "worker_skills" / name)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "start")
    git(root, "push", "-q", "-u", "origin", "main")
    return package


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """Upstream with the pinned tag and one newer skill release: a new rule, skill text and engine version."""
    root = tmp_path / "impeccable"
    git(tmp_path, "init", "-q", "-b", "main", str(root))
    licence = PKG.joinpath("worker_skills", "IMPECCABLE-LICENSE").read_bytes()
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
        self.calls, self.sessions, self.clone = [], [], clone
        self.wrong, self.replay_ok, self.verdict = wrong or {}, replay_ok, verdict
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
        return self.wrong

    def replay(self, _store: Store, candidate) -> calibration.Replay:
        self.calls.append("replay")
        self.replayed = candidate
        return calibration.Replay(40, 40, 40 if self.replay_ok else 0)

    def challenge(self, _store: Store, cfg) -> Run:
        self.calls.append("challenger")
        self.sessions.append(cfg)
        if self.hold:
            self.waiting.set()
            self.hold.wait(10)
        findings = [] if self.verdict == "pass" else [tools.Finding(place="owlbear-ui-review", problem="p", fix="f")]
        result = tools.ReviewResult(verdict=self.verdict, findings=findings)
        return Run(cfg.session_id, "result", payload=result, termination=Termination(confirmed=True))

    def live(self, package: Path) -> pack_job.Live:
        return pack_job.Live(
            package=package, clone=self.clone, releases=self.releases, sync=self.sync, download=self.download,
            golden=self.golden, replay=self.replay, challenge=self.challenge,
        )  # fmt: skip


def run(job: pack_job.Job) -> dict:
    job.start()
    assert job.thread is not None
    job.thread.join(30)
    return job.read()


def snapshot(package: Path) -> tuple[bytes, bytes, str, str]:
    root = package.parents[1]
    notice = (package / "worker_skills" / "NOTICE.md").read_bytes()
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
    assert fakes.calls == ["releases", "sync", f"engine {here}", "golden", "replay", "challenger"]
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
    assert '"skills": ["owlbear-ui-design", "owlbear-ui-review"],' in (checkout / "design_pack.json").read_text()
    notice = (checkout / "worker_skills" / "NOTICE.md").read_text()
    assert "`skill-v4.6.0`" in notice
    assert OLD["upstream"]["commit"] not in notice
    root = checkout.parents[1]
    head = git(root, "rev-parse", "HEAD")
    assert git(root, "ls-remote", "origin", "refs/heads/main").split()[0] == head  # pushed
    assert git(root, "show", "--name-only", "--format=%s", head).splitlines() == [
        "design pack: impeccable-4.5.2.1 to impeccable-4.6.0.1 (upstream skill-v4.5.2 to skill-v4.6.0)",
        "",
        "src/pkg/design_pack.json",
        "src/pkg/worker_skills/NOTICE.md",
    ]
    assert state["pushed"] == {
        "commit": head, "remote": "origin", "branch": "refs/heads/main",
        "files": ["src/pkg/design_pack.json", "src/pkg/worker_skills/NOTICE.md"],
    }  # fmt: skip
    assert git(root, "status", "--porcelain") == ""


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
        ({"verdict": "fix"}, "challenger", "owlbear-ui-review: p (fix: f)"),
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
    assert snapshot(checkout) == before
    assert state["pushed"] is None


def test_a_failed_activation_undoes_only_its_own_commit_never_a_concurrent_one(checkout):
    root, notice = checkout.parents[1], checkout / "worker_skills" / "NOTICE.md"
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
    (checkout / "worker_skills" / "NOTICE.md").write_text("edited by hand\n")
    fakes = Fakes(clone)

    state = run(pack_job.Job(Store(tmp_path / "store"), fakes.live(checkout)))

    assert (state["state"], results(state)["candidate"]) == ("failed", "failed")
    assert "uncommitted changes" in state["reason"]
    assert fakes.calls == ["releases"]
    assert (checkout / "worker_skills" / "NOTICE.md").read_text() == "edited by hand\n"

    loose = tmp_path / "loose"
    shutil.copytree(checkout, loose)
    state = run(pack_job.Job(Store(tmp_path / "store2"), Fakes(clone).live(loose)))
    assert "is not a git checkout" in state["reason"]
    assert (loose / "design_pack.json").read_bytes() == (checkout / "design_pack.json").read_bytes()


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


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
    assert (
        '<p-button id="pack-update" type="button" compact="true" icon="refresh">Update design pack</p-button>' in page
    )
    assert '<p-text id="pack-state" size="sm" role="status" aria-live="polite"></p-text>' in page
    assert '<ol id="pack-stages" aria-label="Update stages"></ol>' in page
    assert "commits design_pack.json and worker_skills/NOTICE.md" in page  # the Update dialog says what it commits
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
    assert '<ul id="actions" class="actions"></ul>' in page.text
    assert '<p-text id="status" role="status" aria-live="polite"></p-text>' in page.text

    got = {a["name"]: a for a in c.get("/api/next/maintenance").json()}
    assert list(got) == ["Memory curation", "Design pack update", "Engine update", "Review Tests", "Backlog triage"]
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
