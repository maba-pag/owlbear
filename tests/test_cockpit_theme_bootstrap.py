"""Regression tests for theme-bootstrap.js static serving."""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import patch

import pytest


_KANBAN_CONFIG = """\
next_id: 1
"""


def _make_kanban_dir(base: Path) -> Path:
    """Create a minimal kanban board directory. Returns kanban_dir path."""
    kanban_dir = base / ".owlbear" / "kanban"
    kanban_dir.mkdir(parents=True)
    (kanban_dir / "config.yml").write_text(_KANBAN_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    (kanban_dir / "archive").mkdir()
    return kanban_dir


@pytest.fixture(autouse=True)
def _reset_app_after_run() -> object:
    """Restore app routes and state between tests that call run().

    run() adds static mounts and a catch-all route to the shared FastAPI app.
    Without cleanup, these persist across tests and pollute later assertions.
    """
    import owlbear_cockpit.main as _m  # noqa: PLC0415

    saved_routes = list(_m.app.routes)
    yield
    _m.app.routes[:] = saved_routes
    with contextlib.suppress(AttributeError, KeyError):
        del _m.app.state.workspace


class TestThemeBootstrapServing:
    """GET /theme-bootstrap.js must be served as JavaScript, not HTML."""

    def test_theme_bootstrap_js_response_contract(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """GET /theme-bootstrap.js returns 200, JavaScript content-type, and non-HTML body."""
        from fastapi.testclient import TestClient  # noqa: PLC0415

        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with patch("uvicorn.run"):
            from owlbear_cockpit.main import app, run  # noqa: PLC0415

            run()

        with TestClient(app, raise_server_exceptions=True) as client:
            resp = client.get("/theme-bootstrap.js")

        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "javascript" in content_type, (
            f"Expected JavaScript content-type, got {content_type!r}. "
            "Bug: /theme-bootstrap.js falls through to SPA catch-all → index.html."
        )
        assert "<html" not in resp.text.lower()

    def test_theme_bootstrap_js_content_type_is_not_html(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Content-type for /theme-bootstrap.js must not be text/html."""
        from fastapi.testclient import TestClient  # noqa: PLC0415

        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with patch("uvicorn.run"):
            from owlbear_cockpit.main import app, run  # noqa: PLC0415

            run()

        with TestClient(app, raise_server_exceptions=True) as client:
            resp = client.get("/theme-bootstrap.js")

        content_type = resp.headers.get("content-type", "")
        assert "text/html" not in content_type, (
            f"Got content-type {content_type!r} — /theme-bootstrap.js must not be served as HTML."
        )

    def test_theme_bootstrap_js_body_is_not_html_document(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Response body for /theme-bootstrap.js must not be an HTML document."""
        from fastapi.testclient import TestClient  # noqa: PLC0415

        kanban_dir = _make_kanban_dir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(kanban_dir))
        monkeypatch.setenv("COCKPIT_NO_OPEN", "1")

        with patch("uvicorn.run"):
            from owlbear_cockpit.main import app, run  # noqa: PLC0415

            run()

        with TestClient(app, raise_server_exceptions=True) as client:
            resp = client.get("/theme-bootstrap.js")

        body = resp.text.lower()
        assert "<html" not in body, (
            "Response body must not be an HTML document. Bug: /theme-bootstrap.js falls through to SPA catch-all."
        )
        assert "<!doctype" not in body
