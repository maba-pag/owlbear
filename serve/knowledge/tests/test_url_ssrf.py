"""Knowledge URL intake should block non-public network targets before fetching."""

from __future__ import annotations

import socket
from typing import ClassVar, Self

import pytest

import owlbear_knowledge._ssrf as ssrf_module
import owlbear_knowledge.fetcher as fetcher_module
from owlbear_knowledge._ssrf import SSRFProtectionError
from owlbear_knowledge.intake import read_url


class FakeResponse:
    text = "public content"

    def raise_for_status(self) -> None:
        return None


class RecordingAsyncClient:
    calls: ClassVar[list[str]] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str) -> FakeResponse:
        self.calls.append(url)
        return FakeResponse()


@pytest.mark.asyncio
async def test_read_url_blocks_loopback_before_http_client(monkeypatch: pytest.MonkeyPatch) -> None:
    RecordingAsyncClient.calls = []
    monkeypatch.setattr(fetcher_module.httpx, "AsyncClient", RecordingAsyncClient)

    with pytest.raises(SSRFProtectionError, match="blocked network address"):
        await read_url("http://127.0.0.1:12345/private")

    assert RecordingAsyncClient.calls == []


@pytest.mark.asyncio
async def test_read_url_allows_public_resolved_address(monkeypatch: pytest.MonkeyPatch) -> None:
    RecordingAsyncClient.calls = []

    def public_getaddrinfo(_host: str, port: int, **kwargs: object) -> list[tuple[object, ...]]:
        socktype = kwargs.get("type", 0)
        return [(socket.AF_INET, socktype, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(ssrf_module.socket, "getaddrinfo", public_getaddrinfo)
    monkeypatch.setattr(fetcher_module.httpx, "AsyncClient", RecordingAsyncClient)

    result = await read_url("https://example.test/page")

    assert result.source == "https://example.test/page"
    assert RecordingAsyncClient.calls == ["https://example.test/page"]
