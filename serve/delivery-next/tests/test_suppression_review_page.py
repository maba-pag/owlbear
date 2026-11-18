"""The real Maintenance actions, review row and owner confirmations in Chromium."""

from types import SimpleNamespace

import pytest
from owlbear_quality import ledger
from playwright.sync_api import expect

from owlbear_delivery_next.audit_runs import job, record
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.local_system import data_place
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import Store

from .test_approval_view import big
from .test_audit_runs import _report as report
from .test_machine_pages import browsing, clone


def confirmation(page, pds, trigger, title, *, destructive=False):
    trigger.click()
    expect(page.get_by_role("dialog", name=title)).to_be_visible()
    modal = pds.modal(page)
    primary = modal.locator('p-button[variant="primary"]')
    expect(primary).to_have_count(1)
    if destructive:
        expect(primary).to_have_text("Cancel")
    for control in modal.get_by_role("button").all():
        big(control)
    for _ in range(8):
        page.keyboard.press("Tab")
        assert page.evaluate(pds.INSIDE)
    pds.answer(page, "Cancel")
    expect(trigger).to_be_focused()


@pytest.mark.browser
def test_suppression_review_is_visible_bounded_and_owner_confirmed(tmp_path, pds, monkeypatch, shared_repo, github):
    monkeypatch.setenv(data_place.VIEW, str(shared_repo[0]))
    work = clone(tmp_path / "shop", origin="https://github.com/acme/shop.git")
    worktree.git(work, "branch", "-M", "main")
    entry, store = registry.register(work), Store.open(work)
    store.write_profile(Profile(entries={profile.DEFAULT: ProfileEntry(state="known", value="main")}))
    items = [
        {"identity": f"i{n}", "place": f"serve/app/src/a.py:{n + 1}", "directive": "noqa: F841", "code": "x"}
        for n in range(3)
    ]
    running, launched = [], []
    monkeypatch.setattr(job.github_writer, "of", lambda *_args: SimpleNamespace(access=lambda: None))
    monkeypatch.setattr(job.workspace, "pin", lambda *_args: worktree.head(work))
    monkeypatch.setattr(job.Audits, "busy", lambda _self: bool(running))

    def launch(audits, audit, state, *, resume):
        assert audit == "suppressions"
        assert not resume
        state.update(inventory=items, counts={"held": 3, "accepted": 0, "refused": 0, "unjudged": 3})
        record.active(audits.store, audit, running=True)
        record.save(audits.store, audit, state)
        running.append(True)
        launched.append((audits.store, state))

    monkeypatch.setattr(job.Audits, "_launch", launch)
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/maintenance?project={entry.id}#token=t")
        row = page.locator("#actions > li", has_text="Suppression review")
        expect(row).to_have_count(1)
        expect(row.locator("p-textarea")).to_have_count(0)
        start = row.get_by_role("button", name="Start review", exact=True)
        expect(start).to_be_enabled()
        confirmation(page, pds, start, "Start suppression review?")
        assert not launched
        start.click()
        expect(pds.modal(page)).to_contain_text("at most 10 batches of 60")
        expect(pds.modal(page)).to_contain_text("Quality judge")
        pds.answer(page, "Start review")
        expect(row).to_contain_text("Running since")
        expect(start).to_be_disabled()
        review_store, last = launched[0]
        reason = "The code can meet the rule. " * 20
        ledger.add(
            review_store.root,
            [
                {
                    "identity": items[n]["identity"],
                    "place": items[n]["place"],
                    "directive": "noqa: F841",
                    "commit": last["commit"],
                    "by": "quality-judge (fixture)",
                    "for": "review",
                    "verdict": v,
                    "reason": reason,
                }
                for n, v in enumerate(("accepted", "refused"))
            ],
        )
        finding = report()["findings"][0] | {"number": 12, "url": "https://github.com/acme/owlbear-data/issues/12"}
        last.update(state="done", phase="", ended_at=record.now(), findings=[finding])
        record.save(review_store, "suppressions", last)
        record.active(review_store, "suppressions", running=False)
        running.clear()
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        expect(row).to_contain_text("3 held")
        expect(row).to_contain_text("1 accepted")
        expect(row).to_contain_text("1 refused")
        expect(row).to_contain_text("1 not yet judged: start again to continue")
        expect(row.get_by_role("link", name="#12", exact=False)).to_have_attribute("href", finding["url"])
        verdict_controls(page, row, pds)
        assert not github.issues


def verdict_controls(page, row, pds):
    row.get_by_role("button", name="Verdicts", exact=True).click()
    lines = row.locator(".suppression-verdicts > li")
    expect(lines).to_have_count(2)
    expect(lines.nth(1)).to_contain_text(("The code can meet the rule. " * 20).strip())
    for control in row.get_by_role("button").all():
        big(control)
    assert row.locator(".review-text").evaluate_all("""nodes => nodes.every(e => {
      const c = document.createElement('canvas').getContext('2d');
      c.font = getComputedStyle(e).font;
      return e.getBoundingClientRect().width <= c.measureText('0'.repeat(75)).width + 1;
    })""")
    refused = lines.filter(has_text="refused")
    confirmation(
        page,
        pds,
        refused.get_by_role("button", name="Judge again"),
        "Judge these suppressions again?",
        destructive=True,
    )
    accept = refused.get_by_role("button", name="Accept", exact=True)
    confirmation(page, pds, accept, "Accept these suppressions?")
    accept.click()
    pds.answer(page, "Accept")
    expect(row).to_contain_text("2 accepted")
    expect(row).to_contain_text("Owner accepted the suppression.")
