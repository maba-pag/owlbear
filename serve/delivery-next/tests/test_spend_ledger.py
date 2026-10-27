"""The spend ledger (D-01M5XCDF6G60VG5GHTWF5QSSDE): a run's start and end, written off the caller's thread."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from owlbear_delivery_next.state_store import spend_ledger
from owlbear_delivery_next.state_store.spend_ledger import Where
from owlbear_delivery_next.state_store.store import Store


def written() -> list[dict]:
    assert spend_ledger.WRITER.settled(5)
    return spend_ledger.lines()


def test_a_run_writes_its_start_and_end_with_where_it_ran_and_the_sessions_own_job() -> None:
    place = Where(project="owlbear", name="owlbear", clone="c1", change="fix-it", step="build", job="chat lookup")
    with spend_ledger.at(place):
        spend_ledger.started("r1", "s1", agent="picker", job="decision-pick", model="m1", before={})
        spend_ledger.ended("r1", "s1", usage={"credits": 0.5, "models": {}}, ending="result", limit=2.0)
    spend_ledger.started("r2", "s2", agent="curator", job="", model="m1", before=None)
    first, last, other = written()
    assert first | {"at": ""} == {
        "id": "start:r1", "type": "start", "run": "r1", "at": "", "session": "s1", "agent": "picker", "model": "m1",
        "before": {}, "project": "owlbear", "name": "owlbear", "clone": "c1", "change": "fix-it", "step": "build",
        "job": "decision-pick",
    }  # fmt: skip
    assert (last["usage"]["credits"], last["limit"], last["job"], last["change"]) == (0.5, 2.0, "", "fix-it")
    assert (other["project"], other["job"], other["before"]) == ("", "", None)  # machine-wide: no place set
    files = list(spend_ledger.folder().glob("spend-*.jsonl"))
    assert len(files) == 1
    assert oct(files[0].stat().st_mode & 0o777) == "0o600"


def test_a_place_reaches_tasks_and_threads_the_block_starts() -> None:
    async def inside() -> tuple[str, str]:
        task = await asyncio.create_task(asyncio.sleep(0, spend_ledger.where().change))
        return task, await asyncio.to_thread(lambda: spend_ledger.where().change)

    with spend_ledger.at(Where(change="c")):
        assert asyncio.run(inside()) == ("c", "c")
    assert spend_ledger.where() == Where()


def test_a_store_names_its_project_by_its_shared_folder_else_its_clone(tmp_path: Path) -> None:
    home = tmp_path / "projects" / "0123456789abcdef"
    assert Where.of(Store(home, None, "owlbear"), tmp_path / "owlbear-dev") == Where(
        project="owlbear", name="owlbear", clone="0123456789abcdef"
    )
    assert Where.of(Store(home), tmp_path / "scratch") == Where(
        project="0123456789abcdef", name="scratch", clone="0123456789abcdef"
    )


def test_a_line_that_cannot_be_written_is_kept_and_written_with_the_next(capsys) -> None:
    spend_ledger.folder().parent.mkdir(parents=True, exist_ok=True)
    spend_ledger.folder().write_text("not a folder")  # every write fails, and never raises
    spend_ledger.started("r1", "s1", agent="builder", job="", model="m1", before={})
    assert spend_ledger.WRITER.settled(5)
    assert [line["id"] for line in spend_ledger.WRITER.unwritten] == ["start:r1"]
    assert "kept to try again" in capsys.readouterr().err
    spend_ledger.folder().unlink()
    spend_ledger.ended("r1", "s1", usage={"error": "not read"}, ending="interrupted")
    assert [line["id"] for line in written()] == ["start:r1", "end:r1"]
    assert spend_ledger.WRITER.unwritten == []


def test_reading_skips_damaged_lines_and_repeated_ids() -> None:
    spend_ledger.folder().mkdir(parents=True)
    line = json.dumps({"id": "look:1", "type": "look"})
    (spend_ledger.folder() / "spend-2026-10.jsonl").write_text(f"{line}\nnot json\n{line}\n[1]\n")
    assert spend_ledger.lines() == [{"id": "look:1", "type": "look"}]
