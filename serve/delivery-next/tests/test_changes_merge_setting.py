"""The Changes page words the merge and branch settings as they are set: ask, by itself, or not set yet (TD-447 area).

The served forms module renders a person check with the status payload the API sends for each setting, so an unset
(null) value shows as unset and never as the false or true wording.
"""

from __future__ import annotations

import contextlib
import socket
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts import models as m
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.state_store.store import Lock, Store

if TYPE_CHECKING:
    from collections.abc import Iterator

NOW = datetime(2026, 10, 16, 2, tzinfo=UTC)
SETTINGS = (True, False, None)  # ask before merging, merge by itself, not set yet


class Host:
    wake = type("W", (), {"set": staticmethod(lambda: None)})()
    maintenance = None
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW, code=CURRENT)  # noqa: S106

    def activity(self, _slug: str) -> Activity:
        return Activity(host_up=True)


def change() -> m.Change:
    brief = m.Brief(
        version=2, challenged=0, title="Flip the hero", outcome="Visitors flip the hero image with one button.",
        criteria=[m.Criterion(id="AC-1", text="Turns the hero 180 degrees in under 300 ms")],
        visual=[m.VisualState(name="flipped", path="/", expect="The hero faces left")], ui=True,
        decisions=[m.BriefDecision(question="Hero motion", answer="Never autoplay", origin="decided")],
        non_goals=[], specified=["AC-1"],
    )  # fmt: skip
    checks = [m.PersonCheck(id="feel", steps=["Flip five times"], expect="No stutter")]
    return m.Change(slug="flip", brief=brief, checks=checks, step=m.Step(kind=m.StepKind.SHAPE))


@pytest.fixture
def page_url(tmp_path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> Iterator[tuple[Store, str]]:
    """A synthetic project whose base layer sets the two preferences to the parametrized values."""
    ask, delete = request.param
    base = config.BASE
    prefs = base.prefs.model_copy(update={"ask_before_merge": ask, "delete_remote_branch": delete})
    monkeypatch.setattr(config, "BASE", base.model_copy(update={"prefs": prefs}))
    store = Store(tmp_path)
    store.write(Lock("flip"), change())
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", Host()), log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    yield store, f"http://127.0.0.1:{sock.getsockname()[1]}"
    server.should_exit = True


@contextlib.contextmanager
def opened(base: str, slug: str, pds: Any) -> Iterator[Any]:
    """The Changes page on *slug* in a real browser: only the test host and the PDS CDN answer."""
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Error as exc:
            pytest.skip(f"no Playwright Chromium: {exc}")
        page = browser.new_page()
        pds.only(page, base)
        page.add_init_script("sessionStorage.setItem('token', 'tok');")
        page.goto(f"{base}/?change={slug}")
        yield page
        browser.close()


# The served forms module renders the person check beside the real settings; the rendered buttons show whether a
# click would open the merge dialog (only the last gate with an automatic merge does).
RENDER = """
async (status) => {
  const forms = await import("/assets/page/changes/forms.mjs");
  const { render } = await import("/assets/lit-html/3.3.3/lit-html.js");
  const d = { key: "flip", target: "main", pr: 657, asks_merge: status.asks_merge,
    deletes_branch: status.deletes_branch, checks: [{ id: "feel", passed: null }] };
  const box = document.createElement("div");
  document.body.append(box);
  render(
    forms.checkForm({ id: "feel", steps: ["Flip five times"], expect: "No stutter", inputs: {}, url: null }, d),
    box,
  );
  return {
    merging: forms.merging(d),
    finale: forms.finale(d),
    text: box.textContent,
    buttons: [...box.querySelectorAll("p-button")].map((b) => ({
      text: b.textContent.trim(), dialog: b.getAttribute("aria") !== null })),
  };
}
"""


@pytest.mark.browser
@pytest.mark.parametrize(
    ("page_url", "ask", "delete"),
    [  # only an automatic merge words the branch setting
        pytest.param((a, d), a, d, id=f"merge-{a}-branch-{d}")
        for a, d in [(False, d) for d in SETTINGS] + [(True, True), (None, True)]
    ],
    indirect=["page_url"],
)
def test_the_changes_page_words_each_merge_and_branch_setting_as_it_is_set(page_url, pds, ask, delete) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _store, base = page_url
    with opened(base, "flip", pds) as page:
        status = page.evaluate(
            "async () => (await fetch('/api/next/changes/flip', { headers: { Authorization: 'Bearer tok' } })).json()"
        )
        assert status["asks_merge"] is ask  # the API sends the stored value, null while unset
        assert status["deletes_branch"] is delete
        shown = page.evaluate(RENDER, status)
        if ask is False:  # the last gate of an automatic merge opens the dialog that says it merges
            page.locator("p-button", has_text="Passed").last.click()
            opened_dialog = page.get_by_role("dialog", name="Pass feel, the last step before merging?")
            expect(opened_dialog).to_be_visible()
            # p-modal keeps its copy in light DOM (.parts) while its role=dialog sits in the shadow root
            dialog_text = page.evaluate("() => document.querySelector('p-modal.ask .parts')?.textContent ?? ''")
            assert shown["finale"] in dialog_text, dialog_text  # the dialog states what the automatic merge does
            expect(page.locator("p-modal.ask p-button", has_text="Pass and merge")).to_be_visible()
            page.locator("p-modal.ask p-button", has_text="Not yet").click()

    buttons = {b["text"]: b["dialog"] for b in shown["buttons"]}
    assert set(buttons) == {"Passed", "Failed"}
    if ask is False:
        assert shown["merging"] == "Delivery merges by itself once every check passes"
        assert buttons["Passed"] is True  # the last gate opens the "Pass and merge" dialog
        assert ("deletes the branch" in shown["finale"]) is (delete is True)
    else:
        assert "by itself" not in shown["text"]  # no automatic merge promised for ask or unset
        assert buttons["Passed"] is False  # no merge dialog: Delivery asks you, or the setting is not set yet
        assert "deletes the branch" not in shown["text"]  # the branch-deletion claim is only in the automatic finale
    if ask is True:
        assert shown["merging"] == "Delivery asks you before merging"
    if ask is None:
        assert shown["merging"] == "Delivery does not merge until the merge setting is chosen on the Settings page"
        assert "asks you" not in shown["text"]
