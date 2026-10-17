"""Driving one capture page: its guard off the preview, the brief's steps, and the errors it records (TD-60, R8)."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from owlbear_delivery_next.change_contracts.visual_records import PageError

if TYPE_CHECKING:
    from playwright.sync_api import ConsoleMessage, Page, Route, WebSocketRoute

    from owlbear_delivery_next.change_contracts.models import VisualState, VisualStep

CONSOLE = frozenset({"error", "assert"})  # console message types that count as errors (R8)
CLICKABLE = ("button", "link", "tab", "menuitem", "checkbox", "radio", "switch", "option")
EDITABLE = (
    "input:not([type=button],[type=submit],[type=reset],[type=checkbox],[type=radio],[type=image],[type=hidden]),"
    " textarea, [contenteditable]:not([contenteditable=false])"
)
STATIC = frozenset({"stylesheet", "font", "image", "media", "script"})  # files a page may fetch from elsewhere
STEP_SETTLE_MS = 750  # after each step, for debounced handlers before the network settles


def root(ready_url: str) -> str:
    """The preview root (scheme and host) under which every state's path is opened."""
    parts = urlsplit(ready_url)
    return f"{parts.scheme}://{parts.netloc}"


def confine(page: Page, origin: str, left: list[str], *, stepped: bool) -> None:
    """Guard one shot's context, so a page a step opens is covered too; whatever is stopped is noted in *left*.

    Main-frame navigation off the preview origin is stopped. A state with steps reaches only static files off it,
    and no WebSocket there, so no click or typing sends anything outside the seeded preview (TD-60).
    """
    from playwright.sync_api import Error  # noqa: PLC0415 - optional browser runtime

    def guard(route: Route) -> None:
        r = route.request
        if root(r.url) == origin:
            route.continue_()
            return
        fetched = r.method in {"GET", "HEAD"} and r.resource_type in STATIC
        try:
            navigating = r.is_navigation_request() and r.frame == page.main_frame
        except Error:  # a page a step opened has no frame yet: it leaves the preview
            navigating = True
        if navigating or (stepped and not fetched):
            left.append(root(r.url))
            route.abort()
        else:
            route.continue_()

    def socket(ws: WebSocketRoute) -> None:
        if urlsplit(ws.url).netloc == urlsplit(origin).netloc:
            ws.connect_to_server()
        else:
            left.append(root(ws.url))
            ws.close()

    page.context.route("**/*", guard)
    if stepped:
        page.context.route_web_socket(lambda _url: True, socket)


def steps(page: Page, s: VisualState, timeout_ms: int) -> str:
    """Run the state's steps in order; why one failed, else empty."""
    for i, step in enumerate(s.steps, 1):
        if why := _act(page, step, timeout_ms):
            return f"state {s.name} step {i} ({step.do} '{step.target}'): {why}"
    return ""


def _act(page: Page, step: VisualStep, timeout_ms: int) -> str:
    """One step on the one control its exact name finds; why it failed, else empty. A repeated name never guesses."""
    from playwright.sync_api import Error  # noqa: PLC0415 - optional browser runtime

    if step.do == "click":
        found = page.get_by_role(CLICKABLE[0], name=step.target, exact=True)
        for role in CLICKABLE[1:]:
            found = found.or_(page.get_by_role(role, name=step.target, exact=True))  # type: ignore[arg-type]
    else:  # only a field takes typing, whether its label or its placeholder names it
        named = page.get_by_label(step.target, exact=True).or_(page.get_by_placeholder(step.target, exact=True))
        found = named.and_(page.locator(EDITABLE))
    try:
        with contextlib.suppress(Error):  # a control a previous step brings in may still be on its way
            found.first.wait_for(state="visible", timeout=timeout_ms)
        if (count := found.count()) != 1:
            return f"{count} controls are named '{step.target}'; name exactly one" if count else "no control named it"
        if step.do == "click":
            found.click(timeout=timeout_ms)
        else:
            found.fill(step.text, timeout=timeout_ms)
        page.wait_for_timeout(STEP_SETTLE_MS)
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Error as exc:
        return str(exc).splitlines()[0][:200]
    return ""


def listen(page: Page, s: VisualState, width: int, seen: list[PageError]) -> None:
    """Record console errors and uncaught page errors until the page closes (R8, TD-51)."""

    def console(m: ConsoleMessage) -> None:
        if m.type in CONSOLE:
            where = m.location or {}
            at = f"{where.get('url', '')}:{where.get('lineNumber', '')}" if where.get("url") else ""
            seen.append(
                PageError(state=s.name, version=s.version, width=width, kind="console", text=m.text, location=at)
            )

    def uncaught(e: Exception) -> None:
        seen.append(PageError(state=s.name, version=s.version, width=width, kind="page", text=str(e)))

    page.on("console", console)
    page.on("pageerror", uncaught)
