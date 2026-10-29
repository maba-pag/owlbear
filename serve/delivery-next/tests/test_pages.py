import re

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.project_host import api, pages
from owlbear_delivery_next.state_store.store import Store

PAGES = [
    ("/", "Changes"),
    ("/backlog", "Backlog"),
    ("/memory", "Memory"),
    ("/decisions", "Decisions"),
    ("/metrics", "Metrics"),
    ("/projects", "Projects"),
    ("/config", "Settings"),
    ("/maintenance", "Maintenance"),
    ("/updates/owlbear", "OwlBear"),
    ("/updates/pds", "Porsche Design System"),
    ("/updates/impeccable", "Impeccable"),
]
WORK = PAGES[:5]  # the top row's links; every page is in the menu (D-01M63C8375KV9WA6NH8K2MB8PN)
UPDATES = PAGES[8:]  # the menu's Updates level (D-01M63C5VGFWJ709X2GA0CE8Q5B), each page titled as an update
LINKED = r'\["(/[a-z/]*)", "([A-Za-z ]+)"\]'  # a menu link as menu.mjs lists it: path and label


ASKING = {"/", "/backlog", "/memory", "/decisions", "/projects", "/config", "/updates/owlbear", "/updates/impeccable"}


@pytest.mark.parametrize(("path", "title"), PAGES)
def test_every_page_shares_the_top_row_stylesheet_and_confirmation_and_ignores_a_query(
    tmp_path, path, title, page_source
):
    c = TestClient(api.create_app(Store(tmp_path), "t", None), base_url="http://127.0.0.1")

    page = c.get(path)
    source = page_source(c, path)  # with its own modules (C-28)

    assert page.status_code == 200
    row = r'<div id="top"><div id="menu"></div><a class="brand" href="/">OwlBear</a>(.*?)<div id="controls"></div>'
    top = re.search(f'{row}</div><script type="module" src="{pages.MENU}">', page.text)
    assert top, "the top row is missing"
    nav = re.fullmatch(r'<nav aria-label="Delivery pages">(.*)</nav>', top.group(1))
    links = re.findall(r'<a href="([^"]+)"( aria-current="page")?>([^<]+)</a>', nav.group(1))
    assert [(href, label) for href, _, label in links] == WORK
    assert [label for _, current, label in links if current] == ([title] if (path, title) in WORK else [])
    named = f"{title} update" if (path, title) in UPDATES else title
    assert f"<title>OwlBear Delivery · {named}</title>" in page.text

    assert "<!-- base -->" not in page.text
    shared = page.text.index("Shared by every host page")
    assert page.text.index(f'href="/assets/pds/{pages.pds_version()}/index.css"') < shared < page.text.rindex("<style>")

    if path in ASKING or (path, title) in UPDATES:  # an Updates page's top row offers Run updates now, which asks
        assert "<!-- ask -->" not in page.text
        assert "function ask(" in page.text
    if path in ASKING:
        assert "window.confirm" not in source
        assert "function confirmed(" not in source
        assert source.index("function ask(") < source.index("await ask(")

    attacked = c.get(path, params={"html": "<script>alert(1)</script>"})

    assert attacked.status_code == 200
    assert "alert(1)" not in attacked.text
    assert attacked.text == page.text


def test_the_menu_links_every_page_the_host_serves_once(tmp_path):
    """D-01M63C8375KV9WA6NH8K2MB8PN: the burger's drilldown is the way to every page, the work pages in one level."""
    c = TestClient(api.create_app(Store(tmp_path), "t", None), base_url="http://127.0.0.1")
    menu = c.get(pages.MENU).text

    linked = re.findall(LINKED, menu)

    assert sorted(linked) == sorted(PAGES) == sorted((path, title) for path, title, _ in pages.PAGES)
    work = re.search(r'id: "work".*?\] \}', menu, re.DOTALL).group()
    assert re.findall(LINKED, work) == WORK
    updates = re.search(r'id: "updates".*?\] \}', menu, re.DOTALL).group()
    assert re.findall(LINKED, updates) == UPDATES
