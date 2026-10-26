"""Chat contracts (D-01M5Q5GKHX7BJTXPEW2MHGS9E0): a chat's server keeps its tools while OwlBear updates beneath it."""

import asyncio
import fcntl
import io
import json
import os
import subprocess
import urllib.error
from datetime import UTC, datetime
from email.message import Message
from http.client import IncompleteRead
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import chat_contract
from owlbear_delivery_next.change_flow import brief_tools
from owlbear_delivery_next.commands import chat_client, mcp_server
from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.machine_host import app, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.state_store.store import Store

FIXTURES = Path(__file__).parent / "fixtures"
WORDING = {"description", "examples", "title"}  # what a tool says to the model; its shape is the contract
AUTH = {"authorization": "Bearer " + "t"}  # the token of record()
SERVES = {"supported": sorted(chat_contract.SUPPORTED)}  # what a current host answers
ROUTES = [  # what chat_client calls, under a project and (the decisions) under /owlbear
    ("post", "/briefs"), ("post", "/briefs/visual"), ("post", "/briefs/challenge"), ("get", "/changes"),
    ("get", "/chat/brief/{slug}"), ("get", "/chat/challenge/{slug}"), ("post", "/changes/{slug}/answers"),
    ("get", "/decisions"), ("post", "/decisions/lookup"), ("post", "/decisions/propose"),
    ("get", "/chat/contract"),
    *(("post", f"/decisions/{{decision_id}}/{w}") for w in ("retire", "read-back", "correct-origin")),
    ("post", "/decisions/{decision_id}/queue-read-back"),
]  # fmt: skip


def shape(schema: object, defs: dict[str, object] | None = None) -> object:
    """*schema* without its wording, its references to *defs* resolved."""
    if isinstance(schema, dict):
        if defs is not None and "$ref" in schema:
            return shape(defs[schema["$ref"].rsplit("/", 1)[1]], defs)
        return {k: shape(v, defs) for k, v in schema.items() if k not in WORDING or isinstance(v, dict)}  # a property
    if isinstance(schema, list):
        return [shape(v, defs) for v in schema]
    return schema


def tools() -> dict[str, object]:
    listed = asyncio.run(mcp_server.mcp.list_tools())
    return {t.name: {"input": shape(t.input_schema), "output": shape(t.output_schema)} for t in listed}


def routes() -> dict[str, object]:
    """The parameters and bodies the host's routes take from a chat."""
    spec = api.create_app(Store(Path("unused")), "t", SimpleNamespace(maintenance=None)).openapi()
    defs = spec["components"]["schemas"]
    ops = {f"{m.upper()} {r}": spec["paths"][f"/api/next{r}"][m] for m, r in ROUTES}
    out = {k: shape({"parameters": op.get("parameters", []), "body": op.get("requestBody")}, defs)
           for k, op in ops.items()}  # fmt: skip
    for k, model in (("POST /briefs", brief_tools.BriefDraft), ("POST /briefs/visual", brief_tools.VisualDraft)):
        schema = model.model_json_schema()  # these routes read the body themselves and parse it with the model
        defs = schema.pop("$defs", {})
        out[k]["body"] = shape(schema, defs)
    return out


def frozen(n: int) -> dict[str, object]:
    return json.loads((FIXTURES / f"chat_contract_{n}.json").read_text())


def covers(old: object, new: object, *, names: bool = False) -> bool:
    """Whether *new* takes all *old* took: it adds optional properties and drops required ones, nothing else.

    *names* marks a ``properties`` mapping, whose keys are field names rather than schema keywords.
    """
    if isinstance(old, dict) and isinstance(new, dict):
        if not names and set(new) - set(old):  # a new keyword (a bound, a pattern, an enum) may reject old requests
            return False
        if isinstance(old.get("required"), list) and set(new.get("required", [])) - set(old["required"]):
            return False
        return all(
            k in new and ((k == "required" and isinstance(v, list)) or covers(v, new[k], names=k == "properties"))
            for k, v in old.items()
        )
    if isinstance(old, list) and isinstance(new, list):
        return len(old) == len(new) and all(map(covers, old, new, strict=True))
    return old == new


