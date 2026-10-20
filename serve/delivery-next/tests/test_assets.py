"""The pages' shared scripts: the vendored lit-html release, pinned file by file, and the shared module (TD-264)."""

import hashlib
import re
from importlib.resources import files

from fastapi.testclient import TestClient

from owlbear_delivery_next.project_host import api, pages
from owlbear_delivery_next.state_store.store import Store

LIT = files("owlbear_delivery_next").joinpath("web", "vendor", "lit-html")
# A module's static import or re-export, a bare import, or a dynamic import of a literal, in either quote.
IMPORTS = re.compile(
    r"""^\s*(?:import|export)\s[^"';]*?\bfrom\s*["']([^"']+)["']|^\s*import\s*["']([^"']+)["']"""
    r"""|\bimport\(\s*["']([^"']+)["']\s*\)""",
    re.MULTILINE,
)


def test_the_vendored_lit_html_is_exactly_the_recorded_release():
    recorded = pages.lit_files()
    shipped = sorted(str(p.relative_to(LIT)) for p in LIT.rglob("*.js"))  # type: ignore[attr-defined]

    assert LIT.joinpath("VERSION").read_text(encoding="utf-8").splitlines()[0] == "lit-html 3.3.3"
    assert "BSD 3-Clause License" in LIT.joinpath("LICENSE").read_text(encoding="utf-8")
    assert sorted(recorded) == shipped  # every served file is pinned and every pinned file ships
    for name, digest in recorded.items():
        assert hashlib.sha256(LIT.joinpath(name).read_bytes()).hexdigest() == digest, name


def test_only_pinned_lit_html_files_and_the_shared_module_are_served_without_the_token(tmp_path):
    c = TestClient(api.create_app(Store(tmp_path), "t", None), base_url="http://127.0.0.1")

    for name in pages.lit_files():
        got = c.get(f"/assets/lit-html/3.3.3/{name}")
        assert (got.status_code, got.headers["content-type"].split(";")[0]) == (200, "text/javascript"), name
    refused = ["VERSION", "SHA256SUMS", "LICENSE", "lit-html.js.map", "..%2Fui.mjs", "..%2F..%2Fpages.py", "x.js"]
    assert [c.get(f"/assets/lit-html/3.3.3/{name}").status_code for name in refused] == [404] * len(refused)
    assert c.get("/assets/lit-html/3.3.2/lit-html.js").status_code == 404  # only the vendored release
    ui = c.get("/assets/ui.mjs")
    assert (ui.status_code, ui.headers["cache-control"]) == (200, "no-cache")
    assert "export async function call(" in ui.text


def test_every_page_imports_lit_html_by_the_vendored_release(tmp_path):
    c = TestClient(api.create_app(Store(tmp_path), "t", None), base_url="http://127.0.0.1")

    for path, _, _ in pages.TABS:
        page = c.get(path).text
        used = set(re.findall(r'"/assets/lit-html/([^/"]+)/', page))
        assert used <= {pages.lit_version()}, path


def test_every_module_a_page_loads_is_served_and_nothing_else_under_its_folder(tmp_path):
    """C-28: the pages' own modules, followed from each page through every import, relative ones included."""
    c = TestClient(api.create_app(Store(tmp_path), "t", None), base_url="http://127.0.0.1")
    todo = [m for path, _, _ in pages.TABS for m in re.findall(r'"(/assets/page/[^"]+)"', c.get(path).text)]
    seen: set[str] = set()
    while todo:
        url = todo.pop()
        if url in seen:
            continue
        seen.add(url)
        got = c.get(url)
        assert (got.status_code, got.headers["cache-control"]) == (200, "no-cache"), url
        assert got.headers["content-type"].split(";")[0] == pages.OWN[url.rpartition(".")[2]], url
        for named in ["".join(m) for m in re.findall(IMPORTS, got.text)]:
            assert named.startswith(("./", "/assets/")), (url, named)
            if named.startswith("./"):
                todo.append(f"{url.rpartition('/')[0]}/{named[2:]}")
            elif named.startswith("/assets/page/"):
                todo.append(named)
            else:
                assert c.get(named).status_code == 200, (url, named)
    assert seen == {f"/assets/page/{p}/{n}" for p, n in pages.page_files()}  # every shipped one is used
    for page in ("changes", "config", "backlog"):
        assert f"/assets/page/{page}/main.mjs" in seen
    refused = ["changes/x.mjs", "changes/..%2F..%2Fui.mjs", "..%2Fui.mjs/x", "nope/main.mjs", "changes/main.mjs.map",
               "changes/%2E%2E", "changes/..%2F..%2Fchanges.html", "..%2Fpages/main.mjs"]  # fmt: skip
    assert [c.get(f"/assets/page/{name}").status_code for name in refused] == [404] * len(refused)
