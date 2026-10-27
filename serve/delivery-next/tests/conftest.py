import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar
from urllib.parse import parse_qsl

import pytest
from fastapi.testclient import TestClient

from owlbear_decisions import Decision, Scope, write
from owlbear_delivery_next.change_contracts import pick_tools, tools
from owlbear_delivery_next.change_contracts.models import Change
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.design_packs import design_pack
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import model_choices, sdk_adapter, spotter_look
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store import backlog, backlog_issues, legacy_family
from owlbear_delivery_next.state_store.store import Lock, Store

MACHINE_HOME = Path.home()  # read before any test replaces HOME
CHAT_REPLIES = json.loads((Path(__file__).parent / "fixtures" / "chat_contract_1.json").read_text())["replies"]


def has(out: object, field: str) -> bool:
    """Whether *out* has *field*: dotted, ``[]`` for each item of a list (and a list, when it is the last)."""
    head, _, rest = field.partition(".")
    if head.endswith("[]"):
        items = out if head == "[]" else out.get(head[:-2]) if isinstance(out, dict) else None
        return isinstance(items, list) and all(has(i, rest) for i in items) if rest else isinstance(items, list)
    return isinstance(out, dict) and head in out and (not rest or has(out[head], rest))


def _chat_replied(method: str, url: str, out: object) -> None:
    path = re.sub(r"^.*/api/next(/owlbear)?", "", url).split("?")[0]
    for route, fields in CHAT_REPLIES.items():
        verb, template = route.split(" ")
        if verb == method and re.fullmatch(re.sub(r"\{[^/]+\}", "[^/]+", template), path):
            assert [f for f in fields if not has(out, f)] == [], f"{route} lost what chat contract 1 reads"


@pytest.fixture
def chat_replied() -> Callable[[str, str, object], None]:
    """Asserts a host's answer to a chat keeps every field a chat of contract 1 reads from it."""
    return _chat_replied


@pytest.fixture
def machine_home() -> Path:
    """This machine's real home, for a test that reads what is installed there and never writes."""
    return MACHINE_HOME


@pytest.fixture
def page_source() -> Callable[[TestClient, str], str]:
    """A page as served, then each of its own modules it loads, followed through their relative imports (C-28)."""

    def read(client: TestClient, path: str) -> str:
        texts = [client.get(path).text]
        todo, seen = re.findall(r'"(/assets/page/[^"]+)"', texts[0]), set()
        while todo:
            url = todo.pop(0)
            if url not in seen:
                seen.add(url)
                texts.append(client.get(url).text)
                base = url.rpartition("/")[0]
                todo += [f"{base}/{n}" for n in re.findall(r'from "\./([^"]+)"', texts[-1])]
        return "\n".join(texts)

    return read


@pytest.fixture(autouse=True)
def _carried_settings(monkeypatch):
    """Code ships no settings defaults (2026-10-23); tests resolve over the carried values as a layer under Global.

    The five preferences are a test-only layer with the values the old code defaults gave (R15): production carries
    none of them. A test of unset settings sets ``config.BASE`` or ``machine_settings.BASE`` to ``None``.
    """
    from owlbear_delivery_next.github.provider import MergeMethod  # noqa: PLC0415
    from owlbear_delivery_next.settings import carried, config  # noqa: PLC0415
    from owlbear_delivery_next.state_store import machine_settings  # noqa: PLC0415

    prefs = config.Prefs(
        merge_method=MergeMethod.SQUASH,
        delete_remote_branch=False,
        ci_poll_seconds=20,
        ci_start_window_seconds=300,
        ask_before_merge=False,
    )
    monkeypatch.setattr(config, "BASE", complete_layer().model_copy(update={"prefs": prefs}))
    monkeypatch.setattr(machine_settings, "BASE", carried.MACHINE.model_copy(update=IMPROVEMENT_MACHINE))


IMPROVEMENT_MACHINE = {  # tests only: settings added after the carry start unset in production (2026-10-25)
    "retro_after_change": "on", "retro_when_idle": "on", "enrolled_chats": [],
}  # fmt: skip


