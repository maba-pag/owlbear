import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import profile_share
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.store import Store

ENTERPRISE = "git.enterprise.invalid"


def confirmed(value: str) -> ProfileEntry:
    return ProfileEntry(state="known", value=value, evidence=f"{profile.CONFIRMED}; owner")


@pytest.fixture
def reached(monkeypatch) -> list[str]:
    """Every host the readiness checks try to reach; the probes are faked, so nothing runs on this machine."""
    hosts: list[str] = []

    def reach(host, *_args, **_kwargs):
        hosts.append(host)
        return f"{host} is not reachable"

    monkeypatch.setattr(readiness, "reach", reach)
    monkeypatch.setattr(readiness, "probe_in", lambda _repo: lambda _cmd: (1, "not checked"))
    monkeypatch.setattr(readiness.pack_update, "notice", lambda *_a, **_k: None)
    monkeypatch.setattr(readiness.pack_update, "said", lambda _n: "design packs not checked")
    return hosts


@pytest.mark.parametrize("raises", [False, True])
def test_a_failed_detection_checks_the_known_enterprise_host_not_the_public_one(
    shared_repo, tmp_path, monkeypatch, reached, raises
):
    root, _remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.HOST: confirmed(ENTERPRISE), profile.POLL: confirmed("45")}))
    monkeypatch.setattr(
        profile,
        "detect",
        lambda *_a: Profile(entries={profile.HOST: confirmed(ENTERPRISE), profile.POLL: confirmed("60")}),
    )
    real, refused = DataRepo.publish, []

    def refuse_detection(self, path, message, until=None):
        if path == profile_share.path(store) and message.endswith("detected in a clone") and not refused:
            refused.append(message)
            if raises:
                msg = "remote unavailable"
                raise DataRepoError(msg)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", refuse_detection)
    checks = readiness.ready(store, root)
    known = store.read_profile()
    assert known is not None, "the known profile must survive a failed detection"
    assert profile.value(known, profile.HOST) == ENTERPRISE

    assert refused
    assert [c.ok for c in checks if c.name == "profile detection"] == [False]
    assert reached == [ENTERPRISE]  # the network check names the known host; the public host is never probed
    network = [c for c in checks if c.name == "network"]
    assert len(network) == 1
    assert ENTERPRISE in network[0].detail


def test_an_unreadable_profile_after_a_failed_detection_defers_the_host_checks(tmp_path, monkeypatch, reached):
    store = Store(tmp_path / "store")

    def unreadable(_self):
        msg = "the profile could not be read: test"
        raise StoreError(msg)

    monkeypatch.setattr(Store, "read_profile", unreadable)
    checks = readiness.ready(store, tmp_path)

    assert [c.name for c in checks] == ["profile detection"]
    assert [c.ok for c in checks] == [False]
    assert reached == []  # no host is guessed while the profile cannot say which host it is
