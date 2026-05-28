"""Source fetcher adapter implementing the SourceFetcher protocol."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_knowledge import intake
from owlbear_knowledge._paths import sandbox_path
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
    from owlbear_knowledge.fetcher import ContentFetcher
    from owlbear_knowledge.protocols.sources import FetchTransport


class CompositeSourceFetcher(SourceFetcher):
    """Composite fetcher delegating source retrieval by source kind."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        content_fetcher_factory: Callable[[FetchTransport], ContentFetcher],
    ) -> None:
        self._workspace_root = workspace_root
        self._content_fetcher_factory = content_fetcher_factory

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

            mismatch = f"source config mismatch for kind {source.kind}"
            return FetchResult(errors=(FetchError(uri=source.id, error=mismatch),))
        except Exception as exc:  # noqa: BLE001 - protocol guarantees no raise.
            return FetchResult(errors=(FetchError(uri=source.id, error=str(exc)),))

    async def _fetch_url_list(
        self,
        config: UrlListConfig,
        *,
        cancel: CancelSignal | None,
    ) -> FetchResult:
        documents: list[FetchedDocument] = []
        errors: list[FetchError] = []

        for url in config.urls:
            if self._cancelled(cancel):
                break
            try:
                intake_result = await intake.read_url(url)
            except Exception as exc:  # noqa: BLE001 - captured into FetchResult.errors.
                errors.append(FetchError(uri=url, error=str(exc)))
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
                errors.append(FetchError(uri=pattern, error=str(exc)))

        for path in paths:
            if self._cancelled(cancel):
                break
            try:
                intake_result = await intake.read_file(path, workspace_root=self._workspace_root)
            except Exception as exc:  # noqa: BLE001 - per-item failure captured.
                errors.append(FetchError(uri=str(path), error=str(exc)))
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
            return FetchResult(errors=(FetchError(uri=base_url, error=str(exc)),))

        document = FetchedDocument(title=base_url, text=content, uri=base_url)
        return FetchResult(documents=(document,))

    @staticmethod
    def _cancelled(cancel: CancelSignal | None) -> bool:
        return cancel is not None and cancel.is_set()
