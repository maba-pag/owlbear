"""The host's pages, their top row, the base stylesheet and the scripts they share (TD-85, TD-113, TD-264)."""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING

from fastapi import HTTPException, Response

if TYPE_CHECKING:
    from fastapi import FastAPI

PAGES = (  # every page the host serves, as path, title and file; the menu links to each of them
    ("/", "Changes", "changes.html"),
    ("/backlog", "Backlog", "backlog.html"),
    ("/memory", "Memory", "memory.html"),
    ("/decisions", "Decisions", "decisions.html"),
    ("/metrics", "Metrics", "metrics.html"),
    ("/projects", "Projects", "projects.html"),
    ("/config", "Settings", "config.html"),
    ("/maintenance", "Maintenance", "maintenance.html"),
)
WORK = ("/", "/backlog", "/memory", "/decisions", "/metrics")  # the work pages the top row links to, on wide screens
MENU = "/assets/page/menu/menu.mjs"  # the burger and its drilldown (D-01M63C8375KV9WA6NH8K2MB8PN)
MARK = "<!-- tabs -->"  # where each page takes the top row
BASE = "<!-- base -->"  # where each page takes the shared stylesheet, before its own
ASK = "<!-- ask -->"  # where a page with consequential buttons takes the shared confirmation, before its script
PDS = {"index.css": "text/css", "load.mjs": "text/javascript"}  # the vendored Porsche Design System 4.10.1 files
LIT = "vendor/lit-html"  # the vendored lit-html release; its SHA256SUMS names every file it serves (TD-264)
OWN = {"mjs": "text/javascript", "css": "text/css"}  # a page's own modules and styles under web/pages/<page>/ (C-28)


def page_files() -> dict[tuple[str, str], str]:
    """Each page's own module or stylesheet, as (page, file name), with its media type."""
    root = files("owlbear_delivery_next").joinpath("web", "pages")
    return {
        (page.name, f.name): OWN[f.name.rpartition(".")[2]]
        for page in root.iterdir()
        if page.is_dir()
        for f in page.iterdir()
        if f.is_file() and f.name.rpartition(".")[2] in OWN and not f.name.startswith(".")
    }


def lit_files() -> dict[str, str]:
    """Each vendored lit-html file with its recorded SHA-256, from ``SHA256SUMS``."""
    sums = files("owlbear_delivery_next").joinpath("web", LIT, "SHA256SUMS").read_text(encoding="utf-8")
    return {name: digest for digest, name in (line.split("  ", 1) for line in sums.splitlines() if line)}


def lit_version() -> str:
    """The vendored release, as its URLs name it, so a browser never mixes files of two releases."""
    first = files("owlbear_delivery_next").joinpath("web", LIT, "VERSION").read_text(encoding="utf-8")
    return first.splitlines()[0].removeprefix("lit-html ")


def pds_version() -> str:
    """The vendored PDS release, from its loader's header, as its URLs name it, so an update never hits a cache."""
    first = files("owlbear_delivery_next").joinpath("web", "pds", "load.mjs").read_text(encoding="utf-8")
    return first.split(None, 3)[2]


def assets(app: FastAPI) -> None:
    """Serve the design system, lit-html and the pages' scripts: fixed names only, never a path from the URL."""
    web, lit, release, own = files("owlbear_delivery_next").joinpath("web"), lit_files(), lit_version(), page_files()
    pds_release = pds_version()

    @app.get("/assets/pds/{version}/{name}")
    def pds(version: str, name: str) -> Response:
        if version != pds_release or name not in PDS:
            raise HTTPException(404, "no such asset")
        body = web.joinpath("pds", name).read_bytes()
        return Response(body, media_type=PDS[name], headers={"Cache-Control": "max-age=3600"})

    @app.get("/assets/lit-html/{version}/{name:path}")
    def lit_html(version: str, name: str) -> Response:
        if version != release or name not in lit:
            raise HTTPException(404, "no such asset")
        body = web.joinpath(LIT, *name.split("/")).read_bytes()
        return Response(body, media_type="text/javascript", headers={"Cache-Control": "max-age=3600"})

    @app.get("/assets/ui.mjs")
    def ui() -> Response:
        body = web.joinpath("ui.mjs").read_bytes()  # changes with Delivery's code, so always revalidated
        return Response(body, media_type="text/javascript", headers={"Cache-Control": "no-cache"})

    @app.get("/assets/page/{page}/{name}")
    def page_asset(page: str, name: str) -> Response:
        if (page, name) not in own:
            raise HTTPException(404, "no such asset")
        body = web.joinpath("pages", page, name).read_bytes()  # changes with Delivery's code, like ui.mjs
        return Response(body, media_type=own[page, name], headers={"Cache-Control": "no-cache"})


def top(current: str) -> str:
    """The top row with page ``current`` marked: the menu's place, OwlBear, the work pages, and the bar's place."""
    links = "".join(
        f'<a href="{path}"{' aria-current="page"' if path == current else ""}>{label}</a>'
        for path, label, _ in PAGES
        if path in WORK
    )
    row = f'<div id="menu"></div><a class="brand" href="/">OwlBear</a><nav aria-label="Delivery pages">{links}</nav>'
    return f'<div class="top">{row}<div id="controls"></div></div><script type="module" src="{MENU}"></script>'


def pages() -> dict[str, str]:
    """Each page's path and its HTML with the shared stylesheet, the confirmation and the top row in place."""
    web = files("owlbear_delivery_next").joinpath("web")
    base = f"<style>\n{web.joinpath('base.css').read_text(encoding='utf-8')}</style>"
    ask = f"<script>\n{web.joinpath('ask.js').read_text(encoding='utf-8')}</script>"
    return {
        path: web.joinpath(name)
        .read_text(encoding="utf-8")
        .replace(BASE, base, 1)
        .replace(ASK, ask, 1)
        .replace(MARK, top(path), 1)
        for path, _, name in PAGES
    }