def complete_layer():
    """The carried values plus test values for what came later: the Spotter's settings, the retro roles and the
    user-config switches, off (D-01M5YE4P5317N1HWD0QN6N05E0)."""
    from owlbear_delivery_next.settings import carried  # noqa: PLC0415
    from owlbear_delivery_next.settings.improvement import CATEGORIES, Spotter  # noqa: PLC0415

    base = carried.layer()
    spotter = Spotter(
        switch="on", steer_share=0, intervention_cap=1, verbose="off", looks=["hand-off"], look_credit_limit=0.75,
        **dict.fromkeys(CATEGORIES.values(), "record"),
    )  # fmt: skip
    agents = base.agents | {
        role: base.agents["curator"].model_copy(update={"model": "gpt-6.1-sol", "effort": "medium"})
        for role in ("retro", "retro-review")
    }
    update = {"spotter": spotter, "agents": agents, "load_user_instructions": False, "load_user_skills": False}
    return base.model_copy(update=update)


@pytest.fixture(autouse=True)
def _no_shared_settings(tmp_path_factory, monkeypatch):
    """Tests never read the machine's pointer to the shared settings repository (TD-57), nor go online.

    HOME is replaced too, so a child process a test starts resolves the same folder: a patch never reaches it.
    Playwright still finds the machine's browsers.
    """
    fake = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(fake))
    browsers = MACHINE_HOME / ("Library/Caches" if sys.platform == "darwin" else ".cache") / "ms-playwright"
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or str(browsers))
    home = fake / ".owlbear"
    home.mkdir()
    monkeypatch.setattr(local_home, "root", lambda: home)  # never the machine's ~/.owlbear
    monkeypatch.delenv("OWLBEAR_DATA", raising=False)
    monkeypatch.setattr(design_pack, "fetch", _offline)
    monkeypatch.setattr(model_choices, "_read", lambda: _offline("models.list"))
    monkeypatch.setattr(backlog_issues, "RUNNER", FakeGitHub(down=True))  # never the real backlog issues
    monkeypatch.setattr(backlog, "_cache", {})
    monkeypatch.setattr(backlog, "_recent", {})
    monkeypatch.setattr(backlog_issues, "_private", {})
    root = tmp_path_factory.mktemp("worktrees").resolve()
    monkeypatch.setattr(worktree, "data_root", lambda: root)  # never the machine's worktrees
    monkeypatch.setattr(sdk_adapter, "CopilotClient", _no_runtime)  # never a real model session; fakes replace it
    monkeypatch.setattr(spotter_look, "judged", _silent_look)  # nor a real Spotter look
    monkeypatch.setattr(sdk_adapter, "own_instructions", _no_instructions)  # fakes list no instruction sources


@pytest.fixture(autouse=True)
def _spotter_writes_end(_no_shared_settings):
    """Every Spotter write a test queued ends before the test's home and patches go."""
    yield
    from owlbear_delivery_next.improvement import spotter  # noqa: PLC0415

    assert spotter.WORK.settled(10), "Spotter writes still running after the test"


async def _silent_look(_card: dict, _ctx: object, _meter: object) -> str:
    return '{"category": "none", "note": "", "evidence": [], "state_change": null}'


async def _no_instructions(_session: object, _worktree: Path) -> list[str]:
    return []


def _no_runtime(**_kw: object) -> None:
    pytest.fail("a test started a real Copilot runtime: fake the session at its boundary")


