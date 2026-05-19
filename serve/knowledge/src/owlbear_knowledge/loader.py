"""KB data loader: parse a sources manifest and ingest files into the knowledge graph."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import strictyaml as sy

from owlbear_knowledge import intake as intake_mod
from owlbear_knowledge._paths import sandbox_path
from owlbear_knowledge.models import KnowledgeSource, SourceType

if TYPE_CHECKING:
    from owlbear_knowledge.ingest import IngestPipeline
    from owlbear_knowledge.source_store import KnowledgeSourceStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Manifest YAML schema
# ---------------------------------------------------------------------------

# strictyaml forbids inline flow-style sequences (e.g. `sources: []`);
# this pattern normalises them to empty scalars before parsing.
_INLINE_EMPTY_SEQ_RE = re.compile(r":\s*\[\s*\]\s*$", re.MULTILINE)

_SOURCE_SCHEMA = sy.Map(
    {
        "name": sy.Str(),
        "type": sy.Enum(["file_glob", "url_list"]),
        "config": sy.MapPattern(sy.Str(), sy.Str() | sy.Seq(sy.Str())),
        sy.Optional("scope"): sy.Str(),
        sy.Optional("enabled"): sy.Bool(),
    }
)

_MANIFEST_SCHEMA = sy.Map(
    {
        "sources": sy.EmptyNone() | sy.Seq(_SOURCE_SCHEMA),
    }
)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ManifestEntry:
    """A single entry parsed from a sources manifest."""

    name: str
    type: str
    config: dict[str, object]
    scope: str = "global"
    enabled: bool = True


@dataclass
class LoadSummary:
    """Summary of a manifest load operation."""

    ingested: int = 0
    skipped: int = 0
    failed: int = 0
    all_source_ok: bool = True


def _source_defaults(entry: ManifestEntry) -> tuple[str, bool, dict[str, object]]:
    """Return fetch/enrich/config values for a manifest source."""
    config: dict[str, object] = dict(entry.config)
    if entry.type == SourceType.FILE_GLOB.value:
        glob_pattern = entry.config.get("glob") or entry.config.get("pattern") or ""
        if glob_pattern:
            config.setdefault("glob", glob_pattern)
            config.setdefault("pattern", glob_pattern)
        return "file", True, config

    if entry.type == SourceType.URL_LIST.value:
        urls = _manifest_urls(config)
        if urls:
            config.setdefault("url", urls[0])
            config["urls"] = urls
        return "http", True, config

    return "", False, config


def _manifest_urls(config: dict[str, object]) -> list[str]:
    """Return URL entries from manifest config keys."""
    urls: list[str] = []
    raw_urls = config.get("urls")
    if isinstance(raw_urls, list):
        urls.extend(url.strip() for url in raw_urls if isinstance(url, str) and url.strip())
    elif isinstance(raw_urls, str) and raw_urls.strip():
        urls.extend(url.strip() for url in raw_urls.split(",") if url.strip())

    raw_url = config.get("url")
    if isinstance(raw_url, str) and raw_url.strip() and raw_url.strip() not in urls:
        urls.append(raw_url.strip())
    return urls


def _find_source_by_name_scope(
    source_store: KnowledgeSourceStore,
    *,
    name: str,
    scope: str,
) -> KnowledgeSource | None:
    """Return an existing source by manifest identity, if present."""
    for source in source_store.list_all(scope):
        if source.name == name:
            return source
    return None


def _upsert_manifest_source(
    source_store: KnowledgeSourceStore,
    entry: ManifestEntry,
    *,
    now: str,
) -> KnowledgeSource:
    """Create or update the source row represented by a manifest entry."""
    fetch_method, enrich, source_config = _source_defaults(entry)
    existing_source = _find_source_by_name_scope(source_store, name=entry.name, scope=entry.scope)
    if existing_source is None:
        source = KnowledgeSource(
            name=entry.name,
            source_type=SourceType(entry.type),
            fetch_method=fetch_method,
            enrich=enrich,
            config=source_config,
            scope=entry.scope,
            enabled=entry.enabled,
            created_at=now,
            updated_at=now,
        )
        source_store.create(source)
        return source

    source = existing_source.model_copy(
        update={
            "source_type": SourceType(entry.type),
            "fetch_method": fetch_method,
            "enrich": enrich,
            "config": source_config,
            "enabled": entry.enabled,
            "updated_at": now,
        }
    )
    source_store.update(source)
    return source


def _record_ingest_result(summary: LoadSummary, result: object) -> bool:
    """Update load counters from an ingest result and return whether it failed."""
    status = getattr(result, "status", "ok")
    if status == "skipped":
        summary.skipped += 1
        return False
    if status == "failed":
        summary.failed += 1
        return True
    summary.ingested += 1
    return False


async def _load_url_list_entry(
    entry: ManifestEntry,
    source: KnowledgeSource,
    pipeline: IngestPipeline,
    summary: LoadSummary,
) -> None:
    """Read and ingest all URLs for a url_list manifest entry."""
    urls = _manifest_urls(source.config)
    if not urls:
        logger.warning("No URLs configured for source %r", entry.name)
        summary.failed += 1
        summary.all_source_ok = False
        return

    source_failed = 0
    for url in urls:
        try:
            intake_result = await intake_mod.read_url(url)
            result = await pipeline.ingest(
                intake_result,
                scope=entry.scope,
                source_id=source.id,
            )
            source_failed += int(_record_ingest_result(summary, result))
        except Exception:
            logger.exception("Failed to process URL %s", url)
            summary.failed += 1
            source_failed += 1

    if source_failed == len(urls):
        summary.all_source_ok = False


async def _load_file_glob_entry(
    entry: ManifestEntry,
    source: KnowledgeSource,
    workspace_root: Path,
    pipeline: IngestPipeline,
    summary: LoadSummary,
) -> None:
    """Read and ingest all files for a file_glob manifest entry."""
    glob_pattern = str(source.config.get("glob") or source.config.get("pattern") or "").strip()
    if not glob_pattern:
        logger.warning("No glob pattern configured for source %r", entry.name)
        summary.failed += 1
        summary.all_source_ok = False
        return

    base_dir_raw = source.config.get("base_dir")
    base_dir_path = Path(base_dir_raw) if isinstance(base_dir_raw, str) and base_dir_raw else workspace_root
    try:
        safe_base = sandbox_path(workspace_root, base_dir_path)
    except PermissionError:
        logger.exception("Invalid base_dir %r for source %r", base_dir_raw, entry.name)
        summary.failed += 1
        summary.all_source_ok = False
        return

    files = await asyncio.to_thread(lambda pat=glob_pattern: sorted(safe_base.glob(pat)))

    if not files:
        logger.warning("No files matched glob %r for source %r", glob_pattern, entry.name)
        summary.failed += 1
        summary.all_source_ok = False
        return

    source_failed = 0
    for file_path in files:
        try:
            intake_result = await intake_mod.read_file(file_path, workspace_root=workspace_root)
            result = await pipeline.ingest(
                intake_result,
                scope=entry.scope,
                source_id=source.id,
            )
            source_failed += int(_record_ingest_result(summary, result))
        except Exception:
            logger.exception("Failed to process file %s", file_path)
            summary.failed += 1
            source_failed += 1

    if source_failed == len(files):
        summary.all_source_ok = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class _ParseError(sy.exceptions.YAMLValidationError):  # type: ignore[misc]
    """Low-level YAML syntax error wrapped as YAMLValidationError.

    Subclasses YAMLValidationError so callers can catch the standard type.
    Overrides the chunk-dependent properties so __str__ is safe to call.
    """

    def __init__(self, message: str) -> None:
        # Skip parent __init__ (requires a chunk object); set attrs directly.
        self.context = "YAML parse error"
        self.problem = message
        self._chunk = None
        self.note = None

    @property  # type: ignore[override]
    def context_mark(self) -> None:  # type: ignore[override]
        return None

    @property  # type: ignore[override]
    def problem_mark(self) -> None:  # type: ignore[override]
        return None


def parse_manifest(yaml_text: str) -> list[ManifestEntry]:
    """Parse a sources manifest YAML string and return a list of ManifestEntry objects.

    Args:
        yaml_text: Raw YAML string containing the sources manifest.

    Returns:
        List of ManifestEntry objects, one per source.

    Raises:
        strictyaml.YAMLValidationError: If the YAML is invalid or does not match the schema.
    """
    # Normalise inline empty-list syntax (`[]`) to a null scalar so that
    # EmptyNone() in the schema can match it (strictyaml forbids flow sequences).
    normalized = _INLINE_EMPTY_SEQ_RE.sub(":", yaml_text)
    try:
        doc = sy.load(normalized, _MANIFEST_SCHEMA)
    except sy.YAMLValidationError:
        raise
    except Exception as exc:
        raise _ParseError(str(exc)) from exc
    raw_sources = doc.data["sources"]
    if raw_sources is None:
        return []
    return [
        ManifestEntry(
            name=entry["name"],
            type=entry["type"],
            config=dict(entry["config"]),
            scope=entry.get("scope", "global"),
            enabled=entry.get("enabled", True),
        )
        for entry in raw_sources
    ]


async def load_manifest_file(
    manifest_path: Path,
    workspace_root: Path,
    source_store: KnowledgeSourceStore,
    pipeline: IngestPipeline,
) -> LoadSummary:
    """Load a manifest file and ingest all matching files into the knowledge graph.

    Args:
        manifest_path: Path to the sources YAML manifest file.
        workspace_root: Root directory for resolving glob patterns.
        source_store: Store used to register each knowledge source.
        pipeline: Ingest pipeline for processing file content.

    Returns:
        LoadSummary with counts of ingested, skipped, and failed files.
    """
    yaml_text = await asyncio.to_thread(manifest_path.read_text, encoding="utf-8")
    entries = parse_manifest(yaml_text)

    summary = LoadSummary()
    now = datetime.now(tz=UTC).isoformat()

    for entry in entries:
        source = _upsert_manifest_source(source_store, entry, now=now)
        if not entry.enabled:
            logger.debug("Skipping disabled source %r", entry.name)
            continue

        if entry.type == SourceType.URL_LIST.value:
            await _load_url_list_entry(entry, source, pipeline, summary)
            continue

        await _load_file_glob_entry(entry, source, workspace_root, pipeline, summary)

    return summary


def main(args: list[str] | None = None) -> int:
    """CLI entry point for the KB data loader.

    Args:
        args: Command-line arguments. If None, sys.argv[1:] is used.

    Returns:
        Exit code: 0 when all sources processed successfully (or some skipped);
        non-zero when any source has all files fail.
    """
    parser = argparse.ArgumentParser(description="Load knowledge sources from a manifest file.")
    parser.add_argument("--manifest", required=True, help="Path to the sources YAML manifest.")
    parser.add_argument("--root", default=None, help="Workspace root (defaults to cwd).")

    parsed = parser.parse_args(args)

    manifest_path = Path(parsed.manifest)
    workspace_root = Path(parsed.root) if parsed.root else Path.cwd()

    from owlbear_knowledge.chunker import TextChunker  # noqa: PLC0415
    from owlbear_knowledge.document_store import DocumentStore  # noqa: PLC0415
    from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider  # noqa: PLC0415
    from owlbear_knowledge.extractor import EntityExtractor  # noqa: PLC0415
    from owlbear_knowledge.graph_store import GraphStore  # noqa: PLC0415
    from owlbear_knowledge.ingest import IngestPipeline  # noqa: PLC0415
    from owlbear_knowledge.qdrant import QdrantVectorStore  # noqa: PLC0415
    from owlbear_knowledge.schema import init_db as _init_db  # noqa: PLC0415
    from owlbear_knowledge.source_store import KnowledgeSourceStore  # noqa: PLC0415

    db_path = os.environ.get("OWLBEAR_LOCAL_KB_PATH") or os.environ.get(
        "OWLBEAR_KB_PATH", ".owlbear/knowledge/local.db"
    )
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    _init_db(conn)
    gs = GraphStore(conn)
    qdrant_path = os.environ.get("OWLBEAR_QDRANT_PATH", ".owlbear/knowledge/vectors")
    vs = QdrantVectorStore(location=qdrant_path)
    emb = BgeM3EmbeddingProvider()
    doc_store = DocumentStore(conn, gs, vs, emb)
    extractor = EntityExtractor()
    chunker = TextChunker()
    pipeline = IngestPipeline(doc_store, extractor, chunker)
    source_store = KnowledgeSourceStore(conn)

    try:
        summary = asyncio.run(
            load_manifest_file(
                manifest_path=manifest_path,
                workspace_root=workspace_root,
                source_store=source_store,
                pipeline=pipeline,
            )
        )
    finally:
        conn.close()

    return 0 if summary.all_source_ok else 1


if __name__ == "__main__":
    sys.exit(main())