def test_the_tools_a_chat_server_offers_are_those_of_its_contract():
    """A change a server of this contract could notice raises ``chat_contract.CHAT``, with its own fixture."""
    assert tools() == frozen(chat_contract.CHAT)["tools"]


@pytest.mark.parametrize("n", sorted(chat_contract.SUPPORTED))
def test_the_host_takes_all_a_chat_of_each_contract_it_serves_sends(n):
    now, before = routes(), frozen(n)["routes"]
    assert [k for k in before if not covers(before[k], now.get(k))] == []
    old = {"required": ["a"], "properties": {"a": {"type": "string"}}}
    assert covers(old, old | {"properties": {"a": {"type": "string"}, "b": {"type": "integer"}}})
    assert covers(old, old | {"required": []})
    assert not covers(old, old | {"required": ["a", "b"]})
    for bound in ({"enum": ["only"]}, {"maxLength": 3}, {"pattern": "^x"}):
        assert not covers(old, old | {"properties": {"a": {"type": "string"} | bound}})


def record(code: str = codebase.CURRENT, project: str = "") -> HostRecord:
    now = datetime.now(UTC)
    return HostRecord(url="http://127.0.0.1:9/", token="t", pid=7, started_at=now, code=code, project=project)  # noqa: S106


class Answering:
    """The host a chat calls, answered here: the requests it got, and canned answers by path."""

    def __init__(self, answers: dict[str, object]) -> None:
        self.answers, self.got = answers, []

    def __call__(self, _rec, method, url, body, _timeout):
        path = url.split("api/next", 1)[1]
        self.got.append((method, path, body))
        answer = self.answers.get(f"{method} {path.split('?')[0]}", {})
        return answer if isinstance(answer, tuple) else (200, answer)


def hosted(monkeypatch, answers: dict[str, object], rec: HostRecord) -> tuple[chat_client.Chat, Answering]:
    chat, host = chat_client.Chat(Path("shop"), Path("home")), Answering(answers)
    monkeypatch.setattr(chat, "record", lambda: rec)
    monkeypatch.setattr(chat, "send", host)
    return chat, host


def test_a_chat_works_whatever_code_its_host_runs_and_never_opens_the_state(monkeypatch):
    monkeypatch.setattr(Store, "open", lambda *_a, **_k: pytest.fail("a chat's server reads no state itself"))
    monkeypatch.setattr(chat_client, "_pause", lambda _s: None)
    row = {"handle": "c1", "slug": "c1-shop"}
    chat, host = hosted(monkeypatch, {
        "GET /chat/contract": SERVES, "GET /changes": [row], "GET /chat/brief/c1-shop": {"version": 2},
        "POST /briefs/challenge": {"slug": "c1-shop", "attempt": 1}, "GET /chat/challenge/c1-shop": {"running": False},
        "GET /decisions": {"available": True, "decisions": []}, "POST /decisions/lookup": {"decisions": []},
        "POST /changes/c1-shop/answers": (409, {"detail": "question q1 is not open"}),
    }, record(code="0" * 64))  # fmt: skip

    said = [chat.save_brief({"title": "t"}), chat.show_status("c1"), chat.challenge_brief("c1", 2, []),
            chat.answer_question("c1.q1", "o1", "", {"kind": "event"}), chat.find_decisions("x", "all",
            include_retired=False), chat.lookup_decisions("q"), chat.write("/decisions/propose", {})]  # fmt: skip

    assert [s.get("error") for s in said] == [None, None, None, "question: c1.q1 is not open", None, None, None]
    assert said[1]["brief"] == {"version": 2}
    assert said[2] == {"requested": True}
    assert [(m, p) for m, p, _ in host.got] == [
        ("GET", "/chat/contract"), ("POST", "/briefs"), ("GET", "/changes"), ("GET", "/chat/brief/c1-shop"),
        ("POST", "/briefs/challenge"), ("GET", "/chat/challenge/c1-shop?version=2&attempt=1"), ("GET", "/changes"),
        ("POST", "/changes/c1-shop/answers"), ("GET", "/decisions?text=x&where=all&retired=false"),
        ("POST", "/decisions/lookup"), ("POST", "/decisions/propose"),
    ]  # fmt: skip  # its contract asked once, before the first write


