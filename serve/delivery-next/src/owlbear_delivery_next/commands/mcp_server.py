"""Chat tools over MCP: each tool asks this workspace's client (``chat_client``) of the running host.

The workspace is told at start, before any state is made (``chat_client.workspace``).
"""

from __future__ import annotations

import argparse
import urllib.parse
from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from owlbear_delivery_next.change_contracts import tools  # noqa: TC001 - MCP resolves the tools' annotations at runtime
from owlbear_delivery_next.change_flow import brief_tools
from owlbear_delivery_next.commands.chat_client import Chat, Closed, workspace
from owlbear_delivery_next.project_host import answers

_STATE: dict[str, Chat | Closed] = {}
ASKED = Field(min_length=1, max_length=1000, description="What you need to decide; a reply with failed is no answer")


def _d(name: str, model: type[tools.Args] = brief_tools.BriefDraft) -> Any:  # noqa: ANN401 - a pydantic FieldInfo
    field = model.model_fields[name]
    return Field(description=field.description, examples=field.examples)


mcp = MCPServer(
    "owlbear-delivery",
    instructions="Shape a Change with the owner, save its brief and visual check, show Delivery status, answer a "
    "worker's question, find decisions, record one the owner confirmed or propose one, retire one, queue a "
    "read-back and record one.",
)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
def save_brief(  # noqa: PLR0913 - the brief's nine fields
    *,
    title: Annotated[str, _d("title")] = "",
    outcome: Annotated[str, _d("outcome")] = "",
    criteria: Annotated[list[str] | None, _d("criteria")] = None,
    scope: Annotated[list[str] | None, _d("scope")] = None,
    non_goals: Annotated[list[str] | None, _d("non_goals")] = None,
    decisions: Annotated[list[brief_tools.DecisionDraft] | None, _d("decisions")] = None,
    person_checks: Annotated[list[brief_tools.PersonCheckDraft] | None, _d("person_checks")] = None,
    specified: Annotated[list[str] | None, _d("specified")] = None,
    change: Annotated[str, _d("change")] = "",
) -> dict[str, Any]:
    """Create or revise one Change's brief draft; the reply gives its handle or one error per field to fix."""
    fields = {"title": title, "outcome": outcome, "criteria": criteria or [], "scope": scope or []}
    fields |= {"non_goals": non_goals or [], "decisions": [d.model_dump() for d in decisions or []]}
    checks = [p.model_dump() for p in person_checks or []]
    return _STATE["chat"].save_brief(fields | {"person_checks": checks, "specified": specified or [], "change": change})


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
def save_visual_check(
    change: Annotated[str, _d("change", brief_tools.VisualDraft)],
    ui: Annotated[bool, _d("ui", brief_tools.VisualDraft)],
    states: Annotated[list[brief_tools.VisualStateDraft] | None, _d("states", brief_tools.VisualDraft)] = None,
    steps: Annotated[list[brief_tools.VisualStepDraft] | None, _d("steps", brief_tools.VisualDraft)] = None,
) -> dict[str, Any]:
    """Set a Change's UI flag, the page states Delivery screenshots, and the clicks or typing before each."""
    body = {"change": change, "ui": ui, "states": [s.model_dump() for s in states or []]}
    return _STATE["chat"].save_brief(body | {"steps": [s.model_dump() for s in steps or []]}, "/briefs/visual")


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
def challenge_brief(
    change: Annotated[str, Field(description="Handle of the Change", examples=["c1"])],
    version: Annotated[int, Field(description="The brief version you saved and ask to be challenged", examples=[2])],
    rejected: Annotated[
        list[tools.Rejection] | None,
        Field(
            description="Findings of the previous round you do not take, by ID, with your evidence; the next "
            "challenger judges each"
        ),
    ] = None,
    *,
    retry_pick: Annotated[
        bool,
        Field(
            description="True only to pick the version's decisions again after the pick failed or the decisions "
            "changed; it uses no challenge round and needs no new version"
        ),
    ] = False,
) -> dict[str, Any]:
    """Ask for the brief version's challenge once the draft is ready; waits for its verdict, gives findings by ID."""
    found = [r.model_dump() for r in rejected or []]
    return _STATE["chat"].challenge_brief(change, version, found, retry_pick=retry_pick)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
