"""The Maintenance page rendered by lit-html in a real browser (TD-264)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from owlbear_delivery_next.change_contracts.models import Brief, Change, StepKind
from owlbear_delivery_next.local_system import data_place, local_home
from owlbear_delivery_next.machine_host import curation
from owlbear_delivery_next.project_host import pack_routes
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import Lock, Store

from .test_machine_pages import browsing, clone

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.browser
def test_the_maintenance_page_lists_each_action_and_says_when_delivery_stops(tmp_path: Path, pds, monkeypatch) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    work = clone(tmp_path / "work")
    entry = registry.register(work)
    store = Store.open(work)
    with browsing(monkeypatch, pds) as (page, base):
        page.set_viewport_size({"width": 1280, "height": 720})
        page.goto(f"{base}/maintenance?project={entry.id}#token=t")
        actions = page.locator("#actions > li")
        expect(actions).to_have_count(5)
        expect(actions.nth(1)).to_contain_text("Impeccable update")
        expect(page.get_by_role("link", name="Open Memory curation in Memory")).to_have_attribute(
            "href", f"/memory?project={entry.id}"
        )
        expect(actions.nth(2)).to_contain_text("No run record kept.")
        expect(page.locator("#use-none")).to_have_text("No step has run in this project yet.")
        store.write(Lock("a"), Change(slug="a", brief=Brief(version=1)))
        ran = [{"agent": "explore", "credits": 1.25, "credits_known": True}]
        store.log(Lock("a"), "a", {"event": "step", "session": "s1", "kind": "build", "subagents": ran})
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        expect(page.locator("#use p-table-cell")).to_have_text(["builder", "1", "1", "1", "1.25", "explore 1"])
        expect(page.locator("#error")).to_be_hidden()
        assert page.evaluate("location.hash") == ""  # the token left the address bar
        held = []  # what Delivery takes but never answers: up, yet busy

        def hold(route) -> None:
            held.append(route)

        page.route("**/api/next/maintenance/subagents", hold)
        page.route("**/api/next/project", lambda r: r.abort("connectionrefused"))
        caught = page.evaluate("""async () => {
          const ui = await import("/assets/ui.mjs"), caught = [];
          for (const [path, method] of [["/maintenance/subagents", "GET"], ["/maintenance/subagents", "POST"],
            ["/project", "GET"]]) {
            await ui.call(path, { method, timeout: 200 }).catch((e) => caught.push({ slow: e instanceof ui.Slow,
              down: e instanceof ui.HostDown, sent: e.sent ?? null, said: e.message }));
          }
          return caught;
        }""")
        unsure = "Delivery did not answer within 0.2 s, so this may have been done or not. It was not sent again;"
        assert caught == [
            {"slow": True, "down": False, "sent": False,
             "said": "Delivery is slow to answer: no reply within 0.2 s. Try again in a moment."},
            {"slow": True, "down": False, "sent": True,
             "said": f"{unsure} reload the page to see which before you try again."},
            {"slow": False, "down": True, "sent": None,
             "said": "Delivery is not running. Start it, then reload this page."},
        ]  # fmt: skip
        assert [r.request.method for r in held].count("POST") == 1  # a timed-out write is never sent again
        page.route("**/api/next/**", lambda r: r.abort())
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        expect(page.locator("#error")).to_have_text("Delivery is not running. Start it, then reload this page.")
        expect(actions).to_have_count(5)  # what it showed stays


@pytest.mark.browser
def test_memory_curation_says_whether_its_last_run_was_the_curator_or_the_owner(
    tmp_path: Path, pds, monkeypatch, shared_repo
) -> None:
    """N1 (D-01M63CF1XKCCF6TP60734BTMWD): it said "Never run." after a curation run, and never said who ran it."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    monkeypatch.setenv(data_place.VIEW, str(shared_repo[0]))
    work = clone(tmp_path / "shop", origin="https://github.com/acme/shop.git")
    entry = registry.register(work)
    Store.open(work)
    ran = datetime.now(UTC) - timedelta(hours=1)
    run = curation.FolderRun(state="done", started_at=ran - timedelta(minutes=1), ended_at=ran)
    (local_home.root() / curation.STATE).write_text(curation.Runs(folders={"shop": run}).model_dump_json())
    with browsing(monkeypatch, pds) as (page, base):
        page.set_viewport_size({"width": 1280, "height": 720})
        page.goto(f"{base}/maintenance?project={entry.id}#token=t")
        memory = page.locator("#actions > li", has_text="Memory curation")
        expect(memory).to_contain_text("Last run (memory curator): done, ")
        expect(memory).not_to_contain_text("Never run.")
        action = {"by": "owner", "state": "done", "action": "approve Run ruff first", "ended_at": ran.isoformat()}

        def owned(route) -> None:
            body = route.fetch().json()
            route.fulfill(json=[a | {"last": action} if a["name"] == "Memory curation" else a for a in body])

        page.route("**/api/next/maintenance", owned)
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        expect(memory).to_contain_text("Last run (your memory action): approve Run ruff first, ")
        expect(memory).not_to_contain_text("memory curator")


