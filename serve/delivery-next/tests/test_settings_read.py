"""#810: one read of outside data, its failures named per source, and notices of Global changed elsewhere."""

import json
import logging
import shutil
import subprocess
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import pytest
from copilot.generated import rpc
from fastapi.testclient import TestClient
from pydantic import ValidationError

from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import model_choices, settings_read, settings_seen
from owlbear_delivery_next.runtimes.settings_read import Reader
from owlbear_delivery_next.runtimes.settings_seen import NAME
from owlbear_delivery_next.settings.config import CONFIG_FORMAT, GlobalLayer
from owlbear_delivery_next.state_store import layers, registry, settings_carry
from owlbear_delivery_next.state_store.store import Store, StoreError


def git(cwd: Path, *args: str) -> None:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True)  # noqa: S603, S607


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


def model(model_id: str) -> rpc.Model:
    limits = rpc.ModelCapabilitiesLimits(max_context_window_tokens=200_000)
    return rpc.Model(id=model_id, name=model_id, capabilities=rpc.ModelCapabilities(limits=limits))


class Sources:
    """Every outside source answering and this machine's reader of them, with no shared repository set up."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.mp = monkeypatch
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


class World(Sources):
    """A shared repository this machine reads, another machine's clone of it, and every outside source answering."""

    def __init__(self, shared_repo: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root, self.remote = shared_repo
        self.other = tmp_path / "other"
        git(tmp_path, "clone", "-q", str(self.remote), str(self.other))
        monkeypatch.setenv(data_repo.VIEW, str(self.root))
        super().__init__(tmp_path, monkeypatch)

    def push(self, rel: str = "config.json", **fields: object) -> None:
        publish(self.other, rel, layer(**fields))


def client(store: Store, reads: Reader) -> TestClient:
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106
    host = SimpleNamespace(
        maintenance=None, wake=SimpleNamespace(set=lambda: None), record=record, reads=reads, repo=None
    )
    app = api.create_app(store, "t", host)
    return TestClient(app, base_url="http://127.0.0.1", headers={"authorization": "Bearer t"})


@pytest.fixture
def world(shared_repo, tmp_path, monkeypatch) -> World:
    return World(shared_repo, tmp_path, monkeypatch)


@pytest.fixture
def sources(tmp_path, monkeypatch) -> Sources:
    return Sources(tmp_path, monkeypatch)


def ids(reader: Reader) -> list[str]:
    return [m["id"] for m in reader.offered()["models"]]


def builder(model_id: str) -> dict[str, object]:
    return {"agents": {"builder": {"model": model_id}}}


def as_saved(model_id: str) -> GlobalLayer:
    return GlobalLayer.model_validate({"format": CONFIG_FORMAT, **builder(model_id)})


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


def _releases(answer: bytes | Exception, w: World) -> str:
    w.releases(answer)
    return "GitHub's releases of"


def _models(w: World) -> str:
    w.mp.setattr(model_choices, "_read", lambda: (_ for _ in ()).throw(RuntimeError("the CLI is gone")))
    return "the Copilot CLI's model list"


ELSEWHERE = '"elsewhere"'
CASES = [  # what breaks, the source named, the Global value the read then finds (None: Global is as before)
    pytest.param(_diverge, settings_read.SHARED, '"mine"', id="sync-refuses"),  # the checkout's own, not pulled
    pytest.param(_no_remote, settings_read.SHARED, None, id="fetch-fails"),
    pytest.param(partial(_releases, OSError("no route")), settings_read.IMPECCABLE, ELSEWHERE, id="impeccable-unknown"),
    pytest.param(partial(_releases, b"not json"), settings_read.IMPECCABLE, ELSEWHERE, id="impeccable-error"),
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
        assert "the CLI is gone" in reader.offered()["error"]  # the kept list, and why it is not new
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
    reader.ledger.dismiss([got.notices[1].id])
    again = world.reader().read()
    assert [n.id for n in again.notices] == [got.notices[i].id for i in (0, 2, 3)]


def test_a_memory_value_changed_elsewhere_is_noticed_under_its_own_key(tmp_path):
    """Global as two reads find it, flattened and recorded as a read does; the pull is the per-key entry test's."""
    ledger, at = settings_seen.Ledger(tmp_path / NAME, [].append), datetime.now().astimezone()
    tuned = {"format": CONFIG_FORMAT, **builder("A"), "memory": {"purge_days": 14, "stale_factor": 50}}
    assert ledger.finish(settings_seen.flatten(as_saved("A")), [], unshared=False, at=at).notices == []
    got = ledger.finish(settings_seen.flatten(GlobalLayer.model_validate(tuned)), [], unshared=False, at=at)
    assert [(n.key, n.old, n.new) for n in got.notices] == [
        ("memory.purge_days", None, "14"),
        ("memory.stale_factor", None, "50"),
    ]


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


def test_an_unreadable_state_file_is_said_and_rebuilt(world, whole_error):
    reader = world.reader()
    world.push(**builder("A"))
    reader.read()
    path = local_home.root() / NAME
    text = json.dumps({whole_error: 1})
    path.write_text(text)
    with pytest.raises(ValidationError) as invalid:
        settings_seen.Seen.model_validate_json(text)
    expected = f"ValidationError: {invalid.value}"
    [failure] = client(world.alone, reader).post("/api/next/config/read").json()["reads"]["failures"]
    assert (failure["source"], failure["error"]) == ("read state", expected)
    assert [line for line in world.said if line.startswith("settings read: read state")] == [
        f"settings read: read state failed at {path}: {expected}; it is rebuilt"
    ]

    path.write_text(text)
    rebuilt = reader.read()
    world.push(**builder("B"))
    after = reader.read()

    assert ([f.source for f in rebuilt.failures], rebuilt.notices) == (["read state"], [])
    assert any(line.startswith("settings read: read state failed") for line in world.said)
    assert [(n.key, n.old, n.new) for n in after.notices] == [("agents.builder.model", '"A"', '"B"')]


def test_unreached_impeccable_releases_are_said_whole_with_their_type(sources, whole_error):
    sources.releases(PermissionError(whole_error))
    place = f"GitHub's releases of {pack_files.manifest()['pack']}"
    why = f"GitHub was not reached: PermissionError: {whole_error}"
    reader = sources.reader()
    reader.read()
    assert f"settings read: {settings_read.IMPECCABLE} failed at {place}: {why}" in sources.said
    failed = {f["source"]: f["error"] for f in reader.shown()["failures"]}
    assert failed[settings_read.IMPECCABLE] == f"{place}: {why}"


def test_a_failed_model_read_keeps_the_last_list_and_says_why(world, tmp_path, monkeypatch):
    reader, calls = world.reader(), []
    c = client(Store(tmp_path / "shop"), reader)

    def read(*found: str) -> None:
        def answer() -> list[rpc.Model]:
            calls.append(found)
            if not found:
                msg = "the CLI is gone"
                raise RuntimeError(msg)
            return [model(i) for i in found]

        monkeypatch.setattr(model_choices, "_read", answer)
        reader.read()

    read("m1")
    read()
    got = c.get("/api/next/config/models").json()
    assert ([m["id"] for m in got["models"]], "the CLI is gone" in got["error"], len(calls)) == (["m1"], True, 2)
    read("m2")
    assert (c.get("/api/next/config/models").json()["error"], ids(reader), len(calls)) == ("", ["m2"], 3)


def test_a_settings_save_is_not_noticed_but_a_key_pulled_during_it_is(world, tmp_path):
    def written(**fields: object) -> str:  # as every machine writes Global: one line per field
        return GlobalLayer.model_validate({"format": CONFIG_FORMAT, **fields}).model_dump_json(indent=1)

    publish(world.other, "config.json", written())
    reader = world.reader()
    reader.read()
    shop = Store(tmp_path / "shop", data_repo.DataRepo(world.root), "shop")
    c = client(shop, reader)
    rev = c.get("/api/next/config").json()["global_rev"]
    publish(world.other, "config.json", written(pr_marker=True))  # another machine, while the page is open

    edited = {"format": CONFIG_FORMAT, "machine": {"channel": "major"}}
    saved = c.put("/api/next/config/global", json={"rev": rev, "layer": edited})

    assert (saved.status_code, saved.json()["notice"]) == (200, "")
    assert '"pr_marker": true' in (world.root / "config.json").read_text()  # pulled by the save's publication
    assert [(n.key, n.old, n.new) for n in reader.read().notices] == [("pr_marker", None, "true")]


def test_a_save_during_a_read_is_not_noticed_against_the_global_the_read_found(world, monkeypatch):
    world.push(**builder("A"))
    reader = world.reader()
    reader.read()
    real = reader._models  # noqa: SLF001

    def models() -> object:  # the owner saves B after this read found Global holding A
        reader.ledger.own(as_saved("A"), as_saved("B"))
        return real()

    monkeypatch.setattr(reader, "_models", models)
    during = reader.read()
    monkeypatch.setattr(reader, "_models", real)
    world.push(**builder("B"))  # the save's publication
    after = reader.read()

    assert (during.notices, during.seen["agents.builder.model"]) == ([], '"B"')
    assert after.notices == []


def test_a_save_published_before_the_sync_never_hides_a_change_the_sync_pulls(world, monkeypatch):
    world.push(**builder("A"))
    reader = world.reader()
    reader.read()
    real = settings_read.settings_carry.sync

    def sync(*args: object) -> str:  # this machine saved and published B; another machine then set C
        reader.ledger.own(as_saved("A"), as_saved("B"))
        world.push(**builder("B"))
        world.push(**builder("C"))
        return real(*args)

    monkeypatch.setattr(settings_read.settings_carry, "sync", sync)
    got = reader.read()

    assert [(n.old, n.new) for n in got.notices] == [('"B"', '"C"')]
    assert got.seen["agents.builder.model"] == '"C"'


def test_a_read_is_dated_when_it_ends(sources, monkeypatch):
    reader, mid = sources.reader(), []
    real = reader._models  # noqa: SLF001
    monkeypatch.setattr(reader, "_models", lambda: mid.append(datetime.now(UTC)) or real())

    got = reader.read()

    assert got.read_at >= mid[0]
    assert got.succeeded_at == got.read_at


def test_a_read_never_takes_an_own_save_for_one_from_elsewhere_before_its_hook_ran(world):
    world.push(**builder("A"))
    reader = world.reader()
    reader.read()
    written, done, got = threading.Event(), threading.Event(), []

    def hook() -> None:  # the save has replaced the file; the read may finish before this records it
        written.set()
        done.wait(2)
        reader.ledger.own(as_saved("A"), as_saved("B"))

    path = world.root / "config.json"
    saving = threading.Thread(target=layers.update_layer, args=(path, GlobalLayer, lambda _c: as_saved("B"), hook))
    saving.start()
    written.wait(10)
    reading = threading.Thread(target=lambda: (got.append(reader.read()), done.set()))
    reading.start()
    reading.join(30)
    saving.join(30)

    assert got[0].notices == []
    assert reader.read().notices == []


def test_a_source_s_whole_error_is_said_and_shown(sources, tmp_path, monkeypatch, whole_error):
    """#921 D1: a source's unexpected failure, type included, uncut in the read state and the host's log."""

    def broken(**_kwargs: object) -> dict[str, object]:
        exc = RuntimeError(whole_error)
        exc.add_note("NOTE-MARK")
        raise exc

    monkeypatch.setattr(settings_read.pack_update, "notice", broken)
    c = client(Store(tmp_path / "shop"), sources.reader())
    expected = f"RuntimeError: {whole_error}\nNOTE-MARK"  # #971: its notes too

    [failure] = c.post("/api/next/config/read").json()["reads"]["failures"]

    assert (failure["source"], failure["error"]) == (settings_read.IMPECCABLE, expected)
    assert f"settings read: {settings_read.IMPECCABLE} failed: {expected}" in sources.said


def test_a_failed_model_read_is_shown_and_logged_whole(sources, tmp_path, monkeypatch, caplog, whole_error):
    """#921 D2: the runtime's whole error, type included, in Settings' models answer and the host's log."""

    def broken() -> list[rpc.Model]:
        raise RuntimeError(whole_error)

    monkeypatch.setattr(model_choices, "_read", broken)
    c = client(Store(tmp_path / "shop"), sources.reader())
    expected = f"RuntimeError: {whole_error}"

    with caplog.at_level(logging.WARNING, logger=model_choices.__name__):
        got = c.get("/api/next/config/models").json()

    assert got["error"] == expected
    logged = [r.getMessage() for r in caplog.records if r.name == model_choices.__name__]
    assert logged == [f"the offered models were not read: {expected}"]


def _raising(exc: Exception) -> Callable[..., object]:
    def raised(*_a: object, **_k: object) -> object:
        raise exc

    return raised


@pytest.mark.parametrize("fails", ["locate", "sync", "global", "machine", "layer"])
def test_each_source_s_typed_error_is_shown_whole(world, tmp_path, monkeypatch, whole_error, fails):
    """#971: a source's own error kept only its message; it is shown with its type and notes, as it is said."""
    world.reader().read()  # the first read: Global as found
    machine = local_home.root() / "settings.json"
    exc, mp, place = {
        "locate": (data_repo.DataRepoError(whole_error), (data_repo, "locate"), "the shared settings location"),
        "sync": (registry.RegistryError(whole_error), (settings_carry, "sync"), str(world.root)),
        "global": (StoreError(whole_error), (settings_read, "read_layer_settled"), str(world.root / "config.json")),
        "machine": (registry.RegistryError(whole_error), (settings_read.machine_settings, "current"), ""),
        "layer": (StoreError(whole_error), (settings_read, "read_layer"), str(machine)),
    }[fails]
    exc.add_note("NOTE-MARK")
    if fails == "layer":
        machine.write_text(layer())
        real = settings_read.read_layer
        monkeypatch.setattr(settings_read, "read_layer", lambda p, m: _raising(exc)() if p == machine else real(p, m))
    else:
        monkeypatch.setattr(*mp, _raising(exc))
    c = client(Store(tmp_path / "shop"), world.reader())
    said = f"{type(exc).__name__}: {whole_error}\nNOTE-MARK"

    failures = c.post("/api/next/config/read").json()["reads"]["failures"]

    assert [f["error"] for f in failures] == [f"{place}: {said}" if place else said]
    assert any(line.endswith(f"failed{f' at {place}' if place else ''}: {said}") for line in world.said)


def test_an_own_save_not_recorded_as_seen_is_said_whole_with_the_save(world, tmp_path, monkeypatch, whole_error):
    """#971 P16: the failure was said to host.log alone; the Global save's notice now says it too, whole."""
    reader = world.reader()
    reader.read()
    c = client(Store(tmp_path / "shop", data_repo.DataRepo(world.root), "shop"), reader)
    rev = c.get("/api/next/config").json()["global_rev"]
    full = OSError(28, whole_error)
    full.add_note("NOTE-MARK")
    monkeypatch.setattr(settings_seen, "atomic_write", _raising(full))

    saved = c.put("/api/next/config/global", json={"rev": rev, "layer": {"format": CONFIG_FORMAT, **builder("x")}})

    said = f"the saved Global values could not be recorded as seen: OSError: [Errno 28] {whole_error}\nNOTE-MARK"
    assert (saved.status_code, saved.json()["notice"]) == (200, said)
    assert f"settings read: {said}" in world.said
