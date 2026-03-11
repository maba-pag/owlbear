"""Knowledge-source subcommands — manage knowledge sources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer

from owlbear.config import OwlBearSettings

if TYPE_CHECKING:
    from owlbear.memory.knowledge.source_store import KnowledgeSourceStore

app = typer.Typer(
    name="knowledge-source",
    help="Manage knowledge sources.",
    no_args_is_help=True,
)


def _get_source_store() -> KnowledgeSourceStore:
    """Return a :class:`KnowledgeSourceStore` backed by the knowledge DB."""
    import sqlite3  # noqa: PLC0415

    from owlbear.memory.knowledge.schema import init_db  # noqa: PLC0415
    from owlbear.memory.knowledge.source_store import (  # noqa: PLC0415
        KnowledgeSourceStore,
    )

    settings = OwlBearSettings()
    settings.knowledge_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.knowledge_db_path))
    init_db(conn)
    return KnowledgeSourceStore(conn)


_VALID_SOURCE_TYPES = ("url_list", "crawl", "file_glob")


@app.command("add")
def ks_add(  # noqa: PLR0913
    name: Annotated[str, typer.Option("--name", "-n", help="Source name.")],
    source_type: Annotated[
        str, typer.Option("--type", "-t", help="Source type: url_list, crawl, or file_glob.")
    ],
    urls: Annotated[str, typer.Option("--urls", help="Comma-separated URLs (for url_list).")] = "",
    seeds: Annotated[
        str, typer.Option("--seeds", help="Comma-separated seed URLs (for crawl).")
    ] = "",
    pattern: Annotated[str, typer.Option("--pattern", help="Glob pattern (for file_glob).")] = "",
    scope: Annotated[
        str, typer.Option("--scope", "-s", help="Scope (default: global).")
    ] = "global",
    max_depth: Annotated[int, typer.Option("--max-depth", help="Max crawl depth (for crawl).")] = 1,
    max_pages: Annotated[
        int, typer.Option("--max-pages", help="Max pages to crawl (for crawl).")
    ] = 50,
) -> None:
    """Add a new knowledge source."""
    from datetime import UTC, datetime  # noqa: PLC0415

    from owlbear.memory.knowledge.models import (  # noqa: PLC0415
        KnowledgeSource,
        SourceType,
    )

    if source_type not in _VALID_SOURCE_TYPES:
        valid = ", ".join(_VALID_SOURCE_TYPES)
        typer.echo(f"Error: Invalid type '{source_type}'. Must be one of: {valid}")
        raise typer.Exit(code=1)

    # Build config dict based on type
    config: dict[str, object] = {}
    if source_type == "url_list":
        if not urls:
            typer.echo("Error: --urls is required for type 'url_list'.")
            raise typer.Exit(code=1)
        config["urls"] = [u.strip() for u in urls.split(",")]
    elif source_type == "crawl":
        if not seeds:
            typer.echo("Error: --seeds is required for type 'crawl'.")
            raise typer.Exit(code=1)
        config["seeds"] = [s.strip() for s in seeds.split(",")]
        config["max_depth"] = max_depth
        config["max_pages"] = max_pages
    elif source_type == "file_glob":
        if not pattern:
            typer.echo("Error: --pattern is required for type 'file_glob'.")
            raise typer.Exit(code=1)
        config["pattern"] = pattern

    now = datetime.now(tz=UTC).isoformat()
    source = KnowledgeSource(
        name=name,
        source_type=SourceType(source_type),
        config=config,
        scope=scope,
        created_at=now,
        updated_at=now,
    )

    store = _get_source_store()
    store.create(source)
    typer.echo(f"Added knowledge source '{name}' (type: {source_type}, scope: {scope})")


@app.command("list")
def ks_list(
    scope: Annotated[str, typer.Option("--scope", "-s", help="Filter by scope.")] = "",
) -> None:
    """List knowledge sources."""
    store = _get_source_store()
    scope_filter = scope or None
    sources = store.list_all(scope=scope_filter)

    if not sources:
        typer.echo("No knowledge sources found.")
        return

    from rich.console import Console  # noqa: PLC0415
    from rich.table import Table  # noqa: PLC0415

    table = Table("Name", "Type", "Scope", "Enabled", "Last Refreshed")
    for s in sources:
        table.add_row(
            s.name,
            str(s.source_type),
            s.scope,
            "yes" if s.enabled else "no",
            s.last_refreshed_at or "never",
        )
    Console().print(table)


@app.command("show")
def ks_show(
    name: Annotated[str, typer.Argument(help="Name of the source to show.")],
    scope: Annotated[str, typer.Option("--scope", "-s", help="Source scope.")] = "global",
) -> None:
    """Show details of a knowledge source."""
    import json  # noqa: PLC0415

    store = _get_source_store()
    source = store.get_by_name(name, scope=scope)
    if source is None:
        typer.echo(f"Error: No knowledge source named '{name}' (scope: {scope})")
        raise typer.Exit(code=1)

    typer.echo(f"Name:           {source.name}")
    typer.echo(f"Type:           {source.source_type}")
    typer.echo(f"Scope:          {source.scope}")
    typer.echo(f"Enabled:        {source.enabled}")
    typer.echo(f"Priority:       {source.priority}")
    typer.echo(f"Config:         {json.dumps(source.config, indent=2)}")
    typer.echo(f"Last Refreshed: {source.last_refreshed_at or 'never'}")
    typer.echo(f"Last Error:     {source.last_error or 'none'}")
    typer.echo(f"Created:        {source.created_at}")


@app.command("remove")
def ks_remove(
    name: Annotated[str, typer.Argument(help="Name of the source to remove.")],
    scope: Annotated[str, typer.Option("--scope", "-s", help="Source scope.")] = "global",
) -> None:
    """Remove a knowledge source."""
    store = _get_source_store()
    source = store.get_by_name(name, scope=scope)
    if source is None:
        typer.echo(f"Error: No knowledge source named '{name}'")
        raise typer.Exit(code=1)

    store.delete(source.id)
    typer.echo(f"Removed knowledge source '{name}'")
