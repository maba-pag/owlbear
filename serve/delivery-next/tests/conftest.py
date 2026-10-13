import pytest


@pytest.fixture(autouse=True)
def _no_shared_settings(tmp_path_factory, monkeypatch):
    """Tests never read the machine's pointer to the shared settings repository (TD-57)."""
    monkeypatch.setenv("OWLBEAR_HOME", str(tmp_path_factory.mktemp("owlbear-home")))
    monkeypatch.delenv("OWLBEAR_COMMON", raising=False)
