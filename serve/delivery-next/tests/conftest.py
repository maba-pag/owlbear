import json
import subprocess
from pathlib import Path
from urllib.parse import parse_qsl

import pytest

from owlbear_delivery_next import backlog, backlog_issues, design_pack, model_choices
from owlbear_delivery_next.steps import worktree


@pytest.fixture(autouse=True)
def _no_shared_settings(tmp_path_factory, monkeypatch):
    """Tests never read the machine's pointer to the shared settings repository (TD-57), nor go online."""
    monkeypatch.setenv("OWLBEAR_HOME", str(tmp_path_factory.mktemp("owlbear-home")))
    monkeypatch.delenv("OWLBEAR_COMMON", raising=False)
    monkeypatch.setattr(design_pack, "fetch", _offline)
    monkeypatch.setattr(model_choices, "_read", lambda: _offline("models.list"))
    monkeypatch.setattr(backlog_issues, "RUNNER", FakeGitHub(down=True))  # never the real backlog issues
    monkeypatch.setattr(backlog, "_cache", {})
    root = tmp_path_factory.mktemp("worktrees").resolve()
    monkeypatch.setattr(worktree, "data_root", lambda: root)  # never the machine's worktrees


class FakeGitHub:
    """GitHub's issue, comment and label REST API for ``acme/owlbear-data``, behind the ``gh api`` runner."""

    def __init__(self, *, down: bool = False) -> None:
        self.issues, self.labels, self.comments, self.calls = {}, {}, [], []
        self.down, self.fail_writes = down, False

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
        assert path.startswith("repos/acme/owlbear-data/"), endpoint
        status, out = self.answer(method, parts, params, body)
        if status:
            return subprocess.CompletedProcess(argv, 1, b"", f"gh: {out} (HTTP {status})\n".encode())
        return subprocess.CompletedProcess(argv, 0, json.dumps(out).encode(), b"")

    def answer(self, method, parts, params, body):  # noqa: PLR0911 - one answer per endpoint
        if parts == ["labels"] and method == "GET":
            return 0, self._page(list(self.labels.values()), params)
        if parts == ["labels"]:
            if body["name"] in self.labels:
                return 422, "Validation Failed"
            self.labels[body["name"]] = {"name": body["name"], "color": body["color"]}
            return 0, self.labels[body["name"]]
        if parts == ["issues"] and method == "GET":
            return 0, self._page(sorted(self.issues.values(), key=lambda i: -i["number"]), params)
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
        return 0, self.edit(self.issues[number], body)

    def edit(self, issue, body):
        for name in body.get("labels", []):  # GitHub makes a missing label itself, in its own colour
            self.labels.setdefault(name, {"name": name, "color": "ededed"})
        issue |= {k: v for k, v in body.items() if k != "labels"}
        if "labels" in body:
            issue["labels"] = [{"name": n} for n in body["labels"]]
        if body.get("state") == "open":
            issue["state_reason"] = None
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


def _offline(url: str, *_args: object, **_kwargs: object) -> bytes:
    msg = f"offline in tests: {url}"
    raise OSError(msg)
