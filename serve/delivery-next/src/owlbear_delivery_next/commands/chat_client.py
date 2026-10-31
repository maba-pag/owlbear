"""The chat tools' client of the running host, one per workspace (D4 §3.1), under chat contract 1.

The workspace is told before any state is made: a registered project's clone gets every tool; OwlBear's own
repository, by its identity, gets OwlBear's decisions through the machine host (TD-435, TD-450); any other folder
is no OwlBear project, and every tool says so. The client reads and writes no state itself: everything goes through
the host over HTTP, naming the chat contract, so a chat keeps its tools while OwlBear updates beneath it
(D-01M5Q5GKHX7BJTXPEW2MHGS9E0). With the host down, the tools say so; nothing is read from the state then (D4 §3.3's
read-only status fallback is gone, since an older chat server could misread what a newer host wrote).
"""

from __future__ import annotations

import functools
import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import chat_contract, pick_tools
from owlbear_delivery_next.local_system import codebase, data_repo, local_home
from owlbear_delivery_next.project_host import answers, api, host
from owlbear_delivery_next.state_store import project_home
from owlbear_delivery_next.state_store.decision_errors import SAVING
from owlbear_delivery_next.state_store.store import StoreError

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
RESTART = (
    f"start a new Copilot-runtime chat, or focus this chat and use {codebase.STOP_START}; "
    "neither the agent host nor the window needs restarting"
)
NOT_OWLBEAR = "{repo} is not an OwlBear project: add its clone on the Changes page, then " + RESTART
NO_CHANGES = "OwlBear's own workspace has no Changes: only the decision tools work here"
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback never goes through a proxy
OK = 200
OLDER_HOST = (
    "the running OwlBear host is older than this chat's owlbear-delivery server (it has no chat contract "
    f"{chat_contract.CHAT}): let `owlbear update` finish, or run `owlbear restart`, then call again"
)
UNKNOWN = (
    "the host's answer was lost, so it may have done it: check with show_status or find_decisions before trying again"
)
STALE = 409
LOST = 0  # a write the host may have done: its outcome is unknown, never "not done"
CUT = (OSError, ValueError, http.client.HTTPException)  # no answer, or one cut short or not JSON


def done(code: int) -> bool | None:
    """Whether a write was done: None when its answer was lost, so it may have been."""
    return None if code == LOST else code == OK


WAIT, POLL = 600.0, 5.0  # seconds a brief challenge request waits for the verdict, and between its reads
# Seconds a decision write waits for its answer: the lock's 20, a save's two 45 s phases of Git commands capped at 10 s
# each, and a replacement's impact report; a margin, not a bound
WRITE = 180.0
ADMIT, SETTLE = 90.0, 150.0  # seconds a propose may take to start its save, and to settle after that (#846)
ADMIT_BY = "X-OwlBear-Admit-By"  # the propose's deadline, on the host's clock (`decision_batch.ADMIT_BY`)
_now = functools.partial(time.clock_gettime, time.CLOCK_MONOTONIC)  # the clock the host's fence reads
PAGE_ONLY = ("progress", "spend", "tool_use", "pullback")  # off the list of all Changes: 16 rows were 77 KB with them
PAUSED = "paused: ask the owner to press Resume on the Changes page; the challenge runs then - call show_status"
_pause = time.sleep  # the poll's own pause
FOUND = 20  # decisions a find returns; the rest are counted
SHORT = ("id", "title", "statement", "scope", "origin", "state", "conflict", "read_back", "revision")
SAVED = "the host's answer was lost; the decision is saved as {id}"
IMPACT_LOST = "; its impact report was lost: see the Decisions page"
NOT_SAVED = "the host's answer was lost and the decision was not saved: record it again"
UNCLEAR = "the host's answer was lost and whether the decision was saved is unclear; do not record it again: {why}"
STILL_SAVING = "a decision save is still in progress; check find_decisions shortly"
UNFENCED = "this host cannot promise the save did not start; check find_decisions shortly, or ask the owner"


