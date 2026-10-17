"""The pages' shared scripts: the vendored lit-html release, pinned file by file, and the shared module (TD-264)."""

import hashlib
from importlib.resources import files

from fastapi.testclient import TestClient

from owlbear_delivery_next.project_host import api, pages
from owlbear_delivery_next.state_store.store import Store

LIT = files("owlbear_delivery_next").joinpath("web", "vendor", "lit-html")


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
        got = c.get(f"/assets/lit-html/{name}")
        assert (got.status_code, got.headers["content-type"].split(";")[0]) == (200, "text/javascript"), name
    refused = ["VERSION", "SHA256SUMS", "LICENSE", "lit-html.js.map", "..%2Fui.mjs", "..%2F..%2Fpages.py", "x.js"]
    assert [c.get(f"/assets/lit-html/{name}").status_code for name in refused] == [404] * len(refused)
    ui = c.get("/assets/ui.mjs")
    assert (ui.status_code, ui.headers["cache-control"]) == (200, "no-cache")
    assert "export async function call(" in ui.text
