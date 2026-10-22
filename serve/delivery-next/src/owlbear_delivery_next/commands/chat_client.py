"""The chat tools' client of the running host, one per workspace, with a read-only status fallback (D4 §3.1, §3.3).

The workspace is told before any state is made: a registered project's clone gets every tool; OwlBear's own
repository, by its identity, gets OwlBear's decisions through the machine host (TD-435, TD-450); any other folder
is no OwlBear project, and every tool says so.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import pick_tools
from owlbear_delivery_next.change_flow import brief_rounds, loop, picks
from owlbear_delivery_next.local_system import codebase, data_repo, local_home
from owlbear_delivery_next.project_host import answers, api, brief_routes, host
from owlbear_delivery_next.state_store import project_home
from owlbear_delivery_next.state_store.store import Store, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

NOT_RUNNING = (
    "Delivery is not running for {repo} - run `owlbear start`, then add this project on its page if it is not "
    "listed. Nothing advances until it runs."
)
NOT_SERVED = (
    "OwlBear is running but does not serve {repo}: its state and reason are on the Changes page, and "
    "`owlbear doctor` names the fix. Nothing advances until it is served."
)
OWLBEAR_DOWN = "Delivery is not running - run `owlbear start`; OwlBear's own clone is never added as a project (TD-435)"
RESTART = "reload the VS Code window; in the Copilot runtime, run Restart Local Agent Host instead"
NOT_OWLBEAR = "{repo} is not an OwlBear project: add its clone on the Changes page, then " + RESTART
NO_CHANGES = "OwlBear's own workspace has no Changes: only the decision tools work here"
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback never goes through a proxy
OK = 200
UPDATED = "OwlBear updated: " + RESTART  # a chat server older than the host (self-update §5.6)
STALE = 409


def updated(rec: host.HostRecord | None) -> bool:
    """Whether OwlBear runs other code than this chat server loaded: the host's, or the files under it changed."""
    return host.stale(rec) or codebase.identity() != codebase.CURRENT


WAIT, POLL = 600.0, 5.0  # seconds a brief challenge request waits for the verdict, and between its reads
PAGE_ONLY = ("progress", "spend", "tool_use", "pullback")  # off the list of all Changes: 16 rows were 77 KB with them
PAUSED = "paused: ask the owner to press Resume on the Changes page; the challenge runs then - call show_status"
_pause = time.sleep  # the poll's own pause
FOUND = 20  # decisions a find returns; the rest are counted
SHORT = ("id", "title", "statement", "scope", "origin", "state", "conflict", "read_back", "revision")


