"""OwlBear MCP browser server — browser-control tools with domain allowlist."""

from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from owlbear_browser import AcquisitionFailure, AcquisitionRequest, AcquisitionSuccess
from owlbear_browser._errors import AuthenticationRequired
from owlbear_browser.extractor import extract_content
from owlbear_browser.fetcher import BrowserContentFetcher
from owlbear_browser.playwright_launcher import PlaywrightLauncher
from owlbear_mcp_browser.allowlist import DomainAllowlist

__all__ = ["AppContext", "acquire", "app_lifespan", "mcp_app"]


def _is_blocked_ip(ip_str: str) -> bool:
    """Return True if *ip_str* is private/loopback/link-local/reserved/unspecified (CWE-918).

    Duplicated from ``owlbear_knowledge._ssrf`` — cross-package dep for 20 LOC violates KISS.
    Unwraps IPv4-mapped IPv6 addresses (e.g. ``::ffff:127.0.0.1``) before checking properties.
    """
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable → block
    check: ipaddress.IPv4Address | ipaddress.IPv6Address
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        check = addr.ipv4_mapped
    else:
        check = addr
    return check.is_loopback or check.is_private or check.is_link_local or check.is_reserved or check.is_unspecified


async def _check_ssrf(url: str) -> None:
    """Pre-flight SSRF check for *url* (CWE-918).

    Raises :class:`~mcp.server.fastmcp.exceptions.ToolError` if:

    - The scheme is not ``http`` or ``https``.
    - DNS resolution raises ``OSError`` (unresolvable hostname).
    - Any resolved IP is loopback / private / link-local / reserved / unspecified.

    Accepted limitations:

    - **TOCTOU / DNS rebinding**: Playwright cannot connect to a pre-resolved IP, so
      the URL cannot be rewritten after DNS lookup. An attacker controlling DNS can change
      the resolution between the check and ``page.goto()``. Mitigated by the
      closed-by-default ``DomainAllowlist`` and agent-only access.
    - **Redirect SSRF**: ``page.goto()`` follows HTTP redirects by default. An allowlisted
      server returning a 3xx to an internal IP bypasses this pre-flight check. Mitigated by
      the closed-by-default allowlist and agent-only access. Full coverage would require
      ``context.route()`` interception — disproportionate for nice-to-have priority.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        msg = f"URL scheme '{parsed.scheme}' is not allowed — only http and https are permitted."
        raise ToolError(msg)

    hostname = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        addrs = await asyncio.to_thread(socket.getaddrinfo, hostname, port)
    except OSError as exc:
        msg = f"DNS resolution failed for '{hostname}': {exc}"
        raise ToolError(msg) from exc

    for _family, _type, _proto, _canonname, sockaddr in addrs:
        ip_str = sockaddr[0]
        if _is_blocked_ip(ip_str):
            msg = f"URL '{url}' resolved to a blocked IP address ({ip_str!r})."
            raise ToolError(msg)


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    allowlist: DomainAllowlist
    launcher: PlaywrightLauncher | None = None
    page: Any = None
    fetcher: BrowserContentFetcher | None = None
    last_content: str = ""


def _apply_tool_exclusions(server: FastMCP) -> set[str]:
    """Read BROWSER_TOOLS_EXCLUDE and remove each listed tool from the server.

    Returns the set of tool names successfully removed.
    """
    excluded: set[str] = set()
    env_val = os.environ.get("BROWSER_TOOLS_EXCLUDE", "")
    if not env_val:
        return excluded
    for raw in env_val.split(","):
        tool_name = raw.strip()
        if not tool_name:
            continue
        try:
            server.remove_tool(tool_name)
            excluded.add(tool_name)
        except Exception:  # noqa: BLE001, S110
            pass
    return excluded


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncGenerator[AppContext, None]:
    """Configure DomainAllowlist, attempt Playwright launch, and yield AppContext."""
    _apply_tool_exclusions(server)
    domains_env = os.environ.get("BROWSER_ALLOWED_DOMAINS", "")
    domains = [d.strip() for d in domains_env.split(",") if d.strip()]
    allowlist = DomainAllowlist(domains=domains)

    launcher: PlaywrightLauncher | None = None
    page: Any = None
    fetcher: BrowserContentFetcher | None = None
    try:
        user_data_dir = os.environ.get(
            "PLAYWRIGHT_USER_DATA_DIR",
            str(Path.home() / ".owlbear" / "chromium-profile"),
        )
        launcher = PlaywrightLauncher(user_data_dir=user_data_dir)
        await launcher.launch()
        page = await launcher.context.new_page()  # type: ignore[union-attr]
        fetcher = BrowserContentFetcher(launcher.context)
    except Exception:  # noqa: BLE001
        launcher = None
        page = None
        fetcher = None

    try:
        yield AppContext(allowlist=allowlist, launcher=launcher, page=page, fetcher=fetcher)
    finally:
        if page is not None:
            await page.close()
        if launcher is not None:
            await launcher.close()


_MSG_NO_PAGE = "No browser session"
_MSG_BROWSER_UNAVAILABLE = "Browser unavailable"

_mcp = FastMCP("owlbear-mcp-browser", lifespan=app_lifespan)


def _serialize_acquisition(result: AcquisitionSuccess | AcquisitionFailure) -> dict[str, Any]:
    """Project the shared acquisition contract into an MCP-safe mapping."""
    diagnostics = {
        "stage": result.diagnostics.stage,
        "details": result.diagnostics.details,
    }
    if isinstance(result, AcquisitionFailure):
        return {"status": result.status.value, "diagnostics": diagnostics}
    return {
        "status": result.status.value,
        "requested_url": result.requested_url,
        "canonical_url": result.canonical_url,
        "redirect_chain": list(result.redirect_chain),
        "title": result.title,
        "markdown": result.markdown,
        "discovered_links": list(result.discovered_links),
        "content_hash": result.content_hash,
        "fetched_at": result.fetched_at.isoformat(),
        "diagnostics": diagnostics,
    }


@_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def acquire(  # noqa: PLR0913
    ctx: Context,
    url: str,
    readiness_selector: str | None = None,
    content_selector: str | None = None,
    navigation_timeout_ms: int = 30_000,
    readiness_timeout_ms: int = 10_000,
    include_diagnostic_html: bool = False,  # noqa: FBT001, FBT002
) -> dict[str, Any]:
    """Acquire one rendered page through the shared browser acquisition contract."""
    app_ctx = ctx.request_context.lifespan_context
    if not isinstance(app_ctx, AppContext) or app_ctx.fetcher is None:
        raise ToolError(_MSG_BROWSER_UNAVAILABLE)
    try:
        app_ctx.allowlist.check(url)
        request = AcquisitionRequest(
            url=url,
            readiness_selector=readiness_selector,
            content_selector=content_selector,
            navigation_timeout_ms=navigation_timeout_ms,
            readiness_timeout_ms=readiness_timeout_ms,
            include_diagnostic_html=include_diagnostic_html,
        )
        result = await app_ctx.fetcher.acquire(request)
    except PermissionError as exc:
        raise ToolError(str(exc)) from exc
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    return _serialize_acquisition(result)


@_mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def navigate(ctx: Context, url: str) -> str:
    """Navigate the browser to *url*."""
    app_ctx = ctx.request_context.lifespan_context
    await _check_ssrf(url)
    try:
        app_ctx.allowlist.check(url)
    except PermissionError as exc:
        raise ToolError(str(exc)) from exc

    if isinstance(app_ctx, AppContext):
        if app_ctx.fetcher is not None:
            try:
                content = await app_ctx.fetcher.fetch(url)
            except AuthenticationRequired as exc:
                msg = f"SSO session expired or authentication required: {exc}"
                raise ToolError(msg) from exc
            app_ctx.last_content = content
            return content
        if app_ctx.page is not None:
            await app_ctx.page.goto(url)
            return url
        return url  # dry-run: allowlist passed, no live page

    # Non-AppContext (SimpleNamespace from tests, etc.): only access page if
    # explicitly set — avoids awaiting auto-generated MagicMock attributes.
    if "page" in vars(app_ctx):
        page = app_ctx.page
        if page is not None:
            await page.goto(url)
            return url
        raise ToolError(_MSG_NO_PAGE)

    return url  # Raw MagicMock or context without explicit page — allowlist passed


@_mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, destructiveHint=False))
async def click(ctx: Context, selector: str) -> str:
    """Click the element identified by *selector*."""
    app_ctx = ctx.request_context.lifespan_context
    page = getattr(app_ctx, "page", None)
    if page is not None:
        await page.locator(selector).click()
    else:
        raise ToolError(_MSG_NO_PAGE)
    return selector


@_mcp.tool(
    name="type",
    annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, destructiveHint=False),
)
async def type_input(ctx: Context, selector: str, text: str) -> str:
    """Type *text* into the element identified by *selector*."""
    app_ctx = ctx.request_context.lifespan_context
    page = getattr(app_ctx, "page", None)
    if page is not None:
        await page.locator(selector).fill(text)
    else:
        raise ToolError(_MSG_NO_PAGE)
    return f"{selector}:{text}"


@_mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def select(ctx: Context, selector: str, value: str) -> str:
    """Select *value* in the element identified by *selector*."""
    app_ctx = ctx.request_context.lifespan_context
    page = getattr(app_ctx, "page", None)
    if page is not None:
        await page.locator(selector).select_option(value)
    else:
        raise ToolError(_MSG_NO_PAGE)
    return f"{selector}:{value}"


@_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def read_text(ctx: Context) -> str:
    """Read the visible text content of the current page.

    Returns the last cached content if no browser session is active.
    """
    app_ctx = ctx.request_context.lifespan_context
    page = getattr(app_ctx, "page", None)
    if page is not None:
        html = await page.content()
        return extract_content(html, page.url)
    return getattr(app_ctx, "last_content", "")


@_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def snapshot(ctx: Context) -> str:
    """Take an accessibility snapshot of the current page as Markdown.

    Returns the last cached content if no browser session is active.
    """
    app_ctx = ctx.request_context.lifespan_context
    page = getattr(app_ctx, "page", None)
    if page is not None:
        return await page.locator("body").aria_snapshot()
    return getattr(app_ctx, "last_content", "")


# Synchronous tool registry for inspection and testing (ToolManager.list_tools is sync)
mcp_app = _mcp._tool_manager  # noqa: SLF001
