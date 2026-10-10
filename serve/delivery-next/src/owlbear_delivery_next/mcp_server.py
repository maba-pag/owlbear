"""Chat tools: a client of the running host, with a read-only status fallback when it is down (D4 §3.1, §3.3)."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from owlbear_delivery_next import api, host, loop, tools
from owlbear_delivery_next.store import Store, StoreError

NOT_RUNNING = (
    "Delivery is not running - start it with the VS Code task 'OwlBear Delivery host', or run "
    "`owlbear-next --repo {repo} host`. Nothing advances until it runs."
)
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback never goes through a proxy
_STATE: dict[str, Chat] = {}
OK = 200


class Chat:
    """The chat tools of one clone; every write goes through the running host."""

    def __init__(self, repo: Path) -> None:
        self.repo, self.store = repo, Store.open(repo)

    def call(self, method: str, path: str, body: object = None) -> tuple[int, Any]:
        """One request to the host with its token; 503 when it is not running."""
        rec = host.running(self.store)
        down = NOT_RUNNING.format(repo=self.repo)
        if rec is None or not rec.token:
            return 503, {"error": down}
        headers = {"Authorization": f"Bearer {rec.token}", "Content-Type": "application/json"}
        data = None if body is None else json.dumps(body).encode()
        url = f"{rec.url}api/next{path}"
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

    def save_brief(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Create or revise a brief draft; the host returns the handle or one error per field."""
        code, out = self.call("POST", "/briefs", fields)
        return {"saved": code == OK, **out}

    def show_status(self, change: str = "") -> dict[str, Any]:
        """Every Change (or one) with its line, next action and open question; read from the state when down."""
        code, rows = self.call("GET", "/changes")
        rec = host.running(self.store)
        out: dict[str, Any] = {"running": code == OK, "changes_page": rec.url if rec and code == OK else None}
        if code != OK:
            now = datetime.now(UTC)
            rows = [api.summary(self.store, s, host.activity(self.store, s, None), now) for s in self.store.slugs()]
            out["message"] = NOT_RUNNING.format(repo=self.repo)
        out["changes"] = [r for r in rows if not change or r.get("handle") == change]
        if change and not out["changes"]:
            out["error"] = f"change: {change} is not a Change here - leave it empty to list all"
        return out

    def answer_question(self, question: str, option: str, text: str) -> dict[str, Any]:
        """Answer one worker question; recovery decisions are refused with the Changes page (T6)."""
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
            return {"answered": False, "error": api.T6, "changes_page": getattr(host.running(self.store), "url", None)}
        body = {"question": qid, "option": option or None, "text": text, "channel": "chat"}
        code, out = self.call("POST", f"/changes/{slug}/answers", body)
        return {"answered": code == OK, **out}


def _d(name: str, model: type[tools.Args] = tools.BriefDraft) -> Any:  # noqa: ANN401 - a pydantic FieldInfo
    field = model.model_fields[name]
    return Field(description=field.description, examples=field.examples)


mcp = MCPServer(
    "owlbear-delivery",
    instructions="Shape a Change with the owner, save its brief, show Delivery status, answer a worker's question.",
)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
def save_brief(  # noqa: PLR0913 - the brief's six fields
    *,
    title: Annotated[str, _d("title")] = "",
    outcome: Annotated[str, _d("outcome")] = "",
    criteria: Annotated[list[str] | None, _d("criteria")] = None,
    scope: Annotated[list[str] | None, _d("scope")] = None,
    person_checks: Annotated[list[dict[str, Any]] | None, _d("person_checks")] = None,
    change: Annotated[str, _d("change")] = "",
) -> dict[str, Any]:
    """Create or revise one Change's brief draft; the reply gives its handle or one error per field to fix."""
    fields = {"title": title, "outcome": outcome, "criteria": criteria or [], "scope": scope or []}
    return _STATE["chat"].save_brief(fields | {"person_checks": person_checks or [], "change": change})


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


def main(argv: list[str] | None = None) -> None:
    """Serve the chat tools over stdio for the clone at ``--repo`` (default: the working directory)."""
    parser = argparse.ArgumentParser(prog="python -m owlbear_delivery_next.mcp_server")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    _STATE["chat"] = Chat(parser.parse_args(argv).repo.resolve())
    mcp.run()


if __name__ == "__main__":
    main()
