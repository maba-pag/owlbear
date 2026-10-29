import re

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.project_host import api, pages
from owlbear_delivery_next.state_store.store import Store

TABS = [
    ("/", "Changes"),
    ("/backlog", "Backlog"),
    ("/memory", "Memory"),
    ("/decisions", "Decisions"),
    ("/metrics", "Metrics"),
    ("/config", "Settings"),
    ("/maintenance", "Maintenance"),
]


ASKING = {"/", "/backlog", "/memory", "/decisions", "/config"}  # pages with consequential buttons


@pytest.mark.parametrize(("path", "title"), TABS)
def test_every_page_shares_the_tab_bar_stylesheet_and_confirmation_and_ignores_a_query(
    tmp_path, path, title, page_source
):
    c = TestClient(api.create_app(Store(tmp_path), "t", None), base_url="http://127.0.0.1")

    page = c.get(path)
    source = page_source(c, path)  # with its own modules (C-28)

    assert page.status_code == 200
    nav = re.search(r'<nav aria-label="Delivery pages">.*?</nav>', page.text, re.DOTALL)
    assert nav, "the tab bar is missing"
    links = re.findall(r'<a href="([^"]+)"( aria-current="page")?>([^<]+)</a>', nav.group())
    assert [(href, label) for href, _, label in links] == TABS
    assert [label for _, current, label in links if current] == [title]
    assert f'active-tab-index="{TABS.index((path, title))}"' in nav.group()
    assert f"<title>OwlBear Delivery · {title}</title>" in page.text

    assert "<!-- base -->" not in page.text
    shared = page.text.index("Shared by every host page")
    assert page.text.index(f'href="/assets/pds/{pages.pds_version()}/index.css"') < shared < page.text.rindex("<style>")

    if path in ASKING:
        assert "<!-- ask -->" not in page.text
        assert "window.confirm" not in source
        assert "function confirmed(" not in source
        assert source.index("function ask(") < source.index("await ask(")

    attacked = c.get(path, params={"html": "<script>alert(1)</script>"})

    assert attacked.status_code == 200
    assert "alert(1)" not in attacked.text
    assert attacked.text == page.text
