import argparse

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.runtimes import step_input
from owlbear_delivery_next.state_store.store import Store


def test_seeding_replaces_only_its_own_profile_entries(tmp_path) -> None:
    store = Store(tmp_path)
    kept = {
        "check:packages/app": ProfileEntry(state="known", value="npm test", evidence="package.json"),
        "install:packages/web": ProfileEntry(state="known", value="npm ci", evidence="package.json"),
        "install:packages/app": ProfileEntry(state="known", value="npm install", evidence="old"),
    }
    store.write_profile(Profile(version=3, entries=kept))
    a = argparse.Namespace(
        change="c1", title="t", outcome="o", criterion=["works"], scope=["packages/app"], check=["npm test"],
        install=[("packages/app", "npm ci")], person_check=[], target="main",
    )  # fmt: skip
    cli.seed(store, a)
    entries = store.read_profile().entries
    assert {k: e.value for k, e in entries.items()} == {
        "check:packages/app": "npm test",
        "install:packages/web": "npm ci",
        "install:packages/app": "npm ci",
    }
    assert store.read_profile().version == 4
    change = store.read("c1")
    assert change.plan.tasks[0].checks == ["cd . && npm test"]
    assert step_input.session(change, store.read_profile(), tmp_path, {}).checks == ("cd . && npm test",)
