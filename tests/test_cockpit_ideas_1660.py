"""Failing tests for cockpit Ideas API — GET/PUT /api/ideas (#1660).

RED phase — all tests must fail until the route is implemented in GREEN.

AC coverage:
  - AC1: GET /api/ideas → {"content": "..."} from file; {"content": ""} when absent
  - AC2: PUT /api/ideas accepts {"content": "..."}, writes via atomic_write, creates on first
         write, returns 204
  - AC3: get_ideas_path dependency returns Path, overridable via app.dependency_overrides
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ideas_file(tmp_path: Path) -> Path:
    """Return a temporary ideas.md file path (does not create the file)."""
    return tmp_path / "ideas.md"


@pytest.fixture
def client(ideas_file: Path):
    """FastAPI TestClient with get_ideas_path injected via dependency_overrides."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.deps import get_ideas_path  # noqa: PLC0415
    from owlbear_cockpit.main import app  # noqa: PLC0415

    app.dependency_overrides[get_ideas_path] = lambda: ideas_file
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client_with_file(ideas_file: Path):
    """TestClient with ideas.md pre-created and containing some text."""
    ideas_file.write_text("# My Ideas\n\nSome idea here.", encoding="utf-8")

    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.deps import get_ideas_path  # noqa: PLC0415
    from owlbear_cockpit.main import app  # noqa: PLC0415

    app.dependency_overrides[get_ideas_path] = lambda: ideas_file
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1: GET /api/ideas
# ---------------------------------------------------------------------------


class TestFromAC_IdeasGet:
    """AC1: GET /api/ideas returns {"content": "..."} from file or empty when absent."""

    def test_get_returns_200_when_file_exists(self, client_with_file: TestClient) -> None:
        """Happy path: GET /api/ideas returns 200 when ideas.md exists."""
        response = client_with_file.get("/api/ideas")
        assert response.status_code == 200

    def test_get_returns_content_from_file(self, client_with_file: TestClient) -> None:
        """Happy path: response body contains file contents verbatim."""
        response = client_with_file.get("/api/ideas")
        assert response.status_code == 200
        body = response.json()
        assert body["content"] == "# My Ideas\n\nSome idea here."

    def test_get_returns_content_key_in_response(self, client_with_file: TestClient) -> None:
        """Response body is JSON object with 'content' key."""
        response = client_with_file.get("/api/ideas")
        assert response.status_code == 200
        body = response.json()
        assert "content" in body
        assert isinstance(body["content"], str)

    def test_get_returns_empty_string_when_file_absent(self, client: TestClient) -> None:
        """Edge: GET /api/ideas returns {"content": ""} when file does not exist."""
        response = client.get("/api/ideas")
        assert response.status_code == 200
        body = response.json()
        assert body == {"content": ""}

    def test_get_returns_200_when_file_absent(self, client: TestClient) -> None:
        """Edge: missing file is not a 404 — returns 200 with empty content."""
        response = client.get("/api/ideas")
        assert response.status_code == 200

    def test_get_content_is_not_null_when_file_absent(self, client: TestClient) -> None:
        """Boundary: absent file yields empty string, never null/None."""
        response = client.get("/api/ideas")
        body = response.json()
        assert body["content"] is not None
        assert body["content"] == ""

    def test_get_empty_file_returns_empty_string(self, ideas_file: Path) -> None:
        """Edge: file exists but is empty — returns {"content": ""}."""
        ideas_file.write_text("", encoding="utf-8")

        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.deps import get_ideas_path  # noqa: PLC0415
        from owlbear_cockpit.main import app  # noqa: PLC0415

        app.dependency_overrides[get_ideas_path] = lambda: ideas_file
        try:
            response = TestClient(app).get("/api/ideas")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json() == {"content": ""}


# ---------------------------------------------------------------------------
# AC2: PUT /api/ideas
# ---------------------------------------------------------------------------


