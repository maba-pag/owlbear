"""Ingest pipeline: text -> chunks + entity extraction -> knowledge graph."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from urllib.parse import unquote, urlparse
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from owlbear_knowledge.content_safety import should_wrap, wrap_untrusted_content

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_knowledge.chunker import TextChunker
    from owlbear_knowledge.extractor import EntityExtractor
    from owlbear_knowledge.intake import IntakeResult
    from owlbear_knowledge.source_store import KnowledgeSourceStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class IngestResult(BaseModel):
    """Result of a single ingest operation."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    chunk_count: int
    entity_count: int
    edge_count: int
    status: Literal["ok", "partial", "failed", "skipped", "cancelled", "blocked"]
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class IngestPipeline:
    """Async pipeline for ingesting content into the knowledge graph.

    Args:
        document_store: Persistence layer for documents, chunks, and embeddings.
        entity_extractor: Entity extraction component.
        text_chunker: Text splitting component.
        cancel_signal: Optional threading.Event; if set, ingest returns cancelled.
        injection_mode: Reserved for future pipeline-level mode override.
        source_store: Optional KnowledgeSourceStore; when supplied, ingest_text
            resolves or creates a KnowledgeSource record by URL and forwards its
            UUID as the document's source_id FK before chunk storage.
    """

    def __init__(  # noqa: PLR0913
        self,
        document_store: object,
        entity_extractor: EntityExtractor,
        text_chunker: TextChunker,
        cancel_signal: object | None = None,
        injection_mode: Literal["strict", "warn"] = "warn",
        source_store: KnowledgeSourceStore | None = None,
    ) -> None:
        self._docs = document_store
        self._extractor = entity_extractor
        self._chunker = text_chunker
        self._cancel_signal = cancel_signal
        self._injection_mode = injection_mode
        self._source_store = source_store

    def _resolve_source_by_url(
        self,
        source_url: str,
        scope: str,
    ) -> object | None:
        if self._source_store is None:
            return None
        return self._source_store.resolve_by_url(source_url, scope=scope)

    @staticmethod
    def _raise_if_exception(result: object) -> None:
        if isinstance(result, BaseException):
            raise result

    @staticmethod
    def _extraction_warning(chunk_id: str, exc: BaseException) -> str:
        return f"chunk {chunk_id} extraction failed: {type(exc).__name__}: {exc}"

    @staticmethod
    def _local_path_from_source_url(source_url: str) -> str | None:
        if source_url.startswith("file://"):
            raw_path = source_url.removeprefix("file://")
            if raw_path.startswith("localhost/"):
                raw_path = raw_path.removeprefix("localhost")
            return unquote(raw_path)

        parsed = urlparse(source_url)
        if not parsed.scheme:
            return source_url
        return None

    @classmethod
    def _direct_source_config(
        cls,
        source_url: str,
    ) -> tuple[object, str, dict[str, object]]:
        from owlbear_knowledge.models import SourceType  # noqa: PLC0415

        local_path = cls._local_path_from_source_url(source_url)
        if local_path is not None:
            path = Path(local_path)
            config: dict[str, object] = {
                "url": source_url,
                "path": local_path,
                "pattern": path.name if path.is_absolute() else local_path,
            }
            if path.is_absolute():
                config["base_dir"] = str(path.parent)
            return SourceType.FILE_GLOB, "file", config

        return SourceType.URL_LIST, "http", {"url": source_url, "urls": [source_url]}

    def _resolve_or_create_source_id(
        self,
        source_url: str,
        scope: str,
    ) -> tuple[str | None, str | None]:
        if self._source_store is None:
            return None, None

        created_source_id: str | None = None
        resolved_source = self._resolve_source_by_url(source_url, scope)
        if resolved_source is None:
            from owlbear_knowledge.models import KnowledgeSource  # noqa: PLC0415

            now = datetime.now(tz=UTC).isoformat()
            source_type, fetch_method, config = self._direct_source_config(source_url)
            new_source = KnowledgeSource(
                name=source_url,
                source_type=source_type,
                fetch_method=fetch_method,
                enrich=True,
                config=config,
                scope=scope,
                created_at=now,
                updated_at=now,
            )
            created_source_id = new_source.id
            created_source = self._source_store.create(new_source)
            # Store implementation returns None; test doubles may return the source.
            resolved_source = (
                created_source if created_source is not None else self._resolve_source_by_url(source_url, scope)
            )

        resolved_source_id = getattr(resolved_source, "id", None)
        if not isinstance(resolved_source_id, str):
            resolved_source_id = created_source_id
        return resolved_source_id, created_source_id

    @staticmethod
    def _inline_source_name(source: str, metadata: dict[str, object]) -> str:
        for key in ("title", "source"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return source

    def _source_name_exists(self, name: str, scope: str) -> bool:
        if self._source_store is None:
            return False
        try:
            sources = self._source_store.list_all(scope)
        except TypeError:
            sources = self._source_store.list_all()
        return any(getattr(existing_source, "name", None) == name for existing_source in sources)

    def _unique_inline_source_name(self, source: str, scope: str, metadata: dict[str, object]) -> str:
        base_name = self._inline_source_name(source, metadata)
        if not self._source_name_exists(base_name, scope):
            return base_name

        source_suffix = source.rsplit(":", maxsplit=1)[-1][:8]
        candidate = f"{base_name} ({source_suffix})" if source_suffix else base_name
        if not self._source_name_exists(candidate, scope):
            return candidate

        return f"{base_name} ({uuid4().hex[:8]})"

    def _resolve_or_create_inline_source_id(
        self,
        source: str,
        scope: str,
        metadata: dict[str, object],
    ) -> tuple[str | None, str | None]:
        if self._source_store is None:
            return None, None

        resolved_source = self._resolve_source_by_url(source, scope)
        if resolved_source is not None:
            resolved_source_id = getattr(resolved_source, "id", None)
            return (resolved_source_id if isinstance(resolved_source_id, str) else None), None

        from owlbear_knowledge.models import KnowledgeSource, SourceType  # noqa: PLC0415

        now = datetime.now(tz=UTC).isoformat()
        inline_source = KnowledgeSource(
            name=self._unique_inline_source_name(source, scope, metadata),
            source_type=SourceType.INLINE,
            fetch_method="inline",
            enrich=True,
            enabled=True,
            refreshable=False,
            config={"url": source, "source": source, "inline": True},
            scope=scope,
            created_at=now,
            updated_at=now,
        )
        created_source_id = inline_source.id
        created_source = self._source_store.create(inline_source)
        resolved_source = created_source if created_source is not None else self._resolve_source_by_url(source, scope)
        resolved_source_id = getattr(resolved_source, "id", None)
        if not isinstance(resolved_source_id, str):
            resolved_source_id = created_source_id
        return resolved_source_id, created_source_id

    @staticmethod
    def _source_from_metadata(metadata: dict[str, object]) -> str | None:
        for key in ("source", "url"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _is_metadata_source_identity(value: str) -> bool:
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https", "file"}:
            return True
        if parsed.scheme:
            return False

        if value.startswith(("/", "./", "../", "~/")) or "/" in value:
            return True

        return bool(Path(value).suffix and not any(character.isspace() for character in value))

    @classmethod
    def _source_identity_from_metadata(cls, metadata: dict[str, object]) -> str | None:
        url_value = metadata.get("url")
        if isinstance(url_value, str) and url_value.strip():
            return url_value.strip()

        source_value = metadata.get("source")
        if not isinstance(source_value, str) or not source_value.strip():
            return None

        candidate = source_value.strip()
        if cls._is_metadata_source_identity(candidate):
            return candidate
        return None

    async def _cleanup_failed_ingest(
        self,
        doc_id: str,
        chunk_ids: list[str],
        created_source_id: str | None,
    ) -> None:
        try:
            self._docs.delete_document_data(doc_id)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            logger.debug("cleanup of failed ingest document failed", exc_info=True)

        if chunk_ids:
            try:
                self._docs.delete_chunk_embeddings(chunk_ids)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                logger.debug(
                    "cleanup of failed ingest embeddings failed",
                    exc_info=True,
                )

        if created_source_id is not None and self._source_store is not None:
            try:
                self._source_store.delete(created_source_id)
            except Exception:  # noqa: BLE001
                logger.debug("cleanup of failed ingest source failed", exc_info=True)

    async def ingest_text(
        self,
        text: str,
        *,
        metadata: dict[str, object] | None = None,
        scope: str = "global",
        source_id: str | None = None,
        source_url: str | None = None,
    ) -> IngestResult:
        """Chunk *text*, extract entities, persist to store, return IngestResult.

        On internal failure, returns IngestResult with status='failed' and
        zero counts — no exceptions are propagated.
        """
        created_source_id: str | None = None
        fallback_doc_id = uuid4().hex
        try:
            from owlbear_knowledge.intake import IntakeResult  # noqa: PLC0415

            intake_metadata: dict[str, object] = dict(metadata or {})
            metadata_source_identity = self._source_identity_from_metadata(intake_metadata)
            metadata_source = self._source_from_metadata(intake_metadata)
            source = (
                source_url
                or metadata_source_identity
                or metadata_source
                or (f"source:{source_id}" if source_id is not None else f"inline:{fallback_doc_id}")
            )
            source_identity = source_url or metadata_source_identity
            if "source_type" not in intake_metadata:
                if source_identity is None:
                    intake_metadata["source_type"] = "text"
                else:
                    intake_metadata["source_type"] = (
                        "file" if self._local_path_from_source_url(source_identity) is not None else "url"
                    )
            intake_metadata.setdefault("fetched_at", datetime.now(tz=UTC).isoformat())

            resolved_source_id = source_id
            if source_identity is not None and self._source_store is not None:
                resolved_source_id, created_source_id = self._resolve_or_create_source_id(
                    source_identity,
                    scope,
                )
            elif resolved_source_id is None and self._source_store is not None:
                resolved_source_id, created_source_id = self._resolve_or_create_inline_source_id(
                    source,
                    scope,
                    intake_metadata,
                )

            result = await self.ingest(
                IntakeResult(content=text, source=source, metadata=intake_metadata),
                scope=scope,
                source_id=resolved_source_id,
            )
            if result.status == "failed" and created_source_id is not None:
                await self._cleanup_failed_ingest(result.document_id, [], created_source_id)

        except Exception:
            logger.exception("ingest_text failed for doc_id=%s", fallback_doc_id)
            await self._cleanup_failed_ingest(fallback_doc_id, [], created_source_id)
            return IngestResult(
                document_id=fallback_doc_id,
                chunk_count=0,
                entity_count=0,
                edge_count=0,
                status="failed",
            )
        else:
            return result

    async def ingest(
        self,
        intake: IntakeResult,
        *,
        scope: str = "global",
        source_id: str | None = None,
        content_cleaner: Callable[[str], str] | None = None,
    ) -> IngestResult:
        """Ingest an IntakeResult with delta detection and cancellation support.

        **Replace-on-change semantics:** when ``check_content_changed`` returns
        ``changed=True`` with an ``existing_id``, the replacement document is
        staged first.  The prior document is deleted only after the replacement
        has been persisted and content-hashed successfully, preserving the last
        good version if replacement ingest fails.

        Untrusted-source content (determined by
        :func:`~owlbear_knowledge.content_safety.should_wrap`) is wrapped in
        ``<untrusted_web_content>`` sentinel tags before entity extraction to
        prevent prompt injection from malicious web pages.  Local/text sources
        (``file``, ``file_glob``, ``text``) and absent source types are not
        wrapped; all other source types are wrapped by default.

        Args:
            intake: Content to ingest, as produced by read_file/read_url/read_text.
            scope: Scope tag applied to all stored objects.  Defaults to ``'global'``.
            source_id: Optional source UUID to persist on the document row.
            content_cleaner: Optional callable applied to raw content before hashing.
                When provided, delta detection compares hashes of the *cleaned* output
                rather than the raw content, so cosmetic HTML changes do not trigger
                unnecessary re-ingestion.

        Returns:
            IngestResult with status: ok | partial | skipped | cancelled | failed | blocked.
        """
        doc_id = uuid4().hex
        chunk_ids: list[str] = []
        try:
            if self._cancel_signal is not None and self._cancel_signal.is_set():  # type: ignore[union-attr]
                return IngestResult(
                    document_id=doc_id,
                    chunk_count=0,
                    entity_count=0,
                    edge_count=0,
                    status="cancelled",
                )

            content_for_hash = content_cleaner(intake.content) if content_cleaner is not None else intake.content
            changed, existing_id = self._docs.check_content_changed(  # type: ignore[union-attr]
                intake.source, content_for_hash, scope
            )
            if not changed:
                return IngestResult(
                    document_id=existing_id or doc_id,
                    chunk_count=0,
                    entity_count=0,
                    edge_count=0,
                    status="skipped",
                )

            _meta: dict[str, object] = dict(intake.metadata)
            chunks = await asyncio.to_thread(self._chunker.chunk, intake.content, metadata=_meta)
            chunk_count = len(chunks)

            self._docs.insert_document(  # type: ignore[union-attr]
                doc_id,
                intake,
                scope=scope,
                source_id=source_id,
            )

            chunk_ids = self._docs.store_chunks(doc_id, chunks, scope=scope)  # type: ignore[union-attr]
            chunk_texts = [c.text for c in chunks]

            _should_wrap = should_wrap(_meta.get("source_type"))  # type: ignore[arg-type]

            extract_coros = [
                self._extractor.extract(
                    wrap_untrusted_content(c.text, source_url=str(intake.source)) if _should_wrap else c.text
                )
                for c in chunks
            ]

            embed_coro = asyncio.to_thread(
                self._docs.store_embeddings,
                chunk_ids,
                chunk_texts,  # type: ignore[union-attr]
                scope=scope,
            )
            all_results = await asyncio.gather(embed_coro, *extract_coros, return_exceptions=True)
            self._raise_if_exception(all_results[0])

            extraction_results = []
            extraction_chunk_ids = []
            warnings = []
            for chunk_id, extraction_result in zip(chunk_ids, all_results[1:], strict=False):
                if isinstance(extraction_result, BaseException):
                    warnings.append(self._extraction_warning(chunk_id, extraction_result))
                    continue
                extraction_results.append(extraction_result)
                extraction_chunk_ids.append(chunk_id)

            entity_count, edge_count = self._docs.store_extractions(  # type: ignore[union-attr]
                extraction_results,
                scope=scope,
                document_id=doc_id,
                chunk_ids=extraction_chunk_ids,
            )
            status: Literal["ok", "partial"] = "partial" if warnings else "ok"
            error = "; ".join(warnings) if warnings else None
            self._docs.set_status(  # type: ignore[union-attr]
                doc_id,
                status,
                source=intake.source,
                error=error,
                scope=scope,
            )
            self._docs.update_content_hash(doc_id, content_for_hash)  # type: ignore[union-attr]
            if existing_id is not None:
                self._docs.delete_document_data(existing_id)  # type: ignore[union-attr]

        except Exception:
            logger.exception("ingest failed for doc_id=%s", doc_id)
            await self._cleanup_failed_ingest(doc_id, chunk_ids, None)
            return IngestResult(
                document_id=doc_id,
                chunk_count=0,
                entity_count=0,
                edge_count=0,
                status="failed",
            )

        return IngestResult(
            document_id=doc_id,
            chunk_count=chunk_count,
            entity_count=entity_count,
            edge_count=edge_count,
            status=status,
            warnings=warnings,
        )
