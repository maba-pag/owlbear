"""Tests for GitHubToolset — httpx GitHub API tools.

Covers: constructor validation (missing/empty token), auto-detection of
owner/repo from git remote URL (HTTPS + SSH), create_pr (POST with auth
headers, request body, hook emission), list_prs (GET with query params),
list_issues (GET with state filter), get_issue (GET with path param),
and FunctionToolset registration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from pydantic import SecretStr

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.tools.github_api import GitHubToolset, parse_git_remote

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODULE = "owlbear.tools.github_api"
_TOKEN_RAW = "ghp_test1234567890"
TOKEN = SecretStr(_TOKEN_RAW)
OWNER = "test-owner"
REPO = "test-repo"

EXPECTED_TOOL_NAMES = frozenset(
    {
        "create_pr",
        "list_prs",
        "list_issues",
        "get_issue",
    }
)

EXPECTED_HEADERS = {
    "Authorization": f"Bearer {_TOKEN_RAW}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    *,
    json_data: object = None,
    status_code: int = 200,
) -> httpx.Response:
    """Build a real httpx.Response with the given JSON payload."""
    import json

    body = json.dumps(json_data or {}).encode()
    return httpx.Response(
        status_code=status_code,
        content=body,
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://api.github.com/"),
    )


def _make_client(response: httpx.Response) -> AsyncMock:
    """Build a mock httpx.AsyncClient that returns *response* for any method."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


def _toolset(
    *,
    token: SecretStr = TOKEN,
    owner: str | None = OWNER,
    repo: str | None = REPO,
    hooks: HookRegistry | None = None,
) -> GitHubToolset:
    """Shorthand for constructing a GitHubToolset with defaults."""
    return GitHubToolset(token=token, owner=owner, repo=repo, hooks=hooks)


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


class TestConstructorValidation:
    """Missing or empty token raises ValueError at construction time."""

    def test_empty_string_token_raises(self) -> None:
        with pytest.raises(ValueError, match=r"[Tt]oken"):
            GitHubToolset(token=SecretStr(""), owner=OWNER, repo=REPO)

    def test_whitespace_only_token_raises(self) -> None:
        with pytest.raises(ValueError, match=r"[Tt]oken"):
            GitHubToolset(token=SecretStr("   "), owner=OWNER, repo=REPO)

    def test_valid_token_accepted(self) -> None:
        ts = _toolset()
        assert ts._token == TOKEN

    def test_owner_and_repo_stored(self) -> None:
        ts = _toolset()
        assert ts._owner == OWNER
        assert ts._repo == REPO

    def test_hooks_stored_when_provided(self) -> None:
        hooks = HookRegistry()
        ts = _toolset(hooks=hooks)
        assert ts._hooks is hooks

    def test_hooks_default_none(self) -> None:
        ts = _toolset()
        assert ts._hooks is None


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """GitHubToolset registers 4 tools on FunctionToolset."""

    def test_inherits_function_toolset(self) -> None:
        from pydantic_ai.toolsets import FunctionToolset

        ts = _toolset()
        assert isinstance(ts, FunctionToolset)

    def test_all_tools_registered(self) -> None:
        ts = _toolset()
        assert set(ts.tools) == EXPECTED_TOOL_NAMES

    def test_tool_count(self) -> None:
        ts = _toolset()
        assert len(ts.tools) == 4


# ---------------------------------------------------------------------------
# parse_git_remote — owner/repo from remote URL
# ---------------------------------------------------------------------------


class TestParseGitRemote:
    """parse_git_remote extracts owner/repo from HTTPS and SSH URLs."""

    def test_https_url(self) -> None:
        owner, repo = parse_git_remote("https://github.com/octocat/Hello-World.git")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_https_url_without_dot_git(self) -> None:
        owner, repo = parse_git_remote("https://github.com/octocat/Hello-World")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_ssh_url(self) -> None:
        owner, repo = parse_git_remote("git@github.com:octocat/Hello-World.git")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_ssh_url_without_dot_git(self) -> None:
        owner, repo = parse_git_remote("git@github.com:octocat/Hello-World")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_https_with_trailing_slash(self) -> None:
        owner, repo = parse_git_remote("https://github.com/owner/repo/")
        assert owner == "owner"
        assert repo == "repo"

    def test_invalid_url_raises(self) -> None:
        with pytest.raises(ValueError, match=r"[Cc]annot parse"):
            parse_git_remote("not-a-valid-url")

    def test_non_github_url_raises(self) -> None:
        with pytest.raises(ValueError, match=r"[Cc]annot parse"):
            parse_git_remote("https://gitlab.com/owner/repo.git")


