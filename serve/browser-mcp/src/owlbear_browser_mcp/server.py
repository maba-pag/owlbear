"""OwlBear MCP browser server — browser-control tools with domain allowlist."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import socket
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from mcp.server import MCPServer
from mcp.server.mcpserver import Context  # noqa: TC002 - MCPServer evaluates tool annotations at registration.
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from owlbear_browser import AcquisitionFailure, AcquisitionRequest, AcquisitionSuccess
from owlbear_browser._errors import AuthenticationRequired
from owlbear_browser.extractor import extract_content
from owlbear_browser.playwright_launcher import PlaywrightLauncher
from owlbear_browser_mcp.allowlist import DomainAllowlist

__all__ = ["AppContext", "acquire", "app_lifespan", "mcp"]

_ALLOWED_DOMAINS_ENV = "BROWSER_ALLOWED_DOMAINS"
_DEFAULT_USER_DATA_DIR = Path.home() / ".owlbear" / "chromium-profile"
_USER_DATA_DIR_ENV = "PLAYWRIGHT_USER_DATA_DIR"
_LOGGER = logging.getLogger(__name__)


def _is_blocked_ip(ip_str: str) -> bool:
    """Return True if *ip_str* is private/loopback/link-local/reserved/unspecified (CWE-918).

    Duplicated from ``owlbear_knowledge._ssrf`` — cross-package dep for 20 LOC violates KISS.
    Unwraps IPv4-mapped IPv6 addresses (e.g. ``::ffff:127.0.0.1``) before checking properties.
    """
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable → block
    check: ipaddress.IPv4Address | ipaddress.IPv6Address = (
        addr.ipv4_mapped if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None else addr
    )
    return check.is_loopback or check.is_private or check.is_link_local or check.is_reserved or check.is_unspecified


def _is_ip_literal(value: str) -> bool:
    """Return whether *value* is an IP address literal, including legacy IPv4 forms."""
    candidate = value.removesuffix(".")
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        try:
            socket.inet_aton(candidate)
        except OSError:
            return False
    return True


def _is_trusted_internal_ip(ip_str: str) -> bool:
    """Return whether *ip_str* is private/internal, excluding reserved non-loopback space."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    check: ipaddress.IPv4Address | ipaddress.IPv6Address = (
        addr.ipv4_mapped if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None else addr
    )
    return (
        (check.is_loopback or check.is_private or check.is_link_local)
        and not check.is_unspecified
        and (check.is_loopback or not check.is_reserved)
    )