class Chat:
    """The chat tools of one clone; every read and write goes through the running host."""

    prefix = ""  # where its decisions are, under the host's API
    not_running = NOT_RUNNING
    checked: tuple[int, str] | None = None  # the host (pid, start) whose chat contract was checked
    fenced = False  # whether that host refuses a save past its chat's deadline (`decision_batch.ADMIT_BY`)

    def __init__(self, repo: Path, home: Path) -> None:
        self.repo, self.home = repo, home  # the project's home: its host's record, never its state

    def record(self) -> chat_contract.HostFound | None:
        """The running host this workspace's tools call."""
        return host.running_at(self.home, chat_contract.HostFound)

    def down(self) -> str:
        """Why the tools reach no host: Delivery is not running, or it runs without this project."""
        machine = host.running_at(local_home.root(), chat_contract.HostFound)
        return (NOT_SERVED if machine and machine.token else self.not_running).format(repo=self.repo)

    def call(
        self, method: str, path: str, body: object = None, timeout: float = 15.0, headers: dict[str, str] | None = None
    ) -> tuple[int, Any]:
        """One request to the host with its token, naming the chat contract; 503 when it is not running.

        A request the host may have received but did not answer is 0: its effect is unknown, never "not done".
        """
        rec = self.record()
        if rec is None or not rec.token:
            return 503, {"error": self.down()}
        if (refused := self.contract(rec)) is not None:
            return refused[0], {"error": refused[1]}
        url = f"{rec.url}{f'p/{rec.project}/' if rec.project else ''}api/next{self.prefix}{path}"  # TD-242
        return self.send(rec, method, url, body, timeout, headers=headers)

    def send(  # noqa: PLR0913 - a request and how long it waits
        self, rec: chat_contract.HostFound, method: str, url: str, body: object, timeout: float, *,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any]:  # fmt: skip
        """One request to *url* at the host of *rec*, with this chat's headers; *headers* never replace them."""
        headers = (headers or {}) | {
            "Authorization": f"Bearer {rec.token}", "Content-Type": "application/json", "X-OwlBear-Use": "chat",
            chat_contract.HEADER: str(chat_contract.CHAT),
        }  # fmt: skip
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(url, data=data, method=method, headers=headers)  # noqa: S310 - loopback
        try:
            with _LOCAL.open(request, timeout=timeout) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                out = json.load(exc)
            except CUT:
                out = {"error": str(exc.reason)}
            if out.get("contract") == "unsupported":  # refused before any route ran
                return STALE, {"error": out.get("detail") or chat_contract.UNSUPPORTED.format(sent="?", served="?")}
            if method != "GET" and exc.code >= 500 and exc.code != 503:  # noqa: PLR2004 - it failed partway, maybe
                return LOST, {"error": f"{UNKNOWN} ({out.get('detail') or out.get('error')})"}
            return exc.code, out
        except CUT as exc:  # URLError included; a refused connection never reached the host
            refused = isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, ConnectionRefusedError)
            if not refused and method != "GET":  # a timeout, a reset or a cut answer after sending: maybe done
                return LOST, {"error": f"{UNKNOWN} ({exc})"}
            why = self.not_running.format(repo=self.repo) if refused else "the host did not answer; call again"
            return 503, {"error": f"{why} ({exc})"}

    def contract(self, rec: chat_contract.HostFound) -> tuple[int, str] | None:
        """Why the host of *rec* cannot serve this chat's contract now, with its code; None when it can.

        A host from before the contract ignores the header, so its support is asked first, before any write; once a
        host said yes it is not asked again. A host that does not answer (503) is asked again on the next call.
        """
        if self.checked == (rec.pid, rec.started_at.isoformat()):
            return None
        code, out = self.send(rec, "GET", f"{rec.url}{chat_contract.CAPABILITY.lstrip('/')}", None, 15.0)
        if code == 404:  # noqa: PLR2004 - the route does not exist there
            return STALE, OLDER_HOST
        if code != OK:
            return code, out.get("error") or out.get("detail") or f"the host answered {code}"
        if chat_contract.CHAT not in (served := out.get("supported", [])):
            listed = ", ".join(map(str, served)) or "none"
            return STALE, chat_contract.UNSUPPORTED.format(sent=chat_contract.CHAT, served=listed)
        self.checked, self.fenced = (rec.pid, rec.started_at.isoformat()), out.get("admit_by") is True
        return None

    def save_brief(self, fields: dict[str, Any], path: str = "/briefs") -> dict[str, Any]:
        """Create or revise a brief draft; the host returns the handle or one error per field."""
        code, out = self.call("POST", path, fields)
        return {"saved": done(code), **out}

    def show_status(self, change: str = "") -> dict[str, Any]:
        """Every Change (or one) with its line, next action and open question, as the host reports them."""
        code, rows = self.call("GET", "/changes")
        if code != OK:
            return {
                "running": False,
                "changes_page": None,
                "changes": [],
                "message": rows.get("error") or rows.get("detail"),
            }
        rec = self.record()
        out: dict[str, Any] = {"running": True, "changes_page": api.link(rec)}
        if rec:
            out["readiness"] = "checking" if rec.ready is None else rec.ready or "ok"
        out["changes"] = [r for r in rows if not change or r.get("handle") == change]
        if not change:
            out["changes"] = [{k: v for k, v in r.items() if k not in PAGE_ONLY} for r in out["changes"]]
        if change and not out["changes"]:
            out["error"] = f"change: {change} is not a Change here - leave it empty to list all"
        elif change:
            found, brief = self.call("GET", f"/chat/brief/{urllib.parse.quote(out['changes'][0].get('slug', ''))}")
            if found == OK:
                out["brief"] = brief
            else:  # the host handed over meanwhile, or refused: no brief is not "no brief"
                out["error"] = f"brief: {brief.get('error') or brief.get('detail')}; call show_status again"
        return out

    def challenge_brief(
        self, change: str, version: int, rejected: list[dict[str, str]], *, retry_pick: bool = False
    ) -> dict[str, Any]:
        """Ask for the version's challenge or its pick again, then wait a while for the outcome; findings by ID."""
        body = {"change": change, "version": version, "rejected": rejected, "retry_pick": retry_pick}
        code, out = self.call("POST", "/briefs/challenge", body)
        if code != OK:
            return {"requested": done(code), **out}
        if out.get("paused"):  # TD-283: recorded now, judged once the owner resumes Delivery
            return {"requested": True, "running": False, "next": PAUSED}
        slug, attempt = urllib.parse.quote(out.get("slug", "")), out.get("attempt", 0)
        deadline, why = time.monotonic() + WAIT, {}
        while slug and time.monotonic() < deadline:  # the request is never sent again; only its outcome is read
            code, now = self.call("GET", f"/chat/challenge/{slug}?version={version}&attempt={attempt}")
            if code == OK and not now.get("running"):
                return {"requested": True, **{k: v for k, v in now.items() if k != "running"}}
            if code not in {OK, 503}:  # 503: the host is handing over, so read again; anything else ends the wait
                why = {"error": now.get("error") or now.get("detail")}
                break
            _pause(POLL)
        return {
            "requested": True,
            "running": True,
            "next": "the challenge still runs; call show_status with the handle",
        } | why

    def answer_question(self, question: str, option: str, text: str, said: dict[str, Any]) -> dict[str, Any]:
        """Answer one worker question with its class (*said*); recovery decisions are refused with the page (T6)."""
        handle, _, qid = question.partition(".")
        code, rows = self.call("GET", "/changes")
        if code != OK:
            return {"answered": False, "error": rows.get("error") or rows.get("detail")}
        slug = next((r.get("slug") for r in rows if r.get("handle") == handle), None)
        if slug is None or not qid:
            return {"answered": False, "error": f"question: {question} is not a question id; show_status gives them"}
        body = {"question": qid, "option": option or None, "text": text, "channel": "chat"} | said
        code, out = self.call("POST", f"/changes/{urllib.parse.quote(slug)}/answers", body)
        if code == 403 and out.get("detail") == answers.T6:  # noqa: PLR2004 - a recovery decision, the page's
            return {"answered": False, "error": answers.T6, "changes_page": api.link(self.record())}
        if code == 409 and str(out.get("detail", "")).endswith("is not open"):  # noqa: PLR2004
            return {"answered": False, "error": f"question: {question} is not open"}
        if code != OK:
            return {"answered": done(code), "error": out.get("detail") or out.get("error"), **out}
        return {"answered": True, **out}

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

    def write(self, path: str, body: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        """One decision write through the host: its receipts, or why it was refused."""
        code, out = self.call("POST", path, body, timeout=WRITE, headers=headers)
        if code != OK:
            return {"saved": done(code), "error": out.get("detail") or out.get("error"), "decisions_page": self.page()}
        return out | {"decisions_page": self.page()}

    def propose(self, body: dict[str, Any]) -> dict[str, Any]:
        """Record or propose a decision; when the host's answer is lost, the decisions say whether it was saved.

        The host refuses to start the save past *admit_by*, so a read after it that finds neither the decision nor a
        save in progress proves nothing was written; a host without that fence leaves it unclear (#846).
        """
        started, admit_by = datetime.now(UTC), _now() + ADMIT
        out = self.write("/decisions/propose", body, {ADMIT_BY: repr(admit_by)})
        if out.get("saved") is not None:
            return out
        return self._settled(body, started, admit_by, fenced=self.fenced) | {"decisions_page": self.page()}

    def _settled(self, body: dict[str, Any], started: datetime, admit_by: float, *, fenced: bool) -> dict[str, Any]:
        """Saved with its id, not saved, or unclear with why, from the decisions as the host reads them now."""
        query = urllib.parse.urlencode({"where": "all", "retired": "true"})
        while True:
            t = _now()
            code, out = self.call("GET", f"/decisions?{query}")
            if code != OK or not out.get("available"):
                why = str(out.get("reason") or out.get("detail") or out.get("error") or f"the host answered {code}")
                if SAVING not in why:
                    return {"saved": None, "error": UNCLEAR.format(why=f"{why}; ask the owner")}
                if t > admit_by + SETTLE:
                    return {"saved": None, "error": UNCLEAR.format(why=STILL_SAVING)}
            elif found := [d for d in out["decisions"] if _same(d, body, started)]:
                return self._found(body, found)
            elif t > admit_by and fenced:
                return {"saved": False, "error": NOT_SAVED}
            elif t > admit_by:
                return {"saved": None, "error": UNCLEAR.format(why=UNFENCED)}
            _pause(POLL)

    def _found(self, body: dict[str, Any], found: list[dict[str, Any]]) -> dict[str, Any]:
        """The one decision this propose saved, else why it is unclear: never a decision someone else made."""
        ids = ", ".join(d["id"] for d in found)
        if len(found) > 1:
            return {"saved": None, "error": UNCLEAR.format(why=f"{ids} match it; ask the owner")}
        made = found[0]
        code, detail = self.call("GET", f"/decisions/{urllib.parse.quote(made['id'])}")
        links = [link.get("id") for link in detail.get("links", []) if link.get("type") == "replaces"]
        wanted = (body["replaces"],) if body.get("replaces") else ()
        state, origin = ("in_force", body["origin"]) if body["confirmed"] else ("draft", "autonomous")
        if code != OK or tuple(links) != wanted or (made["state"], made["origin"]) != (state, origin):
            return {"saved": None, "error": UNCLEAR.format(why=f"{ids} matches it in part; ask the owner")}
        notice = SAVED.format(id=made["id"])
        if body["confirmed"] and body.get("replaces") and body.get("effect") != "wording":
            notice += IMPACT_LOST
        return {"saved": True, "receipts": [{"id": made["id"], "saved": True}], "notice": notice}


def _same(row: dict[str, Any], body: dict[str, Any], started: datetime) -> bool:
    """The row has the sent wording and layer, and was made since the propose started."""
    made = datetime.fromisoformat(row.get("created_at") or "1970-01-01T00:00:00Z")
    return (
        (row["title"].strip(), row["statement"].strip()) == (body["title"].strip(), body["statement"].strip())
        and (row["scope"] == "global") == (body["scope"] == "global")
        and made >= started
    )


class OwlBear(Chat):
    """OwlBear's own workspace, never registered (TD-435): its decisions on the machine host, and no Changes."""

    prefix = "/owlbear"
    not_running = OWLBEAR_DOWN

    def __init__(self, repo: Path) -> None:  # no store: opening one makes Delivery state for this clone
        super().__init__(repo, local_home.root())

    def record(self) -> chat_contract.HostFound | None:
        """The machine host's record."""
        return host.running_at(local_home.root(), chat_contract.HostFound)

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

    A clone is a project when the machine's registry lists its id; an id or a project folder left behind is not,
    nor is any id while the registry cannot be read.
    """
    try:
        pid = project_home.clone_id(project_home.clone_dir(repo))
    except StoreError, OSError:
        pid = None
    if pid is not None and project_home.registered(pid):
        return Chat(repo, project_home.home(pid))
    if data_repo.identity(repo) == data_repo.remote_identity(codebase.URL):
        return OwlBear(repo)
    return Closed(repo)
