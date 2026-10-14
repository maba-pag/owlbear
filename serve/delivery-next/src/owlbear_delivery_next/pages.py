"""The host's pages, the tab bar and the base stylesheet they share (TD-85): Changes, Backlog, Memory and Settings."""

from __future__ import annotations

from importlib.resources import files

TABS = (
    ("/", "Changes", "changes.html"),
    ("/backlog", "Backlog", "backlog.html"),
    ("/memory", "Memory", "memory.html"),
    ("/config", "Settings", "config.html"),
)
MARK = "<!-- tabs -->"  # where each page takes the tab bar
BASE = "<!-- base -->"  # where each page takes the shared stylesheet, before its own


def nav(current: int) -> str:
    """The tab bar with tab ``current`` marked; plain links, so it works before the design system loads."""
    links = "".join(
        f'<a href="{path}"{' aria-current="page"' if i == current else ""}>{label}</a>'
        for i, (path, label, _) in enumerate(TABS)
    )
    bar = f'<p-tabs-bar active-tab-index="{current}" compact="true">{links}</p-tabs-bar>'
    return f'<nav aria-label="Delivery pages">{bar}</nav>'


def pages() -> dict[str, str]:
    """Each page's path and its HTML with the shared stylesheet and the tab bar in place."""
    web = files("owlbear_delivery_next").joinpath("web")
    base = f"<style>\n{web.joinpath('base.css').read_text(encoding='utf-8')}</style>"
    return {
        path: web.joinpath(name).read_text(encoding="utf-8").replace(BASE, base, 1).replace(MARK, nav(i), 1)
        for i, (path, _, name) in enumerate(TABS)
    }