def show_status(
    change: Annotated[str, Field(description="Handle of one Change; empty for all", examples=["c1"])] = "",
) -> dict[str, Any]:
    """Show each Change's status line, next action and open question with its id, and the Changes page."""
    return _STATE["chat"].show_status(change)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
def answer_question(  # noqa: PLR0913 - the answer, its class and a clarification's confirmed intent
    question: Annotated[str, Field(description="Question id from show_status", examples=["c1.q2"])],
    kind: Annotated[Literal["event", "clarification", "brief_change"], Field(description=answers.KIND)],
    option: Annotated[str, Field(description="Chosen option id, if any", examples=["o1"])] = "",
    text: Annotated[str, Field(description="The owner's answer in words", max_length=2000)] = "",
    statement: Annotated[str, Field(description=answers.STATEMENT, max_length=240)] = "",
    *,
    confirmed: Annotated[bool, Field(description=answers.CONFIRMED)] = False,
) -> dict[str, Any]:
    """Answer one worker question for the owner, classed; read a clarification back to him before you pass it.

    Recovery decisions are made in the Changes page.
    """
    said = {"kind": kind, "statement": statement, "confirmed": confirmed}
    return _STATE["chat"].answer_question(question, option, text, said)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
def find_decisions(
    *,
    text: Annotated[str, Field(description="Words the title or statement holds; empty for all", max_length=200)] = "",
    where: Annotated[
        Literal["project", "global", "all", "owlbear"],
        Field(
            description="This workspace's own decisions (OwlBear's in OwlBear's workspace), Global ones, both, or "
            "OwlBear's own with Global"
        ),
    ] = "all",
    include_retired: Annotated[bool, Field(description="Also replaced, withdrawn and spent decisions")] = False,
) -> dict[str, Any]:
    """Find the decisions in force (and drafts) of this project and Global, with the revision a read-back names."""
    return _STATE["chat"].find_decisions(text, where, include_retired=include_retired)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=False, destructive_hint=False))
def lookup_decisions(question: Annotated[str, ASKED]) -> dict[str, Any]:
    """Ask which decisions govern a question; the picker answers in about a minute, a failure says `failed`."""
    return _STATE["chat"].lookup_decisions(question)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
def record_decision(  # noqa: PLR0913 - the decision's fields
    *,
    title: Annotated[str, Field(description="Short name of the decision", max_length=200)],
    statement: Annotated[str, Field(description="The rule in force, at most two lines", max_length=240)],
    rationale: Annotated[
        str,
        Field(
            description="Why; leave unknown reasons out. Required when it replaces one: why the rule changes",
            max_length=4000,
        ),
    ] = "",
    topic: Annotated[str, Field(description="Topic it belongs to, if any", max_length=80)] = "",
    scope: Annotated[
        Literal["here", "global"],
        Field(description="here: this project (OwlBear's own in OwlBear's workspace); global: every project"),
    ] = "here",
    confirmed: Annotated[
        bool,
        Field(
            description="True only when the owner confirmed this statement in this chat after you read it back to "
            "him; it is then his decision, in force at once. False: your own choice, a draft he activates. Never "
            "pass his words."
        ),
    ] = False,
    replaces: Annotated[brief_tools.Replacement | None, Field(description="The decision it replaces, if any")] = None,
) -> dict[str, Any]:
    """Record a decision the owner confirmed (in force at once), or propose your own as a draft.

    Read back free text and unclear answers at once; before the chat ends, run one closing check of everything you
    record. A replacement retires what it replaces; the reply shows its impact on existing work.
    """
    why = {"rationale": "", "reason": rationale} if replaces else {"rationale": rationale}  # a successor says why
    body = {"title": title, "topic": topic, "statement": statement, "scope": scope, "confirmed": confirmed} | why
    if replaces:
        body |= {"replaces": replaces.decision, "revision": replaces.revision, "redecide": replaces.redecide}
        body |= {"effect": replaces.effect}
    return _STATE["chat"].write("/decisions/propose", body)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=True))