class FakeGitHub:
    """GitHub's issue, comment and label REST API for ``acme/owlbear-data``, behind the ``gh api`` runner."""

    def __init__(self, *, down: bool = False) -> None:
        self.issues, self.labels, self.comments, self.calls, self.hidden = {}, {}, [], [], set()
        self.down, self.fail_writes, self.tick, self.visibility = down, False, 0, "private"

    def __call__(self, argv, data, _timeout, _cwd):
        if self.down:
            return subprocess.CompletedProcess(argv, 1, b"", b"error connecting to api.github.com\n")
        method, endpoint = argv[argv.index("--method") + 1], argv[10]
        if self.fail_writes and method != "GET":
            return subprocess.CompletedProcess(argv, 1, b"", b"gh: Server Error (HTTP 502)\n")
        body = json.loads(data) if data else None
        self.calls.append((method, endpoint, body))
        path, _, query = endpoint.partition("?")
        parts, params = path.split("/")[3:], dict(parse_qsl(query))
        assert f"{path}/".startswith("repos/acme/owlbear-data/"), endpoint
        status, out = self.answer(method, parts, params, body)
        if status:
            return subprocess.CompletedProcess(argv, 1, b"", f"gh: {out} (HTTP {status})\n".encode())
        return subprocess.CompletedProcess(argv, 0, json.dumps(out).encode(), b"")

    def answer(self, method, parts, params, body):  # noqa: PLR0911 - one answer per endpoint
        if not parts:
            return 0, {"full_name": "acme/owlbear-data", "private": self.visibility != "public",
                       "visibility": self.visibility}  # fmt: skip
        if parts == ["labels"] and method == "GET":
            return 0, self._page(list(self.labels.values()), params)
        if parts == ["labels"]:
            if body["name"] in self.labels:
                return 422, "Validation Failed"
            self.labels[body["name"]] = {"name": body["name"], "color": body["color"]}
            return 0, self.labels[body["name"]]
        if parts == ["issues"] and method == "GET":  # GitHub lists a new issue only seconds later: ``hidden``
            listed = [i for i in self.issues.values() if i["number"] not in self.hidden]
            return 0, self._page(sorted(listed, key=lambda i: -i["number"]), params)
        if parts == ["issues"]:
            number = len(self.issues) + 1
            self.issues[number] = {"number": number, "state": "open", "state_reason": None,
                                   "html_url": f"https://github.com/acme/owlbear-data/issues/{number}"}  # fmt: skip
            return 0, self.edit(self.issues[number], body)
        number = int(parts[1])
        if number not in self.issues:
            return 404, "Not Found"
        if parts[2:] == ["comments"]:
            self.comments.append((number, body["body"]))
            return 0, {"id": len(self.comments)}
        if method == "GET":  # one issue, as it is now: never hidden
            return 0, self.issues[number]
        return 0, self.edit(self.issues[number], body)

    def edit(self, issue, body):
        for name in body.get("labels", []):  # GitHub makes a missing label itself, in its own colour
            self.labels.setdefault(name, {"name": name, "color": "ededed"})
        issue |= {k: v for k, v in body.items() if k != "labels"}
        if "labels" in body:
            issue["labels"] = [{"name": n} for n in body["labels"]]
        if body.get("state") == "open":
            issue["state_reason"] = None
        self.tick += 1
        issue["updated_at"] = f"2026-10-15T00:{self.tick // 60:02d}:{self.tick % 60:02d}Z"
        return issue

    @staticmethod
    def _page(items, params):
        size, page = int(params.get("per_page", 30)), int(params.get("page", 1))
        return items[(page - 1) * size : page * size]


@pytest.fixture
def github(monkeypatch) -> FakeGitHub:
    """A reachable fake GitHub holding the shared repository's issues."""
    fake = FakeGitHub()
    monkeypatch.setattr(backlog_issues, "RUNNER", fake)
    return fake


def _git(cwd: Path, *args: str) -> str:
    if (cwd / "HEAD").is_file():  # a bare repository: safe.bareRepository=explicit wants it named
        args = ("--git-dir=.", *args)
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def shared_repo(tmp_path: Path) -> tuple[Path, Path]:
    """A shared repository clone whose origin names ``github.com/acme/owlbear-data``; git pushes to a local bare one."""
    remote, root, url = tmp_path / "remote.git", tmp_path / "owlbear-data", "https://github.com/acme/owlbear-data.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    _git(tmp_path, "clone", "-q", str(remote), str(root))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com"), (f"url.{remote}.insteadOf", url)):
        _git(root, "config", key, value)
    _git(root, "remote", "set-url", "origin", url)
    _git(root, "commit", "-q", "--allow-empty", "-m", "start")
    _git(root, "push", "-q", "-u", "origin", "HEAD")
    return root, remote