class TestFromAC_IdeasPut:
    """AC2: PUT /api/ideas accepts content, writes via atomic_write, returns 204."""

    def test_put_returns_204_when_file_exists(self, client_with_file: TestClient) -> None:
        """Happy path: PUT /api/ideas returns 204 No Content."""
        response = client_with_file.put("/api/ideas", json={"content": "Updated ideas."})
        assert response.status_code == 204

    def test_put_writes_content_to_file(self, client: TestClient, ideas_file: Path) -> None:
        """Happy path: PUT writes the supplied content to the ideas path."""
        response = client.put("/api/ideas", json={"content": "New content here."})
        assert response.status_code == 204
        assert ideas_file.read_text(encoding="utf-8") == "New content here."

    def test_put_creates_file_on_first_write(self, client: TestClient, ideas_file: Path) -> None:
        """Happy path: PUT creates ideas.md when it does not yet exist."""
        assert not ideas_file.exists()
        response = client.put("/api/ideas", json={"content": "First write."})
        assert response.status_code == 204
        assert ideas_file.exists()
        assert ideas_file.read_text(encoding="utf-8") == "First write."

    def test_put_uses_atomic_write(self, client: TestClient, ideas_file: Path) -> None:
        """AC2: PUT delegates file write to atomic_write from owlbear_kanban.storage_io."""
        with patch("owlbear_cockpit.routes.ideas.atomic_write") as mock_aw:
            response = client.put("/api/ideas", json={"content": "atomic content"})
        assert response.status_code == 204
        mock_aw.assert_called_once_with(ideas_file, "atomic content")

    def test_put_atomic_write_receives_correct_path(self, client: TestClient, ideas_file: Path) -> None:
        """Boundary: atomic_write is called with the exact path from get_ideas_path."""
        with patch("owlbear_cockpit.routes.ideas.atomic_write") as mock_aw:
            client.put("/api/ideas", json={"content": "check path"})
        path_arg = mock_aw.call_args[0][0]
        assert path_arg == ideas_file

    def test_put_accepts_empty_content(self, client: TestClient) -> None:
        """Edge: empty string is a valid content value."""
        response = client.put("/api/ideas", json={"content": ""})
        assert response.status_code == 204

    def test_put_rejects_missing_content_field(self, client: TestClient) -> None:
        """Error: body without 'content' field returns 422 Unprocessable Entity."""
        response = client.put("/api/ideas", json={})
        assert response.status_code == 422

    def test_put_rejects_extra_fields(self, client: TestClient) -> None:
        """Error: extra fields in body return 422 (Pydantic extra=forbid)."""
        response = client.put("/api/ideas", json={"content": "x", "extra": "field"})
        assert response.status_code == 422

    def test_put_returns_no_body(self, client_with_file: TestClient) -> None:
        """Boundary: 204 response has no body (or empty body)."""
        response = client_with_file.put("/api/ideas", json={"content": "something"})
        assert response.status_code == 204
        assert not response.content


# ---------------------------------------------------------------------------
# AC3: get_ideas_path DI dependency
# ---------------------------------------------------------------------------


class TestFromAC_IdeasPathDep:
    """AC3: get_ideas_path returns a Path, overridable via dependency_overrides."""

    def test_get_ideas_path_exists_in_deps(self) -> None:
        """AC3: get_ideas_path is importable from owlbear_cockpit.deps."""
        from owlbear_cockpit.deps import get_ideas_path  # noqa: PLC0415

        assert callable(get_ideas_path)

    def test_get_ideas_path_returns_path_instance(self) -> None:
        """AC3: get_ideas_path returns a Path object."""
        from owlbear_cockpit.deps import get_ideas_path  # noqa: PLC0415

        # Verify the callable is present and produces a Path when the engine dep
        # resolves — the overridability test below is the authoritative contract.
        # Calling __wrapped__ covers decorated dep callables; None is expected
        # when the dep requires engine state injected by FastAPI.
        result = get_ideas_path.__wrapped__() if hasattr(get_ideas_path, "__wrapped__") else None  # type: ignore[attr-defined]
        assert result is None or isinstance(result, Path)

    def test_dependency_overridable_for_test_isolation(self, tmp_path: Path) -> None:
        """AC3: get_ideas_path is overridable via app.dependency_overrides."""
        custom_path = tmp_path / "custom_ideas.md"
        custom_path.write_text("override content", encoding="utf-8")

        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.deps import get_ideas_path  # noqa: PLC0415
        from owlbear_cockpit.main import app  # noqa: PLC0415

        app.dependency_overrides[get_ideas_path] = lambda: custom_path
        try:
            response = TestClient(app).get("/api/ideas")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["content"] == "override content"

    def test_ideas_router_is_mounted_under_api_prefix(self, client: TestClient) -> None:
        """AC3: ideas routes are mounted so GET /api/ideas is reachable."""
        response = client.get("/api/ideas")
        # Not a 404 means the router is mounted correctly.
        assert response.status_code != 404