def test_a_chat_writes_nothing_to_a_host_older_than_its_contract_and_asks_again_after_a_restart(monkeypatch):
    rec = record()
    chat, host = hosted(monkeypatch, {"GET /chat/contract": (404, {"detail": "Not Found"})}, rec)
    assert chat.write("/decisions/propose", {}) == {
        "saved": False, "error": chat_client.OLDER_HOST, "decisions_page": chat.page()
    }  # fmt: skip
    host.answers = {"GET /chat/contract": {"supported": [1]}}  # a host older than this chat's contract
    refused = chat_contract.UNSUPPORTED.format(sent=chat_contract.CHAT, served="1")
    assert chat.call("POST", "/briefs", {}) == (chat_client.STALE, {"error": refused})
    host.answers = {"GET /chat/contract": {"supported": sorted(chat_contract.SUPPORTED)}}
    assert chat.call("POST", "/briefs", {}) == (200, {})
    monkeypatch.setattr(chat, "record", lambda: rec.model_copy(update={"pid": 8}))  # the host restarted
    chat.call("POST", "/briefs", {})
    assert [(m, p) for m, p, _ in host.got] == [("GET", "/chat/contract")] * 3 + [("POST", "/briefs")] + [
        ("GET", "/chat/contract"), ("POST", "/briefs")
    ]  # fmt: skip


def test_a_challenge_is_read_through_a_host_handover_and_never_asked_for_again(monkeypatch):
    monkeypatch.setattr(chat_client, "_pause", lambda _s: None)
    answers = iter([(200, {"running": True}), (503, {"error": "down"}), (200, {"running": False, "verdict": "ok"})])
    asked = {"GET /chat/contract": SERVES, "POST /briefs/challenge": {"slug": "c1-shop", "attempt": 2}}
    chat, host = hosted(monkeypatch, asked, record())
    reads = host.__call__

    def call(rec, method, url, body, timeout):
        out = reads(rec, method, url, body, timeout)
        return next(answers) if "/chat/challenge/" in url else out

    monkeypatch.setattr(chat, "send", call)
    assert chat.challenge_brief("c1", 3, []) == {"requested": True, "verdict": "ok"}
    assert [m for m, p, _ in host.got if "challenge" in p] == ["POST", "GET", "GET", "GET"]


class Lost:
    """An opener whose request reached the host, or not, and got no answer."""

    def __init__(self, exc: OSError) -> None:
        self.exc = exc

    def open(self, _request, **_kw):
        raise self.exc


def test_a_write_whose_answer_was_lost_is_unknown_never_not_done(monkeypatch):
    chat, rec = chat_client.Chat(Path("shop"), Path("home")), record()
    url = f"{rec.url}api/next/briefs"
    monkeypatch.setattr(chat_client, "_LOCAL", Lost(TimeoutError("timed out")))
    code, out = chat.send(rec, "POST", url, {}, 1.0)
    assert (code, out["error"].startswith(chat_client.UNKNOWN)) == (0, True)
    assert chat.send(rec, "GET", url, None, 1.0)[0] == 503  # a read is just read again
    monkeypatch.setattr(chat_client, "_LOCAL", Lost(urllib.error.URLError(ConnectionRefusedError())))
    assert chat.send(rec, "POST", url, {}, 1.0)[0] == 503  # never reached the host
    for cut in (Cut(b'{"saved": tr'), Cut(b"", IncompleteRead(b'{"sa'))):  # an answer cut short
        monkeypatch.setattr(chat_client, "_LOCAL", cut)
        assert chat.send(rec, "POST", url, {}, 1.0)[0] == chat_client.LOST
        assert chat.send(rec, "GET", url, None, 1.0)[0] == 503