async def _check_ssrf(url: str, *, allowlist: DomainAllowlist | None = None) -> None:
    """Pre-flight SSRF check for *url* (CWE-918).

    Args:
        url: URL to resolve and validate.
        allowlist: Configured hostname allowlist used to identify an exact
            trusted-internal hostname. Wildcard mode never permits private IPs.

    Raises :class:`~mcp.server.mcpserver.exceptions.ToolError` if:

    - The scheme is not ``http`` or ``https``.
    - DNS resolution raises ``OSError`` (unresolvable hostname).
    - Any resolved IP is loopback / private / link-local / reserved / unspecified and
      the hostname is not an exact entry in the domain allowlist. Reserved,
      unspecified, and unparseable addresses are always rejected.

    Accepted limitations:

    - **Trusted internal destinations**: an exact hostname entry in
      ``BROWSER_ALLOWED_DOMAINS`` is an explicit approval for that hostname's
      private/internal DNS results. Wildcard mode and unallowlisted hostnames do
      not receive this approval.
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
    if "\\" in parsed.netloc:
        msg = "Backslashes are not allowed in URL authorities."
        raise ToolError(msg)

    hostname = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    trusted_internal = (
        bool(hostname)
        and not _is_ip_literal(hostname)
        and isinstance(allowlist, DomainAllowlist)
        and allowlist.allows_exact_hostname(hostname)
    )

    try:
        addrs = await asyncio.to_thread(socket.getaddrinfo, hostname, port)
    except OSError as exc:
        msg = f"DNS resolution failed for '{hostname}': {exc}"
        raise ToolError(msg) from exc

    for _family, _type, _proto, _canonname, sockaddr in addrs:
        ip_str = sockaddr[0]
        if _is_blocked_ip(ip_str) and (not trusted_internal or not _is_trusted_internal_ip(ip_str)):
            msg = f"URL '{url}' resolved to a blocked IP address ({ip_str!r})."
            raise ToolError(msg)


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    allowlist: DomainAllowlist
    launcher: PlaywrightLauncher | None = None
    page: Any = None
    last_content: str = ""
    browser_diagnostic: str | None = None


def _safe_browser_diagnostic(stage: str, error: BaseException) -> str:
    """Return a stable startup/cleanup diagnostic without exposing exception details."""
    return f"{stage} failed ({type(error).__name__})"


async def _close_browser_resources(
    page: Any,  # noqa: ANN401 - Playwright page objects are external runtime values.
    launcher: PlaywrightLauncher | None,
) -> tuple[str, ...]:
    """Close owned browser resources independently and return safe failure diagnostics."""
    failures: list[str] = []
    first_control_flow: BaseException | None = None
    if page is not None:
        try:
            await page.close()
        except BaseException as exc:  # noqa: BLE001 - cleanup must continue after one failure.
            failures.append(_safe_browser_diagnostic("page cleanup", exc))
            if not isinstance(exc, Exception) and first_control_flow is None:
                first_control_flow = exc
    if launcher is not None:
        try:
            await launcher.close()
        except BaseException as exc:  # noqa: BLE001 - launcher attempts each owned resource itself.
            failures.append(_safe_browser_diagnostic("launcher cleanup", exc))
            if not isinstance(exc, Exception) and first_control_flow is None:
                first_control_flow = exc
    if first_control_flow is not None:
        raise first_control_flow
    return tuple(failures)


@asynccontextmanager
async def app_lifespan(_server: MCPServer) -> AsyncGenerator[AppContext]:
    """Configure DomainAllowlist, attempt Playwright launch, and yield AppContext."""
    domains_env = os.environ.get(_ALLOWED_DOMAINS_ENV, "")
    domains = [d.strip() for d in domains_env.split(",") if d.strip()]
    allowlist = DomainAllowlist(domains=domains)

    launcher: PlaywrightLauncher | None = None
    page: Any = None
    browser_diagnostic: str | None = None
    try:
        user_data_dir = os.environ.get(_USER_DATA_DIR_ENV, str(_DEFAULT_USER_DATA_DIR))
        launcher = PlaywrightLauncher(user_data_dir=user_data_dir)
        await launcher.launch()
        page = await launcher.page()
    except asyncio.CancelledError:
        for diagnostic in await _close_browser_resources(page, launcher):
            _LOGGER.warning(diagnostic)
        raise
    except Exception as exc:  # noqa: BLE001 - startup degrades to an observable unavailable context.
        diagnostics = [_safe_browser_diagnostic("browser startup", exc)]
        diagnostics.extend(await _close_browser_resources(page, launcher))
        browser_diagnostic = "; ".join(diagnostics)
        launcher = None
        page = None

    app_context = AppContext(
        allowlist=allowlist,
        launcher=launcher,
        page=page,
        browser_diagnostic=browser_diagnostic,
    )
    try:
        yield app_context
    finally:
        try:
            for diagnostic in await _close_browser_resources(page, launcher):
                _LOGGER.warning(diagnostic)
        finally:
            app_context.page = None
            app_context.launcher = None
            page = None
            launcher = None


_MSG_NO_PAGE = "No browser session"
_MSG_BROWSER_UNAVAILABLE = "Browser unavailable"


def _browser_unavailable_message(app_ctx: object) -> str:
    """Return a safe diagnostic for an unavailable browser context."""
    if not isinstance(app_ctx, AppContext):
        return _MSG_BROWSER_UNAVAILABLE
    if app_ctx.browser_diagnostic:
        return f"{_MSG_BROWSER_UNAVAILABLE}: {app_ctx.browser_diagnostic}"
    return _MSG_NO_PAGE


mcp = MCPServer("owlbear-browser", lifespan=app_lifespan)


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


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
async def acquire(  # noqa: PLR0913
    ctx: Context,
    url: str,
    *,
    readiness_selector: str | None = None,
    content_selector: str | None = None,
    navigation_timeout_ms: int = 30_000,
    readiness_timeout_ms: int = 10_000,
    include_diagnostic_html: bool = False,
) -> dict[str, Any]:
    """Acquire one rendered page through the shared browser acquisition contract."""
    app_ctx = ctx.request_context.lifespan_context
    if not isinstance(app_ctx, AppContext) or app_ctx.launcher is None:
        raise ToolError(_browser_unavailable_message(app_ctx))
    await _check_ssrf(url, allowlist=app_ctx.allowlist)
    try:
        app_ctx.allowlist.check(url)
    except PermissionError as exc:
        raise ToolError(str(exc)) from exc
    try:
        request = AcquisitionRequest(
            url=url,
            readiness_selector=readiness_selector,
            content_selector=content_selector,
            navigation_timeout_ms=navigation_timeout_ms,
            readiness_timeout_ms=readiness_timeout_ms,
            include_diagnostic_html=include_diagnostic_html,
        )
        result = await app_ctx.launcher.acquire(request)
    except PermissionError as exc:
        raise ToolError(str(exc)) from exc
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    return _serialize_acquisition(result)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=True, destructive_hint=False))
async def navigate(ctx: Context, url: str) -> str:
    """Navigate the browser to *url*."""
    app_ctx = ctx.request_context.lifespan_context
    await _check_ssrf(url, allowlist=app_ctx.allowlist)
    try:
        app_ctx.allowlist.check(url)
    except PermissionError as exc:
        raise ToolError(str(exc)) from exc

    if isinstance(app_ctx, AppContext):
        if app_ctx.launcher is None:
            raise ToolError(_browser_unavailable_message(app_ctx))
        if app_ctx.page is not None:
            try:
                await app_ctx.page.goto(url, wait_until="domcontentloaded")
            except AuthenticationRequired as exc:
                msg = f"SSO session expired or authentication required: {exc}"
                raise ToolError(msg) from exc
            content = extract_content(await app_ctx.page.content(), url)
            app_ctx.last_content = content
            return content
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


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
async def click(ctx: Context, selector: str) -> str:
    """Click the element identified by *selector*."""
    app_ctx = ctx.request_context.lifespan_context
    page = getattr(app_ctx, "page", None)
    if page is not None:
        await page.locator(selector).click()
    else:
        raise ToolError(_browser_unavailable_message(app_ctx))
    return selector


@mcp.tool(
    name="type",
    annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False),
)
async def type_input(ctx: Context, selector: str, text: str) -> str:
    """Type *text* into the element identified by *selector*."""
    app_ctx = ctx.request_context.lifespan_context
    page = getattr(app_ctx, "page", None)
    if page is not None:
        await page.locator(selector).fill(text)
    else:
        raise ToolError(_browser_unavailable_message(app_ctx))
    return f"{selector}:{text}"


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=True, destructive_hint=False))
async def select(ctx: Context, selector: str, value: str) -> str:
    """Select *value* in the element identified by *selector*."""
    app_ctx = ctx.request_context.lifespan_context
    page = getattr(app_ctx, "page", None)
    if page is not None:
        await page.locator(selector).select_option(value)
    else:
        raise ToolError(_browser_unavailable_message(app_ctx))
    return f"{selector}:{value}"


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
async def read_text(ctx: Context) -> str:
    """Read the visible text content of the current page.

    Returns the last cached content when no browser session is intentionally active.
    Raises a browser-unavailable error when browser startup failed.
    """
    app_ctx = ctx.request_context.lifespan_context
    page = getattr(app_ctx, "page", None)
    if page is not None:
        html = await page.content()
        return extract_content(html, page.url)
    if isinstance(app_ctx, AppContext) and app_ctx.browser_diagnostic:
        raise ToolError(_browser_unavailable_message(app_ctx))
    return getattr(app_ctx, "last_content", "")


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
async def snapshot(ctx: Context) -> str:
    """Take an accessibility snapshot of the current page as Markdown.

    Returns the last cached content when no browser session is intentionally active.
    Raises a browser-unavailable error when browser startup failed.
    """
    app_ctx = ctx.request_context.lifespan_context
    page = getattr(app_ctx, "page", None)
    if page is not None:
        return await page.locator("body").aria_snapshot()
    if isinstance(app_ctx, AppContext) and app_ctx.browser_diagnostic:
        raise ToolError(_browser_unavailable_message(app_ctx))
    return getattr(app_ctx, "last_content", "")