class Chat:
    """The chat tools of one clone; every write goes through the running host."""

    prefix = ""  # where its decisions are, under the host's API
    not_running = NOT_RUNNING

    def __init__(self, repo: Path) -> None:
        self.repo, self.store = repo, Store.open(repo)

    def record(self) -> host.HostRecord | None:
        """The running host this workspace's tools call."""
        return host.running(self.store)

    def down(self) -> str:
        """Why the tools reach no host: Delivery is not running, or it runs without this project."""
        machine = host.running_at(local_home.root())
        return (NOT_SERVED if machine and machine.token else self.not_running).format(repo=self.repo)

    def call(self, method: str, path: str, body: object = None, timeout: float = 15.0) -> tuple[int, Any]:
        """One request to the host with its token; 503 when it is not running."""
        rec = self.record()
        if updated(rec):  # it reads no state either: a newer version may have written it
            return STALE, {"error": UPDATED}
        if rec is None or not rec.token:
            return 503, {"error": self.down()}
        headers = {"Authorization": f"Bearer {rec.token}", "Content-Type": "application/json", "X-OwlBear-Use": "chat"}
        data = None if body is None else json.dumps(body).encode()
        url = f"{rec.url}{f'p/{rec.project}/' if rec.project else ''}api/next{self.prefix}{path}"  # TD-242
        request = urllib.request.Request(url, data=data, method=method, headers=headers)  # noqa: S310 - loopback
        try:
            with _LOCAL.open(request, timeout=timeout) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.load(exc)
            except ValueError:
                return exc.code, {"error": str(exc.reason)}
        except (urllib.error.URLError, OSError) as exc:
            return 503, {"error": f"{self.not_running.format(repo=self.repo)} ({exc})"}

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
            out["message"] = self.down()
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

    def challenge_brief(
        self, change: str, version: int, rejected: list[dict[str, str]], *, retry_pick: bool = False
    ) -> dict[str, Any]:
        """Ask for the version's challenge or its pick again, then wait a while for the outcome; findings by ID."""
        body = {"change": change, "version": version, "rejected": rejected, "retry_pick": retry_pick}
        code, out = self.call("POST", "/briefs/challenge", body)
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
            if not (brief_rounds.running(c, version, attempt) or picks.owed(c)):
                return {"requested": True, **brief_rounds.status(c)}
            _pause(POLL)
        return {
            "requested": True,
            "running": True,
            "next": "the challenge still runs; call show_status with the handle",
        }

    def answer_question(self, question: str, option: str, text: str, said: dict[str, Any]) -> dict[str, Any]:
        """Answer one worker question with its class (*said*); recovery decisions are refused with the page (T6)."""
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
            return {"answered": False, "error": answers.T6, "changes_page": api.link(host.running(self.store))}
        body = {"question": qid, "option": option or None, "text": text, "channel": "chat"} | said
        code, out = self.call("POST", f"/changes/{slug}/answers", body)
        return {"answered": code == OK, **out}

    def page(self) -> str | None:
        """The Decisions page with its token, where the owner looks decisions up and changes them."""
        rec = self.record()
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

    def lookup_decisions(self, question: str) -> dict[str, Any]:
        """The picker's answer, waited for as long as a pick takes; any failure says failed, never none."""
        code, out = self.call("POST", "/decisions/lookup", {"question": question}, timeout=pick_tools.WAIT)
        if code != OK:
            return {"failed": str(out.get("detail") or out.get("error") or f"the host answered {code}")}
        return out

    def write(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """One decision write through the host: its receipts, or why it was refused."""
        code, out = self.call("POST", path, body)
        if code != OK:
            return {"saved": False, "error": out.get("detail") or out.get("error"), "decisions_page": self.page()}
        return out | {"decisions_page": self.page()}


class OwlBear(Chat):
    """OwlBear's own workspace, never registered (TD-435): its decisions on the machine host, and no Changes."""

    prefix = "/owlbear"
    not_running = OWLBEAR_DOWN

    def __init__(self, repo: Path) -> None:  # no store: opening one makes Delivery state for this clone
        self.repo = repo

    def record(self) -> host.HostRecord | None:
        """The machine host's record."""
        return host.running_at(local_home.root())

    def save_brief(self, *_args: object, **_kwargs: object) -> dict[str, Any]:  # type: ignore[override]
        """No Change tool works here."""
        return {"error": NO_CHANGES}

    challenge_brief = show_status = answer_question = save_brief


class Closed:
    """A folder that is no OwlBear project: every tool says so and nothing is written."""

    def __init__(self, repo: Path) -> None:
        self.why = NOT_OWLBEAR.format(repo=repo)

    def __getattr__(self, _name: str) -> Callable[..., dict[str, Any]]:
        return lambda *_args, **_kwargs: {"error": self.why}


def workspace(repo: Path) -> Chat | Closed:
    """The tools for the folder at *repo*, told before any state is made (``Store.open`` makes it).

    A clone is a project when the machine's registry lists its id; an id or a project folder left behind is not.
    """
    try:
        pid = project_home.clone_id(project_home.clone_dir(repo))
    except StoreError, OSError:
        pid = None
    if pid is not None:
        listed = project_home.registered(pid)
        if listed or (listed is None and project_home.home(pid).is_dir()):  # an unreadable registry: its folder tells
            return Chat(repo)
    if data_repo.identity(repo) == data_repo.remote_identity(codebase.URL):
        return OwlBear(repo)
    return Closed(repo)
