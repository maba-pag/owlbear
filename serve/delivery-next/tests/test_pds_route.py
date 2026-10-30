"""The browser tests' route to the PDS CDN settles every request, and a run fetches each CDN file once (#742)."""

from types import SimpleNamespace

import pytest

BASE = "http://127.0.0.1:1/"
FONT = "https://cdn.ui.porsche.com/x.woff2"


class Route:
    """A request the route answers; ``fetch`` gives each answer in turn, raising one that is an exception."""

    def __init__(self, url: str, *answers) -> None:
        self.request = SimpleNamespace(url=url)
        self.answers = list(answers)
        self.fetches, self.settled = [], []

    def fetch(self, **kwargs):
        self.fetches.append(kwargs)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def fulfill(self, **kwargs) -> None:
        self.settled.append(("fulfill", kwargs))

    def abort(self, *args) -> None:
        self.settled.append(("abort", args))

    def continue_(self) -> None:
        self.settled.append(("continue", ()))


def ok(body: bytes) -> SimpleNamespace:
    headers = {"content-type": "font/woff2", "content-length": str(len(body)), "content-encoding": "br"}
    return SimpleNamespace(ok=True, status=200, headers=headers, body=lambda: body)


@pytest.fixture
def routed(pds, monkeypatch, tmp_path):
    """The handler ``pds.only`` routes a page through, as a fresh test worker of a run sharing *tmp_path* has it."""
    monkeypatch.setattr(pds, "_fetched", {})
    monkeypatch.setattr(pds, "shared", tmp_path / "pds-cdn")
    handlers = []
    pds.only(SimpleNamespace(route=lambda _pattern, handler: handlers.append(handler)), BASE)
    return handlers[0]


def test_a_cdn_request_whose_fetch_keeps_failing_is_aborted_so_the_page_loads_on(routed, capsys):
    from playwright.sync_api import Error  # noqa: PLC0415 - the optional browser runtime

    r = Route(FONT, Error("Route.fetch: write EPROTO"), Error("Route.fetch: read ECONNRESET"))
    routed(r)
    assert r.settled == [("abort", ("failed",))]
    assert len(r.fetches) == 2
    assert all(0 < f["timeout"] < 30_000 for f in r.fetches)  # never the test's whole 30 s
    assert "ECONNRESET" in capsys.readouterr().out  # the reason is in the test's output


def test_a_cdn_request_is_fetched_again_once_and_its_answer_kept(routed):
    from playwright.sync_api import Error  # noqa: PLC0415 - the optional browser runtime

    r = Route(FONT, Error("Route.fetch: write EPROTO"), ok(b"font"))
    routed(r)
    ((how, answer),) = r.settled
    assert (how, answer["status"], answer["body"]) == ("fulfill", 200, b"font")
    assert "content-encoding" not in answer["headers"]
    again = Route(FONT)  # any fetch would fail: it has no answers
    routed(again)
    assert (again.fetches, again.settled[0][1]["body"]) == ([], b"font")


def test_another_worker_of_the_run_answers_a_fetched_file_without_the_cdn(routed, pds, monkeypatch):
    routed(Route(FONT, ok(b"font")))
    monkeypatch.setattr(pds, "_fetched", {})  # the next worker's memory starts empty
    again = Route(FONT)  # any fetch would fail: it has no answers
    routed(again)
    assert again.fetches == []
    assert again.settled[0][1]["body"] == b"font"


def test_a_failed_cdn_answer_is_passed_on_and_not_kept(routed, pds):
    missing = SimpleNamespace(ok=False, status=404, headers={}, body=lambda: b"")
    r = Route(FONT, missing)
    routed(r)
    assert r.settled == [("fulfill", {"response": missing})]
    assert not list(pds.shared.glob("*"))
    again = Route(FONT, ok(b"font"))
    routed(again)
    assert len(again.fetches) == 1


def test_the_test_host_goes_through_and_anything_else_is_refused(routed):
    host, other = Route(BASE + "api"), Route("https://example.com/x.js")
    routed(host)
    routed(other)
    assert (host.settled, other.settled) == ([("continue", ())], [("abort", ())])


def test_a_request_routed_while_another_is_fetched_never_waits_for_it(routed):
    """Playwright runs a page's route handlers on one thread, nested within a fetch: waiting there would hang it."""
    nested = Route(FONT, ok(b"font"))

    class Fetching(Route):
        def fetch(self, **kwargs):
            routed(nested)  # the same file asked for again while this fetch is under way
            return super().fetch(**kwargs)

    first = Fetching(FONT, ok(b"font"))
    routed(first)
    assert [r.settled[0][1]["body"] for r in (nested, first)] == [b"font", b"font"]