def test_a_write_the_host_failed_on_may_be_done_and_one_it_refused_was_not(monkeypatch):
    chat, rec = chat_client.Chat(Path("shop"), Path("home")), record()
    url = f"{rec.url}api/next/briefs"
    for body in (b'{"detail": "boom"}', b'{"det', b""):  # a 500 says nothing of what was written
        monkeypatch.setattr(chat_client, "_LOCAL", Lost(failed(url, 500, body)))
        assert chat.send(rec, "POST", url, {}, 1.0)[0] == chat_client.LOST
        assert chat.send(rec, "GET", url, None, 1.0)[0] == 500
    monkeypatch.setattr(chat_client, "_LOCAL", Lost(failed(url, 422, b'{"saved": false, "title": "too short"}')))
    assert chat.send(rec, "POST", url, {}, 1.0) == (422, {"saved": False, "title": "too short"})
    monkeypatch.setattr(chat_client, "_LOCAL", Lost(failed(url, 503, b'{"detail": "draining"}')))
    assert chat.send(rec, "POST", url, {}, 1.0) == (503, {"detail": "draining"})  # refused before the route ran


def failed(url: str, code: int, body: bytes) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "Internal Server Error", Message(), io.BytesIO(body))


class Cut:
    """An opener whose answer arrives cut short: not JSON, or ending early."""

    def __init__(self, body: bytes, exc: Exception | None = None) -> None:
        self.body, self.exc = body, exc

    def open(self, _request, **_kw):
        if self.exc:
            raise self.exc
        return Answer(self.body)


class Answer(io.BytesIO):
    status = 200


def test_every_write_whose_answer_was_lost_tells_the_chat_it_may_be_done(monkeypatch):
    chat, _ = hosted(monkeypatch, {"GET /chat/contract": SERVES, "GET /changes": [{"handle": "c1",
                     "slug": "c1-shop"}]}, record())  # fmt: skip
    lost = (chat_client.LOST, {"error": chat_client.UNKNOWN})
    chat.send = lambda _r, m, url, _b, _t: lost if m == "POST" else (200, [{"handle": "c1", "slug": "c1-shop"}] if
               url.endswith("/changes") else SERVES)  # fmt: skip
    said = [chat.save_brief({}), chat.challenge_brief("c1", 1, []), chat.write("/decisions/propose", {}),
            chat.answer_question("c1.q1", "o1", "", {"kind": "event"})]  # fmt: skip
    assert [(s.get("saved", s.get("requested", s.get("answered"))), s["error"]) for s in said] == [
        (None, chat_client.UNKNOWN)
    ] * 4  # never false: the host may have done it


def test_fields_a_later_host_adds_to_its_record_never_hide_it_from_a_chat(tmp_path):
    lock = os.open(tmp_path / "host.lock", os.O_RDWR | os.O_CREAT)
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        found = record().model_dump(mode="json") | {"version": "v9.0", "anything": {"new": 1}}
        (tmp_path / "host.json").write_text(json.dumps(found))
        seen = chat_client.Chat(Path("shop"), tmp_path).record()
        assert (seen.token, seen.pid, seen.url) == ("t", 7, "http://127.0.0.1:9/")
    finally:
        os.close(lock)


def test_a_host_that_does_not_answer_its_contract_yet_is_asked_again_and_a_challenge_waits_for_it(monkeypatch):
    monkeypatch.setattr(chat_client, "_pause", lambda _s: None)
    chat, host = hosted(monkeypatch, {"GET /chat/contract": (503, {"error": "starting"})}, record())
    assert chat.call("GET", "/changes") == (503, {"error": "starting"})
    host.answers["GET /chat/contract"] = SERVES
    assert chat.call("GET", "/changes") == (200, {})
    host.answers["POST /briefs/challenge"] = {"slug": "c1-shop", "attempt": 1}
    host.answers["GET /chat/challenge/c1-shop"] = (409, {"detail": "refused"})
    assert chat.challenge_brief("c1", 1, [])["error"] == "refused"  # a refusal ends the wait and is told


