import pytest

from owlbear_delivery_next import design_pack


@pytest.fixture(autouse=True)
def _no_shared_settings(tmp_path_factory, monkeypatch):
    """Tests never read the machine's pointer to the shared settings repository (TD-57), nor go online."""
    monkeypatch.setenv("OWLBEAR_HOME", str(tmp_path_factory.mktemp("owlbear-home")))
    monkeypatch.delenv("OWLBEAR_COMMON", raising=False)
    monkeypatch.setattr(design_pack, "fetch", _offline)


def _offline(url: str, *_args: object, **_kwargs: object) -> bytes:
    msg = f"offline in tests: {url}"
    raise OSError(msg)
