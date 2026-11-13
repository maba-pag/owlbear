import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.github.provider import FailureCode, ProviderError
from owlbear_delivery_next.impeccable.detector import DetectorError
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
    monkeypatch.setattr(readiness.pack_update, "said", lambda _n: "Impeccable packs not checked")
    return hosts


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


@pytest.mark.parametrize("refusal", ["returned", "raised", "config"])
def test_a_failed_detection_keeps_its_whole_refusal_and_known_host_until_publication_succeeds(
    shared_repo, monkeypatch, whole_error, refusal, reached
):
    """#971: the data repository's whole refusal, its notes too, is the profile detection check's detail."""
    root, _remote = shared_repo
    store = Store(root.parent / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.HOST: confirmed(ENTERPRISE), profile.POLL: confirmed("45")}))
    done = "done" if refusal == "config" else ""
    fresh = Profile(entries={profile.HOST: confirmed(ENTERPRISE), profile.POLL: confirmed("60")}, prefs_import=done)
    monkeypatch.setattr(profile, "detect", lambda *_a: fresh)
    note = "while publishing shop-site"
    real = DataRepo.publish

    def refuse(self, path, message, until=None):
        if refusal == "config" and path == store.config_path:
            exc = DataRepoError(whole_error)
            exc.add_note(note)
            raise exc
        if refusal != "config" and path == profile_share.path(store) and message.endswith("detected in a clone"):
            if refusal == "returned":
                return whole_error
            exc = DataRepoError(whole_error)
            exc.add_note(note)
            raise exc
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", refuse)
    checks = readiness.ready(store, root)

    refused = {
        "returned": whole_error,
        "raised": f"DataRepoError: {whole_error}\n{note}",
        "config": f"DataRepoError: {whole_error}\n{note}",
    }[refusal]
    detail = f"StoreError: the detected profile could not be published: {refused}"
    assert [c.detail for c in checks if c.name == "profile detection"] == [detail]
    assert [c.ok for c in checks if c.name == "profile detection"] == [False]
    assert not (store.root / profile_share.DETECTED).exists()
    known = store.read_profile()
    assert known is not None, "the known profile must survive a failed detection"
    assert profile.value(known, profile.HOST) == ENTERPRISE
    assert reached == [ENTERPRISE]
    network = [c for c in checks if c.name == "network"]
    assert len(network) == 1
    assert ENTERPRISE in network[0].detail

    monkeypatch.setattr(DataRepo, "publish", real)
    monkeypatch.setattr(readiness, "check", lambda *_a, **_k: [])
    again = readiness.ready(store, root, carry=True)
    assert not [c for c in again if not c.ok]
    assert (store.root / profile_share.DETECTED).exists()


@pytest.mark.parametrize("kind", ["provider", "detector"])
def test_a_detection_read_failure_is_a_failed_check_with_its_details_and_retry(
    shared_repo, tmp_path, monkeypatch, reached, kind
):
    store = Store(tmp_path / "store", DataRepo(shared_repo[0]), "shop-site")
    store.write_profile(Profile(entries={profile.HOST: confirmed(ENTERPRISE)}))
    saved = profile_share.path(store).read_bytes()
    error = (
        ProviderError(FailureCode.UNAVAILABLE, "read repository", "not reachable", retry_safe=True)
        if kind == "provider"
        else DetectorError("detector refused")
    )
    error.add_note("the detection read did not finish")

    def fail(*_args):
        raise error

    monkeypatch.setattr(profile, "detect", fail)
    checks = readiness.ready(store, shared_repo[0])
    failed = next(c for c in checks if c.name == "profile detection")
    assert not failed.ok
    assert f"{type(error).__name__}: {error}\nthe detection read did not finish" in failed.detail
    assert failed.fix == "Resolve the profile detection or publication error reported above, then restart Delivery"
    assert profile_share.path(store).read_bytes() == saved
    assert not (store.root / profile_share.DETECTED).exists()
    assert reached == [ENTERPRISE]
    monkeypatch.setattr(profile, "detect", lambda *_a: store.read_profile())
    readiness.ready(store, shared_repo[0])
    assert (store.root / profile_share.DETECTED).exists()