@pytest.mark.browser
def test_unreadable_curation_runs_show_whole_on_memory_curation(
    tmp_path: Path, pds, monkeypatch, whole_error, shared_repo
) -> None:
    """#971: why memory curation's runs are not counted shows whole under its last run."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    monkeypatch.setenv(data_place.VIEW, str(shared_repo[0]))
    work = clone(tmp_path / "shop", origin="https://github.com/acme/shop.git")
    entry = registry.register(work)
    Store.open(work)
    run = curation.FolderRun(state="done", started_at=datetime.now(UTC), ended_at=datetime.now(UTC))
    (local_home.root() / curation.STATE).write_text(curation.Runs(folders={"shop": run}).model_dump_json())
    error = ValueError(whole_error)
    error.add_note("a note added on the way up")

    def unreadable(_text: str):
        raise error

    with browsing(monkeypatch, pds) as (page, base):
        page.set_viewport_size({"width": 1280, "height": 720})
        monkeypatch.setattr(pack_routes.curation_runs.Runs, "model_validate_json", unreadable)
        page.goto(f"{base}/maintenance?project={entry.id}#token=t")
        reason = page.locator("#actions > li", has_text="Memory curation").locator("p-text[size='xs']")
        expect(reason).to_have_count(1)
        assert reason.text_content() == (
            "memory curation's runs could not be read, so they are not counted: "
            f"ValueError: {whole_error}\na note added on the way up"
        )


@pytest.mark.browser
def test_the_test_review_starts_from_the_chosen_packages_once_confirmed(tmp_path: Path, pds, monkeypatch) -> None:
    """TD-370, TD-390: every package is chosen, the dialog says what runs, and the Start opens one Change."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    work = tmp_path / "work"
    for name in ("pyproject.toml", "tests/test_a.py", "web/package.json", "web/src/b.test.ts"):
        (work / name).parent.mkdir(parents=True, exist_ok=True)
        (work / name).write_text("x\n")
    who = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-qm", "base"]):
        subprocess.run([*who, *args], cwd=work, check=True, capture_output=True)  # noqa: S603
    store = Store.open(work)
    entry = registry.register(work)
    with browsing(monkeypatch, pds) as (page, base):
        page.set_viewport_size({"width": 1280, "height": 720})
        page.goto(f"{base}/maintenance?project={entry.id}#token=t")
        tests = page.locator("#tests")
        expect(tests.get_by_role("checkbox")).to_have_count(2)
        expect(page.locator("#tests-runs")).to_contain_text("2 reviewer sessions on gpt-6.1-sol at medium effort")
        tests.get_by_label("the repository's root: 1 files, 1 lines, 1 share").uncheck()
        expect(page.locator("#tests-runs")).to_contain_text("1 reviewer session on")
        page.get_by_role("button", name="Review tests").click()
        expect(page.get_by_role("dialog", name="Review the tests?")).to_be_visible()
        expect(pds.modal(page)).to_contain_text("which your Start approves")
        pds.answer(page, "Cancel")
        expect(page.get_by_role("dialog")).to_be_hidden()
        assert store.slugs() == []  # declined: nothing starts
        page.get_by_role("button", name="Review tests").click()
        pds.answer(page, "Start the test review")
        expect(page.locator("#status")).to_contain_text("Started test review c1")
        expect(tests).to_contain_text("Test review c1 has not finished")
        assert len(store.slugs()) == 1
        c = store.read(store.slugs()[0])
        assert (c.step.kind, c.tests.packages) == (StepKind.TESTS, ["web"])
