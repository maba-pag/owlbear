"""The host's pages and the tab bar they share (TD-85): Changes, Backlog, Memory and Settings, the current marked."""

from __future__ import annotations

from importlib.resources import files

TABS = (
    ("/", "Changes", "changes.html"),
    ("/backlog", "Backlog", "backlog.html"),
    ("/memory", "Memory", "memory.html"),
    ("/config", "Settings", "config.html"),
)
MARK = "<!-- tabs -->"  # where each page takes the tab bar


def nav(current: int) -> str:
    """The tab bar with tab ``current`` marked; plain links, so it works before the design system loads."""
    links = "".join(
        f'<a href="{path}"{' aria-current="page"' if i == current else ""}>{label}</a>'
        for i, (path, label, _) in enumerate(TABS)
    )
    return f'<nav aria-label="Delivery pages"><p-tabs-bar active-tab-index="{current}">{links}</p-tabs-bar></nav>'


def pages() -> dict[str, str]:
    """Each page's path and its HTML with the tab bar in place."""
    web = files("owlbear_delivery_next").joinpath("web")
    return {
        path: web.joinpath(name).read_text(encoding="utf-8").replace(MARK, nav(i), 1)
        for i, (path, _, name) in enumerate(TABS)
    }