def clone(path: Path) -> Path:
    for args in (["init", "-q", str(path)], ["-C", str(path), "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    return path.resolve()


@pytest.fixture
def http(monkeypatch):
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo: [])
    monkeypatch.setattr(Host, "_spawn", lambda _self, slug: pytest.fail(f"no runner starts in these tests ({slug})"))
    m = Machine(record())
    yield TestClient(app.create(m), base_url="http://127.0.0.1", headers=AUTH)
    m.stop_all()


@pytest.mark.parametrize("sent", ["0", "3", "x", "", "01", "²", "1" * 5000])
def test_a_host_refuses_a_contract_it_does_not_serve_before_any_route_runs(tmp_path, http, shared_repo, monkeypatch,
                                                                           sent):  # fmt: skip
    monkeypatch.setenv("OWLBEAR_DATA", str(shared_repo[0]))
    (shared_repo[0] / "owlbear").mkdir()
    r = http.post("/api/next/projects", json={"path": str(clone(tmp_path / "shop"))})
    assert r.status_code == 200, r.text
    p, head = r.json()["id"], subprocess.run(["git", "-C", str(shared_repo[0]), "rev-parse", "HEAD"],  # noqa: S603, S607
                                              capture_output=True, text=True, check=True).stdout  # fmt: skip
    told = {chat_contract.HEADER: sent.encode("latin-1")}  # as a header's bytes arrive
    decision = {"title": "x", "statement": "x", "confirmed": True}
    for url, body in ((f"/p/{p}/api/next/briefs", {"title": "t"}), ("/api/next/owlbear/decisions/propose", decision),
                      ("/api/next/chat/contract", None)):  # fmt: skip
        r = http.request("GET" if body is None else "POST", url, json=body, headers=told)
        assert (r.status_code, r.json()["contract"]) == (409, "unsupported"), url
        assert r.json()["detail"].startswith(
            "OwlBear does not serve this chat's owlbear-delivery server (chat contract"
        )
    assert http.get(f"/p/{p}/api/next/changes").json() == []  # a page names no contract
    after = subprocess.run(["git", "-C", str(shared_repo[0]), "rev-parse", "HEAD"],  # noqa: S603, S607
                           capture_output=True, text=True, check=True).stdout  # fmt: skip
    assert after == head
    assert http.get("/api/next/chat/contract", headers={chat_contract.HEADER: "1"}).json() == {"supported": [1, 2]}


def test_a_host_reply_without_what_a_chat_reads_breaks_the_contract(chat_replied):
    chat_replied("POST", "/briefs/challenge", {"slug": "c1-shop", "attempt": 1, "paused": False, "more": 1})
    lost = [
        ("POST", "/briefs/challenge", {"attempt": 1, "paused": False}),  # the chat would never read its outcome
        ("GET", "/p/x/api/next/changes", [{"handle": "c1"}]),
        ("GET", "/api/next/owlbear/decisions?text=", {"available": True, "decisions": [{"id": "D-1"}]}),
        ("GET", "/api/next/chat/contract", {"served": [1]}),
    ]
    for method, url, out in lost:
        with pytest.raises(AssertionError, match="lost what chat contract 1 reads"):
            chat_replied(method, url, out)


def test_a_brief_the_host_could_not_give_is_told_not_left_out(monkeypatch):
    chat, _ = hosted(monkeypatch, {
        "GET /chat/contract": SERVES, "GET /changes": [{"handle": "c1", "slug": "c1-shop"}],
        "GET /chat/brief/c1-shop": (503, {"error": "handing over"}),
    }, record())  # fmt: skip
    status = chat.show_status("c1")
    assert ("brief" in status, status["error"]) == (False, "brief: handing over; call show_status again")
