# Adapted from serve/delivery-github/src/owlbear_delivery_github/github.py at ab9cfc6cb.
"""``gh`` transport: run one fixed command and map its exit, HTTP status and JSON to provider errors."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NoReturn
from urllib.parse import quote

from owlbear_delivery_next.github.provider import FailureCode, ProviderError, bounded

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from pathlib import Path

TIMEOUT = 30.0
API_VERSION = "2026-03-10"
# gh prints `gh: <message> (HTTP 409)`, or `gh: HTTP 409` when the body has no top-level message.
_HTTP_STATUS = re.compile(r"^gh: (?:HTTP (\d{3})|.*\(HTTP (\d{3})\))$", re.MULTILINE)

type Runner = Callable[[tuple[str, ...], bytes | None, float, Path | None], subprocess.CompletedProcess[bytes]]
type Json = Any


@dataclass(frozen=True)
class Missing:
    """A read answered with an expected error status; ``message`` is GitHub's evidence."""

    status: int
    message: str


def run(
    argv: tuple[str, ...], data: bytes | None, timeout: float, cwd: Path | None
) -> subprocess.CompletedProcess[bytes]:
    """Run one fixed ``gh`` command without a terminal."""
    return subprocess.run(  # noqa: S603 - fixed gh executable and code-owned argument vectors
        argv, input=data, capture_output=True, timeout=timeout, cwd=cwd, check=False, stdin=None
    )


def status(stderr: bytes) -> int | None:
    """Return the last HTTP status gh reported, if any."""
    found = list(_HTTP_STATUS.finditer(stderr.decode(errors="replace")))
    return int(found[-1].group(1) or found[-1].group(2)) if found else None


def message(stderr: bytes) -> str:
    """Return gh's bounded last error line."""
    text = stderr.decode(errors="replace").strip().splitlines()
    return bounded(text[-1].removeprefix("gh: ") if text else "") or "no message"


def repo(repository: str) -> str:
    """Return the REST path of one ``owner/name`` repository."""
    owner, name = repository.split("/", 1)
    return f"repos/{quote(owner, safe='')}/{quote(name, safe='')}"


def fail(operation: str, stderr: bytes, *, write: bool) -> NoReturn:
    """Raise the provider error that gh's failure output describes."""
    text = stderr.decode(errors="replace").casefold()
    if "rate limit" in text or "http 429" in text:
        code, safe = FailureCode.RATE_LIMITED, True
    elif "gh auth login" in text or "http 401" in text or "bad credentials" in text:
        code, safe = FailureCode.AUTHENTICATION_REQUIRED, False
    elif "http 404" in text or "not found" in text or "could not resolve to" in text:
        code, safe = FailureCode.NOT_FOUND, False
    elif "http 409" in text or "http 422" in text or "already exists" in text:
        code, safe = FailureCode.CONFLICT, False
    elif write:
        code, safe = FailureCode.RESPONSE_UNKNOWN, False
    else:
        code, safe = FailureCode.UNAVAILABLE, True
    raise ProviderError(code, operation, message(stderr), retry_safe=safe)


def invalid(operation: str, detail: str, cause: Exception | None = None) -> NoReturn:
    """Raise a retry-safe invalid-response error."""
    raise ProviderError(FailureCode.INVALID_RESPONSE, operation, detail, retry_safe=True) from cause


class GhClient:
    """Run Delivery's fixed ``gh`` commands; GitHub Enterprise via ``host``."""

    def __init__(self, cwd: Path, *, host: str = "github.com", timeout: float = TIMEOUT, runner: Runner = run) -> None:
        self.cwd, self.host, self.timeout, self.runner = cwd, host, timeout, runner
        self._viewer = ""

    def _gh(  # noqa: PLR0913 - one runner for reads, writes, absent statuses and raw logs
        self,
        operation: str,
        args: tuple[str, ...],
        *,
        body: Json = None,
        write: bool = False,
        absent: Collection[int] = (),
        raw: bool = False,
    ) -> Json:
        data = None if body is None else json.dumps(body, separators=(",", ":")).encode()
        try:
            done = self.runner(("gh", *args), data, self.timeout, self.cwd)
        except FileNotFoundError as exc:
            raise ProviderError(FailureCode.UNAVAILABLE, operation, "gh is not installed", retry_safe=False) from exc
        except subprocess.TimeoutExpired as exc:
            code = FailureCode.RESPONSE_UNKNOWN if write else FailureCode.TIMEOUT
            raise ProviderError(code, operation, "gh timed out", retry_safe=not write) from exc
        if done.returncode != 0:
            if (found := status(done.stderr)) in absent:
                return Missing(found or 0, message(done.stderr))
            fail(operation, done.stderr, write=write)
        if raw:
            return done.stdout.decode(errors="replace")
        try:
            return json.loads(done.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            code = FailureCode.RESPONSE_UNKNOWN if write else FailureCode.INVALID_RESPONSE
            raise ProviderError(code, operation, "gh returned invalid JSON", retry_safe=not write) from exc

    def _api(self, operation: str, method: str, endpoint: str, **kw: Any) -> Json:  # noqa: ANN401 - JSON
        args = ("api", "--method", method, "--hostname", self.host, "-H", "Accept: application/vnd.github+json")
        args += ("-H", f"X-GitHub-Api-Version: {API_VERSION}", endpoint)
        return self._gh(operation, (*args, "--input", "-") if kw.get("body") is not None else args, **kw)

    def _graphql(self, operation: str, query: str, variables: dict[str, Any], *, write: bool = False) -> Json:
        body = {"query": query, "variables": variables}
        return self._gh(operation, ("api", "--hostname", self.host, "graphql", "--input", "-"), body=body, write=write)
