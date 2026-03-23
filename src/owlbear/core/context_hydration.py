"""Context pre-hydration module.

Extracts URLs and file paths from task body text, fetches URL content
via *httpx* + *trafilatura*, reads local files, and bundles everything
into a :class:`HydrationResult`.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel

from owlbear.paths import sandbox_path
from owlbear.web_extract import extract_markdown

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "HydrationResult",
    "extract_file_paths",
    "extract_urls",
    "fetch_url",
    "hydrate",
    "read_file_safe",
]

_URL_RE = re.compile(r"https?://[^\s)<>]+")
_MD_LINK_RE = re.compile(r"\[(?:[^\]]*)\]\((https?://[^)]+)\)")
_PATH_TOKEN_RE = re.compile(r"[^\s,;:!?\"'()\[\]{}]+")


class HydrationResult(BaseModel):
    """Immutable result of context hydration."""

    urls: dict[str, str] = {}
    files: dict[str, str] = {}
    errors: list[str] = []

    def __setattr__(self, name: str, value: object) -> None:
        msg = f"'{type(self).__name__}' is frozen"
        raise TypeError(msg)


def extract_urls(text: str) -> list[str]:
    """Extract http/https URLs from *text*, including markdown links."""
    found: list[str] = []
    seen: set[str] = set()

    for match in _MD_LINK_RE.finditer(text):
        url = match.group(1)
        if url not in seen:
            seen.add(url)
            found.append(url)

    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip(".,;:!?'\"")
        if url not in seen:
            seen.add(url)
            found.append(url)

    return found


def extract_file_paths(text: str, workspace_root: Path) -> list[Path]:
    """Extract file paths from *text* that exist within *workspace_root*."""
    results: list[Path] = []
    seen: set[Path] = set()

    for raw_token in _PATH_TOKEN_RE.findall(text):
        if "/" not in raw_token and "\\" not in raw_token:
            continue
        token = raw_token.rstrip(".,;:!?")
        try:
            resolved = sandbox_path(workspace_root, token)
        except PermissionError:
            continue
        if resolved not in seen and resolved.exists() and resolved.is_file():
            seen.add(resolved)
            results.append(resolved)

    return results


async def fetch_url(
    url: str,
    url_checker: Callable[[str], None] | None = None,
) -> str:
    """Fetch *url* and extract content via trafilatura.

    Raises:
        ValueError: If *url_checker* rejects the URL.
    """
    if url_checker is not None:
        url_checker(url)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=30, follow_redirects=True)
            resp.raise_for_status()
    except httpx.TimeoutException:
        return ""
    except httpx.HTTPStatusError:
        return ""
    except httpx.HTTPError:
        return ""

    result = extract_markdown(resp.text, url=url) or ""

    from owlbear.config import OwlBearSettings  # noqa: PLC0415

    if result and OwlBearSettings().wrap_web_content:
        from owlbear.core.content_safety import wrap_untrusted_content  # noqa: PLC0415

        result = wrap_untrusted_content(result, source_url=url)

    return result


def read_file_safe(path: Path, workspace_root: Path) -> str:
    """Read a file, enforcing workspace confinement.

    Raises:
        PermissionError: If *path* resolves outside *workspace_root*.
        FileNotFoundError: If the resolved path does not exist.
    """
    resolved = sandbox_path(workspace_root, path)
    return resolved.read_text(encoding="utf-8")


def _hydrate_files(
    files_found: list[Path],
    workspace_root: Path,
    budget: int,
) -> tuple[dict[str, str], list[str], int]:
    """Read files, respecting *budget*. Returns (contents, errors, remaining)."""
    contents: dict[str, str] = {}
    errors: list[str] = []
    for path in files_found:
        if budget <= 0:
            break
        try:
            text = read_file_safe(path, workspace_root)
            if len(text) > budget:
                text = text[:budget]
            contents[str(path)] = text
            budget -= len(text)
        except (FileNotFoundError, PermissionError) as exc:
            errors.append(f"{path}: {exc}")
    return contents, errors, budget


async def _hydrate_urls(
    urls_found: list[str],
    url_checker: Callable[[str], None] | None,
    budget: int,
) -> tuple[dict[str, str], list[str]]:
    """Fetch URLs, respecting *budget*. Returns (contents, errors)."""
    contents: dict[str, str] = {}
    errors: list[str] = []
    for url in urls_found:
        if budget <= 0:
            break
        try:
            text = await fetch_url(url, url_checker=url_checker)
        except ValueError as exc:
            errors.append(f"{url}: {exc}")
            continue
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url}: {exc}")
            continue
        if text:
            if len(text) > budget:
                text = text[:budget]
            contents[url] = text
            budget -= len(text)
        else:
            errors.append(f"Failed to fetch {url}")
    return contents, errors


async def hydrate(
    body: str,
    workspace_root: Path,
    url_checker: Callable[[str], None] | None = None,
    max_content_bytes: int = 50_000,
) -> HydrationResult:
    """Hydrate context by fetching URLs and reading files from *body*."""
    if not body or max_content_bytes <= 0:
        return HydrationResult()

    urls_found = extract_urls(body)
    files_found = extract_file_paths(body, workspace_root)

    file_contents, file_errors, budget = _hydrate_files(
        files_found,
        workspace_root,
        max_content_bytes,
    )
    url_contents, url_errors = await _hydrate_urls(
        urls_found,
        url_checker,
        budget,
    )

    return HydrationResult(
        urls=url_contents,
        files=file_contents,
        errors=file_errors + url_errors,
    )
