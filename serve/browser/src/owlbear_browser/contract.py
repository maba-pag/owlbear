"""Typed, side-effect-free browser acquisition contract and content helpers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

from lxml import html


class AcquisitionStatus(StrEnum):
    SUCCESS = "success"
    AUTHENTICATION_REQUIRED = "authentication_required"
    CONTENT_NOT_READY = "content_not_ready"
    SELECTOR_NOT_FOUND = "selector_not_found"
    ACCESS_DENIED = "access_denied"
    REDIRECT_REJECTED = "redirect_rejected"
    UNSUPPORTED_TARGET = "unsupported_target"
    DOWNLOAD_REJECTED = "download_rejected"
    NAVIGATION_FAILED = "navigation_failed"
    EXTRACTION_FAILED = "extraction_failed"


@dataclass(frozen=True, slots=True)
class AcquisitionRequest:
    """Caller-controlled acquisition inputs, excluding credentials and actions."""

    url: str
    readiness_selector: str | None = None
    content_selector: str | None = None
    navigation_timeout_ms: int = 30_000
    readiness_timeout_ms: int = 10_000
    include_diagnostic_html: bool = False
    password: str | None = field(default=None, repr=False)
    mfa_code: str | None = field(default=None, repr=False)
    javascript: str | None = field(default=None, repr=False)
    actions: tuple[Any, ...] = field(default_factory=tuple, repr=False)
    headers: dict[str, str] | None = field(default=None, repr=False)
    storage_state: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("acquisition requires an HTTP(S) URL")  # noqa: EM101, TRY003
        if (
            any(
                value is not None and value != ""
                for value in (self.password, self.mfa_code, self.javascript, self.storage_state)
            )
            or self.actions
            or self.headers
        ):
            raise ValueError("credentials, scripts, actions, and session inputs are not accepted")  # noqa: EM101, TRY003
        if self.navigation_timeout_ms <= 0 or self.readiness_timeout_ms <= 0:
            raise ValueError("timeouts must be positive")  # noqa: EM101, TRY003


@dataclass(frozen=True, slots=True)
class Diagnostics:
    stage: str
    details: dict[str, Any] = field(default_factory=dict)
    html: str | None = None
    include_diagnostic_html: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", redact_diagnostics(self.details))
        if self.html is not None:
            if not self.include_diagnostic_html:
                object.__setattr__(self, "html", None)
            else:
                object.__setattr__(self, "html", _sanitize_diagnostic_html(self.html))


@dataclass(frozen=True, slots=True)
class AcquisitionSuccess:
    status: AcquisitionStatus
    requested_url: str
    canonical_url: str
    redirect_chain: tuple[str, ...]
    title: str
    markdown: str
    discovered_links: tuple[str, ...]
    content_hash: str
    fetched_at: datetime
    diagnostics: Diagnostics

    def __post_init__(self) -> None:
        if self.status is not AcquisitionStatus.SUCCESS:
            raise ValueError("success results must have success status")  # noqa: EM101, TRY003
        if not self.markdown.strip() or self.fetched_at.tzinfo is not UTC:
            raise ValueError("success results require non-empty Markdown and a UTC timestamp")  # noqa: EM101, TRY003


@dataclass(frozen=True, slots=True)
class AcquisitionFailure:
    status: AcquisitionStatus
    diagnostics: Diagnostics

    def __post_init__(self) -> None:
        if self.status is AcquisitionStatus.SUCCESS:
            raise ValueError("failure results cannot have success status")  # noqa: EM101, TRY003


AcquisitionResult = AcquisitionSuccess | AcquisitionFailure


def normalize_markdown(markdown: str) -> str:
    """Normalize insignificant whitespace for stable content identity."""
    text = markdown.replace("\r", "").replace("\u00a0", " ")
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    lines = [re.sub(r" {2,}", " ", line.rstrip()) for line in text.split("\n")]
    return "\n".join(lines).strip()


def content_hash(markdown: str) -> str:
    return hashlib.sha256(normalize_markdown(markdown).encode("utf-8")).hexdigest()


def normalize_links(links: list[str] | tuple[str, ...], base_url: str) -> tuple[str, ...]:
    """Resolve links, remove fragments and unsupported schemes, preserving order."""
    result: list[str] = []
    seen: set[str] = set()
    for link in links:
        absolute = urljoin(base_url, link)
        parsed = urlparse(urldefrag(absolute).url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            continue
        normalized = parsed.geturl()
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return tuple(result)


_SENSITIVE = re.compile(
    r"cookie|storage|authorization|auth|header|password|credential|secret|token",
    re.IGNORECASE,
)
_DIAGNOSTIC_HTML_LIMIT = 100_000
_REMOVED_HTML_ELEMENTS = {"base", "embed", "iframe", "link", "object", "script", "style"}


def redact_diagnostics(value: Any) -> Any:  # noqa: ANN401
    """Recursively remove sensitive diagnostic fields and values."""
    if isinstance(value, dict):
        return {str(key): redact_diagnostics(item) for key, item in value.items() if not _SENSITIVE.search(str(key))}
    if isinstance(value, (list, tuple)):
        return [redact_diagnostics(item) for item in value]
    if isinstance(value, str) and _SENSITIVE.search(value):
        return "[REDACTED]"
    return value


def _sanitize_diagnostic_html(value: str) -> str:
    """Keep bounded, non-executable markup for explicitly requested diagnostics."""
    root = html.fragment_fromstring(value, create_parent=True)
    for element in root.iter():
        if element.tag in _REMOVED_HTML_ELEMENTS:
            element.drop_tree()
            continue
        for name, attribute in list(element.attrib.items()):
            if (
                name.lower().startswith("on")
                or (name.lower() in {"href", "src", "action"} and attribute.strip().lower().startswith("javascript:"))
                or _SENSITIVE.search(name)
            ):
                del element.attrib[name]
        if element.text and _SENSITIVE.search(element.text):
            element.text = "[REDACTED]"
        if element.tail and _SENSITIVE.search(element.tail):
            element.tail = "[REDACTED]"
    serialized = "".join(html.tostring(child, encoding="unicode", method="html") for child in root)
    return serialized[:_DIAGNOSTIC_HTML_LIMIT]