@pytest.fixture
def change_repo(tmp_path, monkeypatch) -> Path:
    """A temporary Change worktree: ``main`` with one commit and ``owlbear/c1`` one commit ahead, checked out."""
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    work = (tmp_path / "work").resolve()
    work.mkdir()
    for args in (("init", "-q", "-b", "main"), ("commit", "-q", "--allow-empty", "-m", "base")):
        subprocess.run(["git", *args], cwd=work, check=True, capture_output=True)  # noqa: S603, S607
    (work / "a.txt").write_text("a\n")
    for args in (("checkout", "-q", "-b", "owlbear/c1"), ("add", "-A"), ("commit", "-qm", "a")):
        subprocess.run(["git", *args], cwd=work, check=True, capture_output=True)  # noqa: S603, S607
    return work


class Host:
    wake = SimpleNamespace(set=lambda: None)
    paused = staticmethod(lambda: False)
    draining = staticmethod(lambda: False)
    maintenance = None  # the real host's seam; None: no maintenance owns this fake's sessions
    started = datetime(2026, 10, 21, 9, tzinfo=UTC)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=started, code=CURRENT)  # noqa: S106

    def activity(self, _slug):
        return Activity(host_up=True)


class Picking:
    """The chat's host API on a project with decisions; the picker's and the challenger's answers, in turn."""

    PROJECT = "shop-site"
    DRAFT: ClassVar[dict[str, Any]] = {
        "title": "Add farewell",
        "outcome": "farewell(name) says goodbye in the app package.",
        "criteria": ["farewell('Ada') returns 'Bye, Ada!'"],
        "scope": ["packages/app"],
    }
    USAGE: ClassVar[dict[str, Any]] = {"credits": 6.0, "models": {"gpt-6.1-sol": {"credits": 6.0, "tokens": 900}}}

    def __init__(self, tmp_path: Path, repo: Path, shared: DataRepo, monkeypatch) -> None:
        self.shared, self.repo = shared, repo
        self.store = Store(tmp_path / "store", shared, self.PROJECT)
        self.http = TestClient(api.create_app(self.store, "t", Host()), base_url="http://127.0.0.1",
                               headers={"authorization": "Bearer t"})  # fmt: skip
        self.picks: list[pick_tools.PickResult | str] = []  # a str is the ending of a failed session
        self.verdicts: list[tools.ReviewResult] = []
        self.told: list[sdk_adapter.Session] = []
        monkeypatch.setattr(runner.sdk_adapter, "run", self.run)
        monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: repo)

    async def run(self, cfg):
        self.told.append(cfg)
        done = Termination(confirmed=True)
        if cfg.role != tools.PICKER:
            return Run(cfg.session_id, "result", self.verdicts.pop(0), termination=done)
        said = self.picks.pop(0)
        if isinstance(said, str):
            return Run(cfg.session_id, said, None, detail="the runtime did not start", termination=done)
        return Run(cfg.session_id, "result", said, usage=self.USAGE, termination=done)

    def pickers(self) -> list[sdk_adapter.Session]:
        return [cfg for cfg in self.told if cfg.role == tools.PICKER]

    @property
    def slug(self) -> str:
        return self.store.slugs()[0]

    def change(self) -> Change:
        return self.store.read(self.slug)

    def put(self, decision: Decision) -> Decision:
        write(decision, self.shared.root if decision.scope is Scope.GLOBAL else self.shared.root / self.PROJECT)
        return decision

    def save(self, **fields) -> dict:
        body = self.DRAFT | {"change": "c1"} | fields if self.store.slugs() else self.DRAFT | fields
        return self.http.post("/api/next/briefs", json=body).json()

    def ask(self, version: int, rejected: dict[str, str] | None = None, *, retry: bool = False):
        said = [{"finding": k, "reason": r} for k, r in (rejected or {}).items()]
        body = {"change": "c1", "version": version, "rejected": said, "retry_pick": retry}
        return self.http.post("/api/next/briefs/challenge", json=body)

    def step(self) -> Change:
        c = self.change()
        runner._step(self.store, Lock(self.slug), c, c.step, self.repo)  # noqa: SLF001
        return self.change()

    def approve(self, version: int, *, unreviewed: bool = False):
        body = {"version": version, "unreviewed": unreviewed}
        return self.http.post(f"/api/next/changes/{self.slug}/approve-brief", json=body)

    def approved(self) -> Change:
        return self.store.fold(Lock(self.slug), self.slug, datetime.now(UTC))[0]


