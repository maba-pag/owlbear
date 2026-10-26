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
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from owlbear_delivery_next.local_system import codebase

CHAT = 2  # the contract this code's chat server speaks
SUPPORTED = frozenset({1, 2})  # the contracts this code's host serves
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
