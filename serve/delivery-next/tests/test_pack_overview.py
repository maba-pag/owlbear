"""Read the machine's last update and old waiting updates without writing."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.impeccable_runs import pack_job, pack_state
from owlbear_delivery_next.machine_host import update_job_routes
from owlbear_delivery_next.state_store import pack_run_record, project_home, registry, update_home

AT = datetime(2026, 10, 17, 2, tzinfo=UTC)


def client():
    app = FastAPI()
    app.include_router(update_job_routes.read_routes(), prefix="/api/next")
    return TestClient(app, base_url="http://127.0.0.1")


def test_machine_view_reads_its_own_run_and_lists_only_old_waiting_runs(tmp_path) -> None:
    left = pack_state.blank() | {"state": "running", "run": "r-machine", "started_at": "2026-10-17T02:00:00+00:00",
                                 "context": {"sid": "kept out of the page"}}  # fmt: skip
    projects = [registry.Project(id=n, path=str(tmp_path / n), added_at=AT) for n in ("alpha", "beta", "gamma")]
    with registry.locked():
        registry.save(registry.Machine(projects=projects))
    pr = {"number": 8, "url": "https://github.com/maba-pag/owlbear/pull/8"}
    old = {**left, "state": "waiting", "context": {"publication": pr}}
    for name, text in {"alpha": json.dumps(old), "beta": json.dumps(left), "gamma": "{"}.items():
        project_home.home(name).mkdir(parents=True)
        (project_home.home(name) / pack_job.FILE).write_text(text)
    before = (project_home.home("alpha") / pack_job.FILE).read_bytes()
    update_home.root().mkdir()
    (update_home.root() / pack_job.FILE).write_text(json.dumps(left | {"invocations": []}))

    got = client().get("/api/next/maintenance/pack/runs").json()

    run = got["run"]
    assert (run["run"], run["state"]) == ("r-machine", "running")
    assert run["interrupted"] is True  # no host holds the machine's lock for it
    assert "context" not in run
    assert "stages" not in run
    assert run["progress"]["phases"] == []
    assert got["old_waiting"] == [{"name": "alpha", **pr}]
    assert "gamma: the update record" in got["errors"][0]
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
    got = client().get("/api/next/maintenance/pack/runs").json()

    whole = f"{type(error).__name__}: {whole_error}\na note added on the way up"
    if where == "registry":
        said = f"the machine's registry cannot be read, so old waiting runs are not shown: {whole}"
        assert got["errors"] == [said]
    else:
        assert got["errors"] == [f"gamma: the update record in {project_home.home('gamma')} cannot be read: {whole}"]
