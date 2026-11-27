"""The demo's six example Changes, each under a fixed slug, written through Delivery's own question and stop code.

Only the inputs are made up here: briefs, a challenge finding, a worker's proposal and a repair's evidence. The
questions, their options and the stop report come from ``brief_rounds.question``, ``worker_questions.admitted`` and
``stuck.stopped``, as a running Delivery would write them.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import pick_tools, tools
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    Criterion,
    ErrorKind,
    Exit,
    Names,
    Plan,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.repair_records import Tried
from owlbear_delivery_next.change_contracts.round_records import BRIEF, RoundFinding, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import brief_rounds, loop, moves, stuck
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import worker_questions

if TYPE_CHECKING:
    from pathlib import Path

SHOP, DOCS = "example-shop", "example-docs"
CHANGES = (  # (project, slug): the address of each is /?change=<the project's id>/<slug> on every start
    (SHOP, "example-shop-cart-badge"),  # being built
    (SHOP, "example-shop-gift-cards"),  # waiting on a disputed brief finding
    (SHOP, "example-shop-search-filters"),  # waiting on a worker's question
    (DOCS, "example-docs-link-checker"),  # stopped after a failed repair
    (DOCS, "example-docs-dark-theme"),  # paused
    (DOCS, "example-docs-install-guide"),  # done
)


def seed(clones: dict[str, Path]) -> None:
    """Write the six Changes into the stores of the registered example projects, named in *clones*."""
    now = datetime.now(UTC)
    made = [_building(now), _disputed(now), _asking(now), _stopped(now), _paused(now), _done(now)]
    for (project, slug), c in zip(CHANGES, made, strict=True):
        store = Store.open(clones[project])
        with store.lock(slug) as lock:
            store.write(lock, c)


def _change(n: int, title: str, outcome: str, criteria: list[str], *, approved: bool = True) -> Change:
    slug = CHANGES[n][1]
    brief = Brief(
        version=1,
        title=title,
        outcome=outcome,
        scope=["src/", "tests/"],
        criteria=[Criterion(id=f"AC-{i}", text=t) for i, t in enumerate(criteria, 1)],
    )
    if approved:
        brief.approved = [brief.model_copy(deep=True)]
        brief.approved_version, brief.challenged = 1, 1
    names = Names(branch=f"owlbear/{slug}", target="main")
    return Change(slug=slug, handle=f"c{n % 3 + 1}", profile_version=1, brief=brief, names=names)


def _plan(*titles: str) -> Plan:
    return Plan(tasks=[Task(id=f"t{i}", title=t, scope=["src/"]) for i, t in enumerate(titles, 1)])


def _building(now: datetime) -> Change:
    c = _change(
        0,
        "A count badge on the cart icon",
        "Shoppers see how many items their cart holds without opening it.",
        ["The cart icon shows the number of items in the cart, and no badge when it is empty."],
    )
    c.brief.approved_at = now - timedelta(hours=3)
    c.plan = _plan("Count the cart's items for the header", "Show the badge on the cart icon")
    c.plan.tasks[0].done = True
    c.step = Step(kind=StepKind.BUILD, task="t2", started_at=now - timedelta(minutes=12))
    return c


def _disputed(now: datetime) -> Change:
    c = _change(
        1,
        "Gift cards at checkout",
        "Shoppers can pay part or all of an order with a gift card code.",
        ["A valid gift card code lowers the order total by its balance, at most to zero."],
        approved=False,
    )
    c.brief.requested = 1
    finding = RoundFinding(
        id="F1",
        text="AC-1: an expired or already used code is not covered - fix: say what the shopper sees for each",
        raised=1,
        state="escalated",
        reason="Expired and used codes are the payment provider's errors, shown as they come; no criterion needed.",
        judgement="The provider's message is in English only, and the shop is in German and French too.",
    )
    lp = RoundLoop(subject=BRIEF, round=2, policy=RoundPolicy(), findings=[finding], head="1")
    c.loops[BRIEF] = lp
    moves.ask(c, brief_rounds.question(lp, finding), now - timedelta(minutes=40))
    return c


def _asking(now: datetime) -> Change:
    c = _change(
        2,
        "Filters on the search results",
        "Shoppers narrow search results by price, size and colour.",
        ["The results page offers price, size and colour filters, and the count updates as each is set."],
    )
    c.brief.approved_at = now - timedelta(days=1)
    c.plan = _plan("Filter the search query", "The filter panel on the results page")
    c.step = Step(kind=StepKind.BUILD, task="t1", started_at=now - timedelta(minutes=25))
    proposed = tools.AskQuestion(
        question="Should the colour filter offer only colours in stock, or every colour the shop has ever sold?",
        why="The brief names the colour filter but not which colours it lists; that changes what shoppers see.",
        options=[
            {"label": "In stock only", "effect": "List only colours with stock today.", "action": "continue"},
            {
                "label": "Every colour",
                "effect": "List every colour, greyed out when none is in stock.",
                "action": "continue",
            },
            {"label": "Pause", "effect": "Pause the Change until the shop decides.", "action": "pause"},
        ],
        recommended=0,
    )
    verdict = pick_tools.QuestionJudgment(
        subject="product",
        plain=True,
        why="Which colours the filter offers changes what the shopper sees.",
        options=[
            {
                "index": i,
                "executable": True,
                "why": "The current step carries it.",
                "check_related": False,
                "recommends": i == 0,
            }
            for i in range(3)
        ],
    )
    return loop.apply(c, worker_questions.admitted(c, proposed, verdict, None), now - timedelta(minutes=8))


EVIDENCE = """The step's checks failed: `npm run test:links` exited 1 after 41.2 s.
docs/install.md:14: https://example.invalid/downloads/latest -> 404 Not Found
docs/install.md:52: https://example.invalid/downloads/checksums.txt -> 404 Not Found
docs/guide/upgrade.md:8: ../install.md#before-you-start -> anchor not found
docs/guide/upgrade.md:61: https://status.example.invalid/ -> timed out after 10 s (3 tries)
docs/reference/cli.md:203: ./flags.md#--dry-run -> anchor not found
5 broken links in 3 of 48 files; 1 211 links checked."""


def _stopped(now: datetime) -> Change:
    c = _change(
        3,
        "Check every link in the docs on each build",
        "A broken link in the docs fails the build instead of reaching readers.",
        ["The docs build fails and names the file and line of each link that does not answer."],
    )
    c.brief.approved_at = now - timedelta(days=2)
    c.plan = _plan("Run the link checker in the docs build")
    c.step = Step(kind=StepKind.BUILD, task="t1", started_at=now - timedelta(hours=2))
    stuck.start(c, cause_key(ErrorKind.PROJECT_ENV, StepKind.BUILD, "links"), EVIDENCE, now - timedelta(hours=1))
    if r := c.repairs.current:  # what the repair session reported before nothing worked
        r.found = "The download links point at a release page the site no longer has; the status page blocks robots"
        r.tried = [
            Tried(fix="Point the download links at the new release page", outcome="2 links fixed; 3 still failed."),
            Tried(fix="Fix the two anchors in the upgrade guide and CLI docs", outcome="The status page timed out."),
            Tried(fix="Retry the status page with a longer timeout", outcome="It still timed out after 30 s."),
        ]
        r.credits = 4.6
    stuck.stopped(c, "nothing it tried worked", now - timedelta(minutes=50))
    return c


def _paused(now: datetime) -> Change:
    c = _change(
        4,
        "A dark theme for the docs",
        "Readers can switch the docs to a dark theme that follows their system setting.",
        ["The docs follow the reader's system theme, and a switch in the header overrides it."],
    )
    c.brief.approved_at = now - timedelta(days=3)
    c.plan = _plan("Theme colours for both modes", "The theme switch in the header")
    c.step = Step(kind=StepKind.PLAN)
    c.intent.paused_at = now - timedelta(hours=5)
    return c


def _done(now: datetime) -> Change:
    c = _change(
        5,
        "An install guide for Windows",
        "Windows readers install the tool from the docs without asking for help.",
        ["The install page has a Windows section with each step and its expected output."],
    )
    c.brief.approved_at = now - timedelta(days=6)
    c.plan = _plan("Write the Windows section of the install guide")
    c.plan.tasks[0].done = True
    c.names.pr = 42
    c.step = Step(kind=StepKind.CLEANUP)
    return loop.apply(c, loop.StepResult(exit=Exit.DONE), now - timedelta(days=4))
