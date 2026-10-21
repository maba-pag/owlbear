"""Chat tools: a client of the running host, with a read-only status fallback when it is down (D4 §3.1, §3.3)."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from owlbear_delivery_next.change_contracts import tools  # noqa: TC001 - tool annotations resolve at runtime
from owlbear_delivery_next.change_flow import brief_rounds, brief_tools, loop
from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.project_host import api, brief_routes, host
from owlbear_delivery_next.state_store.store import Store, StoreError

NOT_RUNNING = (
    "Delivery is not running for {repo} - run `owlbear start`, then add this project on its page if it is not "
    "listed. Nothing advances until it runs."
)
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback never goes through a proxy
_STATE: dict[str, Chat] = {}
OK = 200
UPDATED = "OwlBear updated: reload this VS Code window"  # a chat server older than the host (self-update §5.6)
STALE = 409


def updated(rec: host.HostRecord | None) -> bool:
    """Whether OwlBear runs other code than this chat server loaded: the host's, or the files under it changed."""
    return host.stale(rec) or codebase.identity() != codebase.CURRENT


WAIT, POLL = 600.0, 5.0  # seconds a brief challenge request waits for the verdict, and between its reads
PAGE_ONLY = ("progress", "spend", "pullback")  # left out of the list of every Change: 16 rows were 77 KB with them
PAUSED = "paused: ask the owner to press Resume on the Changes page; the challenge runs then - call show_status"
_pause = time.sleep  # the poll's own pause
FOUND = 20  # decisions a find returns; the rest are counted
SHORT = ("id", "title", "statement", "scope", "origin", "state", "conflict", "read_back", "revision")


