"""Updates ▸ Impeccable reads every project's Impeccable run without settling any (P5)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.impeccable_runs import pack_job, pack_state
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.state_store import pack_run_record, project_home, registry
from owlbear_delivery_next.state_store.store import Store

AT = datetime(2026, 10, 17, 2, tzinfo=UTC)


def test_machine_view_selects_open_run_and_never_settles(tmp_path) -> None:
    left = pack_state.blank() | {"state": "running", "run": "r-alpha", "started_at": "2026-10-17T02:00:00+00:00",
                                 "context": {"sid": "kept out of the page"}}  # fmt: skip
    projects = [registry.Project(id=n, path=str(tmp_path / n), added_at=AT) for n in ("alpha", "beta", "gamma")]
    with registry.locked():
        registry.save(registry.Machine(projects=projects))
    for name, text in {"alpha": json.dumps(left), "gamma": "{"}.items():
        project_home.home(name).mkdir(parents=True)
        (project_home.home(name) / pack_job.FILE).write_text(text)
    before = (project_home.home("alpha") / pack_job.FILE).read_bytes()
    beta = Store(project_home.home("beta"), None, "beta")
    c = TestClient(api.create_app(beta, "t", None), base_url="http://127.0.0.1", headers={"Authorization": "Bearer t"})

    got = c.get("/api/next/maintenance/pack/runs").json()

    run = got["run"]
    assert (run["pid"], run["name"], run["own"], run["state"]) == ("alpha", "alpha", False, "running")
    assert run["interrupted"] is True  # no host holds the machine's lock for it
    assert "context" not in run
    assert run["progress"]["legacy"] is True  # a record without invocations keeps its stages
    seen = {r["pid"]: r for r in got["runs"]}
    assert (seen["beta"]["own"], seen["beta"]["state"]) == (True, "idle")
    assert seen["gamma"]["state"] == "unreadable"
    assert "its run record cannot be read" in seen["gamma"]["error"]  # never taken for an idle one
    assert (project_home.home("alpha") / pack_job.FILE).read_bytes() == before  # read, never settled by a Job


@pytest.mark.parametrize("where", ["registry", "record"])
def test_overview_reports_registry_and_record_errors_whole(tmp_path, monkeypatch, whole_error, where) -> None:
    projects = [registry.Project(id=n, path=str(tmp_path / n), added_at=AT) for n in ("beta", "gamma")]
    with registry.locked():
        registry.save(registry.Machine(projects=projects))
    error = (registry.RegistryError if where == "registry" else OSError)(whole_error)
    error.add_note("a note added on the way up")
    real = pack_run_record.observed

    def raising(*args):
        if where == "record" and args[0] != project_home.home("gamma"):
            return real(*args)
        raise error

    monkeypatch.setattr(*((registry, "load") if where == "registry" else (pack_run_record, "observed")), raising)
    beta = Store(project_home.home("beta"), None, "beta")
    c = TestClient(api.create_app(beta, "t", None), base_url="http://127.0.0.1", headers={"Authorization": "Bearer t"})

    got = c.get("/api/next/maintenance/pack/runs").json()

    whole = f"{type(error).__name__}: {whole_error}\na note added on the way up"
    if where == "registry":
        said = f"the machine's registry cannot be read, so other projects' runs are not shown: {whole}"
        assert (got["registry"], [r["pid"] for r in got["runs"]]) == (said, [""])
    else:
        errors = {r["pid"]: (r["state"], r["error"]) for r in got["runs"]}
        assert errors["gamma"] == ("unreadable", f"its run record cannot be read ({whole})")
