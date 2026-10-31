"""#810: one read of outside data, its failures named per source, and notices of Global changed elsewhere."""

import json
import shutil
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.runtimes import model_choices, settings_read
from owlbear_delivery_next.runtimes.settings_read import Reader
from owlbear_delivery_next.runtimes.settings_seen import NAME
from owlbear_delivery_next.settings.config import CONFIG_FORMAT
from owlbear_delivery_next.state_store import registry, settings_carry
from owlbear_delivery_next.state_store.store import Store


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout  # noqa: S603, S607


def publish(clone: Path, rel: str, text: str) -> None:
    """Another machine changes a file of the shared repository and pushes it."""
    git(clone, "pull", "-q")
    (clone / rel).parent.mkdir(exist_ok=True)
    (clone / rel).write_text(text)
    git(clone, "add", rel)
    git(clone, "commit", "-q", "-m", f"elsewhere: {rel}")
    git(clone, "push", "-q")


def layer(**fields: object) -> str:
    return json.dumps({"format": CONFIG_FORMAT, **fields})


def model(model_id: str) -> SimpleNamespace:
    limits = SimpleNamespace(max_context_window_tokens=200_000)
    return SimpleNamespace(id=model_id, name=model_id, supported_reasoning_efforts=None, default_reasoning_effort=None,
                           billing=SimpleNamespace(token_prices=None), capabilities=SimpleNamespace(limits=limits),
                           policy=None)  # fmt: skip