class Chat:
    """The chat tools of one clone; every write goes through the running host."""

    def __init__(self, repo: Path) -> None:
        self.repo, self.store = repo, Store.open(repo)

    def call(self, method: str, path: str, body: object = None) -> tuple[int, Any]:
        """One request to the host with its token; 503 when it is not running."""
        rec = host.running(self.store)
        down = NOT_RUNNING.format(repo=self.repo)
        if updated(rec):  # it reads no state either: a newer version may have written it
            return STALE, {"error": UPDATED}
        if rec is None or not rec.token:
            return 503, {"error": down}
        headers = {"Authorization": f"Bearer {rec.token}", "Content-Type": "application/json", "X-OwlBear-Use": "chat"}
        data = None if body is None else json.dumps(body).encode()
        url = f"{rec.url}{f'p/{rec.project}/' if rec.project else ''}api/next{path}"  # the machine host's (TD-242)
        request = urllib.request.Request(url, data=data, method=method, headers=headers)  # noqa: S310 - loopback
        try:
            with _LOCAL.open(request, timeout=15) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.load(exc)
            except ValueError:
                return exc.code, {"error": str(exc.reason)}
        except (urllib.error.URLError, OSError) as exc:
            return 503, {"error": f"{down} ({exc})"}

    def save_brief(self, fields: dict[str, Any], path: str = "/briefs") -> dict[str, Any]:
        """Create or revise a brief draft; the host returns the handle or one error per field."""
        code, out = self.call("POST", path, fields)
        return {"saved": code == OK, **out}

    def show_status(self, change: str = "") -> dict[str, Any]:
        """Every Change (or one) with its line, next action and open question; read from the state when down."""
        code, rows = self.call("GET", "/changes")
        if code == STALE:
            return {"running": False, "error": UPDATED}
        rec = host.running(self.store)
        out: dict[str, Any] = {"running": code == OK, "changes_page": api.link(rec) if code == OK else None}
        if code == OK and rec:
            out["readiness"] = "checking" if rec.ready is None else rec.ready or "ok"
        if code != OK:
            now = datetime.now(UTC)
            rows = [api.summary(self.store, s, host.activity(self.store, s, None), now) for s in self.store.slugs()]
            out["message"] = NOT_RUNNING.format(repo=self.repo)
        out["changes"] = [r for r in rows if not change or r.get("handle") == change]
        if not change:
            out["changes"] = [{k: v for k, v in r.items() if k not in PAGE_ONLY} for r in out["changes"]]
        if change and not out["changes"]:
            out["error"] = f"change: {change} is not a Change here - leave it empty to list all"
        elif change and (brief := self.brief(out["changes"][0].get("slug", ""))):
            out["brief"] = brief
        return out

    def brief(self, slug: str) -> dict[str, Any] | None:
        """The Change's current brief as the chat saved it, decisions and non-goals included, to read back."""
        try:
            change = self.store.read(slug)
        except StoreError:
            return None
        b = change.brief
        out = b.model_dump(mode="json", include={"version", "title", "outcome", "scope", "non_goals"})
        out["decisions"] = [d.model_dump(mode="json", exclude={"id", "replaces"}) for d in b.decisions]  # as drafted
        owner = set(b.specified)  # sent back as saved, so a resave keeps who stated what
        states = [{"name": s.name, "owner": f"screen:{s.name}" in owner} for s in b.visual]
        checks = [{"name": p.id, "owner": f"check:{p.id}" in owner} for p in change.checks]
        out |= {"specified": [k.id for k in b.criteria if k.id in owner], "states": states, "person_checks": checks}
        proposed = [i.model_dump(include={"criterion", "old", "new", "why"}) | {"verdict": a.verdict or "not judged"}
                    for a in change.amendments for i in a.items]  # fmt: skip
        out |= {"challenge": brief_rounds.status(change)}  # TD-221: the brief challenge's findings by ID
        return out | {"criteria": [k.text for k in b.criteria], "proposed_wording": proposed}

    def challenge_brief(self, change: str, version: int, rejected: list[dict[str, str]]) -> dict[str, Any]:
        """Ask for the version's challenge, then wait a while for its verdict and return the findings by ID."""
        code, out = self.call("POST", "/briefs/challenge", {"change": change, "version": version, "rejected": rejected})
        if code != OK:
            return {"requested": False, **out}
        if out.get("paused"):  # TD-283: recorded now, judged once the owner resumes Delivery
            return {"requested": True, "running": False, "next": PAUSED}
        slug, attempt = brief_routes.slug_of(self.store, change) or "", out.get("attempt", 0)
        deadline = time.monotonic() + WAIT
        while time.monotonic() < deadline:
            try:
                c = self.store.read(slug)
            except StoreError:
                break
            if not brief_rounds.running(c, version, attempt):
                return {"requested": True, **brief_rounds.status(c)}
            _pause(POLL)
        return {
            "requested": True,
            "running": True,
            "next": "the challenge still runs; call show_status with the handle",
        }

    def answer_question(self, question: str, option: str, text: str) -> dict[str, Any]:
        """Answer one worker question; recovery decisions are refused with the Changes page (T6)."""
        if updated(host.running(self.store)):
            return {"answered": False, "error": UPDATED}
        handle, _, qid = question.partition(".")
        for slug in self.store.slugs():
            try:
                c = self.store.read(slug)
            except StoreError:
                continue
            if c.handle == handle:
                break
        else:
            return {"answered": False, "error": f"question: {question} is not a question id; show_status gives them"}
        q = next((q for q in c.questions if q.id == qid and q.answer is None), None)
        if q is None:
            return {"answered": False, "error": f"question: {question} is not open"}
        if not loop.ordinary(q):
            return {"answered": False, "error": api.T6, "changes_page": api.link(host.running(self.store))}
        body = {"question": qid, "option": option or None, "text": text, "channel": "chat"}
        code, out = self.call("POST", f"/changes/{slug}/answers", body)
        return {"answered": code == OK, **out}

    def page(self) -> str | None:
        """The Decisions page with its token, where the owner activates, replaces and withdraws."""
        rec = host.running(self.store)
        full = api.link(rec)
        return full and rec and full.replace(rec.url, f"{rec.url}decisions", 1)

    def find_decisions(self, text: str, where: str, *, include_retired: bool) -> dict[str, Any]:
        """The decisions of this project and Global, matched by the index; at most FOUND of them."""
        query = urllib.parse.urlencode({"text": text, "where": where, "retired": str(include_retired).lower()})
        code, out = self.call("GET", f"/decisions?{query}")
        if code != OK or not out.get("available"):
            return {"found": False, "error": out.get("reason") or out.get("detail") or out.get("error")}
        rows = [{k: d[k] for k in SHORT} for d in out["decisions"]]
        return {"found": True, "decisions": rows[:FOUND], "more": len(rows[FOUND:]), "decisions_page": self.page()}

    def write(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """One decision write through the host: its receipts, or why it was refused."""
        code, out = self.call("POST", path, body)
        if code != OK:
            return {"saved": False, "error": out.get("detail") or out.get("error"), "decisions_page": self.page()}
        return out | {"decisions_page": self.page()}


def _d(name: str, model: type[tools.Args] = brief_tools.BriefDraft) -> Any:  # noqa: ANN401 - a pydantic FieldInfo
    field = model.model_fields[name]
    return Field(description=field.description, examples=field.examples)


mcp = MCPServer(
    "owlbear-delivery",
    instructions="Shape a Change with the owner, save its brief and visual check, show Delivery status, answer a "
    "worker's question, find decisions, propose one, queue a read-back and record one.",
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
) -> dict[str, Any]:
    """Ask for the brief version's challenge once the draft is ready; waits for its verdict, gives findings by ID."""
    found = [r.model_dump() for r in rejected or []]
    return _STATE["chat"].challenge_brief(change, version, found)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
def show_status(
    change: Annotated[str, Field(description="Handle of one Change; empty for all", examples=["c1"])] = "",
) -> dict[str, Any]:
    """Show each Change's status line, next action and open question with its id, and the Changes page."""
    return _STATE["chat"].show_status(change)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
def answer_question(
    question: Annotated[str, Field(description="Question id from show_status", examples=["c1.q2"])],
    option: Annotated[str, Field(description="Chosen option id, if any", examples=["o1"])] = "",
    text: Annotated[str, Field(description="The owner's answer in words", max_length=2000)] = "",
) -> dict[str, Any]:
    """Answer one worker question for the owner; recovery decisions are made in the Changes page."""
    return _STATE["chat"].answer_question(question, option, text)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
def find_decisions(
    *,
    text: Annotated[str, Field(description="Words the title or statement holds; empty for all", max_length=200)] = "",
    where: Annotated[
        Literal["project", "global", "all"], Field(description="This project's decisions, Global ones, or both")
    ] = "all",
    include_retired: Annotated[bool, Field(description="Also replaced, withdrawn and spent decisions")] = False,
) -> dict[str, Any]:
    """Find the decisions in force (and drafts) of this project and Global, with the revision a read-back names."""
    return _STATE["chat"].find_decisions(text, where, include_retired=include_retired)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
def record_decision(  # noqa: PLR0913 - the proposal's fields
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
    owner_words: Annotated[
        str, Field(description="The owner's own words deciding it in this chat, quoted; empty for your proposal")
    ] = "",
    replaces: Annotated[str, Field(description="Id of the decision it would replace, if any")] = "",
) -> dict[str, Any]:
    """Propose a decision for this project: always a draft the owner activates on the Decisions page."""
    why = {"rationale": "", "reason": rationale} if replaces else {"rationale": rationale}  # a successor says why
    body = {"title": title, "topic": topic, "statement": statement} | why
    return _STATE["chat"].write("/decisions/propose", body | {"words": owner_words, "replaces": replaces})


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
def read_back_decision(
    decision: Annotated[str, Field(description="Decision id from find_decisions")],
    revision: Annotated[str, Field(description="Its revision from find_decisions")],
    answer: Annotated[str, Field(description="The owner's answer when you read it back to him", max_length=2000)],
) -> dict[str, Any]:
    """Record that the owner had a decision read back; a change of mind is his replacement on the Decisions page."""
    path = f"/decisions/{urllib.parse.quote(decision, safe='')}/read-back"
    return _STATE["chat"].write(path, {"revision": revision, "answer": answer})


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
    """Serve the chat tools over stdio for the clone at ``--repo`` (default: the working directory)."""
    parser = argparse.ArgumentParser(prog="python -m owlbear_delivery_next mcp")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    _STATE["chat"] = Chat(parser.parse_args(argv).repo.resolve())
    mcp.run()
