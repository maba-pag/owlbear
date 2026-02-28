"""GitHubToolset — FunctionToolset wrapping GitHub REST API operations.

Provides ``create_pr``, ``list_prs``, ``list_issues``, and ``get_issue``
tools via :mod:`httpx`.  Destructive operations (``create_pr``) emit
:attr:`HookEvent.PRE_TOOL_USE` before the API call.

Usage::

    from owlbear.tools.github_api import GitHubToolset

    toolset = GitHubToolset(token="ghp_...", owner="octocat", repo="Hello-World")
    agent = Agent("model", toolsets=[toolset])
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

import httpx
from pydantic_ai.toolsets import FunctionToolset

from owlbear.core.hooks import HookEvent

if TYPE_CHECKING:
    from pydantic import SecretStr

    from owlbear.core.hooks import HookRegistry

__all__ = ["GitHubToolset", "parse_git_remote"]

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.github.com"
_HTTP_ERROR_THRESHOLD = 400

_REMOTE_PATTERNS: list[re.Pattern[str]] = [
    # HTTPS: https://github.com/owner/repo.git
    re.compile(r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/.]+)"),
    # SSH: git@github.com:owner/repo.git
    re.compile(r"git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/.]+)"),
]


def parse_git_remote(url: str) -> tuple[str, str]:
    """Extract ``(owner, repo)`` from a GitHub remote URL.

    Supports HTTPS and SSH formats.

    Args:
        url: Git remote URL string.

    Returns:
        Tuple of ``(owner, repo)``.

    Raises:
        ValueError: If the URL cannot be parsed as a GitHub remote.
    """
    cleaned = url.rstrip("/")
    for pattern in _REMOTE_PATTERNS:
        m = pattern.search(cleaned)
        if m:
            return m.group("owner"), m.group("repo")
    msg = f"Cannot parse GitHub owner/repo from URL: {url!r}"
    raise ValueError(msg)


class GitHubToolset(FunctionToolset):
    """FunctionToolset subclass wrapping 4 GitHub REST API tools.

    Args:
        token: GitHub Personal Access Token (PAT). Must not be empty.
        owner: Repository owner (org or user). If ``None``, must be
            auto-detected from git remote (not yet implemented).
        repo: Repository name. If ``None``, must be auto-detected
            from git remote (not yet implemented).
        hooks: Optional :class:`HookRegistry` for hook emission on
            destructive operations.
    """

    def __init__(
        self,
        token: SecretStr,
        owner: str | None = None,
        repo: str | None = None,
        hooks: HookRegistry | None = None,
    ) -> None:
        raw = token.get_secret_value()
        if not raw or not raw.strip():
            msg = "Token must not be empty"
            raise ValueError(msg)

        super().__init__()
        self._token = token
        self._owner = owner or ""
        self._repo = repo or ""
        self._hooks = hooks
        self._register_tools()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        """Build standard GitHub API headers."""
        return {
            "Authorization": f"Bearer {self._token.get_secret_value()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _emit_hook(self, tool_name: str, args: dict[str, object]) -> None:
        """Emit :attr:`HookEvent.PRE_TOOL_USE` if hooks are configured."""
        if self._hooks is not None:
            await self._hooks.emit(
                HookEvent.PRE_TOOL_USE,
                {"tool_name": tool_name, "args": args},
            )

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register all 4 GitHub API tools on this toolset."""
        self.add_function(
            self.create_pr,
            name="create_pr",
            description="Create a pull request on GitHub.",
        )
        self.add_function(
            self.list_prs,
            name="list_prs",
            description="List pull requests for the repository.",
        )
        self.add_function(
            self.list_issues,
            name="list_issues",
            description="List issues for the repository.",
        )
        self.add_function(
            self.get_issue,
            name="get_issue",
            description="Get a single issue by number.",
        )

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def create_pr(
        self,
        title: str,
        head: str,
        base: str,
        body: str = "",
    ) -> str:
        """Create a pull request.

        Emits :attr:`HookEvent.PRE_TOOL_USE` before the API call.

        Args:
            title: PR title.
            head: Head branch name.
            base: Base branch name.
            body: Optional PR description.
        """
        hook_args: dict[str, object] = {"title": title, "head": head, "base": base, "body": body}
        await self._emit_hook("create_pr", hook_args)

        url = f"{_BASE_URL}/repos/{self._owner}/{self._repo}/pulls"
        payload = {"title": title, "head": head, "base": base, "body": body}

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=self._headers())

        if resp.status_code >= _HTTP_ERROR_THRESHOLD:
            data = resp.json()
            return f"error: {data.get('message', resp.status_code)}"

        data = resp.json()
        return f"Created PR #{data.get('number')}: {data.get('html_url', '')}"

    async def list_prs(
        self,
        state: str = "open",
        per_page: int = 30,
    ) -> str:
        """List pull requests.

        Args:
            state: Filter by state (``open``, ``closed``, ``all``).
            per_page: Number of results per page.
        """
        url = f"{_BASE_URL}/repos/{self._owner}/{self._repo}/pulls"
        params = {"state": state, "per_page": per_page}

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=self._headers())

        if resp.status_code >= _HTTP_ERROR_THRESHOLD:
            data = resp.json()
            return f"error: {data.get('message', resp.status_code)}"

        prs = resp.json()
        if not prs:
            return "No pull requests found."
        lines = [f"#{pr['number']}: {pr['title']}" for pr in prs]
        return "\n".join(lines)

    async def list_issues(
        self,
        state: str = "open",
        per_page: int = 30,
    ) -> str:
        """List issues.

        Args:
            state: Filter by state (``open``, ``closed``, ``all``).
            per_page: Number of results per page.
        """
        url = f"{_BASE_URL}/repos/{self._owner}/{self._repo}/issues"
        params = {"state": state, "per_page": per_page}

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=self._headers())

        if resp.status_code >= _HTTP_ERROR_THRESHOLD:
            data = resp.json()
            return f"error: {data.get('message', resp.status_code)}"

        issues = resp.json()
        if not issues:
            return "No issues found."
        lines = [f"#{issue['number']}: {issue['title']}" for issue in issues]
        return "\n".join(lines)

    async def get_issue(self, number: int) -> str:
        """Get a single issue by number.

        Args:
            number: Issue number.
        """
        url = f"{_BASE_URL}/repos/{self._owner}/{self._repo}/issues/{number}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers())

        if resp.status_code >= _HTTP_ERROR_THRESHOLD:
            data = resp.json()
            return f"error: {data.get('message', resp.status_code)}"

        data = resp.json()
        return json.dumps(data, indent=2)