@pytest.fixture
def picking(tmp_path, change_repo, shared_repo, monkeypatch) -> Picking:
    """A project with a shared data repository whose Changes are shaped, picked and approved through the host API."""
    shared = DataRepo(shared_repo[0])
    shared.claim(Picking.PROJECT, "github.com/acme/shop-site")
    return Picking(tmp_path, change_repo, shared, monkeypatch)


class Pds:
    """The pages' Porsche Design System controls in Playwright, with the PDS CDN reachable (TD-39, TD-398)."""

    CDN = "https://cdn.ui.porsche.com/"
    _fetched: ClassVar[dict[str, tuple[int, dict[str, str], bytes]]] = {}  # CDN URL -> its answer, per test worker

    @classmethod
    def only(cls, page, base: str) -> None:
        """Let *page* reach the test host and the PDS CDN only; anything else is refused. Routing turns the browser's
        cache off, so each CDN file is fetched once and then answered from memory, as that cache would: a page a click
        opens then loads as fast as a browser loads it, not at the CDN's speed of the moment."""

        def route(r) -> None:
            url = r.request.url
            if url.startswith(base):
                return r.continue_()
            if not url.startswith(cls.CDN):
                return r.abort()
            if url not in cls._fetched:
                got = r.fetch()
                if not got.ok:
                    return r.fulfill(response=got)
                kept = {k: v for k, v in got.headers.items() if k not in ("content-encoding", "content-length")}
                cls._fetched[url] = (got.status, kept, got.body())
            status, headers, body = cls._fetched[url]
            return r.fulfill(status=status, headers=headers, body=body)

        page.route("**/*", route)

    @staticmethod
    def modal(page):
        """The newest open ``p-modal`` (one just answered fades out for a moment): its content is slotted, so its text
        and buttons are found from it, not from its dialog."""
        return page.locator("p-modal").filter(has=page.get_by_role("dialog")).last

    @classmethod
    def answer(cls, page, button: str) -> None:
        """Click *button* in the newest open ``p-modal``, then wait until its dialog has closed: while it fades out the
        page behind it is inert, so a fill or a pick there would be lost without an error. A locator, unlike a handle,
        also ends the wait when the answer opens another page."""
        from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

        modal = cls.modal(page)
        modal.evaluate("m => m.setAttribute('data-test-answered', '')")
        modal.get_by_role("button", name=button).click()
        expect(page.locator("p-modal[data-test-answered]").get_by_role("dialog")).to_have_count(0)

    @staticmethod
    def select(scope, label: str):
        """The ``p-select`` labelled *label*; its label names its combobox and listbox, so get_by_label finds two."""
        return scope.locator(f'p-select[label="{label}"]')

    @classmethod
    def pick(cls, scope, label: str, value: str) -> None:
        """Choose the option of value *value* in the select labelled *label*, as a person does: open it, click it."""
        select = cls.select(scope, label)
        select.get_by_role("combobox").click()
        select.locator(f'p-select-option[value="{value}"]').click()


@pytest.fixture
def pds() -> type[Pds]:
    """Helpers for pages on PDS components in a real browser."""
    return Pds


def _offline(url: str, *_args: object, **_kwargs: object) -> bytes:
    msg = f"offline in tests: {url}"
    raise OSError(msg)


AUDITED_COMMIT = "51aa0e1c6"
LEGACY_V1_COMMIT = "e58e0ace4eadf44fabc775fa82adfdb2bac265e0"
AUDITED_PACKAGE = "serve/delivery-next/src/owlbear_delivery_next"
GIT_IDENTITY = ("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid")


