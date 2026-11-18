"""One browser look at current committed suppressions, using the real Change status response and ledger."""

import shutil

import pytest
from owlbear_quality import ledger
from owlbear_quality.inspect import added
from playwright.sync_api import expect

from owlbear_delivery_next.change_flow import quality
from owlbear_delivery_next.project_host import change_view

from . import test_quality_gate
from .test_approval_view import big
from .test_change_page_view import opened

project = test_quality_gate.project


@pytest.mark.browser
def test_change_suppressions_need_the_owner_by_default_and_acceptances_are_details(c1, pds, project):
    root, fixture, base = project
    head = test_quality_gate.commit(
        root,
        {
            f"{name}.txt": f"# editorconfig-checker-disable-next-line\n{name}_boundary\n"
            for name in ("refused", "unjudged", "accepted")
        },
    )
    store, _ = c1
    reason = "This code can meet the rule without an exception. " * 8 + "Keep this final sentence visible too."
    for addition in added(quality.git, root, base, head):
        name = addition.places[0].path
        if name != "unjudged.txt":
            ledger.add(
                store.root,
                [
                    {
                        "identity": addition.identity,
                        "verdict": "refused" if name == "refused.txt" else "accepted",
                        "reason": reason
                        if name == "refused.txt"
                        else "The generated boundary requires this exception.",
                        "by": "quality-judge (fixture-model)",
                        "for": "c1-fixture",
                        "commit": head,
                        "place": f"{name}:1",
                    }
                ],
            )

    def edit(change):
        change.names, change.plan, change.step = fixture.names, fixture.plan, fixture.step
        change.outcome = None

    with opened(c1, pds, edit) as page:
        shown = page.locator(".suppressions")
        expect(shown).to_have_count(1)
        expect(shown.locator(":scope > ul > li")).to_have_count(2)
        expect(shown).to_contain_text("refused.txt:1")
        expect(shown).to_contain_text("unjudged.txt:1")
        expect(shown).to_contain_text("(not judged)")
        expect(shown).to_contain_text("No verdict has been given for this Change.")
        expect(shown).to_contain_text(reason)
        expect(shown).to_contain_text("Ruled by quality-judge (fixture-model)")
        expect(shown).not_to_contain_text("accepted.txt")
        assert shown.locator("[title], [data-tooltip]").count() == 0
        assert shown.evaluate("""e => {
            const context = document.createElement('canvas').getContext('2d');
            context.font = getComputedStyle(e).font;
            return e.getBoundingClientRect().width <= context.measureText('0'.repeat(75)).width + 1;
        }""")
        expect(shown.locator("xpath=preceding-sibling::ol[1]")).to_contain_text("Build")
        pds.settled(page)
        switch = page.locator("#details-switch")
        big(switch)
        switch.focus()
        page.keyboard.press("Space")
        expect(shown.locator(":scope > ul > li")).to_have_count(3)
        expect(shown).to_contain_text("accepted.txt:1")
        expect(shown).to_contain_text("The generated boundary requires this exception.")
        quality.git(root, ["branch", "-D", "main"])
        page.reload()
        expect(page.get_by_text("Suppressions could not be read", exact=True)).to_be_visible()
        expect(page.locator("#detail")).to_contain_text("fatal: Not a valid object name main")
        expect(page.get_by_role("button", name="Pause", exact=True)).to_be_enabled()
        ledger.add(
            store.root,
            [
                {
                    "identity": "extra",
                    "verdict": "refused",
                    "reason": "Another verdict.",
                    "by": "quality-judge (fixture-model)",
                    "for": "c1-fixture",
                    "commit": head,
                    "place": "extra.txt:1",
                }
            ],
        )
        shutil.rmtree(root)
        rows = change_view.suppressions(store, store.read("c1-fixture"))
        assert sorted(rows, key=lambda row: row["place"]) == [
            {
                "place": "accepted.txt:1",
                "directive": "",
                "verdict": "accepted",
                "reason": "The generated boundary requires this exception.",
                "by": "quality-judge (fixture-model)",
            },
            {
                "place": "extra.txt:1",
                "directive": "",
                "verdict": "refused",
                "reason": "Another verdict.",
                "by": "quality-judge (fixture-model)",
            },
            {
                "place": "refused.txt:1",
                "directive": "",
                "verdict": "refused",
                "reason": reason,
                "by": "quality-judge (fixture-model)",
            },
        ]
        page.reload()
        pds.settled(page)
        if not switch.evaluate("e => e.checked"):
            switch.click()
        expect(page.locator(".suppressions")).to_contain_text("accepted.txt:1 (accepted)")
        (store.root / ledger.FILE).unlink()
        page.reload()
        expect(page.locator(".suppressions")).to_have_count(0)
        expect(page.get_by_role("heading", name="Added suppressions")).to_have_count(0)
