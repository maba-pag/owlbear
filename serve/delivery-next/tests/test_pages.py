import re

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api
from owlbear_delivery_next.store import Store

TABS = [
    ("/", "Changes"),
    ("/backlog", "Backlog"),
    ("/memory", "Memory"),
    ("/config", "Settings"),
    ("/maintenance", "Maintenance"),
]


@pytest.mark.parametrize(("path", "title"), TABS)
def test_every_page_carries_the_same_tab_bar_with_its_own_tab_marked(tmp_path, path, title):
    c = TestClient(api.create_app(Store(tmp_path), "t", None), base_url="http://127.0.0.1")

    page = c.get(path)

    assert page.status_code == 200
    nav = re.search(r'<nav aria-label="Delivery pages">.*?</nav>', page.text, re.DOTALL)
    assert nav, "the tab bar is missing"
    links = re.findall(r'<a href="([^"]+)"( aria-current="page")?>([^<]+)</a>', nav.group())
    assert [(href, label) for href, _, label in links] == TABS
    assert [label for _, current, label in links if current] == [title]
    assert f'active-tab-index="{TABS.index((path, title))}"' in nav.group()
    assert f"<title>OwlBear Delivery · {title}</title>" in page.text


@pytest.mark.parametrize("path", [path for path, _ in TABS])
def test_every_page_takes_the_shared_stylesheet_before_its_own(tmp_path, path):
    c = TestClient(api.create_app(Store(tmp_path), "t", None), base_url="http://127.0.0.1")

    page = c.get(path).text

    assert "<!-- base -->" not in page
    shared = page.index("Shared by every host page")
    assert page.index('href="/assets/pds/index.css"') < shared < page.rindex("<style>")


@pytest.mark.parametrize("path", [path for path, _ in TABS])
def test_a_query_cannot_replace_a_pages_html(tmp_path, path):
    c = TestClient(api.create_app(Store(tmp_path), "t", None), base_url="http://127.0.0.1")

    attacked = c.get(path, params={"html": "<script>alert(1)</script>"})

    assert attacked.status_code == 200
    assert "alert(1)" not in attacked.text
    assert attacked.text == c.get(path).text


@pytest.mark.parametrize("path", ["/", "/backlog", "/memory", "/config"])
def test_a_page_with_consequential_buttons_takes_the_shared_confirmation_before_its_script(tmp_path, path):
    c = TestClient(api.create_app(Store(tmp_path), "t", None), base_url="http://127.0.0.1")

    page = c.get(path).text

    assert "<!-- ask -->" not in page
    assert "window.confirm" not in page
    assert "function confirmed(" not in page
    assert page.index("function ask(") < page.index("await ask(")