class World:
    """A shared repository this machine reads, another machine's clone of it, and every outside source answering."""

    def __init__(self, shared_repo: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root, self.remote, self.mp = *shared_repo, monkeypatch
        self.other = tmp_path / "other"
        git(tmp_path, "clone", "-q", str(self.remote), str(self.other))
        monkeypatch.setenv(data_repo.VIEW, str(self.root))
        self.alone = Store(tmp_path / "alone")  # a project on this machine without a shared repository
        self.alone.root.mkdir()
        self.said: list[str] = []
        self.models(["m1"])
        self.releases(b"[]")

    def models(self, ids: list[str]) -> None:
        self.mp.setattr(model_choices, "_read", lambda: [model(i) for i in ids])

    def releases(self, answer: bytes | Exception) -> None:
        def fetch(_url: str, *_args: object) -> bytes:
            if isinstance(answer, Exception):
                raise answer
            return answer

        self.mp.setattr(pack_files, "fetch", fetch)

    def reader(self, *stores: Store) -> Reader:
        return Reader(self.said.append, lambda: [self.alone, *stores])

    def push(self, rel: str = "config.json", **fields: object) -> None:
        publish(self.other, rel, layer(**fields))


@pytest.fixture
def world(shared_repo, tmp_path, monkeypatch) -> World:
    return World(shared_repo, tmp_path, monkeypatch)


def ids(reader: Reader) -> list[str]:
    return [m["id"] for m in reader.offered.last()["models"]]


def builder(model_id: str) -> dict[str, object]:
    return {"agents": {"builder": {"model": model_id}}}


def _diverge(w: World) -> str:
    (w.root / "config.json").write_text(layer(**builder("mine")))
    git(w.root, "add", "config.json")
    git(w.root, "commit", "-q", "-m", "this machine's unpublished Global")
    return str(w.root)


def _no_remote(w: World) -> str:
    shutil.rmtree(w.remote)
    return str(w.root)


def _settings_json(_w: World) -> str:
    path = local_home.root() / "settings.json"
    path.write_text("{not json")
    return str(path)


def _alone_layer(w: World) -> str:
    w.alone.config_path.write_text("{not json")
    return str(w.alone.config_path)


def _shared_global(w: World) -> str:
    publish(w.other, "config.json", "{not json")
    return str(w.root / "config.json")


def _shared_project(w: World) -> str:
    publish(w.other, "shop/config.json", "{not json")
    return str(w.root / "shop" / "config.json")


def _releases(answer: bytes | Exception) -> object:
    def broken(w: World) -> str:
        w.releases(answer)
        return "GitHub's releases of"

    return broken


def _models(w: World) -> str:
    w.mp.setattr(model_choices, "_read", lambda: (_ for _ in ()).throw(RuntimeError("the CLI is gone")))
    return "the Copilot CLI's model list"


ELSEWHERE = '"elsewhere"'
CASES = [  # what breaks, the source named, the Global value the read then finds (None: Global is as before)
    pytest.param(_diverge, settings_read.SHARED, '"mine"', id="sync-refuses"),  # the checkout's own, not pulled
    pytest.param(_no_remote, settings_read.SHARED, None, id="fetch-fails"),
    pytest.param(_releases(OSError("no route")), settings_read.IMPECCABLE, ELSEWHERE, id="impeccable-unknown"),
    pytest.param(_releases(b"not json"), settings_read.IMPECCABLE, ELSEWHERE, id="impeccable-error"),
    pytest.param(_models, settings_read.MODELS, ELSEWHERE, id="models"),
    pytest.param(_settings_json, settings_read.MACHINE, ELSEWHERE, id="machine-layer"),
    pytest.param(_alone_layer, settings_read.SHARED, ELSEWHERE, id="unshared-project-layer"),
    pytest.param(_shared_global, settings_read.SHARED, None, id="shared-global"),
    pytest.param(_shared_project, settings_read.SHARED, ELSEWHERE, id="shared-project-layer"),
]


@pytest.mark.parametrize(("breaks", "source", "found"), CASES)
def test_each_source_s_failure_is_named_while_the_others_update(world, breaks, source, found):
    reader = world.reader()
    first = reader.read()
    assert (first.failures, first.succeeded_at) == ([], first.read_at)
    if breaks is not _shared_global:
        world.push(**builder("elsewhere"))
    world.models(["m1", "m2"])
    place = breaks(world)

    got = reader.read()

    assert [f.source for f in got.failures] == [source]
    assert place in got.failures[0].error
    assert any(line.startswith(f"settings read: {source} failed at {place}") for line in world.said)
    assert (got.succeeded_at, got.read_at > first.read_at) == (first.succeeded_at, True)
    assert ids(reader) == (["m1"] if source == settings_read.MODELS else ["m1", "m2"])
    if source == settings_read.MODELS:
        assert "the CLI is gone" in reader.offered.last()["error"]  # the kept list, and why it is not new
    notices = [(n.key, n.old, n.new) for n in got.notices]
    assert notices == ([("agents.builder.model", None, found)] if found else [])


def test_the_last_full_read_holds_through_a_partial_one_and_a_new_reader(world, monkeypatch):
    monkeypatch.delenv(data_repo.VIEW)
    one = world.reader().read()
    world.releases(b"not json")
    two = world.reader().read()
    kept = world.reader().ledger.load()
    world.releases(b"[]")
    three = world.reader().read()

    assert (one.unshared, one.failures, one.succeeded_at) == (True, [], one.read_at)
    assert (two.succeeded_at, two.read_at > one.read_at) == (one.read_at, True)
    assert kept == two
    assert [(f.source, f.at > one.read_at) for f in kept.failures] == [(settings_read.IMPECCABLE, True)]
    assert "GitHub's answer is not JSON" in kept.failures[0].error
    assert (three.unshared, three.failures, three.succeeded_at) == (True, [], three.read_at)
    assert three.read_at > two.read_at


def test_each_change_of_one_key_keeps_its_own_entry(world):
    world.push(**builder("A"))
    assert world.reader().read().notices == []  # the first read only records
    world.push(**builder("B"))  # while this host is stopped
    assert [(n.key, n.old, n.new) for n in world.reader().read().notices] == [("agents.builder.model", '"A"', '"B"')]
    reader = world.reader()
    world.push(**builder("C"))
    reader.read()
    world.push(machine={"channel": "major"})
    got = reader.read()
    assert [(n.key, n.old, n.new) for n in got.notices] == [
        ("agents.builder.model", '"A"', '"B"'),
        ("agents.builder.model", '"B"', '"C"'),
        ("agents.builder.model", '"C"', None),
        ("machine.channel", None, '"major"'),
    ]
    reader.dismiss([got.notices[1].id])
    again = world.reader().read()
    assert [n.id for n in again.notices] == [got.notices[i].id for i in (0, 2, 3)]


def test_a_pass_cut_short_by_a_stop_records_nothing(world, monkeypatch):
    reader = world.reader()
    reader.read()
    path = local_home.root() / NAME
    before = path.read_bytes()
    reader.stopping, later = threading.Event(), []
    real = reader._shared  # noqa: SLF001

    def shared() -> object:
        reader.stopping.set()  # the host stops while the first source reads
        return real()

    monkeypatch.setattr(reader, "_shared", shared)
    monkeypatch.setattr(reader, "_models", lambda: later.append("models") or [])
    monkeypatch.setattr(reader, "_impeccable", lambda: later.append("impeccable") or [])

    reader.read()

    assert (path.read_bytes(), later) == (before, [])


def test_a_hand_edit_is_the_sync_s_refusal_and_still_noticed(world):
    reader = world.reader()
    reader.read()
    (world.root / "config.json").write_text(layer(**builder("by hand")))

    got = reader.read()

    assert [(f.source, settings_carry.EDITED in f.error) for f in got.failures] == [(settings_read.SHARED, True)]
    assert [(n.key, n.old, n.new) for n in got.notices] == [("agents.builder.model", None, '"by hand"')]


def test_overrides_name_this_machine_and_its_projects(world):
    shop = Store(world.alone.root.parent / "shop", data_repo.DataRepo(world.root), "shop")
    reader = world.reader(shop)
    reader.read()
    world.push("shop/config.json", **builder("shop's"))
    (local_home.root() / "settings.json").write_text(layer(**builder("mine")))
    with registry.locked():
        machine = registry.load()
        machine.settings = machine.settings.model_copy(update={"channel": "minor"})
        registry.save(machine)
    world.push(**builder("global") | {"machine": {"channel": "major", "sessions": 2}, "pr_marker": True})

    reader.read()

    over = {n["key"]: n["overridden"] for n in reader.shown()["notices"]}
    assert over == {
        "agents.builder.model": ["this machine", "shop"],
        "machine.channel": ["this machine"],
        "machine.sessions": [],
        "pr_marker": [],
    }


def test_an_unreadable_state_file_is_said_and_rebuilt(world):
    reader = world.reader()
    world.push(**builder("A"))
    reader.read()
    (local_home.root() / NAME).write_text("{not json")
    assert [f["source"] for f in reader.shown()["failures"]] == ["read state"]

    rebuilt = reader.read()
    world.push(**builder("B"))
    after = reader.read()

    assert ([f.source for f in rebuilt.failures], rebuilt.notices) == (["read state"], [])
    assert any(line.startswith("settings read: read state failed") for line in world.said)
    assert [(n.key, n.old, n.new) for n in after.notices] == [("agents.builder.model", '"A"', '"B"')]
