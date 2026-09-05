"""Source fetcher adapter implementing the SourceFetcher protocol."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from owlbear_knowledge import intake
from owlbear_knowledge._paths import sandbox_path
from owlbear_knowledge.fetcher import HttpxContentFetcher, failure_for_fetch_exception
from owlbear_knowledge.protocols.failures import KnowledgeFailure, KnowledgeFailureStage
from owlbear_knowledge.protocols.fetcher import FetchedDocument, FetchError, FetchResult, SourceFetcher
from owlbear_knowledge.protocols.sources import (
    AuthenticatedWebConfig,
    ConfiguredSourceRecord,
    FileGlobConfig,
    SourceKind,
    UrlListConfig,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_knowledge.cancellation import CancelSignal
    from owlbear_knowledge.fetcher import ContentFetcher, HttpResponseFetcher
    from owlbear_knowledge.protocols.sources import FetchTransport


class CompositeSourceFetcher(SourceFetcher):
    """Composite fetcher delegating source retrieval by source kind."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        content_fetcher_factory: Callable[[FetchTransport], ContentFetcher],
        http_response_fetcher_factory: Callable[[], HttpResponseFetcher] = HttpxContentFetcher,
    ) -> None:
        self._workspace_root = workspace_root
        self._content_fetcher_factory = content_fetcher_factory
        self._http_response_fetcher_factory = http_response_fetcher_factory

    async def fetch_source(
        self,
        source: ConfiguredSourceRecord,
        *,
        cancel: CancelSignal | None = None,
    ) -> FetchResult:
        """Fetch one source while capturing item-level failures as FetchError."""
        try:
            if source.kind is SourceKind.URL_LIST and isinstance(source.config, UrlListConfig):
                return await self._fetch_url_list(source.config, cancel=cancel)
            if source.kind is SourceKind.FILE_GLOB and isinstance(source.config, FileGlobConfig):
                return await self._fetch_file_glob(source.config, cancel=cancel)
            if source.kind is SourceKind.AUTHENTICATED_WEB and isinstance(
                source.config,
                AuthenticatedWebConfig,
            ):
                return await self._fetch_authenticated_web(source, source.config)
            if source.kind is SourceKind.INLINE:
                return FetchResult()

            failure = KnowledgeFailure(
                stage=KnowledgeFailureStage.ACQUISITION,
                code="transport_failure",
                retryable=False,
                message="Source configuration is invalid",
            )
            return FetchResult(errors=(self._fetch_error(source.id, failure),))
        except Exception as exc:  # noqa: BLE001 - protocol guarantees no raise.
            return FetchResult(errors=(self._fetch_error(source.id, failure_for_fetch_exception(exc)),))

    async def _fetch_url_list(
        self,
        config: UrlListConfig,
        *,
        cancel: CancelSignal | None,
    ) -> FetchResult:
        documents: list[FetchedDocument] = []
        errors: list[FetchError] = []
        response_fetcher = self._http_response_fetcher_factory()

        for url in config.urls:
            if self._cancelled(cancel):
                break
            try:
                intake_result = await intake.read_url(url, fetcher=response_fetcher)
            except Exception as exc:  # noqa: BLE001 - captured into FetchResult.errors.
                errors.append(self._fetch_error(url, failure_for_fetch_exception(exc)))
                continue
            documents.append(
                FetchedDocument(
                    title=url,
                    text=intake_result.content,
                    uri=url,
                    metadata=intake_result.metadata,
                )
            )

        return FetchResult(documents=tuple(documents), errors=tuple(errors))

    async def _fetch_file_glob(
        self,
        config: FileGlobConfig,
        *,
        cancel: CancelSignal | None,
    ) -> FetchResult:
        documents: list[FetchedDocument] = []
        errors: list[FetchError] = []
        base_path = sandbox_path(self._workspace_root, config.base_path)

        seen_paths: set[Path] = set()
        paths: list[Path] = []
        for pattern in config.patterns:
            try:
                for path in base_path.glob(pattern):
                    if not config.follow_symlinks and path.is_symlink():
                        continue
                    if not path.is_file():
                        continue
                    resolved_path = path.resolve()
                    if resolved_path in seen_paths:
                        continue
                    seen_paths.add(resolved_path)
                    paths.append(path)
            except Exception as exc:  # noqa: BLE001 - per-pattern failure captured.
                errors.append(self._fetch_error(pattern, failure_for_fetch_exception(exc)))

        for path in paths:
            if self._cancelled(cancel):
                break
            try:
                intake_result = await intake.read_file(path, workspace_root=self._workspace_root)
            except Exception as exc:  # noqa: BLE001 - per-item failure captured.
                errors.append(self._fetch_error(str(path), failure_for_fetch_exception(exc)))
                continue
            documents.append(
                FetchedDocument(
                    title=Path(intake_result.source).name,
                    text=intake_result.content,
                    uri=intake_result.source,
                    metadata=intake_result.metadata,
                )
            )

        return FetchResult(documents=tuple(documents), errors=tuple(errors))

    async def _fetch_authenticated_web(
        self,
        source: ConfiguredSourceRecord,
        config: AuthenticatedWebConfig,
    ) -> FetchResult:
        base_url = config.base_url
        try:
            fetcher = self._content_fetcher_factory(source.fetch_method)
            content = await fetcher.fetch(base_url)
        except Exception as exc:  # noqa: BLE001 - captured into FetchResult.errors.
            return FetchResult(errors=(self._fetch_error(base_url, failure_for_fetch_exception(exc)),))

        document = FetchedDocument(title=base_url, text=content, uri=base_url)
        return FetchResult(documents=(document,))

    @staticmethod
    def _cancelled(cancel: CancelSignal | None) -> bool:
        return cancel is not None and cancel.is_set()

    @staticmethod
    def _fetch_error(uri: str, failure: KnowledgeFailure) -> FetchError:
        return FetchError(uri=_safe_uri(uri), error=failure.message, failure=failure)


def _safe_uri(uri: str) -> str:
    """Remove credentials and query material from an emitted source URI."""
    try:
        parsed = urlsplit(uri)
        if not parsed.scheme:
            return uri
        hostname = parsed.hostname
        if hostname is None:
            return parsed.scheme
        host = f"[{hostname}]" if ":" in hostname else hostname
        port = f":{parsed.port}" if parsed.port is not None else ""
        return urlunsplit((parsed.scheme, f"{host}{port}", parsed.path, "", ""))
    except ValueError:
        return "<redacted>"