def retire_decision(
    *,
    decision: Annotated[str, Field(description="Decision id from find_decisions")],
    revision: Annotated[str, Field(description="Its revision from find_decisions", pattern=r"^[0-9a-f]{64}$")],
    reason: Annotated[str, Field(description="Why it no longer applies", min_length=1, max_length=4000)],
    redecide: Annotated[bool, Field(description="True only when it is decided and the owner re-decided it")] = False,
    confirmed: Annotated[
        bool, Field(description="True only when the owner confirmed retiring it in this chat after you read it back")
    ] = False,
) -> dict[str, Any]:
    """Withdraw a decision or draft the owner confirmed retiring; it stays in history, hidden by default.

    The reply shows its impact on existing work.
    """
    path = f"/decisions/{urllib.parse.quote(decision, safe='')}/retire"
    body = {"revision": revision, "reason": reason, "redecide": redecide, "confirmed": confirmed}
    return _STATE["chat"].write(path, body)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
def read_back_decision(
    *,
    decision: Annotated[str, Field(description="Decision id from find_decisions")],
    revision: Annotated[str, Field(description="Its revision from find_decisions")],
    confirmed: Annotated[
        bool,
        Field(
            description="True only when the owner confirmed the statement as it stands after you read it back to "
            "him. A different intent is no read-back: record it as a replacement with record_decision. Never "
            "pass his words."
        ),
    ] = False,
) -> dict[str, Any]:
    """Record that the owner confirmed a decision read back to him; a change of mind is a replacement, not this."""
    path = f"/decisions/{urllib.parse.quote(decision, safe='')}/read-back"
    return _STATE["chat"].write(path, {"revision": revision, "confirmed": confirmed})


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
def correct_decision_origin(
    *,
    decision: Annotated[str, Field(description="Decision id from find_decisions")],
    revision: Annotated[str, Field(description="Its revision from find_decisions", pattern=r"^[0-9a-f]{64}$")],
    origin: Annotated[
        Literal["approved", "autonomous"],
        Field(description="approved: an agent's proposal he accepted; autonomous: an agent's own choice"),
    ],
    reason: Annotated[
        str,
        Field(description="Why, in your words, never his: what he stated about where it came from", max_length=4000),
    ],
    confirmed: Annotated[
        bool,
        Field(description="True only when the owner confirmed this correction in this chat after you read it back"),
    ] = False,
) -> dict[str, Any]:
    """Lower a decision's origin the owner says he never decided; its statement and state stay, the reason is recorded.

    Only downward: decided, approved, autonomous. Raising one is his read-back or replacement.
    """
    path = f"/decisions/{urllib.parse.quote(decision, safe='')}/correct-origin"
    body = {"revision": revision, "origin": origin, "reason": reason, "confirmed": confirmed}
    return _STATE["chat"].write(path, body)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
def queue_read_back(
    decision: Annotated[str, Field(description="Decision id from find_decisions")],
    revision: Annotated[str, Field(description="The revision find_decisions showed for it", pattern=r"^[0-9a-f]{64}$")],
    why: Annotated[
        str,
        Field(
            description="What makes it worth asking again: the ambiguity, new evidence, conflict or changed "
            "consequences, in one or two sentences",
            min_length=1,
            max_length=600,
        ),
    ],
    kind: Annotated[
        Literal["safety", "blocked", "uncertain", "improvement"],
        Field(
            description="How urgent: safety (imminent safety or irreversible effects), blocked (work waits on it), "
            "uncertain (consequential uncertainty), improvement (can wait)"
        ),
    ],
) -> dict[str, Any]:
    """Queue a decision for the owner's read-back on the Decisions page; its origin, wording and state stay.

    Only on real ambiguity, new evidence, a conflict or changed consequences; never for consent he already gave.
    """
    path = f"/decisions/{urllib.parse.quote(decision, safe='')}/queue-read-back"
    return _STATE["chat"].write(path, {"why": why, "kind": kind, "revision": revision})


def main(argv: list[str] | None = None) -> None:
    """Serve the chat tools over stdio for the folder at ``--repo`` (default: the working directory)."""
    parser = argparse.ArgumentParser(prog="python -m owlbear_delivery_next mcp")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    _STATE["chat"] = workspace(parser.parse_args(argv).repo.resolve())
    mcp.run()