# ---------------------------------------------------------------------------
# create_pr — POST /repos/{owner}/{repo}/pulls
# ---------------------------------------------------------------------------


class TestCreatePr:
    """create_pr sends POST with correct URL, headers, and body."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sends_post_to_correct_url(self) -> None:
        resp = _make_response(
            json_data={"number": 42, "html_url": "https://github.com/test-owner/test-repo/pull/42"}
        )
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.create_pr(title="Fix bug", head="fix-branch", base="main")

        client.post.assert_called_once()
        call_args = client.post.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        assert f"/repos/{OWNER}/{REPO}/pulls" in url

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sends_correct_request_body(self) -> None:
        resp = _make_response(json_data={"number": 1, "html_url": "https://github.com/o/r/pull/1"})
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.create_pr(
                title="Add feature",
                head="feature-branch",
                base="main",
                body="Description here",
            )

        call_kwargs = client.post.call_args[1]
        json_body = call_kwargs.get("json", {})
        assert json_body["title"] == "Add feature"
        assert json_body["head"] == "feature-branch"
        assert json_body["base"] == "main"
        assert json_body["body"] == "Description here"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sends_auth_header(self) -> None:
        resp = _make_response(json_data={"number": 1, "html_url": "url"})
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.create_pr(title="T", head="h", base="b")

        call_kwargs = client.post.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert headers["Authorization"] == f"Bearer {_TOKEN_RAW}"
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_pr_info_string(self) -> None:
        resp = _make_response(
            json_data={
                "number": 42,
                "html_url": "https://github.com/o/r/pull/42",
            }
        )
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            result = await ts.create_pr(title="T", head="h", base="b")

        assert "42" in result
        assert isinstance(result, str)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_api_error_returns_error_string(self) -> None:
        resp = _make_response(
            json_data={"message": "Validation Failed"},
            status_code=422,
        )
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            result = await ts.create_pr(title="T", head="h", base="b")

        assert "error" in result.lower()


# ---------------------------------------------------------------------------
# create_pr — hook emission
# ---------------------------------------------------------------------------


class TestCreatePrHookEmission:
    """create_pr emits HookEvent.PRE_TOOL_USE before the API call."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_pre_tool_use_emitted(self) -> None:
        hooks = HookRegistry()
        captured: list[object] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        resp = _make_response(json_data={"number": 1, "html_url": "url"})
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset(hooks=hooks)
            await ts.create_pr(title="Hook test", head="h", base="b")

        assert len(captured) == 1
        payload = captured[0]
        assert payload["tool_name"] == "create_pr"  # type: ignore[index]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_hook_emitted_before_api_call(self) -> None:
        """PRE_TOOL_USE must fire BEFORE the httpx POST."""
        call_order: list[str] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.PRE_TOOL_USE, lambda _: call_order.append("hook"))

        resp = _make_response(json_data={"number": 1, "html_url": "url"})

        async def tracking_post(*_args: object, **_kwargs: object) -> httpx.Response:
            call_order.append("api_call")
            return resp

        client = _make_client(resp)
        client.post = AsyncMock(side_effect=tracking_post)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset(hooks=hooks)
            await ts.create_pr(title="Order test", head="h", base="b")

        assert call_order == ["hook", "api_call"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_no_hooks_no_error(self) -> None:
        """When hooks is None, no emission happens (no error)."""
        resp = _make_response(json_data={"number": 1, "html_url": "url"})
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset(hooks=None)
            result = await ts.create_pr(title="No hooks", head="h", base="b")

        assert isinstance(result, str)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_hook_payload_contains_pr_details(self) -> None:
        hooks = HookRegistry()
        captured: list[object] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        resp = _make_response(json_data={"number": 1, "html_url": "url"})
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset(hooks=hooks)
            await ts.create_pr(title="My PR", head="feature", base="main")

        payload = captured[0]
        assert payload["args"]["title"] == "My PR"  # type: ignore[index]
        assert payload["args"]["head"] == "feature"  # type: ignore[index]
        assert payload["args"]["base"] == "main"  # type: ignore[index]


# ---------------------------------------------------------------------------
# list_prs — GET /repos/{owner}/{repo}/pulls
# ---------------------------------------------------------------------------


class TestListPrs:
    """list_prs sends GET with correct URL and query params."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sends_get_to_correct_url(self) -> None:
        resp = _make_response(json_data=[{"number": 1, "title": "PR 1"}])
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.list_prs()

        client.get.assert_called_once()
        call_args = client.get.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        assert f"/repos/{OWNER}/{REPO}/pulls" in url

    @pytest.mark.asyncio(loop_scope="function")
    async def test_default_state_open(self) -> None:
        resp = _make_response(json_data=[])
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.list_prs()

        call_kwargs = client.get.call_args[1]
        params = call_kwargs.get("params", {})
        assert params["state"] == "open"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_custom_state_and_per_page(self) -> None:
        resp = _make_response(json_data=[])
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.list_prs(state="closed", per_page=50)

        call_kwargs = client.get.call_args[1]
        params = call_kwargs.get("params", {})
        assert params["state"] == "closed"
        assert params["per_page"] == 50

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sends_auth_headers(self) -> None:
        resp = _make_response(json_data=[])
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.list_prs()

        call_kwargs = client.get.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert headers["Authorization"] == f"Bearer {_TOKEN_RAW}"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_string(self) -> None:
        resp = _make_response(json_data=[{"number": 1, "title": "PR"}])
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            result = await ts.list_prs()

        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# list_issues — GET /repos/{owner}/{repo}/issues
# ---------------------------------------------------------------------------


class TestListIssues:
    """list_issues sends GET with correct URL and state filter."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sends_get_to_issues_url(self) -> None:
        resp = _make_response(json_data=[{"number": 10, "title": "Bug"}])
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.list_issues()

        client.get.assert_called_once()
        call_args = client.get.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        assert f"/repos/{OWNER}/{REPO}/issues" in url

    @pytest.mark.asyncio(loop_scope="function")
    async def test_default_state_open(self) -> None:
        resp = _make_response(json_data=[])
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.list_issues()

        call_kwargs = client.get.call_args[1]
        params = call_kwargs.get("params", {})
        assert params["state"] == "open"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_custom_state_filter(self) -> None:
        resp = _make_response(json_data=[])
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.list_issues(state="closed")

        call_kwargs = client.get.call_args[1]
        params = call_kwargs.get("params", {})
        assert params["state"] == "closed"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sends_auth_headers(self) -> None:
        resp = _make_response(json_data=[])
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.list_issues()

        call_kwargs = client.get.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert headers["Authorization"] == f"Bearer {_TOKEN_RAW}"
        assert headers["Accept"] == "application/vnd.github+json"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_string(self) -> None:
        resp = _make_response(json_data=[{"number": 1, "title": "Issue"}])
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            result = await ts.list_issues()

        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# get_issue — GET /repos/{owner}/{repo}/issues/{number}
# ---------------------------------------------------------------------------


class TestGetIssue:
    """get_issue sends GET with correct path param interpolation."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sends_get_to_issue_url_with_number(self) -> None:
        resp = _make_response(
            json_data={
                "number": 42,
                "title": "Bug report",
                "state": "open",
                "body": "Describe the bug",
            }
        )
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.get_issue(number=42)

        client.get.assert_called_once()
        call_args = client.get.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        assert f"/repos/{OWNER}/{REPO}/issues/42" in url

    @pytest.mark.asyncio(loop_scope="function")
    async def test_path_param_with_different_number(self) -> None:
        resp = _make_response(json_data={"number": 99, "title": "Feature"})
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.get_issue(number=99)

        url = client.get.call_args[0][0]
        assert "/issues/99" in url

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sends_auth_headers(self) -> None:
        resp = _make_response(json_data={"number": 1, "title": "T"})
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            await ts.get_issue(number=1)

        call_kwargs = client.get.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert headers["Authorization"] == f"Bearer {_TOKEN_RAW}"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_string(self) -> None:
        resp = _make_response(json_data={"number": 1, "title": "Issue"})
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            result = await ts.get_issue(number=1)

        assert isinstance(result, str)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_api_error_returns_error_string(self) -> None:
        resp = _make_response(
            json_data={"message": "Not Found"},
            status_code=404,
        )
        client = _make_client(resp)

        with patch(f"{MODULE}.httpx.AsyncClient", return_value=client):
            ts = _toolset()
            result = await ts.get_issue(number=9999)

        assert "error" in result.lower()
