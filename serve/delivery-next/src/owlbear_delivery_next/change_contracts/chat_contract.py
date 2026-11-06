"""The chat contract (D-01M5Q5GKHX7BJTXPEW2MHGS9E0): what a chat's owlbear-delivery server may send a host.

A chat server loads one version's code and lives as long as its chat; OwlBear updates beneath it. So the server reads
and writes nothing itself and talks to the host only over HTTP, and every request names the contract it speaks in
``HEADER``. A host refuses a contract it does not support before any route runs; it keeps supporting every contract
in ``SUPPORTED`` for as long as such servers may live, through adapters when its own models change.

Contract 1: the tools, their argument schemas and replies as ``commands/mcp_server.py`` advertised them when this
module was written, the routes ``commands/chat_client.py`` calls with the bodies they take
(``tests/fixtures/chat_contract_1.json``), and the fields of ``host.json`` a chat finds its host by (``HostFound``).
A host may only add to them (an optional field, a new route); anything a server of contract 1 could notice raises
``CHAT`` and keeps 1 in ``SUPPORTED``, with its fixture.

Contract 2: contract 1, and ``record_decision`` takes ``origin`` (`approved` when the owner took the chat's
recommendation as shown, D-01M5WAFJ99912ER7V0YEPJP2G5), sent to ``/decisions/propose``
(``tests/fixtures/chat_contract_2.json``).

Contract 3: contract 2, and the ``await_challenge`` tool, which reads a brief version's challenge without asking for
it. Its reads need fields a host answers with but contract 2 did not promise, so they are frozen here: a Change's row
(``GET /changes``) names its ``step``, ``line``, ``action`` and ``actor``; a brief (``GET /chat/brief/{slug}``) its
``challenge.version`` and ``challenge.attempt``; a challenge read (``GET /chat/challenge/{slug}``) the ``version`` of
the draft it answers for, running or not (``tests/fixtures/chat_contract_3.json``).

Contract 4: contract 3, and a person check in ``save_brief`` takes ``covers``, the criteria it checks, so an amendment
redoes only the checks of the criteria it changes (TD-185, ``tests/fixtures/chat_contract_4.json``). A server of an
earlier contract sends none, which covers them all.

Contract 5: contract 4, and ``complete_decision`` marks a wholly finite OwlBear project instruction spent, with
its expected revision, exact condition quote and evidence, sent to ``/decisions/{id}/complete``
(``tests/fixtures/chat_contract_5.json``). Existing withdrawal and replacement contracts are unchanged.

Contract 6: contract 5, and ``lookup_decisions`` starts the lookup and waits about 70 s, then says running with its
``lookup_id``, which the ``await_lookup`` tool reads (``POST /decisions/lookups``,
``GET /decisions/lookups/{lookup_id}``), so no tool call outlasts the Copilot client's 180 s cut (#972). A Change
whose shaping chat acts next shows ``Continue in the shaping chat`` (#960); a host answers it as ``Approve brief`` to
a chat of an earlier contract, whose ``await_challenge`` reads only that label as the shaping chat's own wait
(``own_waits`` in ``tests/fixtures/chat_contract_6.json``).

Contract 7: contract 6, and ``save_visual_check`` takes a UI brief's render ``recipe`` and its ``preparation``
option; a host requires the recipe for a UI brief with states only from a chat of this contract, whose draft it then
captures (D-01M61V2GR0C6JV2R6KJ0WR4PNB). The ``await_capture`` tool reads that capture
(``GET /briefs/capture?change=cN``, ``tests/fixtures/chat_contract_7.json``). A draft an earlier chat saves keeps no
recipe and gets no capture, as before.

A host whose contract answer has ``"admit_by": true`` refuses a ``/decisions/propose`` save that starts after the
time in the request's ``X-OwlBear-Admit-By`` header (#846); a chat whose host lacks it never takes a lost answer as
not saved.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from owlbear_delivery_next.local_system import codebase

CHAT = 7  # the contract this code's chat server speaks
SUPPORTED = frozenset({1, 2, 3, 4, 5, 6, 7})  # the contracts this code's host serves
CAPTURES = 7  # from this contract a chat sends a UI brief's render recipe, and its draft's pages are captured
HEADER = "X-OwlBear-Chat"
CAPABILITY = "/api/next/chat/contract"  # a host that has none predates the contract
UNSUPPORTED = (
    "OwlBear does not serve this chat's owlbear-delivery server (chat contract {sent}; it serves {served}): start a "
    f"new Copilot-runtime chat, or focus this chat and use {codebase.STOP_START}"
)


def refusal(sent: str) -> dict[str, object]:
    """The answer to a request whose contract this host does not serve."""
    served = ", ".join(str(n) for n in sorted(SUPPORTED))
    return {"detail": UNSUPPORTED.format(sent=sent or "none", served=served), "contract": "unsupported"}


def captures(sent: str | None) -> bool:
    """Whether a chat that names *sent* sends a UI brief's render recipe; a page or an older server sends none."""
    return sent is not None and sent.isdigit() and int(sent) >= CAPTURES


def served(sent: str | None) -> bool:
    """Whether this host serves a request that names *sent*; one naming none is a page's, or an older server's."""
    return sent is None or sent in {str(n) for n in SUPPORTED}


class HostFound(BaseModel):
    """What a chat reads of a host's ``host.json``: fields a later host adds never hide it from an older chat."""

    model_config = ConfigDict(extra="ignore")

    url: str
    token: str
    pid: int
    started_at: datetime
    ready: list[str] | None = None
    project: str = ""