def commit_package(package: Path) -> None:
    """Commit every change in a fixture checkout so the gate sees a clean build."""
    subprocess.run(["git", "-C", str(package), "add", "-A"], check=True, capture_output=True)  # noqa: S603, S607
    commit = ["git", "-C", str(package), *GIT_IDENTITY, "commit", "-q", "-m", "fixture"]
    subprocess.run(commit, check=True, capture_output=True)  # noqa: S603


@pytest.fixture
def audited_package(tmp_path: Path) -> Path:
    """A clean git checkout holding the audited source bytes of 51aa0e1c6, read from that commit."""
    return checkout_package(tmp_path, AUDITED_COMMIT, legacy_family.FILES)


@pytest.fixture
def legacy_v1_package(tmp_path: Path) -> Path:
    """A clean git checkout holding the source bytes of the v1.0 cold channel, read from e58e0ace4."""
    return checkout_package(tmp_path / "v1", LEGACY_V1_COMMIT, legacy_family.LEGACY_V1_FILES)


def checkout_package(root: Path, commit: str, files: tuple[str, ...]) -> Path:
    """Write the named package files of one commit into a fresh clean git checkout under root."""
    package = root / "owlbear_delivery_next"
    package.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(package)], check=True, capture_output=True)  # noqa: S603, S607
    for rel in files:
        show = ["git", "-C", str(Path(__file__).parent), "show", f"{commit}:{AUDITED_PACKAGE}/{rel}"]
        blob = subprocess.run(show, capture_output=True, check=True).stdout  # noqa: S603
        (package / rel).parent.mkdir(parents=True, exist_ok=True)
        (package / rel).write_bytes(blob)
    commit_package(package)
    return package


@pytest.fixture
def audited_binding(audited_package: Path, tmp_path: Path, monkeypatch) -> legacy_family.Binding:
    """Bind the gate to the audited checkout through a launcher that runs the interpreter which loaded it."""
    return _bind(audited_package, tmp_path, monkeypatch)


@pytest.fixture
def legacy_v1_binding(legacy_v1_package: Path, tmp_path: Path, monkeypatch) -> legacy_family.Binding:
    """Bind the gate to the v1.0 checkout through the same launcher shape as the audited binding."""
    return _bind(legacy_v1_package, tmp_path / "v1", monkeypatch)


@pytest.fixture
def current_package(tmp_path: Path) -> Path:
    """A clean checkout of the candidate bytes copied from the working tree; the real tree is only read."""
    source = Path(__file__).resolve().parents[1] / "src" / "owlbear_delivery_next"
    package = tmp_path / "current" / "owlbear_delivery_next"
    package.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(package)], check=True, capture_output=True)  # noqa: S603, S607
    for rel in legacy_family.CURRENT_FILES:
        (package / rel).parent.mkdir(parents=True, exist_ok=True)
        (package / rel).write_bytes((source / rel).read_bytes())
    commit_package(package)
    return package


@pytest.fixture
def current_binding(current_package: Path, tmp_path: Path, monkeypatch) -> legacy_family.Binding:
    """Bind the gate to the clean candidate checkout through the same launcher shape as the audited binding."""
    return _bind(current_package, tmp_path / "current", monkeypatch)


@pytest.fixture
def release_binding(tmp_path: Path, monkeypatch) -> Callable[[str], legacy_family.Binding]:
    """Bind the gate to a clean checkout of one shipped release commit's audited family files."""

    def bind(commit: str) -> legacy_family.Binding:
        root = tmp_path / commit[:12]
        return _bind(checkout_package(root, commit, legacy_family.FILES), root, monkeypatch)

    return bind


def _bind(package: Path, root: Path, monkeypatch) -> legacy_family.Binding:
    launcher = root / "owlbear"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(f"#!{sys.executable}\n")
    launcher.chmod(0o755)
    binding = legacy_family.Binding(launcher, Path(sys.executable), package)
    monkeypatch.setattr(legacy_family, "live_binding", lambda: binding)
    return binding
